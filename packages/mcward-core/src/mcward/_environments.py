"""Environment states."""

import os
import shutil
import time
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from . import _daemon
from ._daemon import RunningProcess
from ._exceptions import DeployError, InstallError
from ._protocol import Event, Status
from ._versions import Version

IGNORED_DIRS = ("__pycache__", "node_modules")


@dataclass(frozen=True)
class UninstalledEnvironment:
    directory: Path
    version: Version

    def install(self) -> InstalledEnvironment:
        """Download every asset the environment needs."""
        import asyncio

        from . import _assets  # deferred: the network stack costs ~0.3s to import

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
        coverage: bool = False,
        timeout: float | None = None,
    ) -> Iterator[Event]:
        """Deploy the given datapacks and stream a test run."""
        _daemon.wait_idle(self.process.address)
        _deploy(self.directory / "world" / "datapacks", datapacks)

        return _daemon.stream_tests(
            self.process.address,
            selector,
            coverage=coverage,
            timeout=timeout,
        )


def _deploy(deployed: Path, datapacks: list[Path], attempts: int = 10) -> None:
    """Replace the deployed packs, retrying while the previous server lets go of them."""
    for attempt in range(attempts):
        try:
            return _replace_packs(deployed, datapacks)
        except OSError as e:
            if attempt == attempts - 1:
                raise DeployError(f"Could not copy datapacks to the test server: {e}") from e
            time.sleep(0.5)


def _replace_packs(deployed: Path, datapacks: list[Path]) -> None:
    if deployed.exists():
        shutil.rmtree(deployed)
    deployed.mkdir(parents=True)
    for datapack, name in zip(datapacks, _unique_names(datapacks), strict=True):
        if datapack.is_file():
            shutil.copyfile(datapack, deployed / name)
        else:
            _zip_pack(datapack, deployed / name)


def _zip_pack(source: Path, target: Path) -> None:
    """Archive a pack directory; one stored zip deploys much faster than a file tree."""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_STORED) as archive:
        for root, dirs, files in os.walk(source):
            # Pruned in place so the walk never enters .git or node_modules
            dirs[:] = sorted(d for d in dirs if not _ignored(d))
            for name in sorted(files):
                if not _ignored(name):
                    file = Path(root, name)
                    archive.write(file, file.relative_to(source).as_posix())


def _ignored(name: str) -> bool:
    return name.startswith(".") or name in IGNORED_DIRS


def _unique_names(datapacks: list[Path]) -> list[str]:
    """Deployment names for the packs, suffixing duplicates (pack, pack-2, ...).

    Directory packs deploy zipped, so their names gain the extension.
    """
    bases = [pack.name if pack.is_file() else f"{pack.name}.zip" for pack in datapacks]
    reserved = set(bases)
    names: list[str] = []
    for base in bases:
        name, count = base, 1
        while name in names or (name != base and name in reserved):
            count += 1
            name = f"{base.removesuffix('.zip')}-{count}.zip"
        names.append(name)
    return names
