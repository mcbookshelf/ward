"""Ward - A testing framework for Minecraft datapacks."""

import sys
from pkgutil import extend_path

from ._environments import InstalledEnvironment, RunningEnvironment, UninstalledEnvironment
from ._exceptions import (
    AssetNotFoundError,
    DownloadFailedError,
    InstallError,
    ProcessConnectionError,
    ProcessError,
    ProcessStartupError,
    VersionError,
    VersionNotFoundError,
    WardError,
)
from ._manager import Environment, EnvironmentManager
from ._versions import Version, VersionRegistry

__all__ = [
    "AssetNotFoundError",
    "DownloadFailedError",
    "Environment",
    "EnvironmentManager",
    "InstallError",
    "InstalledEnvironment",
    "ProcessConnectionError",
    "ProcessError",
    "ProcessStartupError",
    "RunningEnvironment",
    "UninstalledEnvironment",
    "Version",
    "VersionError",
    "VersionNotFoundError",
    "VersionRegistry",
    "WardError",
]

__path__ = extend_path(__path__, __name__)

def cli() -> None:
    """Entry point that requires CLI to be installed."""
    try:
        from mcward.cli import main as run
    except ImportError:
        print("Error: CLI dependencies not installed.", file=sys.stderr)
        print("Install with: uv add mcward[cli]", file=sys.stderr)
        sys.exit(1)
    run()
