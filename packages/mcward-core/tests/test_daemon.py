"""Tests for process lifecycle management."""

import subprocess
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import psutil
import pytest

from mcward import Java, ProcessConnectionError, ProcessStartupError
from mcward._constants import (
    PID_FILE,
    PORT_FILE,
    PROTOCOL_VERSION,
    SHUTDOWN_TIMEOUT,
    STARTUP_TIMEOUT,
    WARD_HOST,
)
from mcward._daemon import (
    RunningProcess,
    _wait_ready,
    start,
    status,
    stop,
    stream_tests,
)
from mcward._protocol import (
    Status,
    StreamError,
    TestPassed as Passed,
    TestsFinished as Finished,
    TestsStarted as Started,
)


class TestRunningProcess:
    def test_address_property(self) -> None:
        proc = RunningProcess(Path("/tmp/env"), 12345, 25565)
        assert proc.address == (WARD_HOST, 25565)
        assert proc.address == ("127.0.0.1", 25565)

    def test_load_success(self, tmp_path: Path) -> None:
        directory = tmp_path / "env"
        directory.mkdir()

        (directory / PID_FILE).write_text("12345")
        (directory / PORT_FILE).write_text("25565")

        proc = RunningProcess.load(directory)

        assert proc is not None
        assert proc.directory == directory
        assert proc.pid == 12345
        assert proc.port == 25565


class TestStart:
    @pytest.fixture(autouse=True)
    def mock_find_java(self) -> Iterator[Mock]:
        """Resolve java statically so tests never probe or provision a JVM."""
        with patch("mcward._daemon._java.find", return_value=Java(Path("java"))) as mock:
            yield mock

    @pytest.fixture
    def mock_process(self) -> Mock:
        proc = Mock(spec=subprocess.Popen)
        proc.pid = 12345
        proc.poll.return_value = None  # Process is running
        return proc

    def test_start_success(self, tmp_path: Path, mock_process: Mock) -> None:
        directory = tmp_path / "env"
        directory.mkdir()

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._daemon._wait_ready", return_value=25565) as mock_wait,
        ):
            running = start(directory)

            assert (directory / PID_FILE).exists()
            assert (directory / PID_FILE).read_text() == "12345"

            mock_wait.assert_called_once_with(mock_process, directory, STARTUP_TIMEOUT)

            assert running.directory == directory
            assert running.pid == 12345
            assert running.port == 25565

    def test_start_creates_correct_command(self, tmp_path: Path, mock_process: Mock) -> None:
        directory = tmp_path / "env"
        directory.mkdir()

        with (
            patch("subprocess.Popen", return_value=mock_process) as mock_popen,
            patch("mcward._daemon._wait_ready", return_value=25565),
        ):
            start(directory)

            mock_popen.assert_called_once()
            args = mock_popen.call_args
            cmd = args[0][0]

            assert cmd[0] == "java"
            assert f"-Dward.daemon={directory / PORT_FILE}" in cmd
            assert "-jar" in cmd
            assert str(directory / "server.jar") in cmd
            assert "nogui" in cmd

    def test_start_clears_stale_port_file(self, tmp_path: Path, mock_process: Mock) -> None:
        """A leftover port file must never be read as the new server's port."""
        directory = tmp_path / "env"
        directory.mkdir()
        (directory / PORT_FILE).write_text("9999")

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._daemon._wait_ready", return_value=25565),
        ):
            start(directory)

        assert not (directory / PORT_FILE).exists()

    def test_start_interrupt_does_not_orphan_the_process(
        self, tmp_path: Path, mock_process: Mock
    ) -> None:
        """Ctrl+C while waiting still terminates the spawned JVM."""
        directory = tmp_path / "env"
        directory.mkdir()

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._daemon._wait_ready", side_effect=KeyboardInterrupt),
        ):
            with pytest.raises(KeyboardInterrupt):
                start(directory)

        mock_process.terminate.assert_called_once()
        assert not (directory / PID_FILE).exists()

    def test_start_wait_ready_failure_cleans_up(self, tmp_path: Path, mock_process: Mock) -> None:
        directory = tmp_path / "env"
        directory.mkdir()

        (directory / PORT_FILE).write_text("25565")

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._daemon._wait_ready", side_effect=ProcessStartupError("Timeout")),
        ):
            with pytest.raises(ProcessStartupError):
                start(directory)

            mock_process.terminate.assert_called_once()
            mock_process.wait.assert_called()

            assert not (directory / PID_FILE).exists()
            assert not (directory / PORT_FILE).exists()

    def test_start_process_timeout_kills_process(self, tmp_path: Path, mock_process: Mock) -> None:
        directory = tmp_path / "env"
        directory.mkdir()

        mock_process.wait.side_effect = [subprocess.TimeoutExpired("cmd", 30), None]

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._daemon._wait_ready", side_effect=ProcessStartupError("Timeout")),
        ):
            with pytest.raises(ProcessStartupError):
                start(directory)

            mock_process.terminate.assert_called_once()
            mock_process.kill.assert_called_once()

    def test_start_custom_timeout(self, tmp_path: Path, mock_process: Mock) -> None:
        directory = tmp_path / "env"
        directory.mkdir()

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._daemon._wait_ready", return_value=25565) as mock_wait,
        ):
            start(directory, timeout=60.0)

            mock_wait.assert_called_once_with(mock_process, directory, 60.0)


