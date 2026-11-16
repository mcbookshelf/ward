"""Ward, a testing framework for Minecraft datapacks."""

from pkgutil import extend_path

from ._bench import BenchComparison, BenchReport, compare, run_bench
from ._config import WardConfig
from ._coverage import (
    ConditionNode,
    CoverageConfig,
    CoverageIgnores,
    CoverageMinimum,
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
from ._protocol import Coverage, Diagnostic, FunctionCoverage, Status, TestLog
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
    json_spans,
    scan_functions,
)
from ._versions import Version, VersionRegistry
from ._worlds import check_world

__all__ = [
    "AssetNotFoundError",
    "BenchComparison",
    "BenchReport",
    "ConditionNode",
    "Coverage",
    "CoverageConfig",
    "CoverageIgnores",
    "CoverageMinimum",
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
    "TestLog",
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
    "WardConfig",
    "WardError",
    "check_world",
    "command_lines",
    "compare",
    "find_java",
    "ignored_lines",
    "json_spans",
    "resolve_coverage",
    "resolve_functions",
    "resolve_resources",
    "run_bench",
    "run_tests",
    "scan_functions",
]


# mcward-cli and mcward-beet add mcward.cli, mcward.beet and mcward.mecha from their own folders
__path__ = extend_path(__path__, __name__)
