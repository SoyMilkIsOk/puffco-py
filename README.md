# puffco-py 💨

[![CI](https://github.com/SoyMilkIsOk/puffco-py/actions/workflows/ci.yml/badge.svg)](https://github.com/SoyMilkIsOk/puffco-py/actions/workflows/ci.yml)
[![PyPI Version](https://img.shields.io/pypi/v/puffco-py.svg?color=blue)](https://pypi.org/project/puffco-py/)
[![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-brightgreen.svg)](https://pypi.org/project/puffco-py/)
[![Docs](https://img.shields.io/badge/docs-puffco--py.soymilkisok.com-blue)](https://puffco-py.soymilkisok.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library and CLI for **Puffco Peak Pro** and **Puffco Proxy** smart vaporizers over Bluetooth Low Energy (BLE).

Stream live bowl temperatures and battery levels, control heating sessions and profiles, and build custom desktop widgets, home automations, or web apps.

🌐 **Website & Live Docs**: [puffco-py.soymilkisok.com](https://puffco-py.soymilkisok.com)

---

## Features

- **Real-Time Telemetry**: Stream bowl temperature (~16 FPS active / 250ms idle), battery %, chamber status, and session countdowns.
- **Session Control**: Start/stop heat cycles, trigger boosts, switch profiles, and tweak target temperatures.
- **Async & Thread-Safe**: Built on `asyncio` (`bleak`), with a `ThreadedPuffcoClient` bridge for desktop GUIs (Tkinter, PyQt, rumps) and sync scripts.
- **Auto-Discovery**: Automatically find and connect to nearby Puffco hardware.
- **Built-in CLI**: Terminal commands for monitoring, scanning, and heat control right out of the box.

---

## Installation

```bash
pip install puffco-py
```

For the terminal dashboard and desktop GUI extras:

```bash
pip install "puffco-py[cli,gui]"
```

---

## Quickstart

```python
import asyncio
from puffco_py import PuffcoClient


async def main():
    async with PuffcoClient() as client:
        print(f"Connected to {client.telemetry.device_name} ({client.telemetry.chamber_name})")

        # Stream real-time telemetry updates
        def on_update(telemetry):
            print(f"\rTemp: {telemetry.live_temp_f:.1f}°F | State: {telemetry.state_name}", end="")

        client.add_telemetry_listener(on_update)
        await client.start_telemetry_stream()

        # Stream for 15 seconds
        await asyncio.sleep(15)


asyncio.run(main())
```

> **Building a desktop GUI or synchronous script?** Use `ThreadedPuffcoClient` so you don't have to juggle asyncio event loops. See [`examples/03_threaded_gui.py`](examples/03_threaded_gui.py).

---

## Command-Line Interface (CLI)

`puffco-py` installs a standalone terminal tool:

```bash
# Scan for nearby devices and signal strength
puffco-py scan

# Stream a live terminal telemetry dashboard
puffco-py monitor

# View hardware serial, firmware version, and heat profiles
puffco-py info

# Trigger or abort heat sessions
puffco-py sesh start
puffco-py sesh boost
puffco-py sesh stop
```

---

## Examples & Integrations

The [`examples/`](examples/) directory contains standalone, runnable scripts:

- **[Live Telemetry](examples/01_live_telemetry.py)**: Minimal quickstart streaming temperature and battery.
- **[Session Control](examples/02_session_control.py)**: Switching profile slots and heat settings.
- **[Threaded GUI Worker](examples/03_threaded_gui.py)**: Background BLE worker pattern for PyQt, Tkinter, or PySide.
- **[macOS Menu Bar Widget](examples/04_mac_menu_widget.py)**: Native status bar monitor and remote control (`rumps`).
- **[Home Assistant MQTT Bridge](examples/05_home_assistant_mqtt.py)**: Auto-discovery for smart home sensors and switches.
- **[FastAPI & WebSocket Server](examples/06_fastapi_websocket_server.py)**: REST API and live WebSocket server for web apps.

*See [`examples/README.md`](examples/README.md) for full descriptions and setup steps.*

---

## Documentation

Detailed documentation is available in [`docs/`](docs/) and on the web:

- **[Website & Live Docs](https://puffco-py.soymilkisok.com)** — Interactive web documentation and guides.
- **[Python API Reference](docs/api.md)** — Full reference for `PuffcoClient`, `ThreadedPuffcoClient`, and `PuffcoTelemetry`.
- **[Hardware & Platform Troubleshooting](docs/troubleshooting.md)** — Bluetooth permissions (macOS, Linux BlueZ, Windows) and connection tips.
- **[Lorax BLE Protocol Specification](docs/protocol.md)** — Handshake flow, authentication challenge-response, UUIDs, and VFS endpoints.

---

## Running Tests

Run the offline unit test suite:

```bash
python3 -m unittest discover tests/
```

---

## Contributing

Contributions, bug reports, and hardware dumps are warmly welcomed! Please read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests.

Check out the [Changelog](CHANGELOG.md) for release notes and version history.

---

## Credits & Acknowledgments

`puffco-py` builds upon foundational protocol research and reverse-engineering from the community:

- **[Fr0st3h / PuffcoBLE](https://github.com/Fr0st3h/PuffcoBLE)**: Early BLE exploration and Lorax path research.
- **[PuffcoPC by meekzyr](https://github.com/meekzyr/PuffcoPC)**: Original Puffco Bluetooth communication and pairing work.
- **[home-assistant-puffco](https://github.com/HA-Puff/home-assistant-puffco)**: Home Assistant integration documenting Lorax paths.
- **[Bleak](https://github.com/hbldh/bleak)**: Asynchronous BLE library for Python.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Legal Disclaimer

`puffco-py` is an independent, community-developed open-source reverse-engineering project. It is **NOT** affiliated with, authorized, maintained, sponsored, or endorsed by **Puff Corp.** or any of its affiliates. Puffco, Peak, Peak Pro, Proxy, 3D Chamber, and 3DXL are registered trademarks of Puff Corp. Nominative use of these names is strictly for identification and interoperability purposes under Fair Use.
