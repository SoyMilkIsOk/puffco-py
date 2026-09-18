"""
Example 01: Quickstart Live Telemetry

Connects to the nearest Puffco Peak Pro or Proxy and prints live bowl temperature,
battery percentage, and session countdown in real-time.
"""

import asyncio
import sys
from pathlib import Path

# Ensure parent directory is in sys.path when running from source or subfolder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from puffco_py import PuffcoClient


async def main():
    print("Connecting to nearest Puffco device...")
    async with PuffcoClient() as client:
        print(f"Connected to {client.telemetry.device_name}!")
        print(f"Chamber: {client.telemetry.chamber_name} | Dabs: {client.telemetry.lifetime_dabs}")
        print("-" * 50)

        # Register callback for live telemetry updates
        def on_update(telemetry):
            status = "🔥 Heating" if telemetry.is_heating else "💤 Idle"
            print(
                f"\r[{status}] Live: {telemetry.live_temp_f:.1f}°F | "
                f"Target: {telemetry.target_temp_f:.0f}°F | "
                f"Battery: {telemetry.battery_pct}%",
                end="",
                flush=True,
            )

        client.add_telemetry_listener(on_update)

        # Start low-latency stream (60ms sesh / 250ms standby)
        await client.start_telemetry_stream()

        # Run for 30 seconds
        await asyncio.sleep(30)
        print("\nSession complete. Disconnecting.")


if __name__ == "__main__":
    asyncio.run(main())
