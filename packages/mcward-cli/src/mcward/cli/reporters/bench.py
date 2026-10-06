"""Benchmark output: one block per command, then how the commands compare."""

from collections.abc import Sequence

from mcward import BenchReport, compare


def format_time(nanos: float) -> str:
    """A duration with the unit that keeps it readable."""
    for unit, size in (("s", 1e9), ("ms", 1e6), ("µs", 1e3)):
        if nanos >= size:
            return f"{nanos / size:.1f} {unit}"
    return f"{nanos:.0f} ns"


def format_bytes(count: int) -> str:
    for unit, size in (("MB", 1e6), ("kB", 1e3)):
        if count >= size:
            return f"{count / size:.1f} {unit}"
    return f"{count} B"


def render_report(index: int, report: BenchReport) -> list[str]:
    """The lines of one benchmark, in rich markup."""
    lines = [f"[bold]Benchmark {index}:[/] {report.name}"]

    if report.failed:
        lines.append(f"  [red]✗ not measured: {report.failed}[/]")
        return lines
    if report.error:
        lines.append(f"  [yellow]! first run failed: {report.error}[/]")

    mean, sigma = format_time(report.mean), format_time(report.stddev)
    low, high, median = (format_time(v) for v in (report.fastest, report.p95, report.median))
    share = f"{report.tick_share:.2%}" if report.tick_share >= 0.0001 else "<0.01%"
    lines.append(f"  Time (mean ± σ):    [green]{mean}[/] ± {sigma}    {share} of a tick")
    lines.append(f"  Range (min … p95):  {low} … {high}  median {median}")

    cost = [f"{report.commands} commands"] if report.commands is not None else []
    if report.allocated is not None:
        cost.append(f"{format_bytes(report.allocated)} allocated")
    if cost:
        lines.append(f"  Per run:            {', '.join(cost)}")

    lines.append(f"  [dim]{len(report.times)} samples of {report.batch} runs[/]")
    return lines


def render_summary(reports: Sequence[BenchReport]) -> list[str]:
    """How many times faster the fastest command is than each of the others."""
    comparisons = compare(reports)
    if not comparisons:
        return []

    fastest = min((report for report in reports if report.times), key=lambda r: r.mean)
    lines = ["[bold]Summary[/]", f"  [cyan]{fastest.name}[/] ran"]
    for comparison in comparisons:
        ratio = f"{comparison.ratio:.2f} ± {comparison.uncertainty:.2f}"
        lines.append(f"    [green]{ratio}[/] times faster than {comparison.report.name}")
    return lines
