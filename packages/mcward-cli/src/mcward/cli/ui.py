"""Terminal primitives: the shared console, print helpers, and prompts."""

import io
import sys
from collections.abc import Sequence

import questionary
from questionary import Style
from questionary.prompts.common import Choice
from rich.console import Console

# Windows consoles are not always UTF-8 (cp1252 when piped)
# Symbols like ✓ must degrade to "?" there instead of crashing the print
for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        _stream.reconfigure(errors="replace")

console = Console()

STYLE = Style(
    [
        ("qmark", "ansiblue bold"),  # token in front of the question
        ("question", "nobold"),  # question text
        ("answer", "ansiblue nobold"),  # submitted answer text behind the question
        ("pointer", "ansiblue bold"),  # pointer used in select and checkbox prompts
        ("highlighted", "ansiblue"),  # pointed-at choice in select and checkbox prompts
        ("instruction", "dim"),  # user instructions for select, rawselect, checkbox
        ("disabled", "dim italic"),  # disabled choices for select and checkbox prompts
    ]
)


def print_note(message: str) -> None:
    console.print(f"[dim]{message}[/]", highlight=False)


def print_success(message: str) -> None:
    console.print(f"[green]✓ {message}[/]", highlight=False)


def print_warning(message: str) -> None:
    console.print(f"[yellow]{message}[/]", highlight=False)


def confirm(message: str, default: bool = False) -> bool:
    """Ask for a yes/no answer, treating a cancelled prompt as no."""
    result = questionary.confirm(message, default=default, style=STYLE).ask()
    return result if result is not None else False


def select(message: str, choices: Sequence[str | Choice], **kwargs) -> str:
    """Show a selection prompt; a cancelled prompt exits cleanly."""
    answer = questionary.select(message, choices, style=STYLE, **kwargs).ask()
    if answer is None:
        sys.exit(0)
    return answer
