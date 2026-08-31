"""The list command."""

import rich_click as click

from mcward import Version

from ..environments import curate_versions, manager
from ..ui import console


@click.command(name="list")
@click.option("--remote", is_flag=True, help="Show all available versions from remote.")
@click.pass_context
def list_versions(ctx: click.Context, remote: bool) -> None:
    """List installed Minecraft versions, or all available versions with --remote."""
    installed = manager.list_installed()
    if remote:
        _print_remote(installed, manager.list_available())
    else:
        _print_installed(installed, ctx.command_path)


def _print_installed(installed: list[Version], command_path: str) -> None:
    console.print("\n[bold]Installed Versions[/]:")
    if not installed:
        console.print("  [dim]No versions installed[/dim]")
    for version in installed:
        _print_version(version)

    console.print(f"\n[dim]To see available versions, use: [blue]{command_path} --remote[/]\n")


def _print_remote(installed: list[Version], available: list[Version]) -> None:
    """Print the curated remote versions, marking installed ones."""
    available_names = {v.name for v in available}
    installed_names = {v.name for v in installed}
    curated = curate_versions(available)

    count = len(installed)
    console.print(f"\n[bold]Available Versions[/] [dim]({count} installed)[/]:", highlight=False)

    # Locally installed versions unknown to the registry (e.g. dev builds)
    for version in installed:
        if version.name not in available_names:
            _print_version(version, color="yellow")

    labels = _version_labels(curated)
    for version in curated[:10]:
        color, marker = ("green", "✓") if version.name in installed_names else ("blue", "○")
        _print_version(version, marker, color, labels.get(version, ""))

    console.print(
        "\n[dim]Showing curated list. Full list: https://modrinth.com/mod/ward/versions[/]\n"
    )


def _version_labels(curated: list[Version]) -> dict[Version, str]:
    """Label the newest release as latest and the newest snapshot as snapshot."""
    labels = {}
    if latest := max((v for v in curated if not v.is_snapshot), default=None):
        labels[latest] = "latest"
    if snapshot := max((v for v in curated if v.is_snapshot), default=None):
        labels[snapshot] = "snapshot"
    return labels


def _print_version(
    version: Version,
    marker: str = "✓",
    color: str = "green",
    label: str = "",
) -> None:
    label = f" [dim]({label})[/]" if label else ""
    console.print(f"  [bold {color}]{marker}[/] {version.name}{label}", highlight=False)
