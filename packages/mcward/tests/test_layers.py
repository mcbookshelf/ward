"""The core imports nothing from the extras: a base install has no click, rich or beet."""

import ast
from pathlib import Path

import pytest

import mcward

PACKAGE = Path(mcward.__file__).parent
EXTRAS = {"beet", "click", "mecha", "questionary", "rich", "rich_click", "watchfiles"}
OWN_EXTRAS = {"mcward.beet", "mcward.cli", "mcward.mecha"}


def imported(tree: ast.Module, top_level_only: bool) -> set[str]:
    nodes = tree.body if top_level_only else ast.walk(tree)
    names: set[str] = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


@pytest.mark.parametrize("module", sorted(PACKAGE.glob("*.py")), ids=lambda path: path.name)
def test_core_module_imports_no_extra(module: Path) -> None:
    # The package's __init__ imports the CLI inside its console script, after checking for it
    tree = ast.parse(module.read_text(encoding="utf-8"))
    names = imported(tree, top_level_only=module.name == "__init__.py")
    roots = {name.split(".")[0] for name in names}
    assert not roots & EXTRAS
    assert not {name for name in names if name.startswith(tuple(OWN_EXTRAS))}
