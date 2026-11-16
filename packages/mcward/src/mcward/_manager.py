"""Environment management for Ward."""

from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path

from ._constants import CACHE_DIR
from ._daemon import RunningProcess, clear_files, is_ward_process
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

        if (process := self._running_process(directory)) is not None:
            return RunningEnvironment(directory, version, process)
        if self._is_installed(directory):
            return InstalledEnvironment(directory, version)
        if listed:
            return UninstalledEnvironment(directory, version)
        raise VersionNotFoundError(name)

    def list_available(self) -> list[Version]:
        """Every version in the registry, newest first."""
        return sorted(self.versions.available(), reverse=True)

    def list_installed(self) -> list[Version]:
        """Versions with a complete environment on disk, newest first."""
        installed = (v for v, directory in self._directories() if self._is_installed(directory))
        return sorted(installed, reverse=True)

    def list_running(self) -> list[Version]:
        """Versions whose daemon is alive, newest first."""
        return [environment.version for environment in self.running_environments()]

    def running_environments(self) -> list[RunningEnvironment]:
        """The environments whose daemon is alive, newest first, without asking the registry."""
        environments = [
            RunningEnvironment(directory, version, process)
            for version, directory in self._directories()
            if (process := self._running_process(directory)) is not None
        ]
        return sorted(environments, key=lambda environment: environment.version, reverse=True)

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
        return all((directory / f).exists() for f in INSTALLED_FILES)

    def _running_process(self, directory: Path) -> RunningProcess | None:
        """The recorded process if it is still one of our servers, clearing stale files if not."""
        try:
            process = RunningProcess.load(directory)
        except OSError, ValueError:
            return None
        if is_ward_process(process.pid, directory):
            return process
        clear_files(directory)
        return None

    def _directories(self) -> Iterator[tuple[Version, Path]]:
        """The environment directories on disk, each with the version it holds."""
        for base, prefix in ((self.environments, ""), (self.environments / "dev", "dev/")):
            if not base.exists():
                continue
            for entry in base.iterdir():
                if entry.is_dir():
                    with suppress(ValueError):
                        yield Version.parse(f"{prefix}{entry.name}"), entry
