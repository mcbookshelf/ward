"""Benchmarks: run commands on a test server and turn the raw batch times into numbers."""

import math
import statistics
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from ._environments import RunningEnvironment
from ._exceptions import ProcessError
from ._protocol import BenchFinished, BenchResult, StreamError

TICK_NANOS = 50_000_000


@dataclass(frozen=True)
class BenchReport:
    """One benchmarked command. Times are nanoseconds per run."""

    name: str
    batch: int = 0
    times: tuple[float, ...] = ()
    commands: int | None = None
    allocated: int | None = None
    error: str | None = None
    failed: str | None = None

    @property
    def mean(self) -> float:
        return statistics.fmean(self.times)

    @property
    def stddev(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.times)

    @property
    def fastest(self) -> float:
        return min(self.times)

    @property
    def p95(self) -> float:
        ordered = sorted(self.times)
        return ordered[math.ceil(0.95 * len(ordered)) - 1]

    @property
    def tick_share(self) -> float:
        """The part of a 50 ms tick that one run takes."""
        return self.mean / TICK_NANOS


@dataclass(frozen=True)
class BenchComparison:
    """How many times slower a report is than the fastest one."""

    report: BenchReport
    ratio: float
    uncertainty: float


def summarize(result: BenchResult) -> BenchReport:
    """Turn the batch times of the mod into times per run."""
    return BenchReport(
        name=result.name,
        batch=result.batch,
        times=tuple(sample / result.batch for sample in result.samples) if result.batch else (),
        commands=result.commands,
        allocated=result.allocated,
        error=result.error,
        failed=result.failed,
    )


def compare(reports: Sequence[BenchReport]) -> list[BenchComparison]:
    """Rank the measured reports against the fastest one, which comes first."""
    measured = sorted((report for report in reports if report.times), key=lambda r: r.mean)
    if len(measured) < 2:
        return []

    best = measured[0]
    comparisons = []
    for report in measured[1:]:
        ratio = report.mean / best.mean
        spread = math.hypot(report.stddev / report.mean, best.stddev / best.mean)
        comparisons.append(BenchComparison(report, ratio, ratio * spread))
    return comparisons


def run_bench(
    datapacks: Sequence[Path],
    environment: RunningEnvironment,
    commands: Sequence[str],
    setup: Sequence[str] = (),
    prepare: Sequence[str] = (),
    batch: int = 0,
    warmup: int | None = None,
    duration: int | None = None,
    timeout: float | None = None,
) -> Iterator[BenchReport]:
    """Benchmark commands on a running environment, one report per command as it completes."""
    events = environment.bench(
        list(datapacks),
        commands,
        setup,
        prepare,
        batch,
        warmup=warmup,
        duration=duration,
        timeout=timeout,
    )
    for event in events:
        match event:
            case BenchResult() as result:
                yield summarize(result)
            case BenchFinished():
                return
            case StreamError(message=message):
                raise ProcessError(message)
