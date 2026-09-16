"""
Example 04: Minimal macOS Menu Bar Widget (rumps + ThreadedPuffcoClient)

Displays live bowl temperature and battery percentage in the macOS menu bar,
with quick menu shortcuts to trigger heat sessions and switch profiles.

Requires:
    pip install rumps puffco-py
"""

import sys

try:
    import rumps
except ImportError:
    print("This example requires 'rumps'. Install with: pip install rumps")
    sys.exit(1)

from puffco_py import OperatingState, ThreadedPuffcoClient


class PuffcoMenuBarApp(rumps.App):
    def __init__(self):
        super().__init__("Puffco", title="Puffco: Connecting...")
        self.client = ThreadedPuffcoClient()
        self.client.add_telemetry_listener(self._on_telemetry)

        # Menu items
        self.status_item = rumps.MenuItem("Status: Initializing...")
        self.battery_item = rumps.MenuItem("Battery: --%")
        self.chamber_item = rumps.MenuItem("Chamber: --")
        self.dabs_item = rumps.MenuItem("Total Dabs: --")

        self.start_btn = rumps.MenuItem("🚀 Start Heat Sesh", callback=self._on_start)
        self.stop_btn = rumps.MenuItem("🛑 Abort Sesh", callback=self._on_stop)
        self.boost_btn = rumps.MenuItem("⚡ Boost Heat", callback=self._on_boost)

        self.menu = [
            self.status_item,
            self.battery_item,
            self.chamber_item,
            self.dabs_item,
            None,  # Separator
            self.start_btn,
            self.boost_btn,
            self.stop_btn,
        ]

        self.client.start()

    def _on_telemetry(self, t):
        if not t.connected:
            self.title = "Puffco: Offline"
            self.status_item.title = "Status: Disconnected"
            return

        if t.is_heating:
            self.title = f"🔥 {t.live_temp_f:.0f}°F ({t.time_remaining}s)"
        else:
            self.title = f"💨 {t.live_temp_f:.0f}°F | {t.battery_pct}%"

        self.status_item.title = f"Status: {t.state_name}"
        self.battery_item.title = f"Battery: {t.battery_pct}%{' (⚡)' if t.is_charging else ''}"
        self.chamber_item.title = f"Chamber: {t.chamber_name}"
        self.dabs_item.title = f"Total Dabs: {t.lifetime_dabs:,}"

    def _on_start(self, _):
        self.client.start_session()

    def _on_stop(self, _):
        self.client.stop_session()

    def _on_boost(self, _):
        self.client.boost()


if __name__ == "__main__":
    PuffcoMenuBarApp().run()
