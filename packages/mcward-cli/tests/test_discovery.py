"""Tests for datapack discovery and pack.mcmeta parsing."""

import json
import zipfile
from pathlib import Path

import pytest
import rich_click as click

from mcward.cli.datapacks import (
    DEFAULT_PATTERNS,
    discover_datapacks,
    parse_datapack,
)


def write_datapack(
    directory: Path, min_format: int | list[int], max_format: int | list[int]
) -> Path:
    """Create a minimal datapack with the given pack format range."""
    directory.mkdir(parents=True, exist_ok=True)
    meta = {"pack": {"min_format": min_format, "max_format": max_format}}
    (directory / "pack.mcmeta").write_text(json.dumps(meta), encoding="utf-8")
    return directory


def write_zipped_datapack(
    path: Path, min_format: int | list[int], max_format: int | list[int]
) -> Path:
    """Create a minimal zipped datapack with the given pack format range."""
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"pack": {"min_format": min_format, "max_format": max_format}}
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("pack.mcmeta", json.dumps(meta))
    return path


class TestDiscoverDatapacks:
    """Test datapack discovery from glob patterns."""

    def test_default_patterns_find_cwd_pack(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The "." pattern treats the cwd itself as a datapack."""
        write_datapack(tmp_path, 81, 82)
        monkeypatch.chdir(tmp_path)

        datapacks = discover_datapacks(DEFAULT_PATTERNS)

        assert [dp.path for dp in datapacks] == [tmp_path]
        assert (datapacks[0].min_format, datapacks[0].max_format) == (81, 82)

    def test_default_patterns_find_child_packs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The child patterns pick up packs in subdirectories."""
        write_datapack(tmp_path / "my_pack", 81, 81)
        write_datapack(tmp_path / "datapacks" / "other", 81, 81)
        monkeypatch.chdir(tmp_path)

        datapacks = discover_datapacks(DEFAULT_PATTERNS)

        names = sorted(dp.path.name for dp in datapacks)
        assert names == ["my_pack", "other"]

    def test_directories_without_mcmeta_are_ignored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "not_a_pack").mkdir()
        monkeypatch.chdir(tmp_path)

        assert discover_datapacks(DEFAULT_PATTERNS) == []

    def test_duplicate_matches_are_deduplicated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A pack matched by several patterns is only reported once."""
        write_datapack(tmp_path / "my_pack", 81, 81)
        monkeypatch.chdir(tmp_path)

        datapacks = discover_datapacks(["*", "my_pack"])

        assert len(datapacks) == 1

    def test_literal_paths_outside_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Absolute and parent-relative paths work, not just glob patterns."""
        pack = write_datapack(tmp_path / "elsewhere" / "my_pack", 81, 81)
        (tmp_path / "sub").mkdir()
        monkeypatch.chdir(tmp_path / "sub")

        for pattern in [str(pack), "../elsewhere/my_pack"]:
            [datapack] = discover_datapacks([pattern])
            assert datapack.path == pack.resolve()

    def test_absolute_and_recursive_patterns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Absolute globs and ** work, like pointing -p at another project's build."""
        write_datapack(tmp_path / "build" / "v1" / "my_pack", 81, 81)
        write_datapack(tmp_path / "build" / "v2" / "other", 81, 81)
        (tmp_path / "sub").mkdir()
        monkeypatch.chdir(tmp_path / "sub")

        for pattern in [str(tmp_path / "build" / "**"), "../build/**/"]:
            names = sorted(dp.path.name for dp in discover_datapacks([pattern]))
            assert names == ["my_pack", "other"], pattern

    def test_zipped_packs_are_discovered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Zip files carrying a pack.mcmeta count as datapacks, by glob or path."""
        write_zipped_datapack(tmp_path / "my_pack.zip", 81, 81)
        write_zipped_datapack(tmp_path / "datapacks" / "other.zip", 81, 81)
        monkeypatch.chdir(tmp_path)

        names = sorted(dp.path.name for dp in discover_datapacks(DEFAULT_PATTERNS))
        assert names == ["my_pack.zip", "other.zip"]

        [datapack] = discover_datapacks(["my_pack.zip"])
        assert datapack.path == tmp_path / "my_pack.zip"

    def test_zips_without_mcmeta_are_ignored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with zipfile.ZipFile(tmp_path / "not_a_pack.zip", "w") as archive:
            archive.writestr("readme.txt", "hi")
        monkeypatch.chdir(tmp_path)

        assert discover_datapacks(DEFAULT_PATTERNS) == []


class TestParseDatapack:
    """Test pack.mcmeta format parsing."""

    def test_plain_int_formats(self, tmp_path: Path) -> None:
        pack = write_datapack(tmp_path / "pack", 81, 82)
        datapack = parse_datapack(pack)
        assert (datapack.min_format, datapack.max_format) == (81, 82)

    def test_list_formats_use_first_entry(self, tmp_path: Path) -> None:
        pack = write_datapack(tmp_path / "pack", [81, 0], [82, 5])
        datapack = parse_datapack(pack)
        assert (datapack.min_format, datapack.max_format) == (81, 82)

    def test_zipped_pack_formats(self, tmp_path: Path) -> None:
        pack = write_zipped_datapack(tmp_path / "pack.zip", 81, 82)
        datapack = parse_datapack(pack)
        assert (datapack.min_format, datapack.max_format) == (81, 82)

    def test_invalid_json_raises_click_exception(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "pack.mcmeta").write_text("{ not json", encoding="utf-8")

        with pytest.raises(click.ClickException):
            parse_datapack(pack)

    def test_missing_format_raises_click_exception(self, tmp_path: Path) -> None:
        pack = tmp_path / "pack"
        pack.mkdir()
        (pack / "pack.mcmeta").write_text(json.dumps({"pack": {}}), encoding="utf-8")

        with pytest.raises(click.ClickException):
            parse_datapack(pack)

    def test_empty_format_list_raises_click_exception(self, tmp_path: Path) -> None:
        pack = write_datapack(tmp_path / "pack", [], [])

        with pytest.raises(click.ClickException, match="Invalid pack format"):
            parse_datapack(pack)
