"""
Protocol constants, UUIDs, opcodes, and VFS paths for Puffco devices.
"""

# ==========================================
# BLE SERVICE & CHARACTERISTIC UUIDS
# ==========================================

# Modern Lorax VFS Protocol (Firmware X, W, AW, 1.0+)
PUFFCO_LORAX_SVC_UUID = "e276967f-ea8a-478a-a92e-d78f5dd15dd5"
PUFFCO_LORAX_CHAR_CMD = "60133d5c-5727-4f2c-9697-d842c5292a3c"       # Write without response
PUFFCO_LORAX_CHAR_REPLY = "8dc5ec05-8f7d-45ad-99db-3fbde65dbd9c"     # Notify / Indicate
PUFFCO_LORAX_CHAR_EVENT = "43312cd1-7d34-46ce-a7d3-0a98fd9b4cb8"     # Notify
PUFFCO_LORAX_CHAR_VERSION = "05434bca-cc7f-4ef6-bbb3-b1c520b9800c"   # Read

# Legacy Flat GATT Protocol (Firmware < X)
PUFFCO_LEGACY_SVC_UUID = "06caf9c0-74d3-454f-9be9-e30cd999c17a"
PUFFCO_CHAR_ACCESS_SEED = "06caf9c0-74d3-454f-9be9-e30cd999c17b"
PUFFCO_CHAR_ACCESS_KEY = "06caf9c0-74d3-454f-9be9-e30cd999c17c"
PUFFCO_CHAR_OPERATING_STATE = "06caf9c0-74d3-454f-9be9-e30cd999c17d"
PUFFCO_CHAR_CHAMBER_TEMP = "06caf9c0-74d3-454f-9be9-e30cd999c17e"
PUFFCO_CHAR_BATTERY_SOC = "06caf9c0-74d3-454f-9be9-e30cd999c181"
PUFFCO_CHAR_PROFILE_CURRENT = "06caf9c0-74d3-454f-9be9-e30cd999c185"
PUFFCO_CHAR_TOTAL_DABS = "06caf9c0-74d3-454f-9be9-e30cd999c18b"
PUFFCO_CHAR_DEVICE_NAME = "06caf9c0-74d3-454f-9be9-e30cd999c18d"

# Device Information Service
DEVINFO_SVC_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
DEVINFO_SERIAL_UUID = "00002a25-0000-1000-8000-00805f9b34fb"
DEVINFO_FIRMWARE_UUID = "00002a26-0000-1000-8000-00805f9b34fb"
DEVINFO_HARDWARE_UUID = "00002a27-0000-1000-8000-00805f9b34fb"

# ==========================================
# LORAX OPCODES
# ==========================================
LORAX_OP_GET_ACCESS_SEED = 0x00
LORAX_OP_UNLOCK_ACCESS = 0x01
LORAX_OP_GET_LIMITS = 0x02
LORAX_OP_READ_SHORT = 0x10
LORAX_OP_WRITE_SHORT = 0x11
LORAX_OP_READ = 0x20
LORAX_OP_WRITE = 0x21
LORAX_OP_WATCH = 0x30
LORAX_OP_UNWATCH = 0x31

# ==========================================
# COMMON LORAX VFS PATHS
# ==========================================
# Operating & State
PATH_STATE_ID = "/p/app/stat/id"          # Operating state byte
PATH_TIME_ELAPSED = "/p/app/stat/elap"    # Elapsed session time
PATH_TIME_TOTAL = "/p/app/stat/tott"      # Total session time
PATH_MODE_CONTROL = "/p/app/mc"           # Mode control commands (start/stop/boost)

# Heater & Temperature
PATH_CHAMBER_TEMP = "/p/app/htr/temp"     # Real-time live temperature
PATH_TARGET_TEMP = "/p/app/htr/ttag"      # Target session temperature
PATH_CHAMBER_TYPE = "/p/htr/chmt"         # Chamber hardware type byte

# Battery & Power
PATH_BATTERY_SOC = "/p/bat/soc"           # Battery state of charge (percentage)
PATH_BATTERY_CHARGE_STAT = "/p/bat/chg/stat"  # 0,1,2 = Charging

# Metrics & Odometer
PATH_ODOMETER_DABS = "/p/app/odom/0/nc"   # Lifetime total dabs count

# User Configuration & Profiles
PATH_DEVICE_NAME = "/u/sys/name"          # Custom user device name
PATH_ACTIVE_PROFILE = "/p/app/hcs"        # Active profile index (0..3)
PATH_STEALTH_MODE = "/u/app/ui/stlm"      # Stealth lighting toggle (0=Off, 1=On)
PATH_LANTERN_CMD = "/p/app/ltrn/cmd"      # Lantern mode toggle (0=Off, 1=On)
PATH_LED_BRIGHTNESS = "/u/app/ui/brt"     # LED brightness (4 bytes: base, mid, glass, logo)
PATH_PROFILE_NAME_PREFIX = "/u/app/hc/{slot}/name"
PATH_PROFILE_TEMP_PREFIX = "/u/app/hc/{slot}/temp"
PATH_PROFILE_TIME_PREFIX = "/u/app/hc/{slot}/time"

# ==========================================
# AUTHENTICATION CONSTANTS
# ==========================================
# Verified Lorax Master Handshake Key (Base64: "ZMZFYlbyb1scoSc3pd1x+w==")
LORAX_MASTER_HANDSHAKE_KEY = bytes.fromhex("64c6456256f26f5b1ca12737a5dd71fb")

# Known MAC prefixes (OUI) commonly used by Puffco Nordic/Silabs modules
PUFFCO_MAC_PREFIXES = (
    "84:2E:14",
    "84:FD:27",
    "0C:43:14",
    "F7:11:95",
)

PUFFCO_NAME_KEYWORDS = (
    "puffco",
    "peak",
    "peak pro",
    "proxy",
)
