"""Tests for the watch loop: which events run the tests, and with which selector."""

import pytest
import rich_click as click
from click.testing import CliRunner

from mcward.cli import cli
from mcward.cli.watch import CHANGE, ESCAPE, INTERRUPT, WatchLoop


class Recorder:
    def __init__(self) -> None:
        self.selectors: list[str] = []

    def __call__(self, selector: str) -> None:
        self.selectors.append(selector)


def feed(loop: WatchLoop, *events: str) -> bool:
    """Handle the events like the watch thread does, running after each one."""
    alive = True
    for event in events:
        alive = loop.handle(event)
        loop.run_pending()
    return alive


@pytest.fixture
def run() -> Recorder:
    return Recorder()


@pytest.fixture
def loop(run: Recorder) -> WatchLoop:
    loop = WatchLoop(run, "pack:*")
    loop.run_pending()
    return loop


def test_runs_once_at_start(run: Recorder, loop: WatchLoop) -> None:
    assert run.selectors == ["pack:*"]


def test_change_runs_again(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, CHANGE, CHANGE)
    assert run.selectors == ["pack:*"] * 3


def test_enter_and_a_run_again(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, "\r", "a")
    assert run.selectors == ["pack:*"] * 3


def test_unknown_key_does_nothing(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, "x", "1")
    assert run.selectors == ["pack:*"]


def test_typed_selector_narrows_the_next_runs(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, "p", *"pack:chest/*", "\r", CHANGE)
    assert run.selectors == ["pack:*", "pack:chest/*", "pack:chest/*"]


def test_a_goes_back_to_every_test(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, "p", *"pack:one", "\r", "a")
    assert run.selectors[-1] == "pack:*"


def test_backspace_edits_the_selector(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, "p", *"pack:onx", "\b", "e", "\r")
    assert run.selectors[-1] == "pack:one"


def test_empty_selector_runs_every_test(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, "p", "\r")
    assert run.selectors == ["pack:*", "pack:*"]


def test_keys_are_text_while_typing(run: Recorder, loop: WatchLoop) -> None:
    """q and a are part of the selector, not commands, until Enter."""
    assert feed(loop, "p", "q", "a", "\r")
    assert run.selectors[-1] == "qa"


def test_change_waits_for_the_selector(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, "p", "x", CHANGE)
    assert run.selectors == ["pack:*"]
    feed(loop, "\r")
    assert run.selectors == ["pack:*", "x"]


def test_escape_cancels_the_selector(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, "p", *"pack:one", ESCAPE)
    assert run.selectors == ["pack:*"]
    feed(loop, CHANGE)
    assert run.selectors == ["pack:*", "pack:*"]


def test_change_while_typing_runs_after_escape(run: Recorder, loop: WatchLoop) -> None:
    feed(loop, "p", CHANGE, ESCAPE)
    assert run.selectors == ["pack:*", "pack:*"]


@pytest.mark.parametrize("key", ["q", INTERRUPT])
def test_quit(loop: WatchLoop, key: str) -> None:
    assert not loop.handle(key)


def test_interrupt_quits_while_typing(loop: WatchLoop) -> None:
    loop.handle("p")
    assert not loop.handle(INTERRUPT)


def test_failed_run_keeps_watching(capsys: pytest.CaptureFixture[str]) -> None:
    calls = []

    def run(selector: str) -> None:
        calls.append(selector)
        raise click.ClickException("No compatible versions")

    loop = WatchLoop(run, "*:*")
    loop.run_pending()
    assert feed(loop, CHANGE)
    assert calls == ["*:*", "*:*"]
    assert "No compatible versions" in capsys.readouterr().out


def test_watch_rejects_the_github_reporter() -> None:
    result = CliRunner().invoke(cli, ["test", "--watch", "--reporter", "github"])
    assert result.exit_code != 0
    assert "--watch only works with the live reporter" in result.output
