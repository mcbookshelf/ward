"""Environment installation: every asset a Ward test server needs."""

import asyncio
import platform
import shutil
import sys
import tarfile
import tempfile
import zipfile
from contextlib import suppress
from pathlib import Path
from typing import Any

import httpx
from httpx import AsyncClient

from . import _java
from ._constants import (
    ADOPTIUM_API,
    DOWNLOAD_TIMEOUT,
    FABRIC_API,
    FABRIC_INSTALLER,
    JAVA_DIR,
    JAVA_VERSION,
    MODRINTH_API,
    USER_AGENT,
)
from ._exceptions import (
    AssetNotFoundError,
    DownloadFailedError,
    InstallError,
    JavaNotFoundError,
    WardError,
)
from ._versions import Version

ADOPTIUM_SYSTEMS = {
    "win32": ("windows", ".zip"),
    "darwin": ("mac", ".tar.gz"),
    "linux": ("linux", ".tar.gz"),
}

ADOPTIUM_ARCHITECTURES = {
    "amd64": "x64",
    "x86_64": "x64",
    "arm64": "aarch64",
    "aarch64": "aarch64",
}


async def install(directory: Path, version: Version) -> None:
    """Install every asset the environment needs, downloading concurrently.

    The produced files are what ``_manager.INSTALLED_FILES`` checks for:
    the two must move together.
    """
    async with AsyncClient(
        timeout=DOWNLOAD_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        prod = not version.is_dev
        vers = version.minecraft
        mods = directory / "mods"
        tasks = [
            _install_server(client, vers, directory / "server.jar"),
            _install_mod(client, "fabric-api", vers, mods / "fabric-api.jar"),
            _install_mod(client, "ward", vers, mods / "ward.jar") if prod else _build_ward(mods),
        ]
        if _java.resolve() is None:
            tasks.append(_install_java(client))

        try:
            async with asyncio.TaskGroup() as group:
                for task in tasks:
                    group.create_task(task)
        except* WardError as errors:
            raise errors.exceptions[0] from None


async def _install_server(client: AsyncClient, minecraft: str, file: Path) -> None:
    """Download the Fabric server launcher for the newest stable loader."""
    loaders = await _get_json(client, f"{FABRIC_API}/versions/loader/{minecraft}")
    if not loaders:
        raise AssetNotFoundError("fabric loader", minecraft)
    loader = next((x for x in loaders if x["loader"]["stable"]), loaders[0])["loader"]["version"]
    url = f"{FABRIC_API}/versions/loader/{minecraft}/{loader}/{FABRIC_INSTALLER}/server/jar"
    await _download_file(client, url, file)


async def _install_mod(client: AsyncClient, project: str, minecraft: str, file: Path) -> None:
    """Download the newest Modrinth release of a project for this Minecraft."""
    releases = await _get_json(client, f"{MODRINTH_API}/project/{project}/version")
    for release in releases:
        if minecraft in release["game_versions"]:
            files = release["files"]
            primary = next((x for x in files if x["primary"]), files[0])
            return await _download_file(client, primary["url"], file)
    raise AssetNotFoundError(project, minecraft)


async def _install_java(client: AsyncClient) -> None:
    """Download and unpack a Temurin JRE into the mcward cache."""
    os_name, arch, suffix = _adoptium_platform()
    release = f"{ADOPTIUM_API}/binary/latest/{JAVA_VERSION}/ga"
    url = f"{release}/{os_name}/{arch}/jre/hotspot/normal/eclipse"

    JAVA_DIR.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f"{JAVA_DIR.name}-", dir=JAVA_DIR.parent))
    try:
        archive = staging / f"temurin{suffix}"
        await _download_file(client, url, archive)
        await asyncio.to_thread(_unpack_runtime, archive, JAVA_DIR)
    finally:
        await asyncio.to_thread(shutil.rmtree, staging, ignore_errors=True)

    if _java.find_binary(JAVA_DIR) is None:
        raise JavaNotFoundError(f"provisioned runtime has no java executable in {JAVA_DIR}")


async def _download_file(client: AsyncClient, url: str, file: Path) -> None:
    """Stream the URL into the file, atomically through a .part sibling."""
    file.parent.mkdir(parents=True, exist_ok=True)
    partial = file.with_suffix(file.suffix + ".part")

    try:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with partial.open("wb") as output:
                async for chunk in response.aiter_bytes():
                    output.write(chunk)
    except httpx.HTTPError as e:
        partial.unlink(missing_ok=True)
        raise DownloadFailedError(url, str(e)) from e

    partial.replace(file)


async def _get_json(client: AsyncClient, url: str) -> Any:
    """GET a JSON document; network and HTTP errors become DownloadFailedError."""
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise DownloadFailedError(url, str(e)) from e
    return response.json()


async def _build_ward(directory: Path) -> None:
    """Build ward.jar with gradle and copy it into the directory."""
    root = Path.cwd()
    gradle = root / ("gradlew.bat" if sys.platform == "win32" else "gradlew")

    proc = await asyncio.create_subprocess_exec(
        str(gradle),
        "build",
        "-x",
        "test",
        cwd=root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    output, _ = await proc.communicate()
    if proc.returncode:
        tail = "\n".join(output.decode(errors="replace").splitlines()[-30:])
        raise InstallError(f"Gradle build failed:\n{tail}")

    libs = list((root / "build/libs").glob("*.jar"))
    jar = next((p for p in libs if not p.stem.endswith(("-sources", "-dev"))), None)
    if jar is None:
        raise InstallError("No jar file found in build/libs")
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(jar, directory / "ward.jar")


def _adoptium_platform() -> tuple[str, str, str]:
    """Map this machine to Adoptium's (os, architecture, archive suffix)."""
    if sys.platform not in ADOPTIUM_SYSTEMS:
        raise JavaNotFoundError(f"unsupported platform: {sys.platform}")
    if (machine := platform.machine().lower()) not in ADOPTIUM_ARCHITECTURES:
        raise JavaNotFoundError(f"unsupported architecture: {platform.machine()}")

    os_name, suffix = ADOPTIUM_SYSTEMS[sys.platform]
    return os_name, ADOPTIUM_ARCHITECTURES[machine], suffix


def _unpack_runtime(archive: Path, runtime: Path) -> None:
    """Extract the runtime archive inside its staging directory, then rename.

    A losing concurrent install's rename is ignored on purpose: the caller
    verifies afterwards that a valid runtime is in place.
    """
    extracted = archive.parent / "runtime"
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as file:
            file.extractall(extracted)
    else:
        with tarfile.open(archive) as file:
            file.extractall(extracted, filter="data")

    if not runtime.exists():
        with suppress(OSError):
            extracted.replace(runtime)
