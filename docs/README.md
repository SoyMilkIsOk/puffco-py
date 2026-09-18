# puffco-py Documentation 📖

Welcome to the documentation hub for **`puffco-py`**. Here you'll find detailed guides, complete API references, hardware troubleshooting steps, and deep dives into the reverse-engineered Lorax BLE protocol.

🌐 **Website & Live Docs**: [puffco-py.soymilkisok.com](https://puffco-py.soymilkisok.com)

---

## Documentation Sections

- **[Python API Reference](api.md)**  
  Complete reference for `PuffcoClient`, `ThreadedPuffcoClient`, and `PuffcoTelemetry` dataclasses and enums.

- **[Hardware & Platform Troubleshooting](troubleshooting.md)**  
  Resolutions for Bluetooth permissions, the single-central connection rule, Linux `setcap` configuration, macOS privacy prompts, and Windows WinRT pairing.

- **[Lorax BLE Protocol Specification](protocol.md)**  
  Technical details on the Lorax Virtual File System (VFS), SHA-256 challenge-response handshake sequence, GATT UUIDs, and VFS endpoints.

- **[Integration Examples & Guides](../examples/README.md)**  
  Step-by-step walkthroughs for macOS menu widgets, Home Assistant MQTT auto-discovery, FastAPI WebSockets, and background GUI threading.

---

## Quick Navigation

| Document | Description |
| :--- | :--- |
| **[`api.md`](api.md)** | Method signatures, parameters, return types, and telemetry models. |
| **[`troubleshooting.md`](troubleshooting.md)** | Bluetooth troubleshooting for macOS, Linux, and Windows. |
| **[`protocol.md`](protocol.md)** | Packet framing, authentication handshake, and Lorax file paths. |
| **[`../examples/`](../examples/)** | Standalone runnable scripts covering common use cases. |
| **[`../CONTRIBUTING.md`](../CONTRIBUTING.md)** | Development environment setup, tests, and PR guidelines. |
