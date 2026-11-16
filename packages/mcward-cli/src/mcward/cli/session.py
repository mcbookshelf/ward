"""The test run that mcward test and beet test share."""

from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

import rich_click as click

from mcward import TestSession, WardConfig, WardError, check_world

from .datapacks import DataPack, FileResolver, format_range
from .environments import manager, select_compatible, start_environments
from .reporters import github, live
from .ui import console
from .writers import report_session

type Run = Callable[[str, Sequence[str]], TestSession]

OPTIONS = (
    click.option(
        "--version",
        "-v",
        "versions",
        multiple=True,
        help="Minecraft version(s) to test on",
    ),
    click.option(
        "--reporter",
        type=click.Choice(["live", "github"]),
        default="live",
        help="Result output: interactive live display, or GitHub Actions annotations",
    ),
    click.option(
        "--coverage",
        is_flag=True,
        help="Record which function commands run and report line coverage",
    ),
    click.option(
        "--coverage-report",
        "coverage_reports",
        multiple=True,
        metavar="FORMAT[:PATH]",
        help="Write coverage as 'lcov' or 'html', with an optional path (repeatable); "
        "implies --coverage",
    ),
    click.option(
        "--coverage-min",
        type=click.FloatRange(0, 100),
        default=None,
        metavar="PERCENT",
        help="Fail the run when coverage is below this percentage; implies --coverage",
    ),
    click.option(
        "--junit-xml",
        type=click.Path(dir_okay=False, writable=True, path_type=Path),
        default=None,
        help="Write test results as JUnit XML",
    ),
    click.option(
        "--verbose",
        is_flag=True,
        help="List every test and coverage row instead of collapsing large runs",
    ),
    click.option(
        "--watch",
        "-w",
        is_flag=True,
        help="Run again when a file changes, with keys to rerun or filter",
    ),
    click.option(
        "--world",
        type=click.Path(exists=True, file_okay=False, path_type=Path),
        default=None,
        help="Run in a copy of this world save instead of a flat world",
    ),
    click.argument("selector", default="*:*"),
)


def test_options[F: Callable[..., object]](command: F) -> F:
    """The options and the selector that mcward test and beet test share."""
    for option in reversed(OPTIONS):
        command = option(command)
    return command


def check_watch(watch: bool, reporter: str) -> None:
    if watch and reporter == "github":
        raise click.UsageError("--watch only works with the live reporter")


def load_config(world: Path | None) -> WardConfig:
    """Read ward.toml, ``--world`` replacing its world, and reject a folder that is no world."""
    try:
        config = WardConfig.load()
        if world is not None:
            config = replace(config, world=world)
        if config.world is not None:
            check_world(config.world)
    except WardError as e:
        raise click.ClickException(str(e)) from e
    return config


def rerunnable(versions: Sequence[str], run: Run) -> Callable[[str], TestSession]:
    """Run with the given versions, then with the ones picked, so reruns ask only once."""
    chosen = list(versions)

    def rerun(selector: str) -> TestSession:
        session = run(selector, chosen)
        chosen[:] = [version.name for version in session.versions]
        return session

    return rerun


def run_session(
    datapacks: Sequence[DataPack],
    *,
    config: WardConfig,
    versions: Sequence[str] = (),
    reporter: str = "live",
    selector: str = "*:*",
    coverage: bool = False,
    coverage_specs: Sequence[tuple[str, Path]] = (),
    coverage_min: float | None = None,
    junit_xml: Path | None = None,
    verbose: bool = False,
    resolve: FileResolver | None = None,
) -> TestSession:
    """Pick versions, start them, run and report; ``coverage_min`` overrides ward.toml."""
    low, high = format_range(datapacks)
    selected = versions or select_compatible(low, high)
    paths = [datapack.path for datapack in datapacks]
    coverage = coverage or bool(coverage_specs) or coverage_min is not None
    run = github.run if reporter == "github" else live.run

    try:
        minimum = config.coverage.minimum
        if coverage_min is not None:
            minimum = replace(minimum, total=coverage_min)
        envs = start_environments([manager.get(v) for v in selected])
        console.print()
        session = run(
            paths,
            envs,
            selector,
            coverage=coverage,
            verbose=verbose,
            resolve=resolve,
            world=config.world,
        )
        report_session(
            session,
            paths,
            specs=coverage_specs,
            junit_xml=junit_xml,
            verbose=verbose,
            selector=selector,
            ignores=config.coverage.ignores,
            coverage=coverage,
            minimum=minimum,
        )
    except WardError as e:
        raise click.ClickException(str(e)) from e
    return session
