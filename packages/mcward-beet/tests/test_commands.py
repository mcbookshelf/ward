"""Tests for the beet test command."""

import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from beet import Project
from beet.toolchain.cli import beet as beet_cli
from click.testing import CliRunner

# Importing registers the test command on the beet CLI group,
# independently of the entry-point metadata of the installed distribution
import mcward.beet.commands  # noqa: F401
from mcward.beet.commands import _build_pack


def pack_files(pack: Path) -> list[str]:
    """The file names inside a built (zipped) pack."""
    with zipfile.ZipFile(pack) as archive:
        return archive.namelist()


@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal beet project with one function and one test function."""
    config = {
        "name": "demo",
        "data_pack": {"min_format": 81, "max_format": 82, "load": ["src"]},
    }
    (tmp_path / "beet.json").write_text(json.dumps(config), encoding="utf-8")

    functions = tmp_path / "src" / "data" / "demo" / "function"
    functions.mkdir(parents=True)
    (functions / "hello.mcfunction").write_text("say hello", encoding="utf-8")

    tests = tmp_path / "src" / "data" / "demo" / "test"
    tests.mkdir(parents=True)
    (tests / "example.mcfunction").write_text("assert entity @s", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestBuildPack:
    """Test building the project into a testable data pack."""

    def test_built_pack_contains_test_functions(self, project_dir: Path, tmp_path: Path) -> None:
        """The test/ folder ships with the built (zipped) pack without an explicit require."""
        pack, _ = _build_pack(Project(), tmp_path / "out")

        assert pack.suffix == ".zip"
        files = pack_files(pack)
        assert "pack.mcmeta" in files
        assert "data/demo/function/hello.mcfunction" in files
        assert "data/demo/test/example.mcfunction" in files

    def test_built_pack_keeps_format_range(self, project_dir: Path, tmp_path: Path) -> None:
        pack, _ = _build_pack(Project(), tmp_path / "out")

        with zipfile.ZipFile(pack) as archive:
            meta = json.loads(archive.read("pack.mcmeta"))
        assert meta["pack"]["min_format"] == 81
        assert meta["pack"]["max_format"] == 82

    def test_source_map_points_at_original_files(self, project_dir: Path, tmp_path: Path) -> None:
        """Test ids map back to the workspace files they were loaded from."""
        _, sources = _build_pack(Project(), tmp_path / "out")

        expected = project_dir / "src" / "data" / "demo" / "test" / "example.mcfunction"
        assert sources == {"demo:example": expected}

    def test_explicit_require_stays_compatible(self, project_dir: Path, tmp_path: Path) -> None:
        """A project already requiring the plugin builds fine (idempotent plugin)."""
        config = json.loads((project_dir / "beet.json").read_text(encoding="utf-8"))
        config["require"] = ["mcward.beet.plugin"]
        (project_dir / "beet.json").write_text(json.dumps(config), encoding="utf-8")

        pack, _ = _build_pack(Project(), tmp_path / "out")

        assert "data/demo/test/example.mcfunction" in pack_files(pack)


class TestBeetTestCommand:
    """Test the CLI command end to end with the test run stubbed out."""

    def invoke(self, runner: CliRunner, args: list[str], failed: bool = False) -> tuple:
        """Invoke beet test with the Ward machinery stubbed, returning (result, calls)."""
        calls = SimpleNamespace(packs=None, selector=None, versions=None, shipped_files=[])

        def fake_run_tests_live(datapacks, envs, selector, resolve=None):
            calls.packs = list(datapacks)
            calls.selector = selector
            # Snapshot now: the built pack's TemporaryDirectory is gone once the command returns
            calls.shipped_files = pack_files(datapacks[0])
            return SimpleNamespace(failed=failed)

        def fake_get(version):
            calls.versions = (calls.versions or []) + [version]
            return SimpleNamespace(version=version)

        with (
            patch("mcward.beet.commands.start_environments", side_effect=lambda envs: envs),
            patch("mcward.beet.commands.live.run", side_effect=fake_run_tests_live),
            patch("mcward.beet.commands.manager") as mock_manager,
        ):
            mock_manager.get.side_effect = fake_get
            result = runner.invoke(beet_cli, args, obj=Project())

        return result, calls

    def test_runs_tests_on_built_pack(self, project_dir: Path, runner: CliRunner) -> None:
        result, calls = self.invoke(runner, ["test", "-v", "26.1.2", "demo:*"])

        assert result.exit_code == 0, result.output
        assert calls.selector == "demo:*"
        assert calls.versions == ["26.1.2"]

        # The pack passed to the run is the built one, tests included
        assert len(calls.packs) == 1
        assert "data/demo/test/example.mcfunction" in calls.shipped_files
        assert "data/demo/function/hello.mcfunction" in calls.shipped_files

    def test_selector_defaults_to_everything(self, project_dir: Path, runner: CliRunner) -> None:
        result, calls = self.invoke(runner, ["test", "-v", "26.1.2"])

        assert result.exit_code == 0, result.output
        assert calls.selector == "*:*"

    def test_exits_nonzero_when_tests_fail(self, project_dir: Path, runner: CliRunner) -> None:
        result, _ = self.invoke(runner, ["test", "-v", "26.1.2"], failed=True)

        assert result.exit_code == 1

    def test_versions_resolved_from_pack_formats(
        self, project_dir: Path, runner: CliRunner
    ) -> None:
        """Without -v, compatible versions come from the built pack's format range."""
        with patch(
            "mcward.beet.commands.select_compatible", return_value=["26.1.2"]
        ) as mock_select:
            result, calls = self.invoke(runner, ["test"])

        assert result.exit_code == 0, result.output
        mock_select.assert_called_once_with(81, 82)
        assert calls.versions == ["26.1.2"]
