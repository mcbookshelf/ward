"""Datapack discovery, pack.mcmeta parsing and resource-to-file resolution."""

import glob
import json
import os
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import rich_click as click

DEFAULT_PATTERNS = [".", "*", "datapacks/*"]

type FileResolver = Callable[[str, str], str | None]

# Registry folders holding .mcfunction files; everything else is JSON
MCFUNCTION_FOLDERS = ("test", "function")


@dataclass(frozen=True)
class DataPack:
    path: Path
    min_format: int
    max_format: int


def discover_datapacks(patterns: Sequence[str]) -> list[DataPack]:
    """Find the datapacks (directories or zips) matching the glob patterns."""
    paths = set()

    for pattern in patterns:
        if (p := Path(pattern)).exists():
            paths.add(p.resolve())
        else:
            matches = glob.glob(pattern, recursive=True, include_hidden=True)
            paths.update(Path(m).resolve() for m in matches)

    return [parse_datapack(p) for p in paths if _is_datapack(p)]


def parse_datapack(path: Path) -> DataPack:
    """Parse a datapack's pack.mcmeta for format range (directory or zip)."""

    def _parse_format(value: int | list[int]) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, list) and value:
            return value[0]
        raise click.ClickException(f"Invalid pack format in {path}")

    try:
        data = json.loads(_read_mcmeta(path))
        pack = data["pack"]
        return DataPack(path, _parse_format(pack["min_format"]), _parse_format(pack["max_format"]))
    except Exception as e:
        raise click.ClickException(str(e)) from e


def pack_resolver(datapacks: Sequence[Path]) -> FileResolver:
    """Resolve resources against the datapack directories themselves.

    Zipped datapacks never resolve: there is no file to point at inside an
    archive, so their failures render without a path.
    """

    def resolve(folder: str, resource: str) -> str | None:
        if ":" not in resource:
            return None
        namespace, path = resource.split(":", 1)
        extension = ".mcfunction" if folder in MCFUNCTION_FOLDERS else ".json"
        relative = f"data/{namespace}/{folder}/{path}{extension}"
        return next((f for pack in datapacks if (f := workspace_path(pack / relative))), None)

    return resolve


def workspace_path(file: Path) -> str | None:
    """The file relative to the workspace root, or None when outside of it."""
    workspace = Path(os.environ.get("GITHUB_WORKSPACE") or Path.cwd()).resolve()
    file = file.resolve()
    if file.is_file() and file.is_relative_to(workspace):
        return file.relative_to(workspace).as_posix()
    return None


def _is_datapack(path: Path) -> bool:
    """A directory with a pack.mcmeta, or a zip carrying one at its root."""
    if path.is_dir():
        return (path / "pack.mcmeta").exists()
    if path.suffix == ".zip" and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return "pack.mcmeta" in archive.namelist()
    return False


def _read_mcmeta(path: Path) -> str:
    if path.is_file():  # Zipped datapack
        with zipfile.ZipFile(path) as archive:
            return archive.read("pack.mcmeta").decode("utf-8")
    return (path / "pack.mcmeta").read_text(encoding="utf-8")
