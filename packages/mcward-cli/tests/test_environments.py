"""Tests for version curation and selection in the environment helpers."""

from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest
import rich_click as click

from mcward import (
    InstalledEnvironment,
    InstallError,
    MissingFeatureError,
    RunningEnvironment,
    Status,
    Version,
)
from mcward.cli import environments
from mcward.cli.environments import curate_versions
from mcward.cli.session import check_features
from mcward.cli.ui import select


class TestCurateVersions:
    """Test the curated version listing policy."""

    def test_keeps_newest_snapshot_only(self) -> None:
        """Only the newest snapshot per (year, major) line survives."""
        versions = [
            Version.parse("26.2-snapshot-6"),
            Version.parse("26.2-snapshot-5"),
            Version.parse("26.1.2"),
            Version.parse("26.1.1"),
        ]
        names = [v.name for v in curate_versions(versions)]
        assert names == ["26.2-snapshot-6", "26.1.2", "26.1.1"]


class TestSelectCompatible:
    """Test which versions a pack format range gives."""

    @pytest.fixture
    def two_lines(self) -> Iterator[None]:
        versions = [Version.parse(name) for name in ("26.2", "26.1.2", "26.1.1")]
        with patch.object(environments.manager, "list_compatible", return_value=versions):
            yield

    def test_without_terminal_every_line_is_tested(
        self, two_lines: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        assert environments.select_compatible(80, 82) == ["26.2", "26.1.2"]

    def test_cancelled_prompt_exits_like_an_interrupt(
        self, two_lines: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        prompt = Mock()
        prompt.return_value.ask.return_value = None
        with patch("questionary.select", prompt), pytest.raises(SystemExit) as exit:
            environments.select_compatible(80, 82)
        assert exit.value.code == 130


def test_select_without_terminal_asks_for_the_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(click.UsageError, match="No terminal"):
        select("Select version to stop:", ["26.2", "26.1.2"])


class TestModUpdate:
    """An installed environment gets the newest mod before it starts."""

    @staticmethod
    def installed(update: Mock | None = None) -> Mock:
        env = Mock(spec=InstalledEnvironment, version=Version.parse("26.3"))
        env.update = update or Mock(return_value=True)
        env.start.return_value = Mock(version=env.version, process="(pid: 1, port: 2)")
        return env

    def start(self, env: Mock, outdated: tuple[str, str] | None) -> None:
        with patch.object(environments.manager, "outdated_mod", return_value=outdated):
            environments._start_environment(env, Mock())

    def test_outdated_mod_is_updated_then_started(self, capsys: pytest.CaptureFixture[str]) -> None:
        env = self.installed()
        self.start(env, ("1.2.1", "1.2.2"))
        env.update.assert_called_once()
        env.start.assert_called_once()
        assert "Updated Ward for 26.3: 1.2.1 to 1.2.2" in capsys.readouterr().out

    def test_skipped_update_is_not_announced(self, capsys: pytest.CaptureFixture[str]) -> None:
        env = self.installed(Mock(return_value=False))
        self.start(env, ("1.2.1", "1.2.2"))
        env.start.assert_called_once()
        assert "Updated" not in capsys.readouterr().out

    def test_failed_update_starts_the_old_mod(self, capsys: pytest.CaptureFixture[str]) -> None:
        env = self.installed(Mock(side_effect=InstallError("Modrinth is down")))
        self.start(env, ("1.2.1", "1.2.2"))
        env.start.assert_called_once()
        assert "Could not update Ward for 26.3" in capsys.readouterr().out

    def test_up_to_date_mod_is_not_updated(self) -> None:
        env = self.installed()
        self.start(env, None)
        env.update.assert_not_called()


class TestCheckFeatures:
    def env(self, features: frozenset[str]) -> Mock:
        env = Mock()
        env.version = Version.parse("26.3")
        env.status.return_value = Status(ready=True, features=features)
        env.require = lambda **wanted: RunningEnvironment.require(env, **wanted)
        return env

    def test_server_that_loads_worlds_passes(self) -> None:
        check_features([self.env(frozenset({"worlds"}))], worlds=True)

    def test_plain_run_needs_no_feature(self) -> None:
        env = self.env(frozenset())
        check_features([env], worlds=None, origin=None)
        env.status.assert_not_called()

    def test_older_running_mod_names_the_restart(self) -> None:
        with (
            patch.object(environments.manager, "outdated_mod", return_value=("1.2.1", "1.2.2")),
            pytest.raises(click.ClickException, match="mcward stop 26.3"),
        ):
            check_features([self.env(frozenset())], worlds=True)

    def test_newest_mod_without_worlds_says_so(self) -> None:
        with (
            patch.object(environments.manager, "outdated_mod", return_value=None),
            pytest.raises(MissingFeatureError, match="Ward for Minecraft 26.3 cannot load a world"),
        ):
            check_features([self.env(frozenset())], worlds=True)

    def test_origin_needs_its_feature(self) -> None:
        with (
            patch.object(environments.manager, "outdated_mod", return_value=None),
            pytest.raises(MissingFeatureError, match="cannot place tests at a fixed origin"),
        ):
            check_features([self.env(frozenset({"worlds"}))], worlds=True, origin=(0, 0))
