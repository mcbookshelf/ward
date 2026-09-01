"""Lifecycle of the Ward daemon: the background server process."""

import subprocess
import time
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import override

import psutil

from . import _bridge, _java
from ._constants import (
    PID_FILE,
    PORT_FILE,
    PROTOCOL_VERSION,
    SHUTDOWN_TIMEOUT,
    STARTUP_TIMEOUT,
    STATUS_TIMEOUT,
    WARD_HOST,
)
from ._exceptions import ProcessConnectionError, ProcessStartupError
from ._protocol import Event, Status, StreamError, TestsFinished, parse_event


@dataclass
class RunningProcess:
    """A daemon process, as recorded by its pid and port files."""

    directory: Path
    pid: int
    port: int

    @property
    def address(self) -> tuple[str, int]:
        return (WARD_HOST, self.port)

    @override
    def __str__(self) -> str:
        return f"(pid: {self.pid}, port: {self.port})"

    @classmethod
    def load(cls, directory: Path) -> RunningProcess:
        pid = int(directory.joinpath(PID_FILE).read_text(encoding="utf-8").strip())
        port = int(directory.joinpath(PORT_FILE).read_text(encoding="utf-8").strip())
        return cls(directory, pid, port)


def start(directory: Path, timeout: float = STARTUP_TIMEOUT) -> RunningProcess:
    """Spawn the server process and wait until it is ready to serve requests."""
    proc = _spawn(directory)
    directory.joinpath(PID_FILE).write_text(str(proc.pid), encoding="utf-8")

    # BaseException: a Ctrl+C while waiting must not orphan the spawned JVM
    try:
        port = _wait_ready(proc, directory, timeout)
    except BaseException:
        proc.terminate()
        try:
            proc.wait(timeout=SHUTDOWN_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        clear_files(directory)
        raise

    return RunningProcess(directory, proc.pid, port)


def stop(running: RunningProcess, timeout: float = SHUTDOWN_TIMEOUT) -> None:
    """Ask the daemon to stop, escalating to terminate then kill on timeout."""
    with suppress(ProcessConnectionError), _bridge.connect(running.address) as conn:
        _bridge.send_message(conn, {"type": "stop", "protocol": PROTOCOL_VERSION})

    if is_ward_process(running.pid):
        with suppress(psutil.NoSuchProcess):
            _wait_or_kill(psutil.Process(running.pid), timeout)

    clear_files(running.directory)


def status(address: tuple[str, int], timeout: float = STATUS_TIMEOUT) -> Status:
    """Ask the daemon whether it is ready to serve a run."""
    with _bridge.connect(address) as conn:
        _bridge.send_message(conn, {"type": "status", "protocol": PROTOCOL_VERSION})

        for message in _bridge.receive_messages(conn, timeout=timeout):
            match parse_event(message):
                case Status() as event:
                    return event
                case StreamError(message=error):
                    raise ProcessConnectionError(f"Status failed: {error}")
                case _:
                    pass

        raise ProcessConnectionError("No status response received")


def stream_tests(
    address: tuple[str, int],
    selector: str = "*:*",
    coverage: bool = False,
    timeout: float | None = None,
) -> Iterator[Event]:
    """Start a test run via the bridge and stream its events.

    ``timeout`` bounds the wait between consecutive events; ``None`` waits
    indefinitely.
    """
    with _bridge.connect(address) as conn:
        cmd = {"type": "test", "protocol": PROTOCOL_VERSION, "selector": selector}
        if coverage:
            cmd["coverage"] = True
        _bridge.send_message(conn, cmd)

        for message in _bridge.receive_messages(conn, timeout=timeout):
            if (event := parse_event(message)) is None:
                continue
            yield event
            if isinstance(event, TestsFinished | StreamError):
                return

        raise ProcessConnectionError("Event stream ended before tests finished")


def is_ward_process(pid: int) -> bool:
    """Check that the pid exists and belongs to a Ward server JVM."""
    try:
        cmdline = psutil.Process(pid).cmdline()
    except psutil.Error:
        return False
    return any("server.jar" in arg for arg in cmdline)


def wait_idle(address: tuple[str, int], timeout: float = SHUTDOWN_TIMEOUT) -> None:
    """Wait until the daemon is ready to serve a run."""
    deadline = time.monotonic() + timeout
    while not _probe(address):
        if time.monotonic() > deadline:
            raise ProcessConnectionError(f"Daemon still busy after {timeout}s")
        time.sleep(0.5)


def _spawn(directory: Path) -> subprocess.Popen[bytes]:
    """Launch the JVM, which picks its own port and writes it to ward.port."""
    port_file = directory / PORT_FILE
    # A stale file from a crashed run must never be read as the new port
    port_file.unlink(missing_ok=True)
    java = _java.find()
    return subprocess.Popen(
        java.command(
            directory / "server.jar",
            "-Xmx2g",
            "-Xms1g",
            "-XX:G1PeriodicGCInterval=60000",
            "-XX:+ParallelRefProcEnabled",
            "-XX:+DisableExplicitGC",
            "-XX:+HeapDumpOnOutOfMemoryError",
            "-XX:+ExitOnOutOfMemoryError",
            f"-Dward.daemon={port_file}",
        ),
        cwd=directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_or_kill(proc: psutil.Process, timeout: float) -> None:
    """Wait for the process to exit, escalating to terminate then kill."""
    try:
        proc.wait(timeout)
    except psutil.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout)
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait()


def _wait_ready(process: subprocess.Popen[bytes], directory: Path, timeout: float) -> int:
    """Return the port once the JVM has published it and answers a status call."""
    deadline = time.monotonic() + timeout

    while True:
        if process.poll() is not None:
            raise ProcessStartupError(f"Process exited with code {process.returncode}")
        if time.monotonic() > deadline:
            raise ProcessStartupError(f"Process did not become ready within {timeout}s")
        if (port := _get_port(directory)) is not None and _probe((WARD_HOST, port)):
            return port
        time.sleep(0.1)


def clear_files(directory: Path) -> None:
    directory.joinpath(PID_FILE).unlink(missing_ok=True)
    directory.joinpath(PORT_FILE).unlink(missing_ok=True)


def _get_port(directory: Path) -> int | None:
    try:
        return int(directory.joinpath(PORT_FILE).read_text(encoding="utf-8").strip())
    except ValueError, OSError:
        return None


def _probe(address: tuple[str, int]) -> bool:
    try:
        return status(address, timeout=2).ready
    except ProcessConnectionError:
        return False
