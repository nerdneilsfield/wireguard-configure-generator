"""Contract tests for wg-mesh-gen validate command.

Tests the CLI interface contract for the validate command according to
specs/001-jinja2-dns-wiregurard/contracts/cli-validate.md
"""

import json
import subprocess
from pathlib import Path

import pytest


class TestValidateCommand:
    """Test wg-mesh-gen validate command contract."""

    def test_valid_toml_returns_exit_code_0(self, tmp_path, sample_toml_config):
        """Test that valid TOML returns exit code 0."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)

        result = subprocess.run(
            ["uv", "run", "wg-mesh-gen", "validate", "-c", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "✅ TOML syntax: Valid" in result.stdout
        assert "✅ Schema validation: Passed" in result.stdout
        assert "✅ Business logic validation: Passed" in result.stdout

    def test_syntax_errors_return_exit_code_1(self, tmp_path):
        """Test that syntax errors return exit code 1."""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text("[common\nbroken syntax")  # Invalid TOML

        result = subprocess.run(
            ["uv", "run", "wg-mesh-gen", "validate", "-c", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "❌" in result.stderr or "Error" in result.stderr
        assert "syntax" in result.stderr.lower()

    def test_schema_validation_errors(self, tmp_path):
        """Test that schema validation errors are reported."""
        config_file = tmp_path / "invalid_schema.toml"
        config_file.write_text(
            """
[common]
network_name = "test"
# Missing network_ipv4_addr

[server]
name = "srv"
# Missing required fields
"""
        )

        result = subprocess.run(
            ["uv", "run", "wg-mesh-gen", "validate", "-c", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Schema validation" in result.stderr or "validation failed" in result.stderr.lower()

    def test_business_logic_validation(self, tmp_path):
        """Test business logic validation (unique names/IPs, gen_global/gen_local)."""
        config_file = tmp_path / "duplicate.toml"
        config_file.write_text(
            """
[common]
network_name = "test"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "srv"
endpoint = "1.2.3.4"
vlan_ipv4_addr = "10.0.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "client1"
vlan_ipv4_addr = "10.0.0.2"
port = 51821
gen_global = true
gen_local = false

[[clients]]
name = "client1"
vlan_ipv4_addr = "10.0.0.2"
port = 51822
gen_global = false
gen_local = false
"""
        )

        result = subprocess.run(
            ["uv", "run", "wg-mesh-gen", "validate", "-c", str(config_file)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Duplicate" in result.stderr or "duplicate" in result.stderr.lower()

    def test_keys_flag_validates_key_storage(
        self, tmp_path, sample_toml_config, sample_keys
    ):
        """Test that -k/--keys flag validates key storage."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        keys_file = tmp_path / "keys.json"
        keys_file.write_text(json.dumps(sample_keys))

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "validate",
                "-c",
                str(config_file),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "✅ Key storage validation: Passed" in result.stdout

    def test_missing_keys_for_nodes_detected(self, tmp_path, sample_toml_config):
        """Test that missing keys for nodes are detected."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        keys_file = tmp_path / "keys.json"

        # Incomplete keys - missing client keys
        incomplete_keys = {
            "version": "1.0",
            "server": {
                "private_key": "test",
                "public_key": "test",
                "preshared_key": "test",
            },
            "clients": {},
        }
        keys_file.write_text(json.dumps(incomplete_keys))

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "validate",
                "-c",
                str(config_file),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Missing" in result.stderr or "not found" in result.stderr.lower()

    def test_invalid_key_format_detected(self, tmp_path, sample_toml_config):
        """Test that invalid key format is detected (not 44-char base64)."""
        import base64
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        keys_file = tmp_path / "keys.json"

        # Invalid key format - too short
        invalid_keys = {
            "version": "1.0",
            "server": {
                "private_key": "short",  # Invalid: not 44 chars
                "public_key": "short",
                "preshared_key": "short",
            },
            "clients": {
                "laptop": {
                    "private_key": "short",
                    "public_key": "short",
                    "preshared_key": "short",
                },
                "phone": {
                    "private_key": "short",
                    "public_key": "short",
                    "preshared_key": "short",
                },
            },
        }
        keys_file.write_text(json.dumps(invalid_keys))

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "validate",
                "-c",
                str(config_file),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "Invalid" in result.stderr or "format" in result.stderr.lower()

    def test_extra_keys_show_warning(self, tmp_path, sample_toml_config):
        """Test that extra keys in storage show warning."""
        import base64
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        keys_file = tmp_path / "keys.json"

        # Extra keys for nodes not in config - use valid base64
        extra_keys = {
            "version": "1.0",
            "server": {
                "private_key": base64.b64encode(b"a" * 32).decode("ascii"),
                "public_key": base64.b64encode(b"b" * 32).decode("ascii"),
                "preshared_key": base64.b64encode(b"c" * 32).decode("ascii"),
            },
            "clients": {
                "laptop": {
                    "private_key": base64.b64encode(b"d" * 32).decode("ascii"),
                    "public_key": base64.b64encode(b"e" * 32).decode("ascii"),
                    "preshared_key": base64.b64encode(b"f" * 32).decode("ascii"),
                },
                "phone": {
                    "private_key": base64.b64encode(b"g" * 32).decode("ascii"),
                    "public_key": base64.b64encode(b"h" * 32).decode("ascii"),
                    "preshared_key": base64.b64encode(b"i" * 32).decode("ascii"),
                },
                "extra_client": {  # Not in config
                    "private_key": base64.b64encode(b"j" * 32).decode("ascii"),
                    "public_key": base64.b64encode(b"k" * 32).decode("ascii"),
                    "preshared_key": base64.b64encode(b"l" * 32).decode("ascii"),
                },
            },
        }
        keys_file.write_text(json.dumps(extra_keys))

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "validate",
                "-c",
                str(config_file),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert "⚠️" in result.stdout or "Warning" in result.stdout

    def test_strict_flag_treats_warnings_as_errors(self, tmp_path):
        """Test that --strict flag treats warnings as errors."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(
            """
[common]
network_name = "test"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "srv"
endpoint = "1.2.3.4"
vlan_ipv4_addr = "10.0.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "client1"
vlan_ipv4_addr = "10.0.0.2"
port = 51821
gen_global = false
gen_local = true
# Missing dns1/dns2 might trigger warning
"""
        )

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "validate",
                "-c",
                str(config_file),
                "--strict",
            ],
            capture_output=True,
            text=True,
        )

        # In strict mode, warnings should cause exit code 1
        # (if there are any warnings)
        if "⚠️" in result.stdout or "Warning" in result.stdout:
            assert result.returncode == 1
