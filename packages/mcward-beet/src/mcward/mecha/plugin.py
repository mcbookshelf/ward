"""Parse test functions with the ward command tree.
Inspired by https://github.com/CarbonSmasher/packtest-beet/blob/main/packtest_beet/nesting.py"""

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
    """Root of a test file: rules can target it, and bolt won't treat it as a plain module."""


@dataclass
class TestRootParser:
    """Wraps the root parser so test files yield an AstTestRoot."""

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
    command_tree = JsonFile(source_path=_command_tree(version))

    mc = ctx.inject(Mecha)
    mc.providers.append(FileTypeCompilationUnitProvider([TestFunction]))
    mc.spec.add_commands(command_tree.data)
    mc.spec.parsers["root"] = TestRootParser(mc.database, mc.spec.parsers["root"])


def _command_tree(version: str | None) -> Path:
    """The newest bundled command tree at or below the given Ward version."""
    trees = {tuple(map(int, p.stem.split("."))): p for p in RESOURCES_DIR.glob("*.json")}
    target = _parse_version(version)

    if target is None:
        return trees[max(trees)]

    closest = max((key for key in trees if key <= target), default=None)
    if closest is None:
        available = ", ".join(trees[key].stem for key in sorted(trees))
        raise ValueError(f"No ward command tree for version {version!r} (available: {available}).")

    return trees[closest]


def _parse_version(version: str | float | None) -> tuple[int, float, float] | None:
    """Parse a Ward version specification into a comparable version."""
    spec = str(version).strip() if version is not None else "*"
    if spec in ("*", "latest"):
        return None

    match = _VERSION.fullmatch(spec)
    if match is not None:
        major, minor, patch = match.groups()
        major = int(major)
        minor = int(minor) if minor is not None and minor.isdigit() else None
        patch = int(patch) if patch is not None and patch.isdigit() else None

        # patch requires a concrete minor version
        if minor is not None or patch is None:
            return (
                major,
                math.inf if minor is None else minor,
                math.inf if patch is None else patch,
            )

    raise ValueError(f"Invalid ward version {version!r} (expected '1.2', '1.2.x' or 'latest').")
