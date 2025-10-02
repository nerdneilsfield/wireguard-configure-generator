
# Implementation Plan: Modular Architecture Refactoring with Template System

**Branch**: `001-jinja2-dns-wiregurard` | **Date**: 2025-10-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/home/dengqi/Source/langs/python/wireguard-configure-generator-older/specs/001-jinja2-dns-wiregurard/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Refactor the WireGuard configuration generator from a monolithic single-file design to a modular architecture with:
- **TOML-based configuration** for human-readable network topology definition
- **Jinja2 template system** for flexible WireGuard config file generation
- **Separate JSON key storage** for cryptographic keys (private/public/preshared)
- **Python cryptography library** for key generation (no system `wg` command dependency)
- **Node-level optional DNS** configuration
- **Multi-layer validation** (syntax, types, formats: IP/port/CIDR)
- **Parallel generation** support via CLI flag
- **JSON-to-TOML migration tool** for backward compatibility

## Technical Context
**Language/Version**: Python 3.12+ (per constitution)
**Primary Dependencies**:
- cryptography>=45.0.2 (WireGuard key generation)
- jinja2>=3.1.6 (template rendering)
- toml>=0.10.2 (TOML parsing)
- jsonschema>=4.0 (validation)

**Storage**: File-based (TOML for config, JSON for keys)
**Testing**: pytest with ≥80% coverage (per constitution)
**Target Platform**: Cross-platform (Linux, macOS, Windows)
**Project Type**: Single (CLI tool)
**Performance Goals**: Support parallel generation for multi-node networks (configurable via --parallel flag)
**Constraints**:
- No system WireGuard tools dependency for key generation
- Port range validation: 1024-65535
- IPv4/IPv6 support with CIDR notation validation

**Scale/Scope**: Network topologies with multiple nodes (mesh/hub-spoke/relay), migration from legacy JSON format

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Core Principles Alignment
- ✅ **I. Modular Architecture**: Refactoring explicitly creates separate modules (loader, validator, key_manager, renderer, migrator)
- ✅ **II. CLI-First Design**: All features accessible via CLI with TOML/JSON input support
- ✅ **III. Test-First Development**: TDD workflow enforced (tests → approval → fail → implement)
- ✅ **IV. Comprehensive Validation**: Multi-layer validation (syntax, types, IP/port/CIDR formats)
- ✅ **V. Configuration Format Flexibility**: TOML primary + JSON legacy support via migration tool
- ✅ **VI. Secure Key Management**: Using cryptography library instead of system tools, JSON storage with proper permissions
- ✅ **VII. Network Topology Intelligence**: Preserves existing topology support (mesh/hub-spoke/relay)
- ✅ **VIII. Observability and Documentation**: Maintains logging requirements, updates CLAUDE.md
- ✅ **IX. Modern Python Standards**: Python 3.12+, type hints, PEP 8
- ✅ **X. uv-First Package Management**: All dependencies managed via uv
- ✅ **XI. Ruff-First Linting**: Pre-commit checks with ruff
- ✅ **XII. Comprehensive Testing**: pytest with ≥80% coverage

### Quality Gates
- ✅ No NEEDS CLARIFICATION markers in spec (all resolved via /clarify)
- ✅ TDD workflow: Tests before implementation
- ✅ Schema validation for TOML configs
- ✅ Code must run successfully before commit

**Initial Check Result**: PASS - No constitutional violations detected

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/wg_mesh_gen/
├── __init__.py
├── cli.py              # Click-based CLI interface (entrypoint)
├── loader.py           # TOML/JSON configuration loader
├── validator.py        # Multi-layer validation (schema + business logic)
├── key_manager.py      # Cryptography library key generation
├── renderer.py         # Jinja2 template rendering
├── migrator.py         # JSON-to-TOML migration tool
├── builder.py          # Existing topology builder (preserved)
├── visualizer.py       # Existing visualizer (preserved)
└── templates/
    └── wireguard.conf.j2  # WireGuard configuration template

