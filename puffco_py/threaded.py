"""
Synchronous, thread-safe wrapper around PuffcoClient for desktop GUIs, menu bar apps,
and synchronous scripts.
"""

import asyncio
import logging
import threading
from typing import Any, Callable, List, Optional

from .client import PuffcoClient
from .discovery import PuffcoDiscoveredDevice, scan_puffco_devices
from .models import OperatingState, PuffcoTelemetry

logger = logging.getLogger("puffco_py.threaded")


class ThreadedPuffcoClient:
    """
    Synchronous, thread-safe wrapper around PuffcoClient that runs Bleak in a
    dedicated, persistent background worker thread with its own event loop.
    
    Ideal for integration with macOS menu apps (rumps), Tkinter, PyQt, or simple sync scripts.
    
    Usage:
        client = ThreadedPuffcoClient("F7:11:95:C5:14:9B")
        client.start()
        client.wait_connected(timeout=10.0)
        print(client.telemetry.summary())
        client.start_session()
        time.sleep(5)
        client.stop()
    """

    def __init__(self, target_address: Optional[str] = None):
        self.target_address = target_address
        self._client: Optional[PuffcoClient] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._connected_event = threading.Event()
        self._telemetry_listeners: List[Callable[[PuffcoTelemetry], None]] = []

    @property
    def is_connected(self) -> bool:
        return self._connected_event.is_set()

    @property
    def telemetry(self) -> PuffcoTelemetry:
        if self._client:
            return self._client.telemetry
        return PuffcoTelemetry()

    def add_telemetry_listener(self, callback: Callable[[PuffcoTelemetry], None]):
        """Registers a callback function invoked on each telemetry update."""
        self._telemetry_listeners.append(callback)

    def remove_telemetry_listener(self, callback: Callable[[PuffcoTelemetry], None]):
        """Removes a registered telemetry callback."""
        if callback in self._telemetry_listeners:
            self._telemetry_listeners.remove(callback)

    # ==========================================
    # WORKER THREAD ENGINE
    # ==========================================
    def start(self):
        """Starts the persistent background worker thread."""
        if self._running:
            return
        self._running = True
        self._connected_event.clear()

        ready_event = threading.Event()
        self._thread = threading.Thread(
            target=self._worker_thread, args=(ready_event,), daemon=True
        )
        self._thread.start()
        ready_event.wait(timeout=5.0)

        # Only trigger connection if an explicit address was provided at initialization
        if self.target_address and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_connect(), self._loop)

    def _worker_thread(self, ready_event: threading.Event):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._async_lock = asyncio.Lock()
        ready_event.set()
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def stop(self):
        """Cleanly disconnects and terminates the background worker thread."""
        if not self._running:
            return
        self._running = False
        self._connected_event.clear()

        if self._loop and self._loop.is_running():
            try:
                fut = asyncio.run_coroutine_threadsafe(self._async_disconnect(), self._loop)
                fut.result(timeout=2.5)
            except Exception:
                pass
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    # ==========================================
    # SCANNING & CONNECTION
    # ==========================================
    def scan_devices(self, timeout: float = 4.0) -> List[PuffcoDiscoveredDevice]:
        """Synchronously scans for nearby Puffco devices on the persistent event loop."""
        if not self._running:
            self.start()

        if not self._loop or not self._loop.is_running():
            return []

        fut = asyncio.run_coroutine_threadsafe(scan_puffco_devices(timeout=timeout), self._loop)
        try:
            return fut.result(timeout=timeout + 3.0)
        except Exception as e:
            logger.warning(f"Scan error: {e}")
            return []

    def connect(self, target_address: Optional[str] = None, timeout: float = 12.0) -> bool:
        """Connects or reconnects to target_address (or auto-scans if None)."""
        if not self._running:
            self.start()

        if target_address is not None:
            self.target_address = target_address

        if not self._loop or not self._loop.is_running():
            return False

        fut = asyncio.run_coroutine_threadsafe(self._async_connect(timeout=timeout), self._loop)
        try:
            return fut.result(timeout=timeout + 3.0)
        except Exception as e:
            logger.error(f"Connect error: {e}")
            return False

    def reconnect(self, target_address: Optional[str] = None):
        """Asynchronously begins connecting to the target address."""
        if target_address is not None:
            self.target_address = target_address
        if not self._running:
            self.start()
            return
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_connect(), self._loop)

    def disconnect(self):
        """Disconnects current device without terminating the background worker thread."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_disconnect(), self._loop)

    async def _async_connect(self, timeout: float = 12.0) -> bool:
        if not hasattr(self, "_async_lock") or self._async_lock is None:
            self._async_lock = asyncio.Lock()

        async with self._async_lock:
            if self._client and self._client.is_connected:
                if not self.target_address or self.target_address.upper() == (self._client.target_address or "").upper():
                    return True

            await self._internal_disconnect()

            self._client = PuffcoClient(self.target_address)
            self._client.add_telemetry_listener(self._on_telemetry)

            try:
                connected = await self._client.connect(timeout=timeout)
                if connected:
                    self.target_address = self._client.target_address
                    self._connected_event.set()
                    await self._client.start_telemetry_stream()
                    return True
            except Exception as e:
                logger.warning(f"Connection attempt failed: {e}")

            self._connected_event.clear()
            disconnected_telem = PuffcoTelemetry()
            disconnected_telem.connected = False
            disconnected_telem.operating_state = OperatingState.DISCONNECTED
            self._on_telemetry(disconnected_telem)
            return False

    async def _async_disconnect(self):
        if not hasattr(self, "_async_lock") or self._async_lock is None:
            self._async_lock = asyncio.Lock()

        async with self._async_lock:
            await self._internal_disconnect()
            disconnected_telem = PuffcoTelemetry()
            disconnected_telem.connected = False
            disconnected_telem.operating_state = OperatingState.DISCONNECTED
            self._on_telemetry(disconnected_telem)

    async def _internal_disconnect(self):
        self._connected_event.clear()
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None

    def wait_connected(self, timeout: float = 15.0) -> bool:
        """Blocks until the device is connected and authenticated, or timeout expires."""
        return self._connected_event.wait(timeout=timeout)

    # ==========================================
    # SESSION & DEVICE COMMANDS
    # ==========================================
    def start_session(self):
        """Triggers a heating session."""
        if self._client and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._client.start_session(), self._loop)

    def stop_session(self):
        """Aborts heating session."""
        if self._client and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._client.stop_session(), self._loop)

    def boost(self):
        """Triggers session heat boost."""
        if self._client and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._client.boost(), self._loop)

    def set_profile(self, slot: int):
        """Changes active heat profile slot (0..3)."""
        if self._client and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._client.set_profile(slot), self._loop)

    def set_temperature(self, temp_f: float):
        """Sets temperature for active profile."""
        if self._client and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._client.set_temperature(temp_f), self._loop)

    def set_stealth_mode(self, enabled: bool):
        """Toggles stealth lighting."""
        if self._client and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._client.set_stealth_mode(enabled), self._loop)

    def set_lantern(self, enabled: bool):
        """Toggles lantern lighting mode."""
        if self._client and self._loop and self._loop.is_running():
            coro = self._client.start_lantern() if enabled else self._client.stop_lantern()
            asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _on_telemetry(self, telem: PuffcoTelemetry):
        for cb in self._telemetry_listeners:
            try:
                cb(telem)
            except Exception as e:
                logger.debug(f"Telemetry callback error: {e}")
