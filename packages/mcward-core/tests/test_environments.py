"""Tests for environment state transitions and datapack deployment."""

import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcward import (
    DeployError,
    InstalledEnvironment,
    InstallError,
    RunningEnvironment,
    UninstalledEnvironment,
    Version,
)
from mcward._daemon import RunningProcess

V1 = Version.parse("26.1.2")


def make_running(directory: Path) -> RunningEnvironment:
    return RunningEnvironment(directory, V1, RunningProcess(directory, 12345, 25565))


class TestStateTransitions:
    """Test the Uninstalled -> Installed -> Running state machine."""

    def test_install_transitions_to_installed(self, tmp_path: Path) -> None:
        env = UninstalledEnvironment(tmp_path, V1)

        with patch("mcward._assets.install") as mock_download:
            installed = env.install()

        mock_download.assert_called_once_with(tmp_path, V1)
        assert isinstance(installed, InstalledEnvironment)
        assert (installed.directory, installed.version) == (tmp_path, V1)

    def test_start_transitions_to_running(self, tmp_path: Path) -> None:
        env = InstalledEnvironment(tmp_path, V1)
        process = RunningProcess(tmp_path, 12345, 25565)

        with patch("mcward._daemon.start", return_value=process) as mock_start:
            running = env.start()

        mock_start.assert_called_once_with(tmp_path)
        assert isinstance(running, RunningEnvironment)
        assert running.process is process

    def test_stop_transitions_to_installed(self, tmp_path: Path) -> None:
        env = make_running(tmp_path)

        with patch("mcward._daemon.stop") as mock_stop:
            installed = env.stop()

        mock_stop.assert_called_once_with(env.process)
        assert isinstance(installed, InstalledEnvironment)

    def test_uninstall_removes_directory(self, tmp_path: Path) -> None:
        directory = tmp_path / "env"
        directory.mkdir()
        (directory / "server.jar").write_text("fake")

        env = InstalledEnvironment(directory, V1)
        uninstalled = env.uninstall()

        assert isinstance(uninstalled, UninstalledEnvironment)
        assert not directory.exists()

    def test_uninstall_of_missing_directory_is_fine(self, tmp_path: Path) -> None:
        env = InstalledEnvironment(tmp_path / "absent", V1)
        assert isinstance(env.uninstall(), UninstalledEnvironment)

    def test_uninstall_failure_raises(self, tmp_path: Path) -> None:
        """A directory that cannot be removed (locked jar) is a hard error."""
        directory = tmp_path / "env"
        directory.mkdir()

        env = InstalledEnvironment(directory, V1)
        with (
            patch("shutil.rmtree", side_effect=OSError("locked by JVM")),
            pytest.raises(InstallError, match="locked by JVM"),
        ):
            env.uninstall()


