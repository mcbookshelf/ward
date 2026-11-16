"""The saved world a run starts in: a copy kept in the environment."""

import hashlib
import os
import shutil
import tomllib
from pathlib import Path

from ._constants import WORLD_FILE
from ._exceptions import DeployError, WardError

# The packs under test replace the ones of the save, and the lock belongs to whoever has it open
EXCLUDED = ("datapacks", "session.lock")


def configured_world(directory: Path | None = None) -> Path | None:
    """The ``world`` of the directory's ward.toml, a path relative to that file."""
    file = (directory or Path.cwd()) / "ward.toml"
    try:
        text = file.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        value = tomllib.loads(text).get("world")
    except tomllib.TOMLDecodeError as e:
        raise WardError(f"Invalid {file.name}: {e}") from e

    if value is None:
        return None
    if not isinstance(value, str):
        raise WardError(f"Invalid {file.name}: world must be the path of a world folder")
    return file.parent / value


def check_world(world: Path) -> None:
    if not (world / "level.dat").is_file():
        raise DeployError(f"Not a Minecraft world, it has no level.dat: {world}")


def sync(directory: Path, world: Path | None) -> None:
    """Make the environment's world a copy of the given one, or empty it without one.

    The copy is kept between runs, so the server upgrades an old save once per
    environment. It is made again when a file of the source changes.
    """
    marker = directory / WORLD_FILE
    wanted = None if world is None else _fingerprint(world)
    if _installed(marker) == wanted:
        return

    target = directory / "world"
    marker.unlink(missing_ok=True)
    if target.exists():
        shutil.rmtree(target)
    if world is not None and wanted is not None:
        shutil.copytree(world, target, ignore=lambda folder, _: _excluded(world, folder))
        marker.write_text(wanted, encoding="utf-8")


def _installed(marker: Path) -> str | None:
    try:
        return marker.read_text(encoding="utf-8")
    except OSError:
        return None


def _excluded(world: Path, folder: str) -> tuple[str, ...]:
    return EXCLUDED if Path(folder) == world else ()


def _fingerprint(world: Path) -> str:
    """Changes when the world is another one, or when one of its files does."""
    check_world(world)
    digest = hashlib.sha256(str(world.resolve()).encode())
    for root, dirs, files in os.walk(world):
        if Path(root) == world:
            dirs[:] = [name for name in dirs if name not in EXCLUDED]
            files = [name for name in files if name not in EXCLUDED]
        dirs.sort()
        for name in sorted(files):
            file = Path(root, name)
            stat = file.stat()
            entry = f"{file.relative_to(world).as_posix()}|{stat.st_size}|{stat.st_mtime_ns}\n"
            digest.update(entry.encode())
    return digest.hexdigest()