tests/
├── conftest.py         # Shared pytest fixtures
├── contract/           # Contract tests for CLI commands
│   ├── test_cli_generate.py
│   ├── test_cli_migrate.py
│   └── test_cli_validate.py
├── integration/        # Integration tests for workflows
│   ├── test_end_to_end_generation.py
│   ├── test_parallel_generation.py
│   └── test_migration_workflow.py
└── unit/               # Unit tests per module
    ├── test_loader.py
    ├── test_validator.py
    ├── test_key_manager.py
    ├── test_renderer.py
    └── test_migrator.py

examples/
├── network.toml        # Example TOML config
├── legacy-config.json  # Example JSON config (for migration)
└── keys.json           # Example key storage format
```

**Structure Decision**: Single project structure (CLI tool). Legacy `wg_conf_gen.py` will be deprecated but kept for reference. New modular code goes in `src/wg_mesh_gen/` following constitution's modular architecture principle.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
1. **Load `.specify/templates/tasks-template.md` as base**
2. **Generate tasks from Phase 1 design docs**:
   - From `contracts/cli-generate.md` → contract test tasks for `generate` command
   - From `contracts/cli-migrate.md` → contract test tasks for `migrate` command
   - From `contracts/cli-validate.md` → contract test tasks for `validate` command
   - From `data-model.md` → dataclass/model creation tasks
   - From `quickstart.md` → integration test scenarios

3. **Task Categories** (TDD order):
   - **Setup Tasks**: Project structure, dependencies, templates
   - **Contract Test Tasks**: CLI command interface tests (fail first) [P]
   - **Unit Test Tasks**: Module-specific tests (fail first) [P]
   - **Implementation Tasks**: Make tests pass
   - **Integration Test Tasks**: End-to-end workflows
   - **Documentation Tasks**: Update CLAUDE.md, README.md

4. **Module-Specific Breakdown**:
   - `loader.py`: TOML/JSON parsing → test_loader.py → implementation [P]
   - `validator.py`: Schema + business logic validation → test_validator.py → implementation [P]
   - `key_manager.py`: Curve25519 key generation → test_key_manager.py → implementation [P]
   - `renderer.py`: Jinja2 template rendering → test_renderer.py → implementation [P]
   - `migrator.py`: JSON-to-TOML conversion → test_migrator.py → implementation [P]
   - `cli.py`: Click CLI commands → test_cli_*.py → implementation

**Ordering Strategy**:
1. **Foundation First**: Setup, dependencies, template files
2. **TDD Order**: Contract tests → Unit tests → Implementation
3. **Dependency Order**:
   - loader.py (no deps) → validator.py (uses loader) → key_manager.py (no deps) → renderer.py (uses loader, key_manager) → cli.py (uses all)
4. **Parallel Opportunities** [P]:
   - loader, validator, key_manager, renderer, migrator can be developed in parallel
   - Contract tests can be written in parallel
   - Unit tests can be written in parallel

**Estimated Task Breakdown**:
- Setup tasks: 3-5 (project structure, pyproject.toml, dependencies)
- Contract test tasks: 9-12 (3 CLI commands × 3-4 test cases each)
- Unit test tasks: 15-20 (5 modules × 3-4 test cases each)
- Implementation tasks: 15-20 (5 modules × 3-4 functions/classes each)
- Integration test tasks: 6-8 (quickstart scenarios)
- Documentation tasks: 2-3 (CLAUDE.md, README.md, examples)

**Total Estimated Tasks**: 50-68 tasks

**Critical Path**:
1. Setup dependencies → 2. Write contract tests (fail) → 3. Write unit tests (fail) → 4. Implement loader → 5. Implement validator → 6. Implement key_manager → 7. Implement renderer → 8. Implement CLI → 9. Integration tests → 10. Documentation

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) - ✅ research.md generated
- [x] Phase 1: Design complete (/plan command) - ✅ data-model.md, contracts/, quickstart.md, CLAUDE.md updated
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none)

---
*Based on Constitution v1.2.0 - See `.specify/memory/constitution.md`*
