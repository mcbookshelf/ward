"""The beet test command: build the current project and run its tests with Ward."""

import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from beet import Project
from beet.toolchain.cli import beet, message_fence
from beet.toolchain.project import ProjectBuilder
from mcward import CoverageIgnores, TestSession, WardError
from mcward.cli.datapacks import parse_datapack, workspace_path
from mcward.cli.environments import manager, select_compatible, start_environments
from mcward.cli.reporters import github, live
from mcward.cli.reports import parse_coverage_report, report_session
from mcward.cli.ui import console

from .plugin import TestFunction

pass_project = click.make_pass_decorator(Project)


@beet.command()
@pass_project
@click.option(
    "--version",
    "-v",
    "versions",
    multiple=True,
    help="Minecraft version(s) to test on.",
)
@click.option(
    "--reporter",
    type=click.Choice(["live", "github"]),
    default="live",
    help="Result output: interactive live display, or GitHub Actions annotations.",
)
@click.option(
    "--coverage",
    is_flag=True,
    help="Record which function commands run and report line coverage.",
)
@click.option(
    "--coverage-report",
    "coverage_reports",
    multiple=True,
    metavar="FORMAT[:PATH]",
    help="Write coverage as 'lcov' or 'html', with an optional path (repeatable); "
    "implies --coverage.",
)
@click.option(
    "--junit-xml",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write test results as JUnit XML.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="List every test and coverage row instead of collapsing large runs.",
)
@click.argument("selector", default="*:*")
def test(
    project: Project,
    versions: tuple[str, ...],
    reporter: str,
    coverage: bool,
    coverage_reports: tuple[str, ...],
    junit_xml: Path | None,
    verbose: bool,
    selector: str,
) -> None:
    """Build the current project and run its tests."""
    specs = [parse_coverage_report(value) for value in coverage_reports]
    with message_fence("Building and testing project..."):
        session = test_project(
            project,
            versions=versions,
            reporter=reporter,
            selector=selector,
            coverage=coverage or bool(specs),
            coverage_specs=specs,
            junit_xml=junit_xml,
            verbose=verbose,
        )

    if session.failed:
        sys.exit(1)


def test_project(
    project: Project,
    versions: Sequence[str] = (),
    reporter: str = "live",
    selector: str = "*:*",
    coverage: bool = False,
    coverage_specs: Sequence[tuple[str, Path]] = (),
    junit_xml: Path | None = None,
    verbose: bool = False,
) -> TestSession:
    """Build the beet project and run its tests, returning the session.

    Coverage resolves against the build output, so reports render while the
    built pack still exists.
    """
    # Loaded from the working directory on purpose: touching project.directory
    # here would resolve and cache the config before _build_pack overrides it
    ignores = CoverageIgnores.load()
    with TemporaryDirectory() as directory:
        pack, sources = _build_pack(project, Path(directory))
        session = _run_tests(pack, sources, versions, selector, reporter, coverage, verbose)
        report_session(session, [pack], coverage_specs, junit_xml, verbose, selector, ignores)
        return session


def _build_pack(project: Project, directory: Path) -> tuple[Path, dict[str, Path]]:
    """Build the project and map test ids to their sources if available."""
    with (
        project.override("require[] = mcward.beet.plugin"),
        ProjectBuilder(project, root=True).build() as ctx,
    ):
        sources = {
            name: Path(file.source_path)
            for name, file in ctx.data[TestFunction].items()
            if file.source_path
        }
        pack = ctx.data.save(path=directory / (ctx.project_id or "datapack"), zipped=True)
        return pack, sources


def _run_tests(
    pack: Path,
    sources: dict[str, Path],
    versions: Sequence[str],
    selector: str,
    reporter: str,
    coverage: bool,
    verbose: bool,
) -> TestSession:
    """Run the built pack's tests on the selected versions, mirroring mcward test."""
    datapack = parse_datapack(pack)
    selected = versions or select_compatible(datapack.min_format, datapack.max_format)

    def resolve(folder: str, resource: str) -> str | None:
        if folder != "test" or resource not in sources:
            return None
        return workspace_path(sources[resource])

    try:
        envs = start_environments([manager.get(v) for v in selected])
        console.print()
        run = github.run if reporter == "github" else live.run
        return run([pack], envs, selector, coverage=coverage, verbose=verbose, resolve=resolve)
    except WardError as e:
        raise click.ClickException(str(e)) from e
