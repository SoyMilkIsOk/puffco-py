#!/usr/bin/env python3
"""
Example 04: macOS Menu Bar Widget (rumps + ThreadedPuffcoClient)

A native macOS status bar menu widget for Puffco Peak Pro and Proxy devices.
Features:
  - Interactive BLE device scanner to discover and pair devices directly from the menu bar
  - Rock-solid main-thread UI dispatch to prevent macOS Cocoa hangs/crashes
  - Auto-discovery on startup with instant connection to the strongest device
  - One-click session controls (Start Heat, Boost, Abort)
  - Heat profile switcher (Slots 1-4 with temperatures & durations)
  - Live bowl temperature and battery percentage in the system status bar
  - Native macOS desktop notifications for heating ready & completion
  - Stealth and lantern lighting controls

Requires:
    pip install ".[gui]"  # or: pip install rumps bleak
"""

import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional

# Ensure parent directory is in sys.path when running from source or subfolder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import rumps
except ImportError:
    print("\n❌ Missing required dependency 'rumps'.")
    print("Install GUI requirements with:")
    print("    pip install '.[gui]'   # or: pip install rumps bleak\n")
    sys.exit(1)

try:
    import bleak  # noqa: F401
except ImportError:
    print("\n❌ Missing required dependency 'bleak'.")
    print("Install BLE requirements with:")
    print("    pip install '.[gui]'   # or: pip install rumps bleak\n")
    sys.exit(1)

from puffco_py import OperatingState, PuffcoDiscoveredDevice, PuffcoTelemetry, ThreadedPuffcoClient


