"""
Device discovery and BLE scanning engine for Puffco hardware.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

try:
    from bleak import BleakScanner
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
except ImportError:
    BleakScanner = None
    BLEDevice = None
    AdvertisementData = None

from .constants import (
    PUFFCO_LORAX_SVC_UUID,
    PUFFCO_MAC_PREFIXES,
    PUFFCO_NAME_KEYWORDS,
)

logger = logging.getLogger("puffco_ble.discovery")


@dataclass
class PuffcoDiscoveredDevice:
    """A discovered Puffco BLE device."""
    name: str
    address: str
    rssi: int
    is_lorax: bool = True
    device: Optional[BLEDevice] = None

    def __str__(self) -> str:
        return f"{self.name} ({self.address}) - RSSI: {self.rssi} dBm"


def is_puffco_device(device: BLEDevice, adv: AdvertisementData) -> bool:
    """Determines if a discovered BLE device is a Puffco product."""
    # 1. Check Advertised Local Name
    dev_name = (adv.local_name or device.name or "").lower()
    for kw in PUFFCO_NAME_KEYWORDS:
        if kw in dev_name:
            return True

    # 2. Check Service UUIDs (Lorax)
    if adv.service_uuids:
        for uuid in adv.service_uuids:
            if PUFFCO_LORAX_SVC_UUID.lower() in uuid.lower():
                return True

    # 3. Check MAC OUI Prefix
    addr = (device.address or "").upper()
    for prefix in PUFFCO_MAC_PREFIXES:
        if addr.startswith(prefix):
            return True

    return False


async def scan_puffco_devices(timeout: float = 5.0) -> List[PuffcoDiscoveredDevice]:
    """
    Scans for nearby Puffco Peak Pro and Proxy devices over BLE.
    Returns a sorted list of discovered devices ordered by signal strength (RSSI).
    """
    if BleakScanner is None:
        raise RuntimeError("Bleak is not installed. Install with 'pip install bleak'.")

    discovered: dict[str, PuffcoDiscoveredDevice] = {}

    def _detection_callback(device: BLEDevice, adv: AdvertisementData):
        if is_puffco_device(device, adv):
            name = adv.local_name or device.name or "Puffco Device"
            is_lorax = False
            if adv.service_uuids:
                is_lorax = any(PUFFCO_LORAX_SVC_UUID.lower() in u.lower() for u in adv.service_uuids)
            
            discovered[device.address] = PuffcoDiscoveredDevice(
                name=name,
                address=device.address,
                rssi=adv.rssi,
                is_lorax=is_lorax,
                device=device,
            )

    scanner = BleakScanner(detection_callback=_detection_callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()

    # Sort descending by signal strength
    results = sorted(discovered.values(), key=lambda d: d.rssi, reverse=True)
    return results
