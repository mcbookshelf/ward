"""Tests for asset download functionality."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient, HTTPStatusError, Request, Response

from mcward import AssetNotFoundError, InstallError, Version
from mcward._assets import (
    _build_ward,
    _download_file,
    _resolve_fabric_url,
    _resolve_modrinth_url,
    download,
)


class TestResolveFabricUrl:
    """Test Fabric API URL resolution."""

    @pytest.mark.anyio
    async def test_resolve_fabric_url_success(self) -> None:
        """Test successful Fabric URL resolution."""
        mock_client = AsyncMock(spec=AsyncClient)
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [
            {"loader": {"version": "0.15.11"}},
            {"loader": {"version": "0.15.10"}},
        ]
        mock_client.get.return_value = mock_response

        url = await _resolve_fabric_url(mock_client, "26.1.2")

        # Should get loader versions for MC version
        mock_client.get.assert_called_once()
        call_url = mock_client.get.call_args[0][0]
        assert "26.1.2" in call_url
        assert "fabricmc.net" in call_url

        # Should return server jar URL with latest loader
        assert "0.15.11" in url
        assert "/server/jar" in url

    @pytest.mark.anyio
    async def test_resolve_fabric_url_http_error_propagates(self) -> None:
        """Test that HTTP errors propagate correctly."""
        mock_client = AsyncMock(spec=AsyncClient)
        mock_response = Mock(spec=Response)
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            "404 Not Found", request=Mock(spec=Request), response=Mock(spec=Response)
        )
        mock_client.get.return_value = mock_response

        with pytest.raises(HTTPStatusError):
            await _resolve_fabric_url(mock_client, "99.99.99")


class TestResolveModrinthUrl:
    """Test Modrinth API URL resolution."""

    @pytest.mark.anyio
    async def test_resolve_modrinth_url_success(self) -> None:
        """Test successful Modrinth URL resolution."""
        mock_client = AsyncMock(spec=AsyncClient)
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [
            {
                "game_versions": ["26.1.2", "26.1.1"],
                "files": [{"url": "https://cdn.modrinth.com/data/fabric-api-1.0.jar"}],
            },
            {
                "game_versions": ["26.1.1"],
                "files": [{"url": "https://cdn.modrinth.com/data/fabric-api-0.9.jar"}],
            },
        ]
        mock_client.get.return_value = mock_response

        url = await _resolve_modrinth_url(mock_client, "fabric-api", "26.1.2")

        # Should get project versions
        mock_client.get.assert_called_once()
        call_url = mock_client.get.call_args[0][0]
        assert "modrinth.com" in call_url
        assert "fabric-api" in call_url
        assert "/version" in call_url

        # Should return first compatible version's download URL
        assert url == "https://cdn.modrinth.com/data/fabric-api-1.0.jar"

    @pytest.mark.anyio
    async def test_resolve_modrinth_url_with_version_prefix(self) -> None:
        """Test that version matching works with partial version strings."""
        mock_client = AsyncMock(spec=AsyncClient)
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [
            {
                "game_versions": ["26.1.2", "26.1.1", "26.1"],
                "files": [{"url": "https://example.com/mod.jar"}],
            },
        ]
        mock_client.get.return_value = mock_response

        # Should match "26.1" prefix
        url = await _resolve_modrinth_url(mock_client, "ward", "26.1")
        assert url == "https://example.com/mod.jar"

    @pytest.mark.anyio
    async def test_resolve_modrinth_url_not_found_raises(self) -> None:
        """Test that missing version raises AssetNotFoundError."""
        mock_client = AsyncMock(spec=AsyncClient)
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = [
            {"game_versions": ["26.1.1"], "files": [{"url": "https://example.com/mod.jar"}]},
        ]
        mock_client.get.return_value = mock_response

        with pytest.raises(AssetNotFoundError) as exc_info:
            await _resolve_modrinth_url(mock_client, "ward", "99.99.99")

        assert exc_info.value.asset == "ward"
        assert exc_info.value.version == "99.99.99"

    @pytest.mark.anyio
    async def test_resolve_modrinth_url_empty_versions_raises(self) -> None:
        """Test that empty versions list raises AssetNotFoundError."""
        mock_client = AsyncMock(spec=AsyncClient)
        mock_response = Mock(spec=Response)
        mock_response.json.return_value = []  # No versions
        mock_client.get.return_value = mock_response

        with pytest.raises(AssetNotFoundError):
            await _resolve_modrinth_url(mock_client, "ward", "26.1.2")


class TestDownloadFile:
    """Test single file download."""

    @pytest.mark.anyio
    async def test_download_file_success(self, tmp_path: Path) -> None:
        """Test successful file download."""
        mock_client = AsyncMock(spec=AsyncClient)
        mock_response = Mock(spec=Response)
        mock_response.content = b"fake jar content"
        mock_client.get.return_value = mock_response

        target = tmp_path / "test.jar"

        # Create an async function that returns the URL (simulates resolve function)
        async def mock_url():
            return "https://example.com/test.jar"

        await _download_file(mock_client, mock_url(), target)

        # Should download and write file
        assert target.exists()
        assert target.read_bytes() == b"fake jar content"

    @pytest.mark.anyio
    async def test_download_file_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that parent directories are created."""
        mock_client = AsyncMock(spec=AsyncClient)
        mock_response = Mock(spec=Response)
        mock_response.content = b"content"
        mock_client.get.return_value = mock_response

        target = tmp_path / "nested" / "dirs" / "test.jar"

        async def mock_url():
            return "https://example.com/test.jar"

        await _download_file(mock_client, mock_url(), target)

        assert target.exists()
        assert target.read_bytes() == b"content"

    @pytest.mark.anyio
    async def test_download_file_http_error_propagates(self, tmp_path: Path) -> None:
        """Test that HTTP errors propagate."""
        mock_client = AsyncMock(spec=AsyncClient)
        mock_response = Mock(spec=Response)
        mock_response.raise_for_status.side_effect = HTTPStatusError(
            "404 Not Found", request=Mock(spec=Request), response=Mock(spec=Response)
        )
        mock_client.get.return_value = mock_response

        target = tmp_path / "test.jar"

        async def mock_url():
            return "https://example.com/404.jar"

        with pytest.raises(HTTPStatusError):
            await _download_file(mock_client, mock_url(), target)


