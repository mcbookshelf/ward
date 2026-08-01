"""Inspired by a beet packtest plugin https://github.com/CarbonSmasher/packtest-beet/blob/main/packtest_beet/nesting.py"""

import math
import re
from dataclasses import dataclass
from pathlib import Path

from beet import Context, JsonFile
from tokenstream import TokenStream, set_location

from mcward.beet.plugin import TestFunction
from mecha import (
    AstRoot,
    CompilationDatabase,
    FileTypeCompilationUnitProvider,
    Mecha,
    Parser,
)

RESOURCES_DIR = Path(__file__).parent / "resources"
_VERSION = re.compile(
    r"v?(?P<major>\d+)(?:\.(?P<minor>\d+|[xX*]))?(?:\.(?P<patch>\d+|[xX*]))?"
    r"(?:-[0-9A-Za-z.]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


@dataclass(frozen=True, slots=True)
class AstTestRoot(AstRoot):
    """Ast test root node.

    Technically not required but it's good practice to have custom root nodes for custom
    file types. Makes it easier to target with @rule and bolt won't treat it as a plain module.
    """


@dataclass
class TestRootParser:
    """Parser for test root."""

    database: CompilationDatabase
    root_parser: Parser

    def __call__(self, stream: TokenStream):
        if "test_file" not in stream.data:
            test_file = isinstance(self.database.current, TestFunction)
            with stream.provide(test_file=test_file):
                node = self.root_parser(stream)
            if test_file and isinstance(node, AstRoot):
                test_root = AstTestRoot(commands=node.commands)
                node = set_location(test_root, node)
            return node
        return self.root_parser(stream)


def beet_default(ctx: Context) -> None:
    """Register the ward command tree with mecha and compile test functions."""
    ctx.require("mcward.beet.plugin")

    version = ctx.meta.get("ward", {}).get("version")
    command_tree = JsonFile(source_path=_resolve_command_tree(version))

    mc = ctx.inject(Mecha)
    mc.providers.append(FileTypeCompilationUnitProvider([TestFunction]))
    mc.spec.add_commands(command_tree.data)
    mc.spec.parsers["root"] = TestRootParser(mc.database, mc.spec.parsers["root"])


def _resolve_command_tree(version: str | None) -> Path:
    """Return the newest command tree at or below the given version.

    Trees are only kept when they differ from the previous one, so a version
    without its own file resolves to the closest older tree. Missing or
    wildcard components mean newest: "1.2.1+26.2", "1.2", "1.x", and
    "latest" or "*" for the newest tree.
    """
    trees = {tuple(map(int, p.stem.split("."))): p for p in RESOURCES_DIR.glob("*.json")}
    spec = str(version).strip() if version is not None else "*"
    if spec in ("*", "latest"):
        return trees[max(trees)]

    match = _VERSION.match(spec)
    minor = match and _part(match.group("minor"))
    patch = match and _part(match.group("patch"))
    if match is None or (minor is None and patch is not None):
        err = f"Invalid ward version {version!r} (expected e.g. '1.2', '1.2.x' or 'latest')."
        raise ValueError(err)
    inf = math.inf
    target = (
        int(match.group("major")),
        inf if minor is None else minor,
        inf if patch is None else patch,
    )

    closest = max((key for key in trees if key <= target), default=None)
    if closest is None:
        available = ", ".join(trees[key].stem for key in sorted(trees))
        raise ValueError(f"No ward command tree for version {version!r} (available: {available}).")
    return trees[closest]


def _part(value: str | None) -> int | None:
    """A version component, where wildcards count as unspecified."""
    return int(value) if value is not None and value.isdigit() else None
