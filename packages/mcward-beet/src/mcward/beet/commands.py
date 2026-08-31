"""The beet test command: build the current project and run its tests with Ward.

Importing this module (beet does it through the ``beet``/``commands`` entry
point) registers the command on the beet CLI group.
"""

import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from beet import Project
from beet.toolchain.cli import beet, message_fence
from beet.toolchain.project import ProjectBuilder
from mcward import TestSession, WardError
from mcward.cli.datapacks import parse_datapack, workspace_path
from mcward.cli.environments import manager, select_compatible, start_environments
from mcward.cli.reporters import github, live
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
@click.argument("selector", default="*:*")
def test(project: Project, versions: tuple[str, ...], reporter: str, selector: str) -> None:
    """Build the current project and run its tests."""
    with message_fence("Building and testing project..."):
        session = test_project(project, versions=versions, reporter=reporter, selector=selector)

    if session.failed:
        sys.exit(1)


def test_project(
    project: Project,
    versions: Sequence[str] = (),
    reporter: str = "live",
    selector: str = "*:*",
) -> TestSession:
    """Build the beet project and run its tests, returning the session.

    The programmatic counterpart of the ``beet test`` command. It shares the
    build, the version selection and the reporters, but never exits the process.
    """
    with TemporaryDirectory() as directory:
        pack, sources = _build_pack(project, Path(directory))
        return _run_tests(pack, sources, versions, selector, reporter)


def _build_pack(project: Project, directory: Path) -> tuple[Path, dict[str, Path]]:
    """Build the project into the directory; also map test ids to their sources.

    The built pack lives in a temporary directory, so annotations need the
    original files the tests came from; beet records them as source paths
    (plugin-generated tests have none).
    """
    # Requiring the plugin here loads the test/ folder even when the project does not
    # The plugin is idempotent, so requiring it twice is harmless
    with project.override("require[] = mcward.beet.plugin"):
        with ProjectBuilder(project, root=True).build() as ctx:
            sources = {
                name: Path(file.source_path)
                for name, file in ctx.data[TestFunction].items()
                if file.source_path
            }
            return ctx.data.save(
                path=directory / (ctx.project_id or "datapack"),
                zipped=True,
            ), sources


def _run_tests(
    pack: Path,
    sources: dict[str, Path],
    versions: Sequence[str],
    selector: str,
    reporter: str,
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
        if reporter == "github":
            return github.run([pack], envs, selector, resolve=resolve)
        return live.run([pack], envs, selector, resolve=resolve)
    except WardError as e:
        raise click.ClickException(str(e)) from e
