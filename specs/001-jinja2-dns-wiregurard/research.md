# Research & Technical Decisions

**Feature**: Modular Architecture Refactoring with Template System
**Date**: 2025-10-02
**Status**: Complete

## Research Questions Resolved

### 1. WireGuard Key Generation with Python Cryptography Library

**Question**: How to generate WireGuard-compatible keys using `cryptography>=45.0.2` without system `wg` tools?

**Decision**: Use Curve25519 private key generation with base64 encoding

**Rationale**:
- WireGuard uses Curve25519 for key exchange (same as used in modern protocols)
- Python `cryptography` library provides `X25519PrivateKey` for Curve25519
- Keys are 32-byte values encoded as base64 (matching `wg genkey/pubkey` output)
- Preshared keys are 32 random bytes encoded as base64

**Implementation Pattern**:
```python
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
import base64
import os

def generate_private_key() -> str:
    """Generate WireGuard private key."""
    private_key = x25519.X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    return base64.b64encode(private_bytes).decode('ascii')

def derive_public_key(private_key_b64: str) -> str:
    """Derive public key from private key."""
    private_bytes = base64.b64decode(private_key_b64)
    private_key = x25519.X25519PrivateKey.from_private_bytes(private_bytes)
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return base64.b64encode(public_bytes).decode('ascii')

def generate_preshared_key() -> str:
    """Generate WireGuard preshared key."""
    return base64.b64encode(os.urandom(32)).decode('ascii')
```

**Alternatives Considered**:
- ❌ `nacl` library: Less actively maintained, larger dependency
- ❌ Subprocess calls to `wg`: Violates requirement to avoid system tools

**References**:
- WireGuard protocol: https://www.wireguard.com/protocol/
- Curve25519: RFC 7748

---

### 2. TOML Parsing Library Selection

**Question**: Which TOML library for Python 3.12+?

**Decision**: Use `tomli` for reading (stdlib in Python 3.11+) and `tomli-w` for writing

**Rationale**:
- Python 3.11+ includes `tomllib` in stdlib (read-only)
- `tomli-w` provides write capability (needed for migration tool)
- Lightweight, well-maintained, TOML 1.0 compliant
- No external compilation dependencies (pure Python)

**Implementation Pattern**:
```python
import tomllib  # Python 3.11+ stdlib
import tomli_w  # for writing

def load_toml(path: Path) -> dict:
    with open(path, 'rb') as f:
        return tomllib.load(f)

def write_toml(data: dict, path: Path) -> None:
    with open(path, 'wb') as f:
        tomli_w.dump(data, f)
```

**Alternatives Considered**:
- ❌ `toml`: Deprecated in favor of `tomli`
- ❌ `tomlkit`: Heavier, preserves formatting (not needed for our use case)

---

### 3. Jinja2 Template Best Practices for WireGuard Configs

**Question**: How to structure Jinja2 templates for star topology (server + clients)?

**Decision**: Separate templates for server and client configs matching original format

**Rationale**:
- WireGuard config format is simple (INI-like)
- Server config includes PostUp/PostDown iptables rules for NAT
- Client configs differ by mode: global (AllowedIPs=0.0.0.0/0) vs local (AllowedIPs=network subnet)
- Matches original `wg_conf_gen.py` output format exactly

**Server Template** (`server.conf.j2`):
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

**Client Template** (`client.conf.j2`):
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

**Alternatives Considered**:
- ❌ String formatting: Less readable, harder to maintain
- ❌ Single unified template: Server and client configs too different

---

### 4. JSON Schema Validation for TOML Configs

**Question**: How to validate TOML structure with jsonschema?

**Decision**: Convert TOML dict to JSON-compatible structure, validate with jsonschema

**Rationale**:
- `jsonschema` is mature, well-tested, widely used
- TOML parses to Python dict (JSON-compatible)
- Supports complex validation rules (format checkers for IP/CIDR)
- Can define custom validators for business logic

**Schema Example** (matches original star topology):
```python
TOML_SCHEMA = {
    "type": "object",
    "required": ["common", "server", "clients"],
    "properties": {
        "common": {
            "type": "object",
            "required": ["network_name", "network_ipv4_addr"],
            "properties": {
                "network_name": {"type": "string", "minLength": 1},
                "network_ipv4_addr": {"type": "string", "format": "ipv4-cidr"}
            }
        },
        "server": {
            "type": "object",
            "required": ["name", "ipv4_addr", "vlan_ipv4_addr", "port", "interface"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "ipv4_addr": {"type": "string"},  # Public IP or hostname
                "vlan_ipv4_addr": {"type": "string", "format": "ipv4"},
                "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                "interface": {"type": "string", "minLength": 1}
            }
        },
        "clients": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "vlan_ipv4_addr", "port"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "vlan_ipv4_addr": {"type": "string", "format": "ipv4"},
                    "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                    "dns1": {"type": "string", "format": "ipv4"},
                    "dns2": {"type": "string", "format": "ipv4"},
                    "gen_global": {"type": "boolean"},
                    "gen_local": {"type": "boolean"}
                }
            }
        }
    }
}
```

