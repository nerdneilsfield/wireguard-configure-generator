# WireGuard Configuration Generator Makefile
# Cross-platform build and test support for Windows and Unix systems

# Detect operating system
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    PYTHON := python
    RM := del /Q /F
    RMDIR := rmdir /S /Q
    MKDIR := mkdir
    SEP := /
    NULL := nul
    ECHO := echo
    CHCP := chcp 65001 >nul 2>&1 &
else
    DETECTED_OS := $(shell uname -s)
    PYTHON := python3
    RM := rm -f
    RMDIR := rm -rf
    MKDIR := mkdir -p
    SEP := /
    NULL := /dev/null
    ECHO := echo
    CHCP :=
endif

# Project configuration
PROJECT_NAME := wireguard-configure-generator
OUTPUT_DIR := out
TEST_DIR := tests
COVERAGE_DIR := $(OUTPUT_DIR)$(SEP)coverage
COVERAGE_HTML := $(COVERAGE_DIR)$(SEP)html
TEST_RESULTS := $(OUTPUT_DIR)$(SEP)test_results.xml
COVERAGE_XML := $(OUTPUT_DIR)$(SEP)coverage.xml

# Default target
default: help

.PHONY: help
help: ## Show all available make targets
	@$(ECHO) "WireGuard Configuration Generator - Available Commands:"
	@$(ECHO) ""
	@$(ECHO) "test                     Run all test cases"
	@$(ECHO) "test-verbose             Run tests with verbose output"
	@$(ECHO) "test-coverage            Run tests with coverage report"
	@$(ECHO) "test-quick               Run quick tests (skip slow tests)"
	@$(ECHO) "test-logger              Run logger system tests only"
	@$(ECHO) "test-config              Run configuration processing tests only"
	@$(ECHO) "test-cli                 Run CLI tests only"
	@$(ECHO) "test-file FILE=<name>    Run specific test file"
	@$(ECHO) "test-integration         Run integration tests"
	@$(ECHO) "test-all                 Run complete test workflow"
	@$(ECHO) "test-stats               Show test statistics"
	@$(ECHO) "clean                    Clean generated files and cache"
	@$(ECHO) "clean-test               Clean test-related files only"
	@$(ECHO) "install-deps             Install test dependencies"
	@$(ECHO) "install-dev-deps         Install development dependencies"
	@$(ECHO) "lint                     Run code quality checks"
	@$(ECHO) "format                   Format code"
	@$(ECHO) "check-env                Check development environment dependencies"
	@$(ECHO) ""
	@$(ECHO) "Detected OS: $(DETECTED_OS)"
	@$(ECHO) "Python command: $(PYTHON)"

# Environment check
.PHONY: check-env
check-env: ## Check development environment dependencies
	@$(CHCP)$(ECHO) "Checking development environment..."
	@$(PYTHON) --version || ($(ECHO) "ERROR: Python not installed or not in PATH" && exit 1)
	@$(PYTHON) -c "import pytest" 2>$(NULL) || ($(ECHO) "ERROR: pytest not installed, run: pip install pytest" && exit 1)
	@$(PYTHON) -c "import yaml" 2>$(NULL) || ($(ECHO) "ERROR: PyYAML not installed, run: pip install pyyaml" && exit 1)
	@$(ECHO) "Environment check passed"

# Create output directories
.PHONY: setup-dirs
setup-dirs:
	@$(ECHO) "Creating output directories..."
	@$(MKDIR) $(OUTPUT_DIR) 2>$(NULL) || true
	@$(MKDIR) $(COVERAGE_DIR) 2>$(NULL) || true

# Basic test target
.PHONY: test
test: check-env setup-dirs ## Run all test cases
	@$(CHCP)$(ECHO) "Running test suite..."
	@$(PYTHON) -m pytest $(TEST_DIR) --tb=short --color=yes --junitxml=$(TEST_RESULTS) -q
	@$(ECHO) "Tests completed, results saved to: $(TEST_RESULTS)"

