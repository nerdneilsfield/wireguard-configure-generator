# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WireGuard configuration generator that supports complex mesh network topologies with automatic key management. The codebase uses Python 3.12+ and follows a modular architecture.

## Essential Commands

### Development Setup
```bash
# Install package in development mode
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# Run specific test file
make test-file FILE=tests/test_builder.py

# Run tests for specific module
make test-logger    # Test logger module
make test-config    # Test configuration processing
make test-cli       # Test CLI

# Run integration tests
make test-integration
```

### Code Quality
```bash
# Run linting with Ruff
make lint
# or: uv run ruff check --fix .

# Format code with Ruff
make format
# or: uv run ruff format .

# Run both linting and formatting
uv run ruff check --fix . && uv run ruff format .
```

### Running the Application
```bash
# Generate WireGuard configurations
python -m wg_mesh_gen.cli gen --nodes-file examples/nodes.yaml --topo-file examples/topology.yaml --output-dir out

# Validate configurations
python -m wg_mesh_gen.cli valid --nodes-file examples/nodes.yaml --topo-file examples/topology.yaml

# Generate network visualization
python -m wg_mesh_gen.cli vis --nodes-file examples/nodes.yaml --topo-file examples/topology.yaml --output topology.png

# Key management
python -m wg_mesh_gen.cli keys generate <node_name>
python -m wg_mesh_gen.cli keys list
```

## Architecture Overview

### Core Modules
- **cli.py**: Click-based CLI interface - entry point for all commands
- **builder.py** & **smart_builder.py**: Builds peer configurations based on topology, handles complex mesh networks
- **validator.py**: Unified configuration validation pipeline with schema and business logic checks
- **loader.py**: Loads YAML/JSON configurations
- **simple_storage.py**: JSON-based key storage with file locking
- **render.py**: Jinja2 template rendering for WireGuard config files
- **visualizer.py**: NetworkX-based network topology visualization

### Python Best Practices (Python 3.12+)

#### Type Hints
- **Required**: All public functions MUST have type annotations for parameters and return values
- Use `from __future__ import annotations` at top of files for forward compatibility
- Leverage modern union syntax: `str | None` instead of `Optional[str]`
- Example:
  ```python
  from __future__ import annotations

  def build_config(node: str, peers: list[str]) -> dict[str, Any]:
      ...
  ```

#### Code Style
- **Imports**: Group in order: stdlib → third-party → local (separated by blank lines)
- **String Quotes**: Consistent per file (prefer double quotes for docstrings)
- **Line Length**: Max 88 characters (Black default)
- **Comprehensions**: Use for simple cases; explicit loops for complex logic
- **Error Messages**: Use f-strings with `{var=}` for debugging
  ```python
  if not 0 <= port <= 65535:
      raise ValueError(f"Invalid port: {port=}")
  ```
- **Logging**: Use pattern-strings NOT f-strings
  ```python
  # Good
  logger.info("Processing node %s with %d peers", node_name, peer_count)

  # Bad
  logger.info(f"Processing node {node_name} with {peer_count} peers")
  ```

#### Docstrings
- Google style with Args/Returns/Raises sections
- Describe instances, not classes
- Example:
  ```python
  def validate_topology(nodes: dict, topology: dict) -> bool:
      """Validates network topology configuration.

      Args:
          nodes: Dictionary of node configurations with names as keys
          topology: Topology definition with peer relationships

      Returns:
          True if validation passes

      Raises:
          ValidationError: If topology contains invalid references
      """
  ```

### Key Architectural Decisions
1. **Configuration Format**: Supports both YAML and JSON with schema validation
2. **Key Storage**: Uses simple JSON file storage with file locking for concurrent access
3. **Template System**: Jinja2 templates in `templates/` for flexible config generation
4. **Mesh Network Support**: Handles complex topologies with relay nodes and multiple endpoints
5. **Validation**: Unified validation pipeline with JSON schema and business logic validation

### Configuration Structure
- **Node Configuration**: Defines nodes with roles (client/relay), IPs, and endpoints
- **Topology Configuration**: Defines peer relationships and allowed IP ranges
- **Multiple Endpoints**: Nodes can have different endpoints for different peer groups

