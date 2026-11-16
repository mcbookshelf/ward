"""Locating and parsing datapack sources, on disk or inside zipped packs."""

import json
import re
import sys
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_IGNORE_MARKER = re.compile(r"#\s*@coverage\s+(ignore|off|on)")
_SOURCE_SUFFIXES = (".mcfunction", ".json", ".mcmeta")

type PackFormat = tuple[int, int]


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
    """Lines excluded by ``# @coverage``: ``ignore`` skips one command, ``off`` until ``on``."""
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
    """Non-blank entries and their start lines, folding trailing backslashes like the game."""
    lines = source.splitlines()
    i = 0
    while i < len(lines):
        start = i + 1
        line = lines[i].strip()
        while line.endswith("\\"):
            i += 1
            if i == len(lines):
                # An unterminated continuation fails to compile: nothing after it runs
                return
            line = line[:-1] + lines[i].strip()
        if line:
            yield start, line
        i += 1


def scan_functions(
    datapacks: Sequence[Path],
    pack_format: PackFormat | None = None,
) -> dict[str, SourceFile]:
    """Function ids to sources; later packs win, overlays of ``pack_format`` on top."""
    functions: dict[str, SourceFile] = {}
    for pack in datapacks:
        for folder in _data_folders(pack, pack_format):
            if pack.is_file():
                members = (member for member in _zip_sources(pack) if member.startswith(folder))
                sources = ((m.removeprefix(folder), SourceFile(pack, m)) for m in members)
            else:
                root = pack / folder
                files = root.glob("data/*/function/**/*.mcfunction")
                sources = ((file.relative_to(root).as_posix(), SourceFile(file)) for file in files)
            for member, source in sources:
                if (name := _function_id(member)) is not None:
                    functions[name] = source
    return functions


def find_resource(
    datapacks: Sequence[Path],
    kind: str,
    element: str,
    pack_format: PackFormat | None = None,
) -> SourceFile | None:
    """The element's JSON source in the pack (or zip), and the overlay, that wins the stack."""
    namespace, _, path = element.partition(":")
    for pack in reversed(datapacks):
        for folder in reversed(_data_folders(pack, pack_format)):
            member = f"{folder}data/{namespace}/{kind}/{path}.json"
            if pack.is_file():
                if member in _zip_sources(pack):
                    return SourceFile(pack, member)
            elif (file := pack / member).is_file():
                return SourceFile(file)
    return None


def _data_folders(pack: Path, pack_format: PackFormat | None) -> list[str]:
    """The data folder prefixes for the format: the root, then each overlay, winner last."""
    if pack_format is None:
        return [""]
    source = SourceFile(pack, "pack.mcmeta") if pack.is_file() else SourceFile(pack / "pack.mcmeta")
    try:
        metadata = json.loads(source.read() or "")
    except ValueError:
        return [""]
    return ["", *(f"{overlay}/" for overlay in _overlays(metadata, pack_format))]


def _overlays(metadata: object, pack_format: PackFormat) -> Iterator[str]:
    """The overlay directories whose format range holds the pack format."""
    match metadata:
        case {"overlays": {"entries": [*entries]}}:
            for entry in entries:
                match entry:
                    case {"directory": str(directory), "min_format": low, "max_format": high}:
                        low, high = _format_bound(low, 0), _format_bound(high, sys.maxsize)
                        if low and high and low <= pack_format <= high:
                            yield directory


def _format_bound(value: object, minor: int) -> PackFormat | None:
    """A pack format, a number or [major, minor]; ``minor`` stands in for a missing one."""
    match value:
        case int(major) | [int(major)]:
            return major, minor
        case [int(major), int(given), *_]:
            return major, given
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
    """The pack's function and JSON members, read once and cached on the file's stat."""
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


type JsonSpans = dict[str, tuple[tuple[int, int], tuple[int, int]]]


def json_spans(text: str) -> JsonSpans:
    """Each JSON object's line span and character span, by path (``pools[0].entries[2]``)."""
    spans: JsonSpans = {}
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
            spans[path] = ((start_line, line), (start_pos, pos))
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
            start = pos
            while pos < len(text) and text[pos] not in ",}] \t\r\n":
                pos += 1
            # A value of no length would leave the enclosing array scanning the same spot forever
            if pos == start:
                raise ValueError(f"expected a value at position {pos}")

    scan_value("")
    return spans
