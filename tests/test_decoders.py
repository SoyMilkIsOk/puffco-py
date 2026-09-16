"""
Unit tests for data decoders (temperature, battery, and dab metrics).
"""

import struct
import unittest

from puffco_ble.protocol import (
    c_to_f,
    f_to_c,
    parse_battery,
    parse_dabs,
    parse_temp,
)


class TestDecoders(unittest.TestCase):
    def test_temperature_conversions(self):
        """Verify Fahrenheit <-> Celsius math."""
        # 32°F == 0°C
        self.assertAlmostEqual(f_to_c(32.0), 0.0, places=2)
        self.assertAlmostEqual(c_to_f(0.0), 32.0, places=2)

        # 500°F == 260.0°C
        self.assertAlmostEqual(f_to_c(500.0), 260.0, places=1)
        self.assertAlmostEqual(c_to_f(260.0), 500.0, places=1)

    def test_parse_temp_float(self):
        """Verify Peak Pro IEEE 754 float temperature parsing."""
        target_c = 265.555  # ~510°F
        raw_float = struct.pack("<f", target_c)

        parsed_f = parse_temp(raw_float)
        self.assertAlmostEqual(parsed_f, 510.0, places=0)

    def test_parse_temp_integer_tenths(self):
        """Verify Proxy integer tenths of °C parsing (e.g. 2650 = 265.0°C)."""
        target_c_tenths = 2600  # 260.0°C -> 500°F
        raw_int = struct.pack("<i", target_c_tenths)

        parsed_f = parse_temp(raw_int)
        self.assertAlmostEqual(parsed_f, 500.0, places=0)

    def test_parse_battery(self):
        """Verify 1-byte and 4-byte battery representations."""
        # 1-byte
        self.assertEqual(parse_battery(bytes([85])), 85)
        self.assertEqual(parse_battery(bytes([100])), 100)

        # 4-byte int (0-100)
        self.assertEqual(parse_battery(struct.pack("<I", 75)), 75)

        # 4-byte int scaled (0-10000 e.g. 7500 = 75%)
        self.assertEqual(parse_battery(struct.pack("<I", 7500)), 75)

        # 4-byte float (0.0-100.0)
        self.assertEqual(parse_battery(struct.pack("<f", 92.4)), 92)

    def test_parse_dabs(self):
        """Verify odometer dab counter parsing."""
        # 4-byte integer
        self.assertEqual(parse_dabs(struct.pack("<I", 1420)), 1420)

        # 4-byte float
        self.assertEqual(parse_dabs(struct.pack("<f", 710.0)), 710)

        # 2-byte integer
        self.assertEqual(parse_dabs(struct.pack("<H", 420)), 420)


if __name__ == "__main__":
    unittest.main()
