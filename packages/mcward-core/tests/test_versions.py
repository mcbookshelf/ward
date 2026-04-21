"""Tests for version parsing and comparison."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcward import Version, VersionRegistry


class TestVersionParsing:
    """Test version string parsing."""

    def test_parse_release_with_patch(self) -> None:
        """Test parsing release version with patch number."""
        v = Version.parse("26.1.2")
        assert v.name == "26.1.2"
        assert v.year == 26
        assert v.major == 1
        assert v.patch == 2
        assert v.snapshot == 0
        assert v.is_snapshot is False

    def test_parse_release_without_patch(self) -> None:
        """Test parsing release version without patch number."""
        v = Version.parse("26.1")
        assert v.name == "26.1"
        assert v.year == 26
        assert v.major == 1
        assert v.patch == 0
        assert v.snapshot == 0
        assert v.is_snapshot is False

    def test_parse_snapshot(self) -> None:
        """Test parsing snapshot version."""
        v = Version.parse("26.2-snapshot-6")
        assert v.name == "26.2-snapshot-6"
        assert v.year == 26
        assert v.major == 2
        assert v.patch == 0
        assert v.snapshot == 6
        assert v.is_snapshot is True

    def test_parse_invalid_format(self) -> None:
        """Test parsing invalid version format raises error."""
        with pytest.raises(ValueError, match="Invalid version format"):
            Version.parse("invalid")

        with pytest.raises(ValueError, match="Invalid version format"):
            Version.parse("26")

        with pytest.raises(ValueError, match="Invalid version format"):
            Version.parse("26.1.2.3")

    def test_parse_dev_version(self) -> None:
        """Test parsing dev version with dev/ prefix."""
        v = Version.parse("dev/26.1.2")
        assert v.name == "dev/26.1.2"
        assert v.year == 26
        assert v.major == 1
        assert v.patch == 2
        assert v.snapshot == 0
        assert v.is_snapshot is False

    def test_parse_dev_snapshot(self) -> None:
        """Test parsing dev snapshot version."""
        v = Version.parse("dev/26.2-snapshot-6")
        assert v.name == "dev/26.2-snapshot-6"
        assert v.year == 26
        assert v.major == 2
        assert v.patch == 0
        assert v.snapshot == 6
        assert v.is_snapshot is True


class TestVersionComparison:
    """Test version comparison and ordering."""

    def test_snapshots_before_release(self) -> None:
        """Test that snapshots sort before their release."""
        snapshot = Version.parse("26.1-snapshot-4")
        release = Version.parse("26.1")
        assert snapshot < release
        assert release > snapshot

    def test_snapshot_ordering(self) -> None:
        """Test snapshot numbers order correctly."""
        v1 = Version.parse("26.1-snapshot-1")
        v2 = Version.parse("26.1-snapshot-2")
        v3 = Version.parse("26.1-snapshot-10")
        assert v1 < v2 < v3

    def test_patch_ordering(self) -> None:
        """Test patch numbers order correctly."""
        v1 = Version.parse("26.1")
        v2 = Version.parse("26.1.1")
        v3 = Version.parse("26.1.2")
        assert v1 < v2 < v3

    def test_major_version_ordering(self) -> None:
        """Test major version numbers order correctly."""
        v1 = Version.parse("26.1.2")
        v2 = Version.parse("26.2")
        assert v1 < v2

    def test_year_ordering(self) -> None:
        """Test year numbers order correctly."""
        v1 = Version.parse("25.3.1")
        v2 = Version.parse("26.1")
        assert v1 < v2

    def test_release_newer_than_old_snapshot(self) -> None:
        """Test that release is newer than pre-release snapshots."""
        # 26.1-snapshot-4 was before 26.1 release
        # 26.1.2 is a patch after 26.1
        snapshot = Version.parse("26.1-snapshot-4")
        release = Version.parse("26.1.2")
        assert snapshot < release
        assert release > snapshot

    def test_complex_ordering(self) -> None:
        """Test complex version ordering scenario."""
        versions = [
            Version.parse("26.2-snapshot-6"),
            Version.parse("26.1.2"),
            Version.parse("26.1.1"),
            Version.parse("26.1"),
            Version.parse("26.1-snapshot-4"),
            Version.parse("26.1-snapshot-1"),
            Version.parse("26.0.5"),
            Version.parse("25.3.1"),
        ]

        # Shuffle and sort
        import random

        shuffled = versions.copy()
        random.shuffle(shuffled)
        sorted_versions = sorted(shuffled)

        # Should be in this order
        expected_order = [
            "25.3.1",
            "26.0.5",
            "26.1-snapshot-1",
            "26.1-snapshot-4",
            "26.1",
            "26.1.1",
            "26.1.2",
            "26.2-snapshot-6",
        ]

        assert [v.name for v in sorted_versions] == expected_order

    def test_equality(self) -> None:
        """Test version equality."""
        v1 = Version.parse("26.1.2")
        v2 = Version.parse("26.1.2")
        assert v1 == v2
        assert not (v1 != v2)

    def test_inequality(self) -> None:
        """Test version inequality."""
        v1 = Version.parse("26.1.2")
        v2 = Version.parse("26.1.1")
        assert v1 != v2
        assert not (v1 == v2)

    def test_dev_versions_sort_after_regular(self) -> None:
        """Test that dev versions sort after regular versions (ascending order)."""
        dev = Version.parse("dev/26.1.2")
        regular = Version.parse("26.1.2")
        # In ascending order: regular < dev (so dev appears last)
        assert regular < dev
        assert dev > regular

    def test_dev_versions_sort_among_themselves(self) -> None:
        """Test that dev versions sort correctly relative to each other."""
        dev_old = Version.parse("dev/26.1.1")
        dev_new = Version.parse("dev/26.1.2")
        assert dev_old < dev_new
        assert dev_new > dev_old

    def test_mixed_dev_and_regular_sorting_ascending(self) -> None:
        """Test ascending sort of mixed dev and regular versions."""
        versions = [
            Version.parse("26.1.2"),
            Version.parse("dev/26.1.2"),
            Version.parse("26.1.1"),
            Version.parse("dev/26.1.1"),
            Version.parse("26.2-snapshot-6"),
            Version.parse("dev/26.2-snapshot-6"),
        ]

        sorted_versions = sorted(versions)

        # Ascending: regular versions first, then dev versions
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
        """Test descending sort - this is how list_installed() works."""
        versions = [
            Version.parse("26.1.2"),
            Version.parse("dev/26.1.2"),
            Version.parse("26.1.1"),
            Version.parse("dev/26.1.1"),
        ]

        sorted_versions = sorted(versions, reverse=True)

        # Descending (reverse=True): dev versions first, then regular
        # This is the order users see in list_installed()
        expected_order = [
            "dev/26.1.2",
            "dev/26.1.1",
            "26.1.2",
            "26.1.1",
        ]

        assert [v.name for v in sorted_versions] == expected_order


class TestVersionStringRepresentation:
    """Test version string representations."""

    def test_str(self) -> None:
        """Test __str__ returns version name."""
        v = Version.parse("26.1.2")
        assert str(v) == "26.1.2"

    def test_repr(self) -> None:
        """Test __repr__ is useful for debugging."""
        v = Version.parse("26.1.2")
        assert repr(v) == "Version('26.1.2')"


class TestVersionRegistry:
    """Test VersionRegistry caching and version resolution."""

    @pytest.fixture
    def temp_cache(self, tmp_path: Path) -> Path:
        """Create a temporary cache directory."""
        return tmp_path / "cache"

    @pytest.fixture
    def registry(self, temp_cache: Path) -> VersionRegistry:
        """Create a VersionRegistry with temporary cache."""
        return VersionRegistry(temp_cache, ttl_hours=1)

    @pytest.fixture
    def mock_versions(self) -> list[dict]:
        """Mock version data from Modrinth API."""
        return [
            {"game_versions": ["26.1.2", "26.1.1", "26.1"]},
            {"game_versions": ["26.1.1"]},
            {"game_versions": ["26.2-snapshot-6"]},
            {"game_versions": ["26.2-snapshot-5", "26.2-snapshot-4"]},
        ]

    def test_cache_miss_fetches_versions(
        self, registry: VersionRegistry, mock_versions: list[dict]
    ) -> None:
        """Test that cache miss triggers fetch from API."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response

            versions = registry.list()

            # Should fetch from API
            mock_get.assert_called_once()
            assert len(versions) > 0
            # Should deduplicate versions
            version_names = [v.name for v in versions]
            assert len(version_names) == len(set(version_names))

    def test_cache_hit_uses_cached_versions(
        self, registry: VersionRegistry, mock_versions: list[dict]
    ) -> None:
        """Test that valid cache prevents API calls."""
        # First call - populate cache
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response
            versions1 = registry.list()
            assert mock_get.call_count == 1

        # Second call - should use cache
        with patch("httpx.get") as mock_get:
            versions2 = registry.list()
            mock_get.assert_not_called()
            assert versions1 == versions2

    def test_cache_ttl_expiry(self, temp_cache: Path, mock_versions: list[dict]) -> None:
        """Test that expired cache triggers refetch."""
        # Create registry with very short TTL
        registry = VersionRegistry(temp_cache, ttl_hours=0)

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response

            # First call
            registry.list()
            assert mock_get.call_count == 1

            # Wait a tiny bit to ensure time passes
            time.sleep(0.01)

            # Second call - cache expired, should refetch
            registry.list()
            assert mock_get.call_count == 2

    def test_stale_cache_fallback_on_network_error(
        self, registry: VersionRegistry, mock_versions: list[dict]
    ) -> None:
        """Test that stale cache is used when network fails."""
        import httpx

        # First, populate cache
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response
            versions1 = registry.list()

        # Make cache stale by modifying mtime
        cache_file = registry.cache
        old_time = time.time() - 7200  # 2 hours ago
        cache_file.touch()
        import os

        os.utime(cache_file, (old_time, old_time))

        # Network error on fetch (httpx.HTTPError is what the code catches)
        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("Network error")
            versions2 = registry.list()
            # Should still return stale cache
            assert versions1 == versions2

    def test_network_error_no_cache_raises(self, registry: VersionRegistry) -> None:
        """Test that network error with no cache raises exception."""
        import httpx

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("Network error")
            with pytest.raises(httpx.HTTPError, match="Network error"):
                registry.list()

    def test_sync_forces_refresh(
        self, registry: VersionRegistry, mock_versions: list[dict]
    ) -> None:
        """Test that sync() forces cache refresh."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response

            # First call via list()
            registry.list()
            assert mock_get.call_count == 1

            # Call sync() - should force refresh
            registry.sync()
            assert mock_get.call_count == 2

    def test_get_specific_version(
        self, registry: VersionRegistry, mock_versions: list[dict]
    ) -> None:
        """Test getting a specific version by name."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response

            version = registry.get("26.1.2")
            assert version is not None
            assert version.name == "26.1.2"

    def test_get_nonexistent_version(
        self, registry: VersionRegistry, mock_versions: list[dict]
    ) -> None:
        """Test getting a version that doesn't exist."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response

            version = registry.get("99.99.99")
            assert version is None

    def test_get_latest_alias(self, registry: VersionRegistry, mock_versions: list[dict]) -> None:
        """Test 'latest' alias returns newest release."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response

            version = registry.get("latest")
            assert version is not None
            assert not version.is_snapshot
            # Should be the highest release version
            all_versions = registry.list()
            releases = [v for v in all_versions if not v.is_snapshot]
            assert version == max(releases)

    def test_get_snapshot_alias(self, registry: VersionRegistry, mock_versions: list[dict]) -> None:
        """Test 'snapshot' alias returns newest snapshot."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response

            version = registry.get("snapshot")
            assert version is not None
            assert version.is_snapshot
            # Should be the highest snapshot version
            all_versions = registry.list()
            snapshots = [v for v in all_versions if v.is_snapshot]
            assert version == max(snapshots)

    def test_get_dev_version_with_gradle_props(
        self, registry: VersionRegistry, tmp_path: Path
    ) -> None:
        """Test 'dev' alias reads from gradle.properties."""
        # Create a gradle.properties file
        gradle_props = tmp_path / "gradle.properties"
        gradle_props.write_text("minecraft_version=26.1.2\n")

        # Change to directory with gradle.properties
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            version = registry.get("dev")
            assert version is not None
            # Dev now returns version with name "dev/26.1.2"
            assert version.name == "dev/26.1.2"
            assert version.year == 26
            assert version.major == 1
            assert version.patch == 2
        finally:
            os.chdir(original_cwd)

    def test_get_dev_version_without_gradle_props(
        self, registry: VersionRegistry, tmp_path: Path
    ) -> None:
        """Test 'dev' alias returns None without gradle.properties."""
        # Change to directory without gradle.properties
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            version = registry.get("dev")
            assert version is None
        finally:
            os.chdir(original_cwd)

    def test_cache_persistence(self, registry: VersionRegistry, mock_versions: list[dict]) -> None:
        """Test that cache persists across registry instances."""
        # First registry instance - populate cache
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response
            versions1 = registry.list()

        # Second registry instance - should read from cache
        registry2 = VersionRegistry(registry.cache.parent, ttl_hours=1)
        with patch("httpx.get") as mock_get:
            versions2 = registry2.list()
            mock_get.assert_not_called()
            assert versions1 == versions2

    def test_cache_deduplication(self, registry: VersionRegistry) -> None:
        """Test that duplicate versions in API response are deduplicated."""
        mock_versions = [
            {"game_versions": ["26.1.2", "26.1.1"]},
            {"game_versions": ["26.1.2", "26.1.1"]},  # Duplicates
            {"game_versions": ["26.1.1"]},  # More duplicates
        ]

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response

            versions = registry.list()
            version_names = [v.name for v in versions]

            # Should only have unique versions
            assert len(version_names) == len(set(version_names))
            assert sorted(set(version_names)) == sorted(version_names)

    def test_versions_sorted_descending(
        self, registry: VersionRegistry, mock_versions: list[dict]
    ) -> None:
        """Test that versions are returned in descending order."""
        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_versions
            mock_get.return_value = mock_response

            versions = registry.list()
            # Verify descending order
            for i in range(len(versions) - 1):
                assert versions[i] >= versions[i + 1]
