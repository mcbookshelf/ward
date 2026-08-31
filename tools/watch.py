"""Print the newest Minecraft version Ward has not been checked against.

    uv run tools/watch.py

Prints nothing when up to date. Stateless: a version is "new" when
fabric-loader supports it but neither a published Modrinth version nor the
current gradle.properties target covers it. The calling workflow hands the
version to the release-pr workflow.
"""

import sys

import httpx
from release import MODRINTH_API, PROJECT_ID, USER_AGENT, read_gradle_property

FABRIC_META = "https://meta.fabricmc.net/v2"


def main() -> int:
    current = read_gradle_property("minecraft_version")

    with httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT}) as client:
        supported = [entry["version"] for entry in get_json(client, f"{FABRIC_META}/versions/game")]
        published = {
            game_version
            for version in get_json(client, f"{MODRINTH_API}/project/{PROJECT_ID}/version")
            for game_version in version["game_versions"]
        }

    # The list is newest-first, so everything above the first known version is a candidate
    # Everything below it was processed in an earlier era
    candidates = []
    for version in supported:
        if version == current or version in published:
            break
        candidates.append(version)

    if candidates:
        print(candidates[0])
    return 0


def get_json(client: httpx.Client, url: str):
    response = client.get(url)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    sys.exit(main())
