"""Tests for EnvironmentManager."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock, patch

import psutil
import pytest

from mcward import (
    EnvironmentManager,
    InstalledEnvironment,
    RunningEnvironment,
    UninstalledEnvironment,
    Version,
    VersionNotFoundError,
)


def write_process_files(directory: Path) -> None:
    """Create the pid/port files that mark an environment as running."""
    (directory / "ward.pid").write_text("12345")
    (directory / "ward.port").write_text("25565")


class TestEnvironmentManager:
    def test_initialization(self, temp_dir: Path) -> None:
        manager = EnvironmentManager(temp_dir)
        assert manager.directory == temp_dir
        assert manager.versions is not None

    def test_initialization_default_directory(self) -> None:
        manager = EnvironmentManager()
        assert manager.directory is not None

    def test_get_uninstalled_environment(
        self, manager: EnvironmentManager, mock_version: Version
    ) -> None:
        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            assert isinstance(env, UninstalledEnvironment)
            assert env.version == mock_version
            assert env.directory == manager.environments / "26.1.2"

    def test_get_installed_environment(
        self,
        manager: EnvironmentManager,
        mock_version: Version,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        env_dir = install_environment(temp_dir / "environments" / "26.1.2")

        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            assert isinstance(env, InstalledEnvironment)
            assert env.version == mock_version
            assert env.directory == env_dir

    def test_get_running_environment(
        self,
        manager: EnvironmentManager,
        mock_version: Version,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        env_dir = install_environment(temp_dir / "environments" / "26.1.2")
        write_process_files(env_dir)

        with (
            patch.object(manager.versions, "get", return_value=mock_version),
            patch("mcward._manager.is_ward_process", return_value=True),
        ):
            env = manager.get("26.1.2")
            assert isinstance(env, RunningEnvironment)
            assert env.version == mock_version
            assert env.directory == env_dir
            assert env.process.pid == 12345
            assert env.process.port == 25565

    def test_get_stale_running_environment(
        self,
        manager: EnvironmentManager,
        mock_version: Version,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        """Leftover pid/port files from a dead process fall back to installed."""
        env_dir = install_environment(temp_dir / "environments" / "26.1.2")
        write_process_files(env_dir)

        with (
            patch.object(manager.versions, "get", return_value=mock_version),
            patch("mcward._manager.is_ward_process", return_value=False),
        ):
            env = manager.get("26.1.2")
            assert isinstance(env, InstalledEnvironment)

    def test_get_version_not_found(self, manager: EnvironmentManager) -> None:
        with patch.object(manager.versions, "get", return_value=None):
            with pytest.raises(VersionNotFoundError) as exc_info:
                manager.get("99.99.99")
            assert exc_info.value.version == "99.99.99"

    def test_list_available_cached(self, manager: EnvironmentManager) -> None:
        mock_versions = [
            Version.parse("26.1.2"),
            Version.parse("26.1.1"),
        ]

        with patch.object(manager.versions, "list", return_value=mock_versions):
            versions = manager.list_available()
            assert versions == mock_versions

    def test_list_installed_empty(self, manager: EnvironmentManager) -> None:
        assert manager.list_installed() == []

    def test_list_installed_with_environments(
        self,
        manager: EnvironmentManager,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        install_environment(temp_dir / "environments" / "26.1.2")
        install_environment(temp_dir / "environments" / "26.1.1")

        installed = manager.list_installed()
        assert [v.name for v in installed] == ["26.1.2", "26.1.1"]  # Sorted descending

    def test_list_installed_ignores_incomplete(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        env_dir = temp_dir / "environments" / "26.1.2"
        env_dir.mkdir(parents=True)
        (env_dir / "server.jar").write_text("fake server")
        # Missing mods jars

        assert manager.list_installed() == []

    def test_list_installed_ignores_invalid_version_names(
        self,
        manager: EnvironmentManager,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        install_environment(temp_dir / "not-a-version")

        assert manager.list_installed() == []

    def test_uninstall_removes_environment(
        self,
        manager: EnvironmentManager,
        mock_version: Version,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        env_dir = install_environment(temp_dir / "environments" / "26.1.2")

        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            assert isinstance(env, InstalledEnvironment)
            env.uninstall()

        assert not env_dir.exists()

    def test_is_installed_checks_all_required_files(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        env_dir = temp_dir / "environments" / "26.1.2"
        env_dir.mkdir(parents=True)

        # Not installed - no files
        assert manager._is_installed(env_dir) is False

        # Not installed - only server.jar
        (env_dir / "server.jar").write_text("fake server")
        assert manager._is_installed(env_dir) is False

        # Not installed - server.jar + fabric-api.jar
        (env_dir / "mods").mkdir()
        (env_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        assert manager._is_installed(env_dir) is False

        # Installed - all files present
        (env_dir / "mods" / "ward.jar").write_text("fake ward")
        assert manager._is_installed(env_dir) is True


class TestEnvironmentStatePriority:
    def test_running_takes_precedence_over_installed(
        self,
        manager: EnvironmentManager,
        mock_version: Version,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        env_dir = install_environment(temp_dir / "environments" / "26.1.2")
        write_process_files(env_dir)

        with (
            patch.object(manager.versions, "get", return_value=mock_version),
            patch("mcward._manager.is_ward_process", return_value=True),
        ):
            env = manager.get("26.1.2")
            assert isinstance(env, RunningEnvironment)
            assert not isinstance(env, InstalledEnvironment)

    def test_installed_takes_precedence_over_uninstalled(
        self,
        manager: EnvironmentManager,
        mock_version: Version,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        install_environment(temp_dir / "environments" / "26.1.2")

        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            assert isinstance(env, InstalledEnvironment)
            assert not isinstance(env, UninstalledEnvironment)

    def test_incomplete_installation_returns_uninstalled(
        self, manager: EnvironmentManager, mock_version: Version, temp_dir: Path
    ) -> None:
        env_dir = temp_dir / "environments" / "26.1.2"
        env_dir.mkdir(parents=True)
        (env_dir / "server.jar").write_text("fake server")
        # Missing mods directory and jars

        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            assert isinstance(env, UninstalledEnvironment)


class TestGetVersionHelper:
    def test_get_version_from_registry(
        self, manager: EnvironmentManager, mock_version: Version
    ) -> None:
        with patch.object(manager.versions, "get", return_value=mock_version):
            version, listed = manager._get_version("26.1.2")
            assert version == mock_version
            assert listed is True

    def test_get_version_parse_literal(self, manager: EnvironmentManager) -> None:
        with patch.object(manager.versions, "get", return_value=None):
            version, listed = manager._get_version("dev/26.1.2")
            assert version.name == "dev/26.1.2"
            assert version.year == 26
            assert version.major == 1
            assert version.patch == 2
            assert listed is False

    def test_get_version_invalid_raises(self, manager: EnvironmentManager) -> None:
        with patch.object(manager.versions, "get", return_value=None):
            with pytest.raises(VersionNotFoundError) as exc_info:
                manager._get_version("not-a-version")
            assert exc_info.value.version == "not-a-version"


class TestDevDirectoryStructure:
    """Dev environments live under dev/<mc_version>/."""

    def test_get_dev_uses_dev_subdirectory(
        self, manager: EnvironmentManager, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "gradle.properties").write_text("minecraft_version=26.1.2\n")
        monkeypatch.chdir(tmp_path)

        dev_version = Version.parse("dev/26.1.2")
        with patch.object(manager.versions, "get", return_value=dev_version):
            env = manager.get("dev")
            assert isinstance(env, UninstalledEnvironment)
            assert env.directory == manager.environments / "dev" / "26.1.2"
            assert env.version.name == "dev/26.1.2"

    def test_get_installed_dev_version_by_name(
        self,
        manager: EnvironmentManager,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        dev_dir = install_environment(temp_dir / "environments" / "dev" / "26.1.2")

        # Not in the registry: resolved by parsing the literal name
        with patch.object(manager.versions, "get", return_value=None):
            env = manager.get("dev/26.1.2")
            assert isinstance(env, InstalledEnvironment)
            assert env.version.name == "dev/26.1.2"
            assert env.directory == dev_dir

    def test_list_installed_includes_dev_versions(
        self,
        manager: EnvironmentManager,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        install_environment(temp_dir / "environments" / "26.1.2")
        install_environment(temp_dir / "environments" / "dev" / "26.1.1")

        version_names = [v.name for v in manager.list_installed()]
        assert "26.1.2" in version_names
        assert "dev/26.1.1" in version_names

    def test_list_installed_ignores_dev_directory_itself(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        dev_dir = temp_dir / "environments" / "dev"
        dev_dir.mkdir(parents=True)
        (dev_dir / "some-file.txt").write_text("not a real installation")

        assert manager.list_installed() == []

    def test_uninstall_specific_dev_version(
        self,
        manager: EnvironmentManager,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        """Uninstalling one dev build leaves the others untouched."""
        install_environment(temp_dir / "environments" / "dev" / "26.1.2")
        install_environment(temp_dir / "environments" / "dev" / "26.1.1")

        with patch.object(manager.versions, "get", return_value=None):
            env = manager.get("dev/26.1.2")
            assert isinstance(env, InstalledEnvironment)
            env.uninstall()

        assert not (temp_dir / "environments" / "dev" / "26.1.2").exists()
        assert (temp_dir / "environments" / "dev" / "26.1.1").exists()

    def test_multiple_dev_versions_different_mc_versions(
        self,
        manager: EnvironmentManager,
        temp_dir: Path,
        install_environment: Callable[[Path], Path],
    ) -> None:
        install_environment(temp_dir / "environments" / "dev" / "26.1.2")
        install_environment(temp_dir / "environments" / "dev" / "26.2-snapshot-6")

        version_names = [v.name for v in manager.list_installed()]
        assert "dev/26.1.2" in version_names
        assert "dev/26.2-snapshot-6" in version_names


class TestIsRunning:
    """Test stale running-state detection."""

    @pytest.fixture
    def directory(self, temp_dir: Path) -> Path:
        directory = temp_dir / "environments" / "26.1.2"
        directory.mkdir(parents=True)
        write_process_files(directory)
        return directory

    def test_alive_ward_process(self, manager: EnvironmentManager, directory: Path) -> None:
        """A live Ward server counts as running and keeps its files."""
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.cmdline.return_value = ["java", "-jar", "server.jar", "nogui"]

        with patch("psutil.Process", return_value=mock_psutil):
            assert manager._is_running(directory)

        assert (directory / "ward.pid").exists()
        assert (directory / "ward.port").exists()

    def test_dead_process_cleans_stale_files(
        self, manager: EnvironmentManager, directory: Path
    ) -> None:
        """A dead pid is not running and its leftover files are removed."""
        with patch("psutil.Process", side_effect=psutil.NoSuchProcess(12345)):
            assert not manager._is_running(directory)

        assert not (directory / "ward.pid").exists()
        assert not (directory / "ward.port").exists()

    def test_recycled_pid_cleans_stale_files(
        self, manager: EnvironmentManager, directory: Path
    ) -> None:
        """An unrelated process reusing the pid counts as not running."""
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.cmdline.return_value = ["python", "unrelated.py"]

        with patch("psutil.Process", return_value=mock_psutil):
            assert not manager._is_running(directory)

        assert not (directory / "ward.pid").exists()

    def test_missing_files(self, manager: EnvironmentManager, temp_dir: Path) -> None:
        """A directory without pid/port files is not running."""
        assert not manager._is_running(temp_dir)
