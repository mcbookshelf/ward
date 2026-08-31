"""The install and clean commands."""

import rich_click as click

from mcward import RunningEnvironment, UninstalledEnvironment

from ..environments import get_environment, select_available, select_installed
from ..ui import confirm, console, print_success, print_warning


@click.command()
@click.argument("version", required=False)
@click.option("--force", is_flag=True, help="Reinstall even if already installed")
def install(version: str | None, force: bool) -> None:
    """Install a Minecraft version."""
    env = get_environment(version or select_available("Select a version to install:"))
    if not isinstance(env, UninstalledEnvironment):
        if not force:
            print_warning(f"Version {env.version.name} is already installed")
            return
        if isinstance(env, RunningEnvironment):
            with console.status(f"Stopping version {env.version.name}"):
                env = env.stop()
                print_success(f"Stopped version {env.version.name}")
        env = env.uninstall()

    with console.status(f"Installing version {env.version.name}"):
        env.install()
        print_success(f"Installed version {env.version.name}")


@click.command()
@click.argument("version", required=False)
def clean(version: str | None) -> None:
    """Remove an installed version."""
    env = get_environment(version or select_installed("Select a version to remove:"))
    if isinstance(env, UninstalledEnvironment):
        print_warning(f"Version {env.version.name} is not installed")
        return
    if isinstance(env, RunningEnvironment):
        with console.status(f"Stopping version {env.version.name}"):
            env = env.stop()
            print_success(f"Stopped version {env.version.name}")

    if confirm(f"Remove version {env.version.name}?"):
        env.uninstall()
        print_success(f"Removed version {env.version.name}")
