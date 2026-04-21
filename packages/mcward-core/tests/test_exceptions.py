"""Tests for Ward exception hierarchy."""

import pytest

from mcward import (
    AssetNotFoundError,
    DownloadFailedError,
    InstallError,
    ProcessConnectionError,
    ProcessError,
    ProcessStartupError,
    VersionError,
    VersionNotFoundError,
    WardError,
)


def test_exception_hierarchy() -> None:
    """Test that exception hierarchy is correct."""
    # All exceptions inherit from WardError
    assert issubclass(VersionError, WardError)
    assert issubclass(InstallError, WardError)
    assert issubclass(ProcessError, WardError)

    # Specific exceptions inherit from category
    assert issubclass(VersionNotFoundError, VersionError)
    assert issubclass(AssetNotFoundError, InstallError)
    assert issubclass(DownloadFailedError, InstallError)
    assert issubclass(ProcessStartupError, ProcessError)
    assert issubclass(ProcessConnectionError, ProcessError)


def test_catch_by_base_class() -> None:
    """Test that exceptions can be caught by their base class."""
    # Can catch all with WardError
    with pytest.raises(WardError):
        raise VersionNotFoundError("26.1.2")

    # Can catch by category
    with pytest.raises(VersionError):
        raise VersionNotFoundError("26.1.2")

    with pytest.raises(InstallError):
        raise AssetNotFoundError("fabric-api", "26.1.2")

    with pytest.raises(ProcessError):
        raise ProcessStartupError("failed")
