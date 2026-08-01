"""Concurrent multi-version test orchestration and result aggregation."""

import threading
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from queue import Queue

from ._environments import RunningEnvironment
from ._protocol import (
    BatchStarted,
    Diagnostic,
    Event,
    StreamError,
    TestFailed,
    TestPassed,
    TestsFinished,
    TestsStarted,
)
from ._versions import Version


class TestStatus(Enum):
    """Outcome of a single test on a single version."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"  # failed, but the test is optional


@dataclass(frozen=True)
class VersionOutcome:
    """How a single test fared on a single version."""

    status: TestStatus
    time: int = 0
    error: str = ""
    line: int | None = None
    tick: int | None = None


@dataclass(frozen=True)
class TestBatch:
    """A group of tests sharing the same game-test environment and dimension."""

    name: str
    results: list[TestResult]
    dimension: str | None = None


@dataclass
class TestResult:
    """Aggregated result for a single test across every version under test."""

    name: str
    batch: str
    versions: tuple[Version, ...]
    outcomes: dict[Version, VersionOutcome] = field(default_factory=dict)
    dimension: str | None = None

    @property
    def failed_versions(self) -> list[Version]:
        """Versions on which this test failed, in input order."""
        return [
            version
            for version in self.versions
            if (outcome := self.outcomes.get(version)) and outcome.status is TestStatus.FAILED
        ]

    @property
    def status(self) -> TestStatus | None:
        """Overall status, or ``None`` while still awaiting some version."""
        skipped = False
        for version in self.versions:
            match self.outcomes.get(version):
                case None:
                    return None
                case VersionOutcome(status=TestStatus.FAILED):
                    return TestStatus.FAILED
                case VersionOutcome(status=TestStatus.SKIPPED):
                    skipped = True
        return TestStatus.SKIPPED if skipped else TestStatus.PASSED


@dataclass(frozen=True)
class TestSummary:
    """Aggregate counts for the whole run, ready to render."""

    passed: int
    failed: int
    skipped: int
    total: int
    done: bool
    completed: int
    per_version: dict[Version, int]
    durations: dict[Version, int]


class TestSession:
    """Aggregate of the test phase across several running versions."""

    def __init__(self, versions: Sequence[Version]) -> None:
        self.versions = tuple(versions)
        self._results: dict[str, TestResult] = {}
        self._diagnostics: dict[Diagnostic, list[Version]] = {}
        self._batches: list[tuple[str, str | None]] = []
        self._current_batch: dict[Version, tuple[str, str | None]] = {}
        self._finished: dict[Version, TestsFinished] = {}
        self._aborted: dict[Version, str] = {}
        self._total = 0

    @property
    def aborted(self) -> dict[Version, str]:
        """Versions whose whole test stream died, mapped to the fatal error."""
        return self._aborted

    @property
    def diagnostics(self) -> dict[Diagnostic, list[Version]]:
        """Load problems mapped to the versions that reported them."""
        return self._diagnostics

    @property
    def failed(self) -> bool:
        """Whether any test failed, anything failed to load, or a stream aborted."""
        return (
            bool(self._aborted)
            or any(diagnostic.severity == "error" for diagnostic in self._diagnostics)
            or any(
                outcome.status is TestStatus.FAILED
                for result in self._results.values()
                for outcome in result.outcomes.values()
            )
        )

    @property
    def batches(self) -> list[TestBatch]:
        """Tests grouped by game-test environment, in discovery order."""
        return [
            TestBatch(
                name,
                [
                    result
                    for result in self._results.values()
                    if (result.batch, result.dimension) == (name, dimension)
                ],
                dimension,
            )
            for name, dimension in self._batches
        ]

    @property
    def summary(self) -> TestSummary:
        """Aggregate counts for the run."""
        statuses = [result.status for result in self._results.values()]
        completed = sum(status is not None for status in statuses)
        skipped = sum(status is TestStatus.SKIPPED for status in statuses)
        passed = sum(status is TestStatus.PASSED for status in statuses)

        return TestSummary(
            passed=passed,
            failed=completed - passed - skipped,
            skipped=skipped,
            total=self._total or len(self._results),  # fallback before tests_started
            done=all(v in self._finished or v in self._aborted for v in self.versions),
            completed=completed,
            per_version=self._passed_per_version(),
            durations={v: e.elapsed for v, e in self._finished.items()},
        )

    def _passed_per_version(self) -> dict[Version, int]:
        """Count passed tests for each version."""
        counts = dict.fromkeys(self.versions, 0)
        for result in self._results.values():
            for version, outcome in result.outcomes.items():
                if outcome.status is TestStatus.PASSED:
                    counts[version] += 1
        return counts

    def _dispatch(self, version: Version, event: Event) -> None:
        match event:
            case TestsStarted(total=total):
                self._total = max(self._total, total)
            case BatchStarted(environment=environment, dimension=dimension):
                self._current_batch[version] = (environment, dimension)
            case TestPassed(name=name, time=time):
                self._record(version, name, VersionOutcome(TestStatus.PASSED, time))
            case TestFailed(
                name=name, time=time, error=error, required=required, line=line, tick=tick
            ):
                status = TestStatus.FAILED if required else TestStatus.SKIPPED
                self._record(version, name, VersionOutcome(status, time, error, line, tick))
            case Diagnostic() as diagnostic:
                versions = self._diagnostics.setdefault(diagnostic, [])
                if version not in versions:
                    versions.append(version)
            case TestsFinished() as finished:
                self._finished[version] = finished
            case StreamError(message=message):
                self._aborted[version] = message

    def _record(self, version: Version, name: str, outcome: VersionOutcome) -> None:
        batch, dimension = self._current_batch.get(version, ("", None))
        if batch and (batch, dimension) not in self._batches:
            self._batches.append((batch, dimension))
        if name not in self._results:
            self._results[name] = TestResult(name, batch, self.versions, dimension=dimension)

        self._results[name].outcomes[version] = outcome


def run_tests(
    datapacks: Sequence[Path],
    environments: Sequence[RunningEnvironment],
    selector: str = "*:*",
    timeout: float | None = None,
) -> Iterator[TestSession]:
    """Stream tests across already-running environments, aggregating results.

    Yields the same (mutating) session after every event; consumers that need
    snapshots must copy what they read. ``timeout`` bounds the wait between
    consecutive events of one version; exceeding it aborts that stream.
    """
    session = TestSession([env.version for env in environments])
    events: Queue[tuple[Version, Event | None]] = Queue()

    def stream_events(env: RunningEnvironment) -> None:
        try:
            for event in env.test(list(datapacks), selector, timeout=timeout):
                events.put((env.version, event))
        except Exception as error:
            events.put((env.version, StreamError(str(error))))
        finally:
            events.put((env.version, None))  # stream exhausted

    # Daemon threads: if the consumer abandons this generator mid-run (render
    # failure, Ctrl+C), the readers may be blocked on their sockets and must
    # not keep the process alive or be joined on
    for env in environments:
        threading.Thread(target=stream_events, args=(env,), daemon=True).start()

    yield session  # empty starting frame

    pending = len(environments)
    while pending:
        version, event = events.get()
        if event is None:
            pending -= 1
            continue
        session._dispatch(version, event)
        yield session
