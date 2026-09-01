"""Tests for coverage line mapping and report resolution."""

import zipfile
from pathlib import Path

import pytest

from mcward import (
    Coverage,
    CoverageIgnores,
    FunctionCoverage,
    IgnoreRule,
    WardError,
    command_lines,
    ignored_lines,
    json_offsets,
    json_spans,
    resolve_functions,
    resolve_resources,
    scan_functions,
)


class TestCommandLines:
    """Test mapping entry indices to source lines the way the game compiles."""

    def test_skips_blanks_and_comments(self) -> None:
        source = "# setup\n\nsay one\n  # indented comment\nsay two\n"
        assert command_lines(source) == [3, 5]

    def test_macro_lines_count_as_commands(self) -> None:
        assert command_lines("$say $(msg)\nsay plain\n") == [1, 2]

    def test_continuation_folds_into_first_line(self) -> None:
        source = "say one \\\n    two \\\n    three\nsay next\n"
        assert command_lines(source) == [1, 4]

    def test_comment_continuation_folds_like_the_game(self) -> None:
        """A comment ending in a backslash swallows the next line."""
        source = "# comment \\\nsay hidden\nsay real\n"
        assert command_lines(source) == [3]

    def test_unterminated_continuation_stops_mapping(self) -> None:
        assert command_lines("say one\nsay two \\") == [1]


class TestIgnoredLines:
    """Test the ``# @coverage`` markers."""

    def test_ignore_excludes_the_next_command(self) -> None:
        source = "say one\n# @coverage ignore\nsay two\nsay three\n"
        assert ignored_lines(source) == {3}

    def test_ignore_skips_blanks_and_comments(self) -> None:
        source = "# @coverage ignore\n\n# note\nsay one\nsay two\n"
        assert ignored_lines(source) == {4}

    def test_off_excludes_until_on(self) -> None:
        source = "say one\n# @coverage off\nsay two\nsay three\n# @coverage on\nsay four\n"
        assert ignored_lines(source) == {3, 4}

    def test_off_without_on_reaches_the_end(self) -> None:
        source = "# @coverage off\nsay one\nsay two\n"
        assert ignored_lines(source) == {2, 3}

    def test_plain_comments_are_not_markers(self) -> None:
        source = "# coverage off\n# @coverage offline\n# @coverage is great\nsay one\n"
        assert ignored_lines(source) == frozenset()


class TestScanFunctions:
    """Test collecting the function universe from datapack directories."""

    def test_finds_namespaced_functions(self, tmp_path: Path) -> None:
        folder = tmp_path / "pack" / "data" / "demo" / "function" / "nested"
        folder.mkdir(parents=True)
        (folder / "helper.mcfunction").write_text("say hi\n", encoding="utf-8")
        (folder.parent / "main.mcfunction").write_text("say hi\n", encoding="utf-8")

        assert set(scan_functions([tmp_path / "pack"])) == {"demo:main", "demo:nested/helper"}

    def test_ignores_other_registries_and_missing_packs(self, tmp_path: Path) -> None:
        tests = tmp_path / "pack" / "data" / "demo" / "test"
        tests.mkdir(parents=True)
        (tests / "case.mcfunction").write_text("assert entity @s\n", encoding="utf-8")

        assert scan_functions([tmp_path / "pack", tmp_path / "absent"]) == {}


