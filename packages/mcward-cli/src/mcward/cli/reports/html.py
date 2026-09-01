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
    json_offsets,
)

_STYLE = """
/* The OS preference picks the scheme; the toggle pins one on the root */
:root { color-scheme: light dark; }
:root[data-theme="light"] { color-scheme: light; }
:root[data-theme="dark"] { color-scheme: dark; }
:root {
  --bg: light-dark(#fff, #0d1117);
  --fg: light-dark(#222, #e6edf3);
  --muted: light-dark(#888, #8b949e);
  --faint: light-dark(#bbb, #6e7681);
  --border: light-dark(#e5e5e5, #30363d);
  --rule: light-dark(#f2f2f2, #21262d);
  --chip: light-dark(#f0f0f0, #21262d);
  --green: light-dark(#008608, #44c35e);
  --red: light-dark(#be000d, #f85149);
  --yellow: light-dark(#9a6700, #d29922);
  --hit: light-dark(#ddf0dcbb, #1f4129bb);
  --guard: light-dark(#fff8debb, #614a24bb);
  --miss: light-dark(#ffebe9bb, #4c2327bb);
  --hit-edge: light-dark(#00860880, #44c35e80);
  --guard-edge: light-dark(#d8a20080, #d2992280);
  --miss-edge: light-dark(#be000d80, #f8514980);
  --track: light-dark(#e9e5e5, #30363d);
  --fill: light-dark(#1a7f37, #238636);
  --kw: light-dark(#0550ae, #79c0ff);
  --str: light-dark(#0a3069, #a5d6ff);
  --sel: light-dark(#8250df, #d2a8ff);
  --num: light-dark(#953800, #ffa657);
  --mac: light-dark(#cf222e, #ff7b72);
  --cm: light-dark(#6e7781, #8b949e);
}

html { background: var(--bg); }
body { font: 14px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 60rem;
       padding: 0 1rem; color: var(--fg); }
h1 { font-size: 1.3rem; }
h1 em { color: var(--muted); font-style: normal; font-weight: normal; }
#theme { float: right; padding: .35rem; line-height: 0; border: 1px solid var(--border);
         border-radius: .4rem; background: var(--chip); color: var(--muted); cursor: pointer; }
#theme:hover { color: var(--fg); }
#theme svg[hidden] { display: none; }
.counts span { margin-right: 1rem; }
.passed { color: var(--green); } .failed { color: var(--red); } .skipped { color: var(--yellow); }
.errors li { margin: .3rem 0; } .errors .message { color: var(--red); }
input { margin: 1rem 0 .5rem; padding: .4rem; width: 20rem; }
.legend { color: var(--muted); font-size: .85rem; margin: .5rem 0 1rem; }
.legend span { padding: .1rem .65rem; margin-right: .5rem; color: var(--fg); }
/* A colored edge tells the tints apart even where they look alike */
.hit { background: var(--hit); box-shadow: inset 3px 0 var(--hit-edge); }
.guard { background: var(--guard); box-shadow: inset 3px 0 var(--guard-edge); }
.miss { background: var(--miss); box-shadow: inset 3px 0 var(--miss-edge); }

summary { cursor: pointer; list-style: none; }
summary::-webkit-details-marker { display: none; }
.group { border: 1px solid var(--border); border-radius: 6px; margin: .5rem 0; }
.group > summary { display: grid; grid-template-columns: 1fr 8rem 3fr 3.5rem; gap: 1rem;
                   align-items: center; padding: .5rem .75rem; }
.group > summary b { font-family: monospace; }
.group > summary b::before { content: "\\25B8  "; color: var(--muted); }
.group[open] > summary b::before { content: "\\25BE  "; }
.group[open] > summary { border-bottom: 1px solid var(--border); }
.bar { height: .5rem; border-radius: .25rem; background: var(--track); overflow: hidden; }
.bar span { display: block; height: 100%; background: var(--fill); }
div.fn, .fn > summary { display: grid; grid-template-columns: 1fr 6rem 3.5rem; gap: 1rem;
                        padding: .25rem .75rem; font: 13px/1.5 ui-monospace, monospace; }
.fn { border-top: 1px solid var(--rule); }
.fn em { font-style: normal; color: var(--muted); text-align: right; }
.fn em + span { text-align: right; }
.fn.zero .name { color: var(--red); }
.fn.part .name { color: var(--yellow); }
.fn.full .name { color: var(--muted); }
.fn > summary:hover .name { text-decoration: underline; }
/* inline-block keeps the hover underline off the badge */
.badge { display: inline-block; margin-left: .6rem; padding: 0 .35rem; border-radius: .5rem;
         background: var(--chip); color: var(--muted); font-weight: normal; font-size: .85em; }
.group > summary em { font-style: normal; color: var(--muted); text-align: right; }
.group > summary em + span { text-align: right; }

pre { font: 12.5px/1.45 ui-monospace, monospace; margin: 0; padding: .25rem 0;
      overflow-x: auto; counter-reset: line; }
pre span { display: block; padding: 0 .5rem; counter-increment: line; }
pre span::before { content: counter(line); display: inline-block; width: 4ch;
                   margin-right: 1.5ch; color: var(--faint); text-align: right; }
::highlight(hit) { background-color: var(--hit); }
::highlight(guard) { background-color: var(--guard); }
::highlight(miss) { background-color: var(--miss); }
::highlight(kw) { color: var(--kw); }
::highlight(key) { color: var(--kw); }
::highlight(str) { color: var(--str); }
::highlight(sel) { color: var(--sel); }
::highlight(num) { color: var(--num); }
::highlight(mac) { color: var(--mac); }
::highlight(cm) { color: var(--cm); }
"""

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

