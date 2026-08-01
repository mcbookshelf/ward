"""Tests for the Rich rendering of a test run."""

from mcward import Version

# Aliased so pytest does not try to collect the production class as tests
from mcward._protocol import (
    BatchStarted,
    Diagnostic,
    StreamError,
    TestFailed as Failed,
    TestPassed as Passed,
    TestsFinished as Finished,
    TestsStarted as Started,
)
from mcward._runner import TestSession as Session
from mcward.cli.reporters.live import render_header, render_session

V1 = Version.parse("26.1.2")
V2 = Version.parse("26.1.1")


def rendered_lines(session: Session) -> list[str]:
    """Render a session to plain text lines."""
    return render_session(session).plain.splitlines()


def start_run(session: Session, *versions: Version, batch: str = "default") -> None:
    for version in versions:
        session._dispatch(version, Started(total=2, pos=(0, -59, 0)))
        session._dispatch(version, BatchStarted(environment=batch))


def finish_run(session: Session, *versions: Version, elapsed: int = 1000) -> None:
    for version in versions:
        session._dispatch(
            version, Finished(total=0, passed=0, failed=0, skipped=0, elapsed=elapsed)
        )


class TestRenderHeader:
    """Test the run banner."""

    def test_names_packs_and_versions(self) -> None:
        assert render_header(["my_pack"], [V1, V2]).plain == "Testing my_pack on 26.1.2, 26.1.1"

    def test_omits_packs_when_none_or_many(self) -> None:
        """The pack list only fits in the banner when it stays short."""
        assert render_header([], [V1]).plain == "Testing on 26.1.2"
        assert render_header(["a", "b", "c", "d"], [V1]).plain == "Testing on 26.1.2"


