"""Report files written after a run: JUnit XML test results and coverage."""

from collections.abc import Mapping, Sequence
from pathlib import Path

import rich_click as click

from mcward import CoverageIgnores, ResolvedCoverage, TestSession, Version, resolve_coverage

from ..reporters.coverage import render_coverage
from ..ui import console
from .html import write_html
from .junit import write_junit
from .lcov import write_lcov

__all__ = [
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
) -> None:
    """Render the coverage summary and write the requested report files."""
    if junit_xml is not None:
        write_junit(session, junit_xml)
        console.print(f"Test results written to [magenta]{junit_xml}[/magenta]")
    if session.coverage:
        resolved = {
            version: resolve_coverage(coverage, datapacks, selector, ignores)
            for version, coverage in session.coverage.items()
        }
        console.print(render_coverage(resolved, verbose))
        for file in write_coverage_reports(session, resolved, specs):
            console.print(f"Coverage report written to [magenta]{file}[/magenta]")
    if not verbose:
        hint = "More detail: --verbose"
        if session.coverage and not specs:
            hint += ", or --coverage-report html"
        console.print(f"[dim]{hint}[/dim]")


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
