"""Tests for socket IPC communication."""

import json
import socket
from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcward._constants import EVENT_STREAM_TIMEOUT, SOCKET_CONNECT_TIMEOUT
from mcward._exceptions import ProcessConnectionError
from mcward._socket import connect, receive_messages, send_message


class TestConnect:
    """Test socket connection context manager."""

    def test_connect_success(self) -> None:
        """Test successful socket connection."""
        mock_socket = MagicMock()

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with connect(("127.0.0.1", 25565)) as sock:
                assert sock is mock_socket
                mock_socket.settimeout.assert_called_once_with(SOCKET_CONNECT_TIMEOUT)
                mock_socket.connect.assert_called_once_with(("127.0.0.1", 25565))

            # Socket should be closed after context
            mock_socket.close.assert_called_once()

    def test_connect_with_custom_timeout(self) -> None:
        """Test connection with custom timeout."""
        mock_socket = MagicMock()

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with connect(("127.0.0.1", 25565), timeout=5.0) as sock:
                assert sock is mock_socket
                mock_socket.settimeout.assert_called_once_with(5.0)

    def test_connect_failure_raises_process_connection_error(self) -> None:
        """Test that connection failure raises ProcessConnectionError."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with pytest.raises(ProcessConnectionError, match="Failed to connect"):
                with connect(("127.0.0.1", 25565)):
                    pass

            # Socket should still be closed
            mock_socket.close.assert_called_once()

    def test_connect_timeout_raises_process_connection_error(self) -> None:
        """Test that socket timeout raises ProcessConnectionError."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = TimeoutError("Connection timeout")

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with pytest.raises(ProcessConnectionError, match="Failed to connect"):
                with connect(("127.0.0.1", 25565)):
                    pass

    def test_connect_os_error_raises_process_connection_error(self) -> None:
        """Test that OS errors raise ProcessConnectionError."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = OSError("Network unreachable")

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with pytest.raises(ProcessConnectionError, match="Failed to connect"):
                with connect(("127.0.0.1", 25565)):
                    pass

    def test_connect_creates_tcp_socket(self) -> None:
        """Test that connect creates a TCP socket."""
        mock_socket = MagicMock()

        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.return_value = mock_socket

            with connect(("127.0.0.1", 25565)):
                pass

            # Should create AF_INET, SOCK_STREAM socket (TCP)
            mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)


class TestSendMessage:
    """Test JSON message sending."""

    def test_send_simple_message(self) -> None:
        """Test sending a simple JSON message."""
        mock_socket = MagicMock()
        message = {"type": "status", "protocol": 1}

        send_message(mock_socket, message)

        # Should send JSON with newline
        expected = json.dumps(message) + "\n"
        mock_socket.sendall.assert_called_once_with(expected.encode("utf-8"))

    def test_send_complex_message(self) -> None:
        """Test sending a complex message with nested data."""
        mock_socket = MagicMock()
        message = {
            "type": "test",
            "protocol": 1,
            "selector": "*:*",
            "metadata": {
                "timeout": 30,
                "tags": ["integration", "smoke"],
            },
        }

        send_message(mock_socket, message)

        expected = json.dumps(message) + "\n"
        mock_socket.sendall.assert_called_once_with(expected.encode("utf-8"))

    def test_send_message_with_unicode(self) -> None:
        """Test sending message with unicode characters."""
        mock_socket = MagicMock()
        message = {"type": "test", "name": "test_emoji_🎉"}

        send_message(mock_socket, message)

        expected = json.dumps(message) + "\n"
        mock_socket.sendall.assert_called_once_with(expected.encode("utf-8"))


class TestReceiveMessages:
    """Test line-delimited JSON message receiving."""

    def test_receive_single_message(self) -> None:
        """Test receiving a single JSON message."""
        mock_socket = MagicMock()
        message = {"type": "status_response", "ready": True}

        # Mock makefile to return a StringIO with our message
        mock_file = StringIO(json.dumps(message) + "\n")
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        messages = list(receive_messages(mock_socket))

        assert len(messages) == 1
        assert messages[0] == message
        mock_socket.settimeout.assert_called_once_with(EVENT_STREAM_TIMEOUT)

    def test_receive_multiple_messages(self) -> None:
        """Test receiving multiple line-delimited messages."""
        mock_socket = MagicMock()
        messages = [
            {"type": "tests_started", "total": 3},
            {"type": "test_passed", "name": "test1"},
            {"type": "test_passed", "name": "test2"},
            {"type": "tests_finished", "passed": 2},
        ]

        # Create line-delimited JSON
        lines = "\n".join(json.dumps(m) for m in messages) + "\n"
        mock_file = StringIO(lines)
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        received = list(receive_messages(mock_socket))

        assert received == messages

    def test_receive_with_custom_timeout(self) -> None:
        """Test receiving messages with custom timeout."""
        mock_socket = MagicMock()
        mock_file = StringIO('{"type": "status"}\n')
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        list(receive_messages(mock_socket, timeout=5.0))

        mock_socket.settimeout.assert_called_once_with(5.0)

    def test_receive_empty_lines_ignored(self) -> None:
        """Test that empty lines are ignored."""
        mock_socket = MagicMock()

        # Lines with empty/whitespace lines
        lines = '\n{"type": "test1"}\n\n  \n{"type": "test2"}\n'
        mock_file = StringIO(lines)
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        messages = list(receive_messages(mock_socket))

        assert len(messages) == 2
        assert messages[0] == {"type": "test1"}
        assert messages[1] == {"type": "test2"}

    def test_receive_socket_timeout_raises_error(self) -> None:
        """Test that socket timeout raises ProcessConnectionError."""
        mock_socket = MagicMock()
        mock_socket.settimeout = Mock()

        # Simulate timeout when reading
        mock_file = MagicMock()
        mock_file.__iter__.side_effect = TimeoutError("Timeout")
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        with pytest.raises(ProcessConnectionError, match="Socket timeout"):
            list(receive_messages(mock_socket))

    def test_receive_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises ProcessConnectionError."""
        mock_socket = MagicMock()

        # Invalid JSON
        mock_file = StringIO("not valid json\n")
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        with pytest.raises(ProcessConnectionError, match="Invalid JSON"):
            list(receive_messages(mock_socket))

    def test_receive_partial_json_raises_error(self) -> None:
        """Test that incomplete JSON raises ProcessConnectionError."""
        mock_socket = MagicMock()

        # Truncated JSON
        mock_file = StringIO('{"type": "test", "incom\n')
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        with pytest.raises(ProcessConnectionError, match="Invalid JSON"):
            list(receive_messages(mock_socket))

    def test_receive_messages_iterator_behavior(self) -> None:
        """Test that receive_messages works as iterator."""
        mock_socket = MagicMock()
        messages = [{"id": 1}, {"id": 2}, {"id": 3}]

        lines = "\n".join(json.dumps(m) for m in messages) + "\n"
        mock_file = StringIO(lines)
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        # Should work as iterator
        iterator = receive_messages(mock_socket)
        assert next(iterator) == {"id": 1}
        assert next(iterator) == {"id": 2}
        assert next(iterator) == {"id": 3}

        # Should raise StopIteration when done
        with pytest.raises(StopIteration):
            next(iterator)


class TestSocketIntegration:
    """Test socket functions working together."""

    def test_send_and_receive_roundtrip(self) -> None:
        """Test sending and receiving messages in sequence."""
        mock_socket = MagicMock()

        # Simulate sending a command
        command = {"type": "status", "protocol": 1}
        send_message(mock_socket, command)

        # Verify command was sent
        expected_sent = json.dumps(command) + "\n"
        mock_socket.sendall.assert_called_once_with(expected_sent.encode("utf-8"))

        # Simulate receiving response
        response = {"type": "status_response", "ready": True}
        mock_file = StringIO(json.dumps(response) + "\n")
        mock_socket.makefile.return_value.__enter__.return_value = mock_file

        messages = list(receive_messages(mock_socket))
        assert messages == [response]
