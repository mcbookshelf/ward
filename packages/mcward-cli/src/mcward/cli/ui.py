"""Terminal primitives: the shared console, print helpers, and prompts."""

import io
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from rich.console import Console

for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        _stream.reconfigure(errors="replace")

console = Console()

_STYLE = [
    ("qmark", "ansiblue bold"),
    ("question", "nobold"),
    ("answer", "ansiblue nobold"),
    ("pointer", "ansiblue bold"),
    ("highlighted", "ansiblue"),
    ("instruction", "dim"),
    ("disabled", "dim italic"),
]


@dataclass(frozen=True)
class Option:
    """A selectable entry: its title, a dimmed hint after it, and the value it yields."""

    title: str
    hint: str = ""
    value: str | None = None


def print_note(message: str) -> None:
    console.print(f"[dim]{message}[/]", highlight=False)


def print_success(message: str) -> None:
    console.print(f"[green]✓ {message}[/]", highlight=False)


def print_warning(message: str) -> None:
    console.print(f"[yellow]{message}[/]", highlight=False)


def confirm(message: str, default: bool = False) -> bool:
    """Ask for a yes/no answer, treating a cancelled prompt as no."""
    import questionary  # deferred: prompts are rare and the import costs ~0.15s

    style = questionary.Style(_STYLE)
    return bool(questionary.confirm(message, default=default, style=style).ask())


def select(message: str, options: Sequence[str | Option]) -> str:
    """Show a selection prompt; a cancelled prompt exits cleanly."""
    import questionary

    choices = []
    for option in options:
        if isinstance(option, str):
            choices.append(option)
            continue
        title = [("", option.title), ("dim", f" {option.hint}")] if option.hint else option.title
        choices.append(questionary.Choice(title, value=option.value or option.title))
    answer = questionary.select(message, choices, style=questionary.Style(_STYLE)).ask()
    if answer is None:
        sys.exit(0)
    return answer
