"""
Mock BLE engine and simulated Puffco hardware transport layer.
Provides in-memory GATT services, Lorax VFS emulation, and dynamic telemetry
simulations for offline testing and CLI demo mode.
"""

import asyncio
import logging
import random
import struct
from typing import Any, Callable, Dict, List, Optional

from .constants import (
    DEVINFO_FIRMWARE_UUID,
    DEVINFO_MODEL_NUMBER_UUID,
    DEVINFO_SERIAL_UUID,
    LORAX_MASTER_HANDSHAKE_KEY,
    LORAX_OP_GET_ACCESS_SEED,
    LORAX_OP_READ_SHORT,
    LORAX_OP_UNLOCK_ACCESS,
    LORAX_OP_WRITE_SHORT,
    PATH_ACTIVE_PROFILE,
    PATH_BATTERY_CHARGE_STAT,
    PATH_BATTERY_SOC,
    PATH_BOOST_TEMP,
    PATH_BOOST_TIME,
    PATH_CHAMBER_TEMP,
    PATH_CHAMBER_TYPE,
    PATH_DEVICE_NAME,
    PATH_LANTERN_CMD,
    PATH_LED_BRIGHTNESS,
    PATH_MODE_CONTROL,
    PATH_ODOMETER_DABS,
    PATH_PROFILE_NAME_PREFIX,
    PATH_PROFILE_TEMP_PREFIX,
    PATH_PROFILE_TIME_PREFIX,
    PATH_STATE_ID,
    PATH_STEALTH_MODE,
    PATH_TIME_ELAPSED,
    PATH_TIME_TOTAL,
    PUFFCO_LORAX_CHAR_CMD,
    PUFFCO_LORAX_CHAR_REPLY,
    PUFFCO_LORAX_CHAR_VERSION,
    PUFFCO_LORAX_SVC_UUID,
)
from .models import ChamberType, OperatingState
from .protocol import calculate_lorax_auth_token, f_to_c

logger = logging.getLogger("puffco_py.mock")


class MockBLEDevice:
    """Simulated Bleak BLEDevice."""

    def __init__(self, name: str, address: str, rssi: int = -55):
        self.name = name
        self.address = address
        self.rssi = rssi


class MockAdvertisementData:
    """Simulated Bleak AdvertisementData."""

    def __init__(
        self,
        local_name: Optional[str] = None,
        service_uuids: Optional[List[str]] = None,
        rssi: int = -55,
    ):
        self.local_name = local_name
        self.service_uuids = service_uuids or []
        self.rssi = rssi


