"""Shared fixtures for the beet tests."""

from collections.abc import Iterator

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.output import DummyOutput


@pytest.fixture(autouse=True)
def plain_output() -> Iterator[None]:
    """beet prints through prompt_toolkit, which needs a real console on Windows."""
    with create_app_session(output=DummyOutput()):
        yield
