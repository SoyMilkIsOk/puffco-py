"""
Asynchronous BLE Client for Puffco Peak Pro and Proxy devices.
"""

import asyncio
import logging
import struct
import time
from typing import Any, Callable, Dict, List, Optional

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    BleakClient = None
    BleakScanner = None

from .constants import (
    DEVINFO_FIRMWARE_UUID,
    DEVINFO_SERIAL_UUID,
    LORAX_MASTER_HANDSHAKE_KEY,
    LORAX_OP_GET_ACCESS_SEED,
    LORAX_OP_READ_SHORT,
    LORAX_OP_UNLOCK_ACCESS,
    LORAX_OP_WRITE_SHORT,
    PATH_ACTIVE_PROFILE,
    PATH_BATTERY_CHARGE_STAT,
    PATH_BATTERY_SOC,
    PATH_CHAMBER_TEMP,
    PATH_CHAMBER_TYPE,
    PATH_DEVICE_NAME,
    PATH_MODE_CONTROL,
    PATH_ODOMETER_DABS,
    PATH_PROFILE_NAME_PREFIX,
    PATH_PROFILE_TEMP_PREFIX,
    PATH_PROFILE_TIME_PREFIX,
    PATH_STATE_ID,
    PATH_STEALTH_MODE,
    PATH_LANTERN_CMD,
    PATH_LED_BRIGHTNESS,
    PATH_TIME_ELAPSED,
    PATH_TIME_TOTAL,
    PUFFCO_LORAX_CHAR_CMD,
    PUFFCO_LORAX_CHAR_REPLY,
    PUFFCO_LORAX_CHAR_VERSION,
)
from .discovery import scan_puffco_devices
from .models import (
    ChamberType,
    OperatingState,
    PuffcoProfile,
    PuffcoTelemetry,
)
from .protocol import (
    calculate_lorax_auth_token,
    f_to_c,
    pack_lorax_cmd,
    pack_lorax_read_short,
    pack_lorax_write_short,
    parse_battery,
    parse_dabs,
    parse_temp,
    unpack_lorax_reply,
)

logger = logging.getLogger("puffco_py.client")


