"""Tests for reading ward.toml."""

from pathlib import Path

import pytest

from mcward import CoverageMinimum, WardConfig, WardError


class TestWorld:
    def test_no_file_means_no_world(self, tmp_path: Path) -> None:
        assert WardConfig.load(tmp_path).world is None

    def test_file_without_world_means_no_world(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text("[coverage]\nminimum = 80\n")
        assert WardConfig.load(tmp_path).world is None

    def test_path_is_relative_to_the_file(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text('world = "maps/arena"\n')
        assert WardConfig.load(tmp_path).world == tmp_path / "maps" / "arena"

    def test_default_directory_is_the_working_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "ward.toml").write_text('world = "world"\n')
        monkeypatch.chdir(tmp_path)
        assert WardConfig.load().world == tmp_path / "world"

    def test_world_must_be_a_path(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text("world = true\n")
        with pytest.raises(WardError, match="world must be the path"):
            WardConfig.load(tmp_path)

    def test_invalid_file_is_an_error(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text("world = \n")
        with pytest.raises(WardError, match=r"Invalid ward\.toml"):
            WardConfig.load(tmp_path)


class TestWardConfig:
    def test_one_file_gives_world_and_coverage(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text('world = "map"\n[coverage]\nminimum = 80\n')
        config = WardConfig.load(tmp_path)
        assert config.world == tmp_path / "map"
        assert config.coverage.minimum == CoverageMinimum(total=80)

    def test_coverage_must_be_a_table(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text("coverage = 80\n")
        with pytest.raises(WardError, match="coverage must be a table"):
            WardConfig.load(tmp_path)

    def test_origin_is_a_column(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text("origin = [120, -4500]\n")
        assert WardConfig.load(tmp_path).origin == (120, -4500)

    @pytest.mark.parametrize("value", ["[1, 2, 3]", "[1.5, 2]", '"0 0"', "[true, 1]"])
    def test_origin_must_be_two_whole_numbers(self, tmp_path: Path, value: str) -> None:
        (tmp_path / "ward.toml").write_text(f"origin = {value}\n")
        with pytest.raises(WardError, match="origin must be"):
            WardConfig.load(tmp_path)