**Format Checkers**:
```python
from jsonschema import FormatChecker
import ipaddress

@FormatChecker.cls_checks("ipv4")
def check_ipv4(instance):
    try:
        ipaddress.IPv4Address(instance)
        return True
    except ValueError:
        return False

@FormatChecker.cls_checks("ipv4-cidr")
def check_ipv4_cidr(instance):
    try:
        ipaddress.IPv4Network(instance)
        return True
    except ValueError:
        return False
```

**Alternatives Considered**:
- ❌ Pydantic: Heavier dependency, overkill for config validation
- ❌ Custom validators: Reinventing the wheel

---

### 5. Parallel Generation Strategy with Python

**Question**: How to implement --parallel flag for concurrent node config generation?

**Decision**: Use `concurrent.futures.ThreadPoolExecutor` for I/O-bound parallel rendering

**Rationale**:
- Config generation is I/O-bound (file writes, template rendering)
- ThreadPoolExecutor simpler than ProcessPoolExecutor for this use case
- Automatically manages thread pool size (default: min(32, os.cpu_count() + 4))
- Exception handling built-in with futures

**Implementation Pattern**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def generate_configs(nodes, output_dir, parallel=False):
    if parallel:
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(generate_single_config, node, output_dir): node
                for node in nodes
            }
            results = []
            for future in as_completed(futures):
                node = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to generate config for {node.name}: {e}")
                    results.append({"node": node.name, "error": str(e)})
            return results
    else:
        return [generate_single_config(node, output_dir) for node in nodes]
```

**Alternatives Considered**:
- ❌ ProcessPoolExecutor: Overkill, serialization overhead
- ❌ asyncio: More complex, no significant benefit for file I/O
- ❌ Manual threading: Error-prone, ThreadPoolExecutor handles gracefully

---

### 6. JSON-to-TOML Migration Strategy

**Question**: How to preserve all legacy JSON config features during migration?

**Decision**: Direct 1-to-1 field mapping preserving original structure (common/server/clients)

**Rationale**:
- Original JSON format already uses common/server/clients structure
- No field renaming needed (keys match exactly)
- Migration tool mainly converts file format, not structure
- Preserves user data integrity with zero information loss

**Migration Mapping**:
```python
def migrate_json_to_toml(json_config: dict) -> dict:
    """Convert legacy JSON config to TOML format.

    Original format already matches target TOML structure:
    - common: {network_name, network_ipv4_addr}
    - server: {name, ipv4_addr, vlan_ipv4_addr, port, interface}
    - clients: [{name, vlan_ipv4_addr, port, dns1, dns2, gen_global, gen_local}]
    """
    # Remove embedded keys (prvkey, pubkey, psk) - move to separate keys.json
    toml_config = {
        "common": json_config["common"],
        "server": {
            k: v for k, v in json_config["server"].items()
            if k not in ["prvkey", "pubkey", "psk"]
        },
        "clients": [
            {k: v for k, v in client.items() if k not in ["prvkey", "pubkey", "psk"]}
            for client in json_config["clients"]
        ]
    }
    return toml_config
```

**Key Extraction** (separate keys.json file):
```python
def extract_keys_from_json(json_config: dict) -> dict:
    """Extract embedded keys to separate storage."""
    return {
        "version": "1.0",
        "server": {
            "private_key": json_config["server"].get("prvkey"),
            "public_key": json_config["server"].get("pubkey"),
            "preshared_key": json_config["server"].get("psk")
        },
        "clients": {
            client["name"]: {
                "private_key": client.get("prvkey"),
                "public_key": client.get("pubkey"),
                "preshared_key": client.get("psk")
            }
            for client in json_config["clients"]
        }
    }
```

**Validation**: Both JSON and TOML configs validated with same jsonschema after parsing

---

## Dependency Version Justifications

| Dependency | Version | Justification |
|------------|---------|---------------|
| cryptography | >=45.0.2 | User-specified; latest stable with Curve25519 support |
| jinja2 | >=3.1.6 | User-specified; latest stable with security fixes |
| jsonschema | >=4.0 | Format checkers, Draft 2020-12 support |
| tomli-w | >=1.0 | TOML 1.0 write support |

**Note**: `tomllib` is Python 3.11+ stdlib, no external dependency for TOML reading.

---

## Risk Mitigation

### Key Generation Compatibility
**Risk**: Generated keys not compatible with native WireGuard
**Mitigation**: Comprehensive integration tests comparing output with `wg genkey/pubkey`

### Migration Data Loss
**Risk**: JSON-to-TOML migration loses configuration data
**Mitigation**: Bidirectional validation (JSON → TOML → validate → success/fail report)

### Parallel Generation Failures
**Risk**: Partial failure in parallel mode leaves inconsistent state
**Mitigation**: Atomic writes, rollback on any failure, clear error reporting per node

---

## Open Questions
None - All NEEDS CLARIFICATION items resolved via /clarify session.

---

**Research Status**: ✅ Complete - Ready for Phase 1 Design
