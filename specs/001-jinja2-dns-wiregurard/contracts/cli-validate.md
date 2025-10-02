# CLI Contract: validate

**Command**: `wg-mesh-gen validate`

**Purpose**: Validate TOML configuration file without generating configs

---

## Signature

```bash
wg-mesh-gen validate [OPTIONS]
```

---

## Options

| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--config` | `-c` | Path | Yes | - | Path to TOML configuration file to validate |
| `--keys` | `-k` | Path | No | None | Path to key storage file (validates key-config compatibility) |
| `--strict` | `-s` | Flag | No | False | Enable strict mode (warnings treated as errors) |

---

## Input Contract

### Configuration File (TOML)
- **Format**: TOML syntax (may be invalid)
- **Location**: File must exist and be readable

### Key Storage File (JSON, optional)
- **Format**: Valid JSON syntax (if provided)
- **Schema**: Must have `server{}` and `clients{name:{}}` structure
- **Behavior**: If provided via `-k`, validates that keys exist for all nodes in config

---

## Output Contract

### Success (Exit Code 0)

**stdout** (without `--keys`):
```
✅ TOML syntax: Valid
✅ Schema validation: Passed
✅ Business logic validation: Passed

Configuration summary:
  Network: my-vpn (10.0.0.0/24)
  Topology: star (1 server + 2 clients)
  Server: vpn-server
  Clients: 2 (laptop, phone)

Validation checks:
  ✓ No duplicate client names
  ✓ No duplicate IP addresses
  ✓ All IPs within subnet
  ✓ Port ranges valid (1024-65535)
  ✓ DNS nameservers are valid IPv4
  ✓ gen_global/gen_local constraints satisfied

✅ Configuration is valid and ready for generation
```

**stdout** (with `--keys`):
```
✅ TOML syntax: Valid
✅ Schema validation: Passed
✅ Business logic validation: Passed
✅ Key storage validation: Passed

Configuration summary:
  Network: my-vpn (10.0.0.0/24)
  Topology: star (1 server + 2 clients)
  Server: vpn-server
  Clients: 2 (laptop, phone)

Validation checks:
  ✓ No duplicate client names
  ✓ No duplicate IP addresses
  ✓ All IPs within subnet
  ✓ Port ranges valid (1024-65535)
  ✓ DNS nameservers are valid IPv4
  ✓ gen_global/gen_local constraints satisfied

Key storage checks:
  ✓ keys.json exists and is readable
  ✓ Server 'vpn-server' has keys (private_key, public_key, preshared_key)
  ✓ Client 'laptop' has keys
  ✓ Client 'phone' has keys
  ✓ All keys are valid base64 (44 characters)

✅ Configuration and keys are valid and ready for generation
```

---

### Success with Warnings (Exit Code 0, or 1 if `--strict`)

**stdout**:
```
✅ TOML syntax: Valid
✅ Schema validation: Passed
✅ Business logic validation: Passed

⚠️  Warnings:
  - Client 'laptop': dns2 not specified (using only primary DNS)
  - Client 'phone': gen_global=false may limit connectivity (only local subnet routing)
  - Performance: 50+ clients detected, consider using --parallel flag for generation

✅ Configuration is valid with minor warnings
```

**Exit Code**:
- **Normal mode**: 0 (warnings don't fail)
- **Strict mode (`--strict`)**: 1 (warnings treated as errors)

---

### Syntax Errors (Exit Code 1)

**stderr**:
```
❌ TOML syntax error in /path/to/config.toml:

Line 10: Expected '=' after key, found ','
      8 | [[nodes]]
      9 | name = "server"
  --> 10 | ip, = "10.0.0.1"
         |    ^
     11 | port = 51820

Fix: Remove the comma or check TOML syntax
```

---

### Schema Validation Errors (Exit Code 1)

**stderr**:
```
❌ Schema validation failed: /path/to/config.toml

Errors:
  - common.network_name: Required field missing
  - common.network_ipv4_addr: Invalid format "10.0.0/24" (expected CIDR like "10.0.0.0/24")
  - server.interface: Required field missing
  - clients[0].port: Value 70000 exceeds maximum 65535
  - clients[1].vlan_ipv4_addr: Required field missing

Total errors: 5
```

---

### Business Logic Validation Errors (Exit Code 1)

**stderr**:
```
❌ Business logic validation failed: /path/to/config.toml

Errors:
  - Line 15: Duplicate client name 'laptop' (first occurrence at line 10)
  - Line 20: Duplicate client vlan_ipv4_addr '10.0.0.2' (assigned to clients 'laptop' and 'phone')
  - Line 18: Server vlan_ipv4_addr '10.0.1.1' outside network subnet '10.0.0.0/24'
  - Line 25: Client 'laptop' vlan_ipv4_addr '10.0.1.5' outside network subnet '10.0.0.0/24'
  - Line 30: Client 'phone': Both gen_global=false and gen_local=false (at least one must be true)
  - Line 35: Invalid DNS nameserver '8.8.8.256' (not a valid IPv4 address)

Total errors: 6
```

---

### File Errors (Exit Code 1)

**stderr**:
```
❌ Error: Configuration file not found: /path/to/config.toml
```

or

```
❌ Error: Configuration file is not readable: Permission denied
```

or (when `--keys` provided):

```
❌ Error: Key storage file not found: /path/to/keys.json
```

---

### Key Storage Validation Errors (Exit Code 1)

**stderr** (when `--keys` provided):
```
❌ Key storage validation failed: keys.json

