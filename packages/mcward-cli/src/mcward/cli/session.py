"""The test run that mcward test and beet test share."""

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import rich_click as click

from mcward import CoverageConfig, TestSession, WardError

from .datapacks import DataPack, FileResolver, format_range
from .environments import manager, select_compatible, start_environments
from .reporters import github, live
from .reports import report_session
from .ui import console


def run_session(
    datapacks: Sequence[DataPack],
    *,
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
    """Pick the versions, start them, run the tests and write the reports.

    ``coverage_min`` replaces the total minimum of ward.toml for this run.
    """
    low, high = format_range(datapacks)
    selected = versions or select_compatible(low, high)
    paths = [datapack.path for datapack in datapacks]
    coverage = coverage or bool(coverage_specs) or coverage_min is not None
    run = github.run if reporter == "github" else live.run

    try:
        config = CoverageConfig.load()
        minimum = config.minimum
        if coverage_min is not None:
            minimum = replace(minimum, total=coverage_min)
        envs = start_environments([manager.get(v) for v in selected])
        console.print()
        session = run(paths, envs, selector, coverage=coverage, verbose=verbose, resolve=resolve)
        report_session(
            session,
            paths,
            specs=coverage_specs,
            junit_xml=junit_xml,
            verbose=verbose,
            selector=selector,
            ignores=config.ignores,
            coverage=coverage,
            minimum=minimum,
        )
    except WardError as e:
        raise click.ClickException(str(e)) from e
    return session
