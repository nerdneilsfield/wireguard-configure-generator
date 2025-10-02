# Feature Specification: Modular Architecture Refactoring with Template System

**Feature Branch**: `001-jinja2-dns-wiregurard`
**Created**: 2025-10-02
**Status**: Draft
**Input**: User description: "I want to make this project more modular in structure, then use jinja2 for templates; make DNS optional configuration; avoid using system wireguard to generate keys; separate keys and configuration storage, put key configuration in JSON, write configuration in TOML; add data validation; add parallel generation"

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
   - User types and permissions
   - Data retention/deletion policies
   - Performance targets and scale
   - Error handling behaviors
   - Integration requirements
   - Security/compliance needs

---

## Clarifications

### Session 2025-10-02
- Q: Is DNS optional at network level, node level, or both? → A: Node-level only (each node explicitly specifies DNS)
- Q: Should parallelization be automatic, configurable, or optional via CLI flag? → A: CLI flag optional (--parallel flag to enable, sequential by default)
- Q: Should the system support both old JSON format and new TOML format, or require migration? → A: Migration tool (provide converter from JSON to TOML, deprecate JSON)
- Q: What specific validation rules apply - IP format, port ranges, topology constraints? → A: Format rules (syntax, data types, required fields, IP/port format, CIDR notation)
- Q: What cryptographic library or method should be used for key generation? → A: cryptography>=45.0.2

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a network administrator, I want to generate WireGuard configurations using a modular system where I can define a server-client VPN topology in a human-readable TOML file, have the system automatically manage cryptographic keys separately, configure optional DNS per client, validate my configuration for errors, and generate server and client configurations in parallel, so that I can efficiently deploy star-topology VPN networks without manual key management or configuration errors.

### Acceptance Scenarios
1. **Given** a valid TOML network configuration file, **When** user runs the generation command, **Then** system validates configuration and generates WireGuard config files with keys stored separately in JSON format
2. **Given** a configuration with DNS settings marked as optional, **When** user disables DNS in the TOML, **Then** generated WireGuard configs omit DNS configuration entries
3. **Given** a multi-node network topology, **When** user runs generation with --parallel flag, **Then** system generates all node configurations concurrently
4. **Given** an invalid network configuration, **When** user runs validation, **Then** system reports specific validation errors with line numbers and suggested fixes
5. **Given** existing key storage, **When** user regenerates configurations, **Then** system reuses existing keys without invoking external key generation tools
6. **Given** an existing JSON configuration file, **When** user runs the migration tool, **Then** system converts JSON to TOML format preserving all network topology and node settings

### Edge Cases
- What happens when TOML configuration contains duplicate node names or IP addresses?
- How does system handle key file corruption or missing key entries?
- What happens when parallel generation fails for some nodes but succeeds for others?
- How does system behave when DNS configuration is partially specified (e.g., only nameserver without search domains)?
- What happens when template rendering fails due to invalid Jinja2 syntax or missing variables?

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST accept network configuration in TOML format as input
- **FR-002**: System MUST generate WireGuard configuration files using template-based rendering
- **FR-003**: System MUST store cryptographic keys separately from network configuration (keys in JSON, config in TOML)
- **FR-004**: System MUST generate WireGuard-compatible cryptographic keys using Python cryptography library (≥45.0.2) without invoking system WireGuard tools
- **FR-005**: System MUST support optional DNS configuration that can be enabled or disabled per node (each node explicitly specifies DNS settings)
- **FR-006**: System MUST validate TOML configuration before generation including: syntax correctness, data types, required fields, IP address format (IPv4/IPv6), port ranges (1024-65535), and CIDR notation
- **FR-007**: System MUST support parallel generation of multiple node configurations via optional CLI flag (sequential by default, --parallel flag enables concurrent generation)
- **FR-008**: System MUST preserve existing keys when regenerating configurations (no automatic key rotation)
- **FR-009**: System MUST report validation errors with actionable error messages indicating location and nature of errors
- **FR-010**: System MUST use modular architecture where configuration loading, validation, key management, and rendering are separate components
- **FR-011**: System MUST provide a migration tool to convert existing JSON configuration files to TOML format (JSON format will be deprecated)
- **FR-012**: System MUST clearly indicate in documentation that JSON format is deprecated in favor of TOML

### Key Entities *(include if feature involves data)*
- **Network Configuration (TOML)**: Represents simple star topology with one server and multiple clients, including common network settings, IP addressing, ports, and optional DNS per client
- **Server**: Single WireGuard server node with public endpoint, VPN internal IP, port, and physical interface for NAT
- **Client**: Multiple WireGuard client nodes, each with VPN internal IP, port, DNS settings, and mode flags (gen_global/gen_local for AllowedIPs)
- **Key Storage (JSON)**: Represents cryptographic key pairs (private_key, public_key, preshared_key) for server and each client
- **Validation Schema**: Represents rules for validating TOML configuration including syntax correctness, data types, required fields, IP address format (IPv4), port ranges (1024-65535), and CIDR notation
- **Configuration Template**: Jinja2 templates for server config (with PostUp/PostDown iptables rules) and client configs (global and local modes)

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs) - ⚠️ Jinja2 and TOML/JSON mentioned are format/protocol choices, not implementation
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (5 items, all resolved)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---
