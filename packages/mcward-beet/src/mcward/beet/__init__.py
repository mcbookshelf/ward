"""Beet integration for Ward."""

from .commands import test, test_project
from .plugin import TestFunction, beet_default

__all__ = [
    "TestFunction",
    "test",
    "test_project",
    "beet_default",
]