# Verbose test target
.PHONY: test-verbose
test-verbose: check-env setup-dirs ## Run tests with verbose output
	@$(CHCP)$(ECHO) "Running verbose test suite..."
	@$(PYTHON) -m pytest $(TEST_DIR) --tb=long --color=yes --junitxml=$(TEST_RESULTS) -v -s
	@$(ECHO) "Verbose tests completed, results saved to: $(TEST_RESULTS)"

# Coverage test target
.PHONY: test-coverage
test-coverage: check-env setup-dirs ## Run tests with coverage report
	@$(CHCP)$(ECHO) "Running coverage tests..."
	@$(PYTHON) -c "import pytest_cov" 2>$(NULL) || ($(ECHO) "ERROR: pytest-cov not installed, run: pip install pytest-cov" && exit 1)
	@$(PYTHON) -m pytest $(TEST_DIR) --cov=wg_mesh_gen --cov-report=html:$(COVERAGE_HTML) --cov-report=xml:$(COVERAGE_XML) --cov-report=term-missing --tb=short --color=yes --junitxml=$(TEST_RESULTS)
	@$(ECHO) "Coverage tests completed"
	@$(ECHO) "Test results: $(TEST_RESULTS)"
	@$(ECHO) "Coverage report: $(COVERAGE_HTML)$(SEP)index.html"

# Quick test (skip slow tests)
.PHONY: test-quick
test-quick: check-env setup-dirs ## Run quick tests (skip slow tests)
	@$(CHCP)$(ECHO) "Running quick tests..."
	@$(PYTHON) -m pytest $(TEST_DIR) -m "not slow" --tb=short --color=yes -q
	@$(ECHO) "Quick tests completed"

# Specific module tests
.PHONY: test-logger
test-logger: check-env setup-dirs ## Run logger system tests only
	@$(CHCP)$(ECHO) "Running logger system tests..."
	@$(PYTHON) -m pytest $(TEST_DIR)/test_logger.py -v

.PHONY: test-config
test-config: check-env setup-dirs ## Run configuration processing tests only
	@$(CHCP)$(ECHO) "Running configuration processing tests..."
	@$(PYTHON) -m pytest $(TEST_DIR)/test_config_simple.py $(TEST_DIR)/test_config.py -v

.PHONY: test-cli
test-cli: check-env setup-dirs ## Run CLI tests only
	@$(CHCP)$(ECHO) "Running CLI tests..."
	@$(PYTHON) -m pytest $(TEST_DIR)/test_cli.py -v

# Test specific file
.PHONY: test-file
test-file: check-env setup-dirs ## Run specific test file (usage: make test-file FILE=test_logger.py)
ifndef FILE
	@$(ECHO) "ERROR: Please specify test file: make test-file FILE=test_logger.py"
	@exit 1
endif
	@$(CHCP)$(ECHO) "Running test file: $(FILE)"
	@$(PYTHON) -m pytest $(TEST_DIR)/$(FILE) -v

# Clean targets
.PHONY: clean
clean: ## Clean generated files and cache
	@$(ECHO) "Cleaning project files..."
	@$(RMDIR) $(OUTPUT_DIR) 2>$(NULL) || true
	@$(RMDIR) .pytest_cache 2>$(NULL) || true
	@$(PYTHON) -c "import shutil, os; [shutil.rmtree(root, ignore_errors=True) for root, dirs, files in os.walk('.') for d in dirs if d == '__pycache__']" 2>$(NULL) || true
	@$(ECHO) "Cleanup completed"

.PHONY: clean-test
clean-test: ## Clean test-related files only
	@$(ECHO) "Cleaning test files..."
	@$(RMDIR) $(OUTPUT_DIR) 2>$(NULL) || true
	@$(RMDIR) .pytest_cache 2>$(NULL) || true
	@$(ECHO) "Test file cleanup completed"

# Install dependencies
.PHONY: install-deps
install-deps: ## Install test dependencies
	@$(CHCP)$(ECHO) "Installing test dependencies..."
	@$(PYTHON) -m pip install pytest pytest-cov pyyaml
	@$(ECHO) "Dependencies installation completed"

