"""mcward, mcward-cli and mcward-beet release together, so each pins the others exactly."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PIN = re.compile(r"^(mcward(?:-cli|-beet)?)(?:\[\w+\])?==(.+)$")


def requirements(path: Path) -> list[str]:
    project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]
    extras = project.get("optional-dependencies", {}).values()
    return [*project.get("dependencies", []), *(req for extra in extras for req in extra)]


def test_every_pin_is_the_released_version() -> None:
    root = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = root["project"]["version"]
    files = [ROOT / "pyproject.toml", *sorted((ROOT / "packages").glob("mcward-*/pyproject.toml"))]
    pins = {}
    for file in files:
        for requirement in requirements(file):
            if match := PIN.match(requirement):
                pins[f"{file.parent.name}: {requirement}"] = match[2]
            else:
                assert not requirement.startswith("mcward"), f"{file}: {requirement} is not pinned"

    assert len(pins) == 6
    assert set(pins.values()) == {version}, pins
