"""Java runtime resolution: a recent enough java on the PATH wins, then the
runtime in the mcward cache (provisioned by ``_assets`` during installs)."""

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ._constants import JAVA_DIR, JAVA_VERSION
from ._exceptions import JavaNotFoundError

_VERSION_PATTERN = re.compile(r'version "(\d+)(?:\.(\d+))?')


@dataclass(frozen=True)
class Java:
    """A resolved Java runtime."""

    executable: Path

    def command(self, jar: Path, *args: str) -> list[str]:
        """The command line launching a server jar with the given JVM arguments."""
        return [str(self.executable), *args, "-jar", str(jar), "nogui"]


def find() -> Java:
    """The resolved runtime; raises JavaNotFoundError when none is usable."""
    if java := resolve():
        return java
    raise JavaNotFoundError(f"no Java {JAVA_VERSION}+ found")


def resolve() -> Java | None:
    """The first usable runtime, or None when one has to be provisioned."""
    if java := shutil.which("java"):
        major = _probe_major(java)
        if major is not None and major >= JAVA_VERSION:
            return Java(Path(java))

    if binary := find_binary(JAVA_DIR):
        return Java(binary)
    return None


def find_binary(runtime: Path) -> Path | None:
    """Locate the java executable inside a provisioned runtime directory."""
    if not runtime.is_dir():
        return None
    name = "java.exe" if sys.platform == "win32" else "java"
    return next((p for p in runtime.rglob(name) if p.parent.name == "bin"), None)


def _probe_major(executable: str) -> int | None:
    """Return the executable's Java major version, or None when it is unusable."""
    command = [executable, "-version"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    except OSError, subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None

    if match := _VERSION_PATTERN.search(result.stderr + result.stdout):
        major, minor = int(match[1]), match[2]
        # Legacy scheme: version "1.8.0_392" means Java 8
        return int(minor) if major == 1 and minor else major
    return None
