# Quickstart Guide

**Feature**: Modular Architecture Refactoring with Template System
**Date**: 2025-10-02

This quickstart demonstrates the core workflows for the refactored WireGuard configuration generator with TOML support, Jinja2 templates, and modular architecture.

**⚠️ IMPORTANT**: This project uses **simple star topology** (1 server + N clients), NOT mesh/hub-spoke/relay.

---

## Prerequisites

1. Python 3.12+ installed
2. `uv` package manager installed
3. Project dependencies installed: `uv sync`
4. WireGuard installed (for testing generated configs)

---

## Scenario 1: Generate Star Network Configuration

### Step 1: Create TOML Configuration

**File**: `examples/star-network.toml`

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

[[clients]]
name = "phone"
vlan_ipv4_addr = "10.0.0.3"
port = 51822
gen_global = false
gen_local = true
```

### Step 2: Validate Configuration

```bash
uv run wg-mesh-gen validate -c examples/star-network.toml
```

**Expected Output**:
```
✅ TOML syntax: Valid
✅ Schema validation: Passed
✅ Business logic validation: Passed

Configuration summary:
  Network: my-vpn (10.0.0.0/24)
  Topology: star (1 server + 2 clients)
  Server: vpn-server (10.0.0.1)
  Clients: laptop, phone

✅ Configuration is valid and ready for generation
```

### Step 3: Generate Configurations

```bash
uv run wg-mesh-gen generate -c examples/star-network.toml -o output/
```

**Expected Output**:
```
✅ Validated configuration: 1 server + 2 clients
✅ Generated keys for server and 2 clients (new)
✅ Generated configuration: output/wg-my-vpn-server-vpn-server.conf
✅ Generated configuration: output/wg-my-vpn-client-laptop-global.conf
✅ Generated configuration: output/wg-my-vpn-client-phone-local.conf

Summary:
  Server configs: 1
  Client configs: 2 (1 global, 1 local)
  Keys generated: 3
  Output directory: output/
```

### Step 4: Verify Generated Files

```bash
ls -la output/
cat output/wg-my-vpn-server-vpn-server.conf
```

**Expected `output/wg-my-vpn-server-vpn-server.conf`**:
```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = cG9ydHMyNWNyeXB0b2dyYXBoeWxpYnJhcnk=
PostUp = iptables -A FORWARD -i eth0 -o my-vpn -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i eth0 -o my-vpn -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

### Client laptop
[Peer]
PublicKey = Y2xpZW50bGFwdG9wcHVibGlja2V5
PresharedKey = cHJlc2hhcmVka2V5Zm9ybGFwdG9w
AllowedIPs = 10.0.0.2/32

### Client phone
[Peer]
PublicKey = Y2xpZW50cGhvbmVwdWJsaWNrZXk=
PresharedKey = cHJlc2hhcmVka2V5Zm9ycGhvbmU=
AllowedIPs = 10.0.0.3/32
```

**Expected `output/wg-my-vpn-client-laptop-global.conf`**:
```ini
[Interface]
Address = 10.0.0.2/24
PrivateKey = Y2xpZW50bGFwdG9wcHJpdmF0ZWtleQ==
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = c2VydmVycHVibGlja2V5
PresharedKey = cHJlc2hhcmVka2V5Zm9ybGFwdG9w
Endpoint = vpn.example.com:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

**Key Storage** (`keys.json`):
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

### Step 5: Test Configuration (Optional)

```bash
sudo wg-quick up output/wg-my-vpn-server-vpn-server.conf
wg show
sudo wg-quick down output/wg-my-vpn-server-vpn-server.conf
```

---

## Scenario 2: Migrate Legacy JSON Configuration

### Step 1: Create Legacy JSON Config

**File**: `examples/legacy-config.json`

```json
{
  "common": {
    "network_name": "old-vpn",
    "network_ipv4_addr": "10.1.0.0/24"
  },
  "server": {
    "name": "vpn-hub",
    "ipv4_addr": "hub.example.com",
    "vlan_ipv4_addr": "10.1.0.1",
    "port": 51820,
    "interface": "eth0",
    "prvkey": "EMBEDDED_PRIVATE_KEY",
    "pubkey": "EMBEDDED_PUBLIC_KEY",
    "psk": "EMBEDDED_PSK"
  },
  "clients": [
    {
      "name": "spoke1",
      "vlan_ipv4_addr": "10.1.0.2",
      "port": 51821,
      "dns1": "1.1.1.1",
      "gen_global": true,
      "gen_local": false,
      "prvkey": "CLIENT_PRIVATE_KEY",
      "pubkey": "CLIENT_PUBLIC_KEY",
      "psk": "CLIENT_PSK"
    }
  ]
}
```

### Step 2: Migrate to TOML

```bash
uv run wg-mesh-gen migrate -i examples/legacy-config.json -o examples/migrated-config.toml
```

