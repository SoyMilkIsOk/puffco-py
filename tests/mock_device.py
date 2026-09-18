"""
Test fixtures and device factories for simulated Puffco hardware.
"""

from puffco_py.constants import (
    PATH_CHAMBER_TYPE,
    PATH_DEVICE_NAME,
)
from puffco_py.mock import (
    MockBleakClient,
)
from puffco_py.models import ChamberType


def create_mock_peak_pro(
    address: str = "F7:11:95:C5:14:9B",
    auth_fail: bool = False,
    connect_fail: bool = False,
) -> MockBleakClient:
    """Creates a mock Peak Pro BLE device with standard 3DXL chamber."""
    client = MockBleakClient(
        address=address,
        auth_fail=auth_fail,
        connect_fail=connect_fail,
    )
    client.vfs[PATH_DEVICE_NAME] = b"SAMS PEAK\x00"
    client.vfs[PATH_CHAMBER_TYPE] = bytes([ChamberType.CHAMBER_3DXL.value])
    return client


def create_mock_proxy(
    address: str = "00:1B:DC:12:34:56",
    auth_fail: bool = False,
    connect_fail: bool = False,
) -> MockBleakClient:
    """Creates a mock Puffco Proxy BLE device with integer tenths temp format."""
    client = MockBleakClient(
        address=address,
        auth_fail=auth_fail,
        connect_fail=connect_fail,
    )
    client.model_number = "Puffco Proxy"
    client.vfs[PATH_DEVICE_NAME] = b"Puffco Proxy\x00"
    client.vfs[PATH_CHAMBER_TYPE] = bytes([ChamberType.TOAD.value])
    return client
