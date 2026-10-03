"""Self-contained HTML coverage report: run summary, grouped index, tinted sources."""

import json
from collections.abc import Iterator, Sequence
from html import escape
from itertools import count
from pathlib import Path

from mcward import (
    CoverageReport,
    CoverageTotals,
    FunctionReport,
    ResolvedCoverage,
    ResourceReport,
    TestSession,
    TestStatus,
    Version,
    VersionOutcome,
)

_RESOURCES = Path(__file__).parent
_STYLE = (_RESOURCES / "coverage.css").read_text(encoding="utf-8")
_SCRIPT = (_RESOURCES / "coverage.js").read_text(encoding="utf-8")

_ICON = (
    '<svg class="{name}" width="16" height="16" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" {attr}>{shape}</svg>'
)
_THEME_BUTTON = '<button id="theme" type="button">' + (
    _ICON.format(
        name="sun",
        shape='<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4'
        'M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
        attr="hidden",
    )
    + _ICON.format(
        name="moon", shape='<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>', attr=""
    )
    + "</button>"
)


def write_html(
    session: TestSession, version: Version, coverage: ResolvedCoverage, path: Path
) -> None:
    """Render one version's run into a single browsable HTML file."""
    members = coverage.reports
    by_namespace = len({member.namespace for member in members}) > 1
    groups = _grouped(members, by_namespace)
    ids = count()
    sections = [
        _group_section(name, grouped, ids, open=len(groups) == 1, badged=by_namespace)
        for name, grouped in groups
    ]

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ward coverage ({escape(version.name)})</title>
<style>
{_STYLE}</style>
</head>
<body>
{_header(session, version, coverage)}
<input id="filter" type="search" placeholder="Filter resources…">
<p class="legend"><span class="hit">covered</span><span class="guard">guarded: fork or
condition never passed</span><span class="miss">never ran</span></p>
{"\n".join(sections)}
<script>
{_SCRIPT}</script>
</body>
</html>
"""
    path.write_text(page, encoding="utf-8", newline="\n")


def _header(session: TestSession, version: Version, coverage: ResolvedCoverage) -> str:
    functions = CoverageTotals.of(coverage.functions)
    resources = CoverageTotals.of(coverage.resources)
    files = CoverageTotals.of(coverage.reports)
    touched = f"{files.touched / files.files:.1%}" if files.files else "—"

    outcomes = _outcomes(session, version)
    passed = sum(o.status is TestStatus.PASSED for o in outcomes.values())
    skipped = sum(o.status is TestStatus.SKIPPED for o in outcomes.values())
    failed = {name: o for name, o in outcomes.items() if o.status is TestStatus.FAILED}

    counts = [
        f'<span class="passed">{passed} passed</span>',
        f'<span class="failed">{len(failed)} failed</span>' if failed else "",
        f'<span class="skipped">{skipped} skipped</span>' if skipped else "",
        "<span>|</span>",
        f"<span>{_share(functions)} commands ({functions.covered}/{functions.total})</span>",
        f"<span>{_share(resources)} conditions ({resources.covered}/{resources.total})</span>"
        if resources.files
        else "",
        f"<span>{touched} files ({files.touched}/{files.files})</span>",
    ]
    parts = [
        f"<h1>Ward coverage <em>({escape(version.name)})</em>{_THEME_BUTTON}</h1>",
        f'<p class="counts">{"".join(counts)}</p>',
    ]
    if failed:
        items = "".join(
            f"<li><code>{escape(name)}</code> "
            f'<span class="message">{escape(outcome.error)}</span></li>'
            for name, outcome in failed.items()
        )
        parts.append(f'<ul class="errors">{items}</ul>')
    return "\n".join(parts)


def _outcomes(session: TestSession, version: Version) -> dict[str, VersionOutcome]:
    return {
        result.name: outcome
        for batch in session.batches
        for result in batch.results
        if (outcome := result.outcomes.get(version)) is not None
    }


def _grouped(
    members: Sequence[CoverageReport],
    by_namespace: bool,
) -> list[tuple[str, list[CoverageReport]]]:
    """Least-covered first, grouped like the console rollup."""
    groups: dict[str, list[CoverageReport]] = {}
    for member in sorted(members, key=lambda m: (m.ratio, m.name)):
        key = member.namespace if by_namespace else member.kind
        groups.setdefault(key, []).append(member)
    return sorted(groups.items())


def _share(totals: CoverageTotals, digits: int = 1) -> str:
    return f"{totals.ratio:.{digits}%}" if totals.ratio is not None else "—"


def _group_section(
    name: str,
    members: Sequence[CoverageReport],
    ids: Iterator[int],
    open: bool,
    badged: bool,
) -> str:
    functions = CoverageTotals.of(m for m in members if isinstance(m, FunctionReport))
    resources = CoverageTotals.of(m for m in members if isinstance(m, ResourceReport))
    totals = CoverageTotals.of(members)

    parts = []
    if functions.files:
        parts.append(f"{functions.covered}/{functions.total} commands")
    if resources.files:
        parts.append(f"{resources.covered}/{resources.total} conditions")
    parts.append(f"{totals.touched}/{totals.files} files")

    share = _share(totals, digits=0)
    width = round(totals.ratio * 100) if totals.ratio is not None else 100
    rows = "\n".join(_member_row(next(ids), member, badged) for member in members)

    return (
        f'<details class="group"{" open" if open else ""}><summary><b>{escape(name)}</b>'
        f'<span class="bar"><span style="width:{width}%"></span></span>'
        f"<em>{' · '.join(parts)}</em>"
        f"<span>{share}</span></summary>\n{rows}\n</details>"
    )


def _member_row(fid: int, member: CoverageReport, badged: bool) -> str:
    ratio = member.ratio
    style = "full" if ratio == 1 else ("part" if member.touched else "zero")
    badge = f'<b class="badge">{escape(member.kind)}</b>' if badged else ""
    cells = (
        f'<span class="name">{escape(member.name)}{badge}</span>'
        f"<em>{member.covered}/{member.total}</em><span>{ratio:.0%}</span>"
    )
    filterable = f'data-name="{escape(member.name.lower())}"'

    if isinstance(member, FunctionReport):
        source = _source(member)
    elif isinstance(member, ResourceReport):
        source = _resource_source(member)
    else:
        source = None

    if source is None:
        return f'<div class="fn {style}" {filterable}>{cells}</div>'
    return (
        f'<details class="fn {style}" id="f{fid}" {filterable}>'
        f"<summary>{cells}</summary>{source}</details>"
    )


def _source(report: FunctionReport) -> str | None:
    if report.file is None or (source := report.file.read()) is None:
        return None

    contents = source.splitlines()
    styles = [""] * len(contents)
    for line in report.lines:
        if line.line is None:
            continue
        style = "hit" if line.executed else ("guard" if line.reached else "miss")
        # A trailing backslash folds the next line into the command: tint the whole span
        index = line.line - 1
        styles[index] = style
        while index < len(contents) - 1 and contents[index].strip().endswith("\\"):
            index += 1
            styles[index] = style

    rows = [
        f'<span class="{style}">{escape(content)}</span>'
        for style, content in zip(styles, contents, strict=True)
    ]

    # No whitespace between the line spans: a pre would render it as extra blank lines
    return f"<pre>{''.join(rows)}</pre>"


def _resource_source(resource: ResourceReport) -> str | None:
    if resource.file is None or (source := resource.file.read()) is None:
        return None

    # Conditions are marked as character ranges through the highlight API, so
    # the tints land on the exact chunk even inside minified one-line files
    marks = json.dumps(_mark_segments(resource), separators=(",", ":"))
    rows = "".join(f"<span>{escape(content)}</span>" for content in source.splitlines())
    return f'<pre class="json" data-marks="{escape(marks)}">{rows}</pre>'


def _mark_segments(resource: ResourceReport) -> list[tuple[int, int, str]]:
    """Non-overlapping [start, end, status) character segments."""
    statuses = [(node.offsets, "hit" if node.evaluated else "miss") for node in resource.nodes]
    statuses += [
        (run.offsets, "hit" if run.ran else ("guard" if run.reached else "miss"))
        for run in resource.runs
    ]
    spanned = [(span, status) for span, status in statuses if span]
    spanned.sort(key=lambda item: (item[0][0], -item[0][1]))

    segments: list[tuple[int, int, str]] = []
    stack: list[tuple[int, str]] = []
    cursor = 0

    def advance(upto: int) -> None:
        nonlocal cursor
        if stack and cursor < upto:
            segments.append((cursor, upto, stack[-1][1]))
        cursor = max(cursor, upto)

    for (start, end), status in spanned:
        while stack and stack[-1][0] <= start:
            advance(stack[-1][0])
            stack.pop()
        advance(start)
        stack.append((end, status))
    while stack:
        advance(stack[-1][0])
        stack.pop()
    return segments
