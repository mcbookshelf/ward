"""The bench command."""

import json
import sys
from pathlib import Path

import rich_click as click

from mcward import BenchReport, WardError, run_bench

from ..datapacks import DEFAULT_PATTERNS, discover_datapacks, format_range
from ..environments import manager, select_compatible, start_environments
from ..reporters.bench import render_report, render_summary
from ..ui import console


@click.command()
@click.option(
    "--pack",
    "-p",
    "packs",
    multiple=True,
    help="Datapack paths or glob patterns",
)
@click.option(
    "--version",
    "-v",
    "versions",
    multiple=True,
    help="Minecraft version(s) to bench on, one after the other",
)
@click.option(
    "--setup",
    multiple=True,
    metavar="COMMAND",
    help="Run once before each benchmarked command (repeatable)",
)
@click.option(
    "--prepare",
    multiple=True,
    metavar="COMMAND",
    help="Run before each timed batch, outside of the timing (repeatable)",
)
@click.option(
    "--batch",
    type=click.IntRange(min=1),
    default=None,
    help="Runs per sample. By default the warmup picks it",
)
@click.option(
    "--json",
    "json_path",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Write the results, with every sample, to a JSON file",
)
@click.argument("commands", nargs=-1, required=True)
def bench(
    versions: tuple[str, ...],
    packs: tuple[str, ...],
    setup: tuple[str, ...],
    prepare: tuple[str, ...],
    batch: int | None,
    json_path: Path | None,
    commands: tuple[str, ...],
) -> None:
    """Time commands on a test server and compare them."""
    datapacks = discover_datapacks(packs if packs else DEFAULT_PATTERNS)
    if not datapacks and not versions:
        raise click.ClickException("Datapack not found. Without a pack, give a version with -v")

    selected = versions or select_compatible(*format_range(datapacks))
    paths = [datapack.path for datapack in datapacks]
    results = []
    failed = False

    try:
        envs = start_environments([manager.get(v) for v in selected])
        for env in envs:
            console.print()
            if len(envs) > 1:
                console.print(f"[bold]{env.version.name}[/]", highlight=False)

            reports: list[BenchReport] = []
            with console.status("Running the benchmarks"):
                for report in run_bench(paths, env, commands, setup, prepare, batch or 0):
                    reports.append(report)
                    for line in render_report(len(reports), report):
                        console.print(line, highlight=False)
                    console.print()

            for line in render_summary(reports):
                console.print(line, highlight=False)

            failed = failed or any(report.failed for report in reports)
            results += [_to_json(env.version.name, report) for report in reports]
    except WardError as e:
        if "Unknown command" in str(e):
            raise click.ClickException(
                "This server runs a Ward mod that cannot bench. "
                "Reinstall it with: mcward install <version> --force"
            ) from e
        raise click.ClickException(str(e)) from e

    if json_path:
        json_path.write_text(json.dumps({"results": results}, indent=2) + "\n", encoding="utf-8")
    if failed:
        sys.exit(1)


def _to_json(version: str, report: BenchReport) -> dict:
    """One result. Times are nanoseconds per run."""
    data: dict = {"version": version, "command": report.name}
    if report.failed:
        return data | {"failed": report.failed}
    return data | {
        "mean": report.mean,
        "stddev": report.stddev,
        "median": report.median,
        "min": report.fastest,
        "p95": report.p95,
        "batch": report.batch,
        "commands": report.commands,
        "allocated": report.allocated,
        "error": report.error,
        "times": list(report.times),
    }
