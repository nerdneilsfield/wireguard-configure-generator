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
# Run linting
make lint

# Format code
make format
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

## Development Conventions

- **Script Organization**:
  - 脚本都放到 scripts 下面去 (All scripts should be placed in the scripts directory)

## Repository Guidelines

- **File Organization**:
  - 不要在根目录放任何测试文件 (Do not place any test files in the root directory)

## Commit and Logging Guidelines

- **Logging Workflow**:
  - Complete all operations for a phase and record them with a timestamp in `docs/claude_logs.md`
  - Commit changes with English commit messages

## Project Management Notes
- This project is managed by uv, use uv to install and run, remember to use uv venv

## Operational Notes

- **Commit Practices**:
  - Ensure code can be run everytime before committing