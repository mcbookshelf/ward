class WardError(Exception):
    """Base exception for all Ward errors."""


class VersionError(WardError):
    pass


class VersionNotFoundError(VersionError):
    def __init__(self, version: str):
        self.version = version
        super().__init__(f"Version not found: {version}")


class InstallError(WardError):
    pass


class AssetNotFoundError(InstallError):
    def __init__(self, asset: str, version: str):
        self.asset = asset
        self.version = version
        super().__init__(f"No compatible {asset} found for Minecraft {version}")


class DownloadFailedError(InstallError):
    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Download failed from {url}: {reason}")


class JavaNotFoundError(InstallError):
    """No usable Java runtime could be resolved or provisioned."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Java runtime unavailable: {reason}")


class DeployError(WardError):
    """Datapacks could not be deployed into the environment's world."""


class MissingFeatureError(DeployError):
    def __init__(self, version: str, what: str):
        self.version = version
        self.what = what
        super().__init__(f"Ward for Minecraft {version} cannot {what}")


class ProcessError(WardError):
    pass


class ProcessStartupError(ProcessError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Process startup failed: {reason}")


class ProcessConnectionError(ProcessError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Process connection failed: {reason}")


class ProcessTimeoutError(ProcessConnectionError):
    pass
