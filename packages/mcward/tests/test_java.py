"""Tests for Java runtime resolution."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcward import Java, JavaNotFoundError, find_java
from mcward._constants import JAVA_VERSION
from mcward._java import _probe_major, find_binary, resolve

JAVA_NAME = "java.exe" if sys.platform == "win32" else "java"


def probe_result(stderr: str, returncode: int = 0) -> Mock:
    result = Mock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stderr = stderr
    result.stdout = ""
    return result


def fake_runtime(root: Path) -> Path:
    """Create a runtime directory shaped like an extracted JRE archive."""
    binary = root / f"jdk-{JAVA_VERSION}.0.1+9-jre" / "bin" / JAVA_NAME
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"")
    return binary


class TestProbeMajor:
    def test_modern_version(self) -> None:
        output = f'openjdk version "{JAVA_VERSION}.0.1" 2025-10-21'
        with patch("subprocess.run", return_value=probe_result(output)):
            assert _probe_major("java") == JAVA_VERSION

    def test_major_only_version(self) -> None:
        with patch("subprocess.run", return_value=probe_result('openjdk version "25" 2025-09-16')):
            assert _probe_major("java") == 25

    def test_legacy_version_scheme(self) -> None:
        with patch("subprocess.run", return_value=probe_result('java version "1.8.0_392"')):
            assert _probe_major("java") == 8

    def test_missing_executable(self) -> None:
        with patch("subprocess.run", side_effect=OSError("No such file")):
            assert _probe_major("nope") is None

    def test_failing_executable(self) -> None:
        with patch("subprocess.run", return_value=probe_result("boom", returncode=1)):
            assert _probe_major("java") is None

    def test_unparseable_output(self) -> None:
        with patch("subprocess.run", return_value=probe_result("not a version banner")):
            assert _probe_major("java") is None


class TestFindBinary:
    def test_finds_binary_under_bin(self, tmp_path: Path) -> None:
        binary = fake_runtime(tmp_path)
        assert find_binary(tmp_path) == binary

    def test_ignores_java_outside_bin(self, tmp_path: Path) -> None:
        stray = tmp_path / "lib" / JAVA_NAME
        stray.parent.mkdir(parents=True)
        stray.write_bytes(b"")
        assert find_binary(tmp_path) is None

    def test_missing_directory(self, tmp_path: Path) -> None:
        assert find_binary(tmp_path / "absent") is None


class TestResolveJava:
    def test_path_java_recent_enough(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/java"),
            patch("mcward._java._probe_major", return_value=JAVA_VERSION),
        ):
            assert resolve() == Java(Path("/usr/bin/java"))

    def test_path_java_too_old_uses_cache(self, tmp_path: Path) -> None:
        binary = fake_runtime(tmp_path / "runtime")
        with (
            patch("shutil.which", return_value="/usr/bin/java"),
            patch("mcward._java._probe_major", return_value=JAVA_VERSION - 1),
            patch("mcward._java.JAVA_DIR", tmp_path / "runtime"),
        ):
            assert resolve() == Java(binary)

    def test_nothing_resolves(self, tmp_path: Path) -> None:
        with (
            patch("shutil.which", return_value=None),
            patch("mcward._java.JAVA_DIR", tmp_path),
        ):
            assert resolve() is None

    def test_find_java_fails_hard_when_unresolved(self) -> None:
        """find_java never provisions on its own: installs do that."""
        with (
            patch("mcward._java.resolve", return_value=None),
            pytest.raises(JavaNotFoundError, match="no Java"),
        ):
            find_java()


class TestJavaCommand:
    def test_command_shape(self) -> None:
        java = Java(Path("/jre/bin/java"))
        command = java.command(Path("server.jar"), "-Xmx2G", "-Dward.daemon=ward.port")
        assert command == [
            str(Path("/jre/bin/java")),
            "-Xmx2G",
            "-Dward.daemon=ward.port",
            "-jar",
            "server.jar",
            "nogui",
        ]
