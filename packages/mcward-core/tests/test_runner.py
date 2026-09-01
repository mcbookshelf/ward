"""Tests for test run orchestration and result aggregation."""

from collections.abc import Iterator
from typing import cast

from mcward import RunningEnvironment, Version, run_tests
from mcward._protocol import (
    BatchFinished,
    BatchStarted,
    Diagnostic,
    Event,
    StreamError,
    TestFailed as Failed,
    TestPassed as Passed,
    TestsFinished as Finished,
    TestsStarted as Started,
)

# Aliased so pytest does not try to collect the production classes as tests
from mcward._runner import TestSession as Session, TestStatus as Status


class FakeEnvironment:
    """Duck-typed stand-in for RunningEnvironment: a version and an event stream."""

    def __init__(self, version: Version, events: list[Event] | Exception):
        self.version = version
        self._events = events

    def test(self, datapacks, selector="*:*", coverage=False, timeout=None) -> Iterator[Event]:
        if isinstance(self._events, Exception):
            raise self._events
        yield from self._events


def drain(environments: list[FakeEnvironment]) -> Session:
    """Run to completion and return the final session."""
    # run_tests only needs .version and .test(); the fake fills the contract
    *_, session = run_tests([], cast("list[RunningEnvironment]", environments))
    return session


V1 = Version.parse("26.1.2")
V2 = Version.parse("26.1.1")


def events_for(passed: list[str], failed: dict[str, str], batch: str = "default") -> list[Event]:
    """Build a plausible event stream for one version."""
    events: list[Event] = [
        Started(total=len(passed) + len(failed), pos=(0, -59, 0)),
        BatchStarted(environment=batch),
    ]
    events.extend(Passed(name=name, time=5) for name in passed)
    events.extend(
        Failed(name=name, time=5, error=error, required=True, line=None, tick=None)
        for name, error in failed.items()
    )
    events.append(BatchFinished(environment=batch))
    events.append(
        Finished(
            total=len(passed) + len(failed),
            passed=len(passed),
            failed=len(failed),
            skipped=0,
            elapsed=1000,
        )
    )
    return events


