"""Low-level communication for Ward process IPC."""

import json
import socket
from collections.abc import Iterator
from contextlib import contextmanager

from ._constants import EVENT_STREAM_TIMEOUT, SOCKET_CONNECT_TIMEOUT
from ._exceptions import ProcessConnectionError


@contextmanager
def connect(address, timeout: float = SOCKET_CONNECT_TIMEOUT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        sock.connect(address)
        yield sock
    except OSError as e:
        raise ProcessConnectionError(f"Failed to connect: {e}") from e
    finally:
        sock.close()


def send_message(sock: socket.socket, message: dict) -> None:
    """Send JSON message to socket."""
    data = json.dumps(message) + "\n"
    sock.sendall(data.encode("utf-8"))


def receive_messages(sock: socket.socket, timeout: float = EVENT_STREAM_TIMEOUT) -> Iterator[dict]:
    """Receive line-delimited JSON messages from socket."""
    try:
        sock.settimeout(timeout)
        with sock.makefile("r", encoding="utf-8") as f:
            for line in f:
                if line := line.strip():
                    yield json.loads(line)
    except TimeoutError as e:
        raise ProcessConnectionError("Socket timeout while receiving messages") from e
    except json.JSONDecodeError as e:
        raise ProcessConnectionError(f"Invalid JSON from process: {e}") from e
