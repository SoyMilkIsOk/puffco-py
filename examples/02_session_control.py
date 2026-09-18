"""
Example 02: Session Control & Profile Management

Demonstrates how to select heat profiles, start a sesh, boost temperature,
and toggle stealth mode.
"""

import asyncio
from pathlib import Path
import sys
import time

# Ensure parent directory is in sys.path when running from source or subfolder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from puffco_py import PuffcoClient, OperatingState


async def main():
    async with PuffcoClient() as client:
        print(f"Connected to {client.telemetry.device_name} ({client.telemetry.mac_address})")

        # 1. Print available profiles
        print("\nAvailable Profiles:")
        for p in client.telemetry.profiles:
            print(f"  {p}")

        # 2. Select Profile 2 (Slot 1)
        print("\nSelecting Profile Slot 1...")
        await client.set_profile(slot=1)
        print(f"Active Profile Target: {client.telemetry.target_temp_f}°F")

        # 3. Toggle Stealth Mode
        print("\nToggling Stealth Mode ON...")
        await client.set_stealth_mode(True)
        await asyncio.sleep(2)
        print("Toggling Stealth Mode OFF...")
        await client.set_stealth_mode(False)

        # 4. Optional: Start a session
        # Uncomment below to trigger heat:
        # print("\nStarting heat session...")
        # await client.start_session()
        # await asyncio.sleep(10)
        # print("Boosting session (+15s / +10°F)...")
        # await client.boost()
        # await asyncio.sleep(10)
        # print("Stopping session...")
        # await client.stop_session()


if __name__ == "__main__":
    asyncio.run(main())
