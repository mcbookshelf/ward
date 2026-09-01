"""Live reporter: an interactive Rich display updating as results stream in."""

from collections.abc import Sequence
from pathlib import Path
from time import monotonic

from rich.live import Live
from rich.text import Text

from mcward import (
    RunningEnvironment,
    TestBatch,
    TestResult,
    TestSession,
    TestStatus,
    TestSummary,
    Version,
    VersionOutcome,
    run_tests,
)

from ..datapacks import FileResolver, pack_resolver
from ..ui import console

_SYMBOL: dict[TestStatus | None, tuple[str | tuple[str, ...], str]] = {
    None: (("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"), "yellow"),
    TestStatus.PASSED: ("✓", "green"),
    TestStatus.FAILED: ("✗", "red"),
    TestStatus.SKIPPED: ("⊘", "yellow"),
}

_TIME_STYLE: dict[TestStatus, str] = {
    TestStatus.PASSED: "green",
    TestStatus.FAILED: "red",
    TestStatus.SKIPPED: "yellow",
}


def run(
    datapacks: Sequence[Path],
    environments: Sequence[RunningEnvironment],
    selector: str = "*:*",
    coverage: bool = False,
    verbose: bool = False,
    resolve: FileResolver | None = None,
) -> TestSession:
    """Run tests across running environments with a live Rich display."""
    versions = [env.version for env in environments]
    console.print(render_header([p.name for p in datapacks], versions))
    resolve = resolve or pack_resolver(datapacks)

    session = TestSession(versions)  # rebound by every frame; bound even if none arrives
    rendered = 0.0
    with Live(console=console, refresh_per_second=10) as live:
        for session in run_tests(datapacks, environments, selector=selector, coverage=coverage):
            # Events can outpace the display many times over; render at frame rate
            if (now := monotonic()) - rendered < 0.1:
                continue
            rendered = now
            live.update(render_session(session, resolve, verbose), refresh=False)
        live.update(render_session(session, resolve, verbose), refresh=False)
    return session


def format_millis(millis: int) -> str:
    """Format a duration the way the mod's own reporters do (5ms, 1.2s)."""
    return f"{millis}ms" if millis < 1000 else f"{millis / 1000:.1f}s"


def describe_failure(outcome: VersionOutcome, file: str | None = None) -> str:
    """The failure message, with its position (``file:line`` when the file is known) and tick."""
    if outcome.line is None:
        return outcome.error
    if file is None:
        return f"{outcome.error} (line {outcome.line}, tick {outcome.tick})"
    return f"{outcome.error} ({file}:{outcome.line}, tick {outcome.tick})"


def render_header(datapacks: Sequence[str], versions: Sequence[Version]) -> Text:
    """The single-line ``Testing <packs> on <versions>`` banner."""
    text = Text()
    text.append("Testing ", "bold")
    if 0 < len(datapacks) <= 3:
        text.append(", ".join(datapacks), "magenta")
        text.append(" ")
    text.append("on ", "bold")
    text.append(", ".join(v.name for v in versions), "magenta")
    return text


def render_session(
    session: TestSession,
    resolve: FileResolver | None = None,
    verbose: bool = False,
) -> Text:
    """The full aggregated results view for the test phase."""
    text = Text()
    batches = session.batches
    summary = session.summary
    _render_diagnostics(text, session, resolve)
    if not verbose and batches:
        text.append("\n")
        active = session.active_batches if not summary.done else set()
        width = max(len(batch.name) for batch in batches)
        counts = [_count(batch) for batch in batches]
        count_width = max(map(len, counts))
        for batch, count in zip(batches, counts, strict=True):
            _render_batch(text, batch, active, width, f"{count:>{count_width}}", resolve)
    else:
        for batch in batches:
            text.append(f"\n {_label(batch)}\n", "dim")
            for result in batch.results:
                _render_result(text, result, resolve)

    for version, message in session.aborted.items():
        text.append(f"✗ {version.name}: {message}\n", "red")
    text.append("\n")
    _render_summary(text, summary, session.versions)
    return text


def _render_diagnostics(
    text: Text,
    session: TestSession,
    resolve: FileResolver | None = None,
) -> None:
    if not session.diagnostics:
        return
    text.append("\n")
    for diagnostic, versions in session.diagnostics.items():
        symbol, style = ("✗", "red") if diagnostic.severity == "error" else ("⊘", "yellow")
        text.append(f"{symbol} ", style)
        text.append(f"[{diagnostic.kind}] ")

        # The path already carries the id (data/<ns>/<folder>/<id-path>)
        file = resolve(diagnostic.kind.split(":", 1)[-1], diagnostic.id) if resolve else None
        if file:
            text.append(f"{file}", "dim")
        else:
            text.append(diagnostic.id, "dim")
        if len(versions) < len(session.versions):
            text.append(f" ({', '.join(v.name for v in versions)})", "dim")
        text.append("\n")
        text.append(f"  {diagnostic.message}\n", f"dim {style}")


