# Data Model

**Feature**: Modular Architecture Refactoring with Template System
**Date**: 2025-10-02
**Topology**: Simple star (1 server + N clients) - matches original `wg_conf_gen.py`

## Overview
This document defines the data structures for TOML configuration, JSON key storage, and internal representations. The architecture follows the original simple star topology: **one server + multiple clients** (not mesh/hub-spoke/relay).

---

## 1. TOML Configuration Schema

### NetworkConfig
Top-level configuration loaded from `.toml` files.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class NetworkConfig:
    """Network configuration (star topology: server + clients)."""
    common: CommonConfig
    server: ServerConfig
    clients: list[ClientConfig]
```

**Validation Rules**:
- `clients` MUST contain at least 1 client
- Simple star topology only (server connects to all clients)

---

### CommonConfig
Network-level common settings.

```python
@dataclass
class CommonConfig:
    """Common network settings."""
    network_name: str         # Network identifier
    network_ipv4_addr: str    # IPv4 CIDR (e.g., "10.0.0.0/24")
```

**Validation Rules**:
- `network_name`: Non-empty string, used in config filenames
- `network_ipv4_addr`: Valid IPv4 CIDR notation

**Example**:
```toml
[common]
network_name = "my-network"
network_ipv4_addr = "10.0.0.0/24"
```

---

### ServerConfig
Server node configuration.

```python
@dataclass
class ServerConfig:
    """WireGuard server configuration."""
    name: str               # Server name
    endpoint: str           # Public endpoint (IPv4, IPv6, or hostname)
    vlan_ipv4_addr: str     # VPN internal IP (within network_ipv4_addr)
    port: int               # Listen port (1024-65535)
    interface: str          # Physical network interface for NAT (e.g., "eth0")
```

**Validation Rules**:
- `name`: Non-empty string
- `endpoint`: Valid IPv4 address, IPv6 address, or hostname (public endpoint for clients to connect)
  - IPv4 example: `114.114.11.11`
  - IPv6 example: `2001:db8::1` or `[2001:db8::1]`
  - Hostname example: `vpn.example.com`
- `vlan_ipv4_addr`: Valid IPv4 within `common.network_ipv4_addr`
- `port`: Integer in range [1024, 65535]
- `interface`: Non-empty string (used for iptables rules)

**Example**:
```toml
[server]
name = "my-server"
endpoint = "vpn.example.com"     # Hostname (recommended for dynamic IPs)
# endpoint = "114.114.11.11"     # Or IPv4
# endpoint = "2001:db8::1"       # Or IPv6
vlan_ipv4_addr = "10.0.0.1"      # VPN IP
port = 51820
interface = "eth0"
```

---

### ClientConfig
Client node configuration.

```python
@dataclass
class ClientConfig:
    """WireGuard client configuration."""
    name: str               # Client name (unique)
    vlan_ipv4_addr: str     # VPN internal IP (unique, within network_ipv4_addr)
    port: int               # Listen port (1024-65535)
    dns1: Optional[str]     # Primary DNS server (IPv4)
    dns2: Optional[str]     # Secondary DNS server (IPv4)
    gen_global: bool        # Generate config with AllowedIPs = 0.0.0.0/0 (all traffic)
    gen_local: bool         # Generate config with AllowedIPs = network_ipv4_addr (VPN traffic only)
```

**Validation Rules**:
- `name`: Non-empty string, unique across all clients
- `vlan_ipv4_addr`: Valid IPv4 within `common.network_ipv4_addr`, unique
- `port`: Integer in range [1024, 65535]
- `dns1`, `dns2`: Optional, valid IPv4 addresses if provided
- `gen_global`, `gen_local`: At least one MUST be `true`

**Example**:
```toml
[[clients]]
name = "laptop"
vlan_ipv4_addr = "10.0.0.2"
port = 8080
dns1 = "10.15.44.11"
dns2 = "114.114.114.114"
gen_global = true    # Generate global config file (all traffic through VPN)
gen_local = true     # Generate local config file (VPN subnet traffic only)

[[clients]]
name = "phone"
vlan_ipv4_addr = "10.0.0.3"
port = 8081
dns1 = "1.1.1.1"
dns2 = "8.8.8.8"
gen_global = false
gen_local = true
```

---

## 2. JSON Key Storage Schema

### KeyStorage
Persistent storage for cryptographic keys. Matches original format with keys stored inline in config.

```python
# Storage format (JSON) - integrated with config
{
    "common": {...},
    "server": {
        "name": "my-server",
        ...,
        "prvkey": "cG9...",    # Base64-encoded Curve25519 private key
        "pubkey": "yJ3...",    # Base64-encoded Curve25519 public key
        "psk": "aB9..."        # Base64-encoded preshared key
    },
    "clients": [
        {
            "name": "laptop",
            ...,
            "prvkey": "xK2...",
            "pubkey": "tL5...",
            "psk": "mP7..."
        }
    ]
}
```

**New Separate Key Storage** (for this refactor):
```json
{
    "version": "1.0",
    "server": {
        "private_key": "cG9...",
        "public_key": "yJ3...",
        "preshared_key": "aB9..."
    },
    "clients": {
        "laptop": {
            "private_key": "xK2...",
            "public_key": "tL5...",
            "preshared_key": "mP7..."
        },
        "phone": {...}
    }
}
```

**Validation Rules**:
- All keys MUST be valid base64 strings
- Private/public keys MUST be 44 characters (32 bytes base64)
- Preshared keys MUST be 44 characters (32 bytes base64)

**File Permissions**: `0600` (owner read/write only)

---

## 3. Internal Representations

### RenderedServerConfig
Generated WireGuard configuration for server.

```python
@dataclass
class RenderedServerConfig:
    """Server WireGuard configuration."""
    interface_address: str           # e.g., "10.0.0.1/24"
    listen_port: int
    private_key: str
    post_up: str                     # iptables NAT rules
    post_down: str                   # iptables cleanup rules
    peers: list[ServerPeerConfig]    # One per client
