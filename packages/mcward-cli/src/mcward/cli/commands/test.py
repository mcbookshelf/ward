"""The test command."""

import sys
from pathlib import Path

import rich_click as click

from mcward import CoverageIgnores, WardError

from ..datapacks import DEFAULT_PATTERNS, discover_datapacks
from ..environments import manager, select_compatible, start_environments
from ..reporters import github, live
from ..reports import parse_coverage_report, report_session
from ..ui import console


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
    junit_xml: Path | None,
    verbose: bool,
    selector: str,
) -> None:
    """Run datapack tests."""
    datapacks = discover_datapacks(packs if packs else DEFAULT_PATTERNS)
    if not datapacks:
        raise click.ClickException("Datapack not found")

    strictest = max(datapacks, key=lambda datapack: datapack.min_format)
    loosest = min(datapacks, key=lambda datapack: datapack.max_format)
    if strictest.min_format > loosest.max_format:
        raise click.ClickException(
            f"Datapacks have disjoint pack format ranges: {strictest.path.name} needs "
            f">= {strictest.min_format} but {loosest.path.name} caps at {loosest.max_format}"
        )

    selected = versions or select_compatible(strictest.min_format, loosest.max_format)
    paths = [datapack.path for datapack in datapacks]

    specs = [parse_coverage_report(value) for value in coverage_reports]
    enabled = coverage or bool(specs)
    run = github.run if reporter == "github" else live.run
    try:
        ignores = CoverageIgnores.load()
        envs = start_environments([manager.get(v) for v in selected])
        console.print()
        session = run(paths, envs, selector, coverage=enabled, verbose=verbose)
        report_session(session, paths, specs, junit_xml, verbose, selector, ignores)
        if session.failed:
            sys.exit(1)
    except WardError as e:
        raise click.ClickException(str(e)) from e
