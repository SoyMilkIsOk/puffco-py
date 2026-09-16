"""
puffco-ble: Modern Python BLE client and telemetry engine for Puffco devices.
"""

from .client import PuffcoClient
from .discovery import PuffcoDiscoveredDevice, scan_puffco_devices
from .models import (
    CHAMBER_NAMES,
    ChamberType,
    OperatingState,
    PuffcoProfile,
    PuffcoTelemetry,
)
from .threaded import ThreadedPuffcoClient

__version__ = "0.1.0"
__all__ = [
    "PuffcoClient",
    "ThreadedPuffcoClient",
    "PuffcoTelemetry",
    "PuffcoProfile",
    "OperatingState",
    "ChamberType",
    "CHAMBER_NAMES",
    "scan_puffco_devices",
    "PuffcoDiscoveredDevice",
    "__version__",
]
