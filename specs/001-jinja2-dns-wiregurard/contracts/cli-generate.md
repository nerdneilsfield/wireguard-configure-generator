# CLI Contract: generate

**Command**: `wg-mesh-gen generate`

**Purpose**: Generate WireGuard configuration files from TOML network definition (simple star topology: 1 server + N clients)

---

## Signature

```bash
wg-mesh-gen generate [OPTIONS]
```

---

## Options

| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--config` | `-c` | Path | Yes | - | Path to TOML configuration file (star topology) |
| `--output` | `-o` | Path | No | `./output` | Output directory for generated configs |
| `--keys` | `-k` | Path | No | `./keys.json` | Path to JSON key storage file |
| `--parallel` | - | Flag | No | False | Enable parallel generation for client configs |
| `--force` | `-f` | Flag | No | False | Overwrite existing config files |

---

## Input Contract

### Configuration File (TOML)
- **Format**: Valid TOML syntax with [common], [server], [[clients]] sections
- **Schema**: Must conform to star topology schema (see data-model.md)
- **Location**: File must exist and be readable
- **Topology**: Simple star (1 server + N clients)

### Key Storage File (JSON)
- **Format**: Valid JSON syntax (if exists)
- **Schema**: Must have `server{}` and `clients{name:{}}` structure (see data-model.md)
- **Behavior**:
  - If missing: Generated automatically with new keys for server and all clients
  - If exists: Keys reused for matching server/client names

---

## Output Contract

### Success (Exit Code 0)

**stdout**:
```
✅ Validated configuration: 1 server + 2 clients
✅ Loaded keys for server and 1 client, generated 1 new key
✅ Generated server config → output/wg-my-vpn-server-vpn-server.conf
✅ Generated client config → output/wg-my-vpn-client-laptop-global.conf
✅ Generated client config → output/wg-my-vpn-client-laptop-local.conf (if gen_local=true)
✅ Generated client config → output/wg-my-vpn-client-phone-global.conf (if gen_global=true)
✅ Generated client config → output/wg-my-vpn-client-phone-local.conf

Summary:
  Server configs: 1
  Client configs: 4 (2 global, 2 local)
  Keys reused: 2 (server + laptop)
  Keys generated: 1 (phone)
  Output directory: /path/to/output
```

**Generated Files**:
```
output/
├── wg-my-vpn-server-vpn-server.conf      # Server config
├── wg-my-vpn-client-laptop-global.conf   # Client global mode (AllowedIPs=0.0.0.0/0)
├── wg-my-vpn-client-laptop-local.conf    # Client local mode (AllowedIPs=network_subnet)
├── wg-my-vpn-client-phone-global.conf    # (if gen_global=true)
└── wg-my-vpn-client-phone-local.conf     # (if gen_local=true)

keys.json             # Updated key storage (server{} + clients{name:{}})
```

**File Permissions**:
- `*.conf`: `0600` (owner read/write only)
- `keys.json`: `0600` (owner read/write only)

---

### Validation Errors (Exit Code 1)

**stderr**:
```
❌ Validation failed: /path/to/config.toml

Errors:
  - Line 10: Duplicate client name 'laptop' (first occurrence at line 5)
  - Line 15: Invalid port 70000 (must be 1024-65535)
  - Line 20: vlan_ipv4_addr 10.0.1.5 outside network subnet 10.0.0.0/24
  - Line 25: Client 'phone': At least one of gen_global or gen_local must be true
```

**Behavior**: No files generated, exit immediately

---

### File Errors (Exit Code 1)

**stderr**:
```
❌ Error: Configuration file not found: /path/to/config.toml
```

or

```
❌ Error: Output directory /path/to/output is not writable
```

---

### Generation Errors (Exit Code 1)

**stderr** (sequential mode):
```
❌ Error generating configuration for client 'laptop':
  Template rendering failed: Missing server endpoint
```

**stderr** (parallel mode):
```
❌ Errors occurred during parallel generation:

