# Python API Reference 📚

This document details the core classes, methods, and data models provided by `puffco-py`.

---

## Table of Contents

- [Client Classes](#client-classes)
  - [`PuffcoClient` (Async)](#puffcoclient-async)
  - [`ThreadedPuffcoClient` (Sync / Threaded)](#threadedpuffcoclient-sync--threaded)
- [Client Methods Reference](#client-methods-reference)
- [Telemetry Model (`PuffcoTelemetry`)](#telemetry-model-puffcotelemetry)
- [Profile Model (`PuffcoProfile`)](#profile-model-puffcoprofile)
- [Enums](#enums)
  - [`OperatingState`](#operatingstate)
  - [`ChamberType`](#chambertype)

---

## Client Classes

### `PuffcoClient` (Async)

The primary asynchronous client for interacting with Puffco devices using `asyncio` and `bleak`.

```python
from puffco_py import PuffcoClient

async with PuffcoClient() as client:
    print(f"Connected to {client.telemetry.device_name}")
    await client.start_session()
```

#### Constructor
```python
PuffcoClient(mac_address: Optional[str] = None, timeout: float = 10.0)
```
- `mac_address`: Specific BLE MAC address or macOS UUID. If omitted, the client scans and connects to the nearest Puffco device automatically.
- `timeout`: Discovery and connection timeout in seconds.

---

### `ThreadedPuffcoClient` (Sync / Threaded)

A synchronous wrapper around `PuffcoClient` designed for desktop GUIs (Tkinter, PyQt, PySide, rumps) and synchronous scripts. It manages its own event loop on a dedicated background worker thread so the main UI thread never blocks.

```python
from puffco_py import ThreadedPuffcoClient

client = ThreadedPuffcoClient()
client.start()

if client.wait_connected(timeout=10.0):
    client.start_session()

client.stop()
```

#### Additional Methods on `ThreadedPuffcoClient`
- `start()`: Launches the background thread and begins connecting.
- `stop()`: Disconnects and cleanly terminates the worker thread.
- `wait_connected(timeout: float = 10.0) -> bool`: Blocks until connection is established or times out.
- `is_connected -> bool`: Returns `True` if connected.

---

## Client Methods Reference

All session control and profile configuration methods are available on both `PuffcoClient` (as async coroutines) and `ThreadedPuffcoClient` (as synchronous methods).

| Method | Parameters | Description |
| :--- | :--- | :--- |
| `start_session()` | — | Starts a heating session using the currently selected profile slot. |
| `stop_session()` | — | Immediately aborts and cancels an active heating session. |
| `boost()` | — | Triggers a heat boost during an active session (`+15s / +10°F` by default). |
| `set_profile(slot)` | `slot: int` (0–3) | Switches active heat profile slot (0 = Profile 1, 3 = Profile 4). |
| `set_temperature(temp_f, [slot])` | `temp_f: float`, `slot: Optional[int]` | Sets the target temperature in °F for the active profile or a specific slot. |
| `set_profile_duration(slot, seconds)` | `slot: int`, `seconds: int` (15–180) | Sets the session duration in seconds for a specific profile slot. |
| `set_profile_name(slot, name)` | `slot: int`, `name: str` (max 16 chars) | Sets display name for a profile slot. |
| `save_profile(slot, profile)` | `slot: int`, `profile: PuffcoProfile` | Updates name, temperature, and duration for a slot in one call. |
| `set_boost_temperature(temp_f)` | `temp_f: float` (5–50°F) | Configures the temperature increment applied when boosting. |
| `set_boost_duration(seconds)` | `seconds: int` (5–60s) | Configures the session extension time applied when boosting. |
| `set_stealth_mode(enabled)` | `enabled: bool` | Disables LEDs (`True`) or restores normal lighting (`False`). |
| `start_lantern()` | — | Activates continuous ambient lantern light mode. |
| `stop_lantern()` | — | Deactivates ambient lantern light mode. |
| `start_telemetry_stream(...)` | — *(async only)* | Starts continuous polling engine (sub-100ms when active, 250ms when idle). |
| `stop_telemetry_stream()` | — *(async only)* | Stops the background telemetry polling loop. |
| `add_telemetry_listener(fn)` | `fn: Callable[[PuffcoTelemetry], None]` | Registers a callback triggered whenever new telemetry is received. |
| `remove_telemetry_listener(fn)` | `fn: Callable[[PuffcoTelemetry], None]` | Unregisters a telemetry callback. |
| `add_state_listener(fn)` | `fn: Callable[[OperatingState], None]` | Registers a callback triggered on operating state transitions. |
| `add_connection_listener(fn)` | `fn: Callable[[bool], None]` | Registers a callback triggered on connect/disconnect events. |

---

## Telemetry Model (`PuffcoTelemetry`)

Accessible via `client.telemetry`. Contains live snapshot state parsed from device sensors:

| Attribute | Type | Units / Values | Description |
| :--- | :--- | :--- | :--- |
| `device_name` | `str` | Text | User-assigned device name. |
| `device_model` | `str` | Text | Resolved hardware model (e.g., `"Peak Pro (V2)"`, `"Puffco Proxy"`). |
| `serial_number` | `str` | Text | Hardware serial number. |
| `firmware_version` | `str` | Text | Device firmware release string. |
| `live_temp_f` | `float` | °F | Current real-time temperature of the heating bowl. |
| `live_temp_c` | `float` | °C | Current bowl temperature in Celsius. |
| `target_temp_f` | `float` | °F | Target temperature of the active profile slot. |
| `target_temp_c` | `float` | °C | Target temperature in Celsius. |
| `battery_pct` | `int` | 0–100% | Battery State of Charge percentage. |
| `is_charging` | `bool` | `True` / `False` | Whether USB-C or wireless Qi charging is active. |
| `chamber_type` | `ChamberType` | Enum | Chamber enum identifier. |
| `chamber_name` | `str` | `"3DXL"`, `"3D"`, etc. | Human-readable chamber name. |
| `operating_state` | `OperatingState`| Enum | Current hardware operating state enum. |
| `state_name` | `str` | `"IDLE"`, `"HEAT_ACTIVE"` | Human-readable operating state name. |
| `is_heating` | `bool` | `True` / `False` | `True` whenever the chamber heater is actively powered. |
| `time_remaining` | `int` | Seconds | Seconds remaining in the current active heat cycle. |
| `total_time` | `int` | Seconds | Total programmed duration of current heat session. |
| `lifetime_dabs` | `int` | Count | Lifetime total dab odometer counter. |
| `boost_temp_f` | `float` | °F | Configured heat boost temperature offset. |
| `boost_duration_s` | `int` | Seconds | Configured heat boost time extension. |
| `profiles` | `List[PuffcoProfile]` | 4 items | Configurations for all 4 device profile slots. |

---

## Profile Model (`PuffcoProfile`)

A dataclass representing a single saved heat profile slot:

```python
@dataclass
class PuffcoProfile:
    slot: int  # 0 to 3
    name: str  # Display name (e.g. "Low", "Max")
    target_temp_f: float  # Target temperature in °F
    duration_s: int  # Session duration in seconds
```

---

## Enums

### `OperatingState`
Represents the state of the vaporizer:
- `OperatingState.IDLE` (0x00): Standby, not heating.
- `OperatingState.HEAT_PREHEAT` (0x01): Chamber is actively ramping up to target temperature.
- `OperatingState.HEAT_ACTIVE` (0x02): Chamber reached target temperature, session timer running.
- `OperatingState.HEAT_FADE` (0x03): Heat cycle complete, chamber fading out.

### `ChamberType`
Represents the connected atomizer hardware:
- `ChamberType.NONE` (0x00): No atomizer detected.
- `ChamberType.REGULAR_3D` (0x01): Standard 3D Chamber.
- `ChamberType.CHAMBER_3DXL` (0x03): 3DXL High-Capacity Chamber.
- `ChamberType.PROXY` (0x04): Puffco Proxy modular chamber.
