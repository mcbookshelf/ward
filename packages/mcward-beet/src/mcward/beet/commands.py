"""The beet test command: build the current project and run its tests with Ward."""

import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from beet import Project
from beet.toolchain.cli import beet, error_handler, message_fence
from beet.toolchain.project import ProjectBuilder
from mcward import TestSession
from mcward.cli.datapacks import parse_datapack, workspace_path
from mcward.cli.reports import parse_coverage_report
from mcward.cli.session import run_session
from mcward.cli.watch import watch as watch_tests

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
    "--coverage-min",
    type=click.FloatRange(0, 100),
    default=None,
    metavar="PERCENT",
    help="Fail the run when coverage is below this percentage; implies --coverage.",
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
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    help="Build and run again when a project file changes, with keys to rerun or filter.",
)
@click.option(
    "--world",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Run the tests in a copy of this world save instead of a flat world.",
)
@click.argument("selector", default="*:*")
def test(
    project: Project,
    versions: tuple[str, ...],
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
    """Build the current project and run its tests."""
    if watch and reporter == "github":
        raise click.UsageError("--watch only works with the live reporter")

    specs = [parse_coverage_report(value) for value in coverage_reports]
    chosen = list(versions)

    def run(selector: str) -> TestSession:
        session = test_project(
            project,
            versions=chosen,
            reporter=reporter,
            selector=selector,
            coverage=coverage,
            coverage_specs=specs,
            coverage_min=coverage_min,
            junit_xml=junit_xml,
            verbose=verbose,
            world=world,
        )
        # Ask for the versions once, not on every rerun
        chosen[:] = [version.name for version in session.versions]
        return session

    if watch:
        watch_tests(
            lambda selector: rebuild(project, run, selector),
            selector,
            [project.directory],
            ignore=project_ignore(project),
        )
        return

    with message_fence("Building and testing project..."):
        session = run(selector)

    if session.failed:
        sys.exit(1)


def rebuild(project: Project, run: Callable[[str], TestSession], selector: str) -> None:
    """Reload the project config, then build and test; a failed build is shown, not raised."""
    project.reset()
    with error_handler(format_padding=1):
        run(selector)


def project_ignore(project: Project) -> Callable[[Path], bool]:
    """The files a change of which does not rebuild: beet's cache, hidden and temporary files."""
    root = project.directory.resolve()
    cache = project.cache.path.resolve()

    def ignored(path: Path) -> bool:
        if path.is_relative_to(cache):
            return True
        parts = path.relative_to(root).parts if path.is_relative_to(root) else path.parts
        return path.suffix == ".tmp" or any(part.startswith(".") for part in parts)

    return ignored


def test_project(
    project: Project,
    versions: Sequence[str] = (),
    reporter: str = "live",
    selector: str = "*:*",
    coverage: bool = False,
    coverage_specs: Sequence[tuple[str, Path]] = (),
    coverage_min: float | None = None,
    junit_xml: Path | None = None,
    verbose: bool = False,
    world: Path | None = None,
) -> TestSession:
    """Build the beet project and run its tests, returning the session.

    Coverage resolves against the build output, so reports render while the
    built pack still exists.
    """
    with TemporaryDirectory() as directory:
        pack, sources = _build_pack(project, Path(directory))

        def resolve(folder: str, resource: str) -> str | None:
            if folder != "test" or resource not in sources:
                return None
            return workspace_path(sources[resource])

        return run_session(
            [parse_datapack(pack)],
            versions=versions,
            reporter=reporter,
            selector=selector,
            coverage=coverage,
            coverage_specs=coverage_specs,
            coverage_min=coverage_min,
            junit_xml=junit_xml,
            verbose=verbose,
            resolve=resolve,
            world=world,
        )


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
