"""The test command."""

import sys
from pathlib import Path

import rich_click as click

from ..datapacks import DEFAULT_PATTERNS, discover_datapacks
from ..reports import parse_coverage_report
from ..session import run_session


@click.command()
@click.option(
    "--pack",
    "-p",
    "packs",
    multiple=True,
    help="Datapack paths or glob patterns",
)
@click.option(
    "--version",
    "-v",
    "versions",
    multiple=True,
    help="Minecraft version(s) to test on",
)
@click.option(
    "--reporter",
    type=click.Choice(["live", "github"]),
    default="live",
    help="Result output: interactive live display, or GitHub Actions annotations",
)
@click.option(
    "--coverage",
    is_flag=True,
    help="Record which function commands run and report line coverage",
)
@click.option(
    "--coverage-report",
    "coverage_reports",
    multiple=True,
    metavar="FORMAT[:PATH]",
    help="Write coverage as 'lcov' or 'html', with an optional path (repeatable); "
    "implies --coverage",
)
@click.option(
    "--coverage-min",
    type=click.FloatRange(0, 100),
    default=None,
    metavar="PERCENT",
    help="Fail the run when coverage is below this percentage; implies --coverage",
)
@click.option(
    "--junit-xml",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write test results as JUnit XML",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="List every test and coverage row instead of collapsing large runs",
)
@click.argument("selector", default="*:*")
def test(
    versions: tuple[str, ...],
    packs: tuple[str, ...],
    reporter: str,
    coverage: bool,
    coverage_reports: tuple[str, ...],
    coverage_min: float | None,
    junit_xml: Path | None,
    verbose: bool,
    selector: str,
) -> None:
    """Run datapack tests."""
    datapacks = discover_datapacks(packs if packs else DEFAULT_PATTERNS)
    if not datapacks:
        raise click.ClickException("Datapack not found")

    session = run_session(
        datapacks,
        versions=versions,
        reporter=reporter,
        selector=selector,
        coverage=coverage,
        coverage_specs=[parse_coverage_report(value) for value in coverage_reports],
        coverage_min=coverage_min,
        junit_xml=junit_xml,
        verbose=verbose,
    )
    if session.failed:
        sys.exit(1)
