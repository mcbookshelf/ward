"""Environment management for Ward."""

from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from ._constants import CACHE_DIR, PID_FILE, PORT_FILE
from ._daemon import RunningProcess, is_ward_process
from ._environments import InstalledEnvironment, RunningEnvironment, UninstalledEnvironment
from ._exceptions import VersionNotFoundError
from ._versions import Version, VersionRegistry

type Environment = RunningEnvironment | InstalledEnvironment | UninstalledEnvironment


INSTALLED_FILES = ("server.jar", "mods/fabric-api.jar", "mods/ward.jar")


class EnvironmentManager:
    """High-level facade resolving version names into environment states.

    A custom directory relocates environments and the registry cache, but
    not the provisioned Java runtime, which is machine-global (JAVA_DIR).
    The "dev" alias reads gradle.properties from the working directory: it
    means "the mod checkout this command runs in".
    """

    def __init__(self, directory: Path | None = None):
        self.directory = directory or CACHE_DIR
        self.environments = self.directory / "environments"
        self.versions = VersionRegistry(self.directory)

    def get(self, name: str) -> Environment:
        """The environment for a version name or alias, in whatever state it is in."""
        version, listed = self._get_version(name)
        directory = self.environments / version.name

        if self._is_running(directory):
            return RunningEnvironment(directory, version, RunningProcess.load(directory))
        if self._is_installed(directory):
            return InstalledEnvironment(directory, version)
        if listed:
            return UninstalledEnvironment(directory, version)
        raise VersionNotFoundError(name)

    def list_available(self) -> list[Version]:
        """Every version in the registry, newest first."""
        return sorted(self.versions.list(), reverse=True)

    def list_installed(self) -> list[Version]:
        """Versions with a complete environment on disk, newest first."""
        return sorted(self._scan_directory(self._is_installed), reverse=True)

    def list_running(self) -> list[Version]:
        """Versions whose daemon is alive, newest first."""
        return sorted(self._scan_directory(self._is_running), reverse=True)

    def list_compatible(self, min_fmt: int, max_fmt: int) -> list[Version]:
        """Versions whose pack format falls in the range, newest first."""
        return sorted(self.versions.list_in_range(min_fmt, max_fmt), reverse=True)

    def _get_version(self, name: str) -> tuple[Version, bool]:
        """The version and whether the registry actually lists it."""
        if version := self.versions.get(name):
            return version, True
        if name == "dev":
            raise VersionNotFoundError("dev (no gradle.properties in the working directory)")
        try:
            return Version.parse(name), False
        except ValueError:
            raise VersionNotFoundError(name) from None

    def _is_installed(self, directory: Path) -> bool:
        """Whether the directory holds every asset of an installed environment."""
        return directory.exists() and all((directory / f).exists() for f in INSTALLED_FILES)

    def _is_running(self, directory: Path) -> bool:
        """Whether the recorded pid is still one of our servers, clearing it if not."""
        try:
            running = RunningProcess.load(directory)
        except OSError, ValueError:
            return False
        if is_ward_process(running.pid):
            return True
        directory.joinpath(PID_FILE).unlink(missing_ok=True)
        directory.joinpath(PORT_FILE).unlink(missing_ok=True)
        return False

    def _scan_directory(self, predicate: Callable[[Path], bool]) -> list[Version]:
        """Collect versions whose environment directory matches the predicate."""
        versions = []
        sources = [(self.environments, ""), (self.environments / "dev", "dev/")]
        for base, prefix in filter(lambda e: e[0].exists(), sources):
            for entry in base.iterdir():
                if entry.is_dir() and predicate(entry):
                    with suppress(ValueError):
                        versions.append(Version.parse(f"{prefix}{entry.name}"))
        return versions
