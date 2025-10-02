# CLAUDE.md - WireGuard Configuration Generator Development Guide

**Version**: 1.1.0
**Last Updated**: 2025-10-02
**Constitutional Compliance**: v1.2.0
**Topology**: Simple star (1 server + N clients) - matches `wg_conf_gen.py`

This document provides operational guidance for Claude when working on the WireGuard Configuration Generator project. It complements `.specify/memory/constitution.md` with practical development workflows and project-specific conventions.

---

## ⚠️ CRITICAL: Simple Star Topology Only

**This project uses SIMPLE STAR TOPOLOGY**: 1 server + N clients (NOT mesh/hub-spoke/relay)

- **Server**: Single node with public endpoint, all clients connect to it
- **Clients**: Multiple nodes, each client connects only to server
- **No complex routing**: No mesh, no multi-relay, no hub-spoke variants
- **Based on**: Original `wg_conf_gen.py` (187 lines, simple server/client model)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Development Environment](#development-environment)
3. [Data Model](#data-model)
4. [Code Standards](#code-standards)
5. [Testing Workflow](#testing-workflow)
6. [CLI Development](#cli-development)
7. [Configuration Management](#configuration-management)
8. [Security Guidelines](#security-guidelines)
9. [Common Tasks](#common-tasks)
10. [Quick Reference](#quick-reference)

---

## Project Overview

### Mission
Generate WireGuard VPN configurations from TOML files for **simple star topology** (1 server + N clients) with:
- TOML configuration format (human-readable)
- Jinja2 template rendering
- Separate JSON key storage
- Python cryptography library for key generation (no system `wg` command)
- Optional DNS per client
- Client mode support: global (AllowedIPs=0.0.0.0/0) or local (AllowedIPs=subnet)
- JSON-to-TOML migration tool

### Current Architecture

**Legacy Implementation**:
- File: `wg_conf_gen.py` (~187 lines)
- Config: JSON with embedded keys
- Keys: Generated via system `wg genkey/pubkey/genpsk`
- Topology: Server + clients (star)

**Target Modular Architecture**:
```
src/wg_mesh_gen/
├── __init__.py
├── cli.py              # Click-based CLI (generate, validate, migrate commands)
├── loader.py           # TOML/JSON configuration loader
├── validator.py        # JSON Schema + business logic validation
├── key_manager.py      # Python cryptography library key generation
├── renderer.py         # Jinja2 template rendering
├── migrator.py         # JSON-to-TOML migration + key extraction
└── templates/
    ├── server.conf.j2  # Server config with PostUp/PostDown iptables
    └── client.conf.j2  # Client config (variable allowed_ips)

tests/
├── conftest.py         # Shared pytest fixtures
├── contract/           # CLI command contract tests
├── integration/        # End-to-end workflow tests
└── unit/               # Module-specific unit tests

examples/
├── network.toml        # Example TOML config
├── config.example.json # Legacy JSON config
└── keys.json           # Example key storage
```

### Key Principles (from Constitution v1.2.0)
1. **Modular Architecture**: Separate modules for load/validate/render/keys
2. **CLI-First Design**: All features via CLI commands
3. **TDD Non-Negotiable**: Tests → Approval → Fail → Implementation
4. **Modern Python**: 3.12+, type hints, Ruff formatting
5. **uv-First**: No manual pip usage
6. **Comprehensive Testing**: pytest with ≥80% coverage

---

## Development Environment

### Setup Commands

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Navigate to project
cd /home/dengqi/Source/langs/python/wireguard-configure-generator-older

# 3. Sync dependencies (creates .venv automatically)
uv sync

# 4. Verify setup
uv run python -c "import sys; print(f'Python {sys.version}')"
```

### pyproject.toml Configuration

```toml
[project]
name = "wg-mesh-gen"
version = "0.1.0"
description = "WireGuard star topology configuration generator"
requires-python = ">=3.12"
dependencies = [
    "click>=8.1",           # CLI framework
    "jinja2>=3.1.6",        # Template rendering
    "tomli-w>=1.0",         # TOML writing
    "jsonschema>=4.0",      # Configuration validation
    "cryptography>=45.0.2", # Key generation (Curve25519)
]

[dependency-groups]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "ruff>=0.1",
]

[project.scripts]
wg-mesh-gen = "wg_mesh_gen.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "D"]
ignore = ["E501"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=wg_mesh_gen --cov-report=term-missing"
```

---

## Data Model

### TOML Configuration Structure

```toml
[common]
network_name = "my-network"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "vpn-server"
endpoint = "vpn.example.com"     # IPv4, IPv6, or hostname
vlan_ipv4_addr = "10.0.0.1"      # VPN internal IP
port = 51820
interface = "eth0"               # Physical interface for NAT

[[clients]]
name = "laptop"
vlan_ipv4_addr = "10.0.0.2"
port = 51821
dns1 = "1.1.1.1"                 # Optional
dns2 = "8.8.8.8"                 # Optional
gen_global = true                # Generate AllowedIPs=0.0.0.0/0 config
gen_local = true                 # Generate AllowedIPs=subnet config

[[clients]]
name = "phone"
vlan_ipv4_addr = "10.0.0.3"
port = 51822
gen_global = false
gen_local = true
```

### Key Storage (Separate JSON File)

```json
{
  "version": "1.0",
  "server": {
    "private_key": "cG9ydHMyNWNyeXB0b2dyYXBoeQ==",
    "public_key": "c2VydmVycHVibGlja2V5",
    "preshared_key": "cHJlc2hhcmVka2V5"
  },
  "clients": {
    "laptop": {
      "private_key": "bGFwdG9wcHJpdmF0ZWtleQ==",
      "public_key": "bGFwdG9wcHVibGlja2V5",
      "preshared_key": "bGFwdG9wcHNr"
    },
    "phone": {...}
  }
}
```

### Generated File Naming

- **Server**: `wg-{network_name}-server-{server_name}.conf`
  - Example: `wg-my-network-server-vpn-server.conf`

- **Client (global)**: `wg-{network_name}-client-{client_name}-global.conf`
  - Example: `wg-my-network-client-laptop-global.conf`

- **Client (local)**: `wg-{network_name}-client-{client_name}-local.conf`
  - Example: `wg-my-network-client-laptop-local.conf`

---

## Code Standards

### Type Hints (Mandatory)

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class ServerConfig:
    """WireGuard server configuration."""
    name: str
    endpoint: str          # IPv4, IPv6, or hostname
    vlan_ipv4_addr: str
    port: int
    interface: str

@dataclass
class ClientConfig:
    """WireGuard client configuration."""
    name: str
    vlan_ipv4_addr: str
    port: int
    dns1: Optional[str] = None
    dns2: Optional[str] = None
    gen_global: bool = True
    gen_local: bool = True
```

### Jinja2 Templates

**Server Template** (`templates/server.conf.j2`):
```jinja2
[Interface]
Address = {{ server.vlan_ipv4_addr }}/24
ListenPort = {{ server.port }}
PrivateKey = {{ server.private_key }}
PostUp = iptables -A FORWARD -i {{ server.interface }} -o {{ network_name }} -j ACCEPT; iptables -A FORWARD -i {{ network_name }} -j ACCEPT; iptables -t nat -A POSTROUTING -o {{ server.interface }} -j MASQUERADE
PostDown = iptables -D FORWARD -i {{ server.interface }} -o {{ network_name }} -j ACCEPT; iptables -D FORWARD -i {{ network_name }} -j ACCEPT; iptables -t nat -D POSTROUTING -o {{ server.interface }} -j MASQUERADE

{% for client in clients %}
### Client {{ client.name }}
[Peer]
PublicKey = {{ client.public_key }}
PresharedKey = {{ client.preshared_key }}
AllowedIPs = {{ client.vlan_ipv4_addr }}/32

{% endfor %}
```

**Client Template** (`templates/client.conf.j2`):
```jinja2
[Interface]
PrivateKey = {{ client.private_key }}
Address = {{ client.vlan_ipv4_addr }}/32
{% if client.dns1 and client.dns2 %}
DNS = {{ client.dns1 }},{{ client.dns2 }}
{% elif client.dns1 %}
DNS = {{ client.dns1 }}
{% endif %}

# server {{ server.name }}
[Peer]
PublicKey = {{ server.public_key }}
PresharedKey = {{ client.preshared_key }}
Endpoint = {{ server.endpoint }}:{{ server.port }}
AllowedIPs = {{ allowed_ips }}
PersistentKeepalive = 25
```

### Validation Rules

**Schema Validation**:
1. TOML syntax correctness
2. Required fields: `common`, `server`, `clients[]`
3. Port range: 1024-65535
4. IP format: Valid IPv4 addresses

**Business Logic Validation**:
1. Unique client names
2. Unique client `vlan_ipv4_addr`
3. All IPs within `common.network_ipv4_addr`
4. Each client: `gen_global=true` OR `gen_local=true`

---

## Testing Workflow

### TDD Cycle (Non-Negotiable)

```
1. Write test (RED) → 2. Get user approval → 3. Run test (FAIL) → 4. Implement → 5. Run test (GREEN) → 6. Refactor
```

### Example Test

```python
# tests/unit/test_key_manager.py
from wg_mesh_gen.key_manager import generate_keypair

def test_generate_keypair_returns_valid_base64_keys():
    """Test key generation produces valid base64 encoded keys."""
    keypair = generate_keypair()

    assert len(keypair.private_key) == 44  # 32 bytes base64
    assert len(keypair.public_key) == 44
    assert len(keypair.preshared_key) == 44

    # Verify base64 encoding
    import base64
    base64.b64decode(keypair.private_key)  # Should not raise
```

### Running Tests

```bash
uv run pytest                           # All tests
uv run pytest --cov                     # With coverage
uv run pytest tests/unit               # Unit tests only
uv run pytest -k "client"              # Tests matching "client"
```

---

## CLI Development

### CLI Commands

```bash
# Generate configs from TOML
wg-mesh-gen generate -c network.toml -o /etc/wireguard -k keys.json

# Generate with fresh keys (ignore existing keys.json)
wg-mesh-gen generate -c network.toml -o /etc/wireguard -k keys.json --refresh-force

# Validate TOML config only
wg-mesh-gen validate -c network.toml

# Validate TOML config + key storage
wg-mesh-gen validate -c network.toml -k keys.json

# Migrate JSON to TOML (extract embedded keys)
wg-mesh-gen migrate -i config.json -o network.toml -k keys.json
```

### Click Implementation Pattern

```python
import click
from pathlib import Path

@click.group()
@click.version_option(version="0.1.0")
def main():
    """WireGuard star topology configuration generator."""
    pass

@main.command()
@click.option("-c", "--config", type=click.Path(exists=True), required=True)
@click.option("-o", "--output", type=click.Path(), default=".")
@click.option("-k", "--keys", type=click.Path(), default="./keys.json")
@click.option("--parallel", is_flag=True, help="Enable parallel generation")
@click.option("--refresh-force", is_flag=True, help="Regenerate all keys (ignore existing)")
def generate(config, output, keys, parallel, refresh_force):
    """Generate WireGuard configurations."""
    # Implementation
    pass
```

---

## Security Guidelines

### Key Generation (Python cryptography)

```python
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
import base64
import os

def generate_keypair():
    """Generate WireGuard key pair using Python cryptography."""
    # Generate private key
    private_key = x25519.X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Derive public key
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    # Generate preshared key
    preshared_bytes = os.urandom(32)

    return {
        "private_key": base64.b64encode(private_bytes).decode('ascii'),
        "public_key": base64.b64encode(public_bytes).decode('ascii'),
        "preshared_key": base64.b64encode(preshared_bytes).decode('ascii')
    }
```

### File Permissions

```python
# Set restrictive permissions on key files
Path("keys.json").chmod(0o600)

# Set restrictive permissions on config files
for conf_file in Path("/etc/wireguard").glob("*.conf"):
    conf_file.chmod(0o600)
```

---

## Common Tasks

### Task 1: Generate Configs from TOML

```bash
# 1. Create TOML config
cat > network.toml <<EOF
[common]
network_name = "test"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "srv"
ipv4_addr = "1.2.3.4"
vlan_ipv4_addr = "10.0.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "laptop"
vlan_ipv4_addr = "10.0.0.2"
port = 51821
dns1 = "1.1.1.1"
gen_global = true
gen_local = true
EOF

# 2. Generate (will create keys.json automatically)
uv run wg-mesh-gen generate -c network.toml -o output/ -k keys.json

# 3. Verify
ls -l output/
cat output/wg-test-server-srv.conf
cat output/wg-test-client-laptop-global.conf
cat keys.json  # Check generated keys
```

### Task 2: Migrate Legacy JSON to TOML

```bash
# Convert config.json to network.toml + keys.json
uv run wg-mesh-gen migrate -i config.json -o network.toml -k keys.json

# Result: network.toml (config) + keys.json (extracted keys)
```

---

## Quick Reference

### uv Commands
```bash
uv sync                          # Install dependencies
uv add <package>                 # Add dependency
uv run <command>                 # Run in venv
```

### pytest Commands
```bash
uv run pytest                    # All tests
uv run pytest --cov              # With coverage
uv run pytest -v -s              # Verbose with output
```

### Ruff Commands
```bash
uv run ruff check --fix .        # Lint and fix
uv run ruff format .             # Format code
```

---

## Project Status

**Current Feature Branch**: `001-jinja2-dns-wiregurard`

**Completed**:
- ✅ Feature specification (spec.md)
- ✅ Design documents (data-model.md, research.md)
- ✅ CLI contracts (generate, validate, migrate)
- ✅ Quickstart guide
- ✅ Implementation plan

**Next Steps**:
1. Run `/tasks` to generate task list
2. Implement modules following TDD workflow
3. Create contract tests
4. Implement functionality
5. Integration testing

---

**End of CLAUDE.md v1.1.0**