```

```python
@dataclass
class ServerPeerConfig:
    """Client as seen by server."""
    name: str                        # Client name (comment)
    public_key: str
    preshared_key: str
    allowed_ips: str                 # e.g., "10.0.0.2/32"
```

---

### RenderedClientConfig
Generated WireGuard configuration for client (global or local mode).

```python
@dataclass
class RenderedClientConfig:
    """Client WireGuard configuration."""
    private_key: str
    address: str                     # e.g., "10.0.0.2/32"
    dns: str                         # e.g., "10.15.44.11,114.114.114.114"
    server_public_key: str
    preshared_key: str
    endpoint: str                    # e.g., "vpn.example.com:51820" or "114.114.11.11:8080" or "[2001:db8::1]:51820"
    allowed_ips: str                 # "0.0.0.0/0" (global) or "10.0.0.0/24" (local)
    persistent_keepalive: int        # Default: 25
```

---

## 4. Validation Schema (JSON Schema)

```python
NETWORK_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["common", "server", "clients"],
    "properties": {
        "common": {
            "type": "object",
            "required": ["network_name", "network_ipv4_addr"],
            "properties": {
                "network_name": {"type": "string", "minLength": 1},
                "network_ipv4_addr": {
                    "type": "string",
                    "pattern": "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}/\\d{1,2}$"
                }
            }
        },
        "server": {
            "type": "object",
            "required": ["name", "endpoint", "vlan_ipv4_addr", "port", "interface"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "endpoint": {
                    "type": "string",
                    "description": "IPv4, IPv6, or hostname for clients to connect"
                },
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
                    "port": {"type": "integer", "minimum": 1024, "maximum": 65535"},
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

---

## 5. Business Logic Validation Rules

### Network-Level Rules
1. **Unique Client Names**: No duplicate `name` in `clients` array
2. **Unique Client IPs**: No duplicate `vlan_ipv4_addr` in `clients` array
3. **IP Subnet Membership**: All `vlan_ipv4_addr` MUST be within `common.network_ipv4_addr`
4. **At Least One Output**: Each client MUST have `gen_global=true` OR `gen_local=true`

---

## 6. State Transitions

### Key Lifecycle
```
[No Key] → generate_key() → [Key Generated] → save_to_json() → [Key Stored]
          ↓
[Key Stored] → load_from_json() → reuse_key() → [Key Reused]
```

**Invariant**: Keys MUST NOT change after first generation (preserve on regeneration)

### Configuration Generation Flow
```
[TOML File] → load_config() → [NetworkConfig]
                            ↓
             validate() → [Validated Config]
                            ↓
             load_keys() → [Config + Keys]
                            ↓
             render_templates() → [Server .conf + Client .conf files]
```

---

## 7. Generated File Naming

**Server Config**:
```
wg-{network_name}-server-{server_name}.conf
```
Example: `wg-my-network-server-my-server.conf`

**Client Configs**:
- Global mode: `wg-{network_name}-client-{client_name}-global.conf`
- Local mode: `wg-{network_name}-client-{client_name}-local.conf`

Examples:
- `wg-my-network-client-laptop-global.conf` (AllowedIPs = 0.0.0.0/0)
- `wg-my-network-client-laptop-local.conf` (AllowedIPs = 10.0.0.0/24)

---

## 8. Example Data Flow

**Input TOML**:
```toml
[common]
network_name = "test-vpn"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "vpn-server"
ipv4_addr = "114.114.11.11"
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

**Rendered Server Config** (`wg-test-vpn-server-vpn-server.conf`):
```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = cG9...
PostUp = iptables -A FORWARD -i eth0 -o test-vpn -j ACCEPT; iptables -A FORWARD -i test-vpn -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i eth0 -o test-vpn -j ACCEPT; iptables -D FORWARD -i test-vpn -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

### Client laptop
[Peer]
PublicKey = tL5...
PresharedKey = mP7...
AllowedIPs = 10.0.0.2/32
```

**Rendered Client Config** (`wg-test-vpn-client-laptop-global.conf`):
```ini
[Interface]
PrivateKey = xK2...
Address = 10.0.0.2/32
DNS = 1.1.1.1,8.8.8.8

# server vpn-server
[Peer]
PublicKey = yJ3...
PresharedKey = mP7...
Endpoint = 114.114.11.11:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

---

**Data Model Status**: ✅ Complete (aligned with original `wg_conf_gen.py`)