class TestRenderSession:
    """Test the aggregated results view."""

    def test_pending_result_uses_spinner_and_dash(self) -> None:
        """A test still awaiting a version shows a spinner and — for the missing cell."""
        session = Session([V1, V2])
        start_run(session, V1, V2)
        session._dispatch(V1, Passed(name="a:one", time=5))

        lines = rendered_lines(session)
        result_line = next(line for line in lines if "a:one" in line)
        assert result_line.lstrip()[0] in "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        assert "5ms" in result_line
        assert "—" in result_line

    def test_passed_result_shows_timings(self) -> None:
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(V1, Passed(name="a:one", time=5))
        finish_run(session, V1)

        assert any("✓ a:one (5ms)" in line for line in rendered_lines(session))

    def test_batch_header_shows_dimension(self) -> None:
        """The batch dimension is displayed next to the environment when known."""
        session = Session([V1])
        session._dispatch(V1, Started(total=1, pos=(0, -59, 0)))
        session._dispatch(
            V1, BatchStarted(environment="ward:default", dimension="minecraft:the_nether")
        )
        session._dispatch(V1, Passed(name="a:one", time=5))
        finish_run(session, V1)

        assert any(
            "ward:default (minecraft:the_nether)" in line for line in rendered_lines(session)
        )

    def test_batch_header_without_dimension_is_plain(self) -> None:
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(V1, Passed(name="a:one", time=5))
        finish_run(session, V1)

        lines = rendered_lines(session)
        assert any(line.strip() == "default" for line in lines)

    def test_single_version_failure_shows_error_only(self) -> None:
        """With one version the error is printed without a Failed on line."""
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(
            V1, Failed("a:one", time=5, error="boom", required=True, line=None, tick=None)
        )
        finish_run(session, V1)

        lines = rendered_lines(session)
        assert any("✗ a:one" in line for line in lines)
        assert any("boom" in line for line in lines)
        assert not any("Failed on:" in line for line in lines)

    def test_multi_version_failure_names_versions(self) -> None:
        """With several versions the failing ones are listed with their errors."""
        session = Session([V1, V2])
        start_run(session, V1, V2)
        session._dispatch(V1, Passed(name="a:one", time=5))
        session._dispatch(
            V2, Failed("a:one", time=7, error="boom", required=True, line=None, tick=None)
        )
        finish_run(session, V1, V2)

        lines = rendered_lines(session)
        assert any("Failed on: 26.1.1" in line for line in lines)
        assert any("26.1.1: boom" in line for line in lines)

    def test_optional_failure_renders_as_skipped(self) -> None:
        """A failed optional test shows its reason but not as a failure."""
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(
            V1, Failed("a:opt", time=5, error="boom", required=False, line=None, tick=None)
        )
        finish_run(session, V1)

        lines = rendered_lines(session)
        assert any("⊘ a:opt" in line for line in lines)
        assert any("boom" in line for line in lines)
        assert any("1 skipped" in line for line in lines)
        assert not any("failed" in line for line in lines)

    def test_failure_position_is_appended(self) -> None:
        """Structured line/tick fields are rendered as the position suffix."""
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(V1, Failed("a:one", time=5, error="boom", required=True, line=4, tick=12))
        finish_run(session, V1)

        assert any("boom (line 4, tick 12)" in line for line in rendered_lines(session))

    def test_failure_position_shows_resolved_file(self) -> None:
        """With a resolver the position is the root-relative path:line."""
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(V1, Failed("a:one", time=5, error="boom", required=True, line=4, tick=12))
        finish_run(session, V1)

        def resolve(folder: str, resource: str) -> str | None:
            assert (folder, resource) == ("test", "a:one")
            return "packs/my_pack/data/a/test/one.mcfunction"

        rendered = render_session(session, resolve)
        assert any(
            "boom (packs/my_pack/data/a/test/one.mcfunction:4, tick 12)" in line
            for line in rendered.plain.splitlines()
        )

    def test_diagnostics_show_resolved_file(self) -> None:
        """Diagnostics resolve their file through the kind's registry folder."""
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(
            V1, Diagnostic("error", "minecraft:loot_table", "a:broken", "Missing type")
        )
        finish_run(session, V1)

        def resolve(folder: str, resource: str) -> str | None:
            assert (folder, resource) == ("loot_table", "a:broken")
            return "my_pack/data/a/loot_table/broken.json"

        rendered = render_session(session, resolve)
        # The path replaces the id: it already carries it
        assert any(
            "[minecraft:loot_table] my_pack/data/a/loot_table/broken.json" in line
            for line in rendered.plain.splitlines()
        )

    def test_diagnostics_are_rendered(self) -> None:
        session = Session([V1, V2])
        start_run(session, V1, V2)
        session._dispatch(
            V1, Diagnostic("error", "minecraft:loot_table", "a:broken", "Missing type")
        )
        session._dispatch(V1, Diagnostic("warn", "pack.mcmeta", "broken", "Invalid meta"))
        finish_run(session, V1, V2)

        lines = rendered_lines(session)
        # Versions are named when only some of them reported the problem
        assert any("✗ [minecraft:loot_table] a:broken (26.1.2)" in line for line in lines)
        assert any("Missing type" in line for line in lines)
        assert any("⊘ [pack.mcmeta] broken" in line for line in lines)

    def test_no_diagnostics_section_when_clean(self) -> None:
        session = Session([V1])
        start_run(session, V1)
        finish_run(session, V1)

        assert not any("Load diagnostics" in line for line in rendered_lines(session))

    def test_aborted_version_is_reported(self) -> None:
        session = Session([V1])
        session._dispatch(V1, StreamError("server died"))

        assert any("✗ 26.1.2: server died" in line for line in rendered_lines(session))

    def test_progress_summary_while_running(self) -> None:
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(V1, Passed(name="a:one", time=5))

        assert rendered_lines(session)[-1] == "Tests: 1/2 completed"

    def test_final_summary_single_version(self) -> None:
        """Single version folds its duration into the summary line."""
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(V1, Passed(name="a:one", time=5))
        session._dispatch(
            V1, Failed("a:two", time=5, error="boom", required=True, line=None, tick=None)
        )
        finish_run(session, V1)

        assert rendered_lines(session)[-1] == "Tests: 1 passed, 1 failed, 2 total (1.0s)"

    def test_final_summary_multi_version_spread(self) -> None:
        """Multiple versions get per-version lines above the summary."""
        session = Session([V1, V2])
        start_run(session, V1, V2)
        for version in (V1, V2):
            session._dispatch(version, Passed(name="a:one", time=5))
            session._dispatch(version, Passed(name="a:two", time=5))
        finish_run(session, V1, V2)

        lines = rendered_lines(session)
        assert lines[-4] == "26.1.2: 2/2 (1.0s)"
        assert lines[-3] == "26.1.1: 2/2 (1.0s)"
        assert lines[-1] == "Tests: 2 passed, 2 total"
