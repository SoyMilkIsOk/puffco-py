"""
puffco-py: Modern Python BLE client and telemetry engine for Puffco devices.
"""

from .client import PuffcoClient
from .discovery import PuffcoDiscoveredDevice, scan_puffco_devices
from .exceptions import (
    PuffcoAuthenticationError,
    PuffcoCommandError,
    PuffcoConnectionError,
    PuffcoDeviceNotFoundError,
    PuffcoError,
    PuffcoTimeoutError,
)
from .mock import MockBleakClient, MockPuffcoClient
from .models import (
    CHAMBER_NAMES,
    ChamberType,
    OperatingState,
    PuffcoProfile,
    PuffcoTelemetry,
)
from .threaded import ThreadedPuffcoClient

__version__ = "0.1.1"
__all__ = [
    "PuffcoClient",
    "ThreadedPuffcoClient",
    "MockPuffcoClient",
    "MockBleakClient",
    "PuffcoTelemetry",
    "PuffcoProfile",
    "OperatingState",
    "ChamberType",
    "CHAMBER_NAMES",
    "scan_puffco_devices",
    "PuffcoDiscoveredDevice",
    "PuffcoError",
    "PuffcoConnectionError",
    "PuffcoDeviceNotFoundError",
    "PuffcoAuthenticationError",
    "PuffcoTimeoutError",
    "PuffcoCommandError",
    "__version__",
]
