"""GitHub Actions reporter: plain logs plus workflow-command annotations."""

from collections.abc import Sequence
from pathlib import Path

from mcward import (
    Diagnostic,
    RunningEnvironment,
    TestResult,
    TestSession,
    TestStatus,
    Version,
    run_tests,
)

from ..datapacks import FileResolver, pack_resolver
from ..ui import console
from .live import describe_failure, render_header, render_session


def run(
    datapacks: Sequence[Path],
    environments: Sequence[RunningEnvironment],
    selector: str = "*:*",
    coverage: bool = False,
    verbose: bool = False,
    resolve: FileResolver | None = None,
) -> TestSession:
    """Run tests, printing the final results view and GitHub annotations."""
    versions = [env.version for env in environments]
    console.print(render_header([p.name for p in datapacks], versions))
    resolve = resolve or pack_resolver(datapacks)

    # Consume the stream without rendering; it always yields a starting frame
    *_, session = run_tests(datapacks, environments, selector=selector, coverage=coverage)
    console.print(render_session(session, resolve, verbose))

    for command in annotations(session, resolve):
        print(command, flush=True)
    return session


def annotations(session: TestSession, resolve: FileResolver) -> list[str]:
    """Build one workflow command for everything wrong with the run."""
    commands = [
        _command("error", f"Ward aborted on {version.name}", message)
        for version, message in session.aborted.items()
    ]
    commands += [
        _annotate_diagnostic(diagnostic, versions, resolve)
        for diagnostic, versions in session.diagnostics.items()
    ]
    commands += [
        _annotate_test(result, resolve)
        for batch in session.batches
        for result in batch.results
        if result.status in (TestStatus.FAILED, TestStatus.SKIPPED)
    ]
    return commands


def _annotate_test(result: TestResult, resolve: FileResolver) -> str:
    failed = result.status is TestStatus.FAILED
    versions = [
        version for version in result.versions if result.outcomes[version].status is result.status
    ]
    outcome = result.outcomes[versions[0]]
    word = "failed" if failed else "skipped"
    title = f"{result.name} {word} on {', '.join(v.name for v in versions)}"

    file = resolve("test", result.name)
    line = outcome.line if file else None
    level = "error" if failed else "warning"
    return _command(level, title, describe_failure(outcome), file=file, line=line)


def _annotate_diagnostic(
    diagnostic: Diagnostic,
    versions: Sequence[Version],
    resolve: FileResolver,
) -> str:
    level = "error" if diagnostic.severity == "error" else "warning"
    title = f"{diagnostic.kind} {diagnostic.id} on {', '.join(v.name for v in versions)}"

    file = resolve(diagnostic.kind.split(":", 1)[-1], diagnostic.id)
    return _command(level, title, diagnostic.message, file=file)


def _command(
    level: str,
    title: str,
    message: str,
    file: str | None = None,
    line: int | None = None,
) -> str:
    """Format a ::level:: workflow command with escaped properties."""
    entries = [("title", title), ("file", file), ("line", line)]
    properties = ",".join(f"{key}={_escape(str(value), True)}" for key, value in entries if value)
    return f"::{level} {properties}::{_escape(message)}"


def _escape(value: str, property: bool = False) -> str:
    """Percent-escape a workflow command value per the GitHub runner rules."""
    value = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property:
        value = value.replace(",", "%2C").replace(":", "%3A")
    return value
