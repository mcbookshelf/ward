"""Bump the version of a Ward release stream.

    uv run tools/bump.py python 1.2.0        # pyproject.toml + lockfile
    uv run tools/bump.py java 1.2.0          # mod_version in gradle.properties
    uv run tools/bump.py minecraft 26.2      # retarget the mod's Minecraft

minecraft also resolves the fabric-loader and fabric-api builds for that
version, and exits 2 when the toolchain has no build for it yet (retry later).
Bumping is the release request: once the change lands, release.py publishes it.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

import httpx
from release import FABRIC_API_ID, MODRINTH_API, USER_AGENT

ROOT = Path(__file__).resolve().parent.parent

FABRIC_META = "https://meta.fabricmc.net/v2"

RELEASE_PATTERN = re.compile(r"\d+\.\d+\.\d+")
MINECRAFT_PATTERN = re.compile(r"\d+\.\d+(\.\d+)?(-[\w.-]+)?")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stream",
        choices=("python", "java", "minecraft"),
        help="The version to bump",
    )
    parser.add_argument("version", help="The new version (e.g. 1.2.0)")
    args = parser.parse_args()

    pattern = MINECRAFT_PATTERN if args.stream == "minecraft" else RELEASE_PATTERN
    if not pattern.fullmatch(args.version):
        raise SystemExit(f"bump: {args.version!r} is not a valid {args.stream} version")

    match args.stream:
        case "python":
            # uv rewrites the root pyproject version and refreshes the lockfile
            subprocess.run(["uv", "version", args.version], check=True, cwd=ROOT, stdout=sys.stderr)
            return 0
        case "java":
            set_gradle_property("mod_version", args.version)
            return 0
        case _:
            return bump_minecraft(args.version)


def bump_minecraft(minecraft: str) -> int:
    """Retarget gradle.properties to the given Minecraft version.

    Resolves the matching fabric-loader and fabric-api; exits 2 when either
    has no build for the version yet.
    """
    with httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT}) as client:
        loaders = get_json(client, f"{FABRIC_META}/versions/loader/{minecraft}")
        if not loaders:
            print(f"bump: fabric loader does not support {minecraft} yet", file=sys.stderr)
            return 2
        # Loaders come newest-first, betas included, so prefer the newest stable one
        entry = next((x for x in loaders if x["loader"]["stable"]), loaders[0])
        loader = entry["loader"]["version"]

        versions = get_json(client, f"{MODRINTH_API}/project/{FABRIC_API_ID}/version")
        compatible = [v for v in versions if minecraft in v["game_versions"]]
        if not compatible:
            print(f"bump: no fabric-api build published for {minecraft} yet", file=sys.stderr)
            return 2
        fabric_api = compatible[0]["version_number"]

    set_gradle_property("minecraft_version", minecraft)
    set_gradle_property("loader_version", loader)
    set_gradle_property("fabric_api_version", fabric_api)
    return 0


def set_gradle_property(name: str, value: str) -> None:
    path = ROOT / "gradle.properties"
    content, count = re.subn(
        rf"^{name}=.+$",
        f"{name}={value}",
        path.read_text(encoding="utf-8"),
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise SystemExit(f"bump: {name} not found in gradle.properties")
    path.write_text(content, encoding="utf-8")
    print(f"bump: {name} set to {value}", file=sys.stderr)


def get_json(client: httpx.Client, url: str):
    response = client.get(url)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    sys.exit(main())
