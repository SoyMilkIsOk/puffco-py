# Hardware & Platform Troubleshooting 🛠️

This guide covers common connection issues, platform-specific Bluetooth permissions, and hardware quirks when working with Puffco devices and `puffco-py`.

---

## 1. The Single-Central Rule (Device Exclusivity)

Puffco hardware enforces an exclusive BLE connection policy: **only ONE central controller can be connected at any time**.

- **Symptoms**: `puffco-py` times out scanning or fails during connection with `BleakError: Device not found` or `Connection failed`.
- **Cause**: The official Puffco iOS/Android app or Puffco Web App (Chrome) is connected or running in the background on your phone, tablet, or another computer.
- **Solution**:
  1. Completely close or force-quit the Puffco app on your phone.
  2. Close any browser tabs that were connected to the Puffco Web App.
  3. Turn your phone's Bluetooth off temporarily if needed to verify exclusivity.

---

## 2. macOS Bluetooth Permissions

On modern macOS (Ventura, Sonoma, Sequoia), macOS enforces strict privacy permissions (TCC) for Bluetooth access:

- **Symptoms**: `puffco-py scan` returns no devices or silently times out, even when the Peak Pro is right next to your Mac.
- **Solution**:
  1. When prompted by macOS on first run, click **Allow** to grant Bluetooth access.
  2. If you accidentally clicked Deny or never saw the prompt, open:
     **System Settings → Privacy & Security → Bluetooth**
  3. Ensure your terminal emulator (e.g. **Terminal**, **iTerm2**, or **Visual Studio Code**) is toggled **ON**.
  4. Restart your terminal application.

---

## 3. Linux & Raspberry Pi (BlueZ Permissions)

On Linux systems, the kernel and BlueZ daemon restrict raw BLE socket access to privileged users (`root`).

### Granting Network Capabilities to Python
To allow standard users to run `puffco-py` without `sudo`, grant the Python binary raw socket capabilities:

```bash
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
```

### Checking BlueZ Daemon Status
Ensure the system Bluetooth service is active and unblocked:

```bash
sudo systemctl status bluetooth
# If blocked by rfkill:
rfkill unblock bluetooth
```

---

## 4. Windows 10/11 Bluetooth Pairing

On Windows, the native WinRT Bluetooth API requires devices to be paired in Windows Settings before third-party applications can enumerate GATT services and characteristics.

1. Turn off your Puffco Peak Pro.
2. Hold down the power button from the powered-off state until the LED ring pulses **Blue** (pairing mode).
3. Open Windows **Settings → Bluetooth & devices → Add device**.
4. Select your Puffco device from the list and complete the pairing process.
5. Once paired, `puffco-py` will automatically connect, authenticate, and communicate over BLE without needing to repeat this step.

---

## 5. General Connection Checklist

- **Device is Powered On**: Press the power button once to wake the device. The LED should illuminate briefly to confirm it is awake and advertising.
- **Proximity**: Maintain a distance of within 10–15 feet (3–5 meters) during initial discovery.
- **Specify MAC/UUID Directly**: If you are in a crowded BLE environment or auto-discovery is slow, supply the device address directly:
  ```bash
  puffco-py monitor --mac "F7:11:95:C5:14:9B"
  ```
- **Cycle Bluetooth Adapter**: If the host BLE stack becomes unresponsive, toggle your computer's Bluetooth off and back on.
