"""An exclusive lock on an environment, shared by every mcward process."""

import os
import sys
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

if sys.platform == "win32":
    import msvcrt

    def _try_lock(fd: int) -> None:
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

    def _unlock(fd: int) -> None:
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


type Notice = Callable[[Path], None]

_on_wait: Notice | None = None


def on_wait(notice: Notice | None) -> None:
    """Set what is called once, with the environment folder, when its lock is not free."""
    global _on_wait
    _on_wait = notice


@contextmanager
def hold(directory: Path, poll: float = 0.2) -> Generator[None]:
    """Wait until no other process holds the environment, then hold it."""
    # Next to the folder: uninstall removes the folder, and an open file blocks that on Windows
    path = directory.with_name(f"{directory.name}.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT)
    try:
        waiting = False
        while True:
            try:
                _try_lock(fd)
                break
            except OSError:
                if _on_wait and not waiting:
                    _on_wait(directory)
                waiting = True
                time.sleep(poll)
        try:
            yield
        finally:
            _unlock(fd)
    finally:
        os.close(fd)
