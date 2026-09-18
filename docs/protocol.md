# Lorax BLE Protocol Specification 🔬

This document outlines the reverse-engineered Bluetooth Low Energy (BLE) protocol used by **Puffco Peak Pro** and **Puffco Proxy** smart vaporizers.

---

## 1. Architecture: The Lorax Virtual File System (VFS)

Modern Puffco devices expose internal hardware metrics and control registers through an abstraction known as the **Lorax Virtual File System (VFS)**. Instead of traditional GATT characteristic-per-value architecture, Puffco uses a command/reply packet multiplexer over a single pair of GATT characteristics.

### BLE GATT Service & Characteristics

| Name | UUID | Type | Description |
| :--- | :--- | :--- | :--- |
| **Lorax Service** | `e276967f-ea8a-478a-a92e-d78f5dd15dd5` | Primary Service | Primary BLE service for all device interaction. |
| **Command** | `60133d5c-5727-4f2c-9697-d842c5292a3c` | Write Without Response | Client sends framed packet requests (reads, writes, commands). |
| **Reply** | `8dc5ec05-8f7d-45ad-99db-3fbde65dbd9c` | Notify / Indicate | Device streams packet responses and notifications back to the client. |

---

## 2. Authentication Handshake Flow

Before the device allows reading sensor data or sending heat commands, an authentication handshake must be completed using a SHA-256 challenge-response scheme:

```
 Host Central (Client)                                  Puffco Device
       │                                                      │
       │──────────────── 1. Connect GATT ────────────────────>│
       │                                                      │
       │<─────────────── 2. Subscribe to Reply Notify ────────│
       │                                                      │
       │──── 3. GET_ACCESS_SEED (Opcode 0x00) ───────────────>│
       │<─── 16-Byte Random Seed Challenge ───────────────────│
       │                                                      │
       │──── 4. UNLOCK_ACCESS (Opcode 0x01) ──────────────────>│
       │        Token = SHA256(MasterKey + Seed)[:16]         │
       │<─── Status: SUCCESS (0x00) ──────────────────────────│
       │                                                      │
       │──── 5. READ / WRITE VFS Paths ──────────────────────>│
       │<─── Sensor Telemetry & Acknowledgment ───────────────│
```

### Handshake Steps
1. **Subscribe**: Client subscribes to notifications on the Reply characteristic (`8dc5...`).
2. **Challenge Request**: Client writes `GET_ACCESS_SEED` (`0x00`) to the Command characteristic.
3. **Challenge Reply**: Device replies with a 16-byte cryptographically random seed.
4. **Token Generation**: Client computes `SHA256(MasterKey + Seed)` and takes the first 16 bytes.
5. **Unlock Access**: Client writes `UNLOCK_ACCESS` (`0x01`) with the 16-byte token to the Command characteristic.
6. **Authentication Confirmation**: Device responds with a status code (`0x00` = success). Once unlocked, VFS read and write operations are accepted.

---

## 3. Lorax VFS Path Registry

Device metrics and controls are organized as virtual file paths in the Lorax hierarchy:

| Path | Type | Description |
| :--- | :--- | :--- |
| `/p/app/stat/id` | `uint8` | Operating state: `0x00` (Idle), `0x01` (Preheat), `0x02` (Active), `0x03` (Fade). |
| `/p/app/htr/temp` | `float32` / `uint16` | Current live bowl temperature. |
| `/p/app/mc` | `uint8` (write) | Mode control command: `0x07` (Start), `0x08` (Stop), `0x09` (Boost). |
| `/p/bat/soc` | `uint8` | Battery State of Charge (0–100%). |
| `/p/bat/chg/stat` | `uint8` | Charging status flag (wireless Qi or USB-C). |
| `/p/app/odom/0/nc` | `uint32` | Lifetime total dab counter (odometer). |
| `/p/app/tc` | `uint8` | Connected chamber type (3DXL, 3D, Proxy, None). |
| `/p/app/stealth` | `uint8` | Stealth mode toggle (LED lights off = 1, on = 0). |
| `/p/app/lantern` | `uint8` | Ambient lantern lighting mode control. |
| `/p/app/ui/prfl` | `uint8` | Currently active profile slot index (0–3). |
| `/p/app/prfl/0/name` | `string` | Profile 1 name (up to 16 characters). |
| `/p/app/prfl/0/temp` | `float32` | Profile 1 target temperature. |
| `/p/app/prfl/0/time` | `uint16` | Profile 1 session duration in seconds. |

---

## 4. Contributing New Endpoints

To explore undocumented paths or reverse-engineer additional features (such as custom LED vapor waves, Bluetooth audio sync, or diagnostic logs), see the **Reverse-Engineering Guide** in [CONTRIBUTING.md](../CONTRIBUTING.md#reverse-engineering-guide).
