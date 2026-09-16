# puffco-py Examples & Integration Guides 💡

This directory contains clean, standalone example scripts demonstrating how to interact with Puffco Peak Pro and Proxy devices using the `puffco-py` library.

---

## 🚀 Prerequisites & Setup

Before running any of the examples, ensure you have installed the package and that Bluetooth is ready:

```bash
# From the repository root:
pip install -e .

# Or install with optional extras (required for Example 04 - macOS Menu Bar):
pip install -e ".[gui]"
```

### 📡 Device & Bluetooth Checklist
1. **Power On**: Ensure your Puffco Peak Pro or Proxy is powered on and awake (press the power button once to ensure BLE advertising is active).
2. **Proximity**: Keep your device within standard Bluetooth range (~10–15 feet / 3–5 meters).
3. **macOS Bluetooth Permissions**: When running for the first time, macOS may prompt you to grant Bluetooth permission to your terminal or IDE (System Settings → Privacy & Security → Bluetooth).

---

## 📋 Examples Overview

| File | Type | Framework / Lib | Purpose |
| :--- | :--- | :--- | :--- |
| **[`01_live_telemetry.py`](01_live_telemetry.py)** | Async | `asyncio` + `bleak` | Quickstart: connects and streams live bowl temperature & battery. |
| **[`02_session_control.py`](02_session_control.py)** | Async | `asyncio` + `bleak` | Inspects profiles, switches slots, toggles stealth mode, session control. |
| **[`03_threaded_gui.py`](03_threaded_gui.py)** | Synchronous | `ThreadedPuffcoClient` | Background BLE worker pattern for desktop GUIs (Tkinter, PyQt, etc.). |
| **[`04_mac_menu_widget.py`](04_mac_menu_widget.py)** | Desktop / GUI | `rumps` (macOS) | Native macOS menu bar status app with live metrics and session buttons. |

---

## 📖 Detailed Guides

### 1. [`01_live_telemetry.py`](01_live_telemetry.py) — Live Telemetry Streaming

The quickest way to verify connection and read real-time device sensor data.

- **What it does**:
  - Automatically discovers and connects to the nearest Puffco device.
  - Queries device information (chamber type, lifetime dab counter).
  - Registers a high-frequency telemetry listener callback.
  - Streams live bowl temperature, target temperature, and battery state directly on a single line in your terminal for 30 seconds.
- **How to run**:
  ```bash
  python3 examples/01_live_telemetry.py
  # or from inside the examples directory:
  python3 01_live_telemetry.py
  ```

---

### 2. [`02_session_control.py`](02_session_control.py) — Profiles & Heat Control

Demonstrates device configuration, profile inspection, and triggering sessions.

- **What it does**:
  - Connects and prints all stored heat profile slots on the device (name, target temperature, session duration).
  - Switches the active heat profile (e.g., selects Slot 1).
  - Toggles **Stealth Mode** (LED lights off) on and off.
  - Includes commented-out sample code to trigger heating sessions, apply heat boosts (`+15s / +10°F`), and abort/stop sessions.
- **How to run**:
  ```bash
  python3 examples/02_session_control.py
  ```
  *(Note: Heat triggering is commented out by default so you don't accidentally heat an empty chamber.)*

---

### 3. [`03_threaded_gui.py`](03_threaded_gui.py) — Threaded Worker for Desktop GUIs

Standard `asyncio` event loops can conflict with desktop GUI frameworks (like PyQt, Tkinter, or PySide). This example shows how to use `ThreadedPuffcoClient` to run all BLE polling on an isolated background thread.

- **What it does**:
  - Starts a background daemon thread that manages BLE connection and telemetry polling.
  - Allows your main application thread to make simple, synchronous, blocking or non-blocking calls (`wait_connected()`, `set_profile()`, `start_session()`, `stop()`).
  - Dispatches telemetry updates safely to your UI callbacks.
- **How to run**:
  ```bash
  python3 examples/03_threaded_gui.py
  ```

---

### 4. [`04_mac_menu_widget.py`](04_mac_menu_widget.py) — macOS Status Bar App

A lightweight, native macOS menu bar widget using `rumps`.

- **Requirements**:
  - macOS
  - `rumps` (`pip install rumps` or `pip install ".[gui]"`)
- **What it does**:
  - Places a live status indicator directly in the macOS menu bar:
    - Idle state: `💨 480°F | 85%`
    - Heating state: `🔥 520°F (35s)`
  - Dropdown menu displaying:
    - Connection state (Connected / Offline)
    - Battery percentage & charging indicator (`⚡`)
    - Chamber type (e.g., 3D, 3DXL, Proxy)
    - Lifetime odometer dab counter
  - Interactive menu action items:
    - 🚀 **Start Heat Sesh**
    - ⚡ **Boost Heat**
    - 🛑 **Abort Sesh**
- **How to run**:
  ```bash
  python3 examples/04_mac_menu_widget.py
  ```

---

## 🔧 Troubleshooting

- **`No Puffco devices found nearby. Ensure device is powered on.`**:
  - Make sure the device is awake. If idle for a while, the device enters deep sleep. Click the physical button once to start BLE advertising.
  - Check that no other application (like the official Puffco mobile app or another BLE script) currently holds an exclusive connection to the device.
- **Targeting a Specific Device (MAC / UUID)**:
  - If you own multiple devices or are in a crowded environment, pass the MAC address or UUID to the client:
    ```python
    async with PuffcoClient(target_mac="F71195C5-149B-5A18-54F0-69BFB3CB217C") as client:
        ...
    ```
