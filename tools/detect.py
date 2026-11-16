"""Print the newest Minecraft version Fabric supports and Ward has no release for."""

import sys

import httpx
from release import (
    FABRIC_META,
    MODRINTH_API,
    PROJECT_ID,
    USER_AGENT,
    get_json,
    read_gradle_property,
)


def main() -> int:
    current = read_gradle_property("minecraft_version")

    with httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT}) as client:
        supported = [entry["version"] for entry in get_json(client, f"{FABRIC_META}/versions/game")]
        published = {
            game_version
            for version in get_json(client, f"{MODRINTH_API}/project/{PROJECT_ID}/version")
            for game_version in version["game_versions"]
        }

    # Newest first: everything above the first known version is new
    candidates = []
    for version in supported:
        if version == current or version in published:
            break
        candidates.append(version)

    if candidates:
        print(candidates[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
