"""Environment states."""

import asyncio
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from . import _assets, _daemon
from ._daemon import RunningProcess
from ._exceptions import DeployError, InstallError
from ._protocol import Event, Status
from ._versions import Version


@dataclass(frozen=True)
class UninstalledEnvironment:
    directory: Path
    version: Version

    def install(self) -> InstalledEnvironment:
        """Download every asset the environment needs."""
        asyncio.run(_assets.install(self.directory, self.version))
        return InstalledEnvironment(self.directory, self.version)


@dataclass(frozen=True)
class InstalledEnvironment:
    directory: Path
    version: Version

    def start(self) -> RunningEnvironment:
        """Spawn the daemon process and wait until it answers."""
        return RunningEnvironment(self.directory, self.version, _daemon.start(self.directory))

    def uninstall(self) -> UninstalledEnvironment:
        """Remove the environment directory and everything in it."""
        try:
            if self.directory.exists():
                shutil.rmtree(self.directory)
        except OSError as e:
            raise InstallError(f"Could not remove {self.directory}: {e}") from e
        return UninstalledEnvironment(self.directory, self.version)


@dataclass(frozen=True)
class RunningEnvironment:
    directory: Path
    version: Version
    process: RunningProcess

    def status(self) -> Status:
        """Ask the daemon whether it is ready to serve a run."""
        return _daemon.status(self.process.address)

    def stop(self) -> InstalledEnvironment:
        """Shut the daemon down, escalating to a kill if it hangs."""
        _daemon.stop(self.process)
        return InstalledEnvironment(self.directory, self.version)

    def test(
        self,
        datapacks: list[Path],
        selector: str = "*:*",
        timeout: float | None = None,
    ) -> Iterator[Event]:
        """Deploy the given datapacks and stream a test run.

        ``timeout`` bounds the wait between consecutive events; ``None``
        waits indefinitely.
        """
        deployed = self.directory / "world" / "datapacks"
        try:
            if deployed.exists():
                shutil.rmtree(deployed)
            deployed.mkdir(parents=True)
            for datapack, name in zip(datapacks, _unique_names(datapacks), strict=True):
                if datapack.is_file():
                    # Zipped datapacks deploy as-is; the server reads them directly
                    shutil.copyfile(datapack, deployed / name)
                else:
                    shutil.copytree(
                        datapack,
                        deployed / name,
                        ignore=shutil.ignore_patterns(".*", "__pycache__", "node_modules"),
                    )
        except OSError as e:
            raise DeployError(f"Could not copy datapacks to the test server: {e}") from e

        return _daemon.stream_tests(self.process.address, selector, timeout=timeout)


def _unique_names(datapacks: list[Path]) -> list[str]:
    """Deployment names for the packs, suffixing duplicates (pack, pack-2, ...)."""
    reserved = {datapack.name for datapack in datapacks}
    names: list[str] = []
    for datapack in datapacks:
        name, count = datapack.name, 1
        while name in names or (name != datapack.name and name in reserved):
            count += 1
            name = f"{datapack.stem}-{count}{datapack.suffix}"
        names.append(name)
    return names
