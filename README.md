# puffco-ble 💨

[![PyPI Version](https://img.shields.io/badge/pypi-v0.1.0-blue.svg)](https://pypi.org/project/puffco-ble/)
[![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-brightgreen.svg)](https://pypi.org/project/puffco-ble/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Powered by Bleak](https://img.shields.io/badge/BLE-Bleak-blueviolet.svg)](https://github.com/hbldh/bleak)

A standalone, modern, asynchronous Python client and real-time telemetry engine for **Puffco Peak Pro** (V1, V2, Limited Editions) and **Puffco Proxy** smart vaporizers over Bluetooth Low Energy (BLE).

---

## ✨ Features

- ⚡ **Lorax VFS Protocol**: Native support for modern Puffco firmware (Lorax Virtual File System) with asynchronous sequence packet multiplexing and SHA-256 challenge-response authentication.
- ⏱️ **Sub-100ms Low Latency**: Adaptive polling engine capable of ~16 FPS streaming during active heating sessions (60ms) and low-power polling during idle (250ms).
- 🎮 **Full Session Control**: Start sessions, abort/stop, trigger heat boosts, change active profile slots, set custom target temperatures, and toggle stealth mode.
- 🧵 **Thread-Safe & GUI Ready**: Includes `ThreadedPuffcoClient` for effortless integration with synchronous scripts, desktop GUIs (Tkinter, PyQt), and macOS menu bar widgets (`rumps`).
- 🔍 **Auto-Discovery**: Automatic scanning and filtering for nearby Puffco hardware based on manufacturer OUI prefixes and Lorax service UUIDs.
- 🛠️ **Built-in CLI**: Terminal utilities (`puffco-ble scan`, `puffco-ble monitor`, `puffco-ble sesh`) ready out of the box.

---

## 📦 Installation

Install from source or local checkout:

```bash
git clone https://github.com/SoyMilkIsOk/puffco-ble.git
cd puffco-ble
pip install .
```

To include optional CLI and GUI dependencies:

```bash
pip install ".[cli,gui]"
```

---

## 🚀 Quickstart

### 1. Async Python (Core Client)

```python
import asyncio
from puffco_ble import PuffcoClient

async def main():
    # Automatically scans for and connects to the nearest Puffco device
    async with PuffcoClient() as client:
        print(f"Connected to: {client.telemetry.device_name}")
        print(f"Chamber: {client.telemetry.chamber_name} | Battery: {client.telemetry.battery_pct}%")

        # Stream live telemetry updates
        def on_update(telemetry):
            print(f"\rTemp: {telemetry.live_temp_f:.1f}°F | State: {telemetry.state_name}", end="")

        client.add_telemetry_listener(on_update)
        await client.start_telemetry_stream()

        # Keep streaming for 15 seconds
        await asyncio.sleep(15)

asyncio.run(main())
```

### 2. Synchronous & GUI Python (Threaded Client)

If you are building a desktop GUI (Tkinter, PyQt, PySide, wxPython) or a synchronous script, use `ThreadedPuffcoClient`. It executes all asynchronous BLE communications inside a dedicated background worker thread with its own event loop, exposing simple thread-safe methods to your main UI thread without blocking event dispatching:

```python
import time
from puffco_ble import ThreadedPuffcoClient

client = ThreadedPuffcoClient()

# Register real-time callbacks from the background thread
client.add_telemetry_listener(lambda t: print(f"Live Temp: {t.live_temp_f:.1f}°F"))

client.start()

if client.wait_connected(timeout=10.0):
    print(client.telemetry.summary())
    
    # Synchronous thread-safe controls from main UI thread
    client.set_profile(slot=1)
    client.start_session()
    time.sleep(10)
    client.boost()
    time.sleep(10)
    client.stop_session()

client.stop()
```

---

## 🖥️ Command-Line Interface (CLI)

The package installs a standalone terminal tool `puffco-ble`:

```bash
# 1. Scan for nearby devices (5s timeout)
puffco-ble scan

# 2. Stream a live terminal telemetry HUD (Ctrl+C to exit)
puffco-ble monitor

# 3. View hardware serial, firmware version, lifetime dabs, and heat profiles
puffco-ble info

# 4. Trigger or abort heat sessions
puffco-ble sesh start
puffco-ble sesh boost
puffco-ble sesh stop
```

### CLI Command Reference

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `puffco-ble scan` | `-t, --timeout <sec>` *(default: 5.0)* | Scans BLE advertisements and prints discovered devices with MAC addresses and RSSI signal strength. |
| `puffco-ble monitor` | `--mac <MAC/UUID>` *(optional)* | Live streams bowl temperature, target temp, battery %, chamber type, and session state. |
| `puffco-ble info` | `--mac <MAC/UUID>` *(optional)* | Connects and dumps hardware serial, firmware version, lifetime dab count, stealth status, and all 4 profile slot configurations. |
| `puffco-ble sesh <action>` | `start`, `stop`, or `boost`<br>`--mac <MAC/UUID>` *(optional)* | Sends immediate heating commands to the connected device. |

> [!TIP]
> If you have multiple devices or a crowded room, supply `--mac <address>` to target a specific unit directly.

---

## 🍏 Native macOS Menu Bar Widget

A fully functional, native status bar widget is provided in [examples/04_mac_menu_widget.py](examples/04_mac_menu_widget.py) (powered by `rumps`).

```
┌────────────────────────────────────────────────────────┐
│  🔥 520°F (35s)       (or: 💨 480°F | 85% when idle)   │
└┬───────────────────────────────────────────────────────┘
 │  Status: Heating (Sesh Active)
 │  Battery: 85% (⚡ Charging)
 │  Chamber: 3DXL
 │  Total Dabs: 1,420
 │  ───────────────────────────
 │  🚀 Start Heat Sesh
 │  ⚡ Boost Heat (+15s / +10°F)
 │  🛑 Abort Sesh
 └─────────────────────────────
```

### Running the Menu Bar App:
```bash
# Install GUI extra dependencies (rumps on macOS)
pip install ".[gui]"

# Run the widget
python3 examples/04_mac_menu_widget.py
```

---

## 📁 Examples & Guides

The **[`examples/`](examples/)** folder contains self-contained reference scripts:

| Example | Execution Model | Description |
| :--- | :--- | :--- |
| **[`01_live_telemetry.py`](examples/01_live_telemetry.py)** | Async (`asyncio`) | Minimal quickstart: connects and streams live bowl temperature & battery. |
| **[`02_session_control.py`](examples/02_session_control.py)** | Async (`asyncio`) | Inspects profile slots, switches active profile, toggles stealth mode. |
| **[`03_threaded_gui.py`](examples/03_threaded_gui.py)** | Threaded / Sync | Background worker pattern for desktop GUIs (Tkinter, PyQt, PySide). |
| **[`04_mac_menu_widget.py`](examples/04_mac_menu_widget.py)** | Desktop GUI (`rumps`) | Full macOS menu bar status indicator and session remote control. |

*See **[`examples/README.md`](examples/README.md)** for in-depth explanations, prerequisites, and troubleshooting tips.*

---

## 📚 Python API Reference

### Client Methods (`PuffcoClient` / `ThreadedPuffcoClient`)

| Method | Async / Sync | Description |
| :--- | :--- | :--- |
| `start_session()` | Both | Initiates a heating session using the currently active profile. |
| `stop_session()` | Both | Aborts and cancels an active heating session immediately. |
| `boost()` | Both | Triggers heat boost during an active session (`+15s / +10°F`). |
| `set_profile(slot)` | Both | Changes active heat profile slot (integer `0` to `3`). |
| `set_stealth_mode(enabled)` | Both | Toggles LED lights on (`False`) or off (`True`). |
| `start_telemetry_stream(...)` | Async | Starts continuous polling engine (60ms active sesh, 250ms idle). |
| `add_telemetry_listener(fn)` | Both | Registers a callback `fn(telemetry)` called upon state change. |

### Telemetry Model (`PuffcoTelemetry`)

Available via `client.telemetry`:

- `live_temp_f`: Current real-time temperature of the heating bowl in °F.
- `target_temp_f`: Target temperature of the active profile in °F.
- `battery_pct`: Battery level (`0`–`100`%).
- `is_charging`: Boolean indicating USB-C or wireless Qi charging state.
- `chamber_name`: Connected chamber type (`"3D"`, `"3DXL"`, `"Proxy"`, or `"None"`).
- `operating_state`: Current state enum (`IDLE`, `HEAT_PREHEAT`, `HEAT_ACTIVE`, `HEAT_FADE`).
- `is_heating`: Boolean flag that is `True` whenever the chamber is actively powered.
- `time_remaining`: Remaining seconds in active heating cycle.
- `lifetime_dabs`: Lifetime total dab counter (odometer).
- `profiles`: List of 4 saved profile configurations (`Profile(slot, name, temp_f, duration_s)`).

---

## 🔬 How the Protocol Works

Puffco devices communicate over Bluetooth Low Energy (BLE) using the **Lorax Virtual File System (VFS)**:

```
 central central (PC/Mac/RPi)                 Puffco Device
      │                                             │
      │──────── 1. Connect (Bleak GATT) ───────────>│
      │                                             │
      │<─────── 2. Lorax Version / Notify ──────────│
      │                                             │
      │── 3. GET_ACCESS_SEED (Opcode 0x00) ────────>│
      │<─ 16-Byte Random Seed Challenge ────────────│
      │                                             │
      │── 4. UNLOCK_ACCESS (Opcode 0x01) ──────────>│
      │      Token = SHA256(MasterKey + Seed)[:16]  │
      │<─ Status: SUCCESS (0x00) ───────────────────│
      │                                             │
      │── 5. READ_SHORT ("/p/app/htr/temp") ───────>│
      │<─ Live Chamber Temp (Float / Int Tenths) ───│
```

1. **Service UUID**: `e276967f-ea8a-478a-a92e-d78f5dd15dd5`
2. **Command Characteristic**: `60133d5c-5727-4f2c-9697-d842c5292a3c` (Write Without Response)
3. **Reply Characteristic**: `8dc5ec05-8f7d-45ad-99db-3fbde65dbd9c` (Notify / Indicate)
4. **VFS Paths**:
   - `/p/app/stat/id`: Operating state byte (Idle, Preheat, Active, Fade).
   - `/p/app/htr/temp`: Live bowl temperature.
   - `/p/app/mc`: Mode control (0x07 = Start, 0x08 = Stop, 0x09 = Boost).
   - `/p/bat/soc`: Battery State of Charge percentage.
   - `/p/app/odom/0/nc`: Lifetime odometer dab count.

---

## 🧪 Running Tests

Run the offline unit test suite:

```bash
python3 -m unittest discover tests/
```

---

## 🙏 Credits & Acknowledgments

This library builds upon foundational protocol research and reverse-engineering from the community:

* **[PuffcoPC by meekzyr](https://github.com/meekzyr/PuffcoPC)**: The original project exploring Puffco Bluetooth communication and pairing.
* **[home-assistant-puffco](https://github.com/HA-Puff/home-assistant-puffco)**: Fantastic Home Assistant integration documenting Lorax paths and characteristics.
* **[Bleak](https://github.com/hbldh/bleak)**: The backbone asynchronous BLE library for Python.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
