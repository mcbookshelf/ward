"""Minecraft versions: parsing, ordering, and the registry of supported ones."""

import json
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import total_ordering
from pathlib import Path
from typing import TYPE_CHECKING

from ._constants import MODRINTH_API, PACK_FORMATS, USER_AGENT
from ._exceptions import VersionError

if TYPE_CHECKING:
    import httpx

_PATTERN = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?(?:-(snapshot|pre|rc)-(\d+))?$")
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
        """Parse "26.1.2", "26.2-snapshot-6", "26.3-pre-1" or "26.3-rc-1", "dev/" allowed."""
        version = name.removeprefix("dev/")
        if match := _PATTERN.match(version):
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


# Each version with its pack format and the newest Ward mod for it
type _Entries = list[tuple[Version, int, str | None]]


class VersionRegistry:
    """The Minecraft versions Ward supports, with pack formats; fetched on first use."""

    def __init__(self, cache_dir: Path, ttl_hours: int = 4):
        self._file = cache_dir / "versions.json"
        self._ttl = timedelta(hours=ttl_hours)
        self._entries: _Entries | None = None

    def get(self, name: str) -> Version | None:
        """Get a specific version by name or alias (dev, latest, snapshot)."""
        if name == "dev":
            return _get_gradle_version()
        entries = self._load()
        if name == "snapshot":
            return max((v for v, _, _ in entries), default=None)
        if name == "latest":
            return max((v for v, _, _ in entries if not v.is_snapshot), default=None)
        return next((v for v, _, _ in entries if v.name == name), None)

    def available(self) -> list[Version]:
        """Every version in the registry, in registry order."""
        return [v for v, _, _ in self._load()]

    def list_in_range(self, min_fmt: int, max_fmt: int) -> list[Version]:
        """Every version whose pack format falls inside the range."""
        return [v for v, fmt, _ in self._load() if min_fmt <= fmt <= max_fmt]

    def newest_mod(self, version: Version) -> str | None:
        """The newest Ward mod published for the version, without its build metadata."""
        return next((mod for v, _, mod in self._load() if v == version), None)

    def refresh(self) -> VersionRegistry:
        """Fetch fresh data from the remote endpoints and update the cache file."""
        self._entries = self._fetch()
        return self

    def _load(self) -> _Entries:
        if self._entries is None:
            self._entries = self._fetch_or_read() if self._is_stale() else self._read()
        return self._entries

    def _fetch_or_read(self) -> _Entries:
        """Fresh entries, or the stale cache file when the network or the API is broken."""
        try:
            return self._fetch()
        except VersionError:
            if not self._file.exists():
                raise
            return self._read()

    def _fetch(self) -> _Entries:
        import asyncio

        import httpx  # deferred: most runs never fetch

        try:
            try:
                formats, versions = asyncio.run(_fetch_remote())
            except httpx.TransportError:
                formats, versions = asyncio.run(_fetch_remote())
        # KeyError and TypeError: a field renamed in one of the two third-party answers
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
            raise VersionError(f"Could not fetch version data: {e}") from e
        # A version without a known pack format is left out
        entries: _Entries = [
            (v, formats[v.name], mod) for v, mod in versions.items() if v.name in formats
        ]
        self._save(entries)
        return entries

    def _read(self) -> _Entries:
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            return [(Version.parse(e["name"]), e["format"], e.get("mod")) for e in data]
        except FileNotFoundError, json.JSONDecodeError, KeyError:
            return []

    def _save(self, entries: _Entries) -> None:
        data = [{"name": v.name, "format": fmt, "mod": mod} for v, fmt, mod in entries]
        self._file.parent.mkdir(parents=True, exist_ok=True)
        partial = self._file.with_suffix(self._file.suffix + ".part")
        partial.write_text(json.dumps(data), encoding="utf-8")
        partial.replace(self._file)

    def _is_stale(self) -> bool:
        try:
            mtime = datetime.fromtimestamp(self._file.stat().st_mtime)
        except FileNotFoundError:
            return True
        return datetime.now() - mtime > self._ttl


async def _fetch_remote() -> tuple[dict[str, int], dict[Version, str]]:
    """Fetch formats and versions in parallel."""
    import asyncio

    import httpx

    async with httpx.AsyncClient(timeout=5, headers={"User-Agent": USER_AGENT}) as client:
        return await asyncio.gather(_fetch_formats(client), _fetch_versions(client))


async def _fetch_formats(client: httpx.AsyncClient) -> dict[str, int]:
    """Map every Minecraft version id to its data pack format."""
    response = await client.get(PACK_FORMATS)
    response.raise_for_status()
    return {e["id"]: int(e["data_pack_version"]) for e in response.json()}


async def _fetch_versions(client: httpx.AsyncClient) -> dict[Version, str]:
    """Each Minecraft version a Ward release supports, newest first, with its newest mod."""
    response = await client.get(f"{MODRINTH_API}/project/ward/version")
    response.raise_for_status()

    mods: dict[Version, str] = {}
    for release in response.json():
        mod = release["version_number"].split("+")[0]
        for name in release["game_versions"]:
            # One mispublished id must not brick the registry
            with suppress(ValueError):
                version = Version.parse(name)
                mods[version] = max(mods.get(version, mod), mod, key=release_numbers)
    return dict(sorted(mods.items(), reverse=True))


def release_numbers(version: str) -> tuple[int, ...]:
    """The numbers to compare two versions by, "1.2.3-beta+26.3" giving (1, 2, 3), or none."""
    try:
        return tuple(int(x) for x in version.split("-")[0].split("+")[0].split("."))
    except ValueError:
        return ()


def _get_gradle_version() -> Version | None:
    """The version targeted by the Ward checkout in the working directory."""
    # Any other Fabric mod would be built and installed as ward.jar
    if not _is_ward_checkout(Path.cwd()):
        return None
    try:
        content = (Path.cwd() / "gradle.properties").read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("minecraft_version="):
                return Version.parse(f"dev/{line.split('=', 1)[1].strip()}")
    except FileNotFoundError, ValueError, IndexError:
        pass
    return None


def _is_ward_checkout(directory: Path) -> bool:
    try:
        metadata = json.loads((directory / "src/main/resources/fabric.mod.json").read_text("utf-8"))
    except OSError, ValueError:
        return False
    return isinstance(metadata, dict) and metadata.get("id") == "ward"
