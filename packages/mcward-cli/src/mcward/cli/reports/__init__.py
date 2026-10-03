"""Report files written after a run: JUnit XML test results and coverage."""

from collections.abc import Mapping, Sequence
from pathlib import Path

import rich_click as click

from mcward import (
    CoverageIgnores,
    CoverageTotals,
    ResolvedCoverage,
    TestSession,
    Version,
    resolve_coverage,
)

from ..reporters.coverage import render_coverage
from ..ui import console, print_warning
from .html import write_html
from .junit import write_junit
from .lcov import write_lcov

__all__ = [
    "coverage_shortfalls",
    "missing_coverage",
    "parse_coverage_report",
    "report_session",
    "write_coverage_reports",
    "write_html",
    "write_junit",
    "write_lcov",
]

COVERAGE_FORMATS = {"lcov": "coverage.lcov", "html": "coverage.html"}


def parse_coverage_report(value: str) -> tuple[str, Path]:
    """Split a ``format[:path]`` value, falling back to the format's default path."""
    format, _, path = value.partition(":")
    if format not in COVERAGE_FORMATS:
        formats = ", ".join(COVERAGE_FORMATS)
        raise click.BadParameter(f"Unknown coverage format {format!r} (expected {formats})")
    return format, Path(path) if path else Path(COVERAGE_FORMATS[format])


def report_session(
    session: TestSession,
    datapacks: Sequence[Path],
    specs: Sequence[tuple[str, Path]] = (),
    junit_xml: Path | None = None,
    verbose: bool = False,
    selector: str = "*:*",
    ignores: CoverageIgnores | None = None,
    coverage: bool = False,
    minimum: float | None = None,
) -> None:
    """Render the coverage summary and write the requested report files.

    With a minimum, a run that measured coverage and stays under it ends in an error.
    """
    if junit_xml is not None:
        write_junit(session, junit_xml)
        console.print(f"Test results written to [magenta]{junit_xml}[/magenta]")
    if coverage:
        for version in missing_coverage(session):
            print_warning(
                f"No coverage reported by {version.name}: its ward mod predates coverage, "
                "reinstall the environment once a newer release supports this Minecraft version"
            )
    resolved = {
        version: resolve_coverage(recorded, datapacks, selector, ignores)
        for version, recorded in session.coverage.items()
    }
    if resolved:
        console.print(render_coverage(resolved, verbose))
        for file in write_coverage_reports(session, resolved, specs):
            console.print(f"Coverage report written to [magenta]{file}[/magenta]")
    if not verbose:
        hint = "More detail: --verbose"
        if session.coverage and not specs:
            hint += ", or --coverage-report html"
        console.print(f"[dim]{hint}[/dim]")
    if coverage and minimum is not None:
        if shortfalls := coverage_shortfalls(session, resolved, minimum):
            raise click.ClickException("\n".join(shortfalls))


def coverage_shortfalls(
    session: TestSession,
    resolved: Mapping[Version, ResolvedCoverage],
    minimum: float,
) -> list[str]:
    """One line per version whose coverage does not reach the minimum percentage."""
    lines = [
        f"No coverage from {version.name} to check against the minimum of {minimum:g}%"
        for version in missing_coverage(session)
    ]
    for version, coverage in resolved.items():
        ratio = CoverageTotals.of(coverage.reports).ratio
        # Compared as it is printed, so a figure shown as 80.0% reaches a minimum of 80
        if ratio is not None and round(ratio * 100, 1) < minimum:
            where = f" on {version.name}" if len(session.versions) > 1 else ""
            lines.append(f"Coverage {ratio:.1%}{where} is below the minimum of {minimum:g}%")
    return lines


def missing_coverage(session: TestSession) -> list[Version]:
    """Versions whose run completed without a coverage event."""
    return [
        version
        for version in session.versions
        if version not in session.coverage and version not in session.aborted
    ]


def write_coverage_reports(
    session: TestSession,
    resolved: Mapping[Version, ResolvedCoverage],
    specs: Sequence[tuple[str, Path]],
) -> list[Path]:
    """Write the requested coverage files, one per reporting version."""
    files = []
    for version, coverage in resolved.items():
        for format, target in specs:
            file = _versioned(target, version, len(resolved) > 1)
            if format == "lcov":
                write_lcov(coverage, file)
            else:
                write_html(session, version, coverage, file)
            files.append(file)
    return files


def _versioned(target: Path, version: Version, several: bool) -> Path:
    if not several:
        return target
    name = version.name.replace("/", "-")
    return target.with_name(f"{target.stem}-{name}{target.suffix}")