### Development Notes
- The codebase contains Chinese comments throughout
- Uses modern Python tooling: uv package manager, black formatter, flake8 linter
- Comprehensive test coverage with pytest
- Cross-platform Makefile for consistent development commands

### Git Commit Requirements
- After completing each modification, record changes in `docs/claude_log.md` with current timestamp
- Commit and push changes using English commit messages
- Follow conventional commit format (e.g., "fix:", "feat:", "refactor:", "docs:")

## Quality Assurance with Ruff

### Why Ruff?
- **10-100x faster** than flake8/black/isort combined
- **All-in-one**: Replaces flake8, black, isort, pyupgrade, and more
- **Modern**: Written in Rust, native support for Python 3.12+ features
- **Comprehensive**: 800+ rules from popular linters

### Essential Ruff Commands

```bash
# Lint code (check for issues)
uv run ruff check .

# Lint and auto-fix issues
uv run ruff check --fix .

# Format code (Black-compatible)
uv run ruff format .

# Run both linting and formatting
uv run ruff check --fix . && uv run ruff format .

# Show what would be fixed (dry run)
uv run ruff check --diff .
```

### Recommended pyproject.toml Configuration

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

# Exclude directories
exclude = [
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
]

[tool.ruff.lint]
# Enable comprehensive rule sets
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes
    "I",   # isort (import sorting)
    "B",   # flake8-bugbear
    "UP",  # pyupgrade (modern Python syntax)
    "D",   # pydocstyle (docstring conventions)
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]

# Ignore specific rules
ignore = [
    "E501",  # Line too long (handled by formatter)
    "D100",  # Missing docstring in public module (optional)
]

