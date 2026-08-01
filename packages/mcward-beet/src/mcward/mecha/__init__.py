from importlib.util import find_spec

if find_spec("mecha") is None:
    raise ImportError(
        "The mcward.mecha plugin requires the mecha extra: pip install mcward-beet[mecha]"
    )

from .plugin import beet_default

__all__ = [
    "beet_default",
]
