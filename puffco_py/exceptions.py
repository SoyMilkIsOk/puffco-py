"""
Custom exceptions for puffco-py.
"""


class PuffcoError(Exception):
    """Base exception for all puffco-py errors."""

    pass


class PuffcoConnectionError(PuffcoError):
    """Raised when connection to the Puffco device fails or drops unexpectedly."""

    pass


class PuffcoDeviceNotFoundError(PuffcoConnectionError):
    """Raised when scanning finds no reachable Puffco hardware."""

    pass


class PuffcoAuthenticationError(PuffcoError):
    """Raised when the Lorax SHA-256 challenge-response handshake fails."""

    pass


class PuffcoTimeoutError(PuffcoError):
    """Raised when a Lorax command or VFS packet response times out."""

    pass


class PuffcoCommandError(PuffcoError):
    """Raised when a Lorax command fails or returns a non-zero error status code."""

    def __init__(self, message: str, status_code: int = -1):
        super().__init__(f"{message} (status: 0x{status_code:02X})")
        self.status_code = status_code
