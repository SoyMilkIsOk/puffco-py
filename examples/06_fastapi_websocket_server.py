#!/usr/bin/env python3
"""
Puffco-py Blueprint: FastAPI REST & WebSocket Telemetry Server.

Provides a full HTTP REST API and WebSocket streaming bridge for Puffco Peak Pro and
Proxy devices. Ideal for building web dashboards, mobile applications, or local
home automation microservices.

REST Endpoints:
  - GET  /api/info            Static device metadata & configured profiles
  - GET  /api/telemetry       Snapshot of current live telemetry
  - POST /api/sesh/start      Trigger heat cycle
  - POST /api/sesh/stop       Cancel / abort heating
  - POST /api/sesh/boost      Trigger heat boost
  - POST /api/profile/select  Switch active profile slot ({"slot": 0})
  - POST /api/profile/update  Edit profile ({"slot": 0, "name": "...", "temp_f": 490, "duration_s": 50})
  - POST /api/stealth         Toggle stealth lighting ({"enabled": true})

WebSocket Endpoint:
  - WS   /ws                  Real-time broadcast of telemetry updates (sub-100ms)

Requirements:
    pip install fastapi uvicorn
"""

import argparse
import asyncio
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    print("\n❌ Missing required dependencies 'fastapi' or 'uvicorn'.")
    print("Install them with:")
    print("    pip install fastapi uvicorn\n")
    sys.exit(1)

from puffco_py import (
    PuffcoClient,
    PuffcoTelemetry,
)
from puffco_py.mock import MockPuffcoClient

# Shared global device client and active WebSocket connections
puffco_client: Optional[PuffcoClient] = None
active_websockets: List[WebSocket] = []


class ProfileSelectRequest(BaseModel):
    slot: int


class ProfileUpdateRequest(BaseModel):
    slot: int
    name: Optional[str] = None
    temp_f: Optional[float] = None
    duration_s: Optional[int] = None


class StealthRequest(BaseModel):
    enabled: bool


def format_telemetry_dict(telem: PuffcoTelemetry) -> dict:
    active_name = (
        telem.profiles[telem.active_profile].name
        if telem.profiles and telem.active_profile < len(telem.profiles)
        else f"Slot {telem.active_profile + 1}"
    )
    return {
        "connected": telem.connected,
        "mac_address": telem.mac_address,
        "device_name": telem.device_name,
        "device_model": telem.device_model,
        "serial_number": telem.serial_number,
        "firmware_version": telem.firmware_version,
        "operating_state": telem.operating_state.value,
        "state_name": telem.state_name,
        "is_heating": telem.is_heating,
        "live_temp_f": round(telem.live_temp_f, 1),
        "target_temp_f": round(telem.target_temp_f, 1),
        "time_remaining": telem.time_remaining,
        "total_time": telem.total_time,
        "battery_pct": telem.battery_pct,
        "is_charging": telem.is_charging,
        "chamber_type": telem.chamber_type.value,
        "chamber_name": telem.chamber_name,
        "lifetime_dabs": telem.lifetime_dabs,
        "stealth_mode": telem.stealth_mode,
        "active_profile": telem.active_profile,
        "active_profile_name": active_name,
        "boost_temp_f": telem.boost_temp_f,
        "boost_duration_s": telem.boost_duration_s,
    }


async def broadcast_telemetry(telem: PuffcoTelemetry):
    """Broadcasts telemetry update to all connected WebSocket clients."""
    if not active_websockets:
        return
    data = format_telemetry_dict(telem)
    dead_sockets = []
    for ws in active_websockets:
        try:
            await ws.send_json(data)
        except Exception:
            dead_sockets.append(ws)
    for dead in dead_sockets:
        if dead in active_websockets:
            active_websockets.remove(dead)


def on_telemetry_update(telem: PuffcoTelemetry):
    try:
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(broadcast_telemetry(telem), loop)
    except RuntimeError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    global puffco_client
    if puffco_client:
        puffco_client.add_telemetry_listener(on_telemetry_update)
        try:
            await puffco_client.connect()
            await puffco_client.start_telemetry_stream()
        except Exception as e:
            print(f"Warning: Could not connect to Puffco device on startup: {e}")

    yield

    if puffco_client and puffco_client.is_connected:
        await puffco_client.stop_telemetry_stream()
        await puffco_client.disconnect()


