"""Consolidated output formatting using Rich."""

import sys
from typing import Any

import questionary
from questionary import Style
from questionary.prompts.common import Choice
from rich.console import Console

from mcward import Environment, EnvironmentManager, Version, VersionNotFoundError

console = Console()

QUESTIONARY_STYLE = Style(
    [
        ("qmark", "ansiblue bold"),    # token in front of the question
        ("question", "nobold"),        # question text
        ("answer", "ansiblue nobold"), # submitted answer text behind the question
        ("pointer", "ansiblue bold"),  # pointer used in select and checkbox prompts
        ("highlighted", "ansiblue"),   # pointed-at choice in select and checkbox prompts
        ("instruction", "dim"),        # user instructions for select, rawselect, checkbox
        ("disabled", "dim italic"),    # disabled choices for select and checkbox prompts
    ]
)


def note(message: str) -> None:
    """Print a note message."""
    console.print(f"[dim]{message}[/]", highlight=False)


def success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓ {message}[/]", highlight=False)


def warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]{message}[/]", highlight=False)


def confirm(message: str, default: bool = False) -> bool:
    """Show a yes/no confirmation prompt."""
    result = questionary.confirm(message, default=default, style=QUESTIONARY_STYLE).ask()
    return result if result is not None else False


def select(message: str, choices: list[Any], **kwargs) -> Any:
    """Show a selection prompt."""
    return questionary.select(message, choices=choices, style=QUESTIONARY_STYLE, **kwargs).ask()


def get_environment(manager: EnvironmentManager, version: str) -> Environment:
    """Get the environment for the given version."""
    try:
        return manager.get(version)
    except VersionNotFoundError as e:
        console.print(f"[red]{str(e)}[/]", highlight=False)
        sys.exit(1)


def curate_versions(versions: list[Version]) -> list[Version]:
    """Curate a list of versions, removing previous snapshot versions."""
    seen = set()
    curated = []
    for v in versions:
        k = (v.year, v.major)
        if v.is_snapshot and k in seen:
            continue
        curated.append(v)
        seen.add(k)
    return curated


def select_installed(message: str, manager: EnvironmentManager) -> str:
    """Select an installed version."""
    versions = manager.list_installed()
    if not versions:
        console.print("[dim]No versions installed[/]")
        sys.exit(1)
    if len(versions) == 1:
        return versions[0].name
    return select(message, [v.name for v in versions]) or sys.exit(0)


def select_running(message: str, manager: EnvironmentManager) -> str:
    """Select a running version."""
    versions = manager.list_running()
    if not versions:
        console.print("[dim]No versions running[/]")
        sys.exit(1)
    if len(versions) == 1:
        return versions[0].name
    return select(message, [v.name for v in versions]) or sys.exit(0)


def select_available(message: str, manager: EnvironmentManager) -> str:
    """Select an available version."""
    curated = curate_versions(manager.list_available())
    snapshot = max(curated, default=None)
    latest = max((v for v in curated if not v.is_snapshot), default=None)

    if not curated:
        console.print("[dim]No versions available[/]")
        sys.exit(1)

    if len(curated) == 1:
        return curated[0].name

    choices = []
    for v in curated:
        label = "latest" if v == latest else "snapshot" if v == snapshot else ""
        choices.append(Choice([("", v.name), ("dim", f" ({label})")] if label else v.name))

    return select(message, choices) or sys.exit(0)
