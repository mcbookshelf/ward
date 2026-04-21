"""Command-line interface for Ward."""

import sys

import rich_click as click

from .commands import clean, install, list_versions, start, status, stop, test
from .utils import console

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.THEME = "quartz2-slim"


class DefaultCommandGroup(click.RichGroup):
    """Click group that routes to test command by default."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        """Parse args, routing to test command if no subcommand specified."""
        if args and args[0] in self.commands:
            return super().parse_args(ctx, args)
        if args and args[0] in ("-h", "--help"):
            return super().parse_args(ctx, args)
        return super().parse_args(ctx, ["test"] + args)


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
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)
    except Exception:
        console.print_exception()
        sys.exit(1)
