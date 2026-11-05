"""Watch mode: rerun the tests when a file changes or a key is pressed."""

import queue
import sys
import threading
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import rich_click as click
import watchfiles

from .ui import console

type Run = Callable[[str], object]
type Ignore = Callable[[Path], bool]

CHANGE = "change"
ENTER = ("\r", "\n")
BACKSPACE = ("\b", "\x7f")
ESCAPE = "\x1b"
INTERRUPT = "\x03"


class WatchLoop:
    """Turns file changes and key presses into runs.

    ``a`` or Enter runs every selected test, ``p`` reads a selector that narrows
    the next runs, and ``q`` quits. Changes made while a selector is typed wait
    for it to be done.
    """

    def __init__(self, run: Run, selector: str) -> None:
        self.run = run
        self.default = selector
        self.selector = selector
        self.prompt: str | None = None
        self.pending = True

    def run_pending(self) -> None:
        if not self.pending or self.prompt is not None:
            return
        self.pending = False
        console.clear()
        try:
            self.run(self.selector)
        except click.ClickException as e:
            console.print(f"[red]Error: {e.format_message()}[/]", highlight=False)
        console.print()
        if self.selector != self.default:
            console.print(f"[dim]Filtered to [bold]{self.selector}[/][/]", highlight=False)
        console.print(
            "[dim]Watching for changes. Press [bold]a[/] or [bold]Enter[/] to run all, "
            "[bold]p[/] to filter by selector, [bold]q[/] to quit.[/]",
            highlight=False,
        )

    def handle(self, event: str) -> bool:
        """Apply one event; False means quit."""
        if event == INTERRUPT:
            return False
        if event == CHANGE:
            self.pending = True
        elif self.prompt is not None:
            self._type(event)
        elif event == "q":
            return False
        elif event == "a" or event in ENTER:
            self.selector = self.default
            self.pending = True
        elif event == "p":
            self.prompt = ""
            _echo("\nSelector: ")
        return True

    def _type(self, key: str) -> None:
        assert self.prompt is not None
        if key in ENTER:
            self.selector = self.prompt.strip() or self.default
            self.prompt = None
            self.pending = True
        elif key == ESCAPE:
            self.prompt = None
            _echo("\n")
        elif key in BACKSPACE:
            if self.prompt:
                self.prompt = self.prompt[:-1]
                _echo("\b \b")
        elif key.isprintable():
            self.prompt += key
            _echo(key)


def watch(run: Run, selector: str, paths: Sequence[Path], ignore: Ignore | None = None) -> None:
    """Run the tests, then again on every change under the paths, until quit."""
    events: queue.Queue[str] = queue.Queue()
    stop = threading.Event()
    loop = WatchLoop(run, selector)

    def changes() -> None:
        default = watchfiles.DefaultFilter()

        def keep(change: watchfiles.Change, path: str) -> bool:
            return default(change, path) and not (ignore and ignore(Path(path)))

        for _ in watchfiles.watch(*paths, watch_filter=keep, stop_event=stop):
            events.put(CHANGE)

    def keys() -> None:
        for key in _read_keys():
            events.put(key)

    threading.Thread(target=changes, daemon=True).start()
    interactive = sys.stdin.isatty()
    if interactive:
        threading.Thread(target=keys, daemon=True).start()

    try:
        with _cbreak(interactive):
            while True:
                loop.run_pending()
                try:
                    # A timeout keeps Ctrl+C responsive on Windows
                    event = events.get(timeout=0.2)
                except queue.Empty:
                    continue
                if not loop.handle(event):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()


def _echo(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


def _read_keys() -> Iterator[str]:
    if sys.platform == "win32":
        import msvcrt

        while True:
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                msvcrt.getwch()  # the second half of an arrow or function key
                continue
            yield key
    else:
        while key := sys.stdin.read(1):
            yield key


@contextmanager
def _cbreak(enabled: bool) -> Iterator[None]:
    """Deliver key presses one by one without echo, restored on exit by the main thread."""
    if not enabled or sys.platform == "win32":
        yield
        return

    import termios
    import tty

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    try:
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)
