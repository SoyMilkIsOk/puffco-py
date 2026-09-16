"""
Synchronous, thread-safe wrapper around PuffcoClient for desktop GUIs, menu bar apps,
and synchronous scripts.
"""

import asyncio
import logging
import queue
import threading
from typing import Any, Callable, List, Optional

from .client import PuffcoClient
from .models import OperatingState, PuffcoTelemetry

logger = logging.getLogger("puffco_py.threaded")


class ThreadedPuffcoClient:
    """
    Synchronous wrapper around PuffcoClient that runs Bleak in a dedicated background worker thread.
    
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
        self._cmd_queue: queue.Queue = queue.Queue()
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

    def start(self):
        """Starts the background worker thread and begins connection."""
        if self._running:
            return
        self._running = True
        self._connected_event.clear()
        self._thread = threading.Thread(target=self._worker_thread, daemon=True)
        self._thread.start()

    def wait_connected(self, timeout: float = 15.0) -> bool:
        """Blocks until the device is connected and authenticated, or timeout expires."""
        return self._connected_event.wait(timeout=timeout)

    def stop(self):
        """Signals the background worker to disconnect and terminate."""
        if not self._running:
            return
        self._running = False
        self._cmd_queue.put(("disconnect", None))
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._connected_event.clear()

    # ==========================================
    # SYNCHRONOUS COMMAND METHODS
    # ==========================================
    def start_session(self):
        """Triggers a heating session."""
        self._cmd_queue.put(("start_session", None))

    def stop_session(self):
        """Aborts heating session."""
        self._cmd_queue.put(("stop_session", None))

    def boost(self):
        """Triggers session heat boost."""
        self._cmd_queue.put(("boost", None))

    def set_profile(self, slot: int):
        """Changes active heat profile slot (0..3)."""
        self._cmd_queue.put(("set_profile", slot))

    def set_temperature(self, temp_f: float):
        """Sets temperature for active profile."""
        self._cmd_queue.put(("set_temperature", temp_f))

    def set_stealth_mode(self, enabled: bool):
        """Toggles stealth lighting."""
        self._cmd_queue.put(("set_stealth_mode", enabled))

    # ==========================================
    # WORKER THREAD ENGINE
    # ==========================================
    def _worker_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_main())
        finally:
            self._loop.close()

    async def _async_main(self):
        self._client = PuffcoClient(self.target_address)
        self._client.add_telemetry_listener(self._on_telemetry)

        try:
            connected = await self._client.connect()
            if connected:
                self._connected_event.set()
                await self._client.start_telemetry_stream()

                # Process commands while connected
                while self._running and self._client.is_connected:
                    while not self._cmd_queue.empty():
                        cmd, arg = self._cmd_queue.get_nowait()
                        if cmd == "disconnect":
                            return
                        elif cmd == "start_session":
                            await self._client.start_session()
                        elif cmd == "stop_session":
                            await self._client.stop_session()
                        elif cmd == "boost":
                            await self._client.boost()
                        elif cmd == "set_profile":
                            await self._client.set_profile(arg)
                        elif cmd == "set_temperature":
                            await self._client.set_temperature(arg)
                        elif cmd == "set_stealth_mode":
                            await self._client.set_stealth_mode(arg)

                    await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"Threaded worker exception: {e}")
        finally:
            self._connected_event.clear()
            if self._client:
                await self._client.disconnect()

    def _on_telemetry(self, telem: PuffcoTelemetry):
        for cb in self._telemetry_listeners:
            try:
                cb(telem)
            except Exception as e:
                logger.debug(f"Telemetry callback error: {e}")
