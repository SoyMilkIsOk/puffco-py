"""
Example 03: Threaded Client (Synchronous GUI / Script Integration)

Demonstrates using ThreadedPuffcoClient to run the BLE engine on a background worker
thread, allowing simple synchronous method calls and callbacks from the main thread.
"""

import sys
import time
from pathlib import Path

# Ensure parent directory is in sys.path when running from source or subfolder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from puffco_py import ThreadedPuffcoClient


def main():
    print("Starting threaded background worker...")
    client = ThreadedPuffcoClient()

    # Register live telemetry callback
    def on_telemetry(t):
        print(f"\r[BG Worker] Temp: {t.live_temp_f:.1f}°F | Bat: {t.battery_pct}%", end="")

    client.add_telemetry_listener(on_telemetry)
    client.start()

    print("Waiting for BLE connection (up to 15s)...")
    if not client.wait_connected(timeout=15.0):
        print("Failed to connect. Exiting.")
        client.stop()
        return

    print(f"\nConnected to {client.telemetry.device_name}!")
    print(
        f"Chamber: {client.telemetry.chamber_name} | Total Dabs: {client.telemetry.lifetime_dabs}"
    )

    # Synchronous control methods (thread-safe)
    time.sleep(3)
    print("\nSetting profile to Slot 0 from main thread...")
    client.set_profile(0)

    # Let worker stream updates for 10 seconds
    time.sleep(10)

    print("\nStopping client...")
    client.stop()
    print("Done!")


if __name__ == "__main__":
    main()
