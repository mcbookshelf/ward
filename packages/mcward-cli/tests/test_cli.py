"""Tests for the CLI entry point and default-command routing."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mcward.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestDefaultCommandRouting:
    """Test how the group decides between subcommands and the default test command."""

    def test_help_lists_commands(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for command in ("clean", "install", "list", "start", "status", "stop", "test"):
            assert command in result.output

    def test_unknown_command_is_an_error(self, runner: CliRunner) -> None:
        """A typo'd subcommand must not silently run zero tests."""
        result = runner.invoke(cli, ["instal"])
        assert result.exit_code != 0
        assert "No such command" in result.output

    def test_selector_routes_to_test(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A namespaced selector runs the test command."""
        monkeypatch.chdir(tmp_path)  # no datapacks here
        result = runner.invoke(cli, ["mypack:*"])
        assert "Datapack not found" in result.output

    def test_bare_invocation_routes_to_test(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No arguments at all defaults to the test command."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, [])
        assert "Datapack not found" in result.output

    def test_option_routes_to_test(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Leading test options default to the test command."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["-p", "nonexistent/*"])
        assert "Datapack not found" in result.output

    def test_subcommand_help_works(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["test", "--help"])
        assert result.exit_code == 0
        assert "SELECTOR" in result.output.upper()


class TestWorldOption:
    """Test where the test command takes its world from."""

    @pytest.fixture
    def project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        pack = tmp_path / "pack"
        (pack / "data").mkdir(parents=True)
        (pack / "pack.mcmeta").write_text('{"pack": {"min_format": 101, "max_format": 101}}')
        for name in ("map", "other"):
            (tmp_path / name).mkdir()
            (tmp_path / name / "level.dat").write_text("level")
        monkeypatch.chdir(tmp_path)
        return tmp_path

    def invoke(self, runner: CliRunner, args: list[str]) -> tuple:
        session = SimpleNamespace(failed=False, versions=())
        with patch("mcward.cli.commands.test.run_session", return_value=session) as run:
            result = runner.invoke(cli, ["test", "-p", "pack", *args])
        return result, run

    def test_no_world_by_default(self, runner: CliRunner, project: Path) -> None:
        result, run = self.invoke(runner, [])
        assert result.exit_code == 0, result.output
        assert run.call_args.kwargs["world"] is None

    def test_option_names_the_world(self, runner: CliRunner, project: Path) -> None:
        result, run = self.invoke(runner, ["--world", "map"])
        assert result.exit_code == 0, result.output
        assert run.call_args.kwargs["world"] == Path("map")

    def test_ward_toml_names_the_world(self, runner: CliRunner, project: Path) -> None:
        (project / "ward.toml").write_text('world = "map"\n')
        result, run = self.invoke(runner, [])
        assert result.exit_code == 0, result.output
        assert run.call_args.kwargs["world"].resolve() == (project / "map").resolve()

    def test_option_wins_over_ward_toml(self, runner: CliRunner, project: Path) -> None:
        (project / "ward.toml").write_text('world = "map"\n')
        result, run = self.invoke(runner, ["--world", "other"])
        assert result.exit_code == 0, result.output
        assert run.call_args.kwargs["world"] == Path("other")

    def test_missing_world_is_an_error(self, runner: CliRunner, project: Path) -> None:
        result, run = self.invoke(runner, ["--world", "absent"])
        assert result.exit_code != 0
        run.assert_not_called()

    def test_invalid_ward_toml_is_an_error(self, runner: CliRunner, project: Path) -> None:
        (project / "ward.toml").write_text("world = 3\n")
        result, run = self.invoke(runner, [])
        assert result.exit_code != 0
        assert "world must be the path" in result.output
        run.assert_not_called()

    def test_watch_also_watches_the_world(self, runner: CliRunner, project: Path) -> None:
        with patch("mcward.cli.commands.test.watch_tests") as watch:
            result = runner.invoke(cli, ["test", "-p", "pack", "--world", "map", "--watch"])
        assert result.exit_code == 0, result.output
        assert watch.call_args.args[2] == [(project / "pack").resolve(), Path("map")]
