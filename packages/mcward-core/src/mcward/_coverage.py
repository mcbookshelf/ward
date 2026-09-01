"""Coverage analysis: mapping recorded hits back to source lines."""

import json
import re
import tomllib
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path

from ._exceptions import WardError
from ._protocol import Coverage, FunctionCoverage
from ._sources import (
    SourceFile,
    command_lines,
    find_resource,
    ignored_lines,
    json_spans,
    scan_functions,
)

_COMBINATORS = frozenset({"any_of", "all_of", "inverted"})
_PATH_SEGMENTS = re.compile(r"\[(\d+)\]|\.?([^.\[\]]+)")
_IGNORE_SHAPE = (
    "[coverage] ignore entries are id globs "
    'or tables like { kind = "loot_table", id = "ns:path", nodes = [...] }'
)


@dataclass(frozen=True)
class IgnoreRule:
    """One coverage exclusion: an element id glob, optionally pinned to a kind
    (ids are not unique across registries) and narrowed to JSON node paths or
    function lines. Without ``nodes`` or ``lines`` the whole element drops."""

    id: str
    kind: str | None = None
    nodes: tuple[str, ...] = ()
    lines: tuple[int, ...] = ()

    def matches(self, kind: str, name: str) -> bool:
        return fnmatchcase(name, self.id) and (self.kind is None or fnmatchcase(kind, self.kind))


@dataclass(frozen=True)
class CoverageIgnores:
    """Report-time exclusions from ``ward.toml``: a list of ignore entries,
    each a bare id glob or a ``{ kind, id, nodes, lines }`` table."""

    rules: tuple[IgnoreRule, ...] = ()

    @classmethod
    def load(cls, directory: Path | None = None) -> CoverageIgnores:
        """The exclusions declared in the directory's ward.toml, if present."""
        file = (directory or Path.cwd()) / "ward.toml"
        try:
            text = file.read_text(encoding="utf-8")
        except OSError:
            return cls()
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            raise WardError(f"Invalid {file.name}: {e}") from e

        entries = data.get("coverage", {}).get("ignore", [])
        if not isinstance(entries, list):
            raise WardError(f"Invalid {file.name}: {_IGNORE_SHAPE}")
        return cls(tuple(_parse_rule(file.name, entry) for entry in entries))

    def element(self, kind: str, name: str) -> bool:
        """Whether the whole element is ignored."""
        return any(
            rule.matches(kind, name) and not rule.nodes and not rule.lines for rule in self.rules
        )

    def node(self, kind: str, element: str, path: str) -> bool:
        """Whether one of the element's JSON nodes is ignored."""
        return any(
            rule.matches(kind, element) and any(_match_path(path, p) for p in rule.nodes)
            for rule in self.rules
        )

    def lines(self, name: str) -> frozenset[int]:
        """The function's source lines ignored from config."""
        return frozenset(
            line
            for rule in self.rules
            if rule.lines and rule.matches("function", name)
            for line in rule.lines
        )


def _parse_rule(source: str, entry: object) -> IgnoreRule:
    if isinstance(entry, str):
        return IgnoreRule(entry)
    if not isinstance(entry, dict) or set(entry) - {"kind", "id", "nodes", "lines"}:
        raise WardError(f"Invalid {source}: {_IGNORE_SHAPE}")
    id = entry.get("id")
    kind = entry.get("kind")
    nodes = entry.get("nodes", [])
    lines = entry.get("lines", [])
    if (
        not isinstance(id, str)
        or not isinstance(kind, str | None)
        or not isinstance(nodes, list)
        or not isinstance(lines, list)
    ):
        raise WardError(f"Invalid {source}: {_IGNORE_SHAPE}")
    node_patterns = tuple(p for p in nodes if isinstance(p, str))
    line_numbers = tuple(n for n in lines if isinstance(n, int))
    if len(node_patterns) != len(nodes) or len(line_numbers) != len(lines):
        raise WardError(f"Invalid {source}: {_IGNORE_SHAPE}")
    return IgnoreRule(id, kind, node_patterns, line_numbers)


def _match_path(path: str, pattern: str) -> bool:
    """Whether the node path matches the pattern, where ``*`` matches any run.

    Paths contain brackets, which fnmatch would read as character classes.
    """
    return re.fullmatch(".*".join(map(re.escape, pattern.split("*"))), path) is not None


@dataclass(frozen=True)
class LineCoverage:
    """Hit counts for one command, at its 1-based source line when known."""

    line: int | None
    reached: int
    executed: int


