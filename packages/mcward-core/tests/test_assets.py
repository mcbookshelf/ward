"""Tests for environment asset installation."""

import asyncio
import sys
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient, ConnectError, HTTPStatusError, Request, Response

from mcward import (
    AssetNotFoundError,
    DownloadFailedError,
    InstallError,
    JavaNotFoundError,
    Version,
)
from mcward._assets import (
    _build_ward,
    _download_file,
    _get_json,
    _install_java,
    _install_mod,
    _install_server,
    _unpack_runtime,
    install,
)
from mcward._constants import JAVA_VERSION
from mcward._java import find_binary

JAVA_NAME = "java.exe" if sys.platform == "win32" else "java"


def json_client(data) -> AsyncMock:
    """An AsyncClient mock whose get() returns the given JSON document."""
    response = Mock(spec=Response)
    response.json.return_value = data
    client = AsyncMock(spec=AsyncClient)
    client.get.return_value = response
    return client


def http_error_client() -> AsyncMock:
    """An AsyncClient mock whose get() response is an HTTP error."""
    response = Mock(spec=Response)
    response.raise_for_status.side_effect = HTTPStatusError(
        "404 Not Found", request=Mock(spec=Request), response=Mock(spec=Response)
    )
    client = AsyncMock(spec=AsyncClient)
    client.get.return_value = response
    return client


def stream_client(content: bytes = b"", error: Exception | None = None) -> Mock:
    """An AsyncClient mock whose stream() yields the given content."""

    async def aiter_bytes():
        yield content

    response = Mock()
    if error:
        response.raise_for_status.side_effect = error
    response.aiter_bytes = aiter_bytes

    context = AsyncMock()
    context.__aenter__.return_value = response
    client = Mock(spec=AsyncClient)
    client.stream.return_value = context
    return client


def zip_archive(tmp_path: Path, *, empty: bool = False) -> bytes:
    """A JRE-shaped zip archive (or an empty one without a java binary)."""
    source = tmp_path / "archive_source"
    if empty:
        (source / "docs").mkdir(parents=True)
    else:
        binary = source / "jdk-jre" / "bin" / JAVA_NAME
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_bytes(b"")
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as file:
        for path in source.rglob("*"):
            file.write(path, path.relative_to(source))
    return archive.read_bytes()


class TestInstallServer:
    @pytest.mark.anyio
    async def test_prefers_newest_stable_loader(self, tmp_path: Path) -> None:
        client = json_client(
            [
                {"loader": {"version": "0.16.0-beta.1", "stable": False}},
                {"loader": {"version": "0.15.11", "stable": True}},
                {"loader": {"version": "0.15.10", "stable": True}},
            ]
        )

        with patch("mcward._assets._download_file") as mock_download:
            await _install_server(client, "26.1.2", tmp_path / "server.jar")

        url = mock_download.call_args[0][1]
        assert "26.1.2" in url
        assert "0.15.11" in url
        assert url.endswith("/server/jar")

    @pytest.mark.anyio
    async def test_falls_back_to_newest_when_nothing_stable(self, tmp_path: Path) -> None:
        client = json_client([{"loader": {"version": "0.16.0-beta.1", "stable": False}}])

        with patch("mcward._assets._download_file") as mock_download:
            await _install_server(client, "26.1.2", tmp_path / "server.jar")

        assert "0.16.0-beta.1" in mock_download.call_args[0][1]

    @pytest.mark.anyio
    async def test_unsupported_version_raises(self, tmp_path: Path) -> None:
        client = json_client([])

        with pytest.raises(AssetNotFoundError):
            await _install_server(client, "99.99.99", tmp_path / "server.jar")


