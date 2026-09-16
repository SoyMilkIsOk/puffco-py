"""
Command-line interface (CLI) for puffco-ble.
"""

import argparse
import asyncio
import sys
import time

try:
    from .client import PuffcoClient
    from .discovery import scan_puffco_devices
except ImportError:
    from puffco_ble.client import PuffcoClient
    from puffco_ble.discovery import scan_puffco_devices


def cmd_scan(args):
    """Scans for nearby Puffco devices."""
    print("🔍 Scanning for Puffco Peak Pro & Proxy devices (5s)...")
    devices = asyncio.run(scan_puffco_devices(timeout=args.timeout))
    if not devices:
        print("❌ No Puffco devices found. Make sure your device is powered on.")
        return

    print(f"\n🎉 Found {len(devices)} device(s):")
    print("=" * 60)
    for i, dev in enumerate(devices, 1):
        print(f"[{i}] {dev.name:<24} | MAC: {dev.address:<18} | RSSI: {dev.rssi} dBm")
    print("=" * 60)


def cmd_info(args):
    """Prints full device diagnostics and profiles."""
    async def _run():
        async with PuffcoClient(args.mac) as client:
            t = client.telemetry
            print("\n" + "=" * 50)
            print(f" DEVICE: {t.device_name} ({t.mac_address})")
            print("=" * 50)
            print(f" Serial:       {t.serial_number or 'N/A'}")
            print(f" Firmware:     {t.firmware_version or 'N/A'}")
            print(f" Battery:      {t.battery_pct}% {'(Charging ⚡)' if t.is_charging else ''}")
            print(f" Chamber:      {t.chamber_name}")
            print(f" Total Dabs:   {t.lifetime_dabs:,}")
            print(f" State:        {t.state_name}")
            print(f" Live Temp:    {t.live_temp_f:.1f}°F")
            print(f" Stealth Mode: {'Enabled' if t.stealth_mode else 'Disabled'}")
            print("\n Profiles:")
            for p in t.profiles:
                marker = " -> " if p.slot == t.active_profile else "    "
                print(f"{marker}[Slot {p.slot}] {p.name:<18} {p.target_temp_f}°F ({p.duration_s}s)")
            print("=" * 50)

    asyncio.run(_run())


def cmd_monitor(args):
    """Live streaming terminal monitor."""
    async def _run():
        print(f"Connecting to Puffco ({args.mac or 'auto-discover'})...")
        async with PuffcoClient(args.mac) as client:
            print(f"Connected to {client.telemetry.device_name}! Press Ctrl+C to stop.\n")

            await client.start_telemetry_stream(interval_heating=0.06, interval_idle=0.25)
            try:
                while True:
                    t = client.telemetry
                    line = f"\r{t.summary():<80}"
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                print("\nStopping monitor...")

    asyncio.run(_run())


def cmd_sesh(args):
    """Triggers session control commands."""
    action = args.action.lower()

    async def _run():
        async with PuffcoClient(args.mac) as client:
            if action == "start":
                print(f"🚀 Starting sesh on {client.telemetry.device_name}...")
                await client.start_session()
            elif action == "stop":
                print(f"🛑 Aborting sesh on {client.telemetry.device_name}...")
                await client.stop_session()
            elif action == "boost":
                print(f"⚡ Boosting heat on {client.telemetry.device_name}...")
                await client.boost()
            else:
                print(f"Unknown action: {action}")
                return
            await asyncio.sleep(1.0)
            print("Done!")

    asyncio.run(_run())


def main():
    parser = argparse.ArgumentParser(
        prog="puffco-ble",
        description="Puffco Peak Pro & Proxy BLE Command Line Tool",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scan
    p_scan = subparsers.add_parser("scan", help="Scan for nearby Puffco devices")
    p_scan.add_argument("-t", "--timeout", type=float, default=5.0, help="Scan timeout in seconds")

    # Info
    p_info = subparsers.add_parser("info", help="Display device diagnostics and heat profiles")
    p_info.add_argument("--mac", type=str, default=None, help="Device MAC address or UUID")

    # Monitor
    p_mon = subparsers.add_parser("monitor", help="Stream real-time telemetry to terminal")
    p_mon.add_argument("--mac", type=str, default=None, help="Device MAC address or UUID")

    # Sesh
    p_sesh = subparsers.add_parser("sesh", help="Trigger heat sesh commands")
    p_sesh.add_argument("action", choices=["start", "stop", "boost"], help="Action to execute")
    p_sesh.add_argument("--mac", type=str, default=None, help="Device MAC address or UUID")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "sesh":
        cmd_sesh(args)


if __name__ == "__main__":
    main()
