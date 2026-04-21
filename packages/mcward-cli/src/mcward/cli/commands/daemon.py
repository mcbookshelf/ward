"""Daemon commands - start, stop, and status."""

from concurrent.futures import ThreadPoolExecutor, as_completed

import rich_click as click
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mcward import (
    EnvironmentManager,
    InstalledEnvironment,
    RunningEnvironment,
    UninstalledEnvironment,
)

from ..utils import (
    console,
    get_environment,
    note,
    select_installed,
    select_running,
    success,
    warning,
)


@click.command()
@click.argument("version", required=False)
def start(version: str | None) -> None:
    """Start the Ward daemon for a specific version."""
    manager = EnvironmentManager()
    ver = version or select_installed("Select a version to start:", manager)
    env = get_environment(manager, ver)
    name = env.version.name

    if isinstance(env, UninstalledEnvironment):
        with console.status(f"Downloading version {name}"):
            env = env.install()
    if isinstance(env, InstalledEnvironment):
        with console.status(f"Starting version {name}"):
            env = env.start()
            success(f"Started version {name} {env.running}")
            return

    warning(f"Version {name} is already running {env.running}")


@click.command()
@click.argument("version", required=False)
@click.option("--all", "-a", is_flag=True, help="Stop all running versions.")
def stop(version: str | None, all: bool = False) -> None:
    """Stop the Ward daemon."""
    manager = EnvironmentManager()
    if not all:
        ver = version or select_running("Select a version to stop:", manager)
        env = get_environment(manager, ver)
        name = env.version.name

        if isinstance(env, RunningEnvironment):
            with console.status(f"Stopping version {name}"):
                env.stop()
                success(f"Stopped version {name}")
                return

        warning(f"Version {name} is not running")

    else:
        running = [manager.get(v.name) for v in manager.list_running()]
        running = [env for env in running if isinstance(env, RunningEnvironment)]

        if not running:
            note("No versions running")
            return

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            tasks = {
                env.version.name: progress.add_task(f"Stopping version {env.version.name}")
                for env in running
            }

            with ThreadPoolExecutor(max_workers=len(running)) as pool:
                for future in as_completed(pool.submit(env.stop) for env in running):
                    env = future.result()
                    progress.update(tasks[env.version.name], completed=1)

        success("Stopped all running versions")


@click.command()
def status() -> None:
    """Show status of running daemons."""
    manager = EnvironmentManager()
    installed = manager.list_installed()
    running = []

    for version in installed:
        env = manager.get(version.name)
        if isinstance(env, RunningEnvironment):
            running.append(env)

    if not running:
        note("No versions running")
        return

    table = Table(title="Running Ward Daemons", box=box.SIMPLE)
    table.add_column("Version", style="")
    table.add_column("PID", style="dim")
    table.add_column("Port", style="dim")
    table.add_column("Status", style="")

    for env in running:
        try:
            env.status()
            state = "[green bold]✓[/] Ready"
        except Exception:
            state = "[red bold]✗[/] No response"

        table.add_row(
            env.version.name,
            str(env.running.pid),
            str(env.running.port),
            state,
        )

    console.print("", table)
