<!--
Sync Impact Report:
- Version change: 1.1.0 → 1.2.0 (MINOR: Added Ruff and pytest best practices)
- Modified principles:
  - Added XI: Ruff-First Linting and Formatting (new)
  - Added XII: Comprehensive Testing with pytest (new)
  - Expanded Code Quality Standards with Ruff configuration
  - Enhanced Testing Requirements with pytest patterns
- Added sections: Ruff Configuration, pytest Best Practices
- Removed sections: N/A
- Templates requiring updates:
  ✅ .specify/templates/plan-template.md (reviewed, compatible)
  ✅ .specify/templates/spec-template.md (reviewed, compatible)
  ✅ .specify/templates/tasks-template.md (reviewed, compatible)
- Follow-up TODOs: Update CLAUDE.md with Ruff and pytest guidance
-->

# WireGuard Configuration Generator Constitution

## Core Principles

### I. Modular Architecture
Every feature must be implemented as a self-contained module with clear responsibilities. Modules must be independently testable with well-defined interfaces. Cross-module dependencies must be minimized and explicitly documented. No organizational-only modules without clear functional purpose.

**Rationale**: The codebase follows a modular design (cli, builder, validator, loader, render, visualizer, etc.) where each module has a specific responsibility. This enables independent testing, easier maintenance, and parallel development.

### II. CLI-First Design
Every feature MUST expose functionality via the CLI interface. Commands follow text in/out protocol: configuration files/args → stdout, errors → stderr. All operations MUST support both YAML and JSON formats for input and human-readable output.

**Rationale**: As specified in CLAUDE.md, the CLI (built with Click) is the entry point for all functionality. This ensures consistency, scriptability, and accessibility for users and automation.

### III. Test-First Development (NON-NEGOTIABLE)
TDD is mandatory: Tests written → User approved → Tests fail → Implementation begins. Red-Green-Refactor cycle strictly enforced. Code MUST be runnable before every commit (as per CLAUDE.md operational notes). No implementation without failing tests first.

**Rationale**: The project has comprehensive test coverage (186 passing tests) and explicit TDD requirements. This ensures quality, prevents regressions, and validates requirements before implementation.

### IV. Comprehensive Validation
Configuration validation MUST use multi-layer approach: JSON Schema validation for structure, business logic validation for domain rules. All user inputs MUST be validated before processing. Validation errors MUST provide actionable feedback.

**Rationale**: The unified validation pipeline (validator.py) combines schema and business logic checks, ensuring configurations are both structurally valid and semantically correct for WireGuard networks.

### V. Configuration Format Flexibility
Support both YAML and JSON for all configuration inputs. Schema validation MUST be format-agnostic. Template rendering MUST support extensibility via Jinja2. Group-based topology definitions MUST simplify complex network configurations.

**Rationale**: The loader.py supports both formats with schema validation, and the template system provides flexibility for diverse deployment scenarios (mesh, star, layered routing, etc.).

### VI. Secure Key Management
Cryptographic operations MUST use industry-standard libraries. Private keys MUST use secure storage with file locking for concurrent access. Key generation MUST be automated and transparent. Manual key handling MUST be supported for advanced use cases.

**Rationale**: Security is critical for VPN configurations. The simple_storage.py provides JSON-based storage with file locking, balancing simplicity with concurrent access safety.

### VII. Network Topology Intelligence
The builder MUST support complex topologies: mesh, hub-and-spoke, multi-relay, and layered routing. Routing optimization MUST prevent AllowedIPs conflicts. Relay nodes MUST automatically configure IP forwarding. Multiple endpoints per node MUST be supported for different peer groups.

**Rationale**: The smart_builder.py handles complex mesh networks with automatic route optimization, which is the core value proposition of this tool over manual WireGuard configuration.

### VIII. Observability and Documentation
Structured logging MUST be used throughout. Configuration changes MUST be logged to docs/claude_log.md with timestamps. Network topology MUST be visualizable (NetworkX-based). Error messages MUST guide users to solutions.

**Rationale**: As per CLAUDE.md commit requirements, all changes are logged. The visualizer.py provides network diagrams essential for understanding complex topologies.