Client 'laptop': Template rendering failed: Missing server endpoint
Client 'phone': File write failed: Permission denied

Successfully generated: 3/5 configs (1 server + 2 client configs)
Failed: 2/5 configs
```

**Behavior**: Partial generation possible in parallel mode; atomic rollback in sequential mode

---

## Examples

### Basic Usage
```bash
wg-mesh-gen generate -c star-network.toml -o /etc/wireguard
```

**Expected**:
- Reads `star-network.toml` ([common], [server], [[clients]])
- Generates 1 server config + N client configs in `/etc/wireguard/`
- Creates/updates `keys.json` in current directory with server{} and clients{name:{}}

---

### Parallel Generation
```bash
wg-mesh-gen generate -c star-network.toml --parallel
```

**Expected**:
- Concurrent config generation for server + all client configs
- Faster execution for networks with many clients

---

### Custom Key Storage
```bash
wg-mesh-gen generate -c star-network.toml -k /secure/keys.json
```

**Expected**:
- Uses `/secure/keys.json` for key storage
- Preserves existing server/client keys for regeneration

---

### Force Overwrite
```bash
wg-mesh-gen generate -c star-network.toml -o /etc/wireguard --force
```

**Expected**:
- Overwrites existing `.conf` files without prompting
- Without `--force`: Fails if output files exist

---

## Validation Rules

### Pre-Generation Validation
1. TOML syntax correctness ([common], [server], [[clients]] sections)
2. JSON schema validation (structure, types, required fields)
3. Business logic validation:
   - Unique client names
   - Unique client vlan_ipv4_addr values
   - All IPs within network_ipv4_addr subnet
   - Port ranges (1024-65535)
   - At least one of gen_global/gen_local true per client
4. Star topology constraints (1 server, ≥1 client)

### Runtime Validation
1. Output directory exists and is writable
2. Key file (if exists) has correct permissions (0600)
3. Template files (server.conf.j2, client.conf.j2) exist and are readable

---

## Error Handling

### Graceful Degradation
- **Parallel mode**: Continue generating other nodes if one fails
- **Sequential mode**: Stop at first failure, rollback if atomic flag set

### User Guidance
All error messages MUST include:
1. Clear description of the problem
2. Location (file, line number if applicable)
3. Suggested fix (when possible)

**Example**:
```
❌ Validation failed: config.toml:15

Error: Invalid port 70000 (must be 1024-65535)
Fix: Change port to a value between 1024 and 65535

Suggested: port = 51820
```

---

## Performance Expectations

### Sequential Mode
- **1 server + 10 clients** (21 configs): < 2 seconds
- **1 server + 100 clients** (201 configs): < 10 seconds

### Parallel Mode
- **1 server + 10 clients** (21 configs): < 1 second
- **1 server + 100 clients** (201 configs): < 5 seconds

**Constraint**: Execution time MUST scale linearly with client count in sequential mode, sub-linearly in parallel mode.

---

## Contract Test Requirements

Tests MUST verify:
1. ✅ Valid TOML input (star topology) generates correct server + client config files
2. ✅ Invalid TOML syntax returns exit code 1 with error message
3. ✅ Validation errors include line numbers and specific violations
4. ✅ Missing config file returns descriptive error
5. ✅ Existing server/client keys are reused (key file unchanged for same names)
6. ✅ New clients generate new keys (key file updated with new client entries)
7. ✅ Parallel mode generates same configs as sequential (order-independent)
8. ✅ File permissions are 0600 for all generated files
9. ✅ --force flag overwrites existing files
10. ✅ Without --force, existing files cause error
11. ✅ Server config includes PostUp/PostDown iptables rules
12. ✅ Client global config has AllowedIPs=0.0.0.0/0
13. ✅ Client local config has AllowedIPs=network_ipv4_addr
14. ✅ File naming follows pattern: wg-{network_name}-server-{server.name}.conf and wg-{network_name}-client-{client.name}-{global|local}.conf

---

**Contract Status**: ✅ Complete (updated for star topology)
