# CLI Contract: migrate

**Command**: `wg-mesh-gen migrate`

**Purpose**: Convert legacy JSON configuration files to TOML format

---

## Signature

```bash
wg-mesh-gen migrate [OPTIONS]
```

---

## Options

| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--input` | `-i` | Path | Yes | - | Path to legacy JSON configuration file |
| `--output` | `-o` | Path | No | `network.toml` | Output path for TOML configuration file |
| `--keys` | `-k` | Path | No | `keys.json` | Output path for extracted key storage file |
| `--validate` | `-v` | Flag | No | True | Validate output TOML before writing |
| `--force` | `-f` | Flag | No | False | Overwrite existing output files (TOML and keys) |

---

## Input Contract

### Legacy JSON Configuration
- **Format**: Valid JSON syntax
- **Schema**: Must conform to legacy JSON schema (see below)
- **Location**: File must exist and be readable

**Legacy JSON Schema** (matches original `wg_conf_gen.py`):
```json
{
  "common": {
    "network_name": "string",
    "network_ipv4_addr": "string (IPv4 CIDR)"
  },
  "server": {
    "name": "string",
    "endpoint": "string (IPv4, IPv6, or hostname)",
    "vlan_ipv4_addr": "string (VPN internal IP)",
    "port": "integer",
    "interface": "string",
    "prvkey": "string (optional, embedded key)",
    "pubkey": "string (optional, embedded key)",
    "psk": "string (optional, embedded key)"
  },
  "clients": [
    {
      "name": "string",
      "vlan_ipv4_addr": "string (VPN internal IP)",
      "port": "integer",
      "dns1": "string (IPv4, optional)",
      "dns2": "string (IPv4, optional)",
      "gen_global": "boolean",
      "gen_local": "boolean",
      "prvkey": "string (optional, embedded key)",
      "pubkey": "string (optional, embedded key)",
      "psk": "string (optional, embedded key)"
    }
  ]
}
```

---

## Output Contract

### Success (Exit Code 0)

**stdout**:
```
✅ Loaded legacy JSON configuration: /path/to/config.json
✅ Extracted embedded keys from server and 2 clients
✅ Converted server + 2 clients from JSON to TOML format
✅ Validated output TOML configuration
✅ Wrote TOML configuration: network.toml
✅ Wrote key storage: keys.json (permissions: 0600)

Migration Summary:
  Server: 1
  Clients: 2
  Keys extracted: 3 (server + 2 clients)
  Output files: network.toml, keys.json
  Warnings: 0
```

**Generated File**: `network.toml`
```toml
[common]
network_name = "my-network"
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
gen_local = true

[[clients]]
name = "phone"
vlan_ipv4_addr = "10.0.0.3"
port = 51822
gen_global = false
gen_local = true
```

**Generated File**: `keys.json` (separate key storage)
```json
{
  "version": "1.0",
  "server": {
    "private_key": "cG9ydH...",
    "public_key": "c2Vydm...",
    "preshared_key": "cHJlc2..."
  },
  "clients": {
    "laptop": {
      "private_key": "bGFwdG...",
      "public_key": "bGFwdG...",
      "preshared_key": "bGFwdG..."
    },
    "phone": {
      "private_key": "cGhvbm...",
      "public_key": "cGhvbm...",
      "preshared_key": "cGhvbm..."
    }
  }
}
```

---

### Validation Warnings (Exit Code 0)

**stdout**:
```
✅ Converted server + 2 clients from JSON to TOML format
⚠️  Warnings:
  - Client 'phone': Missing dns1/dns2 configuration (optional)
  - Client 'phone': gen_global=false may limit connectivity (only local subnet routing)

✅ Wrote TOML configuration: network.toml
✅ Wrote key storage: keys.json
```

**Behavior**: Migration succeeds with warnings logged

---

### Input Errors (Exit Code 1)

**stderr**:
```
❌ Error: Input file not found: /path/to/legacy-config.json
```

or

```
❌ Error: Invalid JSON syntax in /path/to/legacy-config.json:
  Line 10: Unexpected token ','
```

or

```
❌ Error: Legacy JSON does not match expected schema:
  - Missing required field 'common.network_name'
  - Missing required field 'server.interface'
  - Client 'laptop': Missing required field 'vlan_ipv4_addr'
```

---

### Output Errors (Exit Code 1)

**stderr**:
```
❌ Error: Output files already exist: network.toml, keys.json
Use --force to overwrite
```

or

```
❌ Error: Output directory /path/to is not writable
```

or

```
❌ Error: Key storage file keys.json already exists
Use --force to overwrite
```

---

### Validation Errors (Exit Code 1)

**stderr** (when `--validate` is True):
```
❌ Error: Migrated TOML configuration failed validation:
  - Server vlan_ipv4_addr 10.0.1.1 outside network subnet 10.0.0.0/24
  - Client 'laptop' and 'phone': Duplicate vlan_ipv4_addr 10.0.0.2
  - Client 'tablet': Both gen_global=false and gen_local=false (at least one must be true)

