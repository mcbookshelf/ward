"""Release automation, driven by the versions committed to the tree.

    uv run tools/release.py python [--dry-run]   # the mcward packages, to PyPI
    uv run tools/release.py java [--dry-run]     # the ward mod, to Modrinth

A release happens when the version in the tree has no tag yet (see the
versioning section of CONTRIBUTING.md). Artifacts publish first and the tag
comes last with the GitHub release, so a partially failed run is simply
re-run: steps skip what already exists.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent

MODRINTH_API = "https://api.modrinth.com/v2"
PROJECT_ID = "arCLMKiz"  # https://modrinth.com/mod/ward
FABRIC_API_ID = "P7dR8mSH"  # https://modrinth.com/mod/fabric-api

# Modrinth's API rules require a uniquely identifying user agent
USER_AGENT = "mcbookshelf/ward release scripts (github.com/mcbookshelf/ward)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, what in (("python", "mcward packages"), ("java", "ward mod")):
        command = commands.add_parser(name, help=f"Release the {what}")
        command.add_argument("--dry-run", action="store_true", help="Only print the decision")

    args = parser.parse_args()
    os.chdir(ROOT)
    if args.command == "python":
        return release_python(args.dry_run)
    return release_java(args.dry_run)


def release_python(dry_run: bool) -> int:
    """Publish the mcward packages to PyPI when their version has no tag yet."""
    version = read_version(ROOT / "pyproject.toml")
    tag = f"v{version}"
    previous = last_tag("v[0-9]*", exclude="v*+*")

    if (skip := check_released("python", tag, previous, dry_run)) is not None:
        return skip

    # Stale artifacts of older versions must never reach `uv publish dist/*`
    shutil.rmtree(ROOT / "dist", ignore_errors=True)
    subprocess.run(["uv", "build", "--all-packages"], check=True)
    # Trusted publishing via OIDC mints one token covering every matching project
    # The dist/* default therefore uploads all packages in one go
    # --check-url tolerates a re-run by skipping files already on the index
    subprocess.run(["uv", "publish", "--check-url", "https://pypi.org/simple/"], check=True)

    notes = generate_notes(tag, previous)
    create_release(tag, f"mcward {version}", notes, assets=sorted(ROOT.glob("dist/*")))
    print(f"python: released {tag}")
    return 0


def release_java(dry_run: bool) -> int:
    """Build and publish the mod to Modrinth when its full version has no tag yet."""
    version = read_gradle_property("mod_version")
    minecraft = read_gradle_property("minecraft_version")
    tag = f"v{version}+{minecraft}"
    previous = last_tag("v[0-9]*+*")

    if (skip := check_released("java", tag, previous, dry_run)) is not None:
        return skip

    gradlew = str(ROOT / ("gradlew.bat" if os.name == "nt" else "gradlew"))
    subprocess.run([gradlew, "build"], check=True)
    jar = mod_jar()

    notes = generate_notes(tag, previous)
    publish_modrinth(version, minecraft, jar, changelog=notes)

    # Snapshot builds are prereleases
    prerelease = "-" in minecraft
    create_release(tag, f"Ward {version}+{minecraft}", notes, assets=[jar], prerelease=prerelease)
    print(f"java: released {tag}")
    return 0


def check_released(stream: str, tag: str, previous: str | None, dry_run: bool) -> int | None:
    """The early-exit code when there is nothing to do, or None to proceed."""
    if tag_exists(tag):
        print(f"{stream}: {tag} already released")
        return 0
    if dry_run:
        print(f"{stream}: would release {tag} (previous: {previous or 'none'})")
        return 0
    return None


def publish_modrinth(version: str, minecraft: str, jar: Path, changelog: str) -> None:
    """Upload the jar as a new Modrinth version, skipping an already published one."""
    if not (token := os.environ.get("MODRINTH_TOKEN", "")):
        raise SystemExit("release: MODRINTH_TOKEN is required")

    number = f"{version}+{minecraft}"
    headers = {"User-Agent": USER_AGENT, "Authorization": token}

    with httpx.Client(base_url=MODRINTH_API, headers=headers, timeout=120) as client:
        published = client.get(f"/project/{PROJECT_ID}/version")
        published.raise_for_status()
        if any(entry["version_number"] == number for entry in published.json()):
            print(f"modrinth: {number} already published")
            return

        data = {
            "project_id": PROJECT_ID,
            "name": f"[{minecraft}] Ward {version}",
            "version_number": number,
            "changelog": changelog,
            "game_versions": [minecraft],
            "version_type": "beta" if "-" in minecraft else "release",
            "loaders": ["fabric"],
            "featured": False,
            "dependencies": [{"project_id": FABRIC_API_ID, "dependency_type": "required"}],
            "file_parts": ["file"],
            "primary_file": "file",
        }
        response = client.post(
            "/version",
            data={"data": json.dumps(data)},
            files={"file": (jar.name, jar.read_bytes(), "application/java-archive")},
        )
        if response.is_error:
            raise SystemExit(
                f"release: modrinth publish failed ({response.status_code}): {response.text}"
            )

    print(f"modrinth: published {number} for {minecraft}")


def generate_notes(tag: str, previous: str | None) -> str:
    """Release notes GitHub generates from the merged PRs since the previous tag."""
    command = ["gh", "api", "repos/{owner}/{repo}/releases/generate-notes", "--jq", ".body"]
    command += ["-f", f"tag_name={tag}", "-f", f"target_commitish={head()}"]
    command += ["-f", f"previous_tag_name={previous}"] if previous else []
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def create_release(
    tag: str,
    title: str,
    notes: str,
    assets: list[Path],
    prerelease: bool = False,
) -> None:
    """Create the GitHub release (and its tag) on the current commit."""
    command = ["gh", "release", "create", tag, "--title", title, "--notes-file", "-"]
    command += ["--target", head()]
    command += ["--prerelease"] if prerelease else []
    command += [str(asset) for asset in assets]
    subprocess.run(command, check=True, input=notes, text=True)


def mod_jar() -> Path:
    """The built mod jar, ignoring the sources and dev variants."""
    jars = [
        jar for jar in ROOT.glob("build/libs/*.jar") if not jar.stem.endswith(("-sources", "-dev"))
    ]
    if len(jars) != 1:
        raise SystemExit(f"release: expected exactly one mod jar, found {jars}")
    return jars[0]


def head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--quiet", "--verify", f"refs/tags/{tag}"],
        capture_output=True,
    )
    return result.returncode == 0


def last_tag(pattern: str, exclude: str = "") -> str | None:
    """The newest tag matching the glob that is reachable from HEAD."""
    command = ["git", "describe", "--tags", "--abbrev=0", "--match", pattern]
    result = subprocess.run(
        command + (["--exclude", exclude] if exclude else []),
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def read_version(pyproject: Path) -> str:
    content = pyproject.read_text(encoding="utf-8")
    if match := re.search(r'^version = "([^"]+)"$', content, re.MULTILINE):
        return match[1]
    raise SystemExit(f"release: no version in {pyproject}")


def read_gradle_property(name: str) -> str:
    content = (ROOT / "gradle.properties").read_text(encoding="utf-8")
    if match := re.search(rf"^{name}=(.+)$", content, re.MULTILINE):
        return match[1].strip()
    raise SystemExit(f"release: {name} not found in gradle.properties")


if __name__ == "__main__":
    sys.exit(main())
