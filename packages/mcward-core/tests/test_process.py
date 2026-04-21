"""Tests for process lifecycle management."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import psutil
import pytest

from mcward import ProcessConnectionError, ProcessStartupError
from mcward._constants import (
    PID_FILE,
    PORT_FILE,
    PROTOCOL_VERSION,
    SHUTDOWN_TIMEOUT,
    STARTUP_TIMEOUT,
    WARD_HOST,
)
from mcward._process import RunningProcess, start, status, stop, test as run_test


class TestRunningProcess:
    """Test RunningProcess dataclass."""

    def test_address_property(self) -> None:
        """Test that address property returns correct tuple."""
        proc = RunningProcess(Path("/tmp/env"), 12345, 25565)
        assert proc.address == (WARD_HOST, 25565)
        assert proc.address == ("127.0.0.1", 25565)

    def test_load_success(self, tmp_path: Path) -> None:
        """Test loading process metadata from files."""
        directory = tmp_path / "env"
        directory.mkdir()

        # Create PID and port files
        (directory / PID_FILE).write_text("12345")
        (directory / PORT_FILE).write_text("25565")

        proc = RunningProcess.load(directory)

        assert proc is not None
        assert proc.directory == directory
        assert proc.pid == 12345
        assert proc.port == 25565


class TestStart:
    """Test process start function."""

    @pytest.fixture
    def mock_process(self) -> Mock:
        """Create a mock Popen process."""
        proc = Mock(spec=subprocess.Popen)
        proc.pid = 12345
        proc.poll.return_value = None  # Process is running
        return proc

    def test_start_success(self, tmp_path: Path, mock_process: Mock) -> None:
        """Test successful process start."""
        directory = tmp_path / "env"
        directory.mkdir()

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._process._wait_ready", return_value=25565) as mock_wait,
        ):
            running = start(directory)

            # Should write PID file
            assert (directory / PID_FILE).exists()
            assert (directory / PID_FILE).read_text() == "12345"

            # Should call _wait_ready
            mock_wait.assert_called_once_with(mock_process, directory, STARTUP_TIMEOUT)

            # Should return RunningProcess
            assert running.directory == directory
            assert running.pid == 12345
            assert running.port == 25565

    def test_start_creates_correct_command(self, tmp_path: Path, mock_process: Mock) -> None:
        """Test that start creates correct Java command."""
        directory = tmp_path / "env"
        directory.mkdir()

        with (
            patch("subprocess.Popen", return_value=mock_process) as mock_popen,
            patch("mcward._process._wait_ready", return_value=25565),
        ):
            start(directory)

            # Verify Popen was called with correct arguments
            mock_popen.assert_called_once()
            args = mock_popen.call_args
            cmd = args[0][0]

            assert cmd[0] == "java"
            assert f"-Dward.daemon={directory / PORT_FILE}" in cmd
            assert "-jar" in cmd
            assert str(directory / "server.jar") in cmd
            assert "nogui" in cmd

    def test_start_wait_ready_failure_cleans_up(self, tmp_path: Path, mock_process: Mock) -> None:
        """Test that startup failure cleans up PID/port files."""
        directory = tmp_path / "env"
        directory.mkdir()

        # Create port file that will be cleaned up
        (directory / PORT_FILE).write_text("25565")

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._process._wait_ready", side_effect=ProcessStartupError("Timeout")),
        ):
            with pytest.raises(ProcessStartupError):
                start(directory)

            # Should terminate process
            mock_process.terminate.assert_called_once()
            mock_process.wait.assert_called()

            # Should clean up files
            assert not (directory / PID_FILE).exists()
            assert not (directory / PORT_FILE).exists()

    def test_start_process_timeout_kills_process(self, tmp_path: Path, mock_process: Mock) -> None:
        """Test that process is killed if it doesn't terminate in time."""
        directory = tmp_path / "env"
        directory.mkdir()

        # Make wait() raise timeout
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("cmd", 30), None]

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._process._wait_ready", side_effect=ProcessStartupError("Timeout")),
        ):
            with pytest.raises(ProcessStartupError):
                start(directory)

            # Should try terminate, then kill
            mock_process.terminate.assert_called_once()
            mock_process.kill.assert_called_once()

    def test_start_custom_timeout(self, tmp_path: Path, mock_process: Mock) -> None:
        """Test start with custom timeout."""
        directory = tmp_path / "env"
        directory.mkdir()

        with (
            patch("subprocess.Popen", return_value=mock_process),
            patch("mcward._process._wait_ready", return_value=25565) as mock_wait,
        ):
            start(directory, timeout=60.0)

            # Should pass custom timeout to _wait_ready
            mock_wait.assert_called_once_with(mock_process, directory, 60.0)