class TestResolveFunctions:
    """Test merging recorded hits with the scanned universe."""

    def make_pack(self, tmp_path: Path, name: str, source: str) -> Path:
        folder = tmp_path / "pack" / "data" / "demo" / "function"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.mcfunction").write_text(source, encoding="utf-8")
        return tmp_path / "pack"

    def test_maps_hits_to_lines(self, tmp_path: Path) -> None:
        source = "# setup\nsay one\n\nexecute if entity @p run say two\n"
        pack = self.make_pack(tmp_path, "main", source)
        coverage = Coverage(functions={"demo:main": FunctionCoverage((3, 3), (3, 0))})

        (report,) = resolve_functions(coverage, [pack])
        assert [line.line for line in report.lines] == [2, 4]
        assert report.covered == 1
        assert [line.line for line in report.guarded] == [4]

    def test_unscheduled_functions_report_zero(self, tmp_path: Path) -> None:
        pack = self.make_pack(tmp_path, "unused", "say never\n")

        (report,) = resolve_functions(Coverage(functions={}), [pack])
        assert not report.touched
        assert (report.covered, len(report.lines)) == (0, 1)

    def test_unmatched_functions_keep_counts_without_lines(self, tmp_path: Path) -> None:
        coverage = Coverage(functions={"demo:zipped": FunctionCoverage((1,), (1,))})

        (report,) = resolve_functions(coverage, [tmp_path])
        assert report.file is None
        assert [line.line for line in report.lines] == [None]
        assert report.covered == 1

    def test_selector_scopes_to_its_namespace(self, tmp_path: Path) -> None:
        """Testing one namespace measures that namespace, not its dependencies."""
        pack = self.make_pack(tmp_path, "main", "say one\n")
        lib = tmp_path / "pack" / "data" / "lib" / "function"
        lib.mkdir(parents=True)
        (lib / "helper.mcfunction").write_text("say hi\n", encoding="utf-8")
        coverage = Coverage(
            functions={
                "demo:main": FunctionCoverage((1,), (1,)),
                "lib:helper": FunctionCoverage((1,), (1,)),
            }
        )

        (report,) = resolve_functions(coverage, [pack], selector="demo:some/test")
        assert report.name == "demo:main"
        # A wildcard namespace scopes by pattern; tag selectors scope nothing
        assert len(resolve_functions(coverage, [pack], selector="d*:*")) == 1
        assert len(resolve_functions(coverage, [pack], selector="#demo:tag")) == 2

    def test_source_mismatch_drops_line_numbers(self, tmp_path: Path) -> None:
        """A recorded shape differing from the file means the source is stale."""
        pack = self.make_pack(tmp_path, "main", "say one\n")
        coverage = Coverage(functions={"demo:main": FunctionCoverage((1, 1), (1, 1))})

        (report,) = resolve_functions(coverage, [pack])
        assert report.file is None
        assert [line.line for line in report.lines] == [None, None]


