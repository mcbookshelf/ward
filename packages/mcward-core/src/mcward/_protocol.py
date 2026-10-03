"""The WardBridge protocol: every event the server sends, as a type.

Unknown event types parse to ``None`` and are skipped.
"""

from dataclasses import dataclass, field
from typing import Any

from ._exceptions import ProcessConnectionError


@dataclass(frozen=True)
class TestsStarted:
    """A test run began, with the number of tests it will execute."""

    total: int
    pos: tuple[int, int, int] | None


@dataclass(frozen=True)
class BatchStarted:
    """Tests of the given game-test environment begin."""

    environment: str
    dimension: str | None = None
    total: int | None = None


@dataclass(frozen=True)
class BatchFinished:
    """Tests of the given game-test environment are done."""

    environment: str
    dimension: str | None = None


@dataclass(frozen=True)
class TestPassed:
    """A single test passed."""

    name: str
    time: int


@dataclass(frozen=True)
class TestFailed:
    """A single test failed; Ward failures carry their position in the file.

    Failures of optional tests (``required`` false) do not fail the run:
    consumers report them as skipped.
    """

    name: str
    time: int
    error: str
    required: bool
    line: int | None
    tick: int | None


@dataclass(frozen=True)
class Diagnostic:
    """A datapack file failed to load while preparing the run."""

    severity: str
    kind: str
    id: str
    message: str


@dataclass(frozen=True)
class FunctionCoverage:
    """Hit counts for one function, indexed by command order in the file."""

    reached: tuple[int, ...]
    executed: tuple[int, ...]


@dataclass(frozen=True)
class Coverage:
    """Coverage recorded during the run, with the data pack format of the server
    as (major, minor). An older mod does not send the format."""

    functions: dict[str, FunctionCoverage]
    conditions: dict[str, dict[str, dict[str, tuple[int, int]]]] = field(default_factory=dict)
    runs: dict[str, dict[str, dict[str, tuple[int, int]]]] = field(default_factory=dict)
    pack_format: tuple[int, int] | None = None


@dataclass(frozen=True)
class TestsFinished:
    """The run completed."""

    total: int | None
    passed: int | None
    failed: int | None
    skipped: int | None
    elapsed: int


@dataclass(frozen=True)
class BenchResult:
    """One benchmarked command: batch times in nanoseconds, or why it was not measured."""

    index: int
    name: str
    batch: int = 0
    samples: tuple[int, ...] = ()
    commands: int | None = None
    allocated: int | None = None
    error: str | None = None
    failed: str | None = None


@dataclass(frozen=True)
class BenchFinished:
    """Every command of the bench was handled."""

    elapsed: int


@dataclass(frozen=True)
class Status:
    """Response to a status request. An older mod only sends `ready`."""

    ready: bool
    protocol: int | None = None
    mod: str | None = None
    minecraft: str | None = None


@dataclass(frozen=True)
class StreamError:
    """The server aborted the stream with a fatal error."""

    message: str


type Event = (
    TestsStarted
    | BatchStarted
    | BatchFinished
    | TestPassed
    | TestFailed
    | Diagnostic
    | Coverage
    | TestsFinished
    | BenchResult
    | BenchFinished
    | Status
    | StreamError
)


def _node_counts(data: dict[str, Any]) -> dict[str, dict[str, dict[str, tuple[int, int]]]]:
    """Nested per-node count pairs: registry, then element, then path."""
    return {
        registry: {
            element: {path: (first, second) for path, (first, second) in nodes.items()}
            for element, nodes in elements.items()
        }
        for registry, elements in data.items()
    }


def parse_event(data: dict[str, Any]) -> Event | None:
    """Parse a wire message into an event, or None for unknown types."""
    kind = data.get("type")
    try:
        match kind:
            case "tests_started":
                pos = data.get("pos")
                return TestsStarted(total=data["total"], pos=tuple(pos) if pos else None)
            case "batch_started":
                return BatchStarted(
                    environment=data["environment"],
                    dimension=data.get("dimension"),
                    total=data.get("total"),
                )
            case "batch_finished":
                return BatchFinished(
                    environment=data["environment"],
                    dimension=data.get("dimension"),
                )
            case "test_passed":
                return TestPassed(name=data["name"], time=data["time"])
            case "test_failed":
                return TestFailed(
                    name=data["name"],
                    time=data["time"],
                    error=data["error"],
                    required=data["required"],
                    line=data.get("line"),
                    tick=data.get("tick"),
                )
            case "load_diagnostic":
                return Diagnostic(
                    severity=data["severity"],
                    kind=data["kind"],
                    id=data["id"],
                    message=data["message"],
                )
            case "coverage":
                return Coverage(
                    functions={
                        name: FunctionCoverage(tuple(counts["reached"]), tuple(counts["executed"]))
                        for name, counts in data["functions"].items()
                    },
                    conditions=_node_counts(data.get("conditions", {})),
                    runs=_node_counts(data.get("runs", {})),
                    pack_format=tuple(data["pack_format"]) if "pack_format" in data else None,
                )
            case "tests_finished":
                return TestsFinished(
                    total=data.get("total"),
                    passed=data.get("passed"),
                    failed=data.get("failed"),
                    skipped=data.get("skipped"),
                    elapsed=data["elapsed"],
                )
            case "bench_result":
                return BenchResult(
                    index=data["index"],
                    name=data["name"],
                    batch=data.get("batch", 0),
                    samples=tuple(data.get("samples", ())),
                    commands=data.get("commands"),
                    allocated=data.get("allocated"),
                    error=data.get("error"),
                    failed=data.get("failed"),
                )
            case "bench_finished":
                return BenchFinished(elapsed=data["elapsed"])
            case "status":
                return Status(
                    ready=data["ready"],
                    protocol=data.get("protocol"),
                    mod=data.get("mod"),
                    minecraft=data.get("minecraft"),
                )
            case "error":
                return StreamError(message=data["message"])
            case _:
                return None
    except KeyError as e:
        raise ProcessConnectionError(f"Malformed {kind} event: missing {e}") from e
