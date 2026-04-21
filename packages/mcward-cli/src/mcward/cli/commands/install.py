"""Install and clean commands - version management."""

import rich_click as click

from mcward import EnvironmentManager, RunningEnvironment, UninstalledEnvironment

from ..utils import (
    confirm,
    console,
    get_environment,
    select_available,
    select_installed,
    success,
    warning,
)


@click.command()
@click.argument("version", required=False)
@click.option("--force", is_flag=True, help="Reinstall even if already installed")
def install(version: str | None, force: bool) -> None:
    """Install a Minecraft version."""
    manager = EnvironmentManager()
    ver = version or select_available("Select a version to install:", manager)
    env = get_environment(manager, ver)
    name = env.version.name

    if not isinstance(env, UninstalledEnvironment):
        if not force:
            warning(f"Version {name} is already installed")
            return
        if isinstance(env, RunningEnvironment):
            with console.status(f"Stopping version {name}"):
                env = env.stop()
                success(f"Stopped version {name}")
        env = env.uninstall()

    with console.status(f"Installing version {name}"):
        env.install()
        success(f"Installed version {name}")


@click.command()
@click.argument("version", required=False)
def clean(version: str | None) -> None:
    """Remove an installed version."""
    manager = EnvironmentManager()
    ver = version or select_installed("Select a version to remove:", manager)
    env = get_environment(manager, ver)
    name = env.version.name

    if isinstance(env, UninstalledEnvironment):
        warning(f"Version {name} is not installed")
        return
    if isinstance(env, RunningEnvironment):
        with console.status(f"Stopping version {name}"):
            env = env.stop()
            success(f"Stopped version {name}")

    if confirm(f"Remove version {name}?"):
        env.uninstall()
        success(f"Removed version {name}")
