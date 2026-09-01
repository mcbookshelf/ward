from importlib.util import find_spec

if find_spec("mecha") is None:
    raise ImportError("mcward.mecha plugin requires mecha extra: pip install mcward-beet[mecha]")

from .plugin import beet_default

__all__ = [
    "beet_default",
]
