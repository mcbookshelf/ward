"""Tests for version curation in the environment selection helpers."""

from collections.abc import Iterator
from unittest.mock import Mock, patch

import pytest
import rich_click as click

from mcward import Version
from mcward.cli import environments
from mcward.cli.environments import curate_versions
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
