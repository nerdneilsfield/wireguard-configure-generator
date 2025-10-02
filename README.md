# WireGuard Configuration Generator

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Package Manager](https://img.shields.io/badge/package%20manager-uv-blue.svg)](https://github.com/astral-sh/uv)
[![Tests](https://img.shields.io/badge/tests-62%2F62%20passing-brightgreen.svg)](tests/)

[English](README.md) | [中文](README_ZH.md)

---

A modular WireGuard VPN configuration generator with TOML support, Jinja2 templates, and secure key management.

## Features

- **TOML Configuration**: Human-readable configuration format
- **Modular Architecture**: Separate modules for loading, validation, rendering, and key management
- **Secure Key Storage**: Keys stored separately from configurations with 0600 permissions
- **Python Cryptography**: Native key generation using Python's `cryptography` library (no `wg` command required)
- **Multi-Layer Validation**: TOML syntax, JSON schema, and business logic validation
- **Jinja2 Templates**: Flexible template-based configuration rendering
- **Client Modes**: Support for global (0.0.0.0/0) and local (subnet-only) routing modes
- **Optional DNS**: Per-client DNS server configuration
- **Parallel Generation**: Concurrent configuration generation for large networks
- **Key Preservation**: Automatic key reuse on regeneration
- **JSON Migration**: Convert legacy JSON configs to TOML format

## Topology

This tool generates configurations for **simple star topology** networks:
- **1 server** with a public endpoint
- **N clients** connecting to the server
- No mesh, hub-spoke, or relay configurations

## Quick Start

### Installation

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/yourusername/wireguard-configure-generator.git
cd wireguard-configure-generator

# Install dependencies
uv sync
```

### Basic Usage

1. **Create TOML configuration**:

```toml
[common]
network_name = "my-vpn"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "vpn-server"
endpoint = "vpn.example.com"
vlan_ipv4_addr = "10.0.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "laptop"
vlan_ipv4_addr = "10.0.0.2"
port = 51821
dns1 = "1.1.1.1"
dns2 = "8.8.8.8"
gen_global = true
gen_local = false
```

2. **Validate configuration**:

```bash
uv run wg-mesh-gen validate -c network.toml
```

3. **Generate WireGuard configurations**:

```bash
uv run wg-mesh-gen generate -c network.toml -o output/
```

## CLI Commands

<details>
<summary><b>wg-mesh-gen generate</b> - Generate WireGuard configurations</summary>

```bash
uv run wg-mesh-gen generate [OPTIONS]

Options:
  -c, --config PATH        TOML configuration file (required)
  -o, --output PATH        Output directory (default: .)
  -k, --keys PATH          Key storage file (default: keys.json)
  --parallel               Enable parallel generation for large networks
  --force                  Overwrite existing configuration files
  --refresh-force          Regenerate all keys (ignores existing keys.json)
  --help                   Show this message and exit
```

**Examples**:

```bash
# Generate with default settings
uv run wg-mesh-gen generate -c network.toml -o /etc/wireguard

# Use custom key storage
uv run wg-mesh-gen generate -c network.toml -k my-keys.json

# Enable parallel generation for large networks
uv run wg-mesh-gen generate -c network.toml --parallel

# Force overwrite existing files
uv run wg-mesh-gen generate -c network.toml --force

# Regenerate all keys (key rotation)
uv run wg-mesh-gen generate -c network.toml --refresh-force --force
```

</details>

<details>
<summary><b>wg-mesh-gen validate</b> - Validate TOML configuration</summary>

```bash
uv run wg-mesh-gen validate [OPTIONS]

Options:
  -c, --config PATH   TOML configuration file (required)
  -k, --keys PATH     Key storage file to validate (optional)
  --strict            Treat warnings as errors
  --help              Show this message and exit
```

**Validation Checks**:
- TOML syntax correctness
- JSON schema validation (required fields, data types, port ranges)
- Business logic validation (unique names/IPs, subnet membership, gen_global/gen_local constraints)
- Optional key storage validation (key existence, format validation)

**Examples**:

```bash
# Validate TOML configuration only
uv run wg-mesh-gen validate -c network.toml

# Validate configuration and keys
uv run wg-mesh-gen validate -c network.toml -k keys.json

# Strict mode (warnings cause exit code 1)
uv run wg-mesh-gen validate -c network.toml -k keys.json --strict
```

</details>

<details>
<summary><b>wg-mesh-gen migrate</b> - Migrate legacy JSON to TOML</summary>

```bash
uv run wg-mesh-gen migrate [OPTIONS]

Options:
  -i, --input PATH    Legacy JSON configuration file (required)
  -o, --output PATH   Output TOML file (required)
  -k, --keys PATH     Output key storage file (default: keys.json)
  --force             Overwrite existing files
  --help              Show this message and exit
```

**Migration Features**:
- Convert JSON structure to TOML format
- Extract embedded keys to separate `keys.json` file
- Rename `ipv4_addr` field to `endpoint` (new field name)
- Validate output TOML configuration
- Set 0600 permissions on key storage

**Examples**:

```bash
# Migrate with default key storage
uv run wg-mesh-gen migrate -i config.json -o network.toml

# Specify custom key storage path
uv run wg-mesh-gen migrate -i config.json -o network.toml -k custom-keys.json

# Force overwrite existing files
uv run wg-mesh-gen migrate -i config.json -o network.toml --force
```

</details>

## Configuration Format

<details>
<summary><b>TOML Configuration Structure</b></summary>

```toml
# Common network settings
[common]
network_name = "my-network"           # Network identifier (used in config filenames)
network_ipv4_addr = "10.0.0.0/24"     # VPN subnet (CIDR notation)

# Server configuration
[server]
name = "vpn-server"                   # Server identifier
endpoint = "vpn.example.com"          # Public endpoint (IPv4/IPv6/hostname)
vlan_ipv4_addr = "10.0.0.1"           # Server VPN IP (must be in subnet)
port = 51820                          # WireGuard listen port (1024-65535)
interface = "eth0"                    # Physical interface for NAT (iptables PostUp/PostDown)

# Client configurations (multiple clients supported)
[[clients]]
name = "laptop"                       # Client identifier (unique)
vlan_ipv4_addr = "10.0.0.2"           # Client VPN IP (unique, must be in subnet)
port = 51821                          # Client listen port (optional)
dns1 = "1.1.1.1"                      # Primary DNS (optional)
dns2 = "8.8.8.8"                      # Secondary DNS (optional)
gen_global = true                     # Generate config with AllowedIPs=0.0.0.0/0
gen_local = false                     # Generate config with AllowedIPs=subnet

[[clients]]
name = "phone"
vlan_ipv4_addr = "10.0.0.3"
port = 51822
gen_global = false
gen_local = true                      # At least one of gen_global/gen_local must be true
```

</details>

<details>
<summary><b>Key Storage Format</b></summary>

Keys are stored separately in `keys.json` with 0600 permissions:

```json
{
  "version": "1.0",
  "server": {
    "private_key": "cG9ydHMyNWNyeXB0b2dyYXBoeWxpYnJhcnk=",
    "public_key": "c2VydmVycHVibGlja2V5",
    "preshared_key": "cHJlc2hhcmVka2V5Zm9yc2VydmVy"
  },
  "clients": {
    "laptop": {
      "private_key": "Y2xpZW50bGFwdG9wcHJpdmF0ZWtleQ==",
      "public_key": "Y2xpZW50bGFwdG9wcHVibGlja2V5",
      "preshared_key": "cHJlc2hhcmVka2V5Zm9ybGFwdG9w"
    },
    "phone": {...}
  }
}
```

**Security Features**:
- Automatic 0600 permissions (read/write for owner only)
- Keys preserved on regeneration (unless `--refresh-force` used)
- Curve25519 key generation using Python's `cryptography` library
- Base64-encoded 32-byte keys (44 characters)

</details>

## Generated Files

**File Naming Convention**:
- Server: `wg-{network_name}-server-{server_name}.conf`
- Client (global): `wg-{network_name}-client-{client_name}-global.conf`
- Client (local): `wg-{network_name}-client-{client_name}-local.conf`

**Example**: Network named "my-vpn" with server "vpn-server" and client "laptop":
- `wg-my-vpn-server-vpn-server.conf` (1 server config)
- `wg-my-vpn-client-laptop-global.conf` (AllowedIPs=0.0.0.0/0)
- `wg-my-vpn-client-laptop-local.conf` (AllowedIPs=10.0.0.0/24)

## Development

<details>
<summary><b>Testing</b></summary>

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=wg_mesh_gen --cov-report=term-missing

# Run specific test suites
uv run pytest tests/unit/           # Unit tests only
uv run pytest tests/integration/    # Integration tests only
uv run pytest tests/contract/       # CLI contract tests only

# Run tests with verbose output
uv run pytest -v -s
```

**Test Coverage**: 62/62 tests passing (100%)
- Contract tests: 24/24 (CLI commands)
- Integration tests: 5/5 (end-to-end workflows)
- Unit tests: 33/33 (module functions)

</details>

<details>
<summary><b>Code Quality</b></summary>

```bash
# Lint and fix code
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check types (if using mypy)
uv run mypy src/
```

**Code Standards**:
- Python 3.12+
- Type hints for all functions
- Google-style docstrings
- Ruff linting (line length: 88)

</details>

## Project Structure

```
wireguard-configure-generator/
├── src/wg_mesh_gen/
│   ├── __init__.py
│   ├── cli.py              # Click-based CLI
│   ├── loader.py           # TOML/JSON loading
│   ├── validator.py        # Multi-layer validation
│   ├── key_manager.py      # Key generation & storage
│   ├── renderer.py         # Jinja2 template rendering
│   ├── migrator.py         # JSON-to-TOML migration
│   ├── models.py           # Data models
│   └── templates/
│       ├── server.conf.j2  # Server config template
│       └── client.conf.j2  # Client config template
├── tests/
│   ├── contract/           # CLI command tests
│   ├── integration/        # End-to-end tests
│   └── unit/               # Module unit tests
├── examples/
│   ├── star-network.toml   # Example configuration
│   └── legacy-config.json  # Legacy JSON example
├── pyproject.toml
├── README.md
├── README_ZH.md
└── CLAUDE.md               # Development guide
```

## License

BSD 3-Clause License

Copyright (c) 2022-2025, DengQi
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
