"""Lcov tracefile coverage report, for editor gutters and CI coverage services."""

from pathlib import Path

from mcward import ResolvedCoverage, SourceFile


def write_lcov(coverage: ResolvedCoverage, path: Path) -> int:
    """Write an lcov tracefile with per-line hit counts, returning the file count."""
    records = []
    written = 0
    for report in coverage.functions:
        if report.file is None or not report.lines:
            continue
        written += 1
        records.append(f"SF:{_lcov_path(report.file)}")
        records.extend(f"DA:{line.line},{line.executed}" for line in report.lines)
        records.append(f"LF:{len(report.lines)}")
        records.append(f"LH:{report.covered}")
        records.append("end_of_record")

    for resource in coverage.resources:
        nodes = [(node.lines[0], node) for node in resource.nodes if node.lines is not None]
        runs = [(run.lines[0], run) for run in resource.runs if run.lines is not None]
        if resource.file is None or not (nodes or runs):
            continue
        written += 1
        records.append(f"SF:{_lcov_path(resource.file)}")
        hits: dict[int, int] = {}
        for line, node in nodes:
            hits[line] = hits.get(line, 0) + node.passed + node.failed
        for line, run in runs:
            hits[line] = hits.get(line, 0) + run.ran
        records.extend(f"DA:{line},{count}" for line, count in sorted(hits.items()))
        for block, (line, node) in enumerate(nodes):
            records.append(f"BRDA:{line},{block},0,{node.passed}")
            records.append(f"BRDA:{line},{block},1,{node.failed}")
        records.append(f"LF:{len(hits)}")
        records.append(f"LH:{sum(count > 0 for count in hits.values())}")
        records.append("end_of_record")

    content = "\n".join(records) + "\n" if records else ""
    path.write_text(content, encoding="utf-8", newline="\n")
    return written


def _lcov_path(file: SourceFile) -> str:
    """The tracefile path: workspace-relative when possible, absolute otherwise.

    A member of a zipped pack appends its archive path for display; tools
    cannot open it as a file.
    """
    resolved = file.path.resolve()
    if resolved.is_relative_to(cwd := Path.cwd()):
        resolved = resolved.relative_to(cwd)
    return resolved.as_posix() if file.member is None else f"{resolved.as_posix()}/{file.member}"
