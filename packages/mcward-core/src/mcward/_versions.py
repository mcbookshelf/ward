"""Version parsing and comparison utilities for Ward."""

import json
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import total_ordering
from pathlib import Path

import httpx

from ._constants import MODRINTH_API


@total_ordering
@dataclass(frozen=True)
class Version:
    """Parsed Minecraft version with comparison operators."""

    name: str  # "26.1.2" or "26.2-snapshot-6"
    year: int  # 26
    major: int  # 1 or 2
    patch: int  # 2 (0 for snapshots or base release)
    snapshot: int  # 6 (0 for releases)

    @property
    def is_snapshot(self) -> bool:
        """Return whether this is a snapshot version."""
        return self.snapshot > 0

    @classmethod
    def parse(cls, name: str) -> Version:
        """Parse version string into structured format.

        Supports:
        - Release: "26.1" or "26.1.2"
        - Snapshot: "26.2-snapshot-6"
        """
        version = name[4:] if name.startswith("dev/") else name

        # Try snapshot pattern: 26.2-snapshot-6
        if snapshot_match := re.match(r"^(\d+)\.(\d+)-snapshot-(\d+)$", version):
            year = int(snapshot_match.group(1))
            major = int(snapshot_match.group(2))
            snapshot = int(snapshot_match.group(3))
            return cls(name, year, major, 0, snapshot)

        # Try release pattern: 26.1 or 26.1.2
        if release_match := re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?$", version):
            year = int(release_match.group(1))
            major = int(release_match.group(2))
            patch = int(release_match.group(3) or 0)
            return cls(name, year, major, patch, 0)

        raise ValueError(f"Invalid version format: {version}")

    def __lt__(self, other: object) -> bool:
        """Compare versions for ordering.

        Dev versions sort before regular versions (dev is "less than" regular).
        """
        if not isinstance(other, Version):
            return NotImplemented

        return (
            self.name.startswith("dev/"),
            self.year,
            self.major,
            self.patch if not self.is_snapshot else -1,
            self.snapshot,
        ) < (
            other.name.startswith("dev/"),
            other.year,
            other.major,
            other.patch if not other.is_snapshot else -1,
            other.snapshot,
        )

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"Version({self.name!r})"

    def __str__(self) -> str:
        """String representation (returns name)."""
        return self.name


class VersionRegistry:
    """Registry for managing Minecraft versions."""

    def __init__(self, cache_dir: Path, ttl_hours: int = 1):
        self.cache = cache_dir / "versions.json"
        self.ttl = timedelta(hours=ttl_hours)

    def get(self, version: str) -> Version | None:
        """Fetch a specific Version object from cache/registry."""
        if version == "dev":
            return self._get_dev_version()
        versions = self.list()
        if version == "snapshot":
            return max(versions, default=None)
        if version == "latest":
            return max((v for v in versions if not v.is_snapshot), default=None)
        return next((v for v in versions if v.name == version), None)

    def list(self) -> list[Version]:
        """List all known versions."""
        if not self._is_cache_valid():
            try:
                return self.sync()
            except httpx.HTTPError:
                if not self.cache.exists():
                    raise
        return self._read_cache()

    def sync(self) -> list[Version]:
        """Fetch fresh version schemas from remote endpoint."""
        versions = self._fetch_versions()
        self._write_cache(versions)
        return versions

    def _fetch_versions(self) -> list[Version]:
        response = httpx.get(f"{MODRINTH_API}/project/ward/version", timeout=5)
        response.raise_for_status()
        return sorted(
            {Version.parse(name) for item in response.json() for name in item["game_versions"]},
            reverse=True,
        )

    def _is_cache_valid(self) -> bool:
        with suppress(FileNotFoundError):
            timestamp = datetime.fromtimestamp(self.cache.stat().st_mtime)
            return datetime.now() - timestamp < self.ttl
        return False

    def _read_cache(self) -> list[Version]:
        with suppress(FileNotFoundError, json.JSONDecodeError, KeyError):
            data = json.loads(self.cache.read_text(encoding="utf-8"))
            return [Version.parse(v) for v in data.get("versions", [])]
        return []

    def _write_cache(self, versions: list[Version]) -> None:
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        data = {"versions": [v.name for v in versions]}
        self.cache.write_text(json.dumps(data), encoding="utf-8")

    def _get_dev_version(self) -> Version | None:
        """Get dev version from gradle.properties in current working directory."""
        with suppress(FileNotFoundError, ValueError, IndexError):
            props = Path.cwd() / "gradle.properties"
            content = props.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("minecraft_version="):
                    mc_version = line.split("=", 1)[1].strip()
                    return Version.parse(f"dev/{mc_version}")
        return None
