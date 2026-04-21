"""Environment state management."""

import asyncio
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from . import _assets as assets, _process as process
from ._versions import Version


@dataclass(frozen=True)
class UninstalledEnvironment:
    """Represents an environment that has not yet been installed."""

    directory: Path
    version: Version

    def install(self) -> InstalledEnvironment:
        """Download and prepare the environment for use."""
        asyncio.run(assets.download(self.directory, self.version))
        return InstalledEnvironment(self.directory, self.version)


@dataclass(frozen=True)
class InstalledEnvironment:
    """Represents an environment that has been installed but not running."""

    directory: Path
    version: Version

    def start(self) -> RunningEnvironment:
        """Start process for this environment."""
        running = process.start(self.directory)
        return RunningEnvironment(self.directory, self.version, running)

    def uninstall(self) -> UninstalledEnvironment:
        """Uninstall the environment by removing its directory."""
        shutil.rmtree(self.directory, ignore_errors=True)
        return UninstalledEnvironment(self.directory, self.version)


@dataclass(frozen=True)
class RunningEnvironment:
    """Represents an environment with process running."""

    directory: Path
    version: Version
    running: process.RunningProcess

    def test(self, selector: str = "*:*") -> Iterator[dict]:
        """Run tests via process IPC."""
        return process.test(self.running.address, selector)

    def status(self) -> dict:
        """Get process status."""
        return process.status(self.running.address)

    def stop(self) -> InstalledEnvironment:
        """Stop process and transition back to installed state."""
        process.stop(self.running)
        return InstalledEnvironment(self.directory, self.version)