class TestBuildWard:
    """Test gradle build for dev mode."""

    @pytest.mark.anyio
    async def test_build_ward_success(self, tmp_path: Path) -> None:
        """Test successful ward.jar build."""
        # Create fake gradle script and build output
        gradle_script = tmp_path / "gradlew.bat"
        gradle_script.write_text("@echo off")

        build_libs = tmp_path / "build" / "libs"
        build_libs.mkdir(parents=True)
        jar_file = build_libs / "ward-1.0.0.jar"
        jar_file.write_text("fake jar")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            await _build_ward(target_dir)

            # Should copy jar to target directory
            assert (target_dir / "ward.jar").exists()

    @pytest.mark.anyio
    async def test_build_ward_gradle_failure_raises(self, tmp_path: Path) -> None:
        """Test that gradle build failure raises InstallError."""
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"Build failed: compilation error")
        mock_process.returncode = 1

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            with pytest.raises(InstallError, match="Gradle build failed"):
                await _build_ward(tmp_path / "target")

    @pytest.mark.anyio
    async def test_build_ward_no_jar_raises(self, tmp_path: Path) -> None:
        """Test that missing jar file raises InstallError."""
        # Build succeeds but no jar is produced
        build_libs = tmp_path / "build" / "libs"
        build_libs.mkdir(parents=True)

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            with pytest.raises(InstallError, match="No jar file found"):
                await _build_ward(tmp_path / "target")

    @pytest.mark.anyio
    async def test_build_ward_skips_sources_and_dev_jars(self, tmp_path: Path) -> None:
        """Test that -sources and -dev jars are ignored."""
        build_libs = tmp_path / "build" / "libs"
        build_libs.mkdir(parents=True)

        # Create various jars
        (build_libs / "ward-1.0.0-sources.jar").write_text("sources")
        (build_libs / "ward-1.0.0-dev.jar").write_text("dev")
        (build_libs / "ward-1.0.0.jar").write_text("release")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("pathlib.Path.cwd", return_value=tmp_path),
        ):
            await _build_ward(target_dir)

            # Should copy the release jar, not sources or dev
            copied_content = (target_dir / "ward.jar").read_text()
            assert copied_content == "release"