class TestStop:
    @pytest.fixture
    def running(self, tmp_path: Path) -> RunningProcess:
        directory = tmp_path / "env"
        directory.mkdir()
        (directory / PID_FILE).write_text("12345")
        (directory / PORT_FILE).write_text("25565")
        return RunningProcess(directory, 12345, 25565)

    def test_stop_graceful_shutdown(self, running: RunningProcess) -> None:
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.cmdline.return_value = ["java", "-jar", "server.jar", "nogui"]
        mock_psutil.wait.return_value = None  # Exits gracefully

        with (
            patch("mcward._daemon._bridge.connect"),
            patch("mcward._daemon._bridge.send_message"),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            mock_psutil.wait.assert_called_once_with(SHUTDOWN_TIMEOUT)

            assert not (running.directory / PID_FILE).exists()
            assert not (running.directory / PORT_FILE).exists()

    def test_stop_sends_stop_command(self, running: RunningProcess) -> None:
        mock_socket = MagicMock()
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.cmdline.return_value = ["java", "-jar", "server.jar", "nogui"]

        with (
            patch("mcward._daemon._bridge.connect", return_value=mock_socket) as mock_connect,
            patch("mcward._daemon._bridge.send_message") as mock_send,
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            mock_connect.assert_called_once_with(running.address)
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[1] == {"type": "stop", "protocol": PROTOCOL_VERSION}

    def test_stop_terminates_if_not_graceful(self, running: RunningProcess) -> None:
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.cmdline.return_value = ["java", "-jar", "server.jar", "nogui"]
        mock_psutil.wait.side_effect = [psutil.TimeoutExpired(30), None]

        with (
            patch("mcward._daemon._bridge.connect"),
            patch("mcward._daemon._bridge.send_message"),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            assert mock_psutil.wait.call_count == 2
            mock_psutil.terminate.assert_called_once()

    def test_stop_kills_if_terminate_fails(self, running: RunningProcess) -> None:
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.cmdline.return_value = ["java", "-jar", "server.jar", "nogui"]
        # Timeout on wait, timeout after terminate, then succeeds after kill
        mock_psutil.wait.side_effect = [psutil.TimeoutExpired(30), psutil.TimeoutExpired(30), None]

        with (
            patch("mcward._daemon._bridge.connect"),
            patch("mcward._daemon._bridge.send_message"),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            assert mock_psutil.wait.call_count == 3
            mock_psutil.terminate.assert_called_once()
            mock_psutil.kill.assert_called_once()

    def test_stop_handles_no_such_process(self, running: RunningProcess) -> None:
        with (
            patch("mcward._daemon._bridge.connect"),
            patch("mcward._daemon._bridge.send_message"),
            patch("psutil.Process", side_effect=psutil.NoSuchProcess(12345)),
        ):
            stop(running)

            assert not (running.directory / PID_FILE).exists()
            assert not (running.directory / PORT_FILE).exists()

    def test_stop_handles_connection_error(self, running: RunningProcess) -> None:
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.cmdline.return_value = ["java", "-jar", "server.jar", "nogui"]

        with (
            patch("mcward._daemon._bridge.connect", side_effect=ProcessConnectionError("Failed")),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            mock_psutil.wait.assert_called()

    def test_stop_custom_timeout(self, running: RunningProcess) -> None:
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.cmdline.return_value = ["java", "-jar", "server.jar", "nogui"]

        with (
            patch("mcward._daemon._bridge.connect"),
            patch("mcward._daemon._bridge.send_message"),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running, timeout=5.0)

            mock_psutil.wait.assert_called_once_with(5.0)

    def test_stop_skips_recycled_pid(self, running: RunningProcess) -> None:
        """An unrelated process reusing the pid is never touched."""
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.cmdline.return_value = ["python", "unrelated.py"]

        with (
            patch("mcward._daemon._bridge.connect"),
            patch("mcward._daemon._bridge.send_message"),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            mock_psutil.wait.assert_not_called()
            mock_psutil.terminate.assert_not_called()

            assert not (running.directory / PID_FILE).exists()
            assert not (running.directory / PORT_FILE).exists()


class TestStatus:
    def test_status_success(self) -> None:
        address = ("127.0.0.1", 25565)
        response = {"type": "status", "ready": True}
        expected = Status(ready=True)

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter([response]))

        with (
            patch("mcward._daemon._bridge.connect", return_value=mock_socket) as mock_connect,
            patch("mcward._daemon._bridge.send_message") as mock_send,
            patch("mcward._daemon._bridge.receive_messages", mock_receive),
        ):
            result = status(address)

            mock_connect.assert_called_once_with(address)
            mock_send.assert_called_once()
            assert mock_send.call_args[0][1] == {"type": "status", "protocol": PROTOCOL_VERSION}

            assert result == expected

    def test_status_error_response_raises(self) -> None:
        address = ("127.0.0.1", 25565)
        error = {"type": "error", "message": "Protocol mismatch"}

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter([error]))

        with (
            patch("mcward._daemon._bridge.connect", return_value=mock_socket),
            patch("mcward._daemon._bridge.send_message"),
            patch("mcward._daemon._bridge.receive_messages", mock_receive),
        ):
            with pytest.raises(ProcessConnectionError, match="Status failed"):
                status(address)

    def test_status_no_response_raises(self) -> None:
        address = ("127.0.0.1", 25565)

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter([]))  # No messages

        with (
            patch("mcward._daemon._bridge.connect", return_value=mock_socket),
            patch("mcward._daemon._bridge.send_message"),
            patch("mcward._daemon._bridge.receive_messages", mock_receive),
        ):
            with pytest.raises(ProcessConnectionError, match="No status response"):
                status(address)


class TestStreamTests:
    def test_streams_events(self) -> None:
        address = ("127.0.0.1", 25565)
        events = [
            {"type": "tests_started", "total": 2, "pos": [40, -59, -128]},
            {"type": "test_passed", "name": "test1", "time": 5},
            {"type": "test_passed", "name": "test2", "time": 7},
            {
                "type": "tests_finished",
                "total": 2,
                "passed": 2,
                "failed": 0,
                "skipped": 0,
                "elapsed": 1000,
            },
        ]

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter(events))

        with (
            patch("mcward._daemon._bridge.connect", return_value=mock_socket) as mock_connect,
            patch("mcward._daemon._bridge.send_message") as mock_send,
            patch("mcward._daemon._bridge.receive_messages", mock_receive),
        ):
            result = list(stream_tests(address))

            mock_connect.assert_called_once_with(address)
            mock_send.assert_called_once()
            cmd = mock_send.call_args[0][1]
            assert cmd["type"] == "test"
            assert cmd["protocol"] == PROTOCOL_VERSION
            assert cmd["selector"] == "*:*"

            assert result == [
                Started(total=2, pos=(40, -59, -128)),
                Passed(name="test1", time=5),
                Passed(name="test2", time=7),
                Finished(total=2, passed=2, failed=0, skipped=0, elapsed=1000),
            ]

    def test_custom_selector(self) -> None:
        address = ("127.0.0.1", 25565)
        events = [
            {
                "type": "tests_finished",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "elapsed": 5,
            }
        ]

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter(events))

        with (
            patch("mcward._daemon._bridge.connect", return_value=mock_socket),
            patch("mcward._daemon._bridge.send_message") as mock_send,
            patch("mcward._daemon._bridge.receive_messages", mock_receive),
        ):
            list(stream_tests(address, selector="mypack:test_*"))

            cmd = mock_send.call_args[0][1]
            assert cmd["selector"] == "mypack:test_*"

    def test_stops_on_tests_finished(self) -> None:
        address = ("127.0.0.1", 25565)
        events = [
            {"type": "test_passed", "name": "test1", "time": 5},
            {
                "type": "tests_finished",
                "total": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "elapsed": 5,
            },
            {"type": "should_not_see_this"},  # After tests_finished
        ]

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter(events))

        with (
            patch("mcward._daemon._bridge.connect", return_value=mock_socket),
            patch("mcward._daemon._bridge.send_message"),
            patch("mcward._daemon._bridge.receive_messages", mock_receive),
        ):
            result = list(stream_tests(address))

            assert len(result) == 2
            assert isinstance(result[0], Passed)
            assert isinstance(result[1], Finished)

    def test_stops_on_error(self) -> None:
        address = ("127.0.0.1", 25565)
        events = [
            {"type": "test_passed", "name": "test1", "time": 5},
            {"type": "error", "message": "Something failed"},
            {"type": "should_not_see_this"},
        ]

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter(events))

        with (
            patch("mcward._daemon._bridge.connect", return_value=mock_socket),
            patch("mcward._daemon._bridge.send_message"),
            patch("mcward._daemon._bridge.receive_messages", mock_receive),
        ):
            result = list(stream_tests(address))

            assert len(result) == 2
            assert result[1] == StreamError(message="Something failed")

    def test_stream_ending_without_terminal_event_raises(self) -> None:
        """A dead server (socket EOF mid-run) surfaces as an error."""
        address = ("127.0.0.1", 25565)
        events = [{"type": "test_passed", "name": "test1", "time": 5}]

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter(events))

        with (
            patch("mcward._daemon._bridge.connect", return_value=mock_socket),
            patch("mcward._daemon._bridge.send_message"),
            patch("mcward._daemon._bridge.receive_messages", mock_receive),
        ):
            with pytest.raises(ProcessConnectionError, match="before tests finished"):
                list(stream_tests(address))