class TestInstallMod:
    @pytest.mark.anyio
    async def test_downloads_newest_compatible_release(self, tmp_path: Path) -> None:
        client = json_client(
            [
                {
                    "game_versions": ["26.1.2", "26.1.1"],
                    "files": [{"url": "https://cdn/new.jar", "primary": True}],
                },
                {
                    "game_versions": ["26.1.1"],
                    "files": [{"url": "https://cdn/old.jar", "primary": True}],
                },
            ]
        )

        with patch("mcward._assets._download_file") as mock_download:
            await _install_mod(client, "fabric-api", "26.1.2", tmp_path / "mod.jar")

        assert "fabric-api" in client.get.call_args[0][0]
        assert mock_download.call_args[0][1] == "https://cdn/new.jar"

    @pytest.mark.anyio
    async def test_downloads_the_primary_file(self, tmp_path: Path) -> None:
        """The primary file wins over attachment order (e.g. a sources jar)."""
        client = json_client(
            [
                {
                    "game_versions": ["26.1.2"],
                    "files": [
                        {"url": "https://cdn/sources.jar", "primary": False},
                        {"url": "https://cdn/mod.jar", "primary": True},
                    ],
                },
            ]
        )

        with patch("mcward._assets._download_file") as mock_download:
            await _install_mod(client, "ward", "26.1.2", tmp_path / "mod.jar")

        assert mock_download.call_args[0][1] == "https://cdn/mod.jar"

    @pytest.mark.anyio
    async def test_requires_exact_version_match(self, tmp_path: Path) -> None:
        """A "26.1.20" release must not satisfy "26.1.2"."""
        client = json_client(
            [
                {
                    "game_versions": ["26.1.20"],
                    "files": [{"url": "https://cdn/mod.jar", "primary": True}],
                }
            ]
        )

        with pytest.raises(AssetNotFoundError):
            await _install_mod(client, "ward", "26.1.2", tmp_path / "mod.jar")

    @pytest.mark.anyio
    async def test_no_compatible_release_raises(self, tmp_path: Path) -> None:
        client = json_client(
            [
                {
                    "game_versions": ["26.1.1"],
                    "files": [{"url": "https://cdn/mod.jar", "primary": True}],
                }
            ]
        )

        with pytest.raises(AssetNotFoundError) as exc_info:
            await _install_mod(client, "ward", "99.99.99", tmp_path / "mod.jar")

        assert exc_info.value.asset == "ward"
        assert exc_info.value.version == "99.99.99"


class TestGetJson:
    @pytest.mark.anyio
    async def test_returns_document(self) -> None:
        assert await _get_json(json_client({"ok": True}), "https://api/x") == {"ok": True}

    @pytest.mark.anyio
    async def test_http_errors_become_download_failures(self) -> None:
        """Metadata fetch failures surface as WardErrors, not raw tracebacks."""
        with pytest.raises(DownloadFailedError):
            await _get_json(http_error_client(), "https://api/x")


class TestDownloadFile:
    @pytest.mark.anyio
    async def test_writes_file(self, tmp_path: Path) -> None:
        client = stream_client(b"fake jar content")

        target = tmp_path / "test.jar"
        await _download_file(client, "https://example.com/test.jar", target)

        assert target.read_bytes() == b"fake jar content"

    @pytest.mark.anyio
    async def test_creates_parent_directories(self, tmp_path: Path) -> None:
        client = stream_client(b"content")

        target = tmp_path / "nested" / "dirs" / "test.jar"
        await _download_file(client, "https://example.com/test.jar", target)

        assert target.read_bytes() == b"content"

    @pytest.mark.anyio
    async def test_http_error_raises_and_leaves_no_file(self, tmp_path: Path) -> None:
        error = HTTPStatusError(
            "404 Not Found", request=Mock(spec=Request), response=Mock(spec=Response)
        )
        client = stream_client(error=error)

        target = tmp_path / "test.jar"
        with pytest.raises(DownloadFailedError):
            await _download_file(client, "https://example.com/404.jar", target)

        assert not target.exists()
        assert list(tmp_path.iterdir()) == []  # no .part leftover

    @pytest.mark.anyio
    async def test_connection_error_is_wrapped(self, tmp_path: Path) -> None:
        client = stream_client()
        client.stream.return_value.__aenter__.side_effect = ConnectError("offline")

        with pytest.raises(DownloadFailedError):
            await _download_file(client, "https://example.com/test.jar", tmp_path / "test.jar")