Migration aborted. Fix source JSON and retry.
```

**Behavior**: No TOML file written, migration aborted

---

## Field Mapping

### Common Section
| JSON Field | TOML Field | Transformation |
|------------|------------|----------------|
| `common.network_name` | `common.network_name` | Direct copy |
| `common.network_ipv4_addr` | `common.network_ipv4_addr` | Direct copy |

### Server Section
| JSON Field | TOML Field | Transformation |
|------------|------------|----------------|
| `server.name` | `server.name` | Direct copy |
| `server.endpoint` (or `server.ipv4_addr` legacy) | `server.endpoint` | Direct copy (renamed field) |
| `server.vlan_ipv4_addr` | `server.vlan_ipv4_addr` | Direct copy |
| `server.port` | `server.port` | Direct copy |
| `server.interface` | `server.interface` | Direct copy |
| `server.prvkey` | (keys.json) `server.private_key` | Extract to separate file |
| `server.pubkey` | (keys.json) `server.public_key` | Extract to separate file |
| `server.psk` | (keys.json) `server.preshared_key` | Extract to separate file |

### Client Section
| JSON Field | TOML Field | Transformation |
|------------|------------|----------------|
| `clients[].name` | `clients[].name` | Direct copy |
| `clients[].vlan_ipv4_addr` | `clients[].vlan_ipv4_addr` | Direct copy |
| `clients[].port` | `clients[].port` | Direct copy |
| `clients[].dns1` | `clients[].dns1` | Direct copy (optional) |
| `clients[].dns2` | `clients[].dns2` | Direct copy (optional) |
| `clients[].gen_global` | `clients[].gen_global` | Direct copy |
| `clients[].gen_local` | `clients[].gen_local` | Direct copy |
| `clients[].prvkey` | (keys.json) `clients.{name}.private_key` | Extract to separate file |
| `clients[].pubkey` | (keys.json) `clients.{name}.public_key` | Extract to separate file |
| `clients[].psk` | (keys.json) `clients.{name}.preshared_key` | Extract to separate file |

### Key Extraction
**Original**: Keys embedded in same JSON file
**New**: Keys separated into `keys.json` file

**Rationale**: Separation of concerns - configuration data vs cryptographic material

---

## Examples

### Basic Migration
```bash
wg-mesh-gen migrate -i config.json -o network.toml -k keys.json
```

**Expected**:
- Reads `config.json` (with embedded keys)
- Extracts keys to `keys.json` (separate file)
- Converts configuration to TOML format
- Validates output TOML
- Writes `network.toml` and `keys.json`

---

### Migration Without Validation
```bash
wg-mesh-gen migrate -i config.json --no-validate
```

**Expected**:
- Skips TOML validation
- Useful for debugging or partial configs

---

### Force Overwrite
```bash
wg-mesh-gen migrate -i config.json -o network.toml -k keys.json --force
```

**Expected**:
- Overwrites existing `network.toml` and `keys.json` without prompting

---

## Validation Rules

### Pre-Migration Validation
1. JSON syntax correctness
2. Legacy JSON schema compliance (required fields present)
3. Input file exists and is readable

### Post-Migration Validation (if `--validate` is True)
1. TOML syntax correctness
2. Modern TOML schema compliance
3. Business logic validation (same as `generate` command)

---

## Error Handling

### Data Integrity
- Migration MUST preserve all user data from JSON
- No information loss during conversion
- Validation errors detected before writing output

### Rollback
- If validation fails, no TOML file is written
- Original JSON file MUST NOT be modified

---

## Performance Expectations

- **Small configs (< 10 nodes)**: < 100ms
- **Medium configs (10-100 nodes)**: < 500ms
- **Large configs (100-1000 nodes)**: < 2 seconds

---

## Contract Test Requirements

Tests MUST verify:
1. ✅ Valid JSON input generates valid TOML output and keys.json
2. ✅ All JSON fields correctly mapped to TOML equivalents
3. ✅ Embedded keys extracted to separate keys.json file
4. ✅ `-k` option specifies custom key storage path
5. ✅ Invalid JSON syntax returns exit code 1 with error message
6. ✅ Missing required JSON fields return descriptive error
7. ✅ Output TOML passes validation (when --validate is True)
8. ✅ Validation errors prevent file write
9. ✅ --force flag overwrites existing output files (TOML + keys.json)
10. ✅ Without --force, existing output files cause error
11. ✅ keys.json has 0600 permissions
12. ✅ Original JSON file never modified

---

## Deprecation Notice

After migration, users MUST update to TOML format. The migrated TOML file SHOULD include a comment:

```toml
# Migrated from legacy JSON configuration on 2025-10-02
# JSON format is deprecated. Use this TOML file going forward.

[network]
name = "my-vpn"
# ...
```

---

**Contract Status**: ✅ Complete