# Per-file ignores
[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Unused imports in __init__.py
"tests/**" = ["D"]        # No docstrings required in tests

# Docstring convention
[tool.ruff.lint.pydocstyle]
convention = "google"

# Formatting options
[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"
```

### Common Rule Categories

| Category | Code | Description |
|----------|------|-------------|
| **Pycodestyle** | E, W | Style violations (PEP 8) |
| **Pyflakes** | F | Logical errors (undefined vars, etc.) |
| **isort** | I | Import sorting |
| **pyupgrade** | UP | Modernize Python syntax |
| **flake8-bugbear** | B | Find likely bugs |
| **pydocstyle** | D | Docstring conventions |
| **flake8-comprehensions** | C4 | Better comprehensions |
| **flake8-simplify** | SIM | Simplify code patterns |

### Integration with Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.12.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

## Testing with pytest

### Why pytest?
- **Fixture system**: Reusable test setup with dependency injection
- **Parametrization**: Run same test with different inputs
- **Rich assertions**: Better error messages than unittest
- **Plugin ecosystem**: Extensive plugins (pytest-cov, pytest-xdist, etc.)

### Essential pytest Commands

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_builder.py

# Run specific test
uv run pytest tests/test_builder.py::test_build_mesh_config

# Run tests matching pattern
uv run pytest -k "mesh"

# Run with coverage report
uv run pytest --cov=wg_mesh_gen --cov-report=term-missing

# Run only integration tests
uv run pytest -m integration

# Run in parallel (requires pytest-xdist)
uv run pytest -n auto
```

### Project Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_cli.py              # CLI tests
├── test_builder.py          # Builder unit tests
├── test_validator.py        # Validator tests
├── integration/
│   ├── conftest.py          # Integration-specific fixtures
│   ├── test_full_workflow.py
│   └── test_mesh_generation.py
└── fixtures/
    ├── sample_nodes.yaml
    └── sample_topology.yaml
```

### pytest Best Practices

#### 1. Use Fixtures for Setup

```python
# conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_nodes_config():
    """Load sample nodes configuration."""
    config_path = Path(__file__).parent / "fixtures" / "sample_nodes.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)

@pytest.fixture
def tmp_output_dir(tmp_path):
    """Provide a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
```

#### 2. Parametrize Tests

```python
import pytest

@pytest.mark.parametrize("node_count,expected_peers", [
    (2, 1),
    (3, 2),
    (5, 4),
])
def test_mesh_peer_count(node_count, expected_peers):
    config = generate_mesh_config(node_count)
    assert len(config.peers) == expected_peers
```

#### 3. Use Markers for Test Categories

```python
# Mark slow integration tests
@pytest.mark.integration
def test_large_network_generation():
    ...

# Mark tests requiring external services
@pytest.mark.skipif(not has_wireguard(), reason="WireGuard not installed")
def test_wireguard_validation():
    ...
```

#### 4. Descriptive Test Names

```python
# Good: Clear what's being tested
def test_build_config_with_invalid_ip_raises_validation_error():
    ...

def test_mesh_topology_generates_all_peer_connections():
    ...

# Bad: Unclear intent
def test_config():
    ...

def test_mesh():
    ...
```

### pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",  # Show summary of all test outcomes
]

[tool.coverage.run]
source = ["wg_mesh_gen"]
omit = ["tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

## Development Conventions

- **Script Organization**:
  - 脚本都放到 scripts 下面去 (All scripts should be placed in the scripts directory)

## Repository Guidelines

- **File Organization**:
  - 不要在根目录放任何测试文件 (Do not place any test files in the root directory)
  - Tests go in `tests/` directory, mirroring `src/` structure

## Commit and Logging Guidelines

- **Logging Workflow**:
  - Complete all operations for a phase and record them with a timestamp in `docs/claude_logs.md`
  - Commit changes with English commit messages

## Project Management with uv

### Why uv?
- **10-100x faster** than pip for package installation
- **Comprehensive**: Replaces pip, pip-tools, poetry, pyenv in one tool
- **Reliable**: Automatic virtual environment management, reproducible builds via lockfile
- **Modern**: Written in Rust, actively maintained by Astral (creators of Ruff)

### Essential uv Commands

#### Project Setup
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project in development mode
uv sync

# Install with dev dependencies
uv sync --group dev
```

#### Dependency Management
```bash
# Add a new dependency (updates pyproject.toml and uv.lock)
uv add <package>

# Add a development dependency
uv add --group dev <package>

# Update lockfile after manual pyproject.toml edits
uv lock

# Sync environment to match lockfile (reproducible install)
uv sync --locked
```

#### Running Commands
```bash
# Run command in managed virtual environment (no activation needed)
uv run python -m wg_mesh_gen.cli gen --nodes-file examples/nodes.yaml

# Run tests
uv run pytest

# Run linting
uv run ruff check .

# Run any make target
uv run make test
```

#### Advanced Usage
```bash
# Add Git dependency
uv add git+https://github.com/user/repo

# Add local path dependency (editable)
uv add --editable ../local-package

# Compile requirements for Docker/CI (legacy pip compatibility)
uv pip compile pyproject.toml -o requirements.txt
```

### pyproject.toml Best Practices

```toml
[project]
name = "wireguard-configure-generator"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "click>=8.0",
    "pyyaml>=6.0",
    "jinja2>=3.1",
    # ... production dependencies only
]

[dependency-groups]
dev = [
    "pytest>=7.0",
    "black>=23.0",
    "ruff>=0.1.0",
    # ... development dependencies
]

[tool.uv.sources]
# For Git/path/workspace dependencies
# Example: custom-lib = { git = "https://github.com/org/repo", tag = "v1.0" }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Key Differences from pip/poetry

| Task | uv | pip/poetry |
|------|-----|-----------|
| Add dependency | `uv add requests` | `pip install requests` / `poetry add requests` |
| Install project | `uv sync` | `pip install -e .` / `poetry install` |
| Update lock | `uv lock` | N/A / `poetry lock` |
| Run command | `uv run pytest` | `pytest` / `poetry run pytest` |
| Virtual env | Automatic `.venv` | Manual `venv` / Automatic |

### Migration Notes
- **Legacy pip support**: `pip install -e ".[dev]"` still works for users without uv
- **Docker**: Use multi-stage builds with `uv sync --no-install-project` for caching
- **CI/CD**: Install uv in CI, use `uv sync --locked` for reproducible builds

## Operational Notes

- **Commit Practices**:
  - Ensure code can be run everytime before committing