"""
Binary protocol packaging, Lorax VFS command encoders, SHA-256 handshake calculation,
and byte-level telemetry decoders.
"""

import hashlib
import struct
from typing import Tuple

from .constants import (
    LORAX_MASTER_HANDSHAKE_KEY,
    LORAX_OP_READ_SHORT,
    LORAX_OP_WRITE_SHORT,
)


def calculate_lorax_auth_token(seed: bytes, master_key: bytes = LORAX_MASTER_HANDSHAKE_KEY) -> bytes:
    """
    Computes the 16-byte SHA-256 challenge-response token for Lorax VFS access.
    
    Formula: SHA256(MasterKey + Seed[0:16])[0:16]
    """
    if len(seed) < 16:
        raise ValueError("Auth seed must be at least 16 bytes")
    return hashlib.sha256(master_key + seed[:16]).digest()[:16]


def pack_lorax_cmd(seq: int, opcode: int, payload: bytes = b"") -> bytearray:
    """
    Packs a Lorax command into a binary packet.
    
    Layout:
      [0..1]: uint16 Little-Endian sequence number
      [2]:    uint8  opcode
      [3..]:  payload bytes
    """
    return bytearray(struct.pack("<HB", seq & 0xFFFF, opcode & 0xFF)) + payload


def unpack_lorax_reply(data: bytes) -> Tuple[int, int, bytes]:
    """
    Unpacks a Lorax reply notification.
    
    Layout:
      [0..1]: uint16 Little-Endian sequence number
      [2]:    uint8  status (0 = SUCCESS)
      [3..]:  reply payload
    """
    if len(data) < 3:
        raise ValueError(f"Packet too short for Lorax header ({len(data)} bytes)")
    seq = (data[0] & 0xFF) | ((data[1] & 0xFF) << 8)
    status = data[2]
    payload = bytes(data[3:])
    return seq, status, payload


def pack_lorax_read_short(path: str, max_len: int = 240) -> bytes:
    """
    Packs payload for LORAX_OP_READ_SHORT (0x10).
    Payload layout: uint16 offset (0), uint16 max_len, utf-8 path string
    """
    return struct.pack("<HH", 0, max_len) + path.encode("utf-8")


def pack_lorax_write_short(path: str, val: bytes) -> bytes:
    """
    Packs payload for LORAX_OP_WRITE_SHORT (0x11).
    Payload layout: uint16 offset (0), uint8 flags (0), utf-8 path string, 0x00 delimiter, value bytes
    """
    return struct.pack("<HB", 0, 0) + path.encode("utf-8") + b"\x00" + val


# ==========================================
# TEMPERATURE CONVERSIONS & PARSERS
# ==========================================

def c_to_f(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (c * 9.0 / 5.0) + 32.0


def f_to_c(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (f - 32.0) * 5.0 / 9.0


def parse_temp(b: bytes) -> float:
    """
    Parses temperature bytes into Fahrenheit.
    Handles IEEE 754 32-bit floats (Peak Pro) and integer tenths of °C (Proxy).
    """
    if not b or len(b) < 4:
        return 0.0

    # 1. Check IEEE 754 32-bit float (Celsius)
    try:
        f_val = struct.unpack("<f", b[:4])[0]
        if 5.0 <= f_val <= 450.0:
            return round(c_to_f(f_val), 1)
    except Exception:
        pass

    # 2. Check 32-bit signed integer (Tenths of Celsius e.g. 2650 = 265.0°C)
    try:
        i_val = struct.unpack("<i", b[:4])[0]
        if 50 <= i_val <= 4500:
            return round(c_to_f(i_val / 10.0), 1)
        if 5 <= i_val <= 450:
            return round(c_to_f(float(i_val)), 1)
    except Exception:
        pass

    return 0.0


def parse_battery(b: bytes) -> int:
    """Parses battery percentage (0–100%) from 1-byte, 4-byte int, or 4-byte float."""
    if not b:
        return 0
    if len(b) == 1:
        return min(100, max(0, b[0]))
    if len(b) >= 4:
        # Check integer
        i_val = struct.unpack("<I", b[:4])[0]
        if 0 <= i_val <= 100:
            return i_val
        if 100 < i_val <= 10000:
            return min(100, max(0, int(round(i_val / 100.0))))
        # Check float
        f_val = struct.unpack("<f", b[:4])[0]
        if 1.0 <= f_val <= 100.0:
            return min(100, max(0, int(round(f_val))))
    return 0


def parse_dabs(b: bytes) -> int:
    """Parses lifetime odometer dabs count."""
    if not b:
        return 0
    if len(b) >= 4:
        f_val = struct.unpack("<f", b[:4])[0]
        if 1.0 <= f_val < 1000000.0 and f_val.is_integer():
            return int(f_val)
        return struct.unpack("<I", b[:4])[0]
    elif len(b) == 2:
        return struct.unpack("<H", b[:2])[0]
    elif len(b) == 1:
        return b[0]
    return 0