class TestDatapackDeployment:
    """Test how RunningEnvironment.test ships datapacks into the server world."""

    def test_deploys_packs_and_replaces_previous_run(self, tmp_path: Path) -> None:
        """Old datapacks are wiped and the new ones deployed as zips."""
        env_dir = tmp_path / "env"
        deployed = env_dir / "world" / "datapacks"
        (deployed / "stale_pack").mkdir(parents=True)

        pack = tmp_path / "my_pack"
        (pack / "data").mkdir(parents=True)
        (pack / "pack.mcmeta").write_text("{}")
        (pack / "data" / "function.mcfunction").write_text("say hi")

        with patch("mcward._daemon.wait_idle"), patch("mcward._daemon.stream_tests") as mock_stream:
            make_running(env_dir).test([pack], selector="my:*")

        mock_stream.assert_called_once_with(
            ("127.0.0.1", 25565), "my:*", coverage=False, timeout=None
        )
        assert not (deployed / "stale_pack").exists()
        with zipfile.ZipFile(deployed / "my_pack.zip") as archive:
            assert sorted(archive.namelist()) == ["data/function.mcfunction", "pack.mcmeta"]

    def test_excludes_development_files(self, tmp_path: Path) -> None:
        """Hidden and tooling directories never reach the server."""
        env_dir = tmp_path / "env"

        pack = tmp_path / "my_pack"
        (pack / ".git").mkdir(parents=True)
        (pack / ".git" / "HEAD").write_text("ref")
        (pack / "__pycache__").mkdir()
        (pack / "__pycache__" / "junk.pyc").write_text("")
        (pack / "pack.mcmeta").write_text("{}")

        with patch("mcward._daemon.wait_idle"), patch("mcward._daemon.stream_tests"):
            make_running(env_dir).test([pack])

        deployed = env_dir / "world" / "datapacks" / "my_pack.zip"
        with zipfile.ZipFile(deployed) as archive:
            assert archive.namelist() == ["pack.mcmeta"]

    def test_works_without_previous_datapacks_directory(self, tmp_path: Path) -> None:
        """The very first run has no datapacks directory to clear."""
        env_dir = tmp_path / "env"
        pack = tmp_path / "my_pack"
        pack.mkdir()
        (pack / "pack.mcmeta").write_text("{}")

        with patch("mcward._daemon.wait_idle"), patch("mcward._daemon.stream_tests"):
            make_running(env_dir).test([pack])

        assert (env_dir / "world" / "datapacks" / "my_pack.zip").is_file()

    def test_duplicate_pack_names_are_disambiguated(self, tmp_path: Path) -> None:
        """Packs sharing a directory name deploy side by side with a suffix."""
        first = tmp_path / "a" / "my_pack"
        second = tmp_path / "b" / "my_pack"
        third = tmp_path / "c" / "my_pack-2"
        for pack in (first, second, third):
            pack.mkdir(parents=True)
            (pack / "pack.mcmeta").write_text(pack.parent.name)

        env_dir = tmp_path / "env"
        with patch("mcward._daemon.wait_idle"), patch("mcward._daemon.stream_tests"):
            make_running(env_dir).test([first, second, third])

        def mcmeta(name: str) -> str:
            deployed = env_dir / "world" / "datapacks" / name
            with zipfile.ZipFile(deployed) as archive:
                return archive.read("pack.mcmeta").decode()

        # The suffix never displaces the real my_pack-2's own name
        assert mcmeta("my_pack.zip") == "a"
        assert mcmeta("my_pack-3.zip") == "b"
        assert mcmeta("my_pack-2.zip") == "c"

    def test_deploys_zipped_packs_as_files(self, tmp_path: Path) -> None:
        """A zipped datapack is copied as a file the server can read directly."""
        env_dir = tmp_path / "env"
        pack = tmp_path / "my_pack.zip"
        pack.write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # empty zip

        with patch("mcward._daemon.wait_idle"), patch("mcward._daemon.stream_tests"):
            make_running(env_dir).test([pack])

        deployed = env_dir / "world" / "datapacks" / "my_pack.zip"
        assert deployed.is_file()
        assert deployed.read_bytes() == pack.read_bytes()

    def test_duplicate_zip_names_keep_their_extension(self, tmp_path: Path) -> None:
        """The disambiguation suffix goes before .zip, or the server skips the pack."""
        first = tmp_path / "a" / "my_pack.zip"
        second = tmp_path / "b" / "my_pack.zip"
        for pack in (first, second):
            pack.parent.mkdir(parents=True)
            pack.write_bytes(b"PK\x05\x06" + b"\x00" * 18)

        env_dir = tmp_path / "env"
        with patch("mcward._daemon.wait_idle"), patch("mcward._daemon.stream_tests"):
            make_running(env_dir).test([first, second])

        deployed = env_dir / "world" / "datapacks"
        assert (deployed / "my_pack.zip").is_file()
        assert (deployed / "my_pack-2.zip").is_file()

    def test_undeployable_previous_run_raises(self, tmp_path: Path) -> None:
        """A previous deployment that cannot be cleared must not run stale packs."""
        env_dir = tmp_path / "env"
        (env_dir / "world" / "datapacks" / "stale_pack").mkdir(parents=True)
        pack = tmp_path / "my_pack"
        pack.mkdir()

        with (
            patch("mcward._daemon.wait_idle"),
            patch("mcward._environments.time.sleep"),
            patch("shutil.rmtree", side_effect=OSError("locked")),
            pytest.raises(DeployError, match="copy"),
        ):
            make_running(env_dir).test([pack])

    def test_deploy_retries_through_transient_locks(self, tmp_path: Path) -> None:
        """A briefly locked file (server shutdown, antivirus) does not fail the run."""
        env_dir = tmp_path / "env"
        (env_dir / "world" / "datapacks" / "stale_pack").mkdir(parents=True)
        pack = tmp_path / "my_pack"
        pack.mkdir()
        (pack / "pack.mcmeta").write_text("{}")

        locked = iter([OSError("locked"), OSError("locked"), None])

        def rmtree(path, **kwargs):
            if (error := next(locked)) is not None:
                raise error
            for child in sorted(Path(path).rglob("*"), reverse=True):
                if child.is_dir():
                    child.rmdir()
                else:
                    child.unlink()
            Path(path).rmdir()

        with (
            patch("mcward._daemon.wait_idle"),
            patch("mcward._environments.time.sleep"),
            patch("mcward._daemon.stream_tests"),
            patch("mcward._environments.shutil.rmtree", side_effect=rmtree),
        ):
            make_running(env_dir).test([pack])

        assert (env_dir / "world" / "datapacks" / "my_pack.zip").is_file()
