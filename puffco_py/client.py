"""
Asynchronous BLE Client for Puffco Peak Pro and Proxy devices.
"""

import asyncio
import logging
import struct
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from bleak import BleakClient, BleakScanner
else:
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        BleakClient = None
        BleakScanner = None

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
)
from .discovery import scan_puffco_devices
from .exceptions import (
    PuffcoConnectionError,
    PuffcoDeviceNotFoundError,
    PuffcoError,
    PuffcoTimeoutError,
)
from .models import (
    ChamberType,
    OperatingState,
    PuffcoProfile,
    PuffcoTelemetry,
    resolve_device_model,
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
        ble_client: Optional[Any] = None,
    ):
        self.target_address = target_address
        self.auto_reconnect = auto_reconnect
        self.telemetry = PuffcoTelemetry()

        self._client: Optional[BleakClient] = ble_client
        self._seq = 0
        self._lock = asyncio.Lock()
        self._pending_replies: Dict[int, asyncio.Future] = {}
        self._auth_completed = False
        self._stop_guard_until = 0.0

        self._streaming = False
        self._stream_task: Optional[asyncio.Task] = None
        self._last_profile_mutation = 0.0
        self._telemetry_listeners: List[Callable[[PuffcoTelemetry], None]] = []
        self._state_listeners: List[Callable[[OperatingState], None]] = []
        self._connection_listeners: List[Callable[[bool], None]] = []

        self._explicit_disconnect = False
        self._reconnect_task: Optional[asyncio.Task] = None

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
        if BleakClient is None and self._client is None:
            raise PuffcoError("Bleak is not installed. Run 'pip install bleak'.")

        self._explicit_disconnect = False

        if not self.target_address and self._client is None:
            logger.info("No target address provided. Scanning for nearby Puffco devices...")
            devices = await scan_puffco_devices(timeout=4.0)
            if not devices:
                raise PuffcoDeviceNotFoundError(
                    "No Puffco devices found nearby. Ensure device is powered on."
                )
            self.target_address = devices[0].address
            logger.info(
                f"Auto-selected strongest device: {devices[0].name} ({self.target_address})"
            )

        logger.info(f"Connecting to Puffco ({self.target_address})...")
        if self._client is None:
            if not self.target_address:
                raise PuffcoConnectionError("Target address is required to connect.")
            self._client = BleakClient(
                self.target_address,
                disconnected_callback=self._on_ble_disconnected,
            )
        elif hasattr(self._client, "disconnected_callback"):
            self._client.disconnected_callback = self._on_ble_disconnected

        try:
            await self._client.connect(timeout=timeout)
        except Exception as exc:
            self.telemetry.connected = False
            self.telemetry.operating_state = OperatingState.DISCONNECTED
            raise PuffcoConnectionError(
                f"Failed to connect to Puffco ({self.target_address}): {exc}"
            ) from exc

        self.telemetry.connected = True
        self.telemetry.mac_address = self.target_address or ""

        # Keep connection alive by reading Lorax version if present
        try:
            await self._client.read_gatt_char(PUFFCO_LORAX_CHAR_VERSION)
        except Exception:
            pass

        # Subscribe to Lorax reply notifications
        try:
            await self._client.start_notify(PUFFCO_LORAX_CHAR_REPLY, self._on_lorax_notification)
            await asyncio.sleep(0.05)
        except Exception as exc:
            await self.disconnect()
            raise PuffcoConnectionError(f"Failed to subscribe to Lorax replies: {exc}") from exc

        # Authenticate with SHA-256 challenge-response
        await self._authenticate()

        # Read static device diagnostics
        await self._poll_device_info()
        await self._poll_slow_diagnostics()
        await self._poll_fast_telemetry()

        self._notify_connection_listeners(True)
        logger.info(f"Connected and authenticated with {self.telemetry.device_name}!")
        return True

    async def disconnect(self):
        """Stops telemetry stream and cleanly disconnects from the device."""
        self._explicit_disconnect = True
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            self._reconnect_task = None

        await self.stop_telemetry_stream()
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.debug(f"Disconnect error: {e}")

        self.telemetry.connected = False
        self.telemetry.operating_state = OperatingState.DISCONNECTED
        self._client = None
        self._notify_connection_listeners(False)

    def _on_ble_disconnected(self, _client):
        """Callback invoked by Bleak upon unexpected BLE connection drop."""
        logger.warning(f"Puffco device ({self.target_address}) disconnected unexpectedly.")
        self.telemetry.connected = False
        self.telemetry.operating_state = OperatingState.DISCONNECTED
        self._notify_connection_listeners(False)
        self._notify_listeners()

        if self.auto_reconnect and not self._explicit_disconnect:
            if self._reconnect_task is None or self._reconnect_task.done():
                try:
                    loop = asyncio.get_running_loop()
                    self._reconnect_task = loop.create_task(self._reconnect_loop())
                except RuntimeError:
                    pass

    async def _reconnect_loop(self):
        """Background loop attempting reconnect with exponential backoff."""
        delay = 2.0
        max_delay = 15.0
        while self.auto_reconnect and not self._explicit_disconnect and not self.is_connected:
            logger.info(f"Attempting to reconnect to Puffco in {delay:.1f}s...")
            await asyncio.sleep(delay)
            if self._explicit_disconnect:
                break
            try:
                await self.connect(timeout=10.0)
                logger.info(f"Reconnected successfully to {self.telemetry.device_name}!")
                break
            except Exception as e:
                logger.debug(f"Reconnect attempt failed: {e}")
                delay = min(delay * 1.5, max_delay)

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
            else:
                logger.warning(f"Lorax get seed returned status {status}")
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

    async def _send_lorax_cmd(
        self, opcode: int, payload: bytes = b"", timeout: float = 1.5
    ) -> tuple:
        if not self._client or not self._client.is_connected:
            raise PuffcoConnectionError("Device is not connected")

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
                try:
                    status, reply_payload = await asyncio.wait_for(fut, timeout=timeout)
                    return status, reply_payload
                except asyncio.TimeoutError as exc:
                    raise PuffcoTimeoutError(
                        f"Lorax command opcode 0x{opcode:02X} (seq {seq}) timed out after {timeout}s"
                    ) from exc
            finally:
                self._pending_replies.pop(seq, None)

    async def read_path(self, path: str, max_len: int = 240) -> bytes:
        """Reads a virtual file path on the device over Lorax VFS."""
        payload = pack_lorax_read_short(path, max_len=max_len)
        try:
            status, data = await self._send_lorax_cmd(LORAX_OP_READ_SHORT, payload)
            if status != 0:
                return b""
            return data
        except (PuffcoError, asyncio.TimeoutError) as e:
            logger.debug(f"Read path '{path}' failed: {e}")
            return b""

    async def write_path(self, path: str, val: bytes) -> bool:
        """Writes binary data to a virtual file path on the device over Lorax VFS."""
        payload = pack_lorax_write_short(path, val)
        try:
            status, _ = await self._send_lorax_cmd(LORAX_OP_WRITE_SHORT, payload)
            return status == 0
        except (PuffcoError, asyncio.TimeoutError) as e:
            logger.debug(f"Write path '{path}' failed: {e}")
            return False

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
        model_str = ""
        try:
            mod = await self._client.read_gatt_char(DEVINFO_MODEL_NUMBER_UUID)
            if mod:
                model_str = mod.decode("utf-8", errors="ignore").strip()
        except Exception:
            pass

        self._model_number_raw = model_str
        self.telemetry.device_model = resolve_device_model(
            name=self.telemetry.device_name,
            model_number=model_str,
            firmware=self.telemetry.firmware_version,
        )

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
                elap = (
                    struct.unpack("<f", elap_b[:4])[0]
                    if len(elap_b) == 4
                    else struct.unpack("<I", elap_b[:4])[0]
                )
                tott = (
                    struct.unpack("<f", tott_b[:4])[0]
                    if len(tott_b) == 4
                    else struct.unpack("<I", tott_b[:4])[0]
                )
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
                self.telemetry.device_model = resolve_device_model(
                    name=clean,
                    model_number=getattr(self, "_model_number_raw", ""),
                    firmware=self.telemetry.firmware_version,
                )

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
        poll_start = time.time()
        if not self.telemetry.profiles or len(self.telemetry.profiles) < 4:
            self.telemetry.profiles = [
                PuffcoProfile(slot=i, name=f"Profile {i + 1}", target_temp_f=0, duration_s=45)
                for i in range(4)
            ]

        for slot in range(4):
            pn_b = await self.read_path(PATH_PROFILE_NAME_PREFIX.format(slot=slot))
            pt_b = await self.read_path(PATH_PROFILE_TEMP_PREFIX.format(slot=slot))
            ptime_b = await self.read_path(PATH_PROFILE_TIME_PREFIX.format(slot=slot))

            if self._last_profile_mutation < poll_start:
                if pn_b:
                    clean_name = pn_b.decode("utf-8", errors="ignore").rstrip("\x00").strip()
                    if clean_name:
                        self.telemetry.profiles[slot].name = clean_name
                if pt_b:
                    t_val = int(round(parse_temp(pt_b)))
                    if t_val > 0:
                        self.telemetry.profiles[slot].target_temp_f = t_val
                if ptime_b and len(ptime_b) >= 4:
                    d_val = struct.unpack("<I", ptime_b[:4])[0]
                    if d_val > 0:
                        self.telemetry.profiles[slot].duration_s = d_val

        if self._last_profile_mutation < poll_start:
            if 0 <= self.telemetry.active_profile < len(self.telemetry.profiles):
                active_t = self.telemetry.profiles[self.telemetry.active_profile].target_temp_f
                if active_t > 0:
                    self.telemetry.target_temp_f = float(active_t)

        # Stealth Mode
        stlth_b = await self.read_path(PATH_STEALTH_MODE)
        if stlth_b and len(stlth_b) >= 1:
            self.telemetry.stealth_mode = bool(stlth_b[0])

        # Boost Settings
        try:
            bst_t_b = await self.read_path(PATH_BOOST_TEMP)
            if bst_t_b:
                self.telemetry.boost_temp_f = int(round(parse_temp(bst_t_b)))
            bst_time_b = await self.read_path(PATH_BOOST_TIME)
            if bst_time_b and len(bst_time_b) >= 4:
                self.telemetry.boost_duration_s = struct.unpack("<I", bst_time_b[:4])[0]
        except Exception:
            pass

    # ==========================================
    # STREAMING LOOP & LISTENERS
    # ==========================================
    def add_telemetry_listener(self, callback: Callable[[PuffcoTelemetry], None]):
        """Registers a listener for live telemetry updates."""
        self._telemetry_listeners.append(callback)

    def remove_telemetry_listener(self, callback: Callable[[PuffcoTelemetry], None]):
        """Removes a registered telemetry listener."""
        if callback in self._telemetry_listeners:
            self._telemetry_listeners.remove(callback)

    def add_state_listener(self, callback: Callable[[OperatingState], None]):
        """Registers a listener for operating state changes."""
        self._state_listeners.append(callback)

    def remove_state_listener(self, callback: Callable[[OperatingState], None]):
        """Removes a registered operating state listener."""
        if callback in self._state_listeners:
            self._state_listeners.remove(callback)

    def add_connection_listener(self, callback: Callable[[bool], None]):
        """Registers a listener for connection status changes (connected=True/False)."""
        self._connection_listeners.append(callback)

    def remove_connection_listener(self, callback: Callable[[bool], None]):
        """Removes a registered connection status listener."""
        if callback in self._connection_listeners:
            self._connection_listeners.remove(callback)

    def _notify_connection_listeners(self, connected: bool):
        for cb in self._connection_listeners:
            try:
                cb(connected)
            except Exception as e:
                logger.debug(f"Connection listener error: {e}")

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
            last_slow = time.time()
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
        self._stop_guard_until = 0.0
        success = await self.write_path(PATH_MODE_CONTROL, bytes([0x07]))
        if success:
            self.telemetry.operating_state = OperatingState.HEAT_PREHEAT
            self._notify_listeners()
        return success

    async def stop_session(self) -> bool:
        """Aborts / stops the active heating session."""
        logger.info("Aborting session...")
        self._stop_guard_until = time.time() + 2.0
        success = await self.write_path(PATH_MODE_CONTROL, bytes([0x08]))
        if success:
            self.telemetry.operating_state = OperatingState.IDLE
            self.telemetry.time_remaining = 0
            self._notify_listeners()
        return success

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
            self._last_profile_mutation = time.time()
            self.telemetry.active_profile = slot
            if self.telemetry.profiles and slot < len(self.telemetry.profiles):
                t = self.telemetry.profiles[slot].target_temp_f
                if t > 0:
                    self.telemetry.target_temp_f = float(t)
            self._notify_listeners()
        return success

    async def set_temperature(self, temp_f: float, slot: Optional[int] = None) -> bool:
        """Sets target temperature for the active profile (or specified slot 0..3)."""
        c = f_to_c(temp_f)
        target_slot = self.telemetry.active_profile if slot is None else max(0, min(3, int(slot)))
        path = PATH_PROFILE_TEMP_PREFIX.format(slot=target_slot)

        if "proxy" in self.telemetry.device_name.lower():
            payload = struct.pack("<i", int(round(c * 10.0)))
        else:
            payload = struct.pack("<f", c)

        success = await self.write_path(path, payload)
        if success:
            self._last_profile_mutation = time.time()
            if self.telemetry.profiles and target_slot < len(self.telemetry.profiles):
                self.telemetry.profiles[target_slot].target_temp_f = int(round(temp_f))
            if target_slot == self.telemetry.active_profile:
                self.telemetry.target_temp_f = temp_f
            self._notify_listeners()
        return success

    async def set_profile_duration(self, slot: int, seconds: int) -> bool:
        """Sets the session duration in seconds (15..180s) for a profile slot."""
        slot = max(0, min(3, int(slot)))
        seconds = max(15, min(180, int(seconds)))
        logger.info(f"Setting profile {slot} duration to {seconds}s")
        path = PATH_PROFILE_TIME_PREFIX.format(slot=slot)
        payload = struct.pack("<I", seconds)
        success = await self.write_path(path, payload)
        if success:
            self._last_profile_mutation = time.time()
            if self.telemetry.profiles and slot < len(self.telemetry.profiles):
                self.telemetry.profiles[slot].duration_s = seconds
            if slot == self.telemetry.active_profile:
                self.telemetry.total_time = seconds
            self._notify_listeners()
        return success

    async def set_profile_name(self, slot: int, name: str) -> bool:
        """Sets the profile display name (up to 16 chars) for a profile slot."""
        slot = max(0, min(3, int(slot)))
        clean_name = name.strip()[:16]
        logger.info(f"Setting profile {slot} name to '{clean_name}'")
        path = PATH_PROFILE_NAME_PREFIX.format(slot=slot)
        payload = clean_name.encode("utf-8")
        success = await self.write_path(path, payload)
        if success:
            self._last_profile_mutation = time.time()
            if self.telemetry.profiles and slot < len(self.telemetry.profiles):
                self.telemetry.profiles[slot].name = clean_name
            self._notify_listeners()
        return success

    async def save_profile(self, slot: int, profile: PuffcoProfile) -> bool:
        """Saves name, temperature, and duration for a given profile slot."""
        slot = max(0, min(3, int(slot)))
        ok_name = await self.set_profile_name(slot, profile.name)
        ok_temp = await self.set_temperature(float(profile.target_temp_f), slot=slot)
        ok_dur = await self.set_profile_duration(slot, profile.duration_s)
        success = bool(ok_name and ok_temp and ok_dur)
        if success:
            self._last_profile_mutation = time.time()
            if self.telemetry.profiles and slot < len(self.telemetry.profiles):
                self.telemetry.profiles[slot].name = profile.name.strip()[:16]
                self.telemetry.profiles[slot].target_temp_f = int(round(profile.target_temp_f))
                self.telemetry.profiles[slot].duration_s = profile.duration_s
            self._notify_listeners()
        return success

    async def set_boost_temperature(self, temp_f: float) -> bool:
        """Sets boost session temperature increment in °F (e.g. 5 to 50°F)."""
        temp_f = max(5.0, min(50.0, float(temp_f)))
        logger.info(f"Setting boost temperature increment to +{temp_f:.0f}°F")
        c = temp_f * 5.0 / 9.0
        if "proxy" in self.telemetry.device_name.lower():
            payload = struct.pack("<i", int(round(c * 10.0)))
        else:
            payload = struct.pack("<f", c)
        success = await self.write_path(PATH_BOOST_TEMP, payload)
        if success:
            self.telemetry.boost_temp_f = int(round(temp_f))
            self._notify_listeners()
        return success

    async def set_boost_duration(self, seconds: int) -> bool:
        """Sets boost session time extension in seconds (e.g. 5 to 60s)."""
        seconds = max(5, min(60, int(seconds)))
        logger.info(f"Setting boost duration extension to +{seconds}s")
        payload = struct.pack("<I", seconds)
        success = await self.write_path(PATH_BOOST_TIME, payload)
        if success:
            self.telemetry.boost_duration_s = seconds
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
        payload = bytes(
            [
                max(0, min(255, int(base))),
                max(0, min(255, int(mid))),
                max(0, min(255, int(glass))),
                max(0, min(255, int(logo))),
            ]
        )
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
        return self.telemetry.lifetime_dabs
