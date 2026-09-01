"""Coverage rendering shared by the terminal reporters."""

from collections.abc import Callable, Mapping, Sequence

from rich.text import Text

from mcward import (
    CoverageReport,
    CoverageTotals,
    FunctionReport,
    ResolvedCoverage,
    ResourceReport,
    Version,
)

_GAP_PATHS_SHOWN = 3


def render_coverage(resolved: Mapping[Version, ResolvedCoverage], verbose: bool = False) -> Text:
    """The coverage summary, one section per version that reported it."""
    text = Text()
    for version, coverage in resolved.items():
        reports = coverage.reports
        if len(resolved) > 1:
            text.append(f"{version.name}\n", "magenta")
        _render_summary(text, reports)
        _render_groups(text, reports)
        if verbose:
            _render_gaps(text, coverage.functions)
            _render_uncalled(text, coverage.functions)
            _render_condition_gaps(text, coverage.resources)
    return text


def _render_summary(text: Text, reports: Sequence[CoverageReport]) -> None:
    totals = CoverageTotals.of(reports)
    text.append("Coverage: ", "bold")
    text.append(_share(totals))
    text.append(
        f" ({totals.covered}/{totals.total}, {totals.touched}/{totals.files} files)\n", "dim"
    )


def _render_groups(text: Text, reports: Sequence[CoverageReport]) -> None:
    """One rollup row per group: combined share, covered count, files reached."""
    key = _group_key(reports)
    groups = sorted({key(report) for report in reports})
    if len(groups) < 2:
        return

    rows = []
    for group in groups:
        totals = CoverageTotals.of(report for report in reports if key(report) == group)
        counts = f"{totals.covered}/{totals.total}"
        rows.append((group, _share(totals, 6), counts, f"{totals.touched}/{totals.files} files"))

    name_width = max(len(row[0]) for row in rows)
    count_width = max(len(row[2]) for row in rows)
    for group, share, counts, files in rows:
        text.append(f"  {group:<{name_width}}  {share}")
        text.append(f"  {counts:>{count_width}}", "dim")
        text.append(f"  {files}\n", "dim")


def _share(totals: CoverageTotals, width: int = 0) -> str:
    return f"{totals.ratio:{width}.1%}" if totals.ratio is not None else f"{'—':>{width}}"


def _group_key(reports: Sequence[CoverageReport]) -> Callable[[CoverageReport], str]:
    """Group by namespace, or by resource type when there is only one."""
    if len({report.namespace for report in reports}) > 1:
        return lambda report: report.namespace
    return lambda report: report.kind


def _render_gaps(text: Text, reports: Sequence[FunctionReport]) -> None:
    gaps = [r for r in reports if r.touched and r.covered < r.total]
    gaps.sort(key=lambda r: (r.covered - r.total, r.name))

    for report in gaps:
        text.append("  ~ ", "yellow")
        text.append(report.name)
        text.append(f" {report.covered}/{report.total}", "dim")
        if detail := _describe_gaps(report):
            text.append(f"  {detail}", "dim yellow")
        text.append("\n")


def _render_condition_gaps(text: Text, resources: Sequence[ResourceReport]) -> None:
    """An untouched file gets counts only: paths would drown big generated files."""
    gaps = [r for r in resources if r.covered < r.total]
    gaps.sort(key=lambda r: (r.covered - r.total, r.name))

    for resource in gaps:
        symbol, style = ("~", "yellow") if resource.touched else ("✗", "red")
        text.append(f"  {symbol} ", style)
        text.append(resource.name)
        text.append(f" ({resource.kind})", "dim")
        text.append(f" {resource.covered}/{resource.total}", "dim")
        if resource.touched and (detail := _describe_nodes(resource)):
            text.append(f"  {detail}", "dim yellow")
        text.append("\n")


def _describe_nodes(resource: ResourceReport) -> str:
    groups: dict[str, list[str]] = {"never": [], "blocked": [], "unreached": []}
    for node in resource.counted:
        if not node.evaluated:
            groups["never"].append(node.path)
    for run in resource.runs:
        if run.blocked:
            groups["blocked"].append(run.path)
        elif not run.reached:
            groups["unreached"].append(run.path)
    return "; ".join(f"{label} {_some_paths(paths)}" for label, paths in groups.items() if paths)


def _some_paths(paths: list[str]) -> str:
    shown = ", ".join(path or "(root)" for path in paths[:_GAP_PATHS_SHOWN])
    extra = len(paths) - _GAP_PATHS_SHOWN
    return f"{shown} +{extra} more" if extra > 0 else shown


def _render_uncalled(text: Text, reports: Sequence[FunctionReport]) -> None:
    for report in reports:
        if report.lines and not report.touched:
            text.append("  ✗ ", "red")
            text.append(report.name)
            text.append(f" 0/{report.total}\n", "dim")


def _describe_gaps(report: FunctionReport) -> str:
    if report.file is None:
        return ""
    unreached = [line.line for line in report.lines if not line.reached and line.line is not None]
    guarded = [line.line for line in report.guarded if line.line is not None]
    parts = []
    if unreached:
        parts.append(f"missing {_ranges(unreached)}")
    if guarded:
        parts.append(f"guarded {_ranges(guarded)}")
    return "; ".join(parts)


def _ranges(lines: Sequence[int]) -> str:
    """Consecutive line numbers folded into ranges: 5-6, 10."""

    def fold(start: int, end: int) -> str:
        return str(start) if start == end else f"{start}-{end}"

    parts: list[str] = []
    start = previous = lines[0]
    for line in lines[1:]:
        if line != previous + 1:
            parts.append(fold(start, previous))
            start = line
        previous = line
    parts.append(fold(start, previous))
    return ", ".join(parts)
