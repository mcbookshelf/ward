from typing import ClassVar

from beet import Context, NamespaceFile, NamespaceFileScope, TextFileBase


class TestFunction(TextFileBase, NamespaceFile):
    """A .mcfunction under data/<ns>/test/."""

    scope: ClassVar[NamespaceFileScope] = ("test",)
    extension: ClassVar[str] = ".mcfunction"


def beet_default(ctx: Context) -> None:
    """Include test functions from the test folder."""
    # The beet test command requires this plugin automatically
    # A project may also require it itself, so the append has to be idempotent
    if TestFunction not in ctx.data.extend_namespace:
        ctx.data.extend_namespace.append(TestFunction)
