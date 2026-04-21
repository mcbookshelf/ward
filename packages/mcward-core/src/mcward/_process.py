"""Process lifecycle management for Ward."""

import subprocess
import time
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import psutil

from . import _socket as socket
from ._constants import (
    PID_FILE,
    PORT_FILE,
    PROTOCOL_VERSION,
    SHUTDOWN_TIMEOUT,
    STARTUP_TIMEOUT,
    WARD_HOST,
)
from ._exceptions import ProcessConnectionError, ProcessStartupError


@dataclass
class RunningProcess:
    """Metadata about a running process."""

    directory: Path
    pid: int
    port: int

    @property
    def address(self) -> tuple[str, int]:
        return (WARD_HOST, self.port)

    def __repr__(self) -> str:
        return f"(pid: {self.pid}, port: {self.port})"

    @classmethod
    def load(cls, directory: Path) -> RunningProcess:
        pid = int(directory.joinpath(PID_FILE).read_text(encoding="utf-8").strip())
        port = int(directory.joinpath(PORT_FILE).read_text(encoding="utf-8").strip())
        return cls(directory, pid, port)


def start(directory: Path, timeout: float = STARTUP_TIMEOUT) -> RunningProcess:
    proc = _spawn(directory)
    directory.joinpath(PID_FILE).write_text(str(proc.pid), encoding="utf-8")

    try:
        port = _wait_ready(proc, directory, timeout)
    except Exception:
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        directory.joinpath(PID_FILE).unlink(missing_ok=True)
        directory.joinpath(PORT_FILE).unlink(missing_ok=True)
        raise

    return RunningProcess(directory, proc.pid, port)


def stop(running: RunningProcess, timeout: float = SHUTDOWN_TIMEOUT) -> None:
    """Stop process gracefully."""
    with (
        suppress(ProcessConnectionError),
        socket.connect(running.address) as conn,
    ):
        socket.send_message(conn, {"type": "stop", "protocol": PROTOCOL_VERSION})

    with suppress(psutil.NoSuchProcess):
        proc = psutil.Process(running.pid)
        try:
            proc.wait(timeout)
        except psutil.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout)
            except psutil.TimeoutExpired:
                proc.kill()
                proc.wait()

    running.directory.joinpath(PID_FILE).unlink(missing_ok=True)
    running.directory.joinpath(PORT_FILE).unlink(missing_ok=True)


def status(address: tuple[str, int]) -> dict:
    """Get process status via IPC."""
    with socket.connect(address) as conn:
        socket.send_message(conn, {"type": "status", "protocol": PROTOCOL_VERSION})

        for event in socket.receive_messages(conn):
            if event["type"] == "status_response":
                return event
            if event["type"] == "error":
                raise ProcessConnectionError(f"Status failed: {event['message']}")

        raise ProcessConnectionError("No status response received")


def test(address: tuple[str, int], selector: str = "*:*") -> Iterator[dict]:
    """Run tests via process IPC."""
    with socket.connect(address) as conn:
        cmd = {"type": "test", "protocol": PROTOCOL_VERSION, "selector": selector}
        socket.send_message(conn, cmd)

        for event in socket.receive_messages(conn):
            yield event
            if event["type"] in ("tests_finished", "error"):
                break


def _spawn(directory: Path) -> subprocess.Popen:
    """Spawn JVM process. Java will choose port and write to ward.port file."""
    port_file = directory / PORT_FILE
    return subprocess.Popen(
        ["java", f"-Dward.daemon={port_file}", "-jar", str(directory / "server.jar"), "nogui"],
        cwd=directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_ready(process: subprocess.Popen, directory: Path, timeout: float) -> int:
    """Wait for Java to write port file and become responsive. Returns port."""
    deadline = time.time() + timeout
    file = directory.joinpath(PORT_FILE)

    while True:
        if process.poll() is not None:
            raise ProcessStartupError(f"Process exited with code {process.returncode}")
        if time.time() > deadline:
            raise ProcessStartupError(f"Process did not become ready within {timeout}s")
        if file.exists():
            with suppress(ValueError, OSError):
                port = int(file.read_text(encoding="utf-8").strip())
                address = (WARD_HOST, port)
                # Verify server is responsive
                with suppress(ProcessConnectionError, ConnectionRefusedError, OSError):
                    status(address)
                    return port

        time.sleep(0.1)
