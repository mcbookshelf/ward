"""CLI commands."""

from .daemon import start, status, stop
from .install import clean, install
from .list import list_versions
from .test import test

__all__ = [
    "clean",
    "install",
    "list_versions",
    "start",
    "status",
    "stop",
    "test",
]
