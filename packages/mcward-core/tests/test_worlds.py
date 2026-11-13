"""Tests for the world setting of ward.toml."""

from pathlib import Path

import pytest

from mcward import WardError, configured_world


class TestConfiguredWorld:
    def test_no_file_means_no_world(self, tmp_path: Path) -> None:
        assert configured_world(tmp_path) is None

    def test_file_without_world_means_no_world(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text("[coverage]\nminimum = 80\n")
        assert configured_world(tmp_path) is None

    def test_path_is_relative_to_the_file(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text('world = "maps/arena"\n')
        assert configured_world(tmp_path) == tmp_path / "maps" / "arena"

    def test_default_directory_is_the_working_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "ward.toml").write_text('world = "world"\n')
        monkeypatch.chdir(tmp_path)
        assert configured_world() == tmp_path / "world"

    def test_world_must_be_a_path(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text("world = true\n")
        with pytest.raises(WardError, match="world must be the path"):
            configured_world(tmp_path)

    def test_invalid_file_is_an_error(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text("world = \n")
        with pytest.raises(WardError, match=r"Invalid ward\.toml"):
            configured_world(tmp_path)
