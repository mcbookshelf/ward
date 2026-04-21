"""List command - show available and installed versions."""

import rich_click as click

from mcward import EnvironmentManager, Version

from ..utils import console, curate_versions


@click.command(name="list")
@click.option("--remote", is_flag=True, help="Show all available versions from remote.")
def list_versions(remote: bool) -> None:
    """List installed Minecraft versions, or all available versions with --remote."""
    manager = EnvironmentManager()
    installed = manager.list_installed()
    if not remote:
        console.print("\n[bold]Installed Versions[/]:")
        if not installed:
            console.print("  [dim]No versions installed[/dim]")
        for v in installed:
            _print_version(v)
        console.print("\n[dim]To see available versions, use: [blue]mcward list --remote[/]\n")

    else:
        available = manager.list_available()
        available_names = {v.name for v in available}
        installed_names = {v.name for v in installed}

        curated = curate_versions(available)
        snapshot = max(curated, default=None)
        latest = max((v for v in curated if not v.is_snapshot), default=None)

        i = len(installed)
        console.print(f"\n[bold]Available Versions[/] [dim]({i} installed)[/]:", highlight=False)

        for v in installed:
            if v.name not in available_names:
                _print_version(v, color="yellow")

        for v in curated[:10]:
            color, marker = ("green", "✓") if v.name in installed_names else ("blue", "○")
            label = "latest" if v == latest else "snapshot" if v == snapshot else ""
            _print_version(v, marker, color, label)

        console.print("\n[dim]Showing curated list. Full list: https://modrinth.com/mod/ward/versions[/]\n")


def _print_version(
    version: Version,
    marker: str = "✓",
    color: str = "green",
    label: str = "",
) -> None:
    """Print a version entry to the console."""
    label = f" [dim]({label})[/]" if label else ""
    console.print(f"  [bold {color}]{marker}[/] {version.name}{label}", highlight=False)