class TestBuildWard:
    @pytest.mark.anyio
    async def test_build_ward_success(self, tmp_path: Path) -> None:
        """A successful build copies the produced jar into the mods directory."""
        gradle_script = tmp_path / "gradlew.bat"
        gradle_script.write_text("@echo off")

        build_libs = tmp_path / "build" / "libs"
        build_libs.mkdir(parents=True)
        jar_file = build_libs / "ward-1.0.0.jar"
        jar_file.write_text("fake jar")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", None)
        mock_process.returncode = 0

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            await _build_ward(target_dir)

            assert (target_dir / "ward.jar").exists()

    @pytest.mark.anyio
    async def test_build_ward_gradle_failure_raises(self, tmp_path: Path) -> None:
        """A failing build surfaces the tail of the merged gradle output."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"> Task :compileJava FAILED\nboom", None)
        mock_process.returncode = 1

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            with pytest.raises(InstallError, match="compileJava FAILED"):
                await _build_ward(tmp_path / "target")

    @pytest.mark.anyio
    async def test_build_ward_no_jar_raises(self, tmp_path: Path) -> None:
        """A build that produces no jar fails instead of installing nothing."""
        build_libs = tmp_path / "build" / "libs"
        build_libs.mkdir(parents=True)

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", None)
        mock_process.returncode = 0

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            with pytest.raises(InstallError, match="No jar file found"):
                await _build_ward(tmp_path / "target")

    @pytest.mark.anyio
    async def test_build_ward_skips_sources_and_dev_jars(self, tmp_path: Path) -> None:
        """The release jar wins over the -sources and -dev variants beside it."""
        build_libs = tmp_path / "build" / "libs"
        build_libs.mkdir(parents=True)

        (build_libs / "ward-1.0.0-sources.jar").write_text("sources")
        (build_libs / "ward-1.0.0-dev.jar").write_text("dev")
        (build_libs / "ward-1.0.0.jar").write_text("release")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", None)
        mock_process.returncode = 0

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            await _build_ward(target_dir)

            copied_content = (target_dir / "ward.jar").read_text()
            assert copied_content == "release"


class TestInstall:
    @pytest.mark.anyio
    async def test_regular_version_installs_three_assets(self, tmp_path: Path) -> None:
        version = Version.parse("26.1.2")

        with (
            patch("mcward._assets._install_server", AsyncMock()) as mock_server,
            patch("mcward._assets._install_mod", AsyncMock()) as mock_mod,
            patch("mcward._assets._java.resolve", return_value=Mock()),
        ):
            await install(tmp_path, version)

        mock_server.assert_awaited_once()
        [server_call] = mock_server.await_args_list
        assert server_call.args[1] == "26.1.2"
        projects = [call.args[1] for call in mock_mod.await_args_list]
        assert sorted(projects) == ["fabric-api", "ward"]

    @pytest.mark.anyio
    async def test_dev_version_builds_ward(self, tmp_path: Path) -> None:
        """A dev version builds the mod with gradle instead of downloading it."""
        version = Version.parse("dev/26.1.2")

        with (
            patch("mcward._assets._install_server", AsyncMock()) as mock_server,
            patch("mcward._assets._install_mod", AsyncMock()) as mock_mod,
            patch("mcward._assets._build_ward", AsyncMock()) as mock_build,
            patch("mcward._assets._java.resolve", return_value=Mock()),
        ):
            await install(tmp_path, version)

        # The dev/ prefix is stripped for asset resolution
        [server_call] = mock_server.await_args_list
        assert server_call.args[1] == "26.1.2"
        mock_build.assert_awaited_once()
        projects = [call.args[1] for call in mock_mod.await_args_list]
        assert projects == ["fabric-api"]

    @pytest.mark.anyio
    async def test_provisions_java_when_unresolved(self, tmp_path: Path) -> None:
        """A missing Java runtime is provisioned in the same gather."""
        version = Version.parse("26.1.2")

        with (
            patch("mcward._assets._install_server", AsyncMock()),
            patch("mcward._assets._install_mod", AsyncMock()),
            patch("mcward._assets._java.resolve", return_value=None),
            patch("mcward._assets._install_java", AsyncMock()) as mock_java,
        ):
            await install(tmp_path, version)

        mock_java.assert_awaited_once()

    @pytest.mark.anyio
    async def test_installer_failure_surfaces_as_ward_error(self, tmp_path: Path) -> None:
        """A failing task cancels the rest and raises the Ward error itself."""
        failure = AssetNotFoundError("ward", "26.1.2")

        with (
            patch("mcward._assets._install_server", AsyncMock()),
            patch("mcward._assets._install_mod", AsyncMock(side_effect=failure)),
            patch("mcward._assets._java.resolve", return_value=Mock()),
            pytest.raises(AssetNotFoundError),
        ):
            await install(tmp_path, Version.parse("26.1.2"))

    @pytest.mark.anyio
    async def test_assets_download_concurrently(self, tmp_path: Path) -> None:
        version = Version.parse("26.1.2")
        order = []

        async def tracked(*args) -> None:
            order.append("start")
            await asyncio.sleep(0.01)
            order.append("end")

        with (
            patch("mcward._assets._install_server", side_effect=tracked),
            patch("mcward._assets._install_mod", side_effect=tracked),
            patch("mcward._assets._java.resolve", return_value=Mock()),
        ):
            await install(tmp_path, version)

        # All three started before any finished
        assert order[:3] == ["start", "start", "start"]


class TestInstallJava:
    def fake_download(self, archive: bytes):
        async def download(client, url, file: Path) -> None:
            file.write_bytes(archive)

        return download

    @pytest.mark.anyio
    async def test_extracts_archive_into_cache(self, tmp_path: Path) -> None:
        runtime = tmp_path / "cache" / "java" / str(JAVA_VERSION)

        with (
            patch("mcward._assets._adoptium_platform", return_value=("linux", "x64", ".zip")),
            patch("mcward._assets._download_file", self.fake_download(zip_archive(tmp_path))),
            patch("mcward._assets.JAVA_DIR", runtime),
        ):
            await _install_java(AsyncMock())

        assert find_binary(runtime) is not None
        # No archive or staging leftovers next to the runtime
        assert [p.name for p in runtime.parent.iterdir()] == [str(JAVA_VERSION)]

    @pytest.mark.anyio
    async def test_rejects_runtime_without_java(self, tmp_path: Path) -> None:
        runtime = tmp_path / "cache" / "java" / str(JAVA_VERSION)
        archive = zip_archive(tmp_path, empty=True)

        with (
            patch("mcward._assets._adoptium_platform", return_value=("linux", "x64", ".zip")),
            patch("mcward._assets._download_file", self.fake_download(archive)),
            patch("mcward._assets.JAVA_DIR", runtime),
            pytest.raises(JavaNotFoundError, match="no java executable"),
        ):
            await _install_java(AsyncMock())

    def test_losing_the_provisioning_race_is_harmless(self, tmp_path: Path) -> None:
        """A runtime installed concurrently survives; the loser discards its copy."""
        runtime = tmp_path / "java" / str(JAVA_VERSION)
        winner = runtime / "jdk-winner" / "bin" / JAVA_NAME
        winner.parent.mkdir(parents=True)
        winner.write_bytes(b"")

        staging = tmp_path / "java" / "staging"
        staging.mkdir()
        archive = staging / "temurin.zip"
        archive.write_bytes(zip_archive(tmp_path))

        _unpack_runtime(archive, runtime)

        # The winner's runtime survives; the loser's copy stays in staging for the caller to remove
        assert winner.exists()
        assert (staging / "runtime" / "jdk-jre").exists()
