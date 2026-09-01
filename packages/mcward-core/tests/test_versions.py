"""Tests for version parsing and comparison."""

import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from mcward import Version, VersionError, VersionRegistry
from mcward._versions import _fetch_versions


class TestVersionParsing:
    def test_parse_release_with_patch(self) -> None:
        v = Version.parse("26.1.2")
        assert v.name == "26.1.2"
        assert v.year == 26
        assert v.major == 1
        assert v.patch == 2
        assert v.stage == ""
        assert v.build == 0
        assert v.is_snapshot is False

    def test_parse_release_without_patch(self) -> None:
        v = Version.parse("26.1")
        assert v.name == "26.1"
        assert v.year == 26
        assert v.major == 1
        assert v.patch == 0
        assert v.stage == ""
        assert v.build == 0
        assert v.is_snapshot is False

    def test_parse_snapshot(self) -> None:
        v = Version.parse("26.2-snapshot-6")
        assert v.name == "26.2-snapshot-6"
        assert v.year == 26
        assert v.major == 2
        assert v.patch == 0
        assert v.stage == "snapshot"
        assert v.build == 6
        assert v.is_snapshot is True

    def test_parse_pre_release(self) -> None:
        v = Version.parse("26.3-pre-1")
        assert v.name == "26.3-pre-1"
        assert v.year == 26
        assert v.major == 3
        assert v.patch == 0
        assert v.stage == "pre"
        assert v.build == 1
        assert v.is_snapshot is True

    def test_parse_release_candidate(self) -> None:
        v = Version.parse("26.3-rc-2")
        assert v.name == "26.3-rc-2"
        assert v.year == 26
        assert v.major == 3
        assert v.patch == 0
        assert v.stage == "rc"
        assert v.build == 2
        assert v.is_snapshot is True

    def test_parse_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="Invalid version format"):
            Version.parse("invalid")

        with pytest.raises(ValueError, match="Invalid version format"):
            Version.parse("26")

        with pytest.raises(ValueError, match="Invalid version format"):
            Version.parse("26.1.2.3")

    def test_parse_dev_version(self) -> None:
        v = Version.parse("dev/26.1.2")
        assert v.name == "dev/26.1.2"
        assert v.year == 26
        assert v.major == 1
        assert v.patch == 2
        assert v.stage == ""
        assert v.build == 0
        assert v.is_snapshot is False

    def test_parse_dev_snapshot(self) -> None:
        v = Version.parse("dev/26.2-snapshot-6")
        assert v.name == "dev/26.2-snapshot-6"
        assert v.year == 26
        assert v.major == 2
        assert v.patch == 0
        assert v.stage == "snapshot"
        assert v.build == 6
        assert v.is_snapshot is True


class TestVersionComparison:
    def test_snapshots_before_release(self) -> None:
        snapshot = Version.parse("26.1-snapshot-4")
        release = Version.parse("26.1")
        assert snapshot < release
        assert release > snapshot

    def test_snapshot_ordering(self) -> None:
        v1 = Version.parse("26.1-snapshot-1")
        v2 = Version.parse("26.1-snapshot-2")
        v3 = Version.parse("26.1-snapshot-10")
        assert v1 < v2 < v3

    def test_stage_ordering(self) -> None:
        snapshot = Version.parse("26.3-snapshot-10")
        pre = Version.parse("26.3-pre-1")
        rc = Version.parse("26.3-rc-1")
        release = Version.parse("26.3")
        assert snapshot < pre < rc < release

    def test_patch_ordering(self) -> None:
        v1 = Version.parse("26.1")
        v2 = Version.parse("26.1.1")
        v3 = Version.parse("26.1.2")
        assert v1 < v2 < v3

    def test_major_version_ordering(self) -> None:
        v1 = Version.parse("26.1.2")
        v2 = Version.parse("26.2")
        assert v1 < v2

    def test_year_ordering(self) -> None:
        v1 = Version.parse("25.3.1")
        v2 = Version.parse("26.1")
        assert v1 < v2

    def test_release_newer_than_old_snapshot(self) -> None:
        snapshot = Version.parse("26.1-snapshot-4")
        release = Version.parse("26.1.2")
        assert snapshot < release
        assert release > snapshot

    def test_complex_ordering(self) -> None:
        versions = [
            Version.parse("26.2-snapshot-6"),
            Version.parse("26.1.2"),
            Version.parse("26.1.1"),
            Version.parse("26.1"),
            Version.parse("26.1-rc-1"),
            Version.parse("26.1-pre-2"),
            Version.parse("26.1-snapshot-4"),
            Version.parse("26.1-snapshot-1"),
            Version.parse("26.0.5"),
            Version.parse("25.3.1"),
        ]

        sorted_versions = sorted(versions)

        expected_order = [
            "25.3.1",
            "26.0.5",
            "26.1-snapshot-1",
            "26.1-snapshot-4",
            "26.1-pre-2",
            "26.1-rc-1",
            "26.1",
            "26.1.1",
            "26.1.2",
            "26.2-snapshot-6",
        ]

        assert [v.name for v in sorted_versions] == expected_order

    def test_equality(self) -> None:
        v1 = Version.parse("26.1.2")
        v2 = Version.parse("26.1.2")
        assert v1 == v2
        assert not (v1 != v2)

    def test_inequality(self) -> None:
        v1 = Version.parse("26.1.2")
        v2 = Version.parse("26.1.1")
        assert v1 != v2
        assert not (v1 == v2)

    def test_dev_versions_sort_after_regular(self) -> None:
        dev = Version.parse("dev/26.1.2")
        regular = Version.parse("26.1.2")
        assert regular < dev
        assert dev > regular

    def test_dev_versions_sort_among_themselves(self) -> None:
        dev_old = Version.parse("dev/26.1.1")
        dev_new = Version.parse("dev/26.1.2")
        assert dev_old < dev_new
        assert dev_new > dev_old

    def test_mixed_dev_and_regular_sorting_ascending(self) -> None:
        versions = [
            Version.parse("26.1.2"),
            Version.parse("dev/26.1.2"),
            Version.parse("26.1.1"),
            Version.parse("dev/26.1.1"),
            Version.parse("26.2-snapshot-6"),
            Version.parse("dev/26.2-snapshot-6"),
        ]

        sorted_versions = sorted(versions)

        expected_order = [
            "26.1.1",
            "26.1.2",
            "26.2-snapshot-6",
            "dev/26.1.1",
            "dev/26.1.2",
            "dev/26.2-snapshot-6",
        ]

        assert [v.name for v in sorted_versions] == expected_order

    def test_mixed_dev_and_regular_sorting_descending(self) -> None:
        """Descending sort, the order list_installed() returns."""
        versions = [
            Version.parse("26.1.2"),
            Version.parse("dev/26.1.2"),
            Version.parse("26.1.1"),
            Version.parse("dev/26.1.1"),
        ]

        sorted_versions = sorted(versions, reverse=True)

        expected_order = [
            "dev/26.1.2",
            "dev/26.1.1",
            "26.1.2",
            "26.1.1",
        ]

        assert [v.name for v in sorted_versions] == expected_order


