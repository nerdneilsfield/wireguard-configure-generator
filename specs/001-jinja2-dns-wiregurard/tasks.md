# Tasks: Modular Architecture Refactoring with Template System

**Feature Branch**: `001-jinja2-dns-wiregurard`
**Input**: Design documents from `/home/dengqi/Source/langs/python/wireguard-configure-generator-older/specs/001-jinja2-dns-wiregurard/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/, quickstart.md

---

## Quick Reference Guide for Implementers

### Key Design Documents (Read BEFORE implementing)

1. **research.md** - Contains EXACT implementation code for:
   - Lines 21-52: Key generation functions (copy directly)
   - Lines 76-88: TOML loading/writing pattern
   - Lines 108-145: Jinja2 templates (copy directly)
   - Lines 165-231: JSON Schema validation setup
   - Lines 252-274: Parallel generation with ThreadPoolExecutor

2. **data-model.md** - Contains data structure definitions:
   - Lines 38-139: CommonConfig, ServerConfig, ClientConfig fields
   - Lines 202-244: RenderedServerConfig, RenderedClientConfig
   - Lines 250-300: Complete NETWORK_CONFIG_SCHEMA (copy directly)
   - Lines 303-311: Business logic validation rules

3. **contracts/** - Contains CLI command specifications:
   - cli-generate.md: Lines 18-25 (options), 48-66 (output format)
   - cli-validate.md: Lines 18-22 (options), 38-57 (output format)
   - cli-migrate.md: Lines 18-24 (options), 75-89 (output format)

4. **wg_conf_gen.py** (original code) - Reference for:
   - Lines 110-112: Server config file naming
   - Lines 121-136: Server config format
   - Lines 143-183: Client config format and gen_global/gen_local logic

### Critical Implementation Notes

⚠️ **Simple Star Topology**: This refactor preserves the original 1 server + N clients topology. Do NOT implement mesh/hub-spoke features.

⚠️ **Field Name Change**: Legacy JSON uses `ipv4_addr` for server endpoint. New TOML uses `endpoint` (supports IPv4/IPv6/hostname). Migration tool must handle both.

⚠️ **Key Security**: All key files and .conf files MUST have 0600 permissions. Call `os.chmod(path, 0o600)` after writing.

⚠️ **TDD Mandatory**: ALL tests (T006-T019) must be written and failing before ANY implementation (T020-T030).

---

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions
- Follow TDD: Write tests → Get approval → Run tests (fail) → Implement → Tests pass

---

## Phase 3.1: Project Setup

- [ ] **T001** Create src/wg_mesh_gen/ module structure with __init__.py
- [ ] **T002** Update pyproject.toml with dependencies (cryptography>=45.0.2, jinja2>=3.1.6, tomli-w>=1.0, jsonschema>=4.0)
- [ ] **T003** [P] Configure Ruff linting in pyproject.toml (line-length=88, target-version="py312", select E/W/F/I/B/UP/D)
- [ ] **T004** [P] Create src/wg_mesh_gen/templates/ directory with server.conf.j2 and client.conf.j2 Jinja2 templates
- [ ] **T005** [P] Create examples/ directory with star-network.toml, legacy-config.json, and keys.json example files

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (CLI Commands)

- [ ] **T006** [P] Contract test for `wg-mesh-gen generate` command in tests/contract/test_cli_generate.py
  - Test valid TOML input generates server + client configs
  - Test validation errors return exit code 1
  - Test --parallel flag works
  - Test --force flag overwrites existing config files
  - Test -k/--keys flag specifies custom key storage path
  - Test key reuse on regeneration (existing keys preserved)
  - Test --refresh-force regenerates all keys (ignores existing keys.json)
  - Test missing keys.json is created automatically

- [ ] **T007** [P] Contract test for `wg-mesh-gen validate` command in tests/contract/test_cli_validate.py
  - Test valid TOML returns exit code 0
  - Test syntax errors return exit code 1
  - Test schema validation errors
  - Test business logic validation (unique names/IPs, gen_global/gen_local)
  - Test -k/--keys flag validates key storage
  - Test missing keys for nodes detected
  - Test invalid key format detected (not 44-char base64)
  - Test extra keys in storage show warning
  - Test --strict flag treats warnings as errors

- [ ] **T008** [P] Contract test for `wg-mesh-gen migrate` command in tests/contract/test_cli_migrate.py
  - Test JSON to TOML conversion
  - Test embedded key extraction to keys.json
  - Test -k/--keys flag specifies custom key storage path
  - Test validation of migrated config
  - Test --force flag overwrites existing TOML and keys.json
  - Test keys.json has 0600 permissions

### Unit Tests (Modules)

- [ ] **T009** [P] Unit tests for loader module in tests/unit/test_loader.py
  - Test load_toml() parses valid TOML
  - Test load_toml() raises error on invalid TOML
  - Test load_toml() handles missing file

- [ ] **T010** [P] Unit tests for validator module in tests/unit/test_validator.py
  - Test TOML schema validation (required fields, types, port ranges)
  - Test business logic validation (unique client names, unique IPs, subnet membership)
  - Test gen_global/gen_local constraint validation
  - Test IPv4/IPv6/hostname endpoint validation

- [ ] **T011** [P] Unit tests for key_manager module in tests/unit/test_key_manager.py
  - Test generate_private_key() returns 44-char base64
  - Test derive_public_key() from private key
  - Test generate_preshared_key() returns 44-char base64
  - Test key compatibility with WireGuard format

- [ ] **T012** [P] Unit tests for renderer module in tests/unit/test_renderer.py
  - Test render_server_config() generates correct WireGuard format
  - Test render_client_config() with gen_global (AllowedIPs=0.0.0.0/0)
  - Test render_client_config() with gen_local (AllowedIPs=subnet)
  - Test DNS field rendering (dns1 only, dns1+dns2, neither)
  - Test PostUp/PostDown iptables rules in server config

- [ ] **T013** [P] Unit tests for migrator module in tests/unit/test_migrator.py
  - Test migrate_json_to_toml() preserves all fields
  - Test extract_keys_from_json() to keys.json structure
  - Test handling of missing embedded keys
  - Test field mapping (endpoint support)

### Integration Tests (End-to-End Workflows)

- [ ] **T014** [P] Integration test: Generate star network configuration in tests/integration/test_star_network_generation.py
  - Test Scenario 1 from quickstart.md
  - Validate all 5 generated config files
  - Verify keys.json structure

- [ ] **T015** [P] Integration test: JSON-to-TOML migration workflow in tests/integration/test_migration_workflow.py
  - Test Scenario 2 from quickstart.md
  - Verify migrated TOML matches expected format
  - Verify keys extracted to separate file

- [ ] **T016** [P] Integration test: Parallel generation performance in tests/integration/test_parallel_generation.py
  - Test Scenario 3 from quickstart.md
  - Measure sequential vs parallel execution time
  - Verify identical output in both modes

- [ ] **T017** [P] Integration test: Key preservation on regeneration in tests/integration/test_key_preservation.py
  - Test Scenario 4 from quickstart.md
  - Verify existing keys unchanged
  - Verify new client gets new key

- [ ] **T018** [P] Integration test: Validation error handling in tests/integration/test_validation_errors.py
  - Test Scenario 5 from quickstart.md
  - Verify error messages include line numbers
  - Verify actionable error descriptions

### Shared Test Fixtures

- [ ] **T019** Create pytest fixtures in tests/conftest.py
  - sample_toml_config fixture (2 clients)
  - sample_json_config fixture (legacy format)
  - sample_keys fixture (server + clients)
  - tmp_output_dir fixture
  - mock_key_generation fixture

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models

- [ ] **T020** [P] Create CommonConfig, ServerConfig, ClientConfig dataclasses in src/wg_mesh_gen/models.py
  - **Reference**: data-model.md lines 38-139 for complete field definitions
  - **Fields to implement**:
    - CommonConfig: network_name (str), network_ipv4_addr (str)
    - ServerConfig: name, endpoint, vlan_ipv4_addr, port, interface
    - ClientConfig: name, vlan_ipv4_addr, port, dns1, dns2, gen_global, gen_local
  - Implement from_dict() class methods for TOML parsing
  - Add __post_init__() validation (raise ValueError on invalid data)
  - Use @dataclass decorator with type hints

- [ ] **T021** [P] Create RenderedServerConfig, RenderedClientConfig dataclasses in src/wg_mesh_gen/models.py
  - **Reference**: data-model.md lines 202-244
  - **RenderedServerConfig**: interface_address, listen_port, private_key, post_up, post_down, peers (list)
  - **RenderedClientConfig**: private_key, address, dns, server_public_key, preshared_key, endpoint, allowed_ips, persistent_keepalive
  - **ServerPeerConfig**: name, public_key, preshared_key, allowed_ips

### Module Implementations

- [ ] **T022** [P] Implement loader module in src/wg_mesh_gen/loader.py
  - **Reference**: research.md lines 76-88 for implementation pattern
  - **Functions**:
    - `load_toml(path: Path) -> dict`: Use `tomllib.load()` with 'rb' mode
    - `write_toml(data: dict, path: Path) -> None`: Use `tomli_w.dump()` with 'wb' mode
  - **Error handling**: FileNotFoundError, tomllib.TOMLDecodeError
  - **Note**: tomllib is stdlib in Python 3.11+, tomli-w for writing

- [ ] **T023** [P] Implement validator module in src/wg_mesh_gen/validator.py
  - **Reference**:
    - data-model.md lines 250-300 for NETWORK_CONFIG_SCHEMA
    - data-model.md lines 303-311 for business logic rules
    - research.md lines 165-231 for format checkers
  - **Schema validation**:
    - Copy NETWORK_CONFIG_SCHEMA from data-model.md
    - Use jsonschema.validate(config, schema, format_checker=checker)
  - **Format checkers**:
    - @FormatChecker.cls_checks("ipv4"): ipaddress.IPv4Address()
    - @FormatChecker.cls_checks("ipv4-cidr"): ipaddress.IPv4Network()
  - **Business logic** (raise ValueError with descriptive message):
    1. Check unique client names (use set comparison)
    2. Check unique client IPs (use set comparison)
    3. Check all IPs within subnet (ipaddress.ip_address in ipaddress.ip_network)
    4. Check each client has gen_global=True OR gen_local=True

- [ ] **T024** [P] Implement key_manager module in src/wg_mesh_gen/key_manager.py
  - **Reference**: research.md lines 21-52 for EXACT implementation
  - **Functions** (copy from research.md):
    - `generate_private_key() -> str`: Use X25519PrivateKey.generate(), serialize to Raw, base64 encode
    - `derive_public_key(private_key_b64: str) -> str`: Decode base64, derive public key, encode
    - `generate_preshared_key() -> str`: os.urandom(32), base64 encode
    - `load_keys_from_json(path: Path) -> dict`: json.load() with error handling
    - `save_keys_to_json(keys: dict, path: Path) -> None`: json.dump() with indent=2
  - **Security**: Call `os.chmod(path, 0o600)` after saving keys.json
  - **Import**: `from cryptography.hazmat.primitives.asymmetric import x25519`

- [ ] **T025** [P] Implement renderer module in src/wg_mesh_gen/renderer.py
  - **Reference**:
    - research.md lines 108-145 for Jinja2 template structure
    - wg_conf_gen.py lines 115-183 for original formatting logic
  - **Functions**:
    - `render_server_config(server: ServerConfig, clients: list[ClientConfig], keys: dict, network_name: str) -> str`
    - `render_client_config(client: ClientConfig, server: ServerConfig, keys: dict, allowed_ips: str) -> str`
  - **Template loading**:
    - `env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))`
    - `template = env.get_template("server.conf.j2" or "client.conf.j2")`
  - **Context preparation**:
    - Server: {server, clients (with public_key/preshared_key), network_name, interface}
    - Client: {client, server, private_key, dns (conditional), allowed_ips, endpoint}
  - **PostUp/PostDown**: See wg_conf_gen.py lines 125-126 for iptables format

- [ ] **T026** [P] Implement migrator module in src/wg_mesh_gen/migrator.py
  - **Reference**: research.md lines 296-342 for migration mapping
  - **Functions**:
    - `migrate_json_to_toml(json_config: dict) -> dict`: Remove embedded keys (prvkey/pubkey/psk)
    - `extract_keys_from_json(json_config: dict) -> dict`: Build {version, server{}, clients{name:{}}} structure
  - **Field handling**:
    - Legacy `ipv4_addr` → modern `endpoint` (for backward compatibility)
    - Direct copy: common.*, server.* (except keys), clients[].* (except keys)
  - **Key extraction**: Check for presence of prvkey/pubkey/psk in server and each client

### CLI Implementation

- [ ] **T027** Implement CLI entry point in src/wg_mesh_gen/cli.py
  - **Reference**: CLAUDE.md (search for Click framework patterns)
  - **Structure**:
    ```python
    import click

    @click.group()
    @click.version_option(version="0.1.0")
    def main():
        """WireGuard mesh network configuration generator."""
        pass

    if __name__ == "__main__":
        main()
    ```
  - **Error handling**: Use try/except, click.echo() for errors to stderr, sys.exit(1) on failure

- [ ] **T028** Implement `generate` command in src/wg_mesh_gen/cli.py
  - **Reference**: contracts/cli-generate.md for complete contract specification
  - **Signature**:
    ```python
    @main.command()
    @click.option("-c", "--config", type=click.Path(exists=True), required=True)
    @click.option("-o", "--output", type=click.Path(), default="./output")
    @click.option("-k", "--keys", type=click.Path(), default="./keys.json")
    @click.option("--parallel", is_flag=True, default=False)
    @click.option("-f", "--force", is_flag=True, default=False)
    @click.option("--refresh-force", is_flag=True, default=False)
    def generate(config, output, keys, parallel, force, refresh_force):
    ```
  - **Implementation flow**:
    1. Load TOML: `config_dict = loader.load_toml(Path(config))`
    2. Validate: `validator.validate_toml_config(config_dict)`
    3. Parse models: `network = NetworkConfig.from_dict(config_dict)`
    4. Load/generate keys:
       - If `--refresh-force`: Generate all new keys (ignore existing keys.json)
       - Else if keys.json exists: Load existing keys, generate only for new nodes
       - Else: Generate all new keys
    5. Save keys: `key_manager.save_keys_to_json(keys, Path(keys))` with 0600 permissions
    6. Render configs: `renderer.render_server_config()`, `renderer.render_client_config()`
    7. Write files: Loop through clients, handle gen_global/gen_local flags
    8. Set permissions: `os.chmod(file, 0o600)` for each .conf file
  - **Parallel mode**: Use `concurrent.futures.ThreadPoolExecutor` (see research.md lines 252-274)
  - **File naming**: See wg_conf_gen.py lines 110-112, 156-173 for exact format
  - **Key management**: Track reused vs generated keys for summary output

- [ ] **T029** Implement `validate` command in src/wg_mesh_gen/cli.py
  - **Reference**: contracts/cli-validate.md for output format
  - **Signature**:
    ```python
    @main.command()
    @click.option("-c", "--config", type=click.Path(exists=True), required=True)
    @click.option("-k", "--keys", type=click.Path(), default=None)
    @click.option("-s", "--strict", is_flag=True, default=False)
    def validate(config, keys, strict):
    ```
  - **Implementation**:
    1. Try to load TOML: Catch tomllib.TOMLDecodeError for syntax errors
    2. Validate schema: Catch jsonschema.ValidationError
    3. Validate business logic: Catch ValueError for custom rules
    4. If --keys provided:
       - Load keys.json: Catch FileNotFoundError, json.JSONDecodeError
       - Validate server has keys (private_key, public_key, preshared_key)
       - Validate each client in config has keys in storage
       - Validate key format (44-char base64)
       - Warn if extra keys found (nodes in keys.json not in config)
    5. Display summary: Use click.echo() for each check with ✅/❌
  - **Output format** (see contracts/cli-validate.md lines 38-76):
    - "✅ TOML syntax: Valid"
    - "✅ Schema validation: Passed"
    - "✅ Business logic validation: Passed"
    - "✅ Key storage validation: Passed" (if --keys provided)
    - Configuration summary with network name, server, client count
    - Key storage checks (if --keys provided)
  - **Exit codes**: 0 for valid, 1 for errors, 0 or 1 for warnings (based on --strict)

- [ ] **T030** Implement `migrate` command in src/wg_mesh_gen/cli.py
  - **Reference**: contracts/cli-migrate.md for complete contract
  - **Signature**:
    ```python
    @main.command()
    @click.option("-i", "--input", type=click.Path(exists=True), required=True)
    @click.option("-o", "--output", type=click.Path(), default="network.toml")
    @click.option("-k", "--keys", type=click.Path(), default="keys.json")
    @click.option("-v", "--validate", is_flag=True, default=True)
    @click.option("-f", "--force", is_flag=True, default=False)
    def migrate(input, output, keys, validate, force):
    ```
  - **Implementation**:
    1. Load JSON: `json.load(open(input))`
    2. Extract keys: `extracted_keys = migrator.extract_keys_from_json(json_config)`
    3. Migrate TOML: `toml_config = migrator.migrate_json_to_toml(json_config)`
    4. Validate (if flag): `validator.validate_toml_config(toml_config)`
    5. Check existing files (if not --force): Error if output or keys file exists
    6. Write TOML: `loader.write_toml(toml_config, output)`
    7. Write keys: `key_manager.save_keys_to_json(extracted_keys, Path(keys))` with 0600 permissions
  - **Output**: See contracts/cli-migrate.md lines 75-89 for exact message format

---

## Phase 3.4: Integration & Polish

### File Naming & Permissions

- [ ] **T031** Implement config file naming logic in src/wg_mesh_gen/renderer.py
  - Server: `wg-{network_name}-server-{server_name}.conf`
  - Client global: `wg-{network_name}-client-{client_name}-global.conf`
  - Client local: `wg-{network_name}-client-{client_name}-local.conf`

- [ ] **T032** Add file permission enforcement (0600) in src/wg_mesh_gen/key_manager.py and cli.py
  - Use os.chmod() for keys.json and *.conf files
  - Verify permissions in integration tests

### Error Handling & Logging

- [ ] **T033** Add comprehensive error messages with line numbers in src/wg_mesh_gen/validator.py
  - Parse TOML line info for error context
  - Format: "Line X: {field}: {error} (first occurrence at line Y)"

- [ ] **T034** Add logging throughout modules
  - Use Python logging module
  - Log levels: DEBUG (template rendering), INFO (file writes), ERROR (validation)
  - Format: `%(levelname)s: %(message)s`

### Template Files

- [ ] **T035** Create server.conf.j2 template in src/wg_mesh_gen/templates/
  - **Reference**: research.md lines 108-125 for exact template
  - **Template content**:
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
  - **Note**: Compare with wg_conf_gen.py lines 121-136 for format validation

- [ ] **T036** Create client.conf.j2 template in src/wg_mesh_gen/templates/
  - **Reference**: research.md lines 128-145 for exact template
  - **Template content**:
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
  - **Variables**:
    - `allowed_ips`: "0.0.0.0/0" for gen_global, or network_ipv4_addr for gen_local
  - **Note**: Compare with wg_conf_gen.py lines 143-183 for format validation

### Documentation

- [ ] **T037** Update README.md with installation and usage examples
  - Installation via uv
  - CLI command examples (generate, validate, migrate)
  - TOML configuration reference
  - Link to quickstart.md

- [ ] **T038** Create docs/claude_log.md and log all changes
  - ISO 8601 timestamps
  - Change descriptions
  - Files modified

---

## Phase 3.5: Validation & Cleanup

### Manual Testing

- [ ] **T039** Run Scenario 1 from quickstart.md (Generate star network)
  - Verify all 5 steps execute successfully
  - Compare generated configs to expected output
  - Test with real WireGuard (wg-quick up/down)

- [ ] **T040** Run Scenario 2 from quickstart.md (JSON-to-TOML migration)
  - Verify migration produces correct TOML
  - Verify keys extracted to separate file
  - Generate configs from migrated TOML

- [ ] **T041** Run Scenario 3 from quickstart.md (Parallel generation)
  - Measure performance with 10+ clients
  - Verify --parallel is faster than sequential
  - Verify identical output

- [ ] **T042** Run Scenario 4 from quickstart.md (Key preservation)
  - Add new client to existing config
  - Verify existing keys unchanged
  - Verify only new client gets new key

- [ ] **T043** Run Scenario 5 from quickstart.md (Error handling)
  - Test all validation error scenarios
  - Verify error messages are actionable

### Code Quality

- [ ] **T044** Run Ruff linting and fix all issues
  - `uv run ruff check --fix .`
  - `uv run ruff format .`
  - Ensure zero linting errors

- [ ] **T045** Run full test suite and verify ≥80% coverage
  - `uv run pytest --cov=wg_mesh_gen --cov-report=term-missing`
  - Check coverage for all modules
  - Add tests for any gaps

- [ ] **T046** Remove legacy wg_conf_gen.py or add deprecation notice
  - Add comment: "DEPRECATED: Use wg-mesh-gen CLI instead"
  - Keep for reference during refactor

---

## Dependencies

### Sequential Blocks (Must Complete in Order)

1. **Setup** (T001-T005) → **Tests** (T006-T019)
2. **Tests** (T006-T019) → **Implementation** (T020-T030)
3. **Core Impl** (T020-T030) → **Integration** (T031-T036)
4. **Implementation** (T020-T036) → **Validation** (T039-T046)

### Specific Dependencies

- T020 (models) blocks T022-T026 (modules need models)
- T022-T026 (modules) block T027-T030 (CLI uses modules)
- T035-T036 (templates) block T025 (renderer needs templates)
- T001-T005 (setup) blocks ALL other tasks

---

## Parallel Execution Examples

### Example 1: Contract Tests (After T001-T005 complete)

```bash
# Launch T006-T008 together (different test files):
Task: "Contract test for wg-mesh-gen generate in tests/contract/test_cli_generate.py"
Task: "Contract test for wg-mesh-gen validate in tests/contract/test_cli_validate.py"
Task: "Contract test for wg-mesh-gen migrate in tests/contract/test_cli_migrate.py"
```

### Example 2: Unit Tests (After T006-T008 complete)

```bash
# Launch T009-T013 together (different test files):
Task: "Unit tests for loader in tests/unit/test_loader.py"
Task: "Unit tests for validator in tests/unit/test_validator.py"
Task: "Unit tests for key_manager in tests/unit/test_key_manager.py"
Task: "Unit tests for renderer in tests/unit/test_renderer.py"
Task: "Unit tests for migrator in tests/unit/test_migrator.py"
```

### Example 3: Integration Tests (After T009-T013 complete)

```bash
# Launch T014-T018 together (different test files):
Task: "Integration test star network in tests/integration/test_star_network_generation.py"
Task: "Integration test migration in tests/integration/test_migration_workflow.py"
Task: "Integration test parallel in tests/integration/test_parallel_generation.py"
Task: "Integration test key preservation in tests/integration/test_key_preservation.py"
Task: "Integration test validation errors in tests/integration/test_validation_errors.py"
```

### Example 4: Module Implementation (After T019-T021 complete)

```bash
# Launch T022-T026 together (different source files):
Task: "Implement loader in src/wg_mesh_gen/loader.py"
Task: "Implement validator in src/wg_mesh_gen/validator.py"
Task: "Implement key_manager in src/wg_mesh_gen/key_manager.py"
Task: "Implement renderer in src/wg_mesh_gen/renderer.py"
Task: "Implement migrator in src/wg_mesh_gen/migrator.py"
```

---

## Task Completion Checklist

### All Contracts Covered?
- ✅ cli-generate.md → T006, T028
- ✅ cli-validate.md → T007, T029
- ✅ cli-migrate.md → T008, T030

### All Data Models Covered?
- ✅ CommonConfig, ServerConfig, ClientConfig → T020
- ✅ RenderedServerConfig, RenderedClientConfig → T021

### All Quickstart Scenarios Covered?
- ✅ Scenario 1 (Star network) → T014, T039
- ✅ Scenario 2 (Migration) → T015, T040
- ✅ Scenario 3 (Parallel) → T016, T041
- ✅ Scenario 4 (Key preservation) → T017, T042
- ✅ Scenario 5 (Validation) → T018, T043

### TDD Order Enforced?
- ✅ Tests (T006-T019) before implementation (T020-T030)
- ✅ Integration tests (T014-T018) validate implementation

### File Paths Specified?
- ✅ All tasks include exact file paths
- ✅ Template paths: src/wg_mesh_gen/templates/*.j2
- ✅ Test paths: tests/contract/, tests/unit/, tests/integration/
- ✅ Source paths: src/wg_mesh_gen/*.py

---

## Notes

- **[P] Tasks**: Can run in parallel (different files, no shared dependencies)
- **TDD Mandatory**: Write tests → Get user approval → Run tests (FAIL) → Implement → Tests pass
- **Commit Frequency**: Commit after each task completion
- **Coverage Target**: ≥80% for all modules
- **Constitutional Compliance**: All tasks follow constitution v1.2.0 principles

---

**Total Tasks**: 46
**Parallel Opportunities**: 28 tasks marked [P]
**Estimated Critical Path**: Setup (5) → Contract Tests (3) → Unit Tests (5) → Models (2) → Modules (5) → CLI (3) → Integration (5) → Templates (2) → Validation (5) = ~35 sequential tasks with parallelization

---

**Tasks Status**: ✅ Ready for execution
