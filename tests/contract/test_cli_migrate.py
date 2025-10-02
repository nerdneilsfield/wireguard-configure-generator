"""Contract tests for wg-mesh-gen migrate command.

Tests the CLI interface contract for the migrate command according to
specs/001-jinja2-dns-wiregurard/contracts/cli-migrate.md
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


class TestMigrateCommand:
    """Test wg-mesh-gen migrate command contract."""

    def test_json_to_toml_conversion(self, tmp_path, sample_json_config):
        """Test JSON to TOML conversion."""
        input_file = tmp_path / "legacy.json"
        input_file.write_text(json.dumps(sample_json_config))
        output_file = tmp_path / "network.toml"
        keys_file = tmp_path / "keys.json"

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "migrate",
                "-i",
                str(input_file),
                "-o",
                str(output_file),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert output_file.exists()
        assert "✅ Loaded legacy JSON configuration" in result.stdout
        assert "✅ Wrote TOML configuration" in result.stdout

    def test_embedded_key_extraction(self, tmp_path, sample_json_config):
        """Test embedded key extraction to keys.json."""
        input_file = tmp_path / "legacy.json"
        input_file.write_text(json.dumps(sample_json_config))
        output_file = tmp_path / "network.toml"
        keys_file = tmp_path / "keys.json"

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "migrate",
                "-i",
                str(input_file),
                "-o",
                str(output_file),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert keys_file.exists()
        assert "✅ Extracted embedded keys" in result.stdout

        # Verify keys extracted correctly
        keys = json.loads(keys_file.read_text())
        assert "server" in keys
        assert "clients" in keys
        assert keys["server"]["private_key"] == sample_json_config["server"]["prvkey"]

    def test_keys_flag_specifies_custom_path(self, tmp_path, sample_json_config):
        """Test -k/--keys flag specifies custom key storage path."""
        input_file = tmp_path / "legacy.json"
        input_file.write_text(json.dumps(sample_json_config))
        output_file = tmp_path / "network.toml"
        custom_keys = tmp_path / "custom_keys.json"

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "migrate",
                "-i",
                str(input_file),
                "-o",
                str(output_file),
                "-k",
                str(custom_keys),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert custom_keys.exists()
        assert not (tmp_path / "keys.json").exists()  # Default not created

    def test_validation_of_migrated_config(self, tmp_path, sample_json_config):
        """Test validation of migrated config."""
        input_file = tmp_path / "legacy.json"
        input_file.write_text(json.dumps(sample_json_config))
        output_file = tmp_path / "network.toml"
        keys_file = tmp_path / "keys.json"

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "migrate",
                "-i",
                str(input_file),
                "-o",
                str(output_file),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "✅ Validated output TOML configuration" in result.stdout

    def test_force_flag_overwrites_existing_files(
        self, tmp_path, sample_json_config
    ):
        """Test --force flag overwrites existing TOML and keys.json."""
        input_file = tmp_path / "legacy.json"
        input_file.write_text(json.dumps(sample_json_config))
        output_file = tmp_path / "network.toml"
        keys_file = tmp_path / "keys.json"

        # Create existing files
        output_file.write_text("existing toml")
        keys_file.write_text("existing keys")

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "migrate",
                "-i",
                str(input_file),
                "-o",
                str(output_file),
                "-k",
                str(keys_file),
                "--force",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert output_file.read_text() != "existing toml"
        assert keys_file.read_text() != "existing keys"

    def test_without_force_existing_files_cause_error(
        self, tmp_path, sample_json_config
    ):
        """Test that without --force, existing files cause error."""
        input_file = tmp_path / "legacy.json"
        input_file.write_text(json.dumps(sample_json_config))
        output_file = tmp_path / "network.toml"
        keys_file = tmp_path / "keys.json"

        # Create existing files
        output_file.write_text("existing")
        keys_file.write_text("existing")

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "migrate",
                "-i",
                str(input_file),
                "-o",
                str(output_file),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "already exist" in result.stderr.lower() or "--force" in result.stderr

    def test_keys_json_has_0600_permissions(self, tmp_path, sample_json_config):
        """Test that keys.json has 0600 permissions."""
        input_file = tmp_path / "legacy.json"
        input_file.write_text(json.dumps(sample_json_config))
        output_file = tmp_path / "network.toml"
        keys_file = tmp_path / "keys.json"

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "migrate",
                "-i",
                str(input_file),
                "-o",
                str(output_file),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert keys_file.exists()

        # Check permissions (0600 = owner read/write only)
        file_mode = os.stat(keys_file).st_mode & 0o777
        assert file_mode == 0o600
