"""Decide what a generated command tree means for the release; --check changes nothing."""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "packages" / "mcward-beet" / "src" / "mcward" / "mecha" / "resources"

type Trees = dict[str, object]


@dataclass(frozen=True)
class Decision:
    """What the generated trees call for: a release, an error (rewritten), or files to drop."""

    release: str | None = None
    rewritten: list[str] = field(default_factory=list)
    duplicate: str | None = None
    reordered: list[str] = field(default_factory=list)


def decide(generated: Trees, committed: Trees) -> Decision:
    """``generated`` and ``committed`` map file names to their parsed tree."""
    reordered = [name for name in committed if name in generated]
    rewritten = [name for name in reordered if generated[name] != committed[name]]
    if rewritten:
        return Decision(rewritten=rewritten)

    new = sorted((name for name in generated if name not in committed), key=_version)
    if not new:
        return Decision(reordered=reordered)
    name = new[-1]
    earlier = [other for other in committed if _version(other) < _version(name)]
    closest = max(earlier, key=_version, default=None)
    if closest is not None and generated[name] == committed[closest]:
        return Decision(duplicate=name, reordered=reordered)
    return Decision(release=name.removesuffix(".json"), reordered=reordered)


def _version(name: str) -> tuple[int, ...]:
    return tuple(int(part) for part in name.removesuffix(".json").split("."))


def _committed() -> Trees:
    relative = RESOURCES.relative_to(ROOT).as_posix()
    listed = _git("ls-files", "--", relative).split()
    return {Path(path).name: json.loads(_git("show", f"HEAD:{path}")) for path in listed}


def _generated() -> Trees:
    return {
        file.name: json.loads(file.read_text(encoding="utf-8")) for file in RESOURCES.glob("*.json")
    }


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Only report, change nothing")
    check = parser.parse_args().check

    decision = decide(_generated(), _committed())
    if decision.rewritten:
        names = ", ".join(decision.rewritten)
        print(
            f"::error::the command tree changed for an already released mod version ({names}); "
            "commands must only change alongside a mod version bump"
        )
        return 1
    if not check:
        # Key order is not semantic: drop the rewrite so only real changes get committed
        for name in decision.reordered:
            _git("checkout", "-q", "--", (RESOURCES / name).relative_to(ROOT).as_posix())
        if decision.duplicate:
            (RESOURCES / decision.duplicate).unlink()

    if decision.release:
        print(f"new command tree for mod {decision.release}")
        if not check and (output := os.environ.get("GITHUB_OUTPUT")):
            with open(output, "a", encoding="utf-8") as file:
                file.write(f"version={decision.release}\n")
    elif decision.duplicate:
        print(f"{decision.duplicate} is identical to the previous tree, nothing to release")
    else:
        print("command tree unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
