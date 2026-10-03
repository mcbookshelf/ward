"""Tests for the GitHub Actions annotation reporter."""

from pathlib import Path

import pytest

from mcward import Version

# Aliased so pytest does not try to collect the production class as tests
from mcward._protocol import (
    BatchStarted,
    Diagnostic,
    StreamError,
    TestFailed as Failed,
    TestsStarted as Started,
)
from mcward._runner import TestSession as Session
from mcward.cli.datapacks import pack_resolver
from mcward.cli.reporters.github import annotations

V1 = Version.parse("26.1.2")
V2 = Version.parse("26.1.1")


@pytest.fixture(autouse=True)
def isolated_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests anchor at their tmp cwd, not the runner's own GITHUB_WORKSPACE."""
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)


def start_run(session: Session, *versions: Version, batch: str = "default") -> None:
    for version in versions:
        session._dispatch(version, Started(total=1, pos=(0, -59, 0)))
        session._dispatch(version, BatchStarted(environment=batch))


def fail_test(
    session: Session,
    version: Version,
    name: str,
    error: str,
    line: int | None = None,
    tick: int | None = None,
) -> None:
    session._dispatch(
        version, Failed(name, time=5, error=error, required=True, line=line, tick=tick)
    )


def make_pack(root: Path, *files: str) -> Path:
    pack = root / "my_pack"
    for file in files:
        path = pack / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    return pack


class TestFailedTests:
    """Annotations for failed tests."""

    def test_annotates_file_and_line(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack = make_pack(tmp_path, "data/ward/test/chest/fill.mcfunction")

        session = Session([V1])
        start_run(session, V1)
        fail_test(session, V1, "ward:chest/fill", "Expected a chest", line=4, tick=12)

        [command] = annotations(session, pack_resolver([pack]))
        assert command == (
            "::error title=ward%3Achest/fill failed on 26.1.2,"
            "file=my_pack/data/ward/test/chest/fill.mcfunction,line=4"
            "::Expected a chest (line 4, tick 12)"
        )

    def test_no_file_when_test_is_not_in_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        session = Session([V1])
        start_run(session, V1)
        fail_test(session, V1, "ward:missing", "boom", line=1, tick=1)

        [command] = annotations(session, pack_resolver([tmp_path / "absent_pack"]))
        assert "file=" not in command
        assert "line=" not in command

    def test_optional_failure_annotates_as_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        session = Session([V1])
        start_run(session, V1)
        session._dispatch(
            V1, Failed("ward:opt", time=5, error="boom", required=False, line=None, tick=None)
        )

        [command] = annotations(session, pack_resolver([tmp_path / "absent_pack"]))
        assert command.startswith("::warning ")
        assert "ward%3Aopt skipped on 26.1.2" in command

    def test_no_line_for_position_less_failures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        pack = make_pack(tmp_path, "data/ward/test/slow.mcfunction")

        session = Session([V1])
        start_run(session, V1)
        fail_test(session, V1, "ward:slow", "Didn't succeed or fail within 100 ticks")

        [command] = annotations(session, pack_resolver([pack]))
        assert "file=my_pack/data/ward/test/slow.mcfunction" in command
        assert "line=" not in command
        assert command.endswith("::Didn't succeed or fail within 100 ticks")

    def test_merges_versions_into_one_annotation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        session = Session([V1, V2])
        start_run(session, V1, V2)
        fail_test(session, V1, "ward:multi", "boom", line=2, tick=3)
        fail_test(session, V2, "ward:multi", "boom", line=2, tick=3)

        [command] = annotations(session, pack_resolver([]))
        assert "ward%3Amulti failed on 26.1.2%2C 26.1.1" in command

    def test_escapes_newlines_in_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        session = Session([V1])
        start_run(session, V1)
        fail_test(session, V1, "ward:multiline", "first\nsecond")

        [command] = annotations(session, pack_resolver([]))
        assert command.endswith("::first%0Asecond")

    def test_pack_outside_cwd_but_inside_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Paths anchor at GITHUB_WORKSPACE, so --pack ../elsewhere still maps."""
        pack = make_pack(tmp_path / "packs", "data/ward/test/deep.mcfunction")
        (tmp_path / "sub").mkdir()
        monkeypatch.chdir(tmp_path / "sub")
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

        session = Session([V1])
        start_run(session, V1)
        fail_test(session, V1, "ward:deep", "boom", line=1, tick=1)

        [command] = annotations(session, pack_resolver([pack]))
        assert "file=packs/my_pack/data/ward/test/deep.mcfunction,line=1" in command

    def test_custom_resolver_maps_to_sources(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        session = Session([V1])
        start_run(session, V1)
        fail_test(session, V1, "ward:generated", "boom", line=2, tick=3)

        [command] = annotations(session, lambda folder, resource: "src/data/test/generated.txt")
        assert "file=src/data/test/generated.txt,line=2" in command


class TestDiagnostics:
    """Annotations for datapack load problems."""

    def diagnose(self, session: Session, version: Version, **fields: str) -> None:
        session._dispatch(
            version,
            Diagnostic(
                severity=fields["severity"],
                kind=fields["kind"],
                id=fields["id"],
                message=fields.get("message", ""),
            ),
        )

    def test_error_annotates_json_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        pack = make_pack(tmp_path, "data/ward/loot_table/broken.json")

        session = Session([V1])
        self.diagnose(
            session,
            V1,
            severity="error",
            kind="minecraft:loot_table",
            id="ward:broken",
            message="Missing type",
        )

        [command] = annotations(session, pack_resolver([pack]))
        assert command.startswith("::error ")
        assert "file=my_pack/data/ward/loot_table/broken.json" in command
        assert command.endswith("::Missing type")

    def test_nested_registry_folder(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        pack = make_pack(tmp_path, "data/ward/tags/function/broken.json")

        session = Session([V1])
        self.diagnose(
            session, V1, severity="error", kind="minecraft:tags/function", id="ward:broken"
        )

        [command] = annotations(session, pack_resolver([pack]))
        assert "file=my_pack/data/ward/tags/function/broken.json" in command

    def test_function_folder_uses_mcfunction(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        pack = make_pack(tmp_path, "data/ward/function/broken.mcfunction")

        session = Session([V1])
        self.diagnose(session, V1, severity="error", kind="minecraft:function", id="ward:broken")

        [command] = annotations(session, pack_resolver([pack]))
        assert "file=my_pack/data/ward/function/broken.mcfunction" in command

    def test_warning_severity_and_plain_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        session = Session([V1])
        self.diagnose(
            session, V1, severity="warn", kind="pack.mcmeta", id="broken", message="Invalid meta"
        )

        [command] = annotations(session, pack_resolver([]))
        assert command.startswith("::warning ")
        assert "file=" not in command


class TestAborted:
    """Annotations for aborted version streams."""

    def test_aborted_version(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        session = Session([V1])
        session._dispatch(V1, StreamError("connection lost"))

        [command] = annotations(session, pack_resolver([]))
        assert command == "::error title=Ward aborted on 26.1.2::connection lost"

    def test_failure_next_to_an_aborted_version(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A test that failed on one version is annotated when the other never reported."""
        monkeypatch.chdir(tmp_path)
        session = Session([V1, V2])
        start_run(session, V1)
        fail_test(session, V1, "ward:one", "boom")
        session._dispatch(V2, StreamError("connection lost"))

        aborted, failed = annotations(session, pack_resolver([]))
        assert aborted == "::error title=Ward aborted on 26.1.1::connection lost"
        assert failed == "::error title=ward%3Aone failed on 26.1.2::boom"
