"""Shared fixtures for the CLI tests."""

import pytest
import rich_click as click


@pytest.fixture(autouse=True)
def plain_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """On a CI runner rich-click colors its output, which cuts the text the tests look for."""
    monkeypatch.setattr(click.rich_click, "FORCE_TERMINAL", False)
