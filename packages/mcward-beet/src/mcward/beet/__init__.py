"""Beet integration for Ward.

The plugin is required by its module path (``require: mcward.beet.plugin``);
this package exports the Python-facing API for custom toolchains.
"""

from .commands import test, test_project
from .plugin import TestFunction, beet_default

__all__ = [
    "TestFunction",
    "test",
    "test_project",
    "beet_default",
]
