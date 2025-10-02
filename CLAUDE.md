# CLAUDE.md - WireGuard Configuration Generator Development Guide

**Version**: 1.0.0
**Last Updated**: 2025-10-02
**Constitutional Compliance**: v1.2.0

This document provides operational guidance for Claude when working on the WireGuard Configuration Generator project. It complements `.specify/memory/constitution.md` with practical development workflows and project-specific conventions.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Development Environment](#development-environment)
3. [Code Standards](#code-standards)
4. [Testing Workflow](#testing-workflow)
5. [Commit Protocol](#commit-protocol)
6. [CLI Development](#cli-development)
7. [Configuration Management](#configuration-management)
8. [Security Guidelines](#security-guidelines)
9. [Common Tasks](#common-tasks)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

### Mission
Generate WireGuard VPN configurations from simple JSON/YAML files, supporting complex network topologies (mesh, hub-spoke, multi-relay) with automatic key management and route optimization.

### Current Architecture
**⚠️ Legacy Status**: This is the "older" version with a single-file prototype (`wg_conf_gen.py`). The project is being refactored to follow modular architecture principles.

**Current State**:
- Single Python script: `wg_conf_gen.py` (~187 lines)
- JSON-based configuration: `config.example.json`
- No external dependencies (stdlib only)
- Simple server/client topology support

**Target Architecture** (per Constitution):
```
src/wg_mesh_gen/
├── cli.py              # Click-based CLI interface
├── builder.py          # Smart network topology builder
├── validator.py        # JSON Schema + business logic validation
├── loader.py           # YAML/JSON configuration loader
├── render.py           # Jinja2 template rendering
├── visualizer.py       # NetworkX-based topology visualization
├── key_manager.py      # Cryptographic key management
└── storage.py          # File-based key storage with locking

tests/
├── conftest.py         # Shared pytest fixtures
├── test_cli.py
├── test_builder.py
└── ... (mirroring src structure)
```

### Key Principles (from Constitution v1.2.0)
1. **Modular Architecture**: Self-contained modules with clear responsibilities
2. **CLI-First Design**: All features via CLI, text in/out protocol
3. **TDD Non-Negotiable**: Tests → Approval → Fail → Implementation
4. **Modern Python**: 3.12+, type hints, Ruff formatting
5. **uv-First**: No manual pip usage
6. **Comprehensive Testing**: pytest with ≥80% coverage

---

## Development Environment

### Setup Commands

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and enter project
cd /home/dengqi/Source/langs/python/wireguard-configure-generator-older

# 3. Initialize uv environment (creates .venv automatically)
uv sync

# 4. Install development dependencies
uv add --group dev pytest pytest-cov ruff

# 5. Verify WireGuard CLI is available
which wg || echo "ERROR: Install wireguard-tools package"
```

### Project Structure Expectations

```
wireguard-configure-generator-older/
├── .specify/                    # Feature specification workflow
│   ├── memory/
│   │   └── constitution.md      # Project constitution (v1.2.0)
│   └── templates/               # Spec/plan/task templates
├── src/wg_mesh_gen/             # Main source (to be created)
├── tests/                       # pytest test suite (to be created)
├── scripts/                     # Build/automation scripts
├── docs/                        # Documentation
│   └── claude_log.md           # Change log with ISO timestamps
├── examples/                    # Real-world usage examples
├── wg_conf_gen.py              # Legacy single-file implementation
├── config.example.json         # Legacy example config
├── pyproject.toml              # uv project configuration
├── uv.lock                     # Dependency lockfile
├── CLAUDE.md                   # This file
└── README.md                   # User-facing documentation
```

### pyproject.toml Configuration

When creating/updating `pyproject.toml`:

```toml
[project]
name = "wg-mesh-gen"
version = "0.1.0"
description = "WireGuard configuration generator with mesh network support"
requires-python = ">=3.12"
dependencies = [
    "click>=8.1",           # CLI framework
    "pyyaml>=6.0",          # YAML support
    "jsonschema>=4.0",      # Configuration validation
    "jinja2>=3.1",          # Template rendering
    "networkx>=3.0",        # Topology visualization
    "cryptography>=41.0",   # Key management
]

[dependency-groups]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "ruff>=0.1",
]

[project.scripts]
wg-mesh-gen = "wg_mesh_gen.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

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

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "--cov=wg_mesh_gen --cov-report=term-missing --strict-markers"
markers = [
    "integration: Integration tests (slower)",
    "performance: Performance benchmarks",
]
```

---

## Code Standards

### Type Hints (Mandatory)

```python
from __future__ import annotations  # Enable forward references

def generate_config(
    nodes: list[dict[str, Any]],
    topology: str = "mesh",
    *,
    optimize_routes: bool = True,
) -> dict[str, str]:
    """Generate WireGuard configurations for nodes.

    Args:
        nodes: List of node configurations with name, ip, port.
        topology: Network topology type (mesh, hub-spoke, relay).
        optimize_routes: Enable route optimization to prevent conflicts.

    Returns:
        Dictionary mapping node names to configuration strings.

    Raises:
        ValidationError: If node configuration is invalid.
        TopologyError: If topology cannot be built.
    """
    ...
```

### String Formatting Rules

```python
# ✅ Good: f-strings for variable interpolation
config_path = f"/etc/wireguard/{interface}.conf"

# ✅ Good: {var=} notation in exceptions
if not node_name:
    raise ValueError(f"Invalid configuration: {node_name=}, {config=}")

# ✅ Good: Pattern-string for logging (NOT f-strings)
logger.info("Generated config for %s nodes", len(nodes))
logger.debug("Topology: %s, optimize=%s", topology, optimize_routes)

# ❌ Bad: f-strings in logging (prevents lazy evaluation)
logger.info(f"Generated config for {len(nodes)} nodes")
```

### Import Organization (Ruff I001)

```python
# Standard library
import json
import logging
from pathlib import Path
from typing import Any

# Third-party
import click
import jsonschema
from jinja2 import Environment

# Local
from wg_mesh_gen.builder import SmartBuilder
from wg_mesh_gen.validator import validate_config
```

### Docstring Format (Google Style)

```python
def validate_topology(config: dict[str, Any]) -> None:
    """Validate network topology configuration.

    Performs multi-layer validation:
    1. JSON Schema structural validation
    2. Business logic rules (IP conflicts, port ranges)
    3. Topology-specific constraints

    Args:
        config: Full network configuration dictionary.

    Raises:
        ValidationError: Configuration fails validation with details.

    Example:
        >>> config = {"nodes": [...], "topology": "mesh"}
        >>> validate_topology(config)  # Raises on invalid config
    """
    ...
```

### Pre-Commit Checks

```bash
# Run before EVERY commit (automated in Makefile)
uv run ruff check --fix .
uv run ruff format .
uv run pytest --cov=wg_mesh_gen --cov-report=term-missing
```

---

## Testing Workflow

### TDD Cycle (Non-Negotiable)

```
1. Write test (RED) → 2. Get user approval → 3. Run test (FAIL) → 4. Implement → 5. Run test (GREEN) → 6. Refactor
```

**Example**:

```python
# tests/test_builder.py
import pytest
from wg_mesh_gen.builder import SmartBuilder
from wg_mesh_gen.exceptions import TopologyError

class TestSmartBuilder:
    """Tests for SmartBuilder topology generation."""

    def test_build_mesh_topology_creates_full_connectivity(self, sample_nodes):
        """Test mesh topology connects all nodes bidirectionally."""
        builder = SmartBuilder()
        result = builder.build(sample_nodes, topology="mesh")

        # Each node should have N-1 peers
        for node_name, config in result.items():
            peers = config["peers"]
            assert len(peers) == len(sample_nodes) - 1

    @pytest.mark.parametrize("node_count,expected_peers", [
        (3, 2),
        (5, 4),
        (10, 9),
    ])
    def test_build_mesh_peer_count_scales_correctly(
        self, node_count, expected_peers
    ):
        """Test mesh topology peer count = N-1 for N nodes."""
        nodes = [{"name": f"node{i}", "ip": f"10.0.0.{i}"} for i in range(node_count)]
        builder = SmartBuilder()
        result = builder.build(nodes, topology="mesh")

        for config in result.values():
            assert len(config["peers"]) == expected_peers

    def test_build_with_invalid_topology_raises_error(self):
        """Test invalid topology type raises TopologyError."""
        builder = SmartBuilder()
        with pytest.raises(TopologyError, match="Unknown topology"):
            builder.build([], topology="invalid")
```

### Fixture Organization (conftest.py)

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_nodes():
    """Provide standard 3-node test configuration."""
    return [
        {"name": "server", "ip": "10.0.0.1", "port": 51820},
        {"name": "client1", "ip": "10.0.0.2", "port": 51821},
        {"name": "client2", "ip": "10.0.0.3", "port": 51822},
    ]

@pytest.fixture
def tmp_config_file(tmp_path):
    """Create temporary configuration file."""
    config = tmp_path / "config.json"
    config.write_text('{"nodes": [], "topology": "mesh"}')
    return config

@pytest.fixture
def mock_wg_command(monkeypatch):
    """Mock subprocess calls to 'wg' command."""
    def fake_check_output(cmd, **kwargs):
        if "genkey" in cmd:
            return b"FAKE_PRIVATE_KEY\n"
        if "pubkey" in cmd:
            return b"FAKE_PUBLIC_KEY\n"
        if "genpsk" in cmd:
            return b"FAKE_PSK\n"

    monkeypatch.setattr("subprocess.check_output", fake_check_output)
```

### Running Tests

```bash
# All tests with coverage
uv run pytest --cov=wg_mesh_gen --cov-report=term-missing

# Only unit tests (fast)
uv run pytest -m "not integration"

# Only integration tests
uv run pytest -m integration

# Specific test file
uv run pytest tests/test_builder.py

# Specific test function
uv run pytest tests/test_builder.py::TestSmartBuilder::test_build_mesh_topology_creates_full_connectivity

# Verbose output with print statements
uv run pytest -v -s
```

### Coverage Requirements

- **New code**: ≥80% coverage mandatory
- **Critical paths**: 100% coverage (validation, key generation, config rendering)
- **Exclude**: `if __name__ == "__main__"`, debug utilities

---

## Commit Protocol

### Change Logging (Mandatory)

**ALWAYS** record changes in `docs/claude_log.md` with ISO 8601 timestamps:

```markdown
## 2025-10-02T14:23:00+00:00 - feat: Add mesh topology builder

- Implemented SmartBuilder.build_mesh() with full peer connectivity
- Added TopologyError exception for invalid topology types
- Tests: 12 new tests in test_builder.py (coverage: 95%)
- Files modified:
  - src/wg_mesh_gen/builder.py (new)
  - src/wg_mesh_gen/exceptions.py (new)
  - tests/test_builder.py (new)
  - tests/conftest.py (added sample_nodes fixture)
```

### Conventional Commit Format

```
<type>: <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `test`: Adding/updating tests
- `docs`: Documentation updates
- `chore`: Build/tooling changes

**Examples**:

```bash
git commit -m "feat: implement JSON schema validation for configurations"
git commit -m "fix: prevent AllowedIPs conflicts in mesh topology"
git commit -m "refactor: extract key generation to separate module"
git commit -m "test: add parametrized tests for topology scaling"
git commit -m "docs: update CLAUDE.md with TDD workflow"
```

### Pre-Commit Checklist

Before EVERY commit:

1. ✅ All tests pass: `uv run pytest`
2. ✅ Ruff checks clean: `uv run ruff check --fix .`
3. ✅ Code formatted: `uv run ruff format .`
4. ✅ Coverage ≥80%: Check pytest output
5. ✅ Changes logged: Update `docs/claude_log.md`
6. ✅ Code runs successfully: Test CLI commands manually

**Automated Check** (add to `.git/hooks/pre-commit`):

```bash
#!/bin/bash
set -e

echo "Running pre-commit checks..."

# Ruff linting
uv run ruff check --fix .

# Ruff formatting
uv run ruff format .

# Tests
uv run pytest --cov=wg_mesh_gen --cov-report=term-missing

echo "✅ All checks passed!"
```

---

## CLI Development

### Click Framework Patterns

```python
# src/wg_mesh_gen/cli.py
import click
import sys
from pathlib import Path

@click.group()
@click.version_option(version="0.1.0")
def main():
    """WireGuard mesh network configuration generator."""
    pass

@main.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to YAML/JSON configuration file.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Output directory for generated configs.",
)
@click.option(
    "--topology",
    type=click.Choice(["mesh", "hub-spoke", "relay"]),
    default="mesh",
    help="Network topology type.",
)
def generate(config: Path, output: Path, topology: str):
    """Generate WireGuard configurations from a config file.

    Example:
        wg-mesh-gen generate -c network.yaml -o /etc/wireguard
    """
    try:
        # Load configuration
        from wg_mesh_gen.loader import load_config
        cfg = load_config(config)

        # Validate
        from wg_mesh_gen.validator import validate_config
        validate_config(cfg)

        # Build topology
        from wg_mesh_gen.builder import SmartBuilder
        builder = SmartBuilder()
        configs = builder.build(cfg["nodes"], topology=topology)

        # Render and write
        from wg_mesh_gen.render import render_configs
        render_configs(configs, output)

        click.echo(f"✅ Generated {len(configs)} configurations in {output}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@main.command()
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=Path("config.example.yaml"),
    help="Path for example config file.",
)
def init(output: Path):
    """Generate an example configuration file.

    Example:
        wg-mesh-gen init --output my-network.yaml
    """
    from wg_mesh_gen.examples import EXAMPLE_CONFIG

    output.write_text(EXAMPLE_CONFIG)
    click.echo(f"✅ Created example config: {output}")

if __name__ == "__main__":
    main()
```

### Input/Output Protocol

- **Input**: Configuration files (YAML/JSON) or CLI arguments
- **Output**:
  - Success: Human-readable messages to **stdout**
  - Errors: Actionable error messages to **stderr**
  - Exit codes: `0` success, `1` error

---

## Configuration Management

### Dual Format Support (YAML + JSON)

```python
# src/wg_mesh_gen/loader.py
import json
import yaml
from pathlib import Path
from typing import Any

def load_config(path: Path) -> dict[str, Any]:
    """Load configuration from YAML or JSON file.

    Args:
        path: Path to configuration file (.yaml, .yml, or .json).

    Returns:
        Parsed configuration dictionary.

    Raises:
        ValueError: Unsupported file extension.
        yaml.YAMLError: Invalid YAML syntax.
        json.JSONDecodeError: Invalid JSON syntax.
    """
    suffix = path.suffix.lower()
    content = path.read_text()

    if suffix in {".yaml", ".yml"}:
        return yaml.safe_load(content)
    elif suffix == ".json":
        return json.loads(content)
    else:
        raise ValueError(f"Unsupported config format: {suffix}")
```

### Configuration Schema Example

```yaml
# examples/mesh-network.yaml
network:
  name: "my-mesh"
  ipv4_subnet: "10.0.0.0/24"

topology: "mesh"

nodes:
  - name: "server"
    ip: "10.0.0.1"
    public_endpoint: "vpn.example.com:51820"
    port: 51820
    interface: "eth0"

  - name: "client1"
    ip: "10.0.0.2"
    port: 51821

  - name: "client2"
    ip: "10.0.0.3"
    port: 51822
```

### Validation (JSON Schema + Business Logic)

```python
# src/wg_mesh_gen/validator.py
import jsonschema
from typing import Any

SCHEMA = {
    "type": "object",
    "required": ["network", "nodes"],
    "properties": {
        "network": {
            "type": "object",
            "required": ["name", "ipv4_subnet"],
            "properties": {
                "name": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                "ipv4_subnet": {"type": "string", "pattern": r"^\d+\.\d+\.\d+\.\d+/\d+$"},
            },
        },
        "topology": {
            "type": "string",
            "enum": ["mesh", "hub-spoke", "relay"],
        },
        "nodes": {
            "type": "array",
            "minItems": 2,
            "items": {
                "type": "object",
                "required": ["name", "ip", "port"],
                "properties": {
                    "name": {"type": "string"},
                    "ip": {"type": "string"},
                    "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                },
            },
        },
    },
}

def validate_config(config: dict[str, Any]) -> None:
    """Validate configuration against schema and business rules.

    Args:
        config: Configuration dictionary to validate.

    Raises:
        jsonschema.ValidationError: Schema validation failed.
        ValueError: Business logic validation failed.
    """
    # Schema validation
    jsonschema.validate(config, SCHEMA)

    # Business logic validation
    node_ips = [node["ip"] for node in config["nodes"]]
    if len(node_ips) != len(set(node_ips)):
        raise ValueError("Duplicate IP addresses detected in nodes")

    node_names = [node["name"] for node in config["nodes"]]
    if len(node_names) != len(set(node_names)):
        raise ValueError("Duplicate node names detected")
```

---

## Security Guidelines

### Key Management Principles

1. **Never log private keys**: Use `{key[:8]}...` in logs
2. **Secure file permissions**: `chmod 600` for private key files
3. **File locking**: Use `fcntl.flock()` for concurrent access
4. **Cryptography library**: Use `cryptography` package for all crypto operations

### Key Generation Example

```python
# src/wg_mesh_gen/key_manager.py
import subprocess
from typing import NamedTuple

class KeyPair(NamedTuple):
    """WireGuard key pair."""
    private_key: str
    public_key: str
    preshared_key: str

def generate_keypair() -> KeyPair:
    """Generate WireGuard private/public key pair and PSK.

    Returns:
        KeyPair with private_key, public_key, preshared_key.

    Raises:
        subprocess.CalledProcessError: wg command failed.
    """
    # Generate private key
    private_key = subprocess.check_output(
        ["wg", "genkey"],
        text=True,
    ).strip()

    # Derive public key
    public_key = subprocess.check_output(
        ["wg", "pubkey"],
        input=private_key,
        text=True,
    ).strip()

    # Generate preshared key
    preshared_key = subprocess.check_output(
        ["wg", "genpsk"],
        text=True,
    ).strip()

    return KeyPair(private_key, public_key, preshared_key)
```

### Secure Storage with File Locking

```python
# src/wg_mesh_gen/storage.py
import json
import fcntl
from pathlib import Path
from typing import Any

class SecureStorage:
    """Thread-safe JSON key storage with file locking."""

    def __init__(self, path: Path):
        """Initialize storage at path."""
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, data: dict[str, Any]) -> None:
        """Save data with exclusive lock."""
        with open(self.path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=2)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

        # Set restrictive permissions
        self.path.chmod(0o600)

    def load(self) -> dict[str, Any]:
        """Load data with shared lock."""
        if not self.path.exists():
            return {}

        with open(self.path, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
```

---

## Common Tasks

### Task 1: Add a New CLI Command

```bash
# 1. Write test first (TDD)
# tests/test_cli.py
def test_visualize_command_generates_network_diagram(tmp_path):
    """Test visualize command creates PNG diagram."""
    config = tmp_path / "config.yaml"
    config.write_text("network:\n  name: test\nnodes: [...]")

    output = tmp_path / "diagram.png"

    result = runner.invoke(cli.main, ["visualize", "-c", str(config), "-o", str(output)])

    assert result.exit_code == 0
    assert output.exists()
    assert "Generated diagram" in result.output

# 2. Get user approval

# 3. Run test (should FAIL)
# uv run pytest tests/test_cli.py::test_visualize_command_generates_network_diagram

# 4. Implement command in src/wg_mesh_gen/cli.py
@main.command()
@click.option("-c", "--config", type=click.Path(exists=True), required=True)
@click.option("-o", "--output", type=click.Path(), default="network.png")
def visualize(config, output):
    """Generate network topology visualization."""
    from wg_mesh_gen.visualizer import generate_diagram
    generate_diagram(config, output)
    click.echo(f"✅ Generated diagram: {output}")

# 5. Run test again (should PASS)
# 6. Refactor if needed
# 7. Log change in docs/claude_log.md
# 8. Commit
```

### Task 2: Refactor Legacy Code to Modular Architecture

```bash
# 1. Create tests for existing behavior
# tests/test_legacy.py - capture current wg_conf_gen.py behavior

# 2. Extract module (e.g., key_manager.py)
# src/wg_mesh_gen/key_manager.py

# 3. Update tests to use new module
# tests/test_key_manager.py

# 4. Replace usage in legacy code with import
# wg_conf_gen.py: from wg_mesh_gen.key_manager import generate_keypair

# 5. Verify all tests still pass

# 6. Log refactoring in docs/claude_log.md
```

### Task 3: Add Support for New Topology Type

```bash
# Example: Add "layered-routing" topology

# 1. Write tests
# tests/test_builder.py
def test_build_layered_routing_creates_hub_with_spokes():
    """Test layered routing creates central hub with client spokes."""
    ...

# 2. Implement in SmartBuilder
# src/wg_mesh_gen/builder.py
def build_layered_routing(self, nodes):
    """Build layered routing topology."""
    ...

# 3. Update CLI choice options
# src/wg_mesh_gen/cli.py
@click.option("--topology", type=click.Choice([..., "layered-routing"]))

# 4. Update schema validation
# src/wg_mesh_gen/validator.py
"topology": {"enum": [..., "layered-routing"]}

# 5. Add example config
# examples/layered-routing.yaml
```

---

## Troubleshooting

### Issue: Tests failing after refactor

**Solution**:
```bash
# 1. Check coverage report for missed branches
uv run pytest --cov=wg_mesh_gen --cov-report=html
firefox htmlcov/index.html

# 2. Run specific failing test with verbose output
uv run pytest -v -s tests/test_builder.py::test_specific_failure

# 3. Use pytest debugger
uv run pytest --pdb tests/test_builder.py::test_specific_failure
```

### Issue: Ruff linting errors

**Solution**:
```bash
# Auto-fix most issues
uv run ruff check --fix .

# See detailed error explanations
uv run ruff check --output-format=full .

# Ignore specific rule temporarily (last resort)
# Add to pyproject.toml: ignore = ["E501", "D100"]
```

### Issue: Import errors with uv

**Solution**:
```bash
# Resync dependencies
uv sync

# Check virtual environment is active
which python  # Should show .venv/bin/python

# Run commands with uv run prefix
uv run python -c "import wg_mesh_gen; print('ok')"
```

### Issue: WireGuard keys not generating

**Solution**:
```bash
# Check wg command availability
which wg || sudo apt install wireguard-tools

# Test key generation manually
wg genkey | tee privatekey | wg pubkey > publickey
cat privatekey publickey

# Mock in tests (see conftest.py fixture example)
```

---

## Quick Reference

### uv Commands

```bash
uv sync                          # Install/sync dependencies
uv add <package>                 # Add production dependency
uv add --group dev <package>     # Add dev dependency
uv run <command>                 # Run command in venv
uv lock                          # Update lockfile
uv pip list                      # List installed packages
```

### Ruff Commands

```bash
uv run ruff check .              # Lint code
uv run ruff check --fix .        # Auto-fix issues
uv run ruff format .             # Format code
uv run ruff check --select=I     # Check imports only
```

### pytest Commands

```bash
uv run pytest                                    # Run all tests
uv run pytest -m integration                     # Integration tests only
uv run pytest --cov --cov-report=term-missing    # With coverage
uv run pytest -k "mesh"                          # Tests matching "mesh"
uv run pytest --lf                               # Re-run last failures
uv run pytest -x                                 # Stop on first failure
```

### Git Commands

```bash
git status                       # Check status
git add .                        # Stage all changes
git commit -m "feat: ..."        # Commit with message
git log --oneline -5             # Recent commits
git diff                         # Unstaged changes
git diff --staged                # Staged changes
```

---

## Documentation Updates

When updating this file:

1. Increment version number (semantic versioning)
2. Update "Last Updated" date (ISO 8601)
3. Log change in `docs/claude_log.md`
4. Verify consistency with `.specify/memory/constitution.md`
5. Update table of contents if sections added/removed

---

## Contact & Resources

- **Constitution**: `.specify/memory/constitution.md` (v1.2.0)
- **Change Log**: `docs/claude_log.md`
- **Examples**: `examples/` directory
- **Issue Tracker**: (Add GitHub repo link when available)
- **License**: BSD-3-Clause (see LICENSE file)

---

**End of CLAUDE.md v1.0.0**
