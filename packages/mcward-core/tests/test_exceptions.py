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
    assert issubclass(VersionError, WardError)
    assert issubclass(InstallError, WardError)
    assert issubclass(ProcessError, WardError)

    assert issubclass(VersionNotFoundError, VersionError)
    assert issubclass(AssetNotFoundError, InstallError)
    assert issubclass(DownloadFailedError, InstallError)
    assert issubclass(ProcessStartupError, ProcessError)
    assert issubclass(ProcessConnectionError, ProcessError)


def test_catch_by_base_class() -> None:
    with pytest.raises(WardError):
        raise VersionNotFoundError("26.1.2")

    with pytest.raises(VersionError):
        raise VersionNotFoundError("26.1.2")

    with pytest.raises(InstallError):
        raise AssetNotFoundError("fabric-api", "26.1.2")

    with pytest.raises(ProcessError):
        raise ProcessStartupError("failed")
