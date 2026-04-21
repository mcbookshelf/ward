"""Ward exception hierarchy.

* WardError
  x VersionError
    - VersionNotFoundError
  x InstallError
    - AssetNotFoundError
    - DownloadFailedError
  x ProcessError
    - ProcessStartupError
    - ProcessConnectionError
"""


class WardError(Exception):
    """Base exception for all Ward errors."""


class VersionError(WardError):
    """Version-related errors."""


class VersionNotFoundError(VersionError):
    """Version or alias not found in registry."""

    def __init__(self, version: str):
        self.version = version
        super().__init__(f"Version not found: {version}")


class InstallError(WardError):
    """Installation-related errors."""


class AssetNotFoundError(InstallError):
    """Required asset not available for target version."""

    def __init__(self, asset: str, version: str):
        self.asset = asset
        self.version = version
        super().__init__(f"No compatible {asset} found for Minecraft {version}")


class DownloadFailedError(InstallError):
    """Network download failed."""

    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Download failed from {url}: {reason}")


class ProcessError(WardError):
    """Process-related errors."""


class ProcessStartupError(ProcessError):
    """Process failed to start or initialize."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Process startup failed: {reason}")


class ProcessConnectionError(ProcessError):
    """Process IPC connection failed."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Process connection failed: {reason}")