### IX. Modern Python Standards
Code MUST target Python 3.12+ with modern features. Type hints MUST be used for all public APIs (functions, methods, class attributes). Use `from __future__ import annotations` for forward compatibility. Follow PEP 8 style with Google Python Style Guide additions. Prefer implicit false evaluation, comprehensions for readability, and proper string quote consistency.

**Rationale**: Type hints enable static analysis with tools like pytype/myright, catching errors at build time. Modern Python features (match statements, union types with `|`, ParamSpec) improve code clarity and maintainability. Consistent style reduces cognitive load.

### X. uv-First Package Management
ALL dependency operations MUST use uv. Project dependencies defined in `pyproject.toml` under `[project.dependencies]`. Development dependencies in `[dependency-groups]` (not `tool.uv.dev-dependencies`). Use `uv sync` for reproducible installs, `uv add` for new dependencies, `uv lock` to update lockfile. Virtual environments managed automatically by uv. NO manual pip usage except for legacy compatibility.

**Rationale**: uv is 10-100x faster than pip and provides comprehensive project management (replaces pip, pip-tools, poetry, pyenv). Automatic virtual environment management eliminates common setup errors. Lockfile ensures reproducible builds across environments.

### XI. Ruff-First Linting and Formatting
Ruff MUST be the primary tool for both linting and formatting. Use `ruff check` for linting with auto-fix, `ruff format` for code formatting (Black-compatible). Configuration in `pyproject.toml` under `[tool.ruff]`. Enable comprehensive rule sets: pycodestyle (E/W), Pyflakes (F), pyupgrade (UP), isort (I), flake8-bugbear (B), pydocstyle (D). Line length 88 characters. Use double quotes for strings. Run `ruff check --fix` before commit.

**Rationale**: Ruff is 10-100x faster than flake8/black/isort combined, written in Rust. Single tool replaces multiple linters/formatters, reducing setup complexity. Native support for modern Python features and comprehensive rule coverage catches more issues earlier.

### XII. Comprehensive Testing with pytest
pytest MUST be used for all testing. Organize tests in `tests/` directory mirroring `src/` structure. Use fixtures for reusable test setup in `conftest.py`. Parametrize tests with `@pytest.mark.parametrize` for multiple scenarios. Test coverage MUST be ≥80% for new code. Integration tests MUST cover critical user workflows. Use descriptive test names: `test_<action>_<condition>_<expected_result>`.

**Rationale**: pytest's fixture system promotes test modularity and reusability. Parametrization reduces test duplication. Comprehensive testing with pytest-cov ensures code quality and prevents regressions. Clear test organization aids maintenance and debugging.

## Development Workflow

### Project Structure
- All scripts MUST be placed in `scripts/` directory
- No test files in root directory; use `tests/` with proper categorization
- Documentation in `docs/` with consistent formatting
- Examples in `examples/` demonstrating real-world use cases

### Code Quality Standards
- Use modern Python tooling: uv package manager (required), Ruff for linting and formatting
- Code MUST pass `uv run ruff check --fix` before commit
- Format with `uv run ruff format` before commit
- Maintain cross-platform compatibility (Makefile supports multiple platforms)

#### Ruff Configuration
Configure in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
    "D",   # pydocstyle
]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

#### Python-Specific Rules
- **Type Hints**: All public functions MUST have parameter and return type annotations
- **Imports**: One import per line, grouped by: stdlib → third-party → local (Ruff I001 enforces)
- **String Quotes**: Double quotes (enforced by Ruff formatter)
- **Indentation**: 4 spaces (enforced by Ruff formatter)
- **Line Length**: Max 88 characters (enforced by Ruff formatter)
- **Comprehensions**: Allowed for simple cases; explicit loops when complex (Ruff C4xx suggests)
- **Error Messages**: Use f-strings with `{var=}` notation for clarity in exceptions
- **Logging**: Use pattern-string literals (e.g., `logger.info('Value: %s', val)`) not f-strings
- **Docstrings**: Google style with Args/Returns/Raises sections (Ruff D enforces)

