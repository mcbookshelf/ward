"""The WardBridge protocol: every event the server sends, as a type.

Unknown event types parse to ``None`` and are skipped: the protocol field
gates real incompatibilities, and informational messages added by a newer
mod must not break older tooling. A *known* event missing a field, however,
is protocol corruption and fails loudly.
"""

from dataclasses import dataclass

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
    """Tests of the given game-test environment begin."""

    environment: str
    dimension: str | None = None


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
    | TestsFinished
    | Status
    | StreamError
)


def parse_event(data: dict) -> Event | None:
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