_SCRIPT = """
const theme = document.getElementById('theme');
const prefersDark = matchMedia('(prefers-color-scheme: dark)');
const isDark = () => {
  const pinned = document.documentElement.dataset.theme;
  return pinned ? pinned === 'dark' : prefersDark.matches;
};
const relabel = () => {
  const dark = isDark();
  theme.title = dark ? 'Switch to light mode' : 'Switch to dark mode';
  theme.querySelector('.sun').toggleAttribute('hidden', !dark);
  theme.querySelector('.moon').toggleAttribute('hidden', dark);
};
theme.addEventListener('click', () => {
  document.documentElement.dataset.theme = isDark() ? 'light' : 'dark';
  relabel();
});
prefersDark.addEventListener('change', relabel);
relabel();

const filter = document.getElementById('filter');
filter.addEventListener('input', () => {
  const query = filter.value.toLowerCase();
  for (const fn of document.querySelectorAll('.fn')) {
    fn.hidden = !fn.dataset.name.includes(query);
  }
  for (const group of document.querySelectorAll('.group')) {
    group.hidden = !group.querySelector('.fn:not([hidden])');
    if (query) group.open = !group.hidden;
  }
});

function reveal() {
  const target = location.hash && document.querySelector(location.hash);
  if (target && target.classList.contains('fn')) {
    target.closest('.group').open = true;
    target.open = true;
    target.scrollIntoView();
  }
}
addEventListener('hashchange', reveal);
reveal();

// Syntax colors through the CSS custom highlight API: ranges over the existing
// text nodes, no extra markup. Sources are tokenized when first opened.
if (CSS.highlights) {
  const commandRules = [
    ['cm', /^\\s*#.*/g],
    ['sel', /@[a-z]+(?:\\[[^\\]]*\\])?/g],
    ['str', /"(?:\\\\.|[^"\\\\])*"|'[^']*'/g],
    ['mac', /\\$\\(\\w+\\)/g],
    ['kw', /(?<=^\\s*\\$?|\\brun\\s)[a-z][a-z_]*/g],
    ['num', /(?<![\\w.-])-?\\d[\\w.]*|[~^]-?[\\d.]*/g],
  ];
  const jsonRules = [
    ['key', /"(?:\\\\.|[^"\\\\])*"(?=\\s*:)|\\b(?:true|false|null)\\b/g],
    ['str', /"(?:\\\\.|[^"\\\\])*"/g],
    ['num', /-?\\d[\\w.]*/g],
  ];
  for (const [name] of [...commandRules, ...jsonRules]) {
    if (!CSS.highlights.has(name)) CSS.highlights.set(name, new Highlight());
  }
  for (const status of ['hit', 'guard', 'miss']) CSS.highlights.set(status, new Highlight());

  // Coverage tints for JSON sources: the pre carries non-overlapping character
  // segments, so a condition is marked exactly, even inside a minified line
  function paint(pre) {
    const lines = [...pre.children];
    let offset = 0;
    const starts = lines.map(line => {
      const start = offset;
      offset += (line.firstChild ? line.firstChild.data.length : 0) + 1;
      return start;
    });
    const locate = target => {
      let index = starts.length - 1;
      while (index > 0 && starts[index] > target) index--;
      const length = lines[index].firstChild ? lines[index].firstChild.data.length : 0;
      return [lines[index], Math.min(target - starts[index], length)];
    };
    for (const [start, end, status] of JSON.parse(pre.dataset.marks || '[]')) {
      const range = new Range();
      const [startLine, startColumn] = locate(start);
      const [endLine, endColumn] = locate(end);
      if (startLine.firstChild) range.setStart(startLine.firstChild, startColumn);
      else range.setStart(startLine, 0);
      if (endLine.firstChild) range.setEnd(endLine.firstChild, endColumn);
      else range.setEnd(endLine, 0);
      CSS.highlights.get(status).add(range);
    }
  }

  function tokenize(pre) {
    const rules = pre.classList.contains('json') ? jsonRules : commandRules;
    let continued = false;
    for (const line of pre.children) {
      const node = line.firstChild;
      const continuation = continued;
      continued = node ? /\\\\\\s*$/.test(node.data) : false;
      if (!node) continue;
      const claimed = [];
      for (const [name, rule] of rules) {
        for (const match of node.data.matchAll(rule)) {
          const [start, end] = [match.index, match.index + match[0].length];
          // A continuation line starts mid-command: its first word is no
          // keyword, and a leading # is no comment
          if (continuation && name === 'cm') continue;
          if (continuation && name === 'kw' && !/\\brun\\s$/.test(node.data.slice(0, start))) {
            continue;
          }
          if (claimed.some(([s, e]) => start < e && end > s)) continue;
          claimed.push([start, end]);
          const range = new Range();
          range.setStart(node, start);
          range.setEnd(node, end);
          CSS.highlights.get(name).add(range);
        }
      }
    }
  }

  for (const fn of document.querySelectorAll('details.fn')) {
    fn.addEventListener('toggle', () => {
      if (fn.open && !fn.dataset.lit) {
        fn.dataset.lit = '1';
        const pre = fn.querySelector('pre');
        tokenize(pre);
        if (pre.dataset.marks) paint(pre);
      }
    });
  }
}
"""


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
<style>{_STYLE}</style>
</head>
<body>
{_header(session, version, coverage)}
<input id="filter" type="search" placeholder="Filter resources…">
<p class="legend"><span class="hit">covered</span><span class="guard">guarded: fork or
condition never passed</span><span class="miss">never ran</span></p>
{"\n".join(sections)}
<script>{_SCRIPT}</script>
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
    try:
        offsets = json_offsets(source)
    except ValueError:
        return None

    # Conditions are marked as character ranges through the highlight API, so
    # the tints land on the exact chunk even inside minified one-line files
    marks = json.dumps(_mark_segments(resource, offsets), separators=(",", ":"))
    rows = "".join(f"<span>{escape(content)}</span>" for content in source.splitlines())
    return f'<pre class="json" data-marks="{escape(marks)}">{rows}</pre>'


def _mark_segments(
    resource: ResourceReport,
    offsets: dict[str, tuple[int, int]],
) -> list[tuple[int, int, str]]:
    """Non-overlapping [start, end, status) character segments."""
    statuses = [(node.path, "hit" if node.evaluated else "miss") for node in resource.nodes]
    statuses += [
        (run.path, "hit" if run.ran else ("guard" if run.reached else "miss"))
        for run in resource.runs
    ]
    spanned = [(span, status) for path, status in statuses if (span := offsets.get(path))]
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
