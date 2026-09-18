"""
Unit tests for puffco-py command-line interface and offline --mock mode.
"""

import argparse
import unittest
from unittest.mock import patch

from puffco_py.cli import (
    _make_battery_bar,
    _render_monitor_dashboard,
    cmd_info,
    cmd_scan,
    cmd_sesh,
    main,
)
from puffco_py.models import ChamberType, OperatingState, PuffcoTelemetry


class TestCLI(unittest.TestCase):
    def test_battery_bar_formatting(self):
        """Verify ASCII / Unicode battery bar color and progress."""
        bar_high = _make_battery_bar(85)
        self.assertIn("85%", bar_high)
        self.assertIn("green", bar_high)

        bar_med = _make_battery_bar(35)
        self.assertIn("35%", bar_med)
        self.assertIn("yellow", bar_med)

        bar_low = _make_battery_bar(12)
        self.assertIn("12%", bar_low)
        self.assertIn("red", bar_low)

    def test_render_monitor_dashboard_states(self):
        """Verify terminal HUD panel renders for all operating states."""
        t = PuffcoTelemetry()
        t.device_name = "Test Peak Pro"
        t.mac_address = "F7:11:95:C5:14:9B"
        t.battery_pct = 80
        t.chamber_type = ChamberType.CHAMBER_3DXL
        t.live_temp_f = 490.0
        t.target_temp_f = 490.0

        for st in [
            OperatingState.IDLE,
            OperatingState.HEAT_PREHEAT,
            OperatingState.HEAT_ACTIVE,
            OperatingState.HEAT_FADE,
            OperatingState.SLEEP,
            OperatingState.DISCONNECTED,
        ]:
            t.operating_state = st
            panel = _render_monitor_dashboard(t)
            self.assertIsNotNone(panel)

    def test_cli_scan_mock(self):
        """Verify puffco-py scan --mock returns discovered simulated devices."""
        args = argparse.Namespace(command="scan", timeout=0.1, mock=True)
        # Verify cmd_scan runs without crashing
        cmd_scan(args)

    def test_cli_info_mock(self):
        """Verify puffco-py info --mock retrieves simulated device diagnostics."""
        args = argparse.Namespace(command="info", mac=None, mock=True)
        # Verify cmd_info runs without crashing
        cmd_info(args)

    def test_cli_sesh_mock(self):
        """Verify puffco-py sesh <action> --mock executes against simulated hardware."""
        for action in ["start", "boost", "stop"]:
            args = argparse.Namespace(command="sesh", action=action, mac=None, mock=True)
            cmd_sesh(args)

    def test_cli_main_argparse(self):
        """Verify main() argument parser handles commands and flags."""
        with patch("sys.argv", ["puffco-py", "info", "--mock"]):
            with patch("puffco_py.cli.cmd_info") as mock_info:
                main()
                mock_info.assert_called_once()
                self.assertTrue(mock_info.call_args[0][0].mock)

        with patch("sys.argv", ["puffco-py", "monitor", "--mock", "--mac", "F7:11:95:C5:14:9B"]):
            with patch("puffco_py.cli.cmd_monitor") as mock_mon:
                main()
                mock_mon.assert_called_once()
                self.assertTrue(mock_mon.call_args[0][0].mock)
                self.assertEqual(mock_mon.call_args[0][0].mac, "F7:11:95:C5:14:9B")

        with patch("sys.argv", ["puffco-py", "sesh", "start", "--mock"]):
            with patch("puffco_py.cli.cmd_sesh") as mock_sesh:
                main()
                mock_sesh.assert_called_once()
                self.assertEqual(mock_sesh.call_args[0][0].action, "start")
                self.assertTrue(mock_sesh.call_args[0][0].mock)


if __name__ == "__main__":
    unittest.main()