class PuffcoMenuBarApp(rumps.App):
    def __init__(self):
        super().__init__("Puffco", title="💨 Puffco: Starting...")
        self.client = ThreadedPuffcoClient()
        self.client.add_telemetry_listener(self._on_telemetry_bg)

        self.current_address: Optional[str] = None
        self.current_device_name: str = "Puffco Device"
        self.discovered_devices: List[PuffcoDiscoveredDevice] = []

        # Thread-safe flags and queues for main-thread UI timer
        self._latest_telemetry: Optional[PuffcoTelemetry] = None
        self._pending_devices_update: Optional[List[PuffcoDiscoveredDevice]] = None
        self._is_scanning = False
        self._was_heating = False
        self._was_connected = False

        # --- Menu Items ---
        # 1. Telemetry & Hardware Diagnostics
        self.device_title_item = rumps.MenuItem("Device: Searching...")
        self.status_item = rumps.MenuItem("Status: Scanning for nearby Puffco...")
        self.temp_item = rumps.MenuItem("Temp: --°F")
        self.battery_item = rumps.MenuItem("Battery: --%")
        self.chamber_item = rumps.MenuItem("Chamber: --")
        self.dabs_item = rumps.MenuItem("Total Dabs: --")

        # 2. Session Controls
        self.start_btn = rumps.MenuItem("🚀 Start Heat Sesh", callback=self._on_start)
        self.boost_btn = rumps.MenuItem("⚡ Boost Heat (+15s / +10°F)", callback=self._on_boost)
        self.stop_btn = rumps.MenuItem("🛑 Abort Sesh", callback=self._on_stop)

        # 3. Heat Profiles Submenu
        self.profiles_menu = rumps.MenuItem("🎨 Heat Profiles")
        self.profiles_menu.add(rumps.MenuItem("(Profiles load once connected)"))
        self._profile_slot_items: Dict[int, rumps.MenuItem] = {}

        # 4. Settings & Lighting Submenu
        self.settings_menu = rumps.MenuItem("⚙️ Controls & Lighting")
        self.stealth_item = rumps.MenuItem("💡 Stealth Mode", callback=self._on_toggle_stealth)
        self.lantern_item = rumps.MenuItem("🏮 Lantern Mode", callback=self._on_toggle_lantern)
        self.settings_menu.add(self.stealth_item)
        self.settings_menu.add(self.lantern_item)

        # 5. Devices & Scanner Submenu
        self.devices_menu = rumps.MenuItem("📡 Devices & Pairing")
        self.scan_btn = rumps.MenuItem("🔍 Scan for Nearby Devices", callback=self._on_scan_clicked)
        self.manual_connect_btn = rumps.MenuItem(
            "✏️ Connect via MAC / UUID...", callback=self._on_manual_connect
        )
        self.disconnect_btn = rumps.MenuItem("🔌 Disconnect Device", callback=self._on_disconnect)
        self.devices_menu.add(self.scan_btn)
        self.devices_menu.add(self.manual_connect_btn)
        self.devices_menu.add(None)
        self.devices_placeholder = rumps.MenuItem("(Scanning nearby devices...)")
        self.devices_menu.add(self.devices_placeholder)

        # Assemble Full Menu
        self.menu = [
            self.device_title_item,
            self.status_item,
            self.temp_item,
            self.battery_item,
            self.chamber_item,
            self.dabs_item,
            None,  # Separator
            self.start_btn,
            self.boost_btn,
            self.stop_btn,
            None,  # Separator
            self.profiles_menu,
            self.settings_menu,
            self.devices_menu,
        ]

        # Start persistent BLE worker
        self.client.start()

        # Start main-thread UI timer (runs on Cocoa main runloop at 4 Hz)
        self._ui_timer = rumps.Timer(self._on_ui_tick, 0.25)
        self._ui_timer.start()

        # Launch initial background scan and auto-connect
        self._start_scan(auto_connect=True)

    # ==========================================
    # MAIN-THREAD UI DISPATCH TIMER
    # ==========================================
    def _on_ui_tick(self, _):
        """Dispatches all UI and NSMenu updates on the macOS Cocoa main thread."""
        # 1. Check for pending device scanner results
        if self._pending_devices_update is not None:
            devs = self._pending_devices_update
            self._pending_devices_update = None
            self._render_devices_menu_on_main(devs)

        # 2. Check for latest telemetry from BLE worker
        t = self._latest_telemetry
        if t is None:
            return

        if not t.connected:
            if self._was_connected:
                self._was_connected = False
                self.title = "💨 Offline"
                self.device_title_item.title = "Device: Offline"
                self.status_item.title = "Status: Disconnected"
                self.temp_item.title = "Temp: --°F"
                self.battery_item.title = "Battery: --%"
                self.chamber_item.title = "Chamber: --"
                self.dabs_item.title = "Total Dabs: --"
                self._render_devices_menu_on_main(self.discovered_devices)
            return

        # Newly connected event
        if not self._was_connected:
            self._was_connected = True
            self.current_device_name = t.device_name
            self.current_address = t.mac_address or self.current_address
            self._render_devices_menu_on_main(self.discovered_devices)
            try:
                rumps.notification(
                    title="Puffco Connected",
                    subtitle=t.device_name,
                    message=f"Chamber: {t.chamber_name} | Battery: {t.battery_pct}%",
                )
            except Exception:
                pass

        # Update Menu Bar Title
        if t.is_heating:
            self.title = f"🔥 {t.live_temp_f:.0f}°F ({t.time_remaining}s)"
        elif t.operating_state == OperatingState.READY:
            self.title = f"💨 Ready ({t.live_temp_f:.0f}°F)"
        else:
            self.title = f"💨 {t.live_temp_f:.0f}°F | {t.battery_pct}%"

        # Heating Ready Notification
        if t.operating_state == OperatingState.READY and not self._was_heating:
            try:
                rumps.notification(
                    title="Puffco Ready! 🔥",
                    subtitle=f"{t.device_name} reached {t.target_temp_f:.0f}°F",
                    message=f"Chamber: {t.chamber_name} | Time: {t.time_remaining}s",
                )
            except Exception:
                pass
        self._was_heating = t.is_heating

        # Update Telemetry Labels
        self.device_title_item.title = f"Device: {t.device_name}"
        self.status_item.title = f"Status: {t.state_name}"
        self.battery_item.title = (
            f"Battery: {t.battery_pct}%{' (⚡ Charging)' if t.is_charging else ''}"
        )
        self.chamber_item.title = f"Chamber: {t.chamber_name}"
        self.temp_item.title = f"Temp: {t.live_temp_f:.1f}°F (Target: {t.target_temp_f:.0f}°F)"
        self.dabs_item.title = f"Total Dabs: {t.lifetime_dabs:,}"

        # Update Profiles Submenu
        self._render_profiles_on_main(t)

        # Update Settings toggles
        self.stealth_item.state = 1 if t.stealth_mode else 0

    # ==========================================
    # BACKGROUND TELEMETRY LISTENER
    # ==========================================
    def _on_telemetry_bg(self, t: PuffcoTelemetry):
        """Called from BLE background thread - store state for main thread render."""
        self._latest_telemetry = t

    # ==========================================
    # DEVICE SCANNING & PAIRING (MAIN THREAD RENDER)
    # ==========================================
    def _render_devices_menu_on_main(self, devices: List[PuffcoDiscoveredDevice]):
        """Reconstructs the Devices submenu safely on the Cocoa main thread."""
        self.discovered_devices = devices
        self.devices_menu.clear()
        self.devices_menu.add(self.scan_btn)
        self.devices_menu.add(self.manual_connect_btn)
        if self.client.is_connected:
            self.devices_menu.add(self.disconnect_btn)
        self.devices_menu.add(None)  # Separator

        if self._is_scanning:
            self.devices_menu.add(rumps.MenuItem("⏳ Scanning nearby devices..."))
            return

        if not devices:
            self.devices_menu.add(rumps.MenuItem("(No Puffco devices found nearby)"))
            return

        # Add each discovered device
        for dev in devices:
            is_active = bool(
                self.current_address
                and self.current_address.upper() == dev.address.upper()
                and self.client.is_connected
            )
            item_title = f"{'✓ ' if is_active else ''}{dev.name} ({dev.rssi} dBm)"

            def _make_handler(target_addr, target_name):
                return lambda sender: self._connect_to(target_addr, target_name)

            dev_item = rumps.MenuItem(item_title, callback=_make_handler(dev.address, dev.name))
            dev_item.state = 1 if is_active else 0
            self.devices_menu.add(dev_item)

    def _render_profiles_on_main(self, t: PuffcoTelemetry):
        """Renders heat profiles safely on the Cocoa main thread."""
        if not t.profiles:
            return

        current_slots = list(self._profile_slot_items.keys())
        needed_slots = [p.slot for p in t.profiles]

        if current_slots != needed_slots:
            self.profiles_menu.clear()
            self._profile_slot_items.clear()
            for p in t.profiles:

                def _make_slot_handler(slot_idx):
                    return lambda sender: self.client.set_profile(slot_idx)

                label = f"Slot {p.slot + 1}: {p.name} ({p.target_temp_f}°F, {p.duration_s}s)"
                item = rumps.MenuItem(label, callback=_make_slot_handler(p.slot))
                self._profile_slot_items[p.slot] = item
                self.profiles_menu.add(item)

        for slot, item in self._profile_slot_items.items():
            item.state = 1 if slot == t.active_profile else 0

    # ==========================================
    # SCANNER ACTIONS
    # ==========================================
    def _on_scan_clicked(self, _):
        if not self._is_scanning:
            self._start_scan(auto_connect=False)

    def _start_scan(self, auto_connect: bool = False):
        """Runs a background BLE scan without blocking the macOS main thread."""
        self._is_scanning = True
        self.scan_btn.title = "🔍 Scanning for Devices... ⏳"
        if not self.client.is_connected:
            self.title = "🔍 Scanning..."
            self.status_item.title = "Status: Scanning for nearby Puffco..."

        def _worker():
            try:
                found = self.client.scan_devices(timeout=4.0)
            except Exception as e:
                print(f"Scan error: {e}")
                found = []

            self._is_scanning = False
            self.scan_btn.title = "🔍 Scan for Nearby Devices"
            self._pending_devices_update = found

            if found:
                top_dev = found[0]
                try:
                    rumps.notification(
                        title="Puffco Scanner",
                        subtitle=f"Found {len(found)} device(s)",
                        message=f"Discovered {top_dev.name} ({top_dev.rssi} dBm)",
                    )
                except Exception:
                    pass

                # Auto-connect if not currently connected
                if auto_connect and not self.client.is_connected:
                    self._connect_to(top_dev.address, top_dev.name)
            else:
                if not self.client.is_connected:
                    self.title = "💨 Offline"
                    self.status_item.title = "Status: No Puffco devices found"

        threading.Thread(target=_worker, daemon=True).start()

    def _connect_to(self, address: str, name: Optional[str] = None):
        """Connects to a specific device address or UUID."""
        self.current_address = address
        display_name = name or address
        self.current_device_name = display_name
        self.title = "⏳ Connecting..."
        self.device_title_item.title = f"Device: {display_name}"
        self.status_item.title = f"Status: Connecting to {display_name}..."
        self.client.reconnect(address)

    def _on_manual_connect(self, _):
        """Prompts for Bluetooth MAC address or macOS UUID."""
        win = rumps.Window(
            message="Enter device Bluetooth MAC address or macOS UUID:\n(e.g., F71195C5-149B-5A18-54F0-69BFB3CB217C)",
            title="Connect to Puffco Device",
            default_text=self.current_address or "",
            ok="Connect",
            cancel="Cancel",
            dimensions=(340, 90),
        )
        resp = win.run()
        if resp.clicked and resp.text.strip():
            self._connect_to(resp.text.strip())

    def _on_disconnect(self, _):
        """Disconnects current device."""
        self.client.disconnect()
        self.current_address = None
        self.title = "💨 Offline"
        self.device_title_item.title = "Device: Offline"
        self.status_item.title = "Status: Disconnected"

    # ==========================================
    # SESSION & LIGHTING ACTIONS
    # ==========================================
    def _on_start(self, _):
        self.client.start_session()

    def _on_stop(self, _):
        self.client.stop_session()

    def _on_boost(self, _):
        self.client.boost()

    def _on_toggle_stealth(self, sender):
        new_val = not (sender.state == 1)
        sender.state = 1 if new_val else 0
        self.client.set_stealth_mode(new_val)

    def _on_toggle_lantern(self, sender):
        new_val = not (sender.state == 1)
        sender.state = 1 if new_val else 0
        self.client.set_lantern(new_val)


if __name__ == "__main__":
    PuffcoMenuBarApp().run()
