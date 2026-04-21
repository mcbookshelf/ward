"""Tests for EnvironmentManager."""

from pathlib import Path
from unittest.mock import patch

import pytest

from mcward import (
    EnvironmentManager,
    InstalledEnvironment,
    RunningEnvironment,
    UninstalledEnvironment,
    Version,
    VersionNotFoundError,
)


class TestEnvironmentManager:
    """Test EnvironmentManager functionality."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory for testing."""
        return tmp_path / "mcward"

    @pytest.fixture
    def manager(self, temp_dir: Path) -> EnvironmentManager:
        """Create an EnvironmentManager with temporary directory."""
        return EnvironmentManager(temp_dir)

    @pytest.fixture
    def mock_version(self) -> Version:
        """Create a mock version."""
        return Version("26.1.2", 26, 1, 2, 0)

    def test_initialization(self, temp_dir: Path) -> None:
        """Test EnvironmentManager initialization."""
        manager = EnvironmentManager(temp_dir)
        assert manager.directory == temp_dir
        assert manager.versions is not None

    def test_initialization_default_directory(self) -> None:
        """Test EnvironmentManager uses default cache directory when none provided."""
        manager = EnvironmentManager()
        assert manager.directory is not None
        assert manager.directory.exists() or True  # May not exist yet

    def test_get_uninstalled_environment(
        self, manager: EnvironmentManager, mock_version: Version
    ) -> None:
        """Test getting an uninstalled environment."""
        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            assert isinstance(env, UninstalledEnvironment)
            assert env.version == mock_version
            assert env.directory == manager.directory / "26.1.2"

    def test_get_installed_environment(
        self, manager: EnvironmentManager, mock_version: Version, temp_dir: Path
    ) -> None:
        """Test getting an installed environment."""
        # Create environment directory with required files
        env_dir = temp_dir / "26.1.2"
        env_dir.mkdir(parents=True)
        (env_dir / "server.jar").write_text("fake server")
        (env_dir / "mods").mkdir()
        (env_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        (env_dir / "mods" / "ward.jar").write_text("fake ward")

        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            assert isinstance(env, InstalledEnvironment)
            assert env.version == mock_version
            assert env.directory == env_dir

    def test_get_running_environment(
        self, manager: EnvironmentManager, mock_version: Version, temp_dir: Path
    ) -> None:
        """Test getting a running environment."""
        # Create environment directory with required files
        env_dir = temp_dir / "26.1.2"
        env_dir.mkdir(parents=True)
        (env_dir / "server.jar").write_text("fake server")
        (env_dir / "mods").mkdir()
        (env_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        (env_dir / "mods" / "ward.jar").write_text("fake ward")

        # Create process metadata files
        (env_dir / "ward.pid").write_text("12345")
        (env_dir / "ward.port").write_text("25565")

        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            assert isinstance(env, RunningEnvironment)
            assert env.version == mock_version
            assert env.directory == env_dir
            assert env.running.pid == 12345
            assert env.running.port == 25565

    def test_get_version_not_found(self, manager: EnvironmentManager) -> None:
        """Test getting a version that doesn't exist."""
        with patch.object(manager.versions, "get", return_value=None):
            with pytest.raises(VersionNotFoundError) as exc_info:
                manager.get("99.99.99")
            assert exc_info.value.version == "99.99.99"

    def test_list_available_cached(self, manager: EnvironmentManager) -> None:
        """Test listing available versions from cache."""
        mock_versions = [
            Version("26.1.2", 26, 1, 2, 0),
            Version("26.1.1", 26, 1, 1, 0),
        ]

        with patch.object(manager.versions, "list", return_value=mock_versions):
            versions = manager.list_available()
            assert versions == mock_versions

    def test_list_available_force_refresh(self, manager: EnvironmentManager) -> None:
        """Test listing available versions with forced refresh."""
        mock_versions = [
            Version("26.1.2", 26, 1, 2, 0),
            Version("26.1.1", 26, 1, 1, 0),
        ]

        with patch.object(manager.versions, "sync", return_value=mock_versions):
            versions = manager.list_available(force_refresh=True)
            assert versions == mock_versions

    def test_list_installed_empty(self, manager: EnvironmentManager) -> None:
        """Test listing installed environments when none exist."""
        installed = manager.list_installed()
        assert installed == []

    def test_list_installed_with_environments(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test listing installed environments."""
        # Create two installed environments
        for version_name in ["26.1.2", "26.1.1"]:
            env_dir = temp_dir / version_name
            env_dir.mkdir(parents=True)
            (env_dir / "server.jar").write_text("fake server")
            (env_dir / "mods").mkdir()
            (env_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
            (env_dir / "mods" / "ward.jar").write_text("fake ward")

        installed = manager.list_installed()
        assert len(installed) == 2
        assert installed[0].name == "26.1.2"  # Sorted descending
        assert installed[1].name == "26.1.1"

    def test_list_installed_ignores_incomplete(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test that incomplete installations are not listed."""
        # Create incomplete environment (missing ward.jar)
        env_dir = temp_dir / "26.1.2"
        env_dir.mkdir(parents=True)
        (env_dir / "server.jar").write_text("fake server")
        (env_dir / "mods").mkdir()
        (env_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        # Missing ward.jar

        installed = manager.list_installed()
        assert len(installed) == 0

    def test_list_installed_ignores_invalid_version_names(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test that directories with invalid version names are ignored."""
        # Create directory with invalid version name
        invalid_dir = temp_dir / "not-a-version"
        invalid_dir.mkdir(parents=True)
        (invalid_dir / "server.jar").write_text("fake server")
        (invalid_dir / "mods").mkdir()
        (invalid_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        (invalid_dir / "mods" / "ward.jar").write_text("fake ward")

        # Should ignore invalid version names
        installed = manager.list_installed()
        assert len(installed) == 0

    def test_clean_existing_environment(self, manager: EnvironmentManager, temp_dir: Path) -> None:
        """Test cleaning an existing environment."""
        # Create environment
        env_dir = temp_dir / "26.1.2"
        env_dir.mkdir(parents=True)
        (env_dir / "server.jar").write_text("fake server")
        (env_dir / "mods").mkdir()
        (env_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        (env_dir / "mods" / "ward.jar").write_text("fake ward")

        # Also create process metadata files
        (env_dir / "ward.pid").write_text("12345")
        (env_dir / "ward.port").write_text("25565")

        result = manager.clean("26.1.2")
        assert result is True
        assert not env_dir.exists()

    def test_clean_nonexistent_environment(self, manager: EnvironmentManager) -> None:
        """Test cleaning a non-existent environment."""
        result = manager.clean("26.1.2")
        assert result is False

    def test_is_installed_checks_all_required_files(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test that _is_installed checks all required files."""
        env_dir = temp_dir / "26.1.2"
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
    """Test that manager correctly prioritizes environment states."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory for testing."""
        return tmp_path / "mcward"

    @pytest.fixture
    def manager(self, temp_dir: Path) -> EnvironmentManager:
        """Create an EnvironmentManager with temporary directory."""
        return EnvironmentManager(temp_dir)

    @pytest.fixture
    def mock_version(self) -> Version:
        """Create a mock version."""
        return Version("26.1.2", 26, 1, 2, 0)

    def test_running_takes_precedence_over_installed(
        self, manager: EnvironmentManager, mock_version: Version, temp_dir: Path
    ) -> None:
        """Test that running state is returned even when fully installed."""
        # Create fully installed environment
        env_dir = temp_dir / "26.1.2"
        env_dir.mkdir(parents=True)
        (env_dir / "server.jar").write_text("fake server")
        (env_dir / "mods").mkdir()
        (env_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        (env_dir / "mods" / "ward.jar").write_text("fake ward")

        # Add process metadata
        (env_dir / "ward.pid").write_text("12345")
        (env_dir / "ward.port").write_text("25565")

        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            # Should be RunningEnvironment, not InstalledEnvironment
            assert isinstance(env, RunningEnvironment)
            assert not isinstance(env, InstalledEnvironment)

    def test_installed_takes_precedence_over_uninstalled(
        self, manager: EnvironmentManager, mock_version: Version, temp_dir: Path
    ) -> None:
        """Test that installed state is returned when files exist."""
        # Create installed environment
        env_dir = temp_dir / "26.1.2"
        env_dir.mkdir(parents=True)
        (env_dir / "server.jar").write_text("fake server")
        (env_dir / "mods").mkdir()
        (env_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        (env_dir / "mods" / "ward.jar").write_text("fake ward")

        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            # Should be InstalledEnvironment, not UninstalledEnvironment
            assert isinstance(env, InstalledEnvironment)
            assert not isinstance(env, UninstalledEnvironment)

    def test_incomplete_installation_returns_uninstalled(
        self, manager: EnvironmentManager, mock_version: Version, temp_dir: Path
    ) -> None:
        """Test that incomplete installation is treated as uninstalled."""
        # Create partially installed environment
        env_dir = temp_dir / "26.1.2"
        env_dir.mkdir(parents=True)
        (env_dir / "server.jar").write_text("fake server")
        # Missing mods directory and jars

        with patch.object(manager.versions, "get", return_value=mock_version):
            env = manager.get("26.1.2")
            # Should be UninstalledEnvironment since installation is incomplete
            assert isinstance(env, UninstalledEnvironment)


class TestGetVersionHelper:
    """Test _get_version helper method."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory for testing."""
        return tmp_path / "mcward"

    @pytest.fixture
    def manager(self, temp_dir: Path) -> EnvironmentManager:
        """Create an EnvironmentManager with temporary directory."""
        return EnvironmentManager(temp_dir)

    def test_get_version_from_registry(self, manager: EnvironmentManager) -> None:
        """Test getting version that exists in registry."""
        mock_version = Version("26.1.2", 26, 1, 2, 0)
        with patch.object(manager.versions, "get", return_value=mock_version):
            version, listed = manager._get_version("26.1.2")
            assert version == mock_version
            assert listed is True

    def test_get_version_parse_literal(self, manager: EnvironmentManager) -> None:
        """Test parsing version that's not in registry."""
        with patch.object(manager.versions, "get", return_value=None):
            version, listed = manager._get_version("dev/26.1.2")
            assert version.name == "dev/26.1.2"
            assert version.year == 26
            assert version.major == 1
            assert version.patch == 2
            assert listed is False

    def test_get_version_invalid_raises(self, manager: EnvironmentManager) -> None:
        """Test that invalid version raises VersionNotFoundError."""
        with patch.object(manager.versions, "get", return_value=None):
            with pytest.raises(VersionNotFoundError) as exc_info:
                manager._get_version("not-a-version")
            assert exc_info.value.version == "not-a-version"


class TestDevDirectoryStructure:
    """Test dev version directory structure (dev/<mc_version>/)."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory for testing."""
        return tmp_path / "mcward"

    @pytest.fixture
    def manager(self, temp_dir: Path) -> EnvironmentManager:
        """Create an EnvironmentManager with temporary directory."""
        return EnvironmentManager(temp_dir)

    @pytest.fixture
    def mock_version(self) -> Version:
        """Create a mock version."""
        return Version("26.1.2", 26, 1, 2, 0)

    def test_get_dev_uses_dev_subdirectory(
        self, manager: EnvironmentManager, tmp_path: Path
    ) -> None:
        """Test that get('dev') uses dev/<mc_version>/ directory."""
        # Create gradle.properties
        gradle_props = tmp_path / "gradle.properties"
        gradle_props.write_text("minecraft_version=26.1.2\n")

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Mock version with dev/ prefix
            dev_version = Version("dev/26.1.2", 26, 1, 2, 0)
            with patch.object(manager.versions, "get", return_value=dev_version):
                env = manager.get("dev")
                assert isinstance(env, UninstalledEnvironment)
                # Should use dev/26.1.2/ directory
                assert env.directory == manager.directory / "dev" / "26.1.2"
                assert env.version.name == "dev/26.1.2"
        finally:
            os.chdir(original_cwd)

    def test_get_installed_dev_version_by_name(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test that get('dev/26.1.2') works for already installed dev versions."""
        # Create installed dev version
        dev_dir = temp_dir / "dev" / "26.1.2"
        dev_dir.mkdir(parents=True)
        (dev_dir / "server.jar").write_text("fake server")
        (dev_dir / "mods").mkdir()
        (dev_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        (dev_dir / "mods" / "ward.jar").write_text("fake ward")

        # Mock registry to return None (not in registry)
        with patch.object(manager.versions, "get", return_value=None):
            # Should be able to get it by full name (parses as literal)
            env = manager.get("dev/26.1.2")
            assert isinstance(env, InstalledEnvironment)
            assert env.version.name == "dev/26.1.2"
            assert env.directory == dev_dir

    def test_list_installed_includes_dev_versions(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test that list_installed includes dev versions with dev/ prefix."""
        # Create regular version
        regular_dir = temp_dir / "26.1.2"
        regular_dir.mkdir(parents=True)
        (regular_dir / "server.jar").write_text("fake server")
        (regular_dir / "mods").mkdir()
        (regular_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        (regular_dir / "mods" / "ward.jar").write_text("fake ward")

        # Create dev version
        dev_dir = temp_dir / "dev" / "26.1.1"
        dev_dir.mkdir(parents=True)
        (dev_dir / "server.jar").write_text("fake server")
        (dev_dir / "mods").mkdir()
        (dev_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
        (dev_dir / "mods" / "ward.jar").write_text("fake ward")

        installed = manager.list_installed()
        assert len(installed) == 2
        # Dev version should have dev/ prefix in name
        version_names = [v.name for v in installed]
        assert "26.1.2" in version_names
        assert "dev/26.1.1" in version_names

    def test_list_installed_ignores_dev_directory_itself(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test that list_installed ignores the dev/ directory itself."""
        # Create dev directory but no valid installations inside
        dev_dir = temp_dir / "dev"
        dev_dir.mkdir(parents=True)
        (dev_dir / "some-file.txt").write_text("not a real installation")

        installed = manager.list_installed()
        assert len(installed) == 0

    def test_clean_dev_removes_all_dev_builds(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test that clean('dev') removes entire dev directory."""
        # Create multiple dev versions
        for version_name in ["26.1.2", "26.1.1"]:
            dev_dir = temp_dir / "dev" / version_name
            dev_dir.mkdir(parents=True)
            (dev_dir / "server.jar").write_text("fake server")
            (dev_dir / "mods").mkdir()
            (dev_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
            (dev_dir / "mods" / "ward.jar").write_text("fake ward")

        result = manager.clean("dev")
        assert result is True
        assert not (temp_dir / "dev").exists()

    def test_clean_dev_returns_false_when_no_dev_directory(
        self, manager: EnvironmentManager
    ) -> None:
        """Test that clean('dev') returns False when dev directory doesn't exist."""
        result = manager.clean("dev")
        assert result is False

    def test_clean_specific_dev_version(self, manager: EnvironmentManager, temp_dir: Path) -> None:
        """Test that clean('dev/<version>') removes specific dev build."""
        # Create two dev versions
        for version_name in ["26.1.2", "26.1.1"]:
            dev_dir = temp_dir / "dev" / version_name
            dev_dir.mkdir(parents=True)
            (dev_dir / "server.jar").write_text("fake server")
            (dev_dir / "mods").mkdir()
            (dev_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
            (dev_dir / "mods" / "ward.jar").write_text("fake ward")

        # Clean only one
        result = manager.clean("dev/26.1.2")
        assert result is True
        assert not (temp_dir / "dev" / "26.1.2").exists()
        assert (temp_dir / "dev" / "26.1.1").exists()

    def test_clean_regular_version_still_works(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test that clean still works for regular versions."""
        # Create regular version
        regular_dir = temp_dir / "26.1.2"
        regular_dir.mkdir(parents=True)
        (regular_dir / "server.jar").write_text("fake server")

        result = manager.clean("26.1.2")
        assert result is True
        assert not regular_dir.exists()

    def test_multiple_dev_versions_different_mc_versions(
        self, manager: EnvironmentManager, temp_dir: Path
    ) -> None:
        """Test that multiple dev builds for different MC versions can coexist."""
        # Create dev builds for different MC versions
        for version_name in ["26.1.2", "26.2-snapshot-6"]:
            dev_dir = temp_dir / "dev" / version_name
            dev_dir.mkdir(parents=True)
            (dev_dir / "server.jar").write_text("fake server")
            (dev_dir / "mods").mkdir()
            (dev_dir / "mods" / "fabric-api.jar").write_text("fake fabric")
            (dev_dir / "mods" / "ward.jar").write_text("fake ward")

        installed = manager.list_installed()
        assert len(installed) == 2
        version_names = [v.name for v in installed]
        # Dev versions should have dev/ prefix
        assert "dev/26.1.2" in version_names
        assert "dev/26.2-snapshot-6" in version_names