def _render_batch(
    text: Text,
    batch: TestBatch,
    active: set[tuple[str, str | None]],
    width: int,
    count: str,
    resolve: FileResolver | None = None,
) -> None:
    """One line per batch: status symbol, name, dimension, aligned passed count."""
    statuses = [result.status for result in batch.results]
    if TestStatus.FAILED in statuses:
        status: TestStatus | None = TestStatus.FAILED
    elif None in statuses or (batch.name, batch.dimension) in active:
        status = None
    elif TestStatus.SKIPPED in statuses:
        status = TestStatus.SKIPPED
    else:
        status = TestStatus.PASSED

    symbol, style = _SYMBOL[status]
    text.append(f"{_frame(symbol)} ", style)
    text.append(f"{batch.name:<{width}}")
    text.append(f" {count}")
    if batch.dimension:
        text.append(f" ({batch.dimension})", "dim")
    text.append("\n")

    for result in batch.results:
        if result.status in (TestStatus.FAILED, TestStatus.SKIPPED):
            _render_result(text, result, resolve)


def _label(batch: TestBatch) -> str:
    return f"{batch.name} ({batch.dimension})" if batch.dimension else batch.name


def _count(batch: TestBatch) -> str:
    """Passed over the announced batch size, so the denominator is stable mid-run."""
    passed = sum(result.status is TestStatus.PASSED for result in batch.results)
    return f"{passed}/{max(batch.total or 0, len(batch.results))}"


def _frame(symbol: str | tuple[str, ...]) -> str:
    if isinstance(symbol, tuple):
        return symbol[(int(console.get_time() * 16 % len(symbol)))]
    return symbol


def _render_result(text: Text, result: TestResult, resolve: FileResolver | None = None) -> None:
    symbol, symbol_style = _SYMBOL[result.status]
    symbol = _frame(symbol)

    text.append("  ")
    text.append(f"{symbol} ", symbol_style)
    text.append(result.name)
    text.append(" (", "dim")
    for i, version in enumerate(result.versions):
        if i:
            text.append(", ", "dim")
        if outcome := result.outcomes.get(version):
            text.append(format_millis(outcome.time), _TIME_STYLE[outcome.status])
        else:
            text.append("—", "dim")
    text.append(")\n", "dim")

    if result.status is TestStatus.FAILED:
        _render_failure(text, result, result.failed_versions, "Failed", "red", resolve)
    elif result.status is TestStatus.SKIPPED:
        skipped = [
            version
            for version in result.versions
            if result.outcomes[version].status is TestStatus.SKIPPED
        ]
        _render_failure(text, result, skipped, "Skipped", "yellow", resolve)


def _render_failure(
    text: Text,
    result: TestResult,
    versions: list[Version],
    label: str,
    style: str,
    resolve: FileResolver | None = None,
) -> None:
    file = resolve("test", result.name) if resolve else None

    if len(result.versions) == 1:
        message = describe_failure(result.outcomes[versions[0]], file)
        text.append(f"    {message}\n", f"dim {style}")
        return

    names = ", ".join(v.name for v in versions)
    text.append(f"    {label} on: {names}\n", style)
    for version in versions:
        message = describe_failure(result.outcomes[version], file)
        text.append(f"    {version.name}: {message}\n", f"dim {style}")


def _render_summary(text: Text, summary: TestSummary, versions: tuple[Version, ...]) -> None:
    if not summary.done:
        if summary.total:
            text.append(f"Tests: {summary.completed}/{summary.total} completed", "dim")
        else:
            # Nothing has been announced yet: the server is still deploying and booting
            text.append("Starting tests…", "dim")
        return

    if len(versions) > 1:
        for v in versions:
            text.append(f"{v.name}: ", "magenta")
            text.append(f"{summary.per_version[v]}/{summary.total}")
            if v in summary.durations:
                text.append(f" ({format_millis(summary.durations[v])})", "dim")
            text.append("\n")
        text.append("\n")

    text.append("Tests: ", "bold")
    text.append(f"{summary.passed} passed", "green")
    if summary.failed:
        text.append(", ")
        text.append(f"{summary.failed} failed", "red")
    if summary.skipped:
        text.append(", ")
        text.append(f"{summary.skipped} skipped", "yellow")
    text.append(f", {summary.total} total")

    if len(versions) == 1:
        if (elapsed := summary.durations.get(versions[0])) is not None:
            text.append(f" ({format_millis(elapsed)})", "dim")
    text.append("\n")
