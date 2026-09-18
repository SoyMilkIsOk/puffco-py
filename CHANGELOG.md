# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.3] - 2026-09-18

### Fixed
- **Source Distribution Packaging**: Added `MANIFEST.in` to ensure `tests/mock_device.py`, docs, and example assets are bundled in `.tar.gz` sdist packages so downstream packagers and offline test runners do not fail.
- **Build Warnings**: Modernized `pyproject.toml` to use PEP 639 standard SPDX string `license = "MIT"`, eliminating setuptools deprecation warnings.

### Added
- **Repository Discoverability**: Added GitHub Actions CI badge, Contributing section, and Changelog references to `README.md`.
- **Git Normalization**: Added `.gitattributes` to enforce LF line endings across platforms.
- **Release Verification**: Added automated `build` and `twine check` steps to CI (`ci.yml`) and release (`release.yml`) workflows.
- Added `twine` to `dev` optional-dependencies for local package verification.

---

## [0.1.2] - 2026-09-18

### Added
- **Mock Simulation Engine**: Introduced `MockBleakClient` and `MockPuffcoClient` for 100% offline development, testing, and CI verification without requiring physical Puffco hardware.
- **Offline Test Suite**: 41 comprehensive unit tests covering protocol packing/unpacking, Lorax SHA-256 handshake auth, telemetry decoders, device discovery, CLI commands, and threaded worker loops.
- **Rich Terminal HUD**: Added interactive terminal monitoring dashboard (`puffco-py monitor`) with color-coded battery gauge, operating state status badges, and live temperature streaming.
- **Reference Integrations**:
  - Home Assistant MQTT discovery bridge (`examples/05_home_assistant_mqtt.py`).
  - FastAPI REST API & WebSocket server with broadcast hub (`examples/06_fastapi_websocket_server.py`).
  - Native macOS menu bar status widget via `rumps` (`examples/04_mac_menu_widget.py`).
- **Comprehensive Documentation**:
  - `docs/api.md`: Full public API reference.
  - `docs/protocol.md`: Lorax VFS specification, GATT UUIDs, packet framing, and auth sequence.
  - `docs/troubleshooting.md`: OS-level BLE setup tips for macOS, Linux BlueZ, and Windows.
- **CI/CD Automation**: Multi-platform GitHub Actions workflow testing Python 3.9 through 3.13 on Ubuntu, macOS, and Windows runners, with automated PyPI Trusted Publishing on tag pushes.

### Changed
- Refactored `ThreadedPuffcoClient` to use direct `asyncio.run_coroutine_threadsafe` dispatch for lower latency and simpler thread synchronization.
- Decoupled high-frequency telemetry polling (150ms during active heat cycles) from slow-path hardware metadata (battery/chamber polling every 2s).

---

## [0.1.1] - 2026-09-17

### Added
- **Threaded Client**: Introduced `ThreadedPuffcoClient` to simplify embedding in synchronous desktop GUI applications (Tkinter, PyQt, PySide).
- **Graceful Disconnect Handling**: Added automatic notification triggers on unexpected Bluetooth link drops.

### Changed
- Improved error handling in `PuffcoClient.connect()` to gracefully report authentication failures while continuing diagnostic discovery.

---

## [0.1.0] - 2026-09-16

### Added
- **Core Async Client**: Asyncio-native `PuffcoClient` built on Bleak.
- **Lorax VFS Framing**: Packet serialization and deserialization for reading and writing virtual filesystem paths.
- **Authentication**: Lorax challenge-response seed calculation using SHA-256 tokens.
- **Hardware Telemetry**: Support for live bowl temperature (float and integer tenths), chamber type detection (3D, 3DXL, Toad), battery charge status, and lifetime dab odometer.
- **Session Control**: Start, boost, and stop heating cycles; switch between 4 device profile slots.
- **BLE Discovery**: Scanner filtering nearby BLE advertisements for known Puffco MAC prefixes and Lorax service UUIDs.
