# Step 4 Implementation Plan: Extended Protocol Features, Platform Guides & Ecosystem Blueprints

This document contains the complete plan, importance rankings, and prompt for executing Step 4 of the `puffco-py` open-source community release roadmap.

---

## 🎯 Importance Rankings & Review

| Item | Focus | Score / Tier | Implementation Effort |
| :--- | :--- | :---: | :---: |
| **4.1** | **Platform Gotchas & Troubleshooting Guide** | **9 / 10 (P0 - Docs)** | Medium |
| **4.2** | **Full Profile Editing (`set_profile_duration`, `set_profile_name`)** | **7 / 10 (P1 - High)** | Medium |
| **4.3** | **Home Assistant MQTT Discovery Blueprint (`examples/05_...`)** | **7 / 10 (P1 - High)** | Medium |
| **4.4** | **FastAPI / WebSocket Server Blueprint (`examples/06_...`)** | **6 / 10 (P2 - Medium)** | Medium |
| **4.5** | **Boost Settings Customization (`set_boost_temp`, `set_boost_time`)** | **6 / 10 (P2 - Medium)** | Low-Medium |
| **4.6** | **Device Model Identification (Peak Pro V1/V2/Proxy/Pivot)** | **6 / 10 (P2 - Medium)** | Low-Medium |
| **4.7** | **Lorax Push Notification Architecture (`LORAX_OP_WATCH`)** | **5 / 10 (P3 - Low)** | High |

### Item Details:
- **4.1 Platform Gotchas & Troubleshooting Guide**: Resolves the top causes of BLE confusion:
  1. *Single Central Lockout*: Puffco devices only allow one active BLE connection; phone apps running in background must be closed.
  2. *Linux BlueZ*: Bleak needs `sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))` to open raw BLE sockets without root.
  3. *macOS Privacy*: Terminal / VS Code needs Bluetooth permission under System Settings > Privacy & Security > Bluetooth.
  4. *Windows Pairing*: Peak Pro must be paired in Windows Bluetooth settings prior to Bleak GATT discovery.
- **4.2 Full Profile Editing**: Extends `set_temperature` to include `set_profile_duration(slot, sec)`, `set_profile_name(slot, name)`, and `save_profile(slot, profile)` so downstream apps can create and customize user profiles.
- **4.3 Home Assistant MQTT Discovery Blueprint**: Provides a turnkey script connecting to local MQTT broker and auto-discovering sensors (temp, battery, dabs, chamber, state) in Home Assistant.
- **4.4 FastAPI / WebSocket Blueprint**: Provides an HTTP/WebSocket bridge allowing browser controllers and mobile apps to query state and trigger heating sessions.
- **4.5 Boost Customization**: Exposes paths for custom boost temperature and duration.
- **4.6 Device Model Identification**: Reads standard GATT model characteristic (`0x2A24`) or Lorax hardware paths rather than substring matching on names.
- **4.7 Lorax Push Notifications**: Replaces continuous polling with event-driven notifications (`LORAX_OP_WATCH` on `PUFFCO_LORAX_CHAR_EVENT`).

---

## 📋 Ready-to-Run Conversation Prompt for Step 4

Copy and paste the block below into a new conversation to execute Step 4:

```markdown
# Task: Step 4 - Extended Protocol Features, Platform Guides & Ecosystem Blueprints for puffco-py

Please execute Step 4 of the open-source release roadmap for `/Users/samste/Desktop/puffco-py`:

1. **Extended Protocol & Hardware Features**:
   - Add full profile editing methods to `PuffcoClient` and `ThreadedPuffcoClient`:
     - `set_profile_duration(slot: int, seconds: int)`
     - `set_profile_name(slot: int, name: str)`
     - `save_profile(slot: int, profile: PuffcoProfile)`
   - Add Boost customization:
     - `set_boost_temperature(temp_f: float)` and `set_boost_duration(seconds: int)`.
   - Add device model detection (Peak Pro V1 vs V2 vs Proxy vs Pivot) via Model Number GATT characteristic (`0x2A24`) and firmware string inspection.

2. **Comprehensive Platform & Troubleshooting Documentation**:
   - Update `README.md` and `site/docs.html` with a prominent **Platform Troubleshooting & Hardware Gotchas** section:
     - **The Single-Central Rule**: Explain that the Puffco only accepts one connection at a time, and the official mobile app must be closed.
     - **Linux / Raspberry Pi**: Document BlueZ setup, `cap_net_raw` permissions, and DBus permissions.
     - **macOS Permissions**: Document enabling Bluetooth under System Settings > Privacy & Security > Bluetooth.
     - **Windows Pairing**: Document pairing in Windows Bluetooth settings prior to Bleak GATT operations.

3. **Integration Blueprints (`examples/`)**:
   - Add `examples/05_home_assistant_mqtt.py`: Blueprint demonstrating how to stream Puffco telemetry into Home Assistant via MQTT Discovery.
   - Add `examples/06_fastapi_websocket_server.py`: Blueprint showing how to serve live telemetry and accept session controls over a REST/WebSocket API for web or mobile apps.

4. **Verify**:
   - Test all new methods against mock devices and update the README API reference table.
```