class PuffcoClient:
    """
    High-level, asynchronous Python BLE client for Puffco Peak Pro and Proxy.
    
    Usage:
        client = PuffcoClient("F7:11:95:C5:14:9B")
        await client.connect()
        print(client.telemetry.summary())
        await client.start_session()
        await client.disconnect()
    """

    def __init__(
        self,
        target_address: Optional[str] = None,
        auto_reconnect: bool = True,
    ):
        self.target_address = target_address
        self.auto_reconnect = auto_reconnect
        self.telemetry = PuffcoTelemetry()

        self._client: Optional[BleakClient] = None
        self._seq = 0
        self._lock = asyncio.Lock()
        self._pending_replies: Dict[int, asyncio.Future] = {}
        self._auth_completed = False
        self._stop_guard_until = 0.0

        self._streaming = False
        self._stream_task: Optional[asyncio.Task] = None
        self._telemetry_listeners: List[Callable[[PuffcoTelemetry], None]] = []
        self._state_listeners: List[Callable[[OperatingState], None]] = []

    # ==========================================
    # CONTEXT MANAGER
    # ==========================================
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    # ==========================================
    # CONNECTION & AUTHENTICATION
    # ==========================================
    async def connect(self, timeout: float = 15.0) -> bool:
        """Connects to the Puffco device and completes the Lorax authentication handshake."""
        if BleakClient is None:
            raise RuntimeError("Bleak is not installed. Run 'pip install bleak'.")

        if not self.target_address:
            logger.info("No target address provided. Scanning for nearby Puffco devices...")
            devices = await scan_puffco_devices(timeout=4.0)
            if not devices:
                raise RuntimeError("No Puffco devices found nearby. Ensure device is powered on.")
            self.target_address = devices[0].address
            logger.info(f"Auto-selected strongest device: {devices[0].name} ({self.target_address})")

        logger.info(f"Connecting to Puffco ({self.target_address})...")
        self._client = BleakClient(self.target_address)
        await self._client.connect(timeout=timeout)

        self.telemetry.connected = True
        self.telemetry.mac_address = self.target_address

        # Keep connection alive by reading Lorax version if present
        try:
            await self._client.read_gatt_char(PUFFCO_LORAX_CHAR_VERSION)
        except Exception:
            pass

        # Subscribe to Lorax reply notifications
        await self._client.start_notify(PUFFCO_LORAX_CHAR_REPLY, self._on_lorax_notification)
        await asyncio.sleep(0.05)

        # Authenticate with SHA-256 challenge-response
        await self._authenticate()

        # Read static device diagnostics
        await self._poll_device_info()
        await self._poll_slow_diagnostics()
        await self._poll_fast_telemetry()

        logger.info(f"Connected and authenticated with {self.telemetry.device_name}!")
        return True

    async def disconnect(self):
        """Stops telemetry stream and cleanly disconnects from the device."""
        await self.stop_telemetry_stream()
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.debug(f"Disconnect error: {e}")
        self.telemetry.connected = False
        self.telemetry.operating_state = OperatingState.DISCONNECTED
        self._client = None

    @property
    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected)

    async def _authenticate(self):
        """Executes Lorax dual SHA-256 challenge-response handshake."""
        try:
            status, seed = await self._send_lorax_cmd(LORAX_OP_GET_ACCESS_SEED)
            if status == 0 and len(seed) >= 16:
                token = calculate_lorax_auth_token(seed, LORAX_MASTER_HANDSHAKE_KEY)
                status, _ = await self._send_lorax_cmd(LORAX_OP_UNLOCK_ACCESS, token)
                if status == 0:
                    self._auth_completed = True
                    logger.debug("Lorax handshake successful!")
                    return
                else:
                    logger.warning(f"Lorax unlock returned status code {status}")
        except Exception as e:
            logger.warning(f"Lorax auth handshake note: {e}")
        self._auth_completed = True

    # ==========================================
    # LORAX VFS PACKET PROTOCOL
    # ==========================================
    def _on_lorax_notification(self, _, data: bytearray):
        try:
            seq, status, payload = unpack_lorax_reply(bytes(data))
            if seq in self._pending_replies and not self._pending_replies[seq].done():
                self._pending_replies[seq].set_result((status, payload))
        except Exception as e:
            logger.debug(f"Error handling reply packet: {e}")

    async def _send_lorax_cmd(self, opcode: int, payload: bytes = b"", timeout: float = 1.5) -> tuple:
        if not self._client or not self._client.is_connected:
            raise RuntimeError("Device is not connected")

        async with self._lock:
            self._seq = (self._seq + 1) & 0xFFFF
            if self._seq == 0:
                self._seq = 1

            seq = self._seq
            pkt = pack_lorax_cmd(seq, opcode, payload)

            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            self._pending_replies[seq] = fut

            try:
                await self._client.write_gatt_char(PUFFCO_LORAX_CHAR_CMD, pkt, response=False)
                status, reply_payload = await asyncio.wait_for(fut, timeout=timeout)
                return status, reply_payload
            finally:
                self._pending_replies.pop(seq, None)

    async def read_path(self, path: str, max_len: int = 240) -> bytes:
        """Reads a virtual file path on the device over Lorax VFS."""
        payload = pack_lorax_read_short(path, max_len=max_len)
        status, data = await self._send_lorax_cmd(LORAX_OP_READ_SHORT, payload)
        if status != 0:
            return b""
        return data

    async def write_path(self, path: str, val: bytes) -> bool:
        """Writes binary data to a virtual file path on the device over Lorax VFS."""
        payload = pack_lorax_write_short(path, val)
        status, _ = await self._send_lorax_cmd(LORAX_OP_WRITE_SHORT, payload)
        return status == 0

    # ==========================================
    # TELEMETRY POLLING ENGINE
    # ==========================================
    async def poll(self) -> PuffcoTelemetry:
        """Performs a single polling cycle of all telemetry metrics."""
        await self._poll_fast_telemetry()
        await self._poll_slow_diagnostics()
        self._notify_listeners()
        return self.telemetry

    async def _poll_device_info(self):
        """Reads static device information GATT characteristics."""
        if not self._client:
            return
        try:
            ser = await self._client.read_gatt_char(DEVINFO_SERIAL_UUID)
            if ser:
                self.telemetry.serial_number = ser.decode("utf-8", errors="ignore").strip()
        except Exception:
            pass
        try:
            fw = await self._client.read_gatt_char(DEVINFO_FIRMWARE_UUID)
            if fw:
                self.telemetry.firmware_version = fw.decode("utf-8", errors="ignore").strip()
        except Exception:
            pass

    async def _poll_fast_telemetry(self):
        """Reads fast real-time metrics (operating state, temperature, countdown timer)."""
        prev_state = self.telemetry.operating_state

        # 1. State
        st = await self.read_path(PATH_STATE_ID)
        if st and len(st) >= 1:
            raw_st = st[0]
            guarded = time.time() < self._stop_guard_until
            if raw_st in (5, 13, 0):
                self.telemetry.operating_state = OperatingState.IDLE
                self._stop_guard_until = 0.0
            elif not guarded:
                try:
                    self.telemetry.operating_state = OperatingState(raw_st)
                except ValueError:
                    self.telemetry.operating_state = OperatingState.IDLE

        # 2. Chamber Temperature
        temp_b = await self.read_path(PATH_CHAMBER_TEMP)
        if temp_b:
            t_f = parse_temp(temp_b)
            if t_f > 0.0:
                self.telemetry.live_temp_f = t_f

        # 3. Heating Sesh Countdown
        if self.telemetry.is_heating:
            elap_b = await self.read_path(PATH_TIME_ELAPSED)
            tott_b = await self.read_path(PATH_TIME_TOTAL)
            if len(elap_b) >= 4 and len(tott_b) >= 4:
                elap = struct.unpack("<f", elap_b[:4])[0] if len(elap_b) == 4 else struct.unpack("<I", elap_b[:4])[0]
                tott = struct.unpack("<f", tott_b[:4])[0] if len(tott_b) == 4 else struct.unpack("<I", tott_b[:4])[0]
                if tott > 300:
                    tott /= 1000.0
                    elap /= 1000.0
                self.telemetry.total_time = int(round(tott))
                self.telemetry.time_remaining = max(0, int(round(tott - elap)))

        # Notify state change
        if self.telemetry.operating_state != prev_state:
            for cb in self._state_listeners:
                try:
                    cb(self.telemetry.operating_state)
                except Exception as e:
                    logger.debug(f"State listener error: {e}")

    async def _poll_slow_diagnostics(self):
        """Reads hardware diagnostics (battery, dabs, profiles, chamber)."""
        # Device Name
        name_b = await self.read_path(PATH_DEVICE_NAME)
        if name_b:
            clean = name_b.decode("utf-8", errors="ignore").rstrip("\x00").strip()
            if clean:
                self.telemetry.device_name = clean

        # Battery
        soc_b = await self.read_path(PATH_BATTERY_SOC)
        if soc_b:
            self.telemetry.battery_pct = parse_battery(soc_b)

        chg_b = await self.read_path(PATH_BATTERY_CHARGE_STAT)
        if chg_b and len(chg_b) >= 1:
            self.telemetry.is_charging = chg_b[0] in (0, 1, 2)

        # Chamber
        ch_b = await self.read_path(PATH_CHAMBER_TYPE)
        if ch_b and len(ch_b) >= 1:
            try:
                self.telemetry.chamber_type = ChamberType(ch_b[0])
            except ValueError:
                self.telemetry.chamber_type = ChamberType.CHAMBER_3DXL
        elif "proxy" in self.telemetry.device_name.lower():
            self.telemetry.chamber_type = ChamberType.TOAD

        # Total Dabs
        dabs_b = await self.read_path(PATH_ODOMETER_DABS)
        if dabs_b:
            self.telemetry.lifetime_dabs = parse_dabs(dabs_b)

        # Active Profile
        prof_b = await self.read_path(PATH_ACTIVE_PROFILE)
        if prof_b and len(prof_b) >= 1:
            self.telemetry.active_profile = prof_b[0]

        # Profiles (Slots 0..3)
        profiles = []
        for slot in range(4):
            pn_b = await self.read_path(PATH_PROFILE_NAME_PREFIX.format(slot=slot))
            pt_b = await self.read_path(PATH_PROFILE_TEMP_PREFIX.format(slot=slot))
            ptime_b = await self.read_path(PATH_PROFILE_TIME_PREFIX.format(slot=slot))

            p_name = pn_b.decode("utf-8", errors="ignore").rstrip("\x00").strip() if pn_b else f"Profile {slot+1}"
            p_temp = int(round(parse_temp(pt_b))) if pt_b else 0
            p_time = struct.unpack("<I", ptime_b[:4])[0] if ptime_b and len(ptime_b) >= 4 else 45

            profiles.append(PuffcoProfile(slot=slot, name=p_name, target_temp_f=p_temp, duration_s=p_time))

        if profiles:
            self.telemetry.profiles = profiles
            if 0 <= self.telemetry.active_profile < len(profiles):
                active_t = profiles[self.telemetry.active_profile].target_temp_f
                if active_t > 0:
                    self.telemetry.target_temp_f = float(active_t)

        # Stealth Mode
        stlth_b = await self.read_path(PATH_STEALTH_MODE)
        if stlth_b and len(stlth_b) >= 1:
            self.telemetry.stealth_mode = bool(stlth_b[0])

    # ==========================================
    # STREAMING LOOP & LISTENERS
    # ==========================================
    def add_telemetry_listener(self, callback: Callable[[PuffcoTelemetry], None]):
        """Registers a listener for live telemetry updates."""
        self._telemetry_listeners.append(callback)

    def add_state_listener(self, callback: Callable[[OperatingState], None]):
        """Registers a listener for operating state changes."""
        self._state_listeners.append(callback)

    def _notify_listeners(self):
        for cb in self._telemetry_listeners:
            try:
                cb(self.telemetry)
            except Exception as e:
                logger.debug(f"Telemetry listener error: {e}")

    async def start_telemetry_stream(
        self,
        interval_heating: float = 0.06,
        interval_idle: float = 0.25,
        slow_poll_interval: float = 5.0,
    ):
        """Launches background adaptive polling loop."""
        if self._streaming:
            return
        self._streaming = True

        async def _loop():
            last_slow = 0.0
            while self._streaming and self.is_connected:
                try:
                    await self._poll_fast_telemetry()
                    if time.time() - last_slow > slow_poll_interval:
                        last_slow = time.time()
                        await self._poll_slow_diagnostics()

                    self._notify_listeners()

                    delay = interval_heating if self.telemetry.is_heating else interval_idle
                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.debug(f"Telemetry stream loop error: {e}")
                    await asyncio.sleep(1.0)

        self._stream_task = asyncio.create_task(_loop())

    async def stop_telemetry_stream(self):
        """Stops background streaming loop."""
        self._streaming = False
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
        self._stream_task = None

    # ==========================================
    # SESSION COMMANDS
    # ==========================================
    async def start_session(self) -> bool:
        """Starts a heating session with the active profile."""
        logger.info("Starting heating session...")
        self.telemetry.operating_state = OperatingState.HEAT_PREHEAT
        self._notify_listeners()
        return await self.write_path(PATH_MODE_CONTROL, bytes([0x07]))

    async def stop_session(self) -> bool:
        """Aborts / stops the active heating session."""
        logger.info("Aborting session...")
        self.telemetry.operating_state = OperatingState.IDLE
        self.telemetry.time_remaining = 0
        self._stop_guard_until = time.time() + 2.0
        self._notify_listeners()
        return await self.write_path(PATH_MODE_CONTROL, bytes([0x08]))

    async def boost(self) -> bool:
        """Triggers heat boost (+time and +temp) during an active session."""
        logger.info("Sending heat boost...")
        return await self.write_path(PATH_MODE_CONTROL, bytes([0x09]))

    async def set_profile(self, slot: int) -> bool:
        """Selects active heat profile slot (0..3)."""
        slot = max(0, min(3, int(slot)))
        logger.info(f"Setting active profile to slot {slot}")
        success = await self.write_path(PATH_ACTIVE_PROFILE, bytes([slot]))
        if success:
            self.telemetry.active_profile = slot
            if self.telemetry.profiles and slot < len(self.telemetry.profiles):
                t = self.telemetry.profiles[slot].target_temp_f
                if t > 0:
                    self.telemetry.target_temp_f = float(t)
            self._notify_listeners()
        return success

    async def set_temperature(self, temp_f: float) -> bool:
        """Sets target temperature for the active profile."""
        c = f_to_c(temp_f)
        slot = self.telemetry.active_profile
        path = PATH_PROFILE_TEMP_PREFIX.format(slot=slot)

        if "proxy" in self.telemetry.device_name.lower():
            payload = struct.pack("<i", int(round(c * 10.0)))
        else:
            payload = struct.pack("<f", c)

        success = await self.write_path(path, payload)
        if success:
            self.telemetry.target_temp_f = temp_f
            self._notify_listeners()
        return success

    async def set_stealth_mode(self, enabled: bool) -> bool:
        """Toggles stealth lighting mode."""
        logger.info(f"Setting stealth mode to {enabled}")
        success = await self.write_path(PATH_STEALTH_MODE, bytes([0x01 if enabled else 0x00]))
        if success:
            self.telemetry.stealth_mode = enabled
            self._notify_listeners()
        return success

    async def start_lantern(self) -> bool:
        """Activates continuous ambient lantern lighting mode."""
        logger.info("Starting lantern mode...")
        return await self.write_path(PATH_LANTERN_CMD, bytes([0x01]))

    async def stop_lantern(self) -> bool:
        """Deactivates lantern lighting mode."""
        logger.info("Stopping lantern mode...")
        return await self.write_path(PATH_LANTERN_CMD, bytes([0x00]))

    async def set_led_brightness(
        self,
        base: int = 255,
        mid: int = 255,
        glass: int = 255,
        logo: int = 255,
    ) -> bool:
        """
        Sets brightness (0..255) for all 4 LED hardware zones:
        base, mid chamber, glass stem, and logo.
        """
        logger.info(f"Setting LED brightness (base={base}, mid={mid}, glass={glass}, logo={logo})")
        payload = bytes([
            max(0, min(255, int(base))),
            max(0, min(255, int(mid))),
            max(0, min(255, int(glass))),
            max(0, min(255, int(logo))),
        ])
        return await self.write_path(PATH_LED_BRIGHTNESS, payload)

    async def enter_sleep_mode(self) -> bool:
        """Places the device into ultra-low-power sleep state."""
        logger.info("Entering sleep mode...")
        return await self.write_path(PATH_MODE_CONTROL, bytes([0x0A]))

    async def power_off(self) -> bool:
        """Sends master power down command to turn off hardware completely."""
        logger.info("Powering off device...")
        return await self.write_path(PATH_MODE_CONTROL, bytes([0x0B]))

    async def get_battery_level(self) -> int:
        """Direct one-shot query for battery SOC percentage (0..100)."""
        data = await self.read_path(PATH_BATTERY_SOC)
        return int(data[0]) if data else int(self.telemetry.battery_pct)

    async def get_total_dabs(self) -> int:
        """Direct one-shot query for lifetime total odometer count."""
        data = await self.read_path(PATH_ODOMETER_DABS)
        if data and len(data) >= 4:
            return struct.unpack("<I", data[:4])[0]
        return self.telemetry.total_dabs
