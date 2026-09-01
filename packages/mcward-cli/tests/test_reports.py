"""Tests for the report files: coverage-report parsing, JUnit XML and HTML."""

from pathlib import Path
from xml.etree.ElementTree import Element, fromstring

import pytest
import rich_click as click

from mcward import ResolvedCoverage, Version, resolve_coverage
from mcward._protocol import (
    BatchStarted,
    Coverage,
    FunctionCoverage,
    StreamError,
    TestFailed as Failed,
    TestPassed as Passed,
)
from mcward._runner import TestSession as Session
from mcward.cli.reports import (
    parse_coverage_report,
    write_coverage_reports,
    write_junit,
    write_lcov,
)

V1 = Version.parse("26.1.2")
V2 = Version.parse("26.1.1")


def resolved(session: Session, pack: Path) -> dict[Version, ResolvedCoverage]:
    return {v: resolve_coverage(coverage, [pack]) for v, coverage in session.coverage.items()}


def find(element: Element, path: str) -> Element:
    child = element.find(path)
    assert child is not None, path
    return child


def make_session(*versions: Version) -> Session:
    session = Session(versions or (V1,))
    for version in versions or (V1,):
        session._dispatch(version, BatchStarted(environment="default"))
        session._dispatch(version, Passed(name="a:good", time=5))
        session._dispatch(
            version, Failed("a:bad", time=7, error="boom", required=True, line=None, tick=None)
        )
        session._dispatch(
            version, Failed("a:opt", time=9, error="meh", required=False, line=None, tick=None)
        )
    return session


class TestParseCoverageReport:
    """Test the format[:path] option values."""

    def test_bare_formats_use_default_paths(self) -> None:
        assert parse_coverage_report("lcov") == ("lcov", Path("coverage.lcov"))
        assert parse_coverage_report("html") == ("html", Path("coverage.html"))

    def test_explicit_path_survives_drive_letters(self) -> None:
        assert parse_coverage_report("html:C:/out/cov.html") == ("html", Path("C:/out/cov.html"))

    def test_unknown_format_is_rejected(self) -> None:
        with pytest.raises(click.BadParameter, match="lcov"):
            parse_coverage_report("cobertura")


class TestWriteJunit:
    """Test the JUnit XML test-result output."""

    def test_one_suite_per_version_with_outcomes(self, tmp_path: Path) -> None:
        out = tmp_path / "results.xml"
        write_junit(make_session(V1, V2), out)

        suites = fromstring(out.read_text(encoding="utf-8"))
        assert [suite.get("name") for suite in suites] == ["26.1.2", "26.1.1"]
        suite = suites[0]
        assert (suite.get("tests"), suite.get("failures"), suite.get("skipped")) == ("3", "1", "1")

        cases = {case.get("name"): case for case in suite}
        assert cases["a:good"].get("classname") == "default"
        assert cases["a:good"].get("time") == "0.005"
        assert find(cases["a:bad"], "failure").get("message") == "boom"
        assert find(cases["a:opt"], "skipped").get("message") == "meh"

    def test_aborted_version_becomes_an_error(self, tmp_path: Path) -> None:
        session = Session([V1])
        session._dispatch(V1, StreamError("server died"))
        out = tmp_path / "results.xml"
        write_junit(session, out)

        (suite,) = fromstring(out.read_text(encoding="utf-8"))
        assert suite.get("errors") == "1"
        assert find(suite, "testcase/error").get("message") == "server died"