class TestWaitReady:
    @pytest.fixture
    def directory(self, tmp_path: Path) -> Path:
        directory = tmp_path / "env"
        directory.mkdir()
        return directory

    @pytest.fixture
    def running_process(self) -> Mock:
        proc = Mock(spec=subprocess.Popen)
        proc.poll.return_value = None  # Still running
        return proc

    def test_returns_port_once_responsive(self, directory: Path, running_process: Mock) -> None:
        (directory / PORT_FILE).write_text("25565")

        with patch("mcward._daemon.status", return_value=Status(ready=True)):
            port = _wait_ready(running_process, directory, timeout=5)

        assert port == 25565

    def test_process_death_raises(self, directory: Path, running_process: Mock) -> None:
        """A crashed process fails startup immediately."""
        running_process.poll.return_value = 1
        running_process.returncode = 1

        with pytest.raises(ProcessStartupError, match="exited with code 1"):
            _wait_ready(running_process, directory, timeout=5)

    def test_deadline_exceeded_raises(self, directory: Path, running_process: Mock) -> None:
        """Startup fails once the deadline passes without a port file."""
        with pytest.raises(ProcessStartupError, match="did not become ready"):
            _wait_ready(running_process, directory, timeout=0)

    def test_keeps_polling_while_server_unresponsive(
        self, directory: Path, running_process: Mock
    ) -> None:
        (directory / PORT_FILE).write_text("25565")
        responses = [ProcessConnectionError("not yet"), {"ready": True}]

        with (
            patch("mcward._daemon.status", side_effect=responses),
            patch("time.sleep"),
        ):
            port = _wait_ready(running_process, directory, timeout=5)

        assert port == 25565
