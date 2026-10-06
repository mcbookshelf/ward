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

    return [parse_datapack(p) for p in sorted(paths, key=_stacking_key) if _is_datapack(p)]


def parse_datapack(path: Path) -> DataPack:
    """Parse a datapack's pack.mcmeta for format range (directory or zip)."""
    try:
        pack = json.loads(_read_mcmeta(path))["pack"]
        return DataPack(path, _major_format(pack["min_format"]), _major_format(pack["max_format"]))
    except KeyError as e:
        raise click.ClickException(f"Invalid pack.mcmeta in {path}: missing {e}") from e
    except Exception as e:
        raise click.ClickException(f"Invalid pack.mcmeta in {path}: {e}") from e


def format_range(datapacks: Sequence[DataPack]) -> tuple[int, int]:
    """The pack formats that every pack supports."""
    strictest = max(datapacks, key=lambda datapack: datapack.min_format)
    loosest = min(datapacks, key=lambda datapack: datapack.max_format)
    if strictest.min_format > loosest.max_format:
        raise click.ClickException(
            f"Datapacks have disjoint pack format ranges: {strictest.path.name} needs "
            f">= {strictest.min_format} but {loosest.path.name} caps at {loosest.max_format}"
        )
    return strictest.min_format, loosest.max_format


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
        files = (workspace_path(pack / relative) for pack in reversed(datapacks))
        return next((file for file in files if file), None)

    return resolve


def workspace_path(file: Path) -> str | None:
    """The file relative to the workspace root, or None when outside of it."""
    workspace = Path(os.environ.get("GITHUB_WORKSPACE") or Path.cwd()).resolve()
    file = file.resolve()
    if file.is_file() and file.is_relative_to(workspace):
        return file.relative_to(workspace).as_posix()
    return None


def _is_datapack(path: Path) -> bool:
    """A directory or a zip with a pack.mcmeta and a data folder at its root.

    The data folder tells a datapack from a resource pack, which has the same pack.mcmeta.
    """
    if path.is_dir():
        return (path / "pack.mcmeta").is_file() and (path / "data").is_dir()
    if path.suffix == ".zip" and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            return "pack.mcmeta" in names and any(name.startswith("data/") for name in names)
    return False


def _stacking_key(path: Path) -> tuple[str, Path]:
    """The file name the pack deploys under: a directory is zipped, so it gains the extension."""
    return f"{path.name.removesuffix('.zip')}.zip", path


def _major_format(value: int | list[int]) -> int:
    """A pack format is a number, or a [major, minor] pair."""
    if isinstance(value, int):
        return value
    if isinstance(value, list) and value:
        return value[0]
    raise ValueError(f"unexpected pack format {value!r}")


def _read_mcmeta(path: Path) -> str:
    if path.is_file():  # Zipped datapack
        with zipfile.ZipFile(path) as archive:
            return archive.read("pack.mcmeta").decode("utf-8")
    return (path / "pack.mcmeta").read_text(encoding="utf-8")
