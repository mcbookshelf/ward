"""Tests for the WardBridge socket protocol."""

import json
import socket
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcward._bridge import connect, receive_messages, send_message
from mcward._constants import SOCKET_CONNECT_TIMEOUT
from mcward._exceptions import ProcessConnectionError


class TestConnect:
    def test_connect_success(self) -> None:
        mock_socket = MagicMock()

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with connect(("127.0.0.1", 25565)) as sock:
                assert sock is mock_socket
                mock_socket.settimeout.assert_called_once_with(SOCKET_CONNECT_TIMEOUT)
                mock_socket.connect.assert_called_once_with(("127.0.0.1", 25565))

            mock_socket.close.assert_called_once()

    def test_connect_with_custom_timeout(self) -> None:
        mock_socket = MagicMock()

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with connect(("127.0.0.1", 25565), timeout=5.0) as sock:
                assert sock is mock_socket
                mock_socket.settimeout.assert_called_once_with(5.0)

    @pytest.mark.parametrize(
        "error",
        [
            ConnectionRefusedError("Connection refused"),
            TimeoutError("Connection timeout"),
            OSError("Network unreachable"),
        ],
    )
    def test_connect_failure_raises_process_connection_error(self, error: OSError) -> None:
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = error

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with pytest.raises(ProcessConnectionError, match="Could not connect"):
                with connect(("127.0.0.1", 25565)):
                    pass

            mock_socket.close.assert_called_once()

    def test_connect_creates_tcp_socket(self) -> None:
        mock_socket = MagicMock()

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with connect(("127.0.0.1", 25565)):
                pass

            mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)

    def test_connect_message_names_the_address(self) -> None:
        """The error says which daemon was unreachable."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = ConnectionRefusedError("refused")

        with patch("socket.socket", return_value=mock_socket):
            with pytest.raises(ProcessConnectionError, match="127.0.0.1:52341"):
                with connect(("127.0.0.1", 52341)):
                    pass

    def test_errors_inside_the_block_are_not_relabeled(self) -> None:
        """A failure after connecting must not read as a connection failure."""
        mock_socket = MagicMock()

        with patch("socket.socket", return_value=mock_socket):
            with pytest.raises(ConnectionResetError):
                with connect(("127.0.0.1", 25565)):
                    raise ConnectionResetError("peer reset")

            mock_socket.close.assert_called_once()


class TestSendMessage:
    def test_send_message(self) -> None:
        mock_socket = MagicMock()
        message = {"type": "status", "protocol": 1}

        send_message(mock_socket, message)

        expected = json.dumps(message) + "\n"
        mock_socket.sendall.assert_called_once_with(expected.encode("utf-8"))

    def test_send_on_dead_connection_raises(self) -> None:
        """A dropped connection surfaces as ProcessConnectionError."""
        mock_socket = MagicMock()
        mock_socket.sendall.side_effect = ConnectionResetError("peer reset")

        with pytest.raises(ProcessConnectionError, match="sending"):
            send_message(mock_socket, {"type": "status"})


class TestReceiveMessages:
    def test_receive_single_message(self) -> None:
        mock_socket = MagicMock()
        message = {"type": "status", "ready": True}

        mock_file = StringIO(json.dumps(message) + "\n")
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        messages = list(receive_messages(mock_socket))

        assert messages == [message]
        # Default is a blocking stream: the peer closing ends it
        mock_socket.settimeout.assert_called_once_with(None)

    def test_receive_multiple_messages(self) -> None:
        mock_socket = MagicMock()
        messages = [
            {"type": "tests_started", "total": 3},
            {"type": "test_passed", "name": "test1"},
            {"type": "test_passed", "name": "test2"},
            {"type": "tests_finished", "passed": 2},
        ]

        lines = "\n".join(json.dumps(m) for m in messages) + "\n"
        mock_file = StringIO(lines)
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        received = list(receive_messages(mock_socket))

        assert received == messages

    def test_receive_with_custom_timeout(self) -> None:
        mock_socket = MagicMock()
        mock_file = StringIO('{"type": "status"}\n')
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        list(receive_messages(mock_socket, timeout=5.0))

        mock_socket.settimeout.assert_called_once_with(5.0)

    def test_receive_empty_lines_ignored(self) -> None:
        mock_socket = MagicMock()

        lines = '\n{"type": "test1"}\n\n  \n{"type": "test2"}\n'
        mock_file = StringIO(lines)
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        messages = list(receive_messages(mock_socket))

        assert messages == [{"type": "test1"}, {"type": "test2"}]

    def test_receive_socket_timeout_raises_error(self) -> None:
        mock_socket = MagicMock()
        mock_socket.settimeout = Mock()

        mock_file = MagicMock()
        mock_file.__iter__.side_effect = TimeoutError("Timeout")
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        with pytest.raises(ProcessConnectionError, match="Socket timeout"):
            list(receive_messages(mock_socket))

    @pytest.mark.parametrize("line", ["not valid json\n", '{"type": "test", "incom\n'])
    def test_receive_invalid_json_raises_error(self, line: str) -> None:
        mock_socket = MagicMock()
        mock_socket.makefile.return_value.__enter__.return_value = StringIO(line)

        with pytest.raises(ProcessConnectionError, match="Invalid JSON"):
            list(receive_messages(mock_socket))