class TestStop:
    """Test process stop function."""

    @pytest.fixture
    def running(self, tmp_path: Path) -> RunningProcess:
        """Create a RunningProcess for testing."""
        directory = tmp_path / "env"
        directory.mkdir()
        (directory / PID_FILE).write_text("12345")
        (directory / PORT_FILE).write_text("25565")
        return RunningProcess(directory, 12345, 25565)

    def test_stop_graceful_shutdown(self, running: RunningProcess) -> None:
        """Test graceful process shutdown."""
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.wait.return_value = None  # Exits gracefully

        with (
            patch("mcward._process.socket.connect"),
            patch("mcward._process.socket.send_message"),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            # Should wait for graceful exit
            mock_psutil.wait.assert_called_once_with(SHUTDOWN_TIMEOUT)

            # Should clean up files
            assert not (running.directory / PID_FILE).exists()
            assert not (running.directory / PORT_FILE).exists()

    def test_stop_sends_stop_command(self, running: RunningProcess) -> None:
        """Test that stop command is sent via socket."""
        mock_socket = MagicMock()
        mock_psutil = Mock(spec=psutil.Process)

        with (
            patch("mcward._process.socket.connect", return_value=mock_socket) as mock_connect,
            patch("mcward._process.socket.send_message") as mock_send,
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            # Should connect and send stop command
            mock_connect.assert_called_once_with(running.address)
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[1] == {"type": "stop", "protocol": PROTOCOL_VERSION}

    def test_stop_terminates_if_not_graceful(self, running: RunningProcess) -> None:
        """Test that process is terminated if it doesn't exit gracefully."""
        mock_psutil = Mock(spec=psutil.Process)
        mock_psutil.wait.side_effect = [psutil.TimeoutExpired(30), None]

        with (
            patch("mcward._process.socket.connect"),
            patch("mcward._process.socket.send_message"),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            # Should call wait, then terminate, then wait again
            assert mock_psutil.wait.call_count == 2
            mock_psutil.terminate.assert_called_once()

    def test_stop_kills_if_terminate_fails(self, running: RunningProcess) -> None:
        """Test that process is killed if terminate fails."""
        mock_psutil = Mock(spec=psutil.Process)
        # Timeout on wait, timeout after terminate, then succeeds after kill
        mock_psutil.wait.side_effect = [psutil.TimeoutExpired(30), psutil.TimeoutExpired(30), None]

        with (
            patch("mcward._process.socket.connect"),
            patch("mcward._process.socket.send_message"),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running)

            # Should try wait, terminate, wait, kill, wait
            assert mock_psutil.wait.call_count == 3
            mock_psutil.terminate.assert_called_once()
            mock_psutil.kill.assert_called_once()

    def test_stop_handles_no_such_process(self, running: RunningProcess) -> None:
        """Test that NoSuchProcess exception is handled."""
        with (
            patch("mcward._process.socket.connect"),
            patch("mcward._process.socket.send_message"),
            patch("psutil.Process", side_effect=psutil.NoSuchProcess(12345)),
        ):
            # Should not raise - just clean up files
            stop(running)

            assert not (running.directory / PID_FILE).exists()
            assert not (running.directory / PORT_FILE).exists()

    def test_stop_handles_connection_error(self, running: RunningProcess) -> None:
        """Test that connection errors are handled gracefully."""
        mock_psutil = Mock(spec=psutil.Process)

        with (
            patch("mcward._process.socket.connect", side_effect=ProcessConnectionError("Failed")),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            # Should not raise - continues with force stop
            stop(running)

            # Should still try psutil operations
            mock_psutil.wait.assert_called()

    def test_stop_custom_timeout(self, running: RunningProcess) -> None:
        """Test stop with custom timeout."""
        mock_psutil = Mock(spec=psutil.Process)

        with (
            patch("mcward._process.socket.connect"),
            patch("mcward._process.socket.send_message"),
            patch("psutil.Process", return_value=mock_psutil),
        ):
            stop(running, timeout=5.0)

            # Should pass custom timeout to wait
            mock_psutil.wait.assert_called_once_with(5.0)


class TestStatus:
    """Test status command."""

    def test_status_success(self) -> None:
        """Test successful status request."""
        address = ("127.0.0.1", 25565)
        response = {"type": "status_response", "ready": True}

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter([response]))

        with (
            patch("mcward._process.socket.connect", return_value=mock_socket) as mock_connect,
            patch("mcward._process.socket.send_message") as mock_send,
            patch("mcward._process.socket.receive_messages", mock_receive),
        ):
            result = status(address)

            # Should connect, send status command, receive response
            mock_connect.assert_called_once_with(address)
            mock_send.assert_called_once()
            assert mock_send.call_args[0][1] == {"type": "status", "protocol": PROTOCOL_VERSION}

            assert result == response

    def test_status_error_response_raises(self) -> None:
        """Test that error response raises ProcessConnectionError."""
        address = ("127.0.0.1", 25565)
        error = {"type": "error", "message": "Protocol mismatch"}

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter([error]))

        with (
            patch("mcward._process.socket.connect", return_value=mock_socket),
            patch("mcward._process.socket.send_message"),
            patch("mcward._process.socket.receive_messages", mock_receive),
        ):
            with pytest.raises(ProcessConnectionError, match="Status failed"):
                status(address)

    def test_status_no_response_raises(self) -> None:
        """Test that no response raises ProcessConnectionError."""
        address = ("127.0.0.1", 25565)

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter([]))  # No messages

        with (
            patch("mcward._process.socket.connect", return_value=mock_socket),
            patch("mcward._process.socket.send_message"),
            patch("mcward._process.socket.receive_messages", mock_receive),
        ):
            with pytest.raises(ProcessConnectionError, match="No status response"):
                status(address)


class TestTest:
    """Test test command and event streaming."""

    def test_test_streams_events(self) -> None:
        """Test that test command streams events."""
        address = ("127.0.0.1", 25565)
        events = [
            {"type": "tests_started", "total": 2},
            {"type": "test_passed", "name": "test1"},
            {"type": "test_passed", "name": "test2"},
            {"type": "tests_finished", "passed": 2, "failed": 0},
        ]

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter(events))

        with (
            patch("mcward._process.socket.connect", return_value=mock_socket) as mock_connect,
            patch("mcward._process.socket.send_message") as mock_send,
            patch("mcward._process.socket.receive_messages", mock_receive),
        ):
            result = list(run_test(address))

            # Should connect and send test command
            mock_connect.assert_called_once_with(address)
            mock_send.assert_called_once()
            cmd = mock_send.call_args[0][1]
            assert cmd["type"] == "test"
            assert cmd["protocol"] == PROTOCOL_VERSION
            assert cmd["selector"] == "*:*"

            # Should yield all events
            assert result == events

    def test_test_custom_selector(self) -> None:
        """Test test command with custom selector."""
        address = ("127.0.0.1", 25565)
        events = [{"type": "tests_finished"}]

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter(events))

        with (
            patch("mcward._process.socket.connect", return_value=mock_socket),
            patch("mcward._process.socket.send_message") as mock_send,
            patch("mcward._process.socket.receive_messages", mock_receive),
        ):
            list(run_test(address, selector="mypack:test_*"))

            # Should send custom selector
            cmd = mock_send.call_args[0][1]
            assert cmd["selector"] == "mypack:test_*"

    def test_test_stops_on_tests_finished(self) -> None:
        """Test that iteration stops when tests_finished is received."""
        address = ("127.0.0.1", 25565)
        events = [
            {"type": "test_passed", "name": "test1"},
            {"type": "tests_finished", "passed": 1},
            {"type": "should_not_see_this"},  # After tests_finished
        ]

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter(events))

        with (
            patch("mcward._process.socket.connect", return_value=mock_socket),
            patch("mcward._process.socket.send_message"),
            patch("mcward._process.socket.receive_messages", mock_receive),
        ):
            result = list(run_test(address))

            # Should stop after tests_finished (only first 2 events)
            assert len(result) == 2
            assert result[0]["type"] == "test_passed"
            assert result[1]["type"] == "tests_finished"

    def test_test_stops_on_error(self) -> None:
        """Test that iteration stops when error is received."""
        address = ("127.0.0.1", 25565)
        events = [
            {"type": "test_passed", "name": "test1"},
            {"type": "error", "message": "Something failed"},
            {"type": "should_not_see_this"},
        ]

        mock_socket = MagicMock()
        mock_receive = MagicMock(return_value=iter(events))

        with (
            patch("mcward._process.socket.connect", return_value=mock_socket),
            patch("mcward._process.socket.send_message"),
            patch("mcward._process.socket.receive_messages", mock_receive),
        ):
            result = list(run_test(address))

            # Should stop after error (only first 2 events)
            assert len(result) == 2
            assert result[1]["type"] == "error"
