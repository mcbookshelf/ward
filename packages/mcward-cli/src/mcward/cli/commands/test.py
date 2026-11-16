import sys
from collections.abc import Sequence
from pathlib import Path

import rich_click as click

from mcward import TestSession

from ..datapacks import DEFAULT_PATTERNS, discover_datapacks
from ..session import check_watch, load_config, rerunnable, run_session, test_options
from ..watch import watch as watch_tests
from ..writers import parse_coverage_report


@click.command()
@click.option(
    "--pack",
    "-p",
    "packs",
    multiple=True,
    help="Datapack paths or glob patterns",
)
@test_options
def test(
    versions: tuple[str, ...],
    packs: tuple[str, ...],
    reporter: str,
    coverage: bool,
    coverage_reports: tuple[str, ...],
    coverage_min: float | None,
    junit_xml: Path | None,
    verbose: bool,
    watch: bool,
    world: Path | None,
    selector: str,
) -> None:
    """Run datapack tests."""
    check_watch(watch, reporter)
    config = load_config(world)
    datapacks = discover_datapacks(packs if packs else DEFAULT_PATTERNS)
    if not datapacks:
        raise click.ClickException("Datapack not found")

    def run_once(selector: str, versions: Sequence[str]) -> TestSession:
        return run_session(
            datapacks,
            versions=versions,
            reporter=reporter,
            selector=selector,
            coverage=coverage,
            coverage_specs=[parse_coverage_report(value) for value in coverage_reports],
            coverage_min=coverage_min,
            junit_xml=junit_xml,
            verbose=verbose,
            config=config,
        )

    run = rerunnable(versions, run_once)
    if watch:
        watched = [datapack.path for datapack in datapacks]
        watch_tests(run, selector, [*watched, config.world] if config.world else watched)
    elif run(selector).failed:
        sys.exit(1)