class MockBleakClient:
    """
    Simulated BleakClient for offline testing and hardware-free operation.
    Implements GATT reads/writes, notifications, and Lorax challenge-response.
    """

    def __init__(
        self,
        address: str = "F7:11:95:C5:14:9B",
        disconnected_callback: Optional[Callable[[Any], None]] = None,
        auth_fail: bool = False,
        connect_fail: bool = False,
        timeout_opcodes: Optional[List[int]] = None,
    ):
        self.address = address
        self.disconnected_callback = disconnected_callback
        self.is_connected = False
        self.auth_fail = auth_fail
        self.connect_fail = connect_fail
        self.timeout_opcodes = timeout_opcodes or []
        self.model_number = "Peak Pro V2"

        self._seed = b"0123456789abcdef"
        self._notify_cb: Optional[Callable[[str, bytearray], None]] = None

        # Virtual File System (Lorax VFS dictionary)
        self.vfs: Dict[str, bytes] = {}
        self._init_default_vfs()

    def _init_default_vfs(self):
        """Initializes default VFS values matching a healthy Puffco Peak Pro with 3DXL."""
        self.vfs[PATH_DEVICE_NAME] = b"Mock Peak Pro\x00"
        self.vfs[PATH_STATE_ID] = bytes([OperatingState.IDLE.value])
        # 84.5°F = ~29.16°C
        self.vfs[PATH_CHAMBER_TEMP] = struct.pack("<f", 29.1667)
        self.vfs[PATH_BATTERY_SOC] = bytes([88])
        self.vfs[PATH_BATTERY_CHARGE_STAT] = bytes([0])  # 0 = charging
        self.vfs[PATH_CHAMBER_TYPE] = bytes([ChamberType.CHAMBER_3DXL.value])
        self.vfs[PATH_ODOMETER_DABS] = struct.pack("<I", 1337)
        self.vfs[PATH_STEALTH_MODE] = bytes([0])
        self.vfs[PATH_ACTIVE_PROFILE] = bytes([1])  # Slot 1 active (Medium)
        self.vfs[PATH_TIME_ELAPSED] = struct.pack("<f", 0.0)
        self.vfs[PATH_TIME_TOTAL] = struct.pack("<f", 50.0)
        self.vfs[PATH_LANTERN_CMD] = bytes([0])
        self.vfs[PATH_LED_BRIGHTNESS] = bytes([255, 255, 255, 255])
        self.vfs[PATH_MODE_CONTROL] = bytes([0])

        # 4 Standard Profiles
        defaults = [
            ("Low", 465.0, 45),
            ("Medium", 485.0, 50),
            ("High", 530.0, 55),
            ("ROSIN", 485.0, 60),
        ]
        for slot, (name, temp_f, duration) in enumerate(defaults):
            self.vfs[PATH_PROFILE_NAME_PREFIX.format(slot=slot)] = name.encode("utf-8") + b"\x00"
            self.vfs[PATH_PROFILE_TEMP_PREFIX.format(slot=slot)] = struct.pack("<f", f_to_c(temp_f))
            self.vfs[PATH_PROFILE_TIME_PREFIX.format(slot=slot)] = struct.pack("<I", duration)

        # Boost Settings
        self.vfs[PATH_BOOST_TEMP] = struct.pack("<f", f_to_c(15.0))
        self.vfs[PATH_BOOST_TIME] = struct.pack("<I", 15)

    async def connect(self, timeout: float = 10.0) -> bool:
        """Simulates BLE connect."""
        if self.connect_fail:
            raise ConnectionError(f"Simulated BLE connection failure to {self.address}")
        self.is_connected = True
        return True

    async def disconnect(self):
        """Simulates BLE disconnect."""
        self.is_connected = False

    def trigger_disconnect(self):
        """Simulates an unexpected BLE disconnect from the device side."""
        self.is_connected = False
        if self.disconnected_callback:
            try:
                self.disconnected_callback(self)
            except Exception as e:
                logger.debug(f"Error in disconnected callback: {e}")

    async def read_gatt_char(self, char_uuid: str) -> bytes:
        """Simulates standard GATT characteristic reads."""
        u = char_uuid.lower()
        if u == DEVINFO_SERIAL_UUID.lower():
            return b"MOCK-SN-88219"
        elif u == DEVINFO_FIRMWARE_UUID.lower():
            return b"W.X.Y (FW v1.2.3)"
        elif u == DEVINFO_MODEL_NUMBER_UUID.lower():
            return self.model_number.encode("utf-8")
        elif u == PUFFCO_LORAX_CHAR_VERSION.lower():
            return b"Lorax v1.0.0"
        return b""

    async def start_notify(self, char_uuid: str, callback: Callable[[Any, bytearray], None]):
        """Registers notification listener."""
        self._notify_cb = callback

    async def stop_notify(self, char_uuid: str):
        """Stops notification listener."""
        self._notify_cb = None

    async def write_gatt_char(self, char_uuid: str, data: bytes, response: bool = False):
        """Simulates Lorax command writes and triggers notification replies."""
        if not self.is_connected:
            raise ConnectionError("Cannot write to disconnected device")

        if char_uuid.lower() != PUFFCO_LORAX_CHAR_CMD.lower():
            return

        if len(data) < 3:
            return

        seq = (data[0] & 0xFF) | ((data[1] & 0xFF) << 8)
        opcode = data[2]
        payload = bytes(data[3:])

        if opcode in self.timeout_opcodes:
            # Drop reply to test client timeout logic
            return

        status = 0
        reply_payload = b""

        if opcode == LORAX_OP_GET_ACCESS_SEED:
            status = 0
            reply_payload = self._seed

        elif opcode == LORAX_OP_UNLOCK_ACCESS:
            expected = calculate_lorax_auth_token(self._seed, LORAX_MASTER_HANDSHAKE_KEY)
            if payload == expected and not self.auth_fail:
                status = 0
                reply_payload = b""
            else:
                status = 1
                reply_payload = b""

        elif opcode == LORAX_OP_READ_SHORT:
            if len(payload) >= 4:
                offset, max_len = struct.unpack("<HH", payload[:4])
                path = payload[4:].decode("utf-8", errors="ignore").rstrip("\x00")
                if path in self.vfs:
                    status = 0
                    reply_payload = self.vfs[path][:max_len]
                else:
                    status = 1
                    reply_payload = b""
            else:
                status = 1

        elif opcode == LORAX_OP_WRITE_SHORT:
            if len(payload) >= 3:
                offset, flags = struct.unpack("<HB", payload[:3])
                rest = payload[3:]
                parts = rest.split(b"\x00", 1)
                path = parts[0].decode("utf-8", errors="ignore")
                val = parts[1] if len(parts) > 1 else b""
                self.vfs[path] = val
                self._handle_write_side_effects(path, val)
                status = 0
                reply_payload = b""
            else:
                status = 1

        # Trigger notification reply asynchronously
        if self._notify_cb:
            reply_bytes = bytearray(struct.pack("<HB", seq, status)) + reply_payload
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon(self._notify_cb, PUFFCO_LORAX_CHAR_REPLY, reply_bytes)
            except RuntimeError:
                pass

    def _handle_write_side_effects(self, path: str, val: bytes):
        """Applies realistic state transitions upon Lorax VFS writes."""
        if path == PATH_MODE_CONTROL and len(val) >= 1:
            cmd = val[0]
            if cmd == 0x07:  # Start Session
                self.vfs[PATH_STATE_ID] = bytes([OperatingState.HEAT_PREHEAT.value])
                self.vfs[PATH_TIME_ELAPSED] = struct.pack("<f", 0.0)
                # Increment odometer
                current_dabs = struct.unpack("<I", self.vfs[PATH_ODOMETER_DABS][:4])[0]
                self.vfs[PATH_ODOMETER_DABS] = struct.pack("<I", current_dabs + 1)
            elif cmd == 0x08:  # Stop Session
                self.vfs[PATH_STATE_ID] = bytes([OperatingState.IDLE.value])
                self.vfs[PATH_TIME_ELAPSED] = struct.pack("<f", 0.0)
            elif cmd == 0x09:  # Boost
                # Extend total time by 15s
                total = struct.unpack("<f", self.vfs[PATH_TIME_TOTAL][:4])[0]
                self.vfs[PATH_TIME_TOTAL] = struct.pack("<f", total + 15.0)
            elif cmd == 0x0A:  # Sleep
                self.vfs[PATH_STATE_ID] = bytes([OperatingState.SLEEP.value])

        elif path == PATH_ACTIVE_PROFILE and len(val) >= 1:
            slot = val[0]
            self.vfs[PATH_ACTIVE_PROFILE] = bytes([slot])
            time_path = PATH_PROFILE_TIME_PREFIX.format(slot=slot)
            if time_path in self.vfs:
                duration = struct.unpack("<I", self.vfs[time_path][:4])[0]
                self.vfs[PATH_TIME_TOTAL] = struct.pack("<f", float(duration))

        elif path == PATH_STEALTH_MODE and len(val) >= 1:
            self.vfs[PATH_STEALTH_MODE] = val

        elif path == PATH_LANTERN_CMD and len(val) >= 1:
            self.vfs[PATH_LANTERN_CMD] = val

        elif path == PATH_LED_BRIGHTNESS and len(val) >= 4:
            self.vfs[PATH_LED_BRIGHTNESS] = val


