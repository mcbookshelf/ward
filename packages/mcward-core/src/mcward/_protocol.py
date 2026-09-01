"""The WardBridge protocol: every event the server sends, as a type.

Unknown event types parse to ``None`` and are skipped.
"""

from dataclasses import dataclass, field
from typing import Any

from ._exceptions import ProcessConnectionError


@dataclass(frozen=True)
class TestsStarted:
    """A test run began, with the number of tests it will execute.

    ``pos`` is the world position the run's structure grid spawns at.
    """

    total: int
    pos: tuple[int, int, int]


@dataclass(frozen=True)
class BatchStarted:
    """Tests of the given game-test environment begin.

    ``total`` is the number of tests the batch will run, when the server
    reports it.
    """

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
    """Coverage recorded during the run.

    A command is *reached* when it starts executing and *executed* when its
    final command dispatches with at least one source: an ``execute`` line
    whose fork or condition dropped every source is reached but not executed.

    ``conditions`` counts data-driven conditionals: registry id, then element
    id, then the condition's path within the element's JSON to its
    ``(times_true, times_false)`` outcomes. ``runs`` counts the gated blocks
    themselves (loot entries, item modifier functions) with the same keys,
    holding ``(times_reached, times_ran)``.
    """

    functions: dict[str, FunctionCoverage]
    conditions: dict[str, dict[str, dict[str, tuple[int, int]]]] = field(default_factory=dict)
    runs: dict[str, dict[str, dict[str, tuple[int, int]]]] = field(default_factory=dict)


@dataclass(frozen=True)
class TestsFinished:
    """The run completed, with its aggregate counts."""

    total: int
    passed: int
    failed: int
    skipped: int
    elapsed: int


@dataclass(frozen=True)
class Status:
    """Response to a status request."""

    ready: bool


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
                x, y, z = data["pos"]
                return TestsStarted(total=data["total"], pos=(x, y, z))
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
                )
            case "tests_finished":
                return TestsFinished(
                    total=data["total"],
                    passed=data["passed"],
                    failed=data["failed"],
                    skipped=data["skipped"],
                    elapsed=data["elapsed"],
                )
            case "status":
                return Status(ready=data["ready"])
            case "error":
                return StreamError(message=data["message"])
            case _:
                return None
    except KeyError as e:
        raise ProcessConnectionError(f"Malformed {kind} event: missing {e}") from e
