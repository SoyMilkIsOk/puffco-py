# Security Policy

## Supported Versions

We actively provide security and bug fix updates for the latest released version of `puffco-py`:

| Version | Supported          |
| :--- | :--- |
| `0.1.x` | :white_check_mark: |
| `< 0.1.0` | :x:                |

---

## Security Context & Scope

`puffco-py` is an independent, open-source Python driver and reverse-engineered telemetry engine for Puffco Bluetooth Low Energy (BLE) vaporizers.

### Local Communication Model
- **Offline & Local**: `puffco-py` operates entirely locally over BLE. It does not run telemetry servers, transmit metrics over the internet, or collect user data.
- **Protocol Encryption**: Communication between client and device uses Puffco's Lorax VFS protocol. Device authentication relies on the shared Lorax handshake seed calculation.

---

## Reporting a Vulnerability

If you discover a security vulnerability, authentication flaw, or safety concern in `puffco-py`, please **do not report it through public GitHub issues**.

Instead, please report security concerns using one of the following methods:

1. **GitHub Security Advisory**: Navigate to the [Security tab](https://github.com/SoyMilkIsOk/puffco-py/security/advisories) of the repository and click **"New draft security advisory"**.
2. **Direct Contact**: Reach out privately to the maintainers via the email address listed in the repository's author metadata.

### Information to Include

To help us triage and resolve the issue quickly, please include:
- A description of the vulnerability and its potential impact.
- Step-by-step instructions or proof-of-concept script to reproduce the behavior.
- Operating system, Python version, and `puffco-py` version.
- Puffco hardware model and firmware version (if hardware-specific).

### Response Timeline

- **Initial Response**: We aim to acknowledge receipt of security reports within 48 hours.
- **Status Updates**: Maintainers will provide regular status updates during investigation and patching.
- **Disclosure**: Coordinated public disclosure will be arranged once a patch or workaround is available.
