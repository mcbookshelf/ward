"""Shared fixtures for mcward-core tests."""

from collections.abc import Callable
from pathlib import Path

import pytest

from mcward import EnvironmentManager, Version


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Directory the manager uses as its environment root."""
    return tmp_path / "mcward"


@pytest.fixture
def manager(temp_dir: Path) -> EnvironmentManager:
    """An EnvironmentManager rooted in a temporary directory."""
    return EnvironmentManager(temp_dir)


@pytest.fixture
def mock_version() -> Version:
    """A plain release version."""
    return Version.parse("26.1.2")


@pytest.fixture
def install_environment() -> Callable[[Path], Path]:
    """Factory creating the files that make a directory count as installed."""

    def _install(directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "server.jar").write_text("fake server")
        (directory / "mods").mkdir(exist_ok=True)
        (directory / "mods" / "fabric-api.jar").write_text("fake fabric")
        (directory / "mods" / "ward.jar").write_text("fake ward")
        return directory

    return _install
