"""Test command - run datapack tests."""

from pathlib import Path

import rich_click as click

from ..utils import console


@click.command()
@click.option(
    "--version",
    "-v",
    "version_name",
    help="Minecraft version to use",
)
@click.option(
    "--packs",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Datapack directories to test",
)
@click.argument("selector", default="*:*")
@click.argument("version", required=False)
def test(version_name: str, packs: tuple[Path, ...], selector: str) -> None:
    """Run datapack tests."""
    # TRY TO GUESS VERSION FROM PACK METADATA
    # IF MULTIPLE POSSIBLE VERSIONS, PROPOSE USER SELECTION (questionary?) or just show a warning?