class TestCoverageIgnores:
    """Test report-time exclusions: markers in functions, ward.toml patterns."""

    def make_pack(self, tmp_path: Path, name: str, source: str) -> Path:
        folder = tmp_path / "pack" / "data" / "demo" / "function"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.mcfunction").write_text(source, encoding="utf-8")
        return tmp_path / "pack"

    def test_markers_drop_lines_from_the_report(self, tmp_path: Path) -> None:
        source = "say one\n# @coverage ignore\nsay two\n"
        pack = self.make_pack(tmp_path, "main", source)
        coverage = Coverage(functions={"demo:main": FunctionCoverage((1, 0), (1, 0))})

        (report,) = resolve_functions(coverage, [pack])
        assert [line.line for line in report.lines] == [1]
        assert (report.covered, report.total) == (1, 1)

    def test_fully_marked_function_drops_out(self, tmp_path: Path) -> None:
        pack = self.make_pack(tmp_path, "debug", "# @coverage off\nsay dump\n")
        coverage = Coverage(functions={"demo:debug": FunctionCoverage((0,), (0,))})

        assert resolve_functions(coverage, [pack]) == []

    def test_element_globs_drop_functions_and_resources(self, tmp_path: Path) -> None:
        folder = tmp_path / "pack" / "data" / "demo" / "function" / "debug"
        folder.mkdir(parents=True)
        (folder / "dump.mcfunction").write_text("say dump\n", encoding="utf-8")
        pack = tmp_path / "pack"
        coverage = Coverage(
            functions={"demo:debug/dump": FunctionCoverage((0,), (0,))},
            conditions={"minecraft:predicate": {"demo:debug/gate": {"": (0, 0)}}},
        )
        ignores = CoverageIgnores((IgnoreRule("demo:debug/*"),))

        assert resolve_functions(coverage, [pack], ignores=ignores) == []
        assert resolve_resources(coverage, [pack], ignores=ignores) == []

    def test_node_patterns_drop_paths(self, tmp_path: Path) -> None:
        coverage = Coverage(
            functions={},
            runs={
                "minecraft:loot_table": {"demo:box": {"": (1, 1), "pools[0].entries[1]": (0, 0)}}
            },
        )
        ignores = CoverageIgnores((IgnoreRule("demo:box", nodes=("pools[*].entries[1]",)),))

        (report,) = resolve_resources(coverage, [tmp_path], ignores=ignores)
        assert [run.path for run in report.runs] == [""]

    def test_element_with_only_ignored_nodes_drops_out(self, tmp_path: Path) -> None:
        coverage = Coverage(
            functions={},
            conditions={"minecraft:predicate": {"demo:gate": {"term": (0, 0)}}},
        )
        ignores = CoverageIgnores((IgnoreRule("demo:*", nodes=("*",)),))

        assert resolve_resources(coverage, [tmp_path], ignores=ignores) == []

    def test_kind_pins_a_rule_to_one_registry(self, tmp_path: Path) -> None:
        """Ids are not unique across registries: a predicate and a loot table
        can share one, so a rule can name the kind it means."""
        coverage = Coverage(
            functions={},
            conditions={
                "minecraft:predicate": {"demo:chest": {"": (0, 0)}},
                "minecraft:loot_table": {"demo:chest": {"": (0, 0)}},
            },
        )
        ignores = CoverageIgnores((IgnoreRule("demo:chest", kind="predicate"),))

        (report,) = resolve_resources(coverage, [tmp_path], ignores=ignores)
        assert report.kind == "loot_table"

    def test_line_rules_drop_lines_from_a_function(self, tmp_path: Path) -> None:
        folder = tmp_path / "pack" / "data" / "demo" / "function"
        folder.mkdir(parents=True)
        (folder / "fill.mcfunction").write_text("say one\nsay two\n", encoding="utf-8")
        coverage = Coverage(functions={"demo:fill": FunctionCoverage((1, 0), (1, 0))})
        ignores = CoverageIgnores((IgnoreRule("demo:fill", kind="function", lines=(2,)),))

        (report,) = resolve_functions(coverage, [tmp_path / "pack"], ignores=ignores)
        assert [line.line for line in report.lines] == [1]

    def test_load_reads_ward_toml(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text(
            "[coverage]\nignore = [\n"
            '  "demo:debug/*",\n'
            '  { kind = "loot_table", id = "demo:box", nodes = ["pools[0]"] },\n'
            '  { kind = "function", id = "demo:fill", lines = [5, 6] },\n'
            "]\n",
            encoding="utf-8",
        )

        ignores = CoverageIgnores.load(tmp_path)
        assert ignores.element("function", "demo:debug/dump")
        assert not ignores.element("function", "demo:main")
        assert ignores.node("loot_table", "demo:box", "pools[0]")
        assert not ignores.node("predicate", "demo:box", "pools[0]")
        assert not ignores.node("loot_table", "demo:box", "pools[1]")
        assert ignores.lines("demo:fill") == {5, 6}

    def test_load_without_file_is_empty(self, tmp_path: Path) -> None:
        assert CoverageIgnores.load(tmp_path) == CoverageIgnores()

    def test_load_rejects_bad_shapes(self, tmp_path: Path) -> None:
        (tmp_path / "ward.toml").write_text("[coverage]\nignore = 1\n", encoding="utf-8")
        with pytest.raises(WardError):
            CoverageIgnores.load(tmp_path)


class TestJsonSpans:
    """Test locating JSON objects by the paths the mod records."""

    def test_nested_objects_and_arrays(self) -> None:
        text = '{\n  "terms": [\n    {\n      "a": 1\n    },\n    {"b": 2}\n  ]\n}\n'
        assert json_spans(text) == {"": (1, 8), "terms[0]": (3, 5), "terms[1]": (6, 6)}

    def test_minified_document_spans_one_line(self) -> None:
        spans = json_spans('{"type":"any_of","terms":[{"type":"inverted","term":{"x":true}}]}')
        assert spans == {"": (1, 1), "terms[0]": (1, 1), "terms[0].term": (1, 1)}

    def test_escaped_keys_match_decoded_form(self) -> None:
        assert json_spans('{"a\\"b": {}}') == {"": (1, 1), 'a"b': (1, 1)}

    def test_strings_and_numbers_are_skipped(self) -> None:
        text = '{"s": "no } brace", "n": -1.5e3, "b": false}'
        assert json_spans(text) == {"": (1, 1)}

    def test_truncated_document_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            json_spans('{"open": [1, 2')

    def test_offsets_address_exact_characters(self) -> None:
        text = '{"terms": [{"a": 1}, {"b": 2}]}'
        assert json_offsets(text) == {
            "": (0, 31),
            "terms[0]": (11, 19),
            "terms[1]": (21, 29),
        }


class TestResolveResources:
    """Test locating recorded conditions in the packs' JSON sources."""

    def make_pack(self, tmp_path: Path, kind: str, name: str, text: str) -> Path:
        folder = tmp_path / "pack" / "data" / "demo" / kind
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.json").write_text(text, encoding="utf-8")
        return tmp_path / "pack"

    def test_maps_nodes_to_spans(self, tmp_path: Path) -> None:
        text = '{\n  "type": "inverted",\n  "term": {\n    "type": "value_check"\n  }\n}\n'
        pack = self.make_pack(tmp_path, "predicate", "gate", text)
        coverage = Coverage(
            functions={},
            conditions={"minecraft:predicate": {"demo:gate": {"": (2, 1), "term": (0, 3)}}},
        )

        (report,) = resolve_resources(coverage, [pack])
        assert (report.name, report.kind) == ("demo:gate", "predicate")
        assert report.file is not None
        assert [(n.path, n.lines, n.passed, n.failed) for n in report.nodes] == [
            ("", (1, 6), 2, 1),
            ("term", (3, 5), 0, 3),
        ]
        # The inverted root is a combinator, so only its term counts as a
        # branch — evaluated is covered, whichever way it went
        assert [node.combinator for node in report.nodes] == [True, False]
        assert (report.covered, report.total) == (1, 1)

    def test_evaluated_and_unevaluated_nodes(self, tmp_path: Path) -> None:
        pack = self.make_pack(tmp_path, "predicate", "gate", "{}")
        coverage = Coverage(
            functions={},
            conditions={"minecraft:predicate": {"demo:gate": {"": (3, 0), "term": (0, 0)}}},
        )

        (report,) = resolve_resources(coverage, [pack])
        root, term = report.nodes
        assert root.evaluated and not term.evaluated
        assert (report.covered, report.total) == (1, 2)

    def test_unmatched_elements_keep_counts_without_spans(self, tmp_path: Path) -> None:
        coverage = Coverage(
            functions={},
            conditions={"minecraft:loot_table": {"demo:zipped": {"pools[0]": (1, 0)}}},
        )

        (report,) = resolve_resources(coverage, [tmp_path])
        assert report.file is None
        assert report.nodes[0].lines is None
        assert report.nodes[0].passed == 1

    def test_selector_scopes_resources_to_its_namespace(self, tmp_path: Path) -> None:
        pack = self.make_pack(tmp_path, "predicate", "gate", "{}")
        coverage = Coverage(
            functions={},
            conditions={
                "minecraft:predicate": {"demo:gate": {"": (1, 1)}, "lib:other": {"": (1, 1)}}
            },
        )

        (report,) = resolve_resources(coverage, [pack], selector="demo:*")
        assert report.name == "demo:gate"

    def test_reference_only_files_count_their_combinators(self, tmp_path: Path) -> None:
        """A predicate whose terms are all references has nothing else to count."""
        text = '{"type": "any_of", "terms": ["demo:a", "demo:b"]}'
        pack = self.make_pack(tmp_path, "predicate", "combo", text)
        coverage = Coverage(
            functions={},
            conditions={"minecraft:predicate": {"demo:combo": {"": (1, 1)}}},
        )

        (report,) = resolve_resources(coverage, [pack])
        assert report.nodes[0].combinator
        assert (report.covered, report.total) == (1, 1)

    def test_runs_merge_into_the_element_report(self, tmp_path: Path) -> None:
        text = (
            '{\n  "pools": [\n    {\n      "entries": [\n        {\n'
            '          "type": "item"\n        }\n      ]\n    }\n  ]\n}\n'
        )
        pack = self.make_pack(tmp_path, "loot_table", "box", text)
        coverage = Coverage(
            functions={},
            runs={"minecraft:loot_table": {"demo:box": {"pools[0].entries[0]": (2, 0)}}},
        )

        (report,) = resolve_resources(coverage, [pack])
        (run,) = report.runs
        assert (run.path, run.lines, run.reached, run.ran) == ("pools[0].entries[0]", (5, 7), 2, 0)
        assert run.blocked
        # Reached but never ran: the file was touched yet nothing is covered
        assert (report.covered, report.total) == (0, 1)
        assert report.touched

    def test_foreign_registries_use_namespaced_folders(self, tmp_path: Path) -> None:
        pack = self.make_pack(tmp_path, "mod/rule", "extra", "{}")
        coverage = Coverage(
            functions={},
            conditions={"mod:rule": {"demo:extra": {"": (1, 1)}}},
        )

        (report,) = resolve_resources(coverage, [pack])
        assert report.kind == "mod/rule"
        assert report.file is not None


class TestZippedPacks:
    """Test resolving sources inside zipped datapacks."""

    def make_zip(self, tmp_path: Path) -> Path:
        pack = tmp_path / "pack.zip"
        with zipfile.ZipFile(pack, "w") as archive:
            archive.writestr("pack.mcmeta", "{}")
            archive.writestr(
                "data/demo/function/nested/main.mcfunction", "# top\nsay one\nsay two\n"
            )
            archive.writestr(
                "data/demo/predicate/gate.json",
                '{\n  "type": "inverted",\n  "term": {\n    "type": "value_check"\n  }\n}\n',
            )
        return pack

    def test_functions_resolve_from_zip(self, tmp_path: Path) -> None:
        pack = self.make_zip(tmp_path)
        coverage = Coverage(functions={"demo:nested/main": FunctionCoverage((1, 1), (1, 0))})

        (report,) = resolve_functions(coverage, [pack])
        assert report.file is not None and report.file.member is not None
        assert [line.line for line in report.lines] == [2, 3]

    def test_resources_resolve_from_zip(self, tmp_path: Path) -> None:
        pack = self.make_zip(tmp_path)
        coverage = Coverage(
            functions={},
            conditions={"minecraft:predicate": {"demo:gate": {"": (2, 1)}}},
        )

        (report,) = resolve_resources(coverage, [pack])
        assert report.file is not None and report.file.member is not None
        assert report.nodes[0].lines == (1, 6)

    def test_rebuilt_zip_is_read_again(self, tmp_path: Path) -> None:
        """The archive cache must not serve a pack that was rebuilt at the same path."""
        pack = self.make_zip(tmp_path)
        assert [line.line for line in self._lines(pack)] == [2, 3]

        with zipfile.ZipFile(pack, "w") as archive:
            archive.writestr("data/demo/function/nested/main.mcfunction", "say one\nsay two\n")
        assert [line.line for line in self._lines(pack)] == [1, 2]

    def _lines(self, pack: Path):
        coverage = Coverage(functions={"demo:nested/main": FunctionCoverage((1, 1), (1, 0))})
        (report,) = resolve_functions(coverage, [pack])
        return report.lines