class CoverageReport(ABC):
    """One row of the coverage report: a function or a JSON resource."""

    name: str
    kind: str

    @property
    @abstractmethod
    def covered(self) -> int: ...

    @property
    @abstractmethod
    def total(self) -> int: ...

    @property
    @abstractmethod
    def touched(self) -> bool: ...

    @property
    def namespace(self) -> str:
        return self.name.partition(":")[0]

    @property
    def ratio(self) -> float:
        return self.covered / self.total if self.total else 1.0


@dataclass(frozen=True)
class FunctionReport(CoverageReport):
    """Line-resolved coverage for one function."""

    name: str
    file: SourceFile | None
    lines: tuple[LineCoverage, ...]

    kind = "function"

    @property
    def covered(self) -> int:
        """Commands that dispatched at least once."""
        return sum(line.executed > 0 for line in self.lines)

    @property
    def total(self) -> int:
        return len(self.lines)

    @property
    def touched(self) -> bool:
        return any(line.reached for line in self.lines)

    @property
    def guarded(self) -> tuple[LineCoverage, ...]:
        """Commands that were reached but whose fork or condition never passed."""
        return tuple(line for line in self.lines if line.reached and not line.executed)


@dataclass(frozen=True)
class ResourceReport(CoverageReport):
    """Data coverage for one JSON resource: its conditions and its gated blocks."""

    name: str
    kind: str
    file: SourceFile | None
    nodes: tuple[ConditionNode, ...]
    runs: tuple[RunNode, ...] = ()

    @property
    def counted(self) -> tuple[ConditionNode, ...]:
        """The conditions that count as branches: the leaves.

        A file holding nothing but combinators (a predicate built from
        references) falls back to counting those, so it still reports.
        """
        leaves = tuple(node for node in self.nodes if not node.combinator)
        if leaves or self.runs:
            return leaves
        return self.nodes

    @property
    def covered(self) -> int:
        """Conditions any test evaluated, plus blocks that actually ran."""
        return sum(node.evaluated for node in self.counted) + sum(run.ran > 0 for run in self.runs)

    @property
    def total(self) -> int:
        return len(self.counted) + len(self.runs)

    @property
    def touched(self) -> bool:
        return any(node.evaluated for node in self.nodes) or any(run.reached for run in self.runs)


@dataclass(frozen=True)
class ConditionNode:
    """Outcome counts for one condition, at its line span when known."""

    path: str
    lines: tuple[int, int] | None
    passed: int
    failed: int
    combinator: bool = False

    @property
    def counts(self) -> tuple[int, int]:
        return (self.passed, self.failed)

    @property
    def evaluated(self) -> bool:
        """Evaluated is covered, whichever way it went: an always-false condition
        still shows its gap at the site it gates (guarded line, blocked entry)."""
        return self.passed > 0 or self.failed > 0


@dataclass(frozen=True)
class RunNode:
    """Run counts for one gated block (loot entry, item modifier function)."""

    path: str
    lines: tuple[int, int] | None
    reached: int
    ran: int

    @property
    def counts(self) -> tuple[int, int]:
        return (self.reached, self.ran)

    @property
    def blocked(self) -> bool:
        """Whether the block was reached but its condition never let it run."""
        return self.reached > 0 and self.ran == 0


@dataclass(frozen=True)
class CoverageTotals:
    """Sums over a set of reports: covered and total units, touched and total files."""

    covered: int = 0
    total: int = 0
    touched: int = 0
    files: int = 0

    @classmethod
    def of(cls, reports: Iterable[CoverageReport]) -> CoverageTotals:
        reports = list(reports)
        return cls(
            sum(report.covered for report in reports),
            sum(report.total for report in reports),
            sum(report.touched for report in reports),
            len(reports),
        )

    @property
    def ratio(self) -> float | None:
        """The covered share, or None when there is nothing to cover."""
        return self.covered / self.total if self.total else None


@dataclass(frozen=True)
class ResolvedCoverage:
    """One run's recorded coverage, located in the packs' sources."""

    functions: list[FunctionReport]
    resources: list[ResourceReport]

    @property
    def reports(self) -> list[CoverageReport]:
        return [*self.functions, *self.resources]


def resolve_coverage(
    coverage: Coverage,
    datapacks: Sequence[Path],
    selector: str = "*:*",
    ignores: CoverageIgnores | None = None,
) -> ResolvedCoverage:
    """Resolve both the function and the resource reports of a run."""
    return ResolvedCoverage(
        resolve_functions(coverage, datapacks, selector, ignores),
        resolve_resources(coverage, datapacks, selector, ignores),
    )