### Testing Requirements

#### pytest Best Practices
- **Test Organization**: Mirror `src/` structure in `tests/` directory
  ```
  src/wg_mesh_gen/
    cli.py
    builder.py
  tests/
    test_cli.py
    test_builder.py
    conftest.py  # Shared fixtures
  ```
- **Fixtures**: Define reusable setup in `conftest.py`, use dependency injection
- **Parametrization**: Use `@pytest.mark.parametrize` for multiple test scenarios
- **Test Naming**: `test_<function>_<scenario>_<expected>` (e.g., `test_build_config_invalid_node_raises_error`)
- **Coverage**: Run `uv run pytest --cov=wg_mesh_gen --cov-report=term-missing`
- **Markers**: Use `@pytest.mark.integration` for slow tests, run with `-m integration`

#### Test Categories
- **Unit Tests**: Fast, isolated, test individual functions/methods
- **Integration Tests**: Test module interactions, multi-node scenarios
- **Contract Tests**: Validate CLI command interfaces and outputs
- **Performance Tests**: Validate large network generation (<1000 nodes in <10s)

#### Pre-Commit Checklist
- Run `make test` (or `uv run pytest`) - all tests MUST pass
- Coverage ≥80% for new code
- Integration tests MUST cover critical workflows
- Performance tests MUST validate scalability

### Commit and Documentation
- Record all changes in `docs/claude_log.md` with ISO timestamps
- Use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
- Commit messages in English
- Code can contain Chinese comments (existing convention)

### Package Management

#### uv Workflow Best Practices
- **Project Initialization**: Use `uv init` for new projects, creates proper `pyproject.toml`
- **Dependency Management**:
  - Add dependencies: `uv add <package>` (updates pyproject.toml and uv.lock)
  - Add dev dependencies: `uv add --group dev <package>` (uses dependency-groups)
  - Update lockfile: `uv lock` after manual pyproject.toml edits
  - Sync environment: `uv sync` for reproducible installs from lockfile
- **Running Commands**: Use `uv run <command>` to execute in managed virtual environment
- **Virtual Environments**: uv manages `.venv` automatically, no manual activation needed
- **Constraints**: Use `[tool.uv.sources]` for Git/path/workspace dependencies
- **Docker Optimization**: Separate `COPY pyproject.toml uv.lock` → `RUN uv sync --no-install-project` → `COPY .` → `RUN uv sync --locked` for layer caching
- **Workspaces**: Use `[tool.uv.workspace]` for monorepo management with shared dependencies

#### pyproject.toml Structure
```toml
[project]
name = "wg-mesh-gen"
version = "x.y.z"
requires-python = ">=3.12"
dependencies = [...]  # Production dependencies only

[dependency-groups]
dev = [...]  # Development dependencies (tests, linters, formatters)

[tool.uv.sources]
# Git/path dependencies defined here

[build-system]
requires = ["hatchling"]  # or setuptools, uv_build
build-backend = "hatchling.build"
```

#### Compatibility Notes
- Maintain `pip install -e ".[dev]"` compatibility for users without uv
- Use `uv pip install` when uv is available but project mode not suitable
- Document uv installation in README for new contributors

## Governance

### Amendment Process
1. Constitution changes MUST be documented in this file
2. Version MUST be incremented per semantic versioning:
   - MAJOR: Backward incompatible principle removals/redefinitions
   - MINOR: New principles or materially expanded guidance
   - PATCH: Clarifications, wording refinements
3. Changes MUST update Last Amended date
4. All dependent templates MUST be reviewed for consistency

### Compliance Review
- All PRs/changes MUST verify compliance with core principles
- Complexity deviations MUST be explicitly justified in design documents
- Use CLAUDE.md for runtime development guidance
- Constitution supersedes all other documentation in case of conflicts

### Quality Gates
- Code MUST run successfully before commit (operational requirement)
- All tests MUST pass before merge
- Schema validation MUST pass for all configurations
- Network topology visualization MUST render without errors

**Version**: 1.2.0 | **Ratified**: 2025-10-02 | **Last Amended**: 2025-10-02