class MockBleakScanner:
    """Simulated BleakScanner returning pre-canned Puffco and non-Puffco BLE devices."""

    def __init__(self, detection_callback: Optional[Callable] = None):
        self.detection_callback = detection_callback
        self._running = False

    async def start(self):
        self._running = True
        if self.detection_callback:
            # Emit Peak Pro (with Lorax service UUID)
            d1 = MockBLEDevice("SAMS PEAK", "F7:11:95:C5:14:9B", -56)
            a1 = MockAdvertisementData(
                local_name="SAMS PEAK",
                service_uuids=[PUFFCO_LORAX_SVC_UUID],
                rssi=-56,
            )
            self.detection_callback(d1, a1)

            # Emit Proxy (with MAC prefix)
            d2 = MockBLEDevice("Puffco Proxy", "00:1B:DC:AA:BB:CC", -72)
            a2 = MockAdvertisementData(
                local_name="Puffco Proxy",
                service_uuids=[],
                rssi=-72,
            )
            self.detection_callback(d2, a2)

            # Emit non-Puffco device (e.g. Smart Watch)
            d3 = MockBLEDevice("Apple Watch", "E4:55:66:77:88:99", -45)
            a3 = MockAdvertisementData(
                local_name="Apple Watch",
                service_uuids=["0000180d-0000-1000-8000-00805f9b34fb"],
                rssi=-45,
            )
            self.detection_callback(d3, a3)

    async def stop(self):
        self._running = False


# ==========================================
# HIGH-LEVEL MOCK CLIENT & DEMO ENGINE
# ==========================================
from .client import PuffcoClient  # noqa: E402