app = FastAPI(
    title="Puffco Peak Pro Telemetry & Control API",
    description="REST endpoints and real-time WebSocket broadcast hub for Puffco hardware.",
    version="0.1.3",
    lifespan=lifespan,
)

# Enable CORS for browser frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "puffco-py API Server",
        "connected": puffco_client.is_connected if puffco_client else False,
    }


@app.get("/api/info")
async def get_device_info():
    if not puffco_client or not puffco_client.is_connected:
        raise HTTPException(status_code=503, detail="Puffco device not connected")
    telem = puffco_client.telemetry
    return {
        "device_name": telem.device_name,
        "device_model": telem.device_model,
        "mac_address": telem.mac_address,
        "serial_number": telem.serial_number,
        "firmware_version": telem.firmware_version,
        "chamber_name": telem.chamber_name,
        "lifetime_dabs": telem.lifetime_dabs,
        "profiles": [
            {
                "slot": p.slot,
                "name": p.name,
                "target_temp_f": p.target_temp_f,
                "duration_s": p.duration_s,
            }
            for p in telem.profiles
        ],
    }


@app.get("/api/telemetry")
async def get_live_telemetry():
    if not puffco_client or not puffco_client.is_connected:
        raise HTTPException(status_code=503, detail="Puffco device not connected")
    return format_telemetry_dict(puffco_client.telemetry)


@app.post("/api/sesh/start")
async def start_session():
    if not puffco_client or not puffco_client.is_connected:
        raise HTTPException(status_code=503, detail="Puffco device not connected")
    success = await puffco_client.start_session()
    return {"status": "ok" if success else "failed"}


@app.post("/api/sesh/stop")
async def stop_session():
    if not puffco_client or not puffco_client.is_connected:
        raise HTTPException(status_code=503, detail="Puffco device not connected")
    success = await puffco_client.stop_session()
    return {"status": "ok" if success else "failed"}


@app.post("/api/sesh/boost")
async def boost_session():
    if not puffco_client or not puffco_client.is_connected:
        raise HTTPException(status_code=503, detail="Puffco device not connected")
    success = await puffco_client.boost()
    return {"status": "ok" if success else "failed"}


@app.post("/api/profile/select")
async def select_profile(req: ProfileSelectRequest):
    if not puffco_client or not puffco_client.is_connected:
        raise HTTPException(status_code=503, detail="Puffco device not connected")
    success = await puffco_client.set_profile(req.slot)
    return {"status": "ok" if success else "failed", "active_profile": req.slot}


@app.post("/api/profile/update")
async def update_profile(req: ProfileUpdateRequest):
    if not puffco_client or not puffco_client.is_connected:
        raise HTTPException(status_code=503, detail="Puffco device not connected")

    slot = req.slot
    if req.name is not None:
        await puffco_client.set_profile_name(slot, req.name)
    if req.temp_f is not None:
        await puffco_client.set_temperature(req.temp_f, slot=slot)
    if req.duration_s is not None:
        await puffco_client.set_profile_duration(slot, req.duration_s)

    return {"status": "ok", "slot": slot}


@app.post("/api/stealth")
async def set_stealth(req: StealthRequest):
    if not puffco_client or not puffco_client.is_connected:
        raise HTTPException(status_code=503, detail="Puffco device not connected")
    success = await puffco_client.set_stealth_mode(req.enabled)
    return {"status": "ok" if success else "failed", "stealth": req.enabled}


@app.websocket("/ws")
async def websocket_telemetry_feed(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    if puffco_client and puffco_client.is_connected:
        await websocket.send_json(format_telemetry_dict(puffco_client.telemetry))
    try:
        while True:
            # Keep connection open; receive ping or client commands
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


def main():
    global puffco_client
    parser = argparse.ArgumentParser(description="Puffco-py FastAPI & WebSocket Server")
    parser.add_argument(
        "--mac",
        type=str,
        default="F7:11:95:C5:14:9B",
        help="Target Puffco MAC / UUID address",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use simulated offline mock device",
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    args = parser.parse_args()

    client_cls = MockPuffcoClient if args.mock else PuffcoClient
    puffco_client = client_cls(args.mac)

    print(f"\n🚀 Starting puffco-py API Server at http://{args.host}:{args.port}")
    print(f"📡 WebSocket streaming endpoint at ws://{args.host}:{args.port}/ws")
    print(f"📚 OpenAPI interactive docs available at http://{args.host}:{args.port}/docs\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
