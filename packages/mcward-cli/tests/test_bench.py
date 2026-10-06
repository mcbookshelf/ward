"""Tests for the bench command and its report."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from mcward import BenchReport
from mcward.cli import cli
from mcward.cli.reporters.bench import format_bytes, format_time, render_report, render_summary


class TestFormat:
    @pytest.mark.parametrize(
        ("nanos", "text"),
        [(412.0, "412 ns"), (412_300.0, "412.3 µs"), (96_400_000.0, "96.4 ms"), (2.5e9, "2.5 s")],
    )
    def test_time_picks_its_unit(self, nanos: float, text: str) -> None:
        assert format_time(nanos) == text

    def test_bytes_pick_their_unit(self) -> None:
        assert format_bytes(512) == "512 B"
        assert format_bytes(38_200) == "38.2 kB"


class TestRender:
    def test_a_measured_command(self) -> None:
        report = BenchReport(
            name="function a:b",
            batch=73,
            times=(400_000.0, 420_000.0),
            commands=2401,
            allocated=38_200,
        )
        text = "\n".join(render_report(1, report))
        assert "Benchmark 1:" in text
        assert "410.0 µs" in text
        assert "0.82% of a tick" in text
        assert "2401 commands, 38.2 kB allocated" in text
        assert "2 samples of 73 runs" in text

    def test_a_first_run_that_failed_is_a_warning(self) -> None:
        report = BenchReport(
            name="function a:typo", batch=1, times=(100.0,), error="Unknown function"
        )
        text = "\n".join(render_report(1, report))
        assert "first run failed: Unknown function" in text
        assert "Time (mean" in text

    def test_a_command_that_was_not_measured(self) -> None:
        text = "\n".join(render_report(2, BenchReport(name="sya", failed="Unknown command")))
        assert "not measured: Unknown command" in text
        assert "Time (mean" not in text

    def test_the_summary_names_the_fastest(self) -> None:
        slow = BenchReport(name="slow", batch=1, times=(400.0, 420.0))
        fast = BenchReport(name="fast", batch=1, times=(100.0, 100.0))
        text = "\n".join(render_summary([slow, fast]))
        assert "fast" in text.splitlines()[1]
        assert "times faster than slow" in text

    def test_no_summary_for_one_command(self) -> None:
        assert render_summary([BenchReport(name="only", batch=1, times=(100.0,))]) == []


class TestCommand:
    def test_help_lists_bench(self) -> None:
        result = CliRunner().invoke(cli, ["--help"])
        assert "bench" in result.output

    def test_a_command_is_required(self) -> None:
        result = CliRunner().invoke(cli, ["bench"])
        assert result.exit_code != 0

    def test_without_a_pack_a_version_is_needed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(cli, ["bench", "say hi"])
        assert result.exit_code != 0
        assert "give a version with -v" in result.output
