"""Lifecycle of the Ward daemon: the background server process."""

import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, override

import psutil

from . import _bridge, _java
from ._constants import (
    HEARTBEAT_TIMEOUT,
    OUTPUT_FILE,
    PID_FILE,
    PORT_FILE,
    PROTOCOL_VERSION,
    SHUTDOWN_TIMEOUT,
    STARTUP_TIMEOUT,
    STATUS_TIMEOUT,
    WARD_HOST,
)
from ._exceptions import ProcessConnectionError, ProcessStartupError, ProcessTimeoutError
from ._protocol import BenchFinished, Event, Status, StreamError, TestsFinished, parse_event

# Out of the console's process group: a Ctrl+C meant for another program there ended the daemon
if sys.platform == "win32":
    DETACHED = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
else:
    DETACHED = 0


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

    if is_ward_process(running.pid, running.directory):
        with suppress(psutil.NoSuchProcess):
            _wait_or_kill(psutil.Process(running.pid), timeout)

    # Stop holds no lock: another process may have started a new daemon in the meantime
    if _recorded_pid(running.directory) == running.pid:
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

        raise ProcessConnectionError("No status response received")


def stream_tests(
    address: tuple[str, int],
    selector: str = "*:*",
    coverage: bool = False,
    timeout: float | None = None,
    origin: tuple[int, int] | None = None,
) -> Iterator[Event]:
    """Start a test run and stream its events; ``timeout`` bounds the wait between two."""
    request = {"type": "test", "protocol": PROTOCOL_VERSION, "selector": selector}
    if coverage:
        request["coverage"] = True
    if origin is not None:
        request["origin"] = list(origin)
    return _stream(address, request, TestsFinished, timeout)


def stream_bench(
    address: tuple[str, int],
    commands: Sequence[str],
    setup: Sequence[str] = (),
    prepare: Sequence[str] = (),
    batch: int = 0,
    warmup: int | None = None,
    duration: int | None = None,
    timeout: float | None = None,
) -> Iterator[Event]:
    """Start a bench via the bridge and stream its events. Durations are milliseconds."""
    request = {
        "type": "bench",
        "protocol": PROTOCOL_VERSION,
        "commands": list(commands),
        "setup": list(setup),
        "prepare": list(prepare),
        "batch": batch,
    }
    if warmup is not None:
        request["warmup"] = warmup
    if duration is not None:
        request["time"] = duration
    return _stream(address, request, BenchFinished, timeout)


def _stream(
    address: tuple[str, int],
    request: dict[str, Any],
    last: type[Event],
    timeout: float | None,
) -> Iterator[Event]:
    """Yield a request's events up to its last; with no timeout, a heartbeat arms one."""
    armed = False
    with _bridge.connect(address) as conn:
        _bridge.send_message(conn, request)

        try:
            for message in _bridge.receive_messages(conn, timeout=timeout):
                if message.get("type") == "heartbeat":
                    if timeout is None and not armed:
                        conn.settimeout(HEARTBEAT_TIMEOUT)
                        armed = True
                    continue
                if (event := parse_event(message)) is None:
                    continue
                yield event
                if isinstance(event, last | StreamError):
                    return
        except ProcessTimeoutError as e:
            if not armed:
                raise
            raise ProcessConnectionError(
                f"The server stopped ticking: nothing for {HEARTBEAT_TIMEOUT}s. "
                "It stays busy until it is stopped"
            ) from e

        raise ProcessConnectionError("Event stream ended before the run finished")


def find(directory: Path) -> RunningProcess | None:
    """The recorded daemon of this folder if it is alive, clearing stale files if not."""
    try:
        process = RunningProcess.load(directory)
    except OSError, ValueError:
        return None
    if is_ward_process(process.pid, directory):
        return process
    clear_files(directory)
    return None


def is_ward_process(pid: int, directory: Path) -> bool:
    """Check that the pid is the daemon that was started for this directory."""
    try:
        cmdline = psutil.Process(pid).cmdline()
    except psutil.Error:
        return False
    return _daemon_flag(directory) in cmdline


def wait_idle(address: tuple[str, int], timeout: float = SHUTDOWN_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while not _probe(address):
        if time.monotonic() > deadline:
            raise ProcessConnectionError(f"Server still busy after {timeout}s")
        time.sleep(0.5)


def _spawn(directory: Path) -> subprocess.Popen[bytes]:
    """Launch the JVM, which picks its own port and writes it to ward.port."""
    # A stale file from a crashed run must never be read as the new port
    directory.joinpath(PORT_FILE).unlink(missing_ok=True)
    java = _java.find()
    # Kept in a file: when a start fails, the reason is often only printed here
    with directory.joinpath(OUTPUT_FILE).open("wb") as output:
        return subprocess.Popen(
            java.command(
                directory / "server.jar",
                "-Xmx2g",
                "-XX:G1PeriodicGCInterval=60000",
                # A full idle GC compacts the heap: idle memory halves, the next run is ~0.3s slower
                "-XX:-G1PeriodicGCInvokesConcurrent",
                "-XX:+ParallelRefProcEnabled",
                "-XX:+DisableExplicitGC",
                "-XX:+HeapDumpOnOutOfMemoryError",
                # HotSpot never overwrites a dump, so this keeps the first one and no more
                "-XX:HeapDumpPath=ward.hprof",
                "-XX:+ExitOnOutOfMemoryError",
                _daemon_flag(directory),
            ),
            cwd=directory,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            creationflags=DETACHED,
            start_new_session=sys.platform != "win32",
        )


def _daemon_flag(directory: Path) -> str:
    """The JVM argument that turns daemon mode on. It also tells whose daemon a process is."""
    return f"-Dward.daemon={directory / PORT_FILE}"


def _wait_or_kill(proc: psutil.Process, timeout: float) -> None:
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
    output = directory / OUTPUT_FILE

    while True:
        if process.poll() is not None:
            raise ProcessStartupError(
                f"Process exited with code {process.returncode}, see {output}"
            )
        if time.monotonic() > deadline:
            raise ProcessStartupError(
                f"Process did not become ready within {timeout}s, see {output}"
            )
        if (port := _get_port(directory)) is not None and _probe((WARD_HOST, port)):
            return port
        time.sleep(0.1)


def clear_files(directory: Path) -> None:
    directory.joinpath(PID_FILE).unlink(missing_ok=True)
    directory.joinpath(PORT_FILE).unlink(missing_ok=True)


def _recorded_pid(directory: Path) -> int | None:
    try:
        return int(directory.joinpath(PID_FILE).read_text(encoding="utf-8").strip())
    except ValueError, OSError:
        return None


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
