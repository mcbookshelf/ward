"""Ward, a testing framework for Minecraft datapacks."""

import sys
from pkgutil import extend_path

from ._coverage import (
    ConditionNode,
    CoverageIgnores,
    CoverageReport,
    CoverageTotals,
    FunctionReport,
    IgnoreRule,
    LineCoverage,
    ResolvedCoverage,
    ResourceReport,
    RunNode,
    resolve_coverage,
    resolve_functions,
    resolve_resources,
)
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
from ._protocol import Coverage, Diagnostic, FunctionCoverage, Status
from ._runner import (
    TestBatch,
    TestResult,
    TestSession,
    TestStatus,
    TestSummary,
    VersionOutcome,
    run_tests,
)
from ._sources import (
    SourceFile,
    command_lines,
    ignored_lines,
    json_offsets,
    json_spans,
    scan_functions,
)
from ._versions import Version, VersionRegistry

__all__ = [
    "AssetNotFoundError",
    "ConditionNode",
    "Coverage",
    "CoverageIgnores",
    "CoverageReport",
    "CoverageTotals",
    "DeployError",
    "Diagnostic",
    "DownloadFailedError",
    "Environment",
    "EnvironmentManager",
    "FunctionCoverage",
    "FunctionReport",
    "IgnoreRule",
    "InstallError",
    "InstalledEnvironment",
    "Java",
    "JavaNotFoundError",
    "LineCoverage",
    "ProcessConnectionError",
    "ProcessError",
    "ProcessStartupError",
    "ResolvedCoverage",
    "ResourceReport",
    "RunNode",
    "RunningEnvironment",
    "SourceFile",
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
    "command_lines",
    "find_java",
    "ignored_lines",
    "json_offsets",
    "json_spans",
    "resolve_coverage",
    "resolve_functions",
    "resolve_resources",
    "run_tests",
    "scan_functions",
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
