"""
Command-line interface (CLI) for puffco-py.
Includes rich interactive terminal HUDs for device monitoring, scanning, diagnostics, and session control.
"""

import argparse
import asyncio
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress_bar import ProgressBar
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
else:
    try:
        from rich.console import Console
        from rich.live import Live
        from rich.panel import Panel
        from rich.progress_bar import ProgressBar
        from rich.table import Table
        from rich.text import Text

        RICH_AVAILABLE = True
    except ImportError:
        Console = None
        Live = None
        Panel = None
        ProgressBar = None
        Table = None
        Text = None
        RICH_AVAILABLE = False

try:
    from .client import PuffcoClient
    from .discovery import scan_puffco_devices
    from .exceptions import PuffcoError
    from .mock import MockBleakScanner, MockPuffcoClient
    from .models import OperatingState, PuffcoTelemetry
except ImportError:
    from puffco_py.client import PuffcoClient
    from puffco_py.discovery import scan_puffco_devices
    from puffco_py.exceptions import PuffcoError
    from puffco_py.mock import MockBleakScanner, MockPuffcoClient
    from puffco_py.models import OperatingState, PuffcoTelemetry


console = Console() if RICH_AVAILABLE else None


# ==========================================
# RICH DASHBOARD RENDERERS
# ==========================================
def _make_battery_bar(pct: int) -> str:
    filled = max(0, min(10, pct // 10))
    bar = "█" * filled + "░" * (10 - filled)
    if pct > 50:
        color = "green"
    elif pct > 20:
        color = "yellow"
    else:
        color = "red"
    return f"[{color}]{bar}[/{color}] {pct}%"


def _render_monitor_dashboard(t: PuffcoTelemetry):
    if not RICH_AVAILABLE or Table is None:
        return t.summary()

    state_badges = {
        OperatingState.IDLE: "[bold green]● READY / IDLE[/bold green]",
        OperatingState.HEAT_PREHEAT: "[bold yellow]▲ PREHEATING...[/bold yellow]",
        OperatingState.HEAT_ACTIVE: "[bold bright_red]🔥 HEATING ACTIVE[/bold bright_red]",
        OperatingState.HEAT_FADE: "[bold dark_orange]▼ FADING / COOLING[/bold dark_orange]",
        OperatingState.DISCONNECTED: "[bold dim red]✖ DISCONNECTED[/bold dim red]",
        OperatingState.SLEEP: "[bold dim blue]💤 SLEEPING[/bold dim blue]",
    }
    state_str = state_badges.get(t.operating_state, f"[bold]{t.state_name}[/bold]")

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column("left", ratio=1)
    grid.add_column("right", ratio=1)

    # Left: Session & Heat
    left_table = Table(box=None, show_header=False, pad_edge=False)
    left_table.add_column("Key", style="dim", width=16)
    left_table.add_column("Value")

    temp_color = "bright_red" if t.is_heating else ("cyan" if t.live_temp_f > 100 else "white")
    left_table.add_row("Status", state_str)
    left_table.add_row(
        "Live Bowl Temp", f"[bold {temp_color}]{t.live_temp_f:.1f}°F[/bold {temp_color}]"
    )
    left_table.add_row("Target Temp", f"[bold cyan]{t.target_temp_f:.0f}°F[/bold cyan]")

    if t.is_heating and t.total_time > 0:
        countdown_text = f"[bold yellow]{t.time_remaining}s[/bold yellow] / {t.total_time}s"
        left_table.add_row("Countdown", countdown_text)
        bar = ProgressBar(
            total=t.total_time, completed=max(0, t.total_time - t.time_remaining), width=22
        )
        left_table.add_row("Sesh Progress", bar)
    else:
        left_table.add_row("Countdown", "[dim]Standby / Ready[/dim]")

    # Right: Hardware & Diagnostics
    right_table = Table(box=None, show_header=False, pad_edge=False)
    right_table.add_column("Key", style="dim", width=16)
    right_table.add_column("Value")

    chg = " [bold green]⚡ Charging[/bold green]" if t.is_charging else ""
    right_table.add_row("Battery", f"{_make_battery_bar(t.battery_pct)}{chg}")
    right_table.add_row("Chamber", f"[bold magenta]{t.chamber_name}[/bold magenta]")
    right_table.add_row("Total Dabs", f"[bold white]{t.lifetime_dabs:,}[/bold white]")
    right_table.add_row(
        "Stealth Mode", "[green]Enabled[/green]" if t.stealth_mode else "[dim]Disabled[/dim]"
    )

    if t.profiles and 0 <= t.active_profile < len(t.profiles):
        p = t.profiles[t.active_profile]
        right_table.add_row(
            "Active Profile",
            f"[bold cyan]{p.name}[/bold cyan] ({p.target_temp_f}°F, {p.duration_s}s)",
        )
    else:
        right_table.add_row("Active Profile", f"Slot {t.active_profile + 1}")

    left_border = "yellow" if t.is_heating else "blue"
    grid.add_row(
        Panel(left_table, title="[bold]Session & Heat[/bold]", border_style=left_border),
        Panel(right_table, title="[bold]Device Diagnostics[/bold]", border_style="cyan"),
    )

    header_title = (
        f"[bold cyan]💨 puffco-py[/bold cyan] [bold white]Telemetry Monitor[/bold white] — "
        f"[bold green]{t.device_name}[/bold green] [dim]({t.mac_address or 'BLE'})[/dim]"
    )
    footer = "[dim]Press [bold]Ctrl+C[/bold] to exit | Sub-100ms Lorax BLE Streaming[/dim]"
    return Panel(
        grid, title=header_title, subtitle=footer, border_style="bright_blue", padding=(0, 1)
    )


# ==========================================
# COMMAND IMPLEMENTATIONS
# ==========================================
def cmd_scan(args):
    """Scans for nearby Puffco devices."""
    is_mock = getattr(args, "mock", False)
    if is_mock:
        if RICH_AVAILABLE:
            console.print(
                "\n🔍 [bold cyan]Scanning for simulated Puffco devices (--mock)[/bold cyan]..."
            )
        else:
            print("🔍 Scanning for simulated Puffco devices (--mock)...")
    elif RICH_AVAILABLE:
        console.print(
            "\n🔍 [bold cyan]Scanning for Puffco Peak Pro & Proxy devices[/bold cyan] (5s timeout)..."
        )
    else:
        print("🔍 Scanning for Puffco Peak Pro & Proxy devices (5s)...")

    try:
        if is_mock:
            from unittest.mock import patch

            with patch("puffco_py.discovery.BleakScanner", MockBleakScanner):
                devices = asyncio.run(scan_puffco_devices(timeout=0.1))
        else:
            devices = asyncio.run(scan_puffco_devices(timeout=args.timeout))
    except PuffcoError as e:
        if RICH_AVAILABLE:
            console.print(f"[bold red]❌ Scan Error:[/bold red] {e}")
        else:
            print(f"❌ Scan Error: {e}")
        return

    if not devices:
        msg = "❌ No Puffco devices found. Ensure your device is powered on and within range."
        if RICH_AVAILABLE:
            console.print(f"[bold yellow]{msg}[/bold yellow]")
        else:
            print(msg)
        return

    if RICH_AVAILABLE:
        table = Table(
            title=f"Discovered Devices ({len(devices)} found)",
            border_style="cyan",
            header_style="bold magenta",
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Device Name", style="bold green", min_width=20)
        table.add_column("MAC Address / UUID", style="cyan", min_width=18)
        table.add_column("Signal (RSSI)", style="yellow", justify="right")
        table.add_column("Protocol", style="magenta")

        for i, dev in enumerate(devices, 1):
            proto = "Lorax VFS (Modern)" if dev.is_lorax else "Standard GATT"
            table.add_row(str(i), dev.name, dev.address, f"{dev.rssi} dBm", proto)
        console.print("\n", table)
    else:
        print(f"\n🎉 Found {len(devices)} device(s):")
        print("=" * 60)
        for i, dev in enumerate(devices, 1):
            print(f"[{i}] {dev.name:<24} | MAC: {dev.address:<18} | RSSI: {dev.rssi} dBm")
        print("=" * 60)


def cmd_info(args):
    """Prints full device diagnostics and profiles."""
    is_mock = getattr(args, "mock", False)

    async def _run():
        client_cls = MockPuffcoClient if is_mock else PuffcoClient
        mac = args.mac or ("F7:11:95:C5:14:9B" if is_mock else None)
        async with client_cls(mac) as client:
            t = client.telemetry
            if RICH_AVAILABLE:
                # Diagnostics Table
                diag_table = Table(box=None, show_header=False, pad_edge=False)
                diag_table.add_column("Key", style="dim", width=18)
                diag_table.add_column("Value", style="bold white")

                diag_table.add_row("Device Name", f"[bold green]{t.device_name}[/bold green]")
                diag_table.add_row("MAC / UUID", t.mac_address)
                diag_table.add_row("Serial Number", t.serial_number or "[dim]N/A[/dim]")
                diag_table.add_row("Firmware Version", t.firmware_version or "[dim]N/A[/dim]")
                chg = " (⚡ Charging)" if t.is_charging else ""
                diag_table.add_row("Battery", f"{t.battery_pct}%{chg}")
                diag_table.add_row("Chamber Type", f"[magenta]{t.chamber_name}[/magenta]")
                diag_table.add_row("Lifetime Dabs", f"{t.lifetime_dabs:,}")
                diag_table.add_row("Current State", t.state_name)
                diag_table.add_row("Live Temperature", f"{t.live_temp_f:.1f}°F")
                diag_table.add_row(
                    "Stealth Mode",
                    "[green]Enabled[/green]" if t.stealth_mode else "[dim]Disabled[/dim]",
                )

                panel = Panel(
                    diag_table,
                    title=f"[bold cyan]Puffco Diagnostics — {t.device_name}[/bold cyan]",
                    border_style="bright_blue",
                )
                console.print("\n", panel)

                # Profiles Table
                prof_table = Table(
                    title="Configured Heat Profiles",
                    border_style="yellow",
                    header_style="bold yellow",
                )
                prof_table.add_column("Slot", style="dim", width=6)
                prof_table.add_column("Profile Name", style="bold cyan", min_width=18)
                prof_table.add_column("Target Temp", justify="right", style="bright_red")
                prof_table.add_column("Duration", justify="right", style="white")
                prof_table.add_column("Active", justify="center", style="bold green")

                for p in t.profiles:
                    active = "✓ ACTIVE" if p.slot == t.active_profile else ""
                    prof_table.add_row(
                        f"Slot {p.slot + 1}",
                        p.name,
                        f"{p.target_temp_f}°F",
                        f"{p.duration_s}s",
                        active,
                    )
                console.print(prof_table, "\n")
            else:
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
                    print(
                        f"{marker}[Slot {p.slot}] {p.name:<18} {p.target_temp_f}°F ({p.duration_s}s)"
                    )
                print("=" * 50)

    asyncio.run(_run())


def cmd_monitor(args):
    """Live streaming terminal dashboard monitor."""
    is_mock = getattr(args, "mock", False)

    async def _run():
        mac_display = (args.mac or "auto-discover") if not is_mock else "MOCK DEMO"
        if RICH_AVAILABLE:
            console.print(f"Connecting to Puffco ({mac_display})...")
        else:
            print(f"Connecting to Puffco ({mac_display})...")

        if is_mock:
            client = MockPuffcoClient(args.mac or "F7:11:95:C5:14:9B", demo_mode=True)
        else:
            client = PuffcoClient(args.mac)

        async with client:
            await client.start_telemetry_stream(interval_heating=0.06, interval_idle=0.25)

            if RICH_AVAILABLE:
                with Live(
                    _render_monitor_dashboard(client.telemetry),
                    console=console,
                    refresh_per_second=10,
                ) as live:
                    try:
                        while True:
                            live.update(_render_monitor_dashboard(client.telemetry))
                            await asyncio.sleep(0.1)
                    except (KeyboardInterrupt, asyncio.CancelledError):
                        pass
                console.print("\n[bold yellow]Telemetry monitor stopped.[/bold yellow]")
            else:
                print(f"Connected to {client.telemetry.device_name}! Press Ctrl+C to stop.\n")
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
    is_mock = getattr(args, "mock", False)

    async def _run():
        client_cls = MockPuffcoClient if is_mock else PuffcoClient
        mac = args.mac or ("F7:11:95:C5:14:9B" if is_mock else None)
        async with client_cls(mac) as client:
            if action == "start":
                msg = f"🚀 Starting sesh on {client.telemetry.device_name}..."
                if RICH_AVAILABLE:
                    console.print(f"[bold green]{msg}[/bold green]")
                else:
                    print(msg)
                await client.start_session()
            elif action == "stop":
                msg = f"🛑 Aborting sesh on {client.telemetry.device_name}..."
                if RICH_AVAILABLE:
                    console.print(f"[bold red]{msg}[/bold red]")
                else:
                    print(msg)
                await client.stop_session()
            elif action == "boost":
                msg = f"⚡ Boosting heat on {client.telemetry.device_name}..."
                if RICH_AVAILABLE:
                    console.print(f"[bold yellow]{msg}[/bold yellow]")
                else:
                    print(msg)
                await client.boost()
            else:
                print(f"Unknown action: {action}")
                return
            await asyncio.sleep(0.5)
            if RICH_AVAILABLE:
                console.print("[bold green]Command completed![/bold green]")
            else:
                print("Done!")

    asyncio.run(_run())


def main():
    parser = argparse.ArgumentParser(
        prog="puffco-py",
        description="Puffco Peak Pro & Proxy BLE Command Line Tool",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scan
    p_scan = subparsers.add_parser("scan", help="Scan for nearby Puffco devices")
    p_scan.add_argument("-t", "--timeout", type=float, default=5.0, help="Scan timeout in seconds")
    p_scan.add_argument("--mock", action="store_true", help="Simulate BLE scan discovery")

    # Info
    p_info = subparsers.add_parser("info", help="Display device diagnostics and heat profiles")
    p_info.add_argument("--mac", type=str, default=None, help="Device MAC address or UUID")
    p_info.add_argument(
        "--mock",
        action="store_true",
        help="Run in offline simulated mock mode without BLE hardware",
    )

    # Monitor
    p_mon = subparsers.add_parser("monitor", help="Stream real-time telemetry to terminal HUD")
    p_mon.add_argument("--mac", type=str, default=None, help="Device MAC address or UUID")
    p_mon.add_argument(
        "--mock",
        action="store_true",
        help="Run in offline simulated mock mode with animated telemetry demo",
    )

    # Sesh
    p_sesh = subparsers.add_parser("sesh", help="Trigger heat sesh commands")
    p_sesh.add_argument("action", choices=["start", "stop", "boost"], help="Action to execute")
    p_sesh.add_argument("--mac", type=str, default=None, help="Device MAC address or UUID")
    p_sesh.add_argument(
        "--mock", action="store_true", help="Execute sesh command against simulated mock device"
    )

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
