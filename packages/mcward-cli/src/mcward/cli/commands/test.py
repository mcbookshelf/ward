"""The test command."""

import sys

import rich_click as click

from mcward import WardError

from ..datapacks import DEFAULT_PATTERNS, discover_datapacks
from ..environments import manager, select_compatible, start_environments
from ..reporters import github, live
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
@click.argument("selector", default="*:*")
def test(
    versions: tuple[str, ...],
    packs: tuple[str, ...],
    reporter: str,
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

    run = github.run if reporter == "github" else live.run
    try:
        envs = start_environments([manager.get(v) for v in selected])
        console.print()
        session = run(paths, envs, selector)
        if session.failed:
            sys.exit(1)
    except WardError as e:
        raise click.ClickException(str(e)) from e
