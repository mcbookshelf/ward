"""Ward, a testing framework for Minecraft datapacks."""

import sys
from pkgutil import extend_path

from ._environments import InstalledEnvironment, RunningEnvironment, UninstalledEnvironment
from ._exceptions import (
    AssetNotFoundError,
    DeployError,
    DownloadFailedError,
    InstallError,
    JavaNotFoundError,
    ProcessConnectionError,
    ProcessError,
    ProcessStartupError,
    VersionError,
    VersionNotFoundError,
    WardError,
)
from ._java import Java, find as find_java
from ._manager import Environment, EnvironmentManager
from ._protocol import Diagnostic, Status
from ._runner import (
    TestBatch,
    TestResult,
    TestSession,
    TestStatus,
    TestSummary,
    VersionOutcome,
    run_tests,
)
from ._versions import Version, VersionRegistry

__all__ = [
    "AssetNotFoundError",
    "DeployError",
    "Diagnostic",
    "DownloadFailedError",
    "Environment",
    "EnvironmentManager",
    "InstallError",
    "InstalledEnvironment",
    "Java",
    "JavaNotFoundError",
    "ProcessConnectionError",
    "ProcessError",
    "ProcessStartupError",
    "RunningEnvironment",
    "Status",
    "TestBatch",
    "TestResult",
    "TestSession",
    "TestStatus",
    "TestSummary",
    "UninstalledEnvironment",
    "Version",
    "VersionError",
    "VersionNotFoundError",
    "VersionOutcome",
    "VersionRegistry",
    "WardError",
    "find_java",
    "run_tests",
]

__path__ = extend_path(__path__, __name__)


def cli() -> None:
    """Console script entry point, guarded so a missing CLI extra explains itself."""
    try:
        # From the optional mcward-cli distribution, merged into this package via extend_path
        from mcward.cli import main as run  # ty: ignore[unresolved-import]
    except ImportError:
        print("Error: CLI dependencies not installed.", file=sys.stderr)
        print("Install with: uv add mcward[cli]", file=sys.stderr)
        sys.exit(1)
    run()