class MockPuffcoClient(PuffcoClient):
    """
    Drop-in subclass of PuffcoClient that runs completely offline with simulated hardware.
    Optionally runs dynamic demo simulation cycles (preheat -> active heat -> fade -> idle).
    """

    def __init__(
        self,
        target_address: str = "F7:11:95:C5:14:9B",
        auto_reconnect: bool = True,
        demo_mode: bool = False,
        auth_fail: bool = False,
        connect_fail: bool = False,
        timeout_opcodes: Optional[List[int]] = None,
        mock_device: Optional[MockBleakClient] = None,
    ):
        super().__init__(target_address=target_address, auto_reconnect=auto_reconnect)
        self.mock_device = mock_device or MockBleakClient(
            address=target_address,
            disconnected_callback=self._on_ble_disconnected,
            auth_fail=auth_fail,
            connect_fail=connect_fail,
            timeout_opcodes=timeout_opcodes,
        )
        # Ensure the mock device has our disconnected callback wired
        self.mock_device.disconnected_callback = self._on_ble_disconnected
        self.demo_mode = demo_mode
        self._demo_task: Optional[asyncio.Task] = None

    async def connect(self, timeout: float = 15.0) -> bool:
        """Connects using the mock BLE device."""
        self._client = self.mock_device  # type: ignore[assignment]
        self._explicit_disconnect = False

        await self.mock_device.connect(timeout=timeout)
        self.telemetry.connected = True
        self.telemetry.mac_address = self.target_address or ""

        # Register Lorax notification
        await self.mock_device.start_notify(PUFFCO_LORAX_CHAR_REPLY, self._on_lorax_notification)

        # Authenticate
        await self._authenticate()

        # Poll static info & initial telemetry
        await self._poll_device_info()
        await self._poll_slow_diagnostics()
        await self._poll_fast_telemetry()

        self._notify_connection_listeners(True)

        if self.demo_mode:
            self._start_demo_simulation()

        return True

    async def disconnect(self):
        """Disconnects and terminates demo loop if active."""
        if self._demo_task and not self._demo_task.done():
            self._demo_task.cancel()
            try:
                await self._demo_task
            except asyncio.CancelledError:
                pass
            self._demo_task = None

        await super().disconnect()

    def _start_demo_simulation(self):
        """Launches continuous animated demo simulation loop."""
        if self._demo_task and not self._demo_task.done():
            return

        async def _demo_loop():
            ambient_temp = 84.5
            target_temp = 485.0
            sesh_duration = 45.0

            while self.is_connected:
                try:
                    # 1. IDLE PHASE (~3 seconds)
                    self.mock_device.vfs[PATH_STATE_ID] = bytes([OperatingState.IDLE.value])
                    for _ in range(15):
                        if not self.is_connected:
                            return
                        curr_f = ambient_temp + random.uniform(-0.4, 0.4)
                        self.mock_device.vfs[PATH_CHAMBER_TEMP] = struct.pack("<f", f_to_c(curr_f))
                        await asyncio.sleep(0.2)

                    # 2. PREHEAT PHASE (~4 seconds)
                    self.mock_device.vfs[PATH_STATE_ID] = bytes([OperatingState.HEAT_PREHEAT.value])
                    self.mock_device.vfs[PATH_TIME_TOTAL] = struct.pack("<f", sesh_duration)
                    self.mock_device.vfs[PATH_TIME_ELAPSED] = struct.pack("<f", 0.0)

                    steps = 20
                    for i in range(steps):
                        if not self.is_connected:
                            return
                        progress = (i + 1) / steps
                        curr_f = ambient_temp + (target_temp - ambient_temp) * (progress**1.3)
                        self.mock_device.vfs[PATH_CHAMBER_TEMP] = struct.pack("<f", f_to_c(curr_f))
                        await asyncio.sleep(0.2)

                    # 3. ACTIVE HEATING PHASE (10 seconds)
                    self.mock_device.vfs[PATH_STATE_ID] = bytes([OperatingState.HEAT_ACTIVE.value])
                    heat_steps = 40
                    for s in range(heat_steps):
                        if not self.is_connected:
                            return
                        elapsed = (s / heat_steps) * sesh_duration
                        self.mock_device.vfs[PATH_TIME_ELAPSED] = struct.pack("<f", elapsed)
                        temp_fluc = target_temp + random.uniform(-1.2, 1.2)
                        self.mock_device.vfs[PATH_CHAMBER_TEMP] = struct.pack(
                            "<f", f_to_c(temp_fluc)
                        )
                        await asyncio.sleep(0.25)

                    # 4. FADE / COOLING PHASE (3 seconds)
                    self.mock_device.vfs[PATH_STATE_ID] = bytes([OperatingState.HEAT_FADE.value])
                    for f_step in range(15):
                        if not self.is_connected:
                            return
                        curr_f = target_temp - (f_step * 15.0)
                        self.mock_device.vfs[PATH_CHAMBER_TEMP] = struct.pack("<f", f_to_c(curr_f))
                        await asyncio.sleep(0.2)

                    # Increment dab count after completed cycle
                    current_dabs = struct.unpack(
                        "<I", self.mock_device.vfs[PATH_ODOMETER_DABS][:4]
                    )[0]
                    self.mock_device.vfs[PATH_ODOMETER_DABS] = struct.pack("<I", current_dabs + 1)

                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug(f"Demo simulation loop note: {exc}")
                    await asyncio.sleep(1.0)

        self._demo_task = asyncio.create_task(_demo_loop())