def resolve_functions(
    coverage: Coverage,
    datapacks: Sequence[Path],
    selector: str = "*:*",
    ignores: CoverageIgnores | None = None,
) -> list[FunctionReport]:
    """Combine recorded hits with the packs' function sources, sorted by name.

    The report is scoped to the test selector's namespace: running one
    namespace's tests measures that namespace.
    """
    ignores = ignores or CoverageIgnores()
    scope = _scope_pattern(selector)
    sources = scan_functions(datapacks)
    reports = []

    for name in sorted(sources.keys() | coverage.functions.keys()):
        if not fnmatchcase(name.partition(":")[0], scope) or ignores.element("function", name):
            continue
        report = _function_report(name, sources.get(name), coverage.functions.get(name), ignores)
        if report is not None:
            reports.append(report)

    return reports


def _function_report(
    name: str,
    file: SourceFile | None,
    hits: FunctionCoverage | None,
    ignores: CoverageIgnores,
) -> FunctionReport | None:
    """Hits placed on the source's command lines; None when every line is ignored."""
    source = file.read() if file is not None else None
    lines = [] if source is None else command_lines(source)
    if hits is None:
        hits = FunctionCoverage((0,) * len(lines), (0,) * len(lines))
    if len(lines) != len(hits.reached):
        # The recorded entries do not match the source (rewritten or shadowed
        # by another pack): report counts without claiming line numbers
        file, source, lines = None, None, [None] * len(hits.reached)

    excluded = ignores.lines(name)
    if source is not None:
        excluded |= ignored_lines(source)
    entries = tuple(
        LineCoverage(line, reached, executed)
        for line, reached, executed in zip(lines, hits.reached, hits.executed, strict=True)
        if line not in excluded
    )
    if excluded and not entries:
        return None
    return FunctionReport(name, file, entries)


def resolve_resources(
    coverage: Coverage,
    datapacks: Sequence[Path],
    selector: str = "*:*",
    ignores: CoverageIgnores | None = None,
) -> list[ResourceReport]:
    """Locate the recorded nodes in the packs' JSON sources, sorted by kind and name.

    Like :func:`resolve_functions`, the report is scoped to the test selector's
    namespace.
    """
    ignores = ignores or CoverageIgnores()
    scope = _scope_pattern(selector)
    elements = {
        (registry, element)
        for source in (coverage.conditions, coverage.runs)
        for registry, names in source.items()
        for element in names
        if fnmatchcase(element.partition(":")[0], scope)
    }

    reports = []
    for registry, element in elements:
        kind = _registry_folder(registry)
        if ignores.element(kind, element):
            continue
        conditions = coverage.conditions.get(registry, {}).get(element, {})
        runs = coverage.runs.get(registry, {}).get(element, {})
        if ignores.rules:
            conditions = {p: c for p, c in conditions.items() if not ignores.node(kind, element, p)}
            runs = {p: c for p, c in runs.items() if not ignores.node(kind, element, p)}
            if not conditions and not runs:
                continue
        file = find_resource(datapacks, kind, element)
        spans, document = _resource_source(file)
        reports.append(
            ResourceReport(
                element,
                kind,
                file,
                tuple(
                    ConditionNode(
                        path, spans.get(path), passed, failed, _is_combinator(document, path)
                    )
                    for path, (passed, failed) in sorted(conditions.items())
                ),
                tuple(
                    RunNode(path, spans.get(path), reached, ran)
                    for path, (reached, ran) in sorted(runs.items())
                ),
            )
        )

    reports.sort(key=lambda report: (report.kind, report.name))
    return reports


def _scope_pattern(selector: str) -> str:
    """The namespace pattern a test selector scopes coverage to."""
    namespace, colon, _ = selector.partition(":")
    if not colon or namespace.startswith("#"):
        return "*"
    return namespace or "*"


def _registry_folder(registry: str) -> str:
    """The data folder a registry loads from: its path, namespaced unless vanilla."""
    namespace, _, path = registry.partition(":")
    return path if namespace == "minecraft" else f"{namespace}/{path}"


def _resource_source(file: SourceFile | None) -> tuple[dict[str, tuple[int, int]], object]:
    """A resource's node line spans and its parsed document, best effort."""
    text = file.read() if file is not None else None
    if text is None:
        return {}, None
    try:
        return json_spans(text), json.loads(text)
    except ValueError:
        return {}, None


def _is_combinator(document: object, path: str) -> bool:
    """Whether the node at the NBT-style path merely combines other conditions."""
    node = document
    for match in _PATH_SEGMENTS.finditer(path):
        index, key = match.groups()
        if index is not None and isinstance(node, list) and int(index) < len(node):
            node = node[int(index)]
        elif key is not None and isinstance(node, dict):
            node = node.get(key)
        else:
            return False
    if not isinstance(node, dict):
        return False
    kind = node.get("type")
    return isinstance(kind, str) and kind.removeprefix("minecraft:") in _COMBINATORS
