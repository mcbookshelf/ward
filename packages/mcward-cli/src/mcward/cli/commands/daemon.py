"""The start, stop and status commands."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import cast

import rich_click as click
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mcward import (
    InstalledEnvironment,
    ProcessError,
    RunningEnvironment,
    UninstalledEnvironment,
)

from ..environments import get_environment, manager, select_installed, select_running
from ..ui import console, print_note, print_success, print_warning


@click.command()
@click.argument("version", required=False)
def start(version: str | None) -> None:
    """Start the Ward daemon for a specific version."""
    env = get_environment(version or select_installed("Select a version to start:"))
    if isinstance(env, UninstalledEnvironment):
        with console.status(f"Installing version {env.version.name}"):
            env = env.install()
            print_success(f"Installed version {env.version.name}")
    if isinstance(env, InstalledEnvironment):
        with console.status(f"Starting version {env.version.name}"):
            env = env.start()
            print_success(f"Started version {env.version.name} {env.process}")
            return
    print_warning(f"Version {env.version.name} is already running {env.process}")


@click.command()
@click.argument("version", required=False)
@click.option("--all", "-a", is_flag=True, help="Stop all running versions.")
def stop(version: str | None, all: bool = False) -> None:
    """Stop the Ward daemon."""
    if not all:
        env = get_environment(version or select_running("Select a version to stop:"))
        if isinstance(env, RunningEnvironment):
            with console.status(f"Stopping version {env.version.name}"):
                env.stop()
                print_success(f"Stopped version {env.version.name}")
                return
        print_warning(f"Version {env.version.name} is not running")
        return

    envs = _running_environments()
    if not envs:
        print_note("No versions running")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        tasks = {
            env.version.name: progress.add_task(f"Stopping version {env.version.name}")
            for env in envs
        }

        with ThreadPoolExecutor(max_workers=len(envs)) as pool:
            for future in as_completed(pool.submit(env.stop) for env in envs):
                env = future.result()
                progress.remove_task(tasks[env.version.name])

    print_success("Stopped all running versions")


@click.command()
def status() -> None:
    """Show status of running daemons."""
    envs = _running_environments()
    if not envs:
        print_note("No versions running")
        return

    table = Table(title="Running Ward Daemons", box=box.SIMPLE)
    table.add_column("Version", style="")
    table.add_column("PID", style="dim")
    table.add_column("Port", style="dim")
    table.add_column("Status", style="")

    for env in envs:
        try:
            env.status()
            state = "[green bold]✓[/] Ready"
        except ProcessError:
            state = "[red bold]✗[/] No response"
        table.add_row(env.version.name, str(env.process.pid), str(env.process.port), state)

    console.print("", table)


def _running_environments() -> list[RunningEnvironment]:
    return [cast(RunningEnvironment, manager.get(v.name)) for v in manager.list_running()]
