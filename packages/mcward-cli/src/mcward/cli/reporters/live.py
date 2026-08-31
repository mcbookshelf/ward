"""Live reporter: an interactive Rich display updating as results stream in."""

from collections.abc import Sequence
from pathlib import Path

from rich.live import Live
from rich.text import Text

from mcward import (
    RunningEnvironment,
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
    resolve: FileResolver | None = None,
) -> TestSession:
    """Run tests across running environments with a live Rich display."""
    versions = [env.version for env in environments]
    console.print(render_header([p.name for p in datapacks], versions))
    resolve = resolve or pack_resolver(datapacks)

    session = TestSession(versions)  # placeholder so the return is always bound
    with Live(console=console, refresh_per_second=10) as live:
        for session in run_tests(datapacks, environments, selector=selector):
            live.update(render_session(session, resolve), refresh=False)
    return session


def format_millis(millis: int) -> str:
    """Format a duration the way the mod's own reporters do (5ms, 1.2s)."""
    return f"{millis}ms" if millis < 1000 else f"{millis / 1000:.1f}s"


def describe_failure(outcome: VersionOutcome, file: str | None = None) -> str:
    """The failure message, with the position suffix when the test carries one.

    With a ``path:line`` relative to the project root when applicable.
    """
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


def render_session(session: TestSession, resolve: FileResolver | None = None) -> Text:
    """The full aggregated results view for the test phase."""
    text = Text()
    _render_diagnostics(text, session, resolve)
    for batch in session.batches:
        label = f"{batch.name} ({batch.dimension})" if batch.dimension else batch.name
        text.append(f"\n {label}\n", "dim")
        for result in batch.results:
            _render_result(text, result, resolve)

    for version, message in session.aborted.items():
        text.append(f"✗ {version.name}: {message}\n", "red")
    text.append("\n")
    _render_summary(text, session.summary, session.versions)
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


def _render_result(text: Text, result: TestResult, resolve: FileResolver | None = None) -> None:
    symbol, symbol_style = _SYMBOL[result.status]
    if isinstance(symbol, tuple):
        symbol = symbol[(int(console.get_time() * 16 % len(symbol)))]

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
        text.append(f"Tests: {summary.completed}/{summary.total} completed", "dim")
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
