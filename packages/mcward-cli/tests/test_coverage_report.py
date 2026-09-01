"""Tests for the coverage summary rendering."""

from pathlib import Path

from mcward import ResolvedCoverage, Version, resolve_coverage
from mcward._protocol import Coverage, FunctionCoverage
from mcward._runner import TestSession as Session
from mcward.cli.reporters.coverage import render_coverage

V1 = Version.parse("26.1.2")
V2 = Version.parse("26.1.1")


def write_function(pack: Path, name: str, source: str, namespace: str = "demo") -> None:
    file = pack / "data" / namespace / "function" / f"{name}.mcfunction"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(source, encoding="utf-8")


def write_predicate(pack: Path, name: str, text: str, namespace: str = "demo") -> None:
    file = pack / "data" / namespace / "predicate" / f"{name}.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")


def resolved(session: Session, pack: Path) -> dict[Version, ResolvedCoverage]:
    return {v: resolve_coverage(coverage, [pack]) for v, coverage in session.coverage.items()}


def rendered_lines(coverage: Coverage, pack: Path, verbose: bool = False) -> list[str]:
    session = Session([V1])
    session._dispatch(V1, coverage)
    return render_coverage(resolved(session, pack), verbose).plain.splitlines()


class TestRenderCoverage:
    """Test the compact coverage summary."""

    def test_default_output_is_the_dashboard(self, tmp_path: Path) -> None:
        """The console gets totals and rollups; per-function rows are verbose-only."""
        write_function(tmp_path, "full", "say one\n")
        write_function(tmp_path, "partial", "say one\nsay two\nsay three\nsay four\n")
        write_function(tmp_path, "quiet", "say hi\n")
        coverage = Coverage(
            functions={
                "demo:full": FunctionCoverage((1,), (1,)),
                "demo:partial": FunctionCoverage((1, 1, 0, 0), (1, 0, 0, 0)),
            }
        )

        lines = rendered_lines(coverage, tmp_path)
        assert lines[0] == "Coverage: 33.3% (2/6, 2/3 files)"
        assert not any("demo:" in line for line in lines)

    def test_verbose_lists_gaps_and_uncalled(self, tmp_path: Path) -> None:
        write_function(tmp_path, "partial", "say one\nsay two\nsay three\nsay four\n")
        write_function(tmp_path, "quiet", "say hi\n")
        coverage = Coverage(
            functions={"demo:partial": FunctionCoverage((1, 1, 0, 0), (1, 0, 0, 0))}
        )

        lines = rendered_lines(coverage, tmp_path, verbose=True)
        assert any("~ demo:partial 1/4  missing 3-4; guarded 2" in line for line in lines)
        assert any("✗ demo:quiet 0/1" in line for line in lines)

    def test_verbose_gap_rows_are_worst_first(self, tmp_path: Path) -> None:
        functions = {}
        for i in range(3):
            # Function i has i+1 missing commands out of i+2, so high i sorts first
            write_function(tmp_path, f"f{i}", "say hi\n" * (i + 2))
            functions[f"demo:f{i}"] = FunctionCoverage((1,) + (0,) * (i + 1), (1,) + (0,) * (i + 1))

        lines = rendered_lines(Coverage(functions=functions), tmp_path, verbose=True)
        gap_rows = [line for line in lines if "~ demo:" in line]
        assert [row.split()[1] for row in gap_rows] == ["demo:f2", "demo:f1", "demo:f0"]

    def test_namespace_rollup_when_several(self, tmp_path: Path) -> None:
        write_function(tmp_path, "one", "say hi\n", namespace="alpha")
        write_function(tmp_path, "two", "say hi\n", namespace="beta")
        coverage = Coverage(functions={"alpha:one": FunctionCoverage((1,), (1,))})

        lines = rendered_lines(coverage, tmp_path)
        assert any(line.startswith("  alpha") and "100.0%  1/1" in line for line in lines)
        assert any(line.startswith("  beta") and "0.0%  0/1" in line for line in lines)

    def test_single_namespace_groups_by_resource_type(self, tmp_path: Path) -> None:
        write_function(tmp_path, "chest/fill", "say hi\n")
        write_function(tmp_path, "math/pow", "say hi\n")
        write_predicate(tmp_path, "gate", '{"type": "any_of"}')
        coverage = Coverage(
            functions={"demo:chest/fill": FunctionCoverage((1,), (1,))},
            conditions={"minecraft:predicate": {"demo:gate": {"": (1, 1)}}},
        )

        lines = rendered_lines(coverage, tmp_path)
        assert any(line.startswith("  function") and " 50.0%  1/2" in line for line in lines)
        assert any(line.startswith("  predicate") and "100.0%  1/1" in line for line in lines)

    def test_conditions_join_the_namespace_rollup(self, tmp_path: Path) -> None:
        write_function(tmp_path, "one", "say hi\n", namespace="alpha")
        write_function(tmp_path, "two", "say hi\n", namespace="beta")
        write_predicate(tmp_path, "gate", '{"type": "any_of"}', namespace="alpha")
        coverage = Coverage(
            functions={"alpha:one": FunctionCoverage((1,), (1,))},
            conditions={"minecraft:predicate": {"alpha:gate": {"": (1, 1)}}},
        )

        lines = rendered_lines(coverage, tmp_path)
        assert lines[0] == "Coverage: 66.7% (2/3, 2/3 files)"
        # One row per namespace: combined share, merged counts, files
        assert "  alpha  100.0%  2/2  2/2 files" in lines
        assert "  beta     0.0%  0/1  0/1 files" in lines

    def test_unreached_files_list_counts_without_paths(self, tmp_path: Path) -> None:
        write_predicate(tmp_path, "gate", "{}")
        coverage = Coverage(
            functions={},
            conditions={"minecraft:predicate": {"demo:gate": {"": (0, 0), "term": (0, 0)}}},
        )

        lines = rendered_lines(coverage, tmp_path, verbose=True)
        row = next(line for line in lines if "demo:gate" in line)
        assert row.strip() == "✗ demo:gate (predicate) 0/2"

    def test_verbose_lists_blocked_and_unreached_runs(self, tmp_path: Path) -> None:
        file = tmp_path / "data" / "demo" / "loot_table" / "box.json"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('{"pools": []}', encoding="utf-8")
        coverage = Coverage(
            functions={},
            runs={
                "minecraft:loot_table": {
                    "demo:box": {"pools[0].entries[0]": (2, 0), "pools[0].entries[1]": (0, 0)}
                }
            },
        )

        lines = rendered_lines(coverage, tmp_path, verbose=True)
        row = next(line for line in lines if "demo:box" in line)
        assert "~ demo:box (loot_table) 0/2" in row
        assert "blocked pools[0].entries[0]; unreached pools[0].entries[1]" in row

    def test_condition_gap_paths_are_capped(self, tmp_path: Path) -> None:
        write_predicate(tmp_path, "gate", "{}")
        nodes: dict[str, tuple[int, int]] = {f"terms[{i}]": (0, 0) for i in range(6)}
        coverage = Coverage(
            functions={},
            conditions={"minecraft:predicate": {"demo:gate": nodes | {"": (1, 0)}}},
        )

        lines = rendered_lines(coverage, tmp_path, verbose=True)
        row = next(line for line in lines if "demo:gate" in line)
        assert "never terms[0], terms[1], terms[2] +3 more" in row
        assert "terms[5]" not in row

    def test_verbose_lists_condition_gaps(self, tmp_path: Path) -> None:
        write_predicate(
            tmp_path,
            "gate",
            '{"type": "any_of", "terms": [{"type": "a"}, {"type": "b"}]}',
        )
        coverage = Coverage(
            functions={},
            conditions={
                "minecraft:predicate": {
                    "demo:gate": {"": (2, 0), "terms[0]": (2, 0), "terms[1]": (0, 0)}
                }
            },
        )

        lines = rendered_lines(coverage, tmp_path, verbose=True)
        row = next(line for line in lines if "demo:gate" in line)
        # The any_of root is a combinator (not a branch); the evaluated term
        # counts as covered even though it only ever passed
        assert "~ demo:gate (predicate) 1/2" in row
        assert "never terms[1]" in row
        assert "terms[0]" not in row and "(root)" not in row

    def test_multi_version_sections_are_labeled(self, tmp_path: Path) -> None:
        write_function(tmp_path, "one", "say hi\n")
        session = Session([V1, V2])
        for version in (V1, V2):
            session._dispatch(version, Coverage(functions={}))

        lines = render_coverage(resolved(session, tmp_path)).plain.splitlines()
        assert "26.1.2" in lines[0]
        assert any("26.1.1" in line for line in lines)
