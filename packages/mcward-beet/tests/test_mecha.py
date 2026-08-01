"""Tests for the mecha command tree resolution."""

from pathlib import Path

import pytest

from mcward.mecha import plugin


@pytest.fixture
def resources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A resources directory with sparse tree versions, like the shipped package."""
    for version in ("1.1.0", "1.2.3", "1.10.0"):
        (tmp_path / f"{version}.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(plugin, "RESOURCES_DIR", tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (None, "1.10.0"),
        ("*", "1.10.0"),
        ("latest", "1.10.0"),
        ("1.1", "1.1.0"),
        ("1.1.0", "1.1.0"),
        # Versions without their own tree resolve to the closest older one
        ("1.2.0", "1.1.0"),
        ("1.2.3", "1.2.3"),
        ("1.2.9", "1.2.3"),
        ("1.5.0", "1.2.3"),
        ("1.10.0", "1.10.0"),
        ("2.0.0", "1.10.0"),
        # A bare major.minor pin covers its whole line
        ("1.2", "1.2.3"),
        ("1.10", "1.10.0"),
        # Mc build metadata is ignored
        ("1.2.3+26.2", "1.2.3"),
        (1.1, "1.1.0"),
        # Missing or wildcard components mean newest in that line
        ("1", "1.10.0"),
        ("1.x", "1.10.0"),
        ("1.*", "1.10.0"),
        ("1.2.x", "1.2.3"),
        ("v1.2.3", "1.2.3"),
    ],
)
def test_resolution(resources: Path, version: str | None, expected: str) -> None:
    assert plugin._resolve_command_tree(version) == resources / f"{expected}.json"


@pytest.mark.parametrize("version", ["1.0", "1.0.9", "0.9.0"])
def test_older_than_any_tree(resources: Path, version: str) -> None:
    with pytest.raises(ValueError, match="No ward command tree"):
        plugin._resolve_command_tree(version)


@pytest.mark.parametrize("version", ["abc", "", ">=1.2", "1.2.3.4", "1.x.3", "x.2"])
def test_invalid_version(resources: Path, version: str) -> None:
    with pytest.raises(ValueError, match="Invalid ward version"):
        plugin._resolve_command_tree(version)
