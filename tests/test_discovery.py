"""
Unit tests for BLE device discovery, MAC OUI filtering, and RSSI signal sorting.
"""

import asyncio
import unittest
from unittest.mock import patch

from puffco_py.constants import (
    PUFFCO_LORAX_SVC_UUID,
    PUFFCO_MAC_PREFIXES,
)
from puffco_py.discovery import (
    PuffcoDiscoveredDevice,
    is_puffco_device,
    scan_puffco_devices,
)
from puffco_py.mock import (
    MockAdvertisementData,
    MockBleakScanner,
    MockBLEDevice,
)


class TestDiscovery(unittest.TestCase):
    def test_is_puffco_device_by_name(self):
        """Verify matching against Puffco name keywords (case-insensitive)."""
        # Name in advertisement
        dev = MockBLEDevice("Unknown", "AA:BB:CC:DD:EE:FF")
        adv1 = MockAdvertisementData(local_name="Peak Pro 3DXL")
        self.assertTrue(is_puffco_device(dev, adv1))

        adv2 = MockAdvertisementData(local_name="puffco proxy")
        self.assertTrue(is_puffco_device(dev, adv2))

        # Name in device object fallback
        dev_named = MockBLEDevice("My Puffco Sesh", "AA:BB:CC:DD:EE:FF")
        adv_empty = MockAdvertisementData(local_name=None)
        self.assertTrue(is_puffco_device(dev_named, adv_empty))

    def test_is_puffco_device_by_lorax_uuid(self):
        """Verify matching against Lorax BLE service UUID."""
        dev = MockBLEDevice("Custom Gadget", "AA:BB:CC:DD:EE:FF")
        adv = MockAdvertisementData(
            local_name="Custom Gadget",
            service_uuids=[PUFFCO_LORAX_SVC_UUID.lower()],
        )
        self.assertTrue(is_puffco_device(dev, adv))

    def test_is_puffco_device_by_mac_prefix(self):
        """Verify matching against known Puffco MAC OUI prefixes."""
        for prefix in PUFFCO_MAC_PREFIXES:
            addr = f"{prefix}:12:34:56"
            dev = MockBLEDevice("Unknown", addr)
            adv = MockAdvertisementData()
            self.assertTrue(is_puffco_device(dev, adv), f"Failed to match MAC prefix {prefix}")

    def test_is_puffco_device_reject_unknown(self):
        """Verify non-Puffco devices are rejected."""
        dev = MockBLEDevice("Generic Bluetooth Speaker", "11:22:33:44:55:66")
        adv = MockAdvertisementData(
            local_name="Generic Bluetooth Speaker",
            service_uuids=["00001800-0000-1000-8000-00805f9b34fb"],
        )
        self.assertFalse(is_puffco_device(dev, adv))

    def test_discovered_device_dataclass_str(self):
        """Verify PuffcoDiscoveredDevice string formatting."""
        item = PuffcoDiscoveredDevice(
            name="SAMS PEAK",
            address="F7:11:95:C5:14:9B",
            rssi=-56,
            is_lorax=True,
        )
        self.assertIn("SAMS PEAK", str(item))
        self.assertIn("-56 dBm", str(item))

    def test_scan_devices_sorting_and_filtering(self):
        """Verify scan_puffco_devices filters non-Puffco devices and sorts by RSSI descending."""

        async def _run():
            with patch("puffco_py.discovery.BleakScanner", MockBleakScanner):
                devices = await scan_puffco_devices(timeout=0.01)
                self.assertEqual(len(devices), 2)

                # Highest RSSI (-56 dBm) first, lower RSSI (-72 dBm) second
                self.assertEqual(devices[0].name, "SAMS PEAK")
                self.assertEqual(devices[0].rssi, -56)
                self.assertTrue(devices[0].is_lorax)

                self.assertEqual(devices[1].name, "Puffco Proxy")
                self.assertEqual(devices[1].rssi, -72)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
