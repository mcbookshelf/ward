"""Command-line interface for Ward."""

import sys

import rich_click as click

from .commands import clean, install, list_versions, start, status, stop, test
from .ui import console

click.rich_click.TEXT_MARKUP = "rich"
click.rich_click.THEME = "quartz2-slim"


class DefaultCommandGroup(click.RichGroup):
    """Click group that routes to the test command by default."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if not args or self._is_test_invocation(args[0]):
            return super().parse_args(ctx, ["test"] + args)
        return super().parse_args(ctx, args)

    def _is_test_invocation(self, arg: str) -> bool:
        """Whether the first argument is meant for test rather than a subcommand."""
        if arg in self.commands or arg in ("-h", "--help"):
            return False
        return arg.startswith("-") or ":" in arg or "*" in arg


@click.group(
    cls=DefaultCommandGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
    epilog="If no command is provided, [bold]test[/] is executed by default.",
)
def cli() -> None:
    """Ward, testing framework for Minecraft datapacks."""
    pass


cli.add_command(clean)
cli.add_command(install)
cli.add_command(list_versions)
cli.add_command(start)
cli.add_command(status)
cli.add_command(stop)
cli.add_command(test)


def main() -> None:
    try:
        # Click expands globs itself on Windows, which would consume -p patterns
        # discover_datapacks resolves them instead
        cli(windows_expand_args=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)
    except Exception:
        console.print_exception()
        sys.exit(1)