**Expected Output**:
```
✅ Loaded legacy JSON configuration: examples/legacy-config.json
✅ Extracted embedded keys from server and 1 client
✅ Converted to TOML format (common + server + 1 client)
⚠️  Warnings:
  - Embedded keys extracted to keys.json
  - JSON format is deprecated, use TOML going forward

✅ Validated output TOML configuration
✅ Wrote TOML configuration: examples/migrated-config.toml
✅ Wrote key storage: keys.json
```

### Step 3: Verify Migrated TOML

```bash
cat examples/migrated-config.toml
cat keys.json
```

**Expected `examples/migrated-config.toml`**:
```toml
# Migrated from legacy JSON configuration on 2025-10-02
# JSON format is deprecated. Use this TOML file going forward.

[common]
network_name = "old-vpn"
network_ipv4_addr = "10.1.0.0/24"

[server]
name = "vpn-hub"
endpoint = "hub.example.com"
vlan_ipv4_addr = "10.1.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "spoke1"
vlan_ipv4_addr = "10.1.0.2"
port = 51821
dns1 = "1.1.1.1"
gen_global = true
gen_local = false
```

**Expected `keys.json`** (extracted from JSON):
```json
{
  "version": "1.0",
  "server": {
    "private_key": "EMBEDDED_PRIVATE_KEY",
    "public_key": "EMBEDDED_PUBLIC_KEY",
    "preshared_key": "EMBEDDED_PSK"
  },
  "clients": {
    "spoke1": {
      "private_key": "CLIENT_PRIVATE_KEY",
      "public_key": "CLIENT_PUBLIC_KEY",
      "preshared_key": "CLIENT_PSK"
    }
  }
}
```

### Step 4: Generate from Migrated Config

```bash
uv run wg-mesh-gen generate -c examples/migrated-config.toml -o output-migrated/
```

---

## Scenario 3: Parallel Generation for Large Networks

### Step 1: Create Large Network Config

**File**: `examples/large-network.toml` (10 clients example)

```toml
[common]
network_name = "large-vpn"
network_ipv4_addr = "10.2.0.0/24"

[server]
name = "main-server"
endpoint = "vpn.example.com"
vlan_ipv4_addr = "10.2.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "client-01"
vlan_ipv4_addr = "10.2.0.2"
port = 51821
gen_global = true
gen_local = false

[[clients]]
name = "client-02"
vlan_ipv4_addr = "10.2.0.3"
port = 51822
gen_global = true
gen_local = false

# ... (8 more clients)

[[clients]]
name = "client-10"
vlan_ipv4_addr = "10.2.0.11"
port = 51830
gen_global = true
gen_local = false
```

### Step 2: Generate with Parallel Flag

```bash
time uv run wg-mesh-gen generate -c examples/large-network.toml -o output-large/ --parallel
```

**Expected Output**:
```
✅ Validated configuration: 1 server + 10 clients
✅ Generated keys for server and 10 clients (new)
✅ Parallel generation: Processing 11 configs (1 server + 20 client configs) concurrently...
✅ Generated server config → output-large/wg-large-vpn-server-main-server.conf
✅ Generated client configs → output-large/wg-large-vpn-client-*-{global,local}.conf

Summary:
  Server configs: 1
  Client configs: 20 (10 global + 10 local)
  Keys generated: 11
  Output directory: output-large/
  Execution time: 0.8s (parallel mode)

Performance: 5.6x faster than sequential mode
```

### Step 3: Compare with Sequential Mode

```bash
time uv run wg-mesh-gen generate -c examples/large-network.toml -o output-sequential/
```

**Expected**: Sequential mode takes ~4.5s for 1 server + 10 clients (21 total config files)

---

## Scenario 4: Regenerate with Existing Keys

### Step 1: Modify Network Config

Edit `examples/star-network.toml` to add a new client:

```toml
[[clients]]
name = "tablet"
vlan_ipv4_addr = "10.0.0.4"
port = 51823
gen_global = true
gen_local = true
```

### Step 2: Regenerate Configurations

```bash
uv run wg-mesh-gen generate -c examples/star-network.toml -o output/ --force
```

**Expected Output**:
```
✅ Validated configuration: 1 server + 3 clients
✅ Loaded keys for server and 2 clients (vpn-server, laptop, phone)
✅ Generated key for 1 new client (tablet)
✅ Generated server config → output/wg-my-vpn-server-vpn-server.conf
✅ Generated client configs → output/wg-my-vpn-client-*.conf

Summary:
  Server configs: 1
  Client configs: 6 (laptop-global, laptop-local, phone-global, phone-local, tablet-global, tablet-local)
  Keys reused: 3
  Keys generated: 1
```

**Key Observation**: Existing nodes (vpn-server, laptop, phone) keep their original keys. Only `tablet` gets a new key.

---

