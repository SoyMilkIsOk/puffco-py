#!/usr/bin/env python3
"""
Puffco-py Blueprint: Home Assistant MQTT Discovery & Live Telemetry Bridge.

Connects to a Puffco device (or offline mock) and publishes standard Home Assistant
MQTT Discovery payloads so that your Puffco Peak Pro or Proxy automatically appears
as a native device with live sensors in Home Assistant.

Sensors discovered:
  - Live Bowl Temperature (°F)
  - Target Temperature (°F)
  - Battery Percentage (%)
  - Operating State (Idle, Heating, Ready, Fade)
  - Chamber Hardware (3DXL, 3D, Toad, etc.)
  - Total Lifetime Dabs
  - Active Profile Name

Controls subscribed:
  - Start / Stop Session
  - Boost Heat
  - Stealth Lighting Toggle

Requirements:
    pip install paho-mqtt
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any, Dict

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("\n❌ Missing required dependency 'paho-mqtt'.")
    print("Install it with:")
    print("    pip install paho-mqtt\n")
    sys.exit(1)

from puffco_py import (
    PuffcoClient,
    PuffcoTelemetry,
)
from puffco_py.mock import MockPuffcoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("home_assistant_mqtt")


class HomeAssistantPuffcoBridge:
    def __init__(
        self,
        client: PuffcoClient,
        broker: str = "localhost",
        port: int = 1883,
        username: str = "",
        password: str = "",
        topic_prefix: str = "homeassistant",
    ):
        self.puffco = client
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix

        self.mqtt_client = mqtt.Client(
            client_id=f"puffco_bridge_{client.target_address.replace(':', '').lower()}"
        )
        if username and password:
            self.mqtt_client.username_pw_set(username, password)

        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message

        self._device_id = ""
        self._state_topic = ""
        self._command_topic = ""
        self._running = False

    def _setup_topics(self):
        mac_clean = self.puffco.target_address.replace(":", "").replace("-", "").lower()
        self._device_id = f"puffco_{mac_clean}"
        self._state_topic = f"{self.topic_prefix}/sensor/{self._device_id}/state"
        self._command_topic = f"{self.topic_prefix}/sensor/{self._device_id}/cmd"

    def _on_mqtt_connect(self, client: Any, userdata: Any, flags: Any, rc: int):
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            self.mqtt_client.subscribe(self._command_topic)
            logger.info(f"Subscribed to control topic: {self._command_topic}")
            self._publish_discovery()
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")

    def _on_mqtt_message(self, client: Any, userdata: Any, msg: Any):
        payload = msg.payload.decode("utf-8", errors="ignore").strip().lower()
        logger.info(f"Received MQTT command: {payload}")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        if payload == "start":
            asyncio.run_coroutine_threadsafe(self.puffco.start_session(), loop)
        elif payload == "stop":
            asyncio.run_coroutine_threadsafe(self.puffco.stop_session(), loop)
        elif payload == "boost":
            asyncio.run_coroutine_threadsafe(self.puffco.boost(), loop)
        elif payload == "stealth_on":
            asyncio.run_coroutine_threadsafe(self.puffco.set_stealth_mode(True), loop)
        elif payload == "stealth_off":
            asyncio.run_coroutine_threadsafe(self.puffco.set_stealth_mode(False), loop)

    def _publish_discovery(self):
        """Publishes Home Assistant MQTT Auto-Discovery configuration payloads."""
        telem = self.puffco.telemetry
        dev_info = {
            "identifiers": [self._device_id],
            "name": telem.device_name,
            "model": telem.device_model,
            "manufacturer": "Puffco",
            "sw_version": telem.firmware_version or "Unknown",
        }

        sensors = [
            {
                "id": "temperature",
                "name": "Live Bowl Temperature",
                "device_class": "temperature",
                "unit": "°F",
                "value_template": "{{ value_json.temperature }}",
                "icon": "mdi:thermometer",
            },
            {
                "id": "target_temp",
                "name": "Target Temperature",
                "device_class": "temperature",
                "unit": "°F",
                "value_template": "{{ value_json.target_temperature }}",
                "icon": "mdi:thermometer-chevron-up",
            },
            {
                "id": "battery",
                "name": "Battery Level",
                "device_class": "battery",
                "unit": "%",
                "value_template": "{{ value_json.battery }}",
            },
            {
                "id": "state",
                "name": "Operating State",
                "value_template": "{{ value_json.state }}",
                "icon": "mdi:smoke-detector-variant",
            },
            {
                "id": "dabs",
                "name": "Total Dabs",
                "value_template": "{{ value_json.total_dabs }}",
                "state_class": "total_increasing",
                "icon": "mdi:counter",
            },
            {
                "id": "chamber",
                "name": "Chamber Type",
                "value_template": "{{ value_json.chamber }}",
                "icon": "mdi:circle-slice-8",
            },
            {
                "id": "profile",
                "name": "Active Profile",
                "value_template": "{{ value_json.profile }}",
                "icon": "mdi:palette",
            },
        ]

        for s in sensors:
            disc_topic = f"{self.topic_prefix}/sensor/{self._device_id}_{s['id']}/config"
            payload: Dict[str, Any] = {
                "name": f"{telem.device_name} {s['name']}",
                "unique_id": f"{self._device_id}_{s['id']}",
                "state_topic": self._state_topic,
                "value_template": s["value_template"],
                "device": dev_info,
            }
            if "device_class" in s:
                payload["device_class"] = s["device_class"]
            if "unit" in s:
                payload["unit_of_measurement"] = s["unit"]
            if "icon" in s:
                payload["icon"] = s["icon"]
            if "state_class" in s:
                payload["state_class"] = s["state_class"]

            self.mqtt_client.publish(disc_topic, json.dumps(payload), retain=True)

        logger.info(f"Published {len(sensors)} Home Assistant MQTT discovery sensors.")

    def publish_state(self, telem: PuffcoTelemetry):
        """Publishes live state JSON to the state topic."""
        active_prof_name = (
            telem.profiles[telem.active_profile].name
            if telem.profiles and telem.active_profile < len(telem.profiles)
            else f"Slot {telem.active_profile + 1}"
        )
        state_dict = {
            "connected": telem.connected,
            "temperature": round(telem.live_temp_f, 1),
            "target_temperature": round(telem.target_temp_f, 1),
            "battery": telem.battery_pct,
            "charging": telem.is_charging,
            "state": telem.state_name,
            "chamber": telem.chamber_name,
            "total_dabs": telem.lifetime_dabs,
            "profile": active_prof_name,
            "stealth": telem.stealth_mode,
            "time_remaining": telem.time_remaining,
        }
        self.mqtt_client.publish(self._state_topic, json.dumps(state_dict), retain=False)

    async def run(self):
        self._setup_topics()
        self._running = True

        # Connect to MQTT in background thread
        logger.info(f"Connecting to MQTT broker {self.broker}:{self.port}...")
        self.mqtt_client.connect_async(self.broker, self.port, keepalive=60)
        self.mqtt_client.loop_start()

        # Connect to Puffco BLE
        logger.info(f"Connecting to Puffco ({self.puffco.target_address})...")
        await self.puffco.connect()
        logger.info(
            f"Connected to {self.puffco.telemetry.device_name} ({self.puffco.telemetry.device_model})"
        )

        # Telemetry listener callback
        self.puffco.add_telemetry_listener(self.publish_state)

        # Start continuous streaming
        await self.puffco.start_telemetry_stream()

        try:
            while self._running:
                await asyncio.sleep(1.0)
        finally:
            await self.puffco.stop_telemetry_stream()
            await self.puffco.disconnect()
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()


async def main():
    parser = argparse.ArgumentParser(
        description="Puffco-py Home Assistant MQTT Discovery & Telemetry Bridge"
    )
    parser.add_argument(
        "--mac",
        type=str,
        default="F7:11:95:C5:14:9B",
        help="Target Puffco MAC / UUID address",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use simulated offline mock device (no Bluetooth required)",
    )
    parser.add_argument("--broker", type=str, default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port (default: 1883)")
    parser.add_argument("--username", type=str, default="", help="MQTT username (optional)")
    parser.add_argument("--password", type=str, default="", help="MQTT password (optional)")
    parser.add_argument(
        "--prefix", type=str, default="homeassistant", help="Home Assistant discovery prefix"
    )
    args = parser.parse_args()

    client_cls = MockPuffcoClient if args.mock else PuffcoClient
    puffco = client_cls(args.mac)

    bridge = HomeAssistantPuffcoBridge(
        client=puffco,
        broker=args.broker,
        port=args.port,
        username=args.username,
        password=args.password,
        topic_prefix=args.prefix,
    )

    try:
        await bridge.run()
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user.")


if __name__ == "__main__":
    asyncio.run(main())
