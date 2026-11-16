"""Tests for the lock that keeps two mcward processes off one environment."""

import subprocess
import sys
import threading
import time
from pathlib import Path

from mcward._lock import hold, on_wait

HOLD_IN_CHILD = """
import sys, time
from pathlib import Path
from mcward._lock import hold
with hold(Path(sys.argv[1])):
    print("held", flush=True)
    time.sleep(float(sys.argv[2]))
"""


def test_lock_file_sits_next_to_the_environment(tmp_path: Path) -> None:
    with hold(tmp_path / "26.1.2"):
        assert (tmp_path / "26.1.2.lock").is_file()
    assert not (tmp_path / "26.1.2").exists()


def test_second_holder_waits_for_the_first(tmp_path: Path) -> None:
    order: list[str] = []
    entered = threading.Event()

    def second() -> None:
        entered.wait()
        with hold(tmp_path / "env", poll=0.01):
            order.append("second")

    thread = threading.Thread(target=second)
    thread.start()
    with hold(tmp_path / "env"):
        entered.set()
        time.sleep(0.2)
        order.append("first")
    thread.join(timeout=5)

    assert order == ["first", "second"]


def test_a_wait_is_announced_once(tmp_path: Path) -> None:
    announced: list[Path] = []
    entered = threading.Event()

    def second() -> None:
        entered.wait()
        with hold(tmp_path / "env", poll=0.01):
            pass

    on_wait(announced.append)
    try:
        thread = threading.Thread(target=second)
        thread.start()
        with hold(tmp_path / "env"):
            entered.set()
            time.sleep(0.2)
        thread.join(timeout=5)
    finally:
        on_wait(None)

    assert announced == [tmp_path / "env"]


def test_a_free_lock_announces_nothing(tmp_path: Path) -> None:
    announced: list[Path] = []
    on_wait(announced.append)
    try:
        with hold(tmp_path / "env"):
            pass
    finally:
        on_wait(None)

    assert announced == []


def test_lock_excludes_another_process(tmp_path: Path) -> None:
    child = subprocess.Popen(
        [sys.executable, "-c", HOLD_IN_CHILD, str(tmp_path / "env"), "0.5"],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert child.stdout is not None
    assert child.stdout.readline().strip() == "held"

    start = time.monotonic()
    with hold(tmp_path / "env", poll=0.01):
        waited = time.monotonic() - start
    child.wait(timeout=5)

    assert waited > 0.3
