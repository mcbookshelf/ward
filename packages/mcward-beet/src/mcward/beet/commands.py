"""The beet test command: build the current project and run its tests with Ward."""

import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from beet import Project
from beet.core.watch import DirectoryWatcher
from beet.toolchain.cli import beet, error_handler, message_fence
from beet.toolchain.project import ProjectBuilder
from mcward import TestSession, WardConfig
from mcward.cli.datapacks import parse_datapack, workspace_path
from mcward.cli.session import (
    check_watch,
    load_config,
    rerunnable,
    run_session,
    test_options,
)
from mcward.cli.watch import watch as watch_tests
from mcward.cli.writers import is_report_file, parse_coverage_report

from .plugin import TestFunction

pass_project = click.make_pass_decorator(Project)


@beet.command()
@pass_project
@test_options
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
    check_watch(watch, reporter)
    config = load_config(world)
    specs = [parse_coverage_report(value) for value in coverage_reports]

    def run_once(selector: str, versions: Sequence[str]) -> TestSession:
        return test_project(
            project,
            config,
            versions=versions,
            reporter=reporter,
            selector=selector,
            coverage=coverage,
            coverage_specs=specs,
            coverage_min=coverage_min,
            junit_xml=junit_xml,
            verbose=verbose,
        )

    run = rerunnable(versions, run_once)
    if watch:
        ignored = project_ignore(project)
        watch_tests(
            lambda selector: rebuild(project, run, selector),
            selector,
            [project.directory, config.world] if config.world else [project.directory],
            ignore=lambda path: ignored(path) or is_report_file(path, specs, junit_xml),
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
    """The files beet's own watch skips: its caches, the output, .gitignore and the ignore list."""
    root = project.directory.resolve()
    caches = [project.cache.path.resolve(), project.cache.generated.path.resolve()]
    # Only built for its patterns: the same as beet watch, read from .gitignore up the tree
    patterns = DirectoryWatcher(
        root,
        ignore_file=".gitignore",
        ignore_patterns=["__pycache__/", "*.tmp", ".*", *project.ignore],
    ).ignore

    def ignored(path: Path) -> bool:
        if any(path.is_relative_to(cache) for cache in caches):
            return True
        return path.is_relative_to(root) and patterns.match_file(path.relative_to(root))

    return ignored


def test_project(
    project: Project,
    config: WardConfig,
    versions: Sequence[str] = (),
    reporter: str = "live",
    selector: str = "*:*",
    coverage: bool = False,
    coverage_specs: Sequence[tuple[str, Path]] = (),
    coverage_min: float | None = None,
    junit_xml: Path | None = None,
    verbose: bool = False,
) -> TestSession:
    """Build the project and run its tests while the built pack exists for the reports."""
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
            config=config,
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