class TestDownload:
    """Test main download orchestrator."""

    @pytest.mark.anyio
    async def test_download_regular_version(self, tmp_path: Path) -> None:
        """Test downloading a regular (non-dev) version."""
        version = Version("26.1.2", 26, 1, 2, 0)
        directory = tmp_path / "env"
        directory.mkdir()

        with (
            patch("mcward._assets._resolve_fabric_url") as mock_fabric,
            patch("mcward._assets._resolve_modrinth_url") as mock_modrinth,
            patch("mcward._assets._download_file") as mock_download,
        ):
            # Mock URL resolution to return awaitable
            mock_fabric.return_value = "https://fabric.example.com/server.jar"
            mock_modrinth.return_value = "https://modrinth.example.com/mod.jar"

            await download(directory, version)

            # Should resolve all three URLs
            assert mock_fabric.call_count == 1
            assert mock_modrinth.call_count == 2  # fabric-api and ward

            # Should download all three files
            assert mock_download.call_count == 3

    @pytest.mark.anyio
    async def test_download_dev_version_builds_ward(self, tmp_path: Path) -> None:
        """Test downloading dev version builds ward.jar locally."""
        version = Version("dev/26.1.2", 26, 1, 2, 0)
        directory = tmp_path / "env"
        directory.mkdir()

        with (
            patch("mcward._assets._resolve_fabric_url") as mock_fabric,
            patch("mcward._assets._resolve_modrinth_url") as mock_modrinth,
            patch("mcward._assets._download_file") as mock_download,
            patch("mcward._assets._build_ward") as mock_build,
        ):
            mock_fabric.return_value = "https://fabric.example.com/server.jar"
            mock_modrinth.return_value = "https://modrinth.example.com/mod.jar"

            await download(directory, version)

            # Should download server and fabric-api
            assert mock_download.call_count == 2

            # Should build ward instead of downloading
            mock_build.assert_called_once()
            assert mock_modrinth.call_count == 1  # Only fabric-api, not ward

    @pytest.mark.anyio
    async def test_download_concurrent_execution(self, tmp_path: Path) -> None:
        """Test that downloads are executed concurrently."""
        version = Version("26.1.2", 26, 1, 2, 0)
        directory = tmp_path / "env"
        directory.mkdir()

        # Track order of execution
        execution_order = []

        async def mock_download_with_delay(*args):
            execution_order.append("download_start")
            await asyncio.sleep(0.01)
            execution_order.append("download_end")

        # Use AsyncMock for async functions to avoid coroutine warnings
        mock_fabric = AsyncMock(return_value="url1")
        mock_modrinth = AsyncMock(return_value="url2")

        with (
            patch("mcward._assets._resolve_fabric_url", mock_fabric),
            patch("mcward._assets._resolve_modrinth_url", mock_modrinth),
            patch("mcward._assets._download_file", side_effect=mock_download_with_delay),
        ):
            await download(directory, version)

            # All downloads should start before any finish (concurrent)
            # With 3 downloads, we should see multiple "start" before "end"
            start_count_before_first_end = 0
            for event in execution_order:
                if event == "download_start":
                    start_count_before_first_end += 1
                elif event == "download_end":
                    break

            # Should have started multiple downloads before first one finishes
            assert start_count_before_first_end > 1
