"""Tests for the benchmark statistics."""

import pytest

from mcward import BenchReport, compare
from mcward._bench import summarize
from mcward._protocol import BenchResult, parse_event


class TestSummarize:
    def test_batch_times_become_times_per_run(self) -> None:
        result = BenchResult(index=0, name="say a", batch=10, samples=(1000, 2000, 3000))
        report = summarize(result)
        assert report.times == (100.0, 200.0, 300.0)
        assert report.mean == 200.0
        assert report.median == 200.0
        assert report.fastest == 100.0
        assert report.p95 == 300.0
        assert report.stddev == pytest.approx(100.0)

    def test_a_tick_share_is_a_part_of_fifty_milliseconds(self) -> None:
        report = BenchReport(name="say a", batch=1, times=(500_000.0,))
        assert report.tick_share == pytest.approx(0.01)
        assert report.stddev == 0.0

    def test_a_command_that_was_not_measured_has_no_times(self) -> None:
        report = summarize(BenchResult(index=0, name="sya a", failed="Unknown command"))
        assert report.times == ()
        assert report.failed == "Unknown command"


class TestCompare:
    def test_the_fastest_is_the_reference(self) -> None:
        slow = BenchReport(name="slow", batch=1, times=(400.0, 420.0))
        fast = BenchReport(name="fast", batch=1, times=(100.0, 100.0))
        (comparison,) = compare([slow, fast])
        assert comparison.report is slow
        assert comparison.ratio == pytest.approx(4.1)
        assert comparison.uncertainty > 0

    def test_nothing_to_compare_with_one_measured_command(self) -> None:
        only = BenchReport(name="only", batch=1, times=(100.0,))
        broken = BenchReport(name="broken", failed="Unknown command")
        assert compare([only, broken]) == []


class TestProtocol:
    def test_a_result_parses_with_its_samples(self) -> None:
        event = parse_event(
            {
                "type": "bench_result",
                "index": 1,
                "name": "function a:b",
                "batch": 73,
                "samples": [30102334, 29871201],
                "commands": 2401,
                "allocated": 38211,
            }
        )
        assert event == BenchResult(
            index=1,
            name="function a:b",
            batch=73,
            samples=(30102334, 29871201),
            commands=2401,
            allocated=38211,
        )

    def test_a_result_that_was_not_measured_parses(self) -> None:
        event = parse_event({"type": "bench_result", "index": 0, "name": "x", "failed": "nope"})
        assert event == BenchResult(index=0, name="x", failed="nope")
