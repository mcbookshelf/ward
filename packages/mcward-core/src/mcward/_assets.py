"""Asset downloading utilities for Ward."""

import asyncio
import shutil
import sys
from collections.abc import Awaitable
from pathlib import Path

from httpx import AsyncClient

from ._constants import FABRIC_API, MODRINTH_API
from ._exceptions import AssetNotFoundError, InstallError
from ._versions import Version


async def download(directory: Path, version: Version) -> None:
    """Download required assets into the given directory."""
    name = version.name[4:] if version.name.startswith("dev/") else version.name

    async with AsyncClient() as client:
        server = _resolve_fabric_url(client, name)
        fabric = _resolve_modrinth_url(client, "fabric-api", name)

        await asyncio.gather(
            _download_file(client, server, directory / "server.jar"),
            _download_file(client, fabric, directory / "mods/fabric-api.jar"),
            _build_ward(directory / "mods")
            if version.name.startswith("dev/")
            else _download_file(
                client, _resolve_modrinth_url(client, "ward", name), directory / "mods/ward.jar"
            ),
        )


async def _download_file(client: AsyncClient, url: Awaitable[str], file: Path) -> None:
    """Download a file from the given URL to the specified file path."""
    response = await client.get(await url)
    response.raise_for_status()
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(response.content)


async def _resolve_fabric_url(client: AsyncClient, version: str) -> str:
    """Resolve the download URL for a specific Fabric version."""
    response = await client.get(f"{FABRIC_API}/versions/loader/{version}")
    response.raise_for_status()
    loader = response.json()[0]["loader"]["version"]
    return f"{FABRIC_API}/versions/loader/{version}/{loader}/1.1.1/server/jar"


async def _resolve_modrinth_url(client: AsyncClient, project_id: str, version: str) -> str:
    """Resolve the Modrinth download URL for a given project and version."""
    response = await client.get(f"{MODRINTH_API}/project/{project_id}/version")
    response.raise_for_status()
    # Filter versions compatible with the target Minecraft version
    if versions := [
        data
        for data in response.json()
        if any(v.startswith(version) for v in data["game_versions"])
    ]:
        return versions[0]["files"][0]["url"]
    # Raise if no compatible version was found
    raise AssetNotFoundError(project_id, version)


async def _build_ward(directory: Path) -> None:
    """Build ward.jar using gradle and copy to directory."""
    root = Path.cwd()
    gradle = root / ("gradlew.bat" if sys.platform == "win32" else "gradlew")

    proc = await asyncio.create_subprocess_exec(
        str(gradle),
        "build",
        "-x",
        "test",
        cwd=root,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await proc.communicate()
    if proc.returncode:
        raise InstallError(f"Gradle build failed:\n{stderr.decode()}")

    libs = list((root / "build/libs").glob("*.jar"))
    jar = next((p for p in libs if not p.stem.endswith(("-sources", "-dev"))), None)
    if jar is None:
        raise InstallError("No jar file found in build/libs")
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(jar, directory / "ward.jar")
