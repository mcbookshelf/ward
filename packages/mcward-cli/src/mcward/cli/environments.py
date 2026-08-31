"""Environment selection and startup shared by the commands."""

from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from itertools import groupby

import rich_click as click
from questionary.prompts.common import Choice
from rich.progress import Progress, SpinnerColumn, TextColumn

from mcward import (
    Environment,
    EnvironmentManager,
    InstalledEnvironment,
    RunningEnvironment,
    UninstalledEnvironment,
    Version,
    VersionNotFoundError,
)

from .ui import console, print_note, print_success, select

manager = EnvironmentManager()


def curate_versions(versions: Iterable[Version]) -> list[Version]:
    """Keep all releases but only the newest snapshot of each (year, major) line."""
    seen = set()
    curated = []
    for v in versions:
        k = (v.year, v.major)
        if v.is_snapshot and k in seen:
            continue
        curated.append(v)
        seen.add(k)
    return curated


def get_environment(version: str) -> Environment:
    try:
        return manager.get(version)
    except VersionNotFoundError as e:
        raise click.ClickException(str(e)) from e


def select_installed(message: str) -> str:
    """Prompt for an installed version, skipping the prompt when only one fits."""
    versions = manager.list_installed()
    if not versions:
        raise click.ClickException("No versions installed")
    return versions[0].name if len(versions) == 1 else select(message, [v.name for v in versions])


def select_running(message: str) -> str:
    """Prompt for a running version, skipping the prompt when only one fits."""
    versions = manager.list_running()
    if not versions:
        raise click.ClickException("No versions running")
    return versions[0].name if len(versions) == 1 else select(message, [v.name for v in versions])


def select_available(message: str) -> str:
    """Prompt for a version to install, flagging the latest and the snapshot."""
    curated = curate_versions(manager.list_available())
    if not curated:
        raise click.ClickException("No versions available")

    choices = []
    snapshot = next((v for v in curated if v.is_snapshot), None)
    latest = next((v for v in curated if not v.is_snapshot), None)
    for v in curated:
        title = [("", v.name)]
        if v == latest:
            title.append(("dim", " (latest)"))
        elif v == snapshot:
            title.append(("dim", " (snapshot)"))
        choices.append(Choice(title))

    return select(message, choices)


def select_compatible(min_format: int, max_format: int) -> list[str]:
    """The versions to test, one per major line, asking when several qualify."""
    compatible = manager.list_compatible(min_format, max_format)
    if not compatible:
        err = f"No compatible versions found for pack format range {min_format}..{max_format}"
        raise click.ClickException(err)

    lines = groupby(compatible, key=lambda v: (v.year, v.major))
    versions = [next(group) for _, group in lines]
    if len(versions) == 1:
        return [versions[0].name]

    print_note("Pack format range supports multiple major versions")

    choices = [Choice(title=[("", "Use all versions "), ("dim", "(Recommended)")], value="all")]
    choices.extend(Choice(title=f"Use {v.name} only", value=v.name) for v in versions)
    name = select("Select version strategy:", choices)

    return [v.name for v in versions if name == "all" or v.name == name]


def start_environments(envs: Sequence[Environment]) -> list[RunningEnvironment]:
    """Install and start environments concurrently."""
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        with ThreadPoolExecutor(max_workers=len(envs)) as executor:
            return list(executor.map(lambda env: _start_environment(env, progress), envs))


def _start_environment(env: Environment, progress: Progress) -> RunningEnvironment:
    """Start a single environment, reporting steps to the shared progress."""
    if isinstance(env, UninstalledEnvironment):
        task = progress.add_task(f"Installing version {env.version.name}", total=None)
        env = env.install()
        progress.remove_task(task)
        print_success(f"Installed version {env.version.name}")
    if isinstance(env, InstalledEnvironment):
        task = progress.add_task(f"Starting version {env.version.name}", total=None)
        env = env.start()
        progress.remove_task(task)
        print_success(f"Started version {env.version.name} {env.process}")
    return env