class TestVersionStringRepresentation:
    def test_str(self) -> None:
        v = Version.parse("26.1.2")
        assert str(v) == "26.1.2"

    def test_repr(self) -> None:
        v = Version.parse("26.1.2")
        assert repr(v) == "Version('26.1.2')"


class TestVersionRegistry:
    """Test VersionRegistry lazy loading, caching and version resolution."""

    @pytest.fixture
    def temp_cache(self, tmp_path: Path) -> Path:
        return tmp_path / "cache"

    @pytest.fixture
    def registry(self, temp_cache: Path) -> VersionRegistry:
        return VersionRegistry(temp_cache, ttl_hours=1)

    @pytest.fixture
    def fetch_result(self) -> tuple[dict[str, int], list[Version]]:
        """Mock (formats, versions) as produced by _fetch."""
        versions = [
            Version.parse("26.2-snapshot-6"),
            Version.parse("26.1.2"),
            Version.parse("26.1.1"),
            Version.parse("26.1"),
        ]
        formats = {"26.2-snapshot-6": 82, "26.1.2": 81, "26.1.1": 81, "26.1": 80}
        return formats, versions

    @staticmethod
    def patch_fetch(result: tuple[dict[str, int], list[Version]]):
        """Patch the remote fetch with a canned result."""

        async def fake_fetch() -> tuple[dict[str, int], list[Version]]:
            return result

        return patch("mcward._versions._fetch", side_effect=fake_fetch)

    def test_constructor_is_lazy(self, temp_cache: Path) -> None:
        with self.patch_fetch(({}, [])) as mock_fetch:
            VersionRegistry(temp_cache, ttl_hours=1)
            mock_fetch.assert_not_called()

    def test_dev_alias_needs_no_data(
        self, registry: VersionRegistry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "gradle.properties").write_text("minecraft_version=26.1.2\n")
        monkeypatch.chdir(tmp_path)

        with self.patch_fetch(({}, [])) as mock_fetch:
            version = registry.get("dev")
            mock_fetch.assert_not_called()
        assert version is not None
        assert version.name == "dev/26.1.2"

    def test_dev_alias_without_gradle_props(
        self, registry: VersionRegistry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert registry.get("dev") is None

    def test_first_access_fetches_and_caches(
        self, registry: VersionRegistry, fetch_result: tuple[dict[str, int], list[Version]]
    ) -> None:
        with self.patch_fetch(fetch_result) as mock_fetch:
            versions = registry.list()
            registry.list()
            registry.get("26.1.2")
            mock_fetch.assert_called_once()

        assert [v.name for v in versions] == ["26.2-snapshot-6", "26.1.2", "26.1.1", "26.1"]

    def test_cache_persistence(
        self, temp_cache: Path, fetch_result: tuple[dict[str, int], list[Version]]
    ) -> None:
        with self.patch_fetch(fetch_result):
            versions1 = VersionRegistry(temp_cache, ttl_hours=1).list()

        registry2 = VersionRegistry(temp_cache, ttl_hours=1)
        with self.patch_fetch(({}, [])) as mock_fetch:
            versions2 = registry2.list()
            mock_fetch.assert_not_called()

        assert versions1 == versions2

    def test_cache_ttl_expiry(
        self, temp_cache: Path, fetch_result: tuple[dict[str, int], list[Version]]
    ) -> None:
        with self.patch_fetch(fetch_result) as mock_fetch:
            VersionRegistry(temp_cache, ttl_hours=0).list()
            assert mock_fetch.call_count == 1

            time.sleep(0.01)
            VersionRegistry(temp_cache, ttl_hours=0).list()
            assert mock_fetch.call_count == 2

    def test_stale_cache_fallback_on_network_error(
        self, temp_cache: Path, fetch_result: tuple[dict[str, int], list[Version]]
    ) -> None:

        with self.patch_fetch(fetch_result):
            versions1 = VersionRegistry(temp_cache, ttl_hours=0).list()

        with patch("mcward._versions._fetch", side_effect=httpx.HTTPError("Network error")):
            versions2 = VersionRegistry(temp_cache, ttl_hours=0).list()

        assert versions1 == versions2

    def test_network_error_no_cache_raises(self, registry: VersionRegistry) -> None:

        with patch("mcward._versions._fetch", side_effect=httpx.HTTPError("Network error")):
            with pytest.raises(VersionError, match="Network error"):
                registry.list()

    def test_garbage_response_falls_back_to_cache(
        self, temp_cache: Path, fetch_result: tuple[dict[str, int], list[Version]]
    ) -> None:
        """A broken API body is treated like a broken network."""
        with self.patch_fetch(fetch_result):
            versions1 = VersionRegistry(temp_cache, ttl_hours=0).list()

        with patch("mcward._versions._fetch", side_effect=ValueError("not json")):
            versions2 = VersionRegistry(temp_cache, ttl_hours=0).list()

        assert versions1 == versions2

    def test_cache_is_written_atomically(
        self,
        temp_cache: Path,
        registry: VersionRegistry,
        fetch_result: tuple[dict[str, int], list[Version]],
    ) -> None:
        """The cache file appears fully formed, with no partial sibling."""
        with self.patch_fetch(fetch_result):
            registry.list()

        assert [f.name for f in temp_cache.iterdir()] == ["versions.json"]

    def test_refresh_forces_fetch(
        self, registry: VersionRegistry, fetch_result: tuple[dict[str, int], list[Version]]
    ) -> None:
        with self.patch_fetch(fetch_result) as mock_fetch:
            registry.list()
            registry.refresh()
            assert mock_fetch.call_count == 2

    def test_versions_without_format_are_dropped(self, registry: VersionRegistry) -> None:
        result = ({"26.1.2": 81}, [Version.parse("26.1.2"), Version.parse("26.1.1")])
        with self.patch_fetch(result):
            assert [v.name for v in registry.list()] == ["26.1.2"]

    def test_get_specific_version(
        self, registry: VersionRegistry, fetch_result: tuple[dict[str, int], list[Version]]
    ) -> None:
        with self.patch_fetch(fetch_result):
            version = registry.get("26.1.2")
            assert version is not None
            assert version.name == "26.1.2"

            assert registry.get("99.99.99") is None

    def test_get_latest_and_snapshot_aliases(
        self, registry: VersionRegistry, fetch_result: tuple[dict[str, int], list[Version]]
    ) -> None:
        with self.patch_fetch(fetch_result):
            latest = registry.get("latest")
            snapshot = registry.get("snapshot")

        assert latest is not None and latest.name == "26.1.2"
        assert snapshot is not None and snapshot.name == "26.2-snapshot-6"

    def test_list_in_range(
        self, registry: VersionRegistry, fetch_result: tuple[dict[str, int], list[Version]]
    ) -> None:
        with self.patch_fetch(fetch_result):
            names = [v.name for v in registry.list_in_range(81, 81)]
        assert names == ["26.1.2", "26.1.1"]


class TestFetchVersions:
    """Test parsing of the remote version endpoints."""

    @pytest.mark.anyio
    async def test_versions_deduplicated_and_sorted(self) -> None:

        response = Mock()
        response.json.return_value = [
            {"game_versions": ["26.1.2", "26.1.1", "26.1"]},
            {"game_versions": ["26.1.1"]},
            {"game_versions": ["26.2-snapshot-6"]},
            {"game_versions": ["26.2-snapshot-5", "26.2-snapshot-4"]},
        ]
        client = AsyncMock()
        client.get.return_value = response

        versions = await _fetch_versions(client)
        names = [v.name for v in versions]

        assert len(names) == len(set(names))
        assert versions == sorted(versions, reverse=True)

    @pytest.mark.anyio
    async def test_unparseable_ids_are_skipped(self) -> None:
        """One mispublished version id must not break the whole registry."""

        response = Mock()
        response.json.return_value = [
            {"game_versions": ["26.1.2", "26w14craftmine"]},
        ]
        client = AsyncMock()
        client.get.return_value = response

        assert [v.name for v in await _fetch_versions(client)] == ["26.1.2"]
