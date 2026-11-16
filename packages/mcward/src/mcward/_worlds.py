"""The saved world a run starts in: a copy kept in the environment."""

import hashlib
import os
import shutil
from pathlib import Path

from ._constants import WORLD_FILE
from ._exceptions import DeployError

# The packs under test replace the ones of the save, and the lock belongs to whoever has it open
EXCLUDED = ("datapacks", "session.lock")


def check_world(world: Path) -> None:
    if not (world / "level.dat").is_file():
        raise DeployError(f"Not a Minecraft world, it has no level.dat: {world}")


def sync(directory: Path, world: Path | None) -> None:
    """Copy the world into the environment when its files changed, or empty it."""
    marker = directory / WORLD_FILE
    target = directory / "world"
    # Without a world, an interrupted copy has no marker and would still be loaded
    if world is None:
        _clear(marker, target)
        return

    wanted = _fingerprint(world)
    if _installed(marker) == wanted:
        return
    _clear(marker, target)
    shutil.copytree(world, target, ignore=lambda folder, _: _excluded(world, folder))
    marker.write_text(wanted, encoding="utf-8")


def _clear(marker: Path, target: Path) -> None:
    marker.unlink(missing_ok=True)
    if target.exists():
        shutil.rmtree(target)


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
