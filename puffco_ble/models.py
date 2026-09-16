"""
Data models, enums, and telemetry structures for Puffco BLE communication.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional


class OperatingState(IntEnum):
    """Puffco hardware operating states."""
    DISCONNECTED = 0
    OFF = 1
    BOOTING = 2
    SLEEP = 3
    IDLE = 5
    TEMP_SELECT = 6
    HEAT_PREHEAT = 7
    HEAT_ACTIVE = 8
    HEAT_FADE = 9
    READY = 10
    COOLDOWN = 11
    ERROR = 12
    SHUTDOWN = 13


class ChamberType(IntEnum):
    """Chamber hardware attachments."""
    NONE = 0
    STANDARD = 1
    CHAMBER_3DXL_V1 = 2
    CHAMBER_3D = 3
    CHAMBER_3DXL = 4
    TOAD = 5  # Proxy / 3D chamber variant


CHAMBER_NAMES = {
    ChamberType.NONE: "None",
    ChamberType.STANDARD: "Standard",
    ChamberType.CHAMBER_3DXL_V1: "3DXL",
    ChamberType.CHAMBER_3D: "3D",
    ChamberType.CHAMBER_3DXL: "3DXL",
    ChamberType.TOAD: "3D (Proxy)",
}


@dataclass
class PuffcoProfile:
    """A heat profile stored on the device."""
    slot: int
    name: str
    target_temp_f: int
    duration_s: int = 45

    def __str__(self) -> str:
        return f"Slot {self.slot}: '{self.name}' ({self.target_temp_f}°F, {self.duration_s}s)"


@dataclass
class PuffcoTelemetry:
    """Real-time live telemetry and hardware diagnostics."""
    connected: bool = False
    mac_address: str = ""
    device_name: str = "Puffco Device"
    serial_number: str = ""
    firmware_version: str = ""

    # Live Session Telemetry
    operating_state: OperatingState = OperatingState.IDLE
    live_temp_f: float = 0.0
    target_temp_f: float = 510.0
    time_remaining: int = 0
    total_time: int = 45

    # Hardware & Battery Diagnostics
    battery_pct: int = 0
    is_charging: bool = False
    chamber_type: ChamberType = ChamberType.CHAMBER_3DXL
    lifetime_dabs: int = 0
    stealth_mode: bool = False

    # Profiles
    active_profile: int = 0
    profiles: List[PuffcoProfile] = field(default_factory=list)

    @property
    def is_heating(self) -> bool:
        """True if the chamber is preheating or actively heating."""
        return self.operating_state in (
            OperatingState.HEAT_PREHEAT,
            OperatingState.HEAT_ACTIVE,
            OperatingState.HEAT_FADE,
        )

    @property
    def chamber_name(self) -> str:
        """Human-readable chamber name."""
        return CHAMBER_NAMES.get(self.chamber_type, f"Unknown ({int(self.chamber_type)})")

    @property
    def state_name(self) -> str:
        """Human-readable operating state name."""
        return self.operating_state.name.replace("_", " ").title()

    def summary(self) -> str:
        """One-line formatted telemetry summary."""
        state_str = self.state_name
        time_str = f" [{self.time_remaining}s/{self.total_time}s]" if self.is_heating else ""
        return (
            f"[{self.device_name}] {state_str}{time_str} | "
            f"Temp: {self.live_temp_f:.1f}°F / {self.target_temp_f:.0f}°F | "
            f"Bat: {self.battery_pct}%{' (⚡)' if self.is_charging else ''} | "
            f"Chamber: {self.chamber_name} | "
            f"Dabs: {self.lifetime_dabs}"
        )
