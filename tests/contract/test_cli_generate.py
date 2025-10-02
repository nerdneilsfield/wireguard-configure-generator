"""Contract tests for wg-mesh-gen generate command.

Tests the CLI interface contract for the generate command according to
specs/001-jinja2-dns-wiregurard/contracts/cli-generate.md
"""

import json
import subprocess
from pathlib import Path

import pytest


class TestGenerateCommand:
    """Test wg-mesh-gen generate command contract."""

    def test_valid_toml_generates_configs(self, tmp_path, sample_toml_config):
        """Test that valid TOML input generates server + client configs."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        output_dir = tmp_path / "output"
        keys_file = tmp_path / "keys.json"

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(output_dir),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "✅ Validated configuration" in result.stdout
        assert "✅ Generated server config" in result.stdout
        assert output_dir.exists()
        assert keys_file.exists()

        # Check server config exists
        server_configs = list(output_dir.glob("wg-*-server-*.conf"))
        assert len(server_configs) == 1

        # Check client configs exist
        client_configs = list(output_dir.glob("wg-*-client-*.conf"))
        assert len(client_configs) >= 1

    def test_validation_errors_return_exit_code_1(self, tmp_path):
        """Test that validation errors return exit code 1."""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text("[common]\nnetwork_name = 'test'")  # Missing required fields

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(tmp_path / "output"),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "❌" in result.stderr or "Error" in result.stderr

    def test_parallel_flag_works(self, tmp_path, sample_toml_config):
        """Test that --parallel flag enables parallel generation."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        output_dir = tmp_path / "output"

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(output_dir),
                "--parallel",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert output_dir.exists()

    def test_force_flag_overwrites_existing_files(
        self, tmp_path, sample_toml_config
    ):
        """Test that --force flag overwrites existing config files."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create existing file (network_name is "test-vpn", server name is "vpn-server")
        existing_file = output_dir / "wg-test-vpn-server-vpn-server.conf"
        existing_file.write_text("existing content")

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(output_dir),
                "--force",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert existing_file.read_text() != "existing content"

    def test_keys_flag_specifies_custom_path(self, tmp_path, sample_toml_config):
        """Test that -k/--keys flag specifies custom key storage path."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        output_dir = tmp_path / "output"
        custom_keys = tmp_path / "custom_keys.json"

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(output_dir),
                "-k",
                str(custom_keys),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert custom_keys.exists()

    def test_key_reuse_on_regeneration(self, tmp_path, sample_toml_config):
        """Test that existing keys are preserved on regeneration."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        output_dir = tmp_path / "output"
        keys_file = tmp_path / "keys.json"

        # First generation
        subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(output_dir),
                "-k",
                str(keys_file),
            ],
            check=True,
        )

        original_keys = json.loads(keys_file.read_text())

        # Second generation
        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(output_dir),
                "-k",
                str(keys_file),
                "--force",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        new_keys = json.loads(keys_file.read_text())
        assert original_keys == new_keys  # Keys should be reused

    def test_refresh_force_regenerates_all_keys(self, tmp_path, sample_toml_config):
        """Test that --refresh-force regenerates all keys."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        output_dir = tmp_path / "output"
        keys_file = tmp_path / "keys.json"

        # First generation
        subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(output_dir),
                "-k",
                str(keys_file),
            ],
            check=True,
        )

        original_keys = json.loads(keys_file.read_text())

        # Regenerate with --refresh-force
        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(output_dir),
                "-k",
                str(keys_file),
                "--refresh-force",
                "--force",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "⚠️  --refresh-force" in result.stdout
        new_keys = json.loads(keys_file.read_text())
        assert original_keys != new_keys  # Keys should be different

    def test_missing_keys_json_created_automatically(
        self, tmp_path, sample_toml_config
    ):
        """Test that missing keys.json is created automatically."""
        config_file = tmp_path / "network.toml"
        config_file.write_text(sample_toml_config)
        output_dir = tmp_path / "output"
        keys_file = tmp_path / "keys.json"

        assert not keys_file.exists()

        result = subprocess.run(
            [
                "uv",
                "run",
                "wg-mesh-gen",
                "generate",
                "-c",
                str(config_file),
                "-o",
                str(output_dir),
                "-k",
                str(keys_file),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert keys_file.exists()
        assert "✅ Saved keys to" in result.stdout