.PHONY: install-dev-deps
install-dev-deps: ## Install development dependencies
	@$(CHCP)$(ECHO) "Installing development dependencies..."
	@$(PYTHON) -m pip install -r requirements-dev.txt
	@$(ECHO) "Development dependencies installation completed"

# Code quality checks
.PHONY: lint
lint: check-env ## Run code quality checks
	@$(CHCP)$(ECHO) "Running code quality checks..."
	@$(PYTHON) -c "import flake8" 2>$(NULL) || ($(ECHO) "ERROR: flake8 not installed, run: pip install flake8" && exit 1)
	@$(PYTHON) -m flake8 wg_mesh_gen $(TEST_DIR) --max-line-length=120 --ignore=E203,W503
	@$(ECHO) "Code quality checks passed"

.PHONY: format
format: check-env ## Format code
	@$(CHCP)$(ECHO) "Formatting code..."
	@$(PYTHON) -c "import black" 2>$(NULL) || ($(ECHO) "ERROR: black not installed, run: pip install black" && exit 1)
	@$(PYTHON) -m black wg_mesh_gen $(TEST_DIR) --line-length=120
	@$(ECHO) "Code formatting completed"

# Project functionality tests
.PHONY: test-integration
test-integration: check-env setup-dirs ## Run integration tests
	@$(CHCP)$(ECHO) "Running integration tests..."
	@$(ECHO) "Testing YAML configuration file generation..."
	@$(PYTHON) -m wg_mesh_gen.cli --nodes-file examples/nodes.yaml --topo-file examples/topology.yaml --output-dir $(OUTPUT_DIR)/integration_test gen
	@$(ECHO) "Testing JSON configuration file generation..."
	@$(PYTHON) -m wg_mesh_gen.cli --nodes-file examples/nodes.json --topo-file examples/topology.json --output-dir $(OUTPUT_DIR)/integration_test_json gen
	@$(ECHO) "Testing visualization functionality..."
	@$(PYTHON) -m wg_mesh_gen.cli --nodes-file examples/nodes.yaml --topo-file examples/topology.yaml --output-dir $(OUTPUT_DIR)/integration_test vis
	@$(ECHO) "Integration tests completed"

# Complete test workflow
.PHONY: test-all
test-all: clean test-coverage test-integration ## Run complete test workflow
	@$(CHCP)$(ECHO) "Complete test workflow finished!"
	@$(ECHO) "View coverage report: $(COVERAGE_HTML)$(SEP)index.html"

# Show test statistics
.PHONY: test-stats
test-stats: ## Show test statistics
	@$(CHCP)$(ECHO) "Test Statistics:"
ifeq ($(DETECTED_OS),Windows)
	@$(ECHO) "Test files count: $$(dir /b $(TEST_DIR)\test_*.py 2>$(NULL) | find /c /v "" || $(ECHO) Unknown)"
	@$(ECHO) "Test cases count: $$($(PYTHON) -m pytest $(TEST_DIR) --collect-only -q 2>$(NULL) | find /c "<Function" || $(ECHO) Unknown)"
	@$(ECHO) "Project code lines: $$(for /r wg_mesh_gen %%f in (*.py) do @type "%%f" 2>$(NULL) | find /c /v "" || $(ECHO) Unknown)"
	@$(ECHO) "Test code lines: $$(for /r $(TEST_DIR) %%f in (*.py) do @type "%%f" 2>$(NULL) | find /c /v "" || $(ECHO) Unknown)"
else
	@$(ECHO) "Test files count: $$(find $(TEST_DIR) -name 'test_*.py' | wc -l)"
	@$(ECHO) "Test cases count: $$($(PYTHON) -m pytest $(TEST_DIR) --collect-only -q 2>$(NULL) | grep -c '<Function' || $(ECHO) Unknown)"
	@$(ECHO) "Project code lines: $$(find wg_mesh_gen -name '*.py' -exec wc -l {} + 2>$(NULL) | tail -1 | awk '{print $$1}' || $(ECHO) Unknown)"
	@$(ECHO) "Test code lines: $$(find $(TEST_DIR) -name '*.py' -exec wc -l {} + 2>$(NULL) | tail -1 | awk '{print $$1}' || $(ECHO) Unknown)"
endif