## Scenario 5: Error Handling - Invalid Configuration

### Step 1: Create Invalid TOML

**File**: `examples/invalid-network.toml`

```toml
[common]
network_name = "invalid"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "server1"
endpoint = "vpn.example.com"
vlan_ipv4_addr = "10.0.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "client1"
vlan_ipv4_addr = "10.0.0.2"
port = 70000  # Invalid: exceeds max port 65535
gen_global = true
gen_local = false

[[clients]]
name = "client1"  # Duplicate name
vlan_ipv4_addr = "10.0.0.2"  # Duplicate IP
port = 51821
gen_global = false  # Invalid: at least one of gen_global/gen_local must be true
gen_local = false
```

### Step 2: Attempt Validation

```bash
uv run wg-mesh-gen validate -c examples/invalid-network.toml
```

**Expected Output (Exit Code 1)**:
```
❌ Schema validation failed: examples/invalid-network.toml

Errors:
  - clients[0].port: Value 70000 exceeds maximum 65535

❌ Business logic validation failed:

Errors:
  - Line 24: Duplicate client name 'client1' (first occurrence at line 18)
  - Line 25: Duplicate vlan_ipv4_addr '10.0.0.2' (first occurrence at line 19)
  - Line 27-28: Client 'client1': At least one of gen_global or gen_local must be true

Total errors: 4
```

### Step 3: Fix and Re-validate

Fix the errors in `examples/invalid-network.toml`:

```toml
[[clients]]
name = "client1"
vlan_ipv4_addr = "10.0.0.2"
port = 51821  # Fixed
gen_global = true
gen_local = false

[[clients]]
name = "client2"  # Fixed: unique name
vlan_ipv4_addr = "10.0.0.3"  # Fixed: unique IP
port = 51822
gen_global = false
gen_local = true  # Fixed: at least one true
```

```bash
uv run wg-mesh-gen validate -c examples/invalid-network.toml
```

**Expected Output**:
```
✅ TOML syntax: Valid
✅ Schema validation: Passed
✅ Business logic validation: Passed

Configuration summary:
  Network: invalid (10.0.0.0/24)
  Topology: star (1 server + 2 clients)

✅ Configuration is valid and ready for generation
```

---

## Acceptance Criteria Verification

### ✅ FR-001: TOML Configuration Input
- **Verified in**: Scenario 1, Step 1
- **Test**: Created TOML config file with [common], [server], [[clients]] sections

### ✅ FR-002: Jinja2 Template Rendering
- **Verified in**: Scenario 1, Step 4
- **Test**: Generated server/client `.conf` files match WireGuard format with PostUp/PostDown rules

### ✅ FR-003: Separate Key Storage
- **Verified in**: Scenario 1, Step 4 & Scenario 4
- **Test**: Keys stored in `keys.json` with server{} and clients{name:{}} structure

### ✅ FR-004: Cryptography Library Key Generation
- **Verified in**: Scenario 1, Step 3
- **Test**: Keys generated using Python cryptography library (no `wg` command)

### ✅ FR-005: Node-Level DNS Configuration
- **Verified in**: Scenario 1, Step 1 & Step 4
- **Test**: Client `laptop` has dns1/dns2, client `phone` doesn't

### ✅ FR-006: Multi-Layer Validation
- **Verified in**: Scenario 5
- **Test**: TOML syntax, schema (port range, required fields), business logic (unique names/IPs, gen_global/gen_local)

### ✅ FR-007: Parallel Generation
- **Verified in**: Scenario 3
- **Test**: `--parallel` flag enables concurrent generation for multiple client configs

### ✅ FR-008: Key Preservation
- **Verified in**: Scenario 4
- **Test**: Existing server/client keys reused on regeneration

### ✅ FR-009: Actionable Error Messages
- **Verified in**: Scenario 5
- **Test**: Errors include line numbers, field names, and specific violations

### ✅ FR-011: JSON-to-TOML Migration
- **Verified in**: Scenario 2
- **Test**: Legacy JSON (common + server + clients[]) converted to TOML with key extraction

---

## Performance Benchmarks

| Scenario | Server + Clients | Config Files | Mode | Expected Time |
|----------|------------------|--------------|------|---------------|
| Star network | 1 + 2 | 5 (1 server + 4 client) | Sequential | < 1s |
| Large network | 1 + 10 | 21 (1 server + 20 client) | Sequential | ~4.5s |
| Large network | 1 + 10 | 21 (1 server + 20 client) | Parallel | ~0.8s |
| Validation only | 1 + 100 | N/A | N/A | < 1s |

---

## Next Steps

After quickstart verification:
1. Run full test suite: `uv run pytest`
2. Check code coverage: `uv run pytest --cov=wg_mesh_gen --cov-report=term-missing`
3. Deploy to production with validated configs

---

**Quickstart Status**: ✅ Complete