class TestWriteCoverageReports:
    """Test the coverage file dispatch."""

    def make_pack(self, tmp_path: Path) -> Path:
        folder = tmp_path / "pack" / "data" / "demo" / "function"
        folder.mkdir(parents=True)
        source = "say start\nexecute if entity @p run say <gated>\nsay end\n"
        (folder / "main.mcfunction").write_text(source, encoding="utf-8")
        return tmp_path / "pack"

    def coverage_session(self, *versions: Version) -> Session:
        session = make_session(*versions)
        for version in versions or (V1,):
            session._dispatch(
                version,
                Coverage(functions={"demo:main": FunctionCoverage((1, 1, 0), (1, 0, 0))}),
            )
        return session

    def test_writes_lcov_and_html(self, tmp_path: Path) -> None:
        pack = self.make_pack(tmp_path)
        specs = [("lcov", tmp_path / "cov.lcov"), ("html", tmp_path / "cov.html")]

        session = self.coverage_session(V1)
        files = write_coverage_reports(session, resolved(session, pack), specs)
        assert files == [tmp_path / "cov.lcov", tmp_path / "cov.html"]

        assert "DA:1,1" in (tmp_path / "cov.lcov").read_text(encoding="utf-8")
        page = (tmp_path / "cov.html").read_text(encoding="utf-8")
        assert "demo:main" in page
        # Source lines are escaped, tinted by outcome, and packed without
        # whitespace (a pre renders anything between them as blank lines)
        assert (
            '<span class="hit">say start</span>'
            '<span class="guard">execute if entity @p run say &lt;gated&gt;</span>'
            '<span class="miss">say end</span>'
        ) in page
        # The run summary carries the failing test
        assert "a:bad" in page and "boom" in page

    def test_html_tints_continuation_lines(self, tmp_path: Path) -> None:
        folder = tmp_path / "pack" / "data" / "demo" / "function"
        folder.mkdir(parents=True)
        source = "say one\nfunction demo:next \\\n  {arg: 1}\nsay two\n"
        (folder / "main.mcfunction").write_text(source, encoding="utf-8")

        session = make_session(V1)
        session._dispatch(
            V1, Coverage(functions={"demo:main": FunctionCoverage((1, 1, 0), (1, 0, 0))})
        )
        pack = tmp_path / "pack"
        write_coverage_reports(session, resolved(session, pack), [("html", tmp_path / "cov.html")])

        page = (tmp_path / "cov.html").read_text(encoding="utf-8")
        # The folded command spans two physical lines; both carry its tint
        assert '<span class="guard">function demo:next \\</span>' in page
        assert '<span class="guard">  {arg: 1}</span>' in page
        assert '<span class="miss">say two</span>' in page

    def test_html_groups_by_namespace(self, tmp_path: Path) -> None:
        pack = self.make_pack(tmp_path)
        other = tmp_path / "pack" / "data" / "extra" / "function"
        other.mkdir(parents=True)
        (other / "helper.mcfunction").write_text("say hi\n", encoding="utf-8")

        session = make_session(V1)
        session._dispatch(
            V1,
            Coverage(
                functions={
                    "demo:main": FunctionCoverage((1, 1, 0), (1, 0, 0)),
                    "extra:helper": FunctionCoverage((1,), (1,)),
                }
            ),
        )
        write_coverage_reports(session, resolved(session, pack), [("html", tmp_path / "cov.html")])

        page = (tmp_path / "cov.html").read_text(encoding="utf-8")
        # One collapsed section per namespace; a lone group would open by default
        assert page.count('<details class="group">') == 2
        assert "<b>demo</b>" in page and "<b>extra</b>" in page
        # Namespace groups mix types, so rows carry their kind badge
        assert 'demo:main<b class="badge">function</b>' in page

    def test_html_renders_condition_groups(self, tmp_path: Path) -> None:
        pack = self.make_pack(tmp_path)
        predicate = tmp_path / "pack" / "data" / "demo" / "predicate" / "gate.json"
        predicate.parent.mkdir(parents=True)
        predicate.write_text(
            '{\n  "type": "any_of",\n  "terms": [\n    {\n      "type": "a"\n    }\n  ]\n}\n',
            encoding="utf-8",
        )

        session = make_session(V1)
        session._dispatch(
            V1,
            Coverage(
                functions={"demo:main": FunctionCoverage((1, 1, 0), (1, 0, 0))},
                conditions={"minecraft:predicate": {"demo:gate": {"": (1, 0), "terms[0]": (0, 0)}}},
            ),
        )
        write_coverage_reports(session, resolved(session, pack), [("html", tmp_path / "cov.html")])

        page = (tmp_path / "cov.html").read_text(encoding="utf-8")
        # One namespace: groups are resource types, alphabetical, no badges
        assert "<b>function</b>" in page
        assert "<b>predicate</b>" in page
        assert page.index("<b>function</b>") < page.index("<b>predicate</b>")
        assert 'class="badge"' not in page
        assert "1/3 commands · 1/1 files" in page
        # The any_of root is an uncounted combinator; its unevaluated term is
        # the only branch
        assert "0/1 conditions · 1/1 files" in page
        # Condition tints ride the highlight API as character segments: the
        # evaluated root (hit) is carved around its unevaluated term (miss)
        assert (
            'data-marks="[[0,39,&quot;hit&quot;],[39,64,&quot;miss&quot;],[64,70,&quot;hit&quot;]]"'
        ) in page

    def test_several_versions_suffix_the_files(self, tmp_path: Path) -> None:
        pack = self.make_pack(tmp_path)
        specs = [("lcov", tmp_path / "cov.lcov")]

        session = self.coverage_session(V1, V2)
        files = write_coverage_reports(session, resolved(session, pack), specs)
        assert [file.name for file in files] == ["cov-26.1.2.lcov", "cov-26.1.1.lcov"]


class TestWriteLcov:
    """Test the lcov tracefile output."""

    def test_writes_records_with_relative_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        folder = tmp_path / "pack" / "data" / "demo" / "function"
        folder.mkdir(parents=True)
        (folder / "main.mcfunction").write_text("# top\nsay one\nsay two\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        coverage = Coverage(functions={"demo:main": FunctionCoverage((3, 3), (3, 0))})

        out = tmp_path / "coverage.lcov"
        assert write_lcov(resolve_coverage(coverage, [tmp_path / "pack"]), out) == 1

        assert out.read_text(encoding="utf-8").splitlines() == [
            "SF:pack/data/demo/function/main.mcfunction",
            "DA:2,3",
            "DA:3,0",
            "LF:2",
            "LH:1",
            "end_of_record",
        ]

    def test_functions_without_sources_are_left_out(self, tmp_path: Path) -> None:
        coverage = Coverage(functions={"demo:zipped": FunctionCoverage((1,), (1,))})

        out = tmp_path / "coverage.lcov"
        assert write_lcov(resolve_coverage(coverage, [tmp_path]), out) == 0
        assert out.read_text(encoding="utf-8") == ""

    def test_conditions_become_branch_records(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        folder = tmp_path / "pack" / "data" / "demo" / "predicate"
        folder.mkdir(parents=True)
        text = '{\n  "type": "inverted",\n  "term": {\n    "type": "value_check"\n  }\n}\n'
        (folder / "gate.json").write_text(text, encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        coverage = Coverage(
            functions={},
            conditions={"minecraft:predicate": {"demo:gate": {"": (2, 1), "term": (0, 0)}}},
        )

        out = tmp_path / "coverage.lcov"
        assert write_lcov(resolve_coverage(coverage, [tmp_path / "pack"]), out) == 1

        assert out.read_text(encoding="utf-8").splitlines() == [
            "SF:pack/data/demo/predicate/gate.json",
            "DA:1,3",
            "DA:3,0",
            "BRDA:1,0,0,2",
            "BRDA:1,0,1,1",
            "BRDA:3,1,0,0",
            "BRDA:3,1,1,0",
            "LF:2",
            "LH:1",
            "end_of_record",
        ]
