"""Locating and parsing datapack sources, on disk or inside zipped packs."""

import json
import re
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_IGNORE_MARKER = re.compile(r"#\s*@coverage\s+(ignore|off|on)")
_SOURCE_SUFFIXES = (".mcfunction", ".json")


@dataclass(frozen=True)
class SourceFile:
    """A pack source: a file on disk, or a member of a zipped pack."""

    path: Path
    member: str | None = None

    def read(self) -> str | None:
        """The decoded text, or None when unreadable."""
        try:
            if self.member is None:
                return self.path.read_text(encoding="utf-8")
            data = _zip_sources(self.path).get(self.member)
            return None if data is None else data.decode("utf-8")
        except OSError, ValueError:
            return None


def command_lines(source: str) -> list[int]:
    """1-based line numbers of a function file's commands, in entry order."""
    return [start for start, entry in _entries(source) if not entry.startswith("#")]


def ignored_lines(source: str) -> frozenset[int]:
    """Command line numbers excluded by ``# @coverage`` markers.

    ``ignore`` excludes the next command, ``off`` excludes commands until
    ``on`` or the end of the file.
    """
    ignored: set[int] = set()
    off = pending = False
    for start, entry in _entries(source):
        if entry.startswith("#"):
            if marker := _IGNORE_MARKER.fullmatch(entry):
                word = marker.group(1)
                off = word == "off" if word != "ignore" else off
                pending = pending or word == "ignore"
        else:
            if off or pending:
                ignored.add(start)
            pending = False
    return frozenset(ignored)


def _entries(source: str) -> Iterator[tuple[int, str]]:
    """A function file's non-blank entries with their 1-based start lines.

    Mirrors how the game compiles functions: a trailing backslash folds the
    next line into the entry, and an unterminated continuation fails to
    compile, so nothing after it runs.
    """
    lines = source.splitlines()
    i = 0
    while i < len(lines):
        start = i + 1
        line = lines[i].strip()
        while line.endswith("\\"):
            i += 1
            if i == len(lines):
                return
            line = line[:-1] + lines[i].strip()
        if line:
            yield start, line
        i += 1


def scan_functions(datapacks: Sequence[Path]) -> dict[str, SourceFile]:
    """Map function ids to their sources across the given datapacks.

    Later packs win id collisions, matching datapack stacking order.
    """
    functions: dict[str, SourceFile] = {}
    for pack in datapacks:
        if pack.is_file():
            sources = ((member, SourceFile(pack, member)) for member in _zip_sources(pack))
        else:
            files = pack.glob("data/*/function/**/*.mcfunction")
            sources = ((file.relative_to(pack).as_posix(), SourceFile(file)) for file in files)
        for member, source in sources:
            if (name := _function_id(member)) is not None:
                functions[name] = source
    return functions


def find_resource(datapacks: Sequence[Path], kind: str, element: str) -> SourceFile | None:
    """The element's JSON source in the pack (or zip) that wins the stack."""
    namespace, _, path = element.partition(":")
    member = f"data/{namespace}/{kind}/{path}.json"
    for pack in reversed(datapacks):
        if pack.is_file():
            if member in _zip_sources(pack):
                return SourceFile(pack, member)
        elif (file := pack / member).is_file():
            return SourceFile(file)
    return None


def _function_id(member: str) -> str | None:
    """The function id a zip member maps to, or None for any other resource."""
    parts = member.split("/")
    if len(parts) < 4 or parts[0] != "data" or parts[2] != "function":
        return None
    if not member.endswith(".mcfunction"):
        return None
    return f"{parts[1]}:{'/'.join(parts[3:]).removesuffix('.mcfunction')}"


def _zip_sources(pack: Path) -> dict[str, bytes]:
    """The pack's function and JSON members, read in one pass and cached.

    Opening an archive costs far more than reading it whole, and a report
    touches every function several times. The cache is keyed on the file's
    stat so a pack rebuilt at the same path is reloaded.
    """
    try:
        stat = pack.stat()
    except OSError:
        return {}
    return _read_zip_sources(pack, stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=8)
def _read_zip_sources(pack: Path, mtime_ns: int, size: int) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(pack) as archive:
            names = [name for name in archive.namelist() if name.endswith(_SOURCE_SUFFIXES)]
            return {name: archive.read(name) for name in names}
    except OSError, zipfile.BadZipFile:
        return {}


def json_spans(text: str) -> dict[str, tuple[int, int]]:
    """1-based line spans of every JSON object in the document, keyed by its
    NBT-style path (``pools[0].entries[2]``)."""
    return {path: (start, end) for path, (start, end, _, _) in _scan_json(text).items()}


def json_offsets(text: str) -> dict[str, tuple[int, int]]:
    """Character spans of every JSON object, as half-open offsets into the text."""
    return {path: (start, end) for path, (_, _, start, end) in _scan_json(text).items()}


def _scan_json(text: str) -> dict[str, tuple[int, int, int, int]]:
    """Every JSON object's (start_line, end_line, start_offset, end_offset) by path."""
    spans: dict[str, tuple[int, int, int, int]] = {}
    pos = 0
    line = 1

    def skip_whitespace() -> None:
        nonlocal pos, line
        while pos < len(text) and text[pos] in " \t\r\n":
            line += text[pos] == "\n"
            pos += 1

    def expect(char: str) -> None:
        nonlocal pos
        if pos >= len(text) or text[pos] != char:
            raise ValueError(f"expected {char!r} at position {pos}")
        pos += 1

    def scan_string() -> str:
        nonlocal pos
        start = pos = pos + 1
        while pos < len(text) and text[pos] != '"':
            pos += 1 + (text[pos] == "\\")
        expect('"')
        return json.loads(f'"{text[start : pos - 1]}"')

    def scan_value(path: str) -> None:
        nonlocal pos, line
        skip_whitespace()
        if pos >= len(text):
            raise ValueError("unexpected end of document")
        if text[pos] == "{":
            start_line, start_pos = line, pos
            pos += 1
            skip_whitespace()
            while pos < len(text) and text[pos] != "}":
                key = scan_string()
                skip_whitespace()
                expect(":")
                scan_value(f"{path}.{key}" if path else key)
                skip_whitespace()
                if pos < len(text) and text[pos] == ",":
                    pos += 1
                    skip_whitespace()
            expect("}")
            spans[path] = (start_line, line, start_pos, pos)
        elif text[pos] == "[":
            pos += 1
            skip_whitespace()
            index = 0
            while pos < len(text) and text[pos] != "]":
                scan_value(f"{path}[{index}]")
                index += 1
                skip_whitespace()
                if pos < len(text) and text[pos] == ",":
                    pos += 1
                    skip_whitespace()
            expect("]")
        elif text[pos] == '"':
            scan_string()
        else:
            while pos < len(text) and text[pos] not in ",}] \t\r\n":
                pos += 1

    scan_value("")
    return spans
