"""The Python end of the WardBridge: line-delimited JSON over TCP."""

import json
import socket
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import Any

from ._constants import SOCKET_CONNECT_TIMEOUT
from ._exceptions import ProcessConnectionError, ProcessTimeoutError


@contextmanager
def connect(
    address: tuple[str, int],
    timeout: float = SOCKET_CONNECT_TIMEOUT,
) -> Generator[socket.socket]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        try:
            sock.connect(address)
        except OSError as e:
            host, port = address
            raise ProcessConnectionError(f"Could not connect to {host}:{port}: {e}") from e
        yield sock
    finally:
        sock.close()


def send_message(sock: socket.socket, message: dict[str, Any]) -> None:
    data = json.dumps(message) + "\n"
    try:
        sock.sendall(data.encode("utf-8"))
    except OSError as e:
        raise ProcessConnectionError(f"Connection lost while sending: {e}") from e


def receive_messages(
    sock: socket.socket,
    timeout: float | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield each JSON line the peer sends, until it closes or ``timeout`` passes."""
    try:
        sock.settimeout(timeout)
        with sock.makefile("r", encoding="utf-8") as f:
            for line in f:
                if line := line.strip():
                    yield json.loads(line)
    except TimeoutError as e:
        raise ProcessTimeoutError("Socket timeout while receiving messages") from e
    except json.JSONDecodeError as e:
        raise ProcessConnectionError(f"Invalid JSON from process: {e}") from e
    except OSError as e:
        raise ProcessConnectionError(f"Connection lost while receiving messages: {e}") from e
