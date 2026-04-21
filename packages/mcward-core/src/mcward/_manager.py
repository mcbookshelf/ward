"""Environment management for Ward."""

from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from platformdirs import user_cache_path

from ._constants import PID_FILE, PORT_FILE
from ._environments import InstalledEnvironment, RunningEnvironment, UninstalledEnvironment
from ._exceptions import VersionNotFoundError
from ._process import RunningProcess
from ._versions import Version, VersionRegistry

type Environment = RunningEnvironment | InstalledEnvironment | UninstalledEnvironment


class EnvironmentManager:
    """High-level facade orchestrating version curation, resolution, and deployments."""

    def __init__(
        self,
        directory: Path | None = None,
    ):
        self.directory = directory or user_cache_path("mcward", appauthor=False)
        self.versions = VersionRegistry(self.directory)

    def get(self, name: str) -> Environment:
        """Retrieve environment in its current state."""
        version, listed = self._get_version(name)
        directory = self.directory / version.name

        if self._is_running(directory):
            return RunningEnvironment(directory, version, RunningProcess.load(directory))
        if self._is_installed(directory):
            return InstalledEnvironment(directory, version)
        if listed:
            return UninstalledEnvironment(directory, version)
        raise VersionNotFoundError(name)

    def list_available(self, refresh: bool = False) -> list[Version]:
        """Provide access to upstream versions matrix."""
        return sorted(self.versions.sync() if refresh else self.versions.list(), reverse=True)

    def list_installed(self) -> list[Version]:
        """Aggregate sorted collections of valid active environment listings."""
        return sorted(self._scan_directory(self._is_installed, self.directory), reverse=True)

    def list_running(self) -> list[Version]:
        """List all currently running environments."""
        return sorted(self._scan_directory(self._is_running, self.directory), reverse=True)

    def _get_version(self, name: str) -> tuple[Version, bool]:
        """Get a version object, indicating if it was found in the registry."""
        if version := self.versions.get(name):
            return version, True
        try:
            return Version.parse(name), False
        except ValueError:
            raise VersionNotFoundError(name) from None

    def _is_running(self, directory: Path) -> bool:
        """Check if the directory contains a running environment."""
        required = [PID_FILE, PORT_FILE]
        return directory.exists() and all((directory / f).exists() for f in required)

    def _is_installed(self, directory: Path) -> bool:
        """Check if the directory contains a valid installation."""
        required = ["server.jar", "mods/fabric-api.jar", "mods/ward.jar"]
        return directory.exists() and all((directory / f).exists() for f in required)

    def _scan_directory(self, state: Callable[[Path], bool], directory: Path) -> list[Version]:
        """Scan the directory for versions that meet the given state criteria."""
        versions = []
        for base, prefix in filter(lambda e: e[0].exists(), [
            (directory, ""),
            (directory / "dev", "dev/"),
        ]):
            for entry in base.iterdir():
                if entry.is_dir() and state(entry):
                    with suppress(ValueError):
                        versions.append(Version.parse(f"{prefix}{entry.name}"))
        return versions
