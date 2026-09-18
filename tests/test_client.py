"""
Unit and integration tests for PuffcoClient using simulated Lorax BLE hardware.
"""

import asyncio
import unittest

from puffco_py.client import PuffcoClient
from puffco_py.exceptions import PuffcoConnectionError
from puffco_py.mock import MockPuffcoClient
from puffco_py.models import ChamberType, OperatingState, PuffcoProfile
from tests.mock_device import create_mock_peak_pro, create_mock_proxy


class TestPuffcoClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_ble = create_mock_peak_pro()
        self.client = PuffcoClient(
            "F7:11:95:C5:14:9B", auto_reconnect=False, ble_client=self.mock_ble
        )

    async def asyncTearDown(self):
        if self.client.is_connected:
            await self.client.disconnect()

    async def test_connect_and_auth_success(self):
        """Verify successful BLE connect, Lorax handshake, and initial diagnostics poll."""
        connected = await self.client.connect()
        self.assertTrue(connected)
        self.assertTrue(self.client.is_connected)

        telem = self.client.telemetry
        self.assertEqual(telem.device_name, "SAMS PEAK")
        self.assertEqual(telem.serial_number, "MOCK-SN-88219")
        self.assertEqual(telem.firmware_version, "W.X.Y (FW v1.2.3)")
        self.assertEqual(telem.chamber_type, ChamberType.CHAMBER_3DXL)
        self.assertEqual(telem.battery_pct, 88)
        self.assertTrue(telem.is_charging)
        self.assertEqual(telem.lifetime_dabs, 1337)
        self.assertEqual(len(telem.profiles), 4)
        self.assertEqual(telem.active_profile, 1)

    async def test_connect_failure_raises(self):
        """Verify connection error is raised when BLE fails."""
        fail_ble = create_mock_peak_pro(connect_fail=True)
        bad_client = PuffcoClient("F7:11:95:C5:14:9B", auto_reconnect=False, ble_client=fail_ble)
        with self.assertRaises(PuffcoConnectionError):
            await bad_client.connect()
        self.assertFalse(bad_client.is_connected)

    async def test_connect_auth_failure_recovery(self):
        """Verify client gracefully finishes connect even if Lorax auth key differs."""
        auth_fail_ble = create_mock_peak_pro(auth_fail=True)
        fail_auth_client = PuffcoClient(
            "F7:11:95:C5:14:9B", auto_reconnect=False, ble_client=auth_fail_ble
        )
        connected = await fail_auth_client.connect()
        self.assertTrue(connected)
        self.assertTrue(fail_auth_client._auth_completed)
        await fail_auth_client.disconnect()

    async def test_read_and_write_path(self):
        """Verify reading and writing virtual paths over Lorax VFS."""
        await self.client.connect()

        # Read existing device name
        name_bytes = await self.client.read_path("/u/sys/name")
        self.assertEqual(name_bytes, b"SAMS PEAK\x00")

        # Write custom path and verify
        write_ok = await self.client.write_path("/p/test/key", b"test_payload_123")
        self.assertTrue(write_ok)
        read_back = await self.client.read_path("/p/test/key")
        self.assertEqual(read_back, b"test_payload_123")

        # Read nonexistent path
        empty_res = await self.client.read_path("/p/does/not/exist")
        self.assertEqual(empty_res, b"")

    async def test_telemetry_polling_and_listeners(self):
        """Verify poll() triggers listeners and returns live telemetry."""
        await self.client.connect()

        telemetry_updates = []
        state_updates = []
        conn_updates = []

        def _on_telem(t):
            telemetry_updates.append(t.live_temp_f)

        def _on_state(st):
            state_updates.append(st)

        def _on_conn(c):
            conn_updates.append(c)

        self.client.add_telemetry_listener(_on_telem)
        self.client.add_state_listener(_on_state)
        self.client.add_connection_listener(_on_conn)

        # Single manual poll
        polled = await self.client.poll()
        self.assertIsNotNone(polled)
        self.assertGreater(len(telemetry_updates), 0)

        # Remove listener test
        self.client.remove_telemetry_listener(_on_telem)
        prev_count = len(telemetry_updates)
        await self.client.poll()
        self.assertEqual(len(telemetry_updates), prev_count)

        self.client.remove_state_listener(_on_state)
        self.client.remove_connection_listener(_on_conn)

    async def test_session_controls(self):
        """Verify sesh commands: start, stop, boost, profile, stealth, lantern."""
        await self.client.connect()

        # 1. Start session
        start_ok = await self.client.start_session()
        self.assertTrue(start_ok)
        self.assertEqual(self.client.telemetry.operating_state, OperatingState.HEAT_PREHEAT)
        self.assertTrue(self.client.telemetry.is_heating)

        # 2. Boost
        boost_ok = await self.client.boost()
        self.assertTrue(boost_ok)

        # 3. Stop session
        stop_ok = await self.client.stop_session()
        self.assertTrue(stop_ok)
        self.assertEqual(self.client.telemetry.operating_state, OperatingState.IDLE)
        self.assertEqual(self.client.telemetry.time_remaining, 0)

        # 4. Set Profile
        prof_ok = await self.client.set_profile(0)
        self.assertTrue(prof_ok)
        self.assertEqual(self.client.telemetry.active_profile, 0)
        self.assertEqual(self.client.telemetry.target_temp_f, 465.0)

        # 5. Set Temperature
        temp_ok = await self.client.set_temperature(495.0)
        self.assertTrue(temp_ok)
        self.assertEqual(self.client.telemetry.target_temp_f, 495.0)

        # 6. Stealth Mode
        stealth_ok = await self.client.set_stealth_mode(True)
        self.assertTrue(stealth_ok)
        self.assertTrue(self.client.telemetry.stealth_mode)
        stealth_off_ok = await self.client.set_stealth_mode(False)
        self.assertTrue(stealth_off_ok)
        self.assertFalse(self.client.telemetry.stealth_mode)

        # 7. Lantern Mode
        self.assertTrue(await self.client.start_lantern())
        self.assertTrue(await self.client.stop_lantern())

        # 8. LED Brightness
        self.assertTrue(await self.client.set_led_brightness(200, 150, 100, 50))

        # 9. Sleep Mode
        self.assertTrue(await self.client.enter_sleep_mode())

        # 10. Direct one-shot getters
        bat = await self.client.get_battery_level()
        self.assertEqual(bat, 88)
        dabs = await self.client.get_total_dabs()
        self.assertGreaterEqual(dabs, 1337)

    async def test_telemetry_streaming(self):
        """Verify adaptive streaming task starts and cancels cleanly."""
        await self.client.connect()
        await self.client.start_telemetry_stream(interval_heating=0.01, interval_idle=0.01)
        self.assertTrue(self.client._streaming)
        await asyncio.sleep(0.05)
        await self.client.stop_telemetry_stream()
        self.assertFalse(self.client._streaming)

    async def test_unexpected_disconnect_and_listener(self):
        """Verify unexpected BLE drop notifies listeners and marks is_connected=False."""
        await self.client.connect()
        conn_events = []
        self.client.add_connection_listener(lambda c: conn_events.append(c))

        # Simulate unexpected hardware drop
        self.mock_ble.trigger_disconnect()
        self.assertFalse(self.client.is_connected)
        self.assertIn(False, conn_events)

    async def test_mock_puffco_client_subclass(self):
        """Verify high-level MockPuffcoClient works directly."""
        mock_c = MockPuffcoClient("F7:11:95:C5:14:9B", auto_reconnect=False)
        connected = await mock_c.connect()
        self.assertTrue(connected)
        self.assertTrue(mock_c.is_connected)
        self.assertEqual(mock_c.telemetry.device_name, "Mock Peak Pro")
        await mock_c.disconnect()
        self.assertFalse(mock_c.is_connected)

    async def test_proxy_device_temperature_and_chamber(self):
        """Verify Proxy parsing (chamber TOAD, integer tenths temp conversion)."""
        proxy_ble = create_mock_proxy()
        proxy_client = PuffcoClient("00:1B:DC:12:34:56", auto_reconnect=False, ble_client=proxy_ble)
        await proxy_client.connect()

        self.assertEqual(proxy_client.telemetry.chamber_type, ChamberType.TOAD)
        # Set temperature on proxy (stored as tenths of C)
        self.assertTrue(await proxy_client.set_temperature(510.0))
        self.assertEqual(proxy_client.telemetry.target_temp_f, 510.0)
        await proxy_client.disconnect()

    async def test_profile_editing_and_save(self):
        """Verify full profile customization (duration, name, temp, save_profile)."""
        await self.client.connect()

        # 1. Edit duration for slot 0
        self.assertTrue(await self.client.set_profile_duration(0, 60))
        self.assertEqual(self.client.telemetry.profiles[0].duration_s, 60)

        # 2. Edit name for slot 0
        self.assertTrue(await self.client.set_profile_name(0, "SUPER ROSIN"))
        self.assertEqual(self.client.telemetry.profiles[0].name, "SUPER ROSIN")

        # 3. Edit temperature for slot 0
        self.assertTrue(await self.client.set_temperature(490.0, slot=0))
        self.assertEqual(self.client.telemetry.profiles[0].target_temp_f, 490)

        # 4. Atomic save_profile for slot 2
        new_prof = PuffcoProfile(slot=2, name="DIAMONDS", target_temp_f=540, duration_s=45)
        self.assertTrue(await self.client.save_profile(2, new_prof))
        self.assertEqual(self.client.telemetry.profiles[2].name, "DIAMONDS")
        self.assertEqual(self.client.telemetry.profiles[2].target_temp_f, 540)
        self.assertEqual(self.client.telemetry.profiles[2].duration_s, 45)

    async def test_boost_settings(self):
        """Verify boost temperature and duration customization."""
        await self.client.connect()

        self.assertTrue(await self.client.set_boost_temperature(20.0))
        self.assertEqual(self.client.telemetry.boost_temp_f, 20)

        self.assertTrue(await self.client.set_boost_duration(25))
        self.assertEqual(self.client.telemetry.boost_duration_s, 25)

    async def test_device_model_detection(self):
        """Verify device model detection on Peak Pro V2 and Proxy."""
        await self.client.connect()
        # Mock Peak Pro returns "Peak Pro V2"
        self.assertEqual(self.client.telemetry.device_model, "Peak Pro (V2)")

        proxy_ble = create_mock_proxy()
        proxy_client = PuffcoClient("00:1B:DC:12:34:56", auto_reconnect=False, ble_client=proxy_ble)
        await proxy_client.connect()
        self.assertEqual(proxy_client.telemetry.device_model, "Puffco Proxy")
        await proxy_client.disconnect()


if __name__ == "__main__":
    unittest.main()