class TestRunTests:
    """Test the aggregation of event streams across versions."""

    def test_single_version_all_passed(self) -> None:
        env = FakeEnvironment(V1, events_for(["a:one", "a:two"], {}))
        session = drain([env])

        assert not session.failed
        summary = session.summary
        assert summary.done
        assert (summary.passed, summary.failed, summary.total) == (2, 0, 2)
        assert summary.durations[V1] == 1000

    def test_single_version_with_failure(self) -> None:
        env = FakeEnvironment(V1, events_for(["a:one"], {"a:two": "boom"}))
        session = drain([env])

        assert session.failed
        assert session.summary.failed == 1

        result = next(r for b in session.batches for r in b.results if r.name == "a:two")
        assert result.status is Status.FAILED
        assert result.outcomes[V1].error == "boom"

    def test_optional_failure_is_skipped_and_does_not_fail_the_run(self) -> None:
        """A failed optional test reports as skipped, honoring the directive."""
        env = FakeEnvironment(
            V1,
            [
                Started(total=1, pos=(0, -59, 0)),
                BatchStarted(environment="default"),
                Failed("a:opt", time=5, error="boom", required=False, line=None, tick=None),
                Finished(total=1, passed=0, failed=0, skipped=1, elapsed=1000),
            ],
        )
        session = drain([env])

        assert not session.failed
        assert (session.summary.failed, session.summary.skipped) == (0, 1)

        result = next(r for b in session.batches for r in b.results)
        assert result.status is Status.SKIPPED
        assert result.outcomes[V1].error == "boom"

    def test_skipped_on_one_version_failed_on_another_is_failed(self) -> None:
        """FAILED outranks SKIPPED when versions disagree."""
        failed = Failed("a:opt", time=5, error="boom", required=True, line=None, tick=None)
        skipped = Failed("a:opt", time=5, error="boom", required=False, line=None, tick=None)
        done = Finished(total=1, passed=0, failed=1, skipped=0, elapsed=1000)
        started = Started(total=1, pos=(0, -59, 0))
        envs = [
            FakeEnvironment(V1, [started, BatchStarted(environment="d"), failed, done]),
            FakeEnvironment(V2, [started, BatchStarted(environment="d"), skipped, done]),
        ]
        session = drain(envs)

        assert session.failed
        result = next(r for b in session.batches for r in b.results)
        assert result.status is Status.FAILED
        assert result.failed_versions == [V1]

    def test_failure_position_fields_are_captured(self) -> None:
        """Structured line/tick fields from the daemon land on the outcome."""
        env = FakeEnvironment(
            V1,
            [
                Started(total=1, pos=(0, -59, 0)),
                BatchStarted(environment="default"),
                Failed("a:one", time=5, error="boom", required=True, line=7, tick=42),
                Finished(total=1, passed=0, failed=1, skipped=0, elapsed=1000),
            ],
        )
        session = drain([env])

        outcome = next(r for b in session.batches for r in b.results).outcomes[V1]
        assert (outcome.line, outcome.tick) == (7, 42)

    def test_load_diagnostics_are_deduplicated_across_versions(self) -> None:
        diagnostic = Diagnostic("error", "minecraft:loot_table", "a:broken", "Missing type")
        done = Finished(total=0, passed=0, failed=0, skipped=0, elapsed=1000)
        envs = [
            FakeEnvironment(V1, [diagnostic, done]),
            FakeEnvironment(V2, [diagnostic, done]),
        ]
        session = drain(envs)

        [(found, versions)] = session.diagnostics.items()
        assert found.kind == "minecraft:loot_table"
        assert found.severity == "error"
        assert sorted(versions, reverse=True) == [V1, V2]

    def test_repeated_diagnostic_counts_its_version_once(self) -> None:
        diagnostic = Diagnostic("warn", "pack.mcmeta", "broken", "Invalid meta")
        done = Finished(total=0, passed=0, failed=0, skipped=0, elapsed=1000)
        env = FakeEnvironment(V1, [diagnostic, diagnostic, done])
        session = drain([env])

        [(_, versions)] = session.diagnostics.items()
        assert versions == [V1]

    def test_error_diagnostics_fail_the_run(self) -> None:
        """A datapack that fails to load must fail the run, tests or not."""
        diagnostic = Diagnostic("error", "minecraft:loot_table", "a:broken", "Missing type")
        done = Finished(total=0, passed=0, failed=0, skipped=0, elapsed=1000)
        env = FakeEnvironment(V1, [diagnostic, done])

        assert drain([env]).failed

    def test_warning_diagnostics_do_not_fail_the_run(self) -> None:
        diagnostic = Diagnostic("warn", "pack.mcmeta", "broken", "Invalid meta")
        done = Finished(total=0, passed=0, failed=0, skipped=0, elapsed=1000)
        env = FakeEnvironment(V1, [diagnostic, done])

        assert not drain([env]).failed

    def test_versions_disagree(self) -> None:
        """A test passing on one version and failing on another fails overall."""
        envs = [
            FakeEnvironment(V1, events_for(["a:one"], {})),
            FakeEnvironment(V2, events_for([], {"a:one": "only here"})),
        ]
        session = drain(envs)

        assert session.failed
        result = next(r for b in session.batches for r in b.results)
        assert result.status is Status.FAILED
        assert result.failed_versions == [V2]
        assert result.outcomes[V1].status is Status.PASSED

    def test_result_pending_until_all_versions_report(self) -> None:
        """Status stays None while any version has not reported."""
        session = Session([V1, V2])
        session._dispatch(V1, BatchStarted(environment="default"))
        session._dispatch(V1, Passed(name="a:one", time=5))

        result = next(r for b in session.batches for r in b.results)
        assert result.status is None
        assert not session.summary.done

    def test_batches_carry_their_announced_total(self) -> None:
        session = Session([V1])
        session._dispatch(V1, BatchStarted(environment="default", total=17))
        session._dispatch(V1, Passed(name="a:one", time=5))

        (batch,) = session.batches
        assert batch.total == 17

    def test_active_batches_follow_the_batch_lifecycle(self) -> None:
        session = Session([V1])
        assert session.active_batches == set()

        session._dispatch(V1, BatchStarted(environment="default"))
        assert session.active_batches == {("default", None)}

        session._dispatch(V1, BatchFinished(environment="default"))
        assert session.active_batches == set()

    def test_total_falls_back_to_seen_results(self) -> None:
        """Before tests_started arrives, total mirrors the recorded results."""
        session = Session([V1])
        session._dispatch(V1, BatchStarted(environment="default"))
        session._dispatch(V1, Passed(name="a:one", time=5))

        assert session.summary.total == 1

        session._dispatch(V1, Started(total=5, pos=(0, -59, 0)))
        assert session.summary.total == 5

    def test_batches_keep_discovery_order(self) -> None:
        """Batches are grouped and ordered by first appearance."""
        env = FakeEnvironment(
            V1,
            [
                BatchStarted(environment="second"),
                Passed(name="a:two", time=5),
                BatchStarted(environment="first"),
                Passed(name="a:one", time=5),
                Finished(total=2, passed=2, failed=0, skipped=0, elapsed=1000),
            ],
        )
        session = drain([env])

        batches = session.batches
        assert [b.name for b in batches] == ["second", "first"]
        assert [r.name for b in batches for r in b.results] == ["a:two", "a:one"]

    def test_same_environment_split_by_dimension(self) -> None:
        """The same environment in another dimension is a separate batch."""
        env = FakeEnvironment(
            V1,
            [
                BatchStarted(environment="default", dimension="minecraft:overworld"),
                Passed(name="a:one", time=5),
                BatchStarted(environment="default", dimension="minecraft:the_nether"),
                Passed(name="a:two", time=5),
                Finished(total=2, passed=2, failed=0, skipped=0, elapsed=1000),
            ],
        )
        session = drain([env])

        batches = session.batches
        assert [(b.name, b.dimension) for b in batches] == [
            ("default", "minecraft:overworld"),
            ("default", "minecraft:the_nether"),
        ]
        assert [r.name for b in batches for r in b.results] == ["a:one", "a:two"]

    def test_stream_error_aborts_version(self) -> None:
        """An exception in one version's stream aborts it without killing the rest."""
        envs = [
            FakeEnvironment(V1, events_for(["a:one"], {})),
            FakeEnvironment(V2, ConnectionError("server died")),
        ]
        session = drain(envs)

        assert session.failed
        assert V2 in session.aborted
        assert "server died" in session.aborted[V2]
        # The healthy version still completed
        assert session.summary.per_version[V1] == 1

    def test_error_event_aborts_version(self) -> None:
        """A server-sent error event marks the version aborted."""
        env = FakeEnvironment(V1, [StreamError("reload failed")])
        session = drain([env])

        assert session.failed
        assert session.aborted[V1] == "reload failed"
        assert session.summary.done
