"""
Unit tests for ThreadedPuffcoClient background worker thread and synchronous API.
"""

import time
import unittest

from puffco_py.models import OperatingState, PuffcoProfile
from puffco_py.threaded import ThreadedPuffcoClient


class TestThreadedPuffcoClient(unittest.TestCase):
    def test_lifecycle_start_and_stop(self):
        """Verify thread starts, initializes event loop, and stops cleanly."""
        client = ThreadedPuffcoClient(mock=True)
        self.assertFalse(client._running)

        client.start()
        self.assertTrue(client._running)
        self.assertIsNotNone(client._thread)
        self.assertTrue(client._thread.is_alive())

        client.stop()
        self.assertFalse(client._running)
        self.assertIsNone(client._thread)

    def test_context_manager(self):
        """Verify __enter__ starts worker thread and __exit__ stops it."""
        with ThreadedPuffcoClient(mock=True) as client:
            self.assertTrue(client._running)
            self.assertIsNotNone(client._thread)
            self.assertTrue(client._thread.is_alive())

        self.assertFalse(client._running)
        self.assertIsNone(client._thread)

    def test_connect_and_wait_connected(self):
        """Verify synchronous wait_connected blocks and succeeds with mock device."""
        client = ThreadedPuffcoClient("F7:11:95:C5:14:9B", mock=True)
        try:
            client.start()
            connected = client.wait_connected(timeout=5.0)
            self.assertTrue(connected)
            self.assertTrue(client.is_connected)
            self.assertEqual(client.telemetry.device_name, "Mock Peak Pro")
            self.assertEqual(client.telemetry.battery_pct, 88)
        finally:
            client.stop()

    def test_listeners_across_threads(self):
        """Verify callbacks are triggered across thread boundaries."""
        client = ThreadedPuffcoClient("F7:11:95:C5:14:9B", mock=True)
        conn_events = []
        telem_events = []

        def _on_conn(c):
            conn_events.append(c)

        def _on_telem(t):
            telem_events.append(t.live_temp_f)

        client.add_connection_listener(_on_conn)
        client.add_telemetry_listener(_on_telem)

        try:
            client.start()
            self.assertTrue(client.wait_connected(timeout=5.0))
            time.sleep(0.3)

            self.assertIn(True, conn_events)
            self.assertGreater(len(telem_events), 0)

            # Test listener removal
            client.remove_connection_listener(_on_conn)
            client.remove_telemetry_listener(_on_telem)
        finally:
            client.stop()

    def test_sync_commands(self):
        """Verify synchronous session control methods forward to background loop."""
        client = ThreadedPuffcoClient("F7:11:95:C5:14:9B", mock=True)
        try:
            client.start()
            self.assertTrue(client.wait_connected(timeout=5.0))

            # 1. Start Session
            fut = client.start_session()
            if fut:
                fut.result(timeout=2.0)
            self.assertEqual(client.telemetry.operating_state, OperatingState.HEAT_PREHEAT)

            # 2. Boost
            fut = client.boost()
            if fut:
                fut.result(timeout=2.0)

            # 3. Stop Session
            fut = client.stop_session()
            if fut:
                fut.result(timeout=2.0)
            self.assertEqual(client.telemetry.operating_state, OperatingState.IDLE)

            # 4. Set Profile
            fut = client.set_profile(0)
            if fut:
                fut.result(timeout=2.0)
            self.assertEqual(client.telemetry.active_profile, 0)

            # 5. Set Temperature
            fut = client.set_temperature(475.0)
            if fut:
                fut.result(timeout=2.0)
            self.assertEqual(client.telemetry.target_temp_f, 475.0)

            # 6. Stealth Mode
            fut = client.set_stealth_mode(True)
            if fut:
                fut.result(timeout=2.0)
            self.assertTrue(client.telemetry.stealth_mode)

            # 7. Lantern
            fut = client.set_lantern(True)
            if fut:
                fut.result(timeout=2.0)
            fut = client.set_lantern(False)
            if fut:
                fut.result(timeout=2.0)

            # 8. Set Profile Duration & Name
            fut = client.set_profile_duration(1, 55)
            if fut:
                fut.result(timeout=2.0)
            self.assertEqual(client.telemetry.profiles[1].duration_s, 55)

            fut = client.set_profile_name(1, "MELT")
            if fut:
                fut.result(timeout=2.0)
            self.assertEqual(client.telemetry.profiles[1].name, "MELT")

            # 9. Save Profile
            prof = PuffcoProfile(slot=3, name="WATER HASH", target_temp_f=460, duration_s=40)
            fut = client.save_profile(3, prof)
            if fut:
                self.assertTrue(fut.result(timeout=2.0))
            self.assertEqual(client.telemetry.profiles[3].name, "WATER HASH")

            # 10. Boost Settings
            fut = client.set_boost_temperature(25.0)
            if fut:
                fut.result(timeout=2.0)
            self.assertEqual(client.telemetry.boost_temp_f, 25)

            fut = client.set_boost_duration(20)
            if fut:
                fut.result(timeout=2.0)
            self.assertEqual(client.telemetry.boost_duration_s, 20)

        finally:
            client.stop()

    def test_disconnect_and_reconnect(self):
        """Verify disconnect clears connection and reconnect restores it."""
        client = ThreadedPuffcoClient("F7:11:95:C5:14:9B", mock=True)
        try:
            client.start()
            self.assertTrue(client.wait_connected(timeout=5.0))
            self.assertTrue(client.is_connected)

            client.disconnect()
            time.sleep(0.1)
            self.assertFalse(client.is_connected)

            client.reconnect()
            self.assertTrue(client.wait_connected(timeout=5.0))
            self.assertTrue(client.is_connected)
        finally:
            client.stop()


if __name__ == "__main__":
    unittest.main()
