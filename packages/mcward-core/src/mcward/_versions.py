"""Version parsing and comparison utilities for Ward."""

import asyncio
import json
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import total_ordering
from pathlib import Path

import httpx

from ._constants import MODRINTH_API, PACK_FORMATS, USER_AGENT
from ._exceptions import VersionError


# Release ("") sorts above every pre-release stage of its own version
_STAGES = {"snapshot": 0, "pre": 1, "rc": 2, "": 3}


@total_ordering
@dataclass(frozen=True)
class Version:
    """Parsed Minecraft version with comparison operators."""

    name: str  # "26.1.2" or "dev/26.2"
    minecraft: str  # "26.1.2" or "26.2-snapshot-6", without the dev/ prefix
    year: int  # 26
    major: int  # 1 or 2
    patch: int  # 2 (0 for pre-releases or base release)
    stage: str  # "snapshot", "pre", "rc" or "" for releases
    build: int  # 6 (0 for releases)

    @property
    def is_dev(self) -> bool:
        return self.name.startswith("dev/")

    @property
    def is_snapshot(self) -> bool:
        return self.stage != ""

    @classmethod
    def parse(cls, name: str) -> Version:
        """Parse "26.1.2", "26.2-snapshot-6", "26.3-pre-1", "26.3-rc-1"
        or a "dev/" prefixed variant."""
        version = name.removeprefix("dev/")
        if match := re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?(?:-(snapshot|pre|rc)-(\d+))?$", version):
            return cls(
                name,
                version,
                int(match[1]),
                int(match[2]),
                int(match[3] or 0),
                match[4] or "",
                int(match[5] or 0),
            )
        raise ValueError(f"Invalid version format: {version}")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Version({self.name!r})"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._sort_key < other._sort_key

    @property
    def _sort_key(self) -> tuple[bool, int, int, int, int, int]:
        # Dev builds sort above everything
        return (
            self.is_dev,
            self.year,
            self.major,
            self.patch,
            _STAGES[self.stage],
            self.build,
        )


# Aliases used inside VersionRegistry
type _VersionList = list[Version]
type _VersionEntries = list[tuple[Version, int]]


class VersionRegistry:
    """The Minecraft versions Ward supports, with their pack formats.

    Loaded lazily on first access: constructing the registry never touches
    the network, so commands that don't need version data work offline.
    """

    def __init__(self, cache_dir: Path, ttl_hours: int = 4):
        self._file = cache_dir / "versions.json"
        self._ttl = timedelta(hours=ttl_hours)
        self._versions: list[tuple[Version, int]] | None = None

    def get(self, name: str) -> Version | None:
        """Get a specific version by name or alias (dev, latest, snapshot)."""
        if name == "dev":
            return _get_gradle_version()
        versions = self._ensure_loaded()
        if name == "snapshot":
            return max((v for v, _ in versions), default=None)
        if name == "latest":
            return max((v for v, _ in versions if not v.is_snapshot), default=None)
        return next((v for v, _ in versions if v.name == name), None)

    def list(self) -> _VersionList:
        """Every version in the registry, in registry order."""
        return [v for v, _ in self._ensure_loaded()]

    def list_in_range(self, min_fmt: int, max_fmt: int) -> _VersionList:
        """Every version whose pack format falls inside the range."""
        return [v for v, fmt in self._ensure_loaded() if min_fmt <= fmt <= max_fmt]

    def refresh(self) -> VersionRegistry:
        """Fetch fresh data from remote endpoints and update cache."""
        formats, versions = asyncio.run(_fetch())
        # A version without a known pack format is left out
        entries = [(v, formats[v.name]) for v in versions if v.name in formats]
        self._versions = entries
        self._save(entries)
        return self

    def _ensure_loaded(self) -> _VersionEntries:
        """Refresh from remote if stale, falling back to the cached file."""
        if self._versions is None:
            if self._is_stale():
                # ValueError covers a garbage response body
                # A broken API falls back to the cached file, like a broken network
                try:
                    return self.refresh()._versions or []
                except (httpx.HTTPError, ValueError) as e:
                    if not self._file.exists():
                        raise VersionError(f"Could not fetch version data: {e}") from e
            self._load()
        return self._versions or []

    def _load(self) -> None:
        self._versions = []
        with suppress(FileNotFoundError, json.JSONDecodeError, KeyError):
            data = json.loads(self._file.read_text(encoding="utf-8"))
            self._versions = [(Version.parse(e["name"]), e["format"]) for e in data]

    def _save(self, entries: _VersionEntries) -> None:
        data = [{"name": v.name, "format": fmt} for v, fmt in entries]
        self._file.parent.mkdir(parents=True, exist_ok=True)
        partial = self._file.with_suffix(self._file.suffix + ".part")
        partial.write_text(json.dumps(data), encoding="utf-8")
        partial.replace(self._file)

    def _is_stale(self) -> bool:
        with suppress(FileNotFoundError):
            mtime = datetime.fromtimestamp(self._file.stat().st_mtime)
            return datetime.now() - mtime > self._ttl
        return True


async def _fetch() -> tuple[dict[str, int], list[Version]]:
    """Fetch formats and versions in parallel."""
    async with httpx.AsyncClient(timeout=5, headers={"User-Agent": USER_AGENT}) as client:
        return await asyncio.gather(_fetch_formats(client), _fetch_versions(client))


async def _fetch_formats(client: httpx.AsyncClient) -> dict[str, int]:
    """Map every Minecraft version id to its data pack format."""
    response = await client.get(PACK_FORMATS)
    response.raise_for_status()
    return {e["id"]: int(e["data_pack_version"]) for e in response.json()}


async def _fetch_versions(client: httpx.AsyncClient) -> list[Version]:
    """Every Minecraft version a published Ward release supports."""
    response = await client.get(f"{MODRINTH_API}/project/ward/version")
    response.raise_for_status()

    versions = set()
    for release in response.json():
        for name in release["game_versions"]:
            # One mispublished id must not brick the registry
            with suppress(ValueError):
                versions.add(Version.parse(name))
    return sorted(versions, reverse=True)


def _get_gradle_version() -> Version | None:
    """The version targeted by the mod checkout in the working directory."""
    with suppress(FileNotFoundError, ValueError, IndexError):
        props = Path.cwd() / "gradle.properties"
        content = props.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("minecraft_version="):
                mc_version = line.split("=", 1)[1].strip()
                return Version.parse(f"dev/{mc_version}")
    return None