Errors:
  - Server 'vpn-server': Missing keys (expected: private_key, public_key, preshared_key)
  - Client 'laptop': Missing private_key
  - Client 'phone': Not found in key storage (expected clients.phone)
  - Client 'tablet': Invalid public_key format (expected 44-char base64, got 32)

Total errors: 4

Fix: Regenerate keys using --refresh-force or add missing keys manually
```

---

## Examples

### Basic Validation (Config Only)
```bash
wg-mesh-gen validate -c network.toml
```

**Expected**:
- Validates TOML syntax, schema, and business logic
- Reports summary with ✅ or ❌ status
- Does NOT check key storage

---

### Full Validation (Config + Keys)
```bash
wg-mesh-gen validate -c network.toml -k keys.json
```

**Expected**:
- Validates TOML configuration
- Validates key storage file exists
- Validates all nodes in config have corresponding keys
- Validates key format (base64, correct length)

---

### Strict Mode
```bash
wg-mesh-gen validate -c network.toml --strict
```

**Expected**:
- Treats warnings as errors
- Exit code 1 if any warnings present

---

## Validation Layers

### Layer 1: TOML Syntax
- Valid TOML 1.0 syntax
- Parseable by `tomllib`

### Layer 2: JSON Schema Validation
- Required fields present
- Correct data types
- Value constraints (min/max, patterns, enums)
- Format checkers (IPv4, CIDR)

### Layer 3: Business Logic Validation
- Unique constraints (node names, IPs)
- Cross-field validation (IP within subnet)
- Topology-specific rules (star: 1 server + N clients)
- DNS configuration validity

### Layer 4: Key Storage Validation (if `--keys` provided)
- Key file exists and is valid JSON
- Server has complete keyset (private_key, public_key, preshared_key)
- All clients in config have keys in storage
- All keys are valid base64 format (44 characters)
- No extra keys for non-existent nodes (warning)

---

## Validation Rules Checklist

### Common Section
- ✅ `network_name` is non-empty string
- ✅ `network_ipv4_addr` is valid IPv4 CIDR notation

### Server Section
- ✅ `name` is non-empty string
- ✅ `ipv4_addr` is valid IPv4 address or hostname
- ✅ `vlan_ipv4_addr` is valid IPv4 within `common.network_ipv4_addr`
- ✅ `port` value in range [1024, 65535]
- ✅ `interface` is non-empty string

### Clients Array
- ✅ At least 1 client present
- ✅ All clients have unique `name` values
- ✅ All clients have unique `vlan_ipv4_addr` values
- ✅ All client `vlan_ipv4_addr` are within `common.network_ipv4_addr`
- ✅ All `port` values in range [1024, 65535]
- ✅ Each client: `gen_global=true` OR `gen_local=true` (at least one)

### DNS (per client, optional)
- ✅ `dns1` (if present) is valid IPv4 address
- ✅ `dns2` (if present) is valid IPv4 address

### Key Storage (if `--keys` provided)
- ✅ Key file exists and is readable
- ✅ Key file is valid JSON
- ✅ Server has all required keys (private_key, public_key, preshared_key)
- ✅ Each client in config has keys in storage
- ✅ All keys are valid base64 (44 characters, 32 bytes)
- ⚠️ Warning if extra keys found (nodes in keys.json not in config.toml)

---

## Error Message Format

All validation errors MUST include:
1. **Location**: File path and line number (when available)
2. **Description**: Clear explanation of the problem
3. **Expected**: What the validator expected
4. **Actual**: What was found
5. **Suggestion**: How to fix (when possible)

**Template**:
```
❌ {description}

Location: {file}:{line}
Expected: {expected_value_or_format}
Actual: {actual_value}

Fix: {suggested_action}
```

---

## Performance Expectations

- **Small configs (< 10 nodes)**: < 50ms
- **Medium configs (10-100 nodes)**: < 200ms
- **Large configs (100-1000 nodes)**: < 1 second

---

## Contract Test Requirements

Tests MUST verify:
1. ✅ Valid TOML passes all validation layers
2. ✅ TOML syntax errors return exit code 1 with line number
3. ✅ Schema validation errors list all violations
4. ✅ Business logic errors include line numbers
5. ✅ Duplicate client names detected
6. ✅ Duplicate IPs detected
7. ✅ IP outside subnet detected
8. ✅ Invalid port ranges detected
9. ✅ Invalid DNS nameservers detected
10. ✅ Warnings don't fail in normal mode
11. ✅ Warnings fail in strict mode (--strict)
12. ✅ Missing config file returns descriptive error
13. ✅ `-k` option validates key storage file
14. ✅ Missing keys for nodes detected
15. ✅ Invalid key format detected (not 44-char base64)
16. ✅ Extra keys in storage show warning
17. ✅ Missing key file returns descriptive error

---

## Use Cases

### Pre-Generation Check (Config Only)
```bash
wg-mesh-gen validate -c network.toml && wg-mesh-gen generate -c network.toml -k keys.json
```

**Purpose**: Validate TOML before generating (keys created during generate)

### Pre-Generation Check (Config + Keys)
```bash
wg-mesh-gen validate -c network.toml -k keys.json && wg-mesh-gen generate -c network.toml -k keys.json
```

**Purpose**: Validate both TOML and existing keys before regenerating configs

### CI/CD Integration
```bash
wg-mesh-gen validate -c network.toml --strict
```

**Purpose**: Enforce zero warnings in automated pipelines

### Syntax Debugging
```bash
wg-mesh-gen validate -c network.toml
```

**Purpose**: Quickly identify TOML syntax or schema issues

---

**Contract Status**: ✅ Complete
