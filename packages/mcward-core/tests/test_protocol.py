"""Tests for wire message parsing."""

import pytest

from mcward import Coverage, Diagnostic, FunctionCoverage, ProcessConnectionError, Status
from mcward._protocol import (
    BatchFinished,
    BatchStarted,
    StreamError,
    TestFailed as Failed,
    TestPassed as Passed,
    TestsFinished as Finished,
    TestsStarted as Started,
    parse_event,
)


class TestParseEvent:
    """Test parsing wire dicts into typed events."""

    @pytest.mark.parametrize(
        ("message", "event"),
        [
            (
                {"type": "tests_started", "total": 3, "pos": [40, -59, -128]},
                Started(total=3, pos=(40, -59, -128)),
            ),
            ({"type": "tests_started", "total": 3}, Started(total=3, pos=None)),
            ({"type": "batch_started", "environment": "e"}, BatchStarted(environment="e")),
            ({"type": "batch_finished", "environment": "e"}, BatchFinished(environment="e")),
            (
                {"type": "batch_started", "environment": "e", "dimension": "minecraft:the_nether"},
                BatchStarted(environment="e", dimension="minecraft:the_nether"),
            ),
            (
                {"type": "batch_started", "environment": "e", "total": 17},
                BatchStarted(environment="e", total=17),
            ),
            (
                {"type": "batch_finished", "environment": "e", "dimension": "minecraft:the_nether"},
                BatchFinished(environment="e", dimension="minecraft:the_nether"),
            ),
            ({"type": "test_passed", "name": "a:one", "time": 5}, Passed(name="a:one", time=5)),
            (
                {"type": "test_failed", "name": "a:one", "time": 5, "error": "x", "required": True},
                Failed(name="a:one", time=5, error="x", required=True, line=None, tick=None),
            ),
            (
                {
                    "type": "test_failed",
                    "name": "a:one",
                    "time": 5,
                    "error": "boom",
                    "required": False,
                    "line": 4,
                    "tick": 12,
                },
                Failed(name="a:one", time=5, error="boom", required=False, line=4, tick=12),
            ),
            (
                {
                    "type": "load_diagnostic",
                    "severity": "error",
                    "kind": "minecraft:loot_table",
                    "id": "a:broken",
                    "message": "Missing type",
                },
                Diagnostic("error", "minecraft:loot_table", "a:broken", "Missing type"),
            ),
            (
                {
                    "type": "coverage",
                    "functions": {"a:helper": {"reached": [2, 1, 0], "executed": [2, 0, 0]}},
                },
                Coverage(functions={"a:helper": FunctionCoverage((2, 1, 0), (2, 0, 0))}),
            ),
            (
                {
                    "type": "coverage",
                    "functions": {},
                    "conditions": {"minecraft:predicate": {"a:gate": {"": [1, 0]}}},
                },
                Coverage(
                    functions={},
                    conditions={"minecraft:predicate": {"a:gate": {"": (1, 0)}}},
                ),
            ),
            (
                {"type": "coverage", "functions": {}, "pack_format": [119, 1]},
                Coverage(functions={}, pack_format=(119, 1)),
            ),
            (
                {
                    "type": "tests_finished",
                    "total": 3,
                    "passed": 1,
                    "failed": 1,
                    "skipped": 1,
                    "elapsed": 900,
                },
                Finished(total=3, passed=1, failed=1, skipped=1, elapsed=900),
            ),
            (
                {"type": "tests_finished", "elapsed": 900},
                Finished(total=None, passed=None, failed=None, skipped=None, elapsed=900),
            ),
            ({"type": "status", "ready": True}, Status(ready=True)),
            (
                {"type": "status", "ready": False, "protocol": 1, "mod": "1.3", "minecraft": "26"},
                Status(ready=False, protocol=1, mod="1.3", minecraft="26"),
            ),
            ({"type": "error", "message": "boom"}, StreamError(message="boom")),
        ],
    )
    def test_known_events_parse(self, message: dict, event: object) -> None:
        assert parse_event(message) == event

    def test_unknown_types_parse_to_none(self) -> None:
        """Informational messages from a newer mod are skipped, not fatal."""
        assert parse_event({"type": "brand_new_thing", "data": 1}) is None
        assert parse_event({}) is None

    def test_known_event_with_missing_field_fails_loudly(self) -> None:
        """A known type missing a required field is protocol corruption."""
        with pytest.raises(ProcessConnectionError, match="test_passed"):
            parse_event({"type": "test_passed", "name": "a:one"})
