# Contributing to puffco-py

Thank you for your interest in contributing to `puffco-py`! We welcome contributions ranging from bug reports and code improvements to newly discovered Lorax BLE protocol endpoints and device hardware dumps.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Environment Setup](#development-environment-setup)
- [Development Workflow & Commands](#development-workflow--commands)
- [Reverse-Engineering Guide](#reverse-engineering-guide)
  - [Lorax VFS Architecture](#lorax-vfs-architecture)
  - [Capturing BLE Traffic](#capturing-ble-traffic)
  - [Documenting & Adding New Endpoints](#documenting--adding-new-endpoints)
  - [Updating the Mock Device](#updating-the-mock-device)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Commit Conventions](#commit-conventions)

---

## Code of Conduct

All contributors and maintainers are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat everyone with empathy and respect.

---

## Development Environment Setup

### Prerequisites

- Python 3.9, 3.10, 3.11, 3.12, or 3.13
- Git
- Bluetooth 4.0+ (BLE) adapter (optional; mock devices work 100% offline)

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SoyMilkIsOk/puffco-py.git
   cd puffco-py
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   # On Windows PowerShell:
   # .venv\Scripts\Activate.ps1
   ```

3. **Install the package in editable mode with all development extras:**
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev,cli,gui]"
   ```

---

## Development Workflow & Commands

Before submitting code, please ensure formatting, linting, type-checking, and tests pass cleanly:

### Running Unit Tests

Our test suite is 100% offline and requires no physical Bluetooth hardware:

```bash
# Using pytest
pytest tests/ -v

# Or using Python's standard unittest runner
python3 -m unittest discover tests -v
```

### Code Formatting & Linting

We use [Ruff](https://github.com/astral-sh/ruff) for fast formatting and linting:

```bash
# Check lint rules
ruff check .

# Auto-fix fixable lint errors
ruff check --fix .

# Check formatting
ruff format --check .

# Apply auto-formatting
ruff format .
```

### Static Type Checking

We use [Mypy](https://mypy-lang.org/) for type safety across the library:

```bash
mypy puffco_py/
```

### CLI Verification with Mock Hardware

You can run the full CLI dashboard and session commands against the built-in mock simulator:

```bash
# Diagnostic info
puffco-py info --mock

# Interactive live HUD monitor
puffco-py monitor --mock

# Heat cycle simulation
puffco-py sesh start --mock
```

---

## Reverse-Engineering Guide

The Puffco Peak Pro and Proxy communicate over Bluetooth Low Energy (BLE) using a proprietary binary framing protocol named **Lorax**, which exposes an internal **Virtual File System (VFS)**.

### Lorax VFS Architecture

1. **Service UUID**: `06A5...` (see `PUFFCO_LORAX_SVC_UUID` in `puffco_py/constants.py`)
2. **Key Characteristics**:
   - `PUFFCO_LORAX_CHAR_COMMAND`: Used to write requests (read/write VFS paths, authenticate).
   - `PUFFCO_LORAX_CHAR_REPLY`: Notifies responses from the device.
3. **Authentication Handshake**:
   - Client sends opcode `0x25` (`LORAX_OP_GET_ACCESS_SEED`).
   - Device returns a 16-byte random seed.
   - Client calculates `SHA256(MasterKey + Seed[0:16])[0:16]`.
   - Client sends opcode `0x26` (`LORAX_OP_UNLOCK_ACCESS`) with the token to grant read/write access.
4. **VFS Path Prefixes**:
   - `/p/...` Profile configuration (temperatures, session durations, names, colors)
   - `/l/...` Lighting and lantern modes
   - `/u/...` User settings, telemetry streams, stealth modes
   - `/a/...` Diagnostic logs and device hardware metadata

### Lorax Push Notifications (`LORAX_OP_WATCH`) & Polling Architecture

Lorax defines opcodes `LORAX_OP_WATCH` (`0x30`) and `LORAX_OP_UNWATCH` (`0x31`) paired with the `PUFFCO_LORAX_CHAR_EVENT` characteristic (`06a5da28-8d78-4522-97fb-cf34752c363f`) intended for push notifications on file modifications.

**Why puffco-py defaults to adaptive polling:**
- **Firmware Inconsistencies:** Hardware dumps and testing across Peak Pro V1, V2, and Proxy indicate uneven support. While certain status paths emit event packets, continuous chamber temperature deltas during active heating cycles frequently do not push updates reliably across all firmware versions.
- **Reliability Guarantee:** To ensure rock-solid stability across every hardware variant, `puffco-py` employs a state-aware adaptive polling loop (150ms during active heat cycles, 2000ms during idle, with slow-path polling decoupled).
- **Ongoing Research:** If you are reverse-engineering event stream packets or have firmware supporting full async push streaming for live temperature deltas, please submit packet logs via our [Hardware Dump Issue Template](.github/ISSUE_TEMPLATE/hardware_dump.yml)!

### Capturing BLE Traffic

To discover new endpoints or decode unknown payloads:

#### On Android
1. Go to **Settings > Developer Options**.
2. Enable **Bluetooth HCI Snoop Log**.
3. Toggle Bluetooth off and on, open the official Puffco Web App (or app), and perform the action you want to reverse engineer (e.g., change a light color, set a custom profile).
4. Connect your phone via USB and retrieve the snoop log:
   ```bash
   adb pull /sdcard/btsnoop_hci.log .
   ```
5. Open `btsnoop_hci.log` in **Wireshark**, filter by `btatt.opcode == 0x12 || btatt.opcode == 0x1b`, and inspect the attribute values.

#### On macOS
1. Download **Additional Tools for Xcode** from developer.apple.com.
2. Launch **PacketLogger**.
3. Filter by the Puffco device MAC address or Lorax service UUID.

#### Using nRF Connect
- Install **nRF Connect for Mobile** (iOS / Android).
- Connect to your Puffco device to inspect GATT services, characteristics, and live notification streams.

### Documenting & Adding New Endpoints

1. Check if the path or constant is already declared in `puffco_py/constants.py`.
2. If new, define the path constant with a descriptive name and docstring (e.g., `PATH_CUSTOM_COLOR = "/l/col"`).
3. If payload decoding is required, add decoder/encoder functions to `puffco_py/decoders.py` with unit tests in `tests/test_decoders.py`.
4. Expose the functionality via high-level async methods on `PuffcoClient` (`puffco_py/client.py`) and sync methods on `ThreadedPuffcoClient` (`puffco_py/threaded.py`).

### Updating the Mock Device

When adding new VFS paths or commands:
1. Update `create_mock_peak_pro()` and `create_mock_proxy()` in `puffco_py/mock.py` to seed default byte values for the new paths.
2. Ensure `MockPuffcoClient` simulates appropriate behavior.
3. Add a unit test verifying both read and write operations.

---

## Pull Request Guidelines

1. **Keep PRs Focused**: A pull request should ideally address one bug fix, feature, or reverse-engineering discovery.
2. **Add Tests**: Any new decoder, protocol handler, or client method should have corresponding test coverage in `tests/`.
3. **Verify Linters**: Run `ruff check .` and `mypy puffco_py/` locally before opening the PR.
4. **Follow the PR Template**: Fill out the checklist provided in the pull request template.

---

## Commit Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` A new feature or client capability
- `fix:` A bug fix
- `docs:` Documentation updates or guides
- `test:` Adding or refactoring unit tests
- `refactor:` Code improvements without functional changes
- `chore:` Build scripts, CI workflow, or dependency updates

**Example**:
```
feat(client): add support for custom vapor production setting
fix(protocol): handle 0-byte reply packets gracefully
docs: update reverse-engineering guide with Wireshark filters
```
