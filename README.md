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

If you are building a desktop app (or just don't want to deal with `asyncio` event loops), use `ThreadedPuffcoClient`:

```python
import time
from puffco_ble import ThreadedPuffcoClient

client = ThreadedPuffcoClient()
client.start()

if client.wait_connected(timeout=10.0):
    print(client.telemetry.summary())
    
    # Synchronous thread-safe controls
    client.set_profile(slot=1)
    client.start_session()
    time.sleep(10)
    client.stop_session()

client.stop()
```

---

## 🖥️ Command-Line Interface (CLI)

The package includes a command-line tool `puffco-ble`:

```bash
# Scan for nearby Puffco hardware
puffco-ble scan

# Stream live bowl temperature and metrics in your terminal
puffco-ble monitor

# Display device diagnostics, total dabs, and saved heat profiles
puffco-ble info

# Trigger heat session actions
puffco-ble sesh start
puffco-ble sesh boost
puffco-ble sesh stop
```

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
