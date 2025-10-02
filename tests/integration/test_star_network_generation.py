"""Integration test for star network generation (Scenario 1 from quickstart.md)."""

import json
import subprocess
from pathlib import Path

import pytest


def test_generate_star_network_end_to_end(tmp_path, sample_toml_config):
    """Test complete workflow: validate → generate → verify files.

    This implements Scenario 1 from quickstart.md.
    """
    # Step 1: Create TOML config
    config_file = tmp_path / "star-network.toml"
    config_file.write_text(sample_toml_config)

    # Step 2: Validate configuration
    result = subprocess.run(
        ["uv", "run", "wg-mesh-gen", "validate", "-c", str(config_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Step 3: Generate configurations
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

    # Step 4: Verify generated files
    assert output_dir.exists()
    assert keys_file.exists()

    # Check server config
    server_configs = list(output_dir.glob("wg-*-server-*.conf"))
    assert len(server_configs) == 1

    # Check client configs
    client_configs = list(output_dir.glob("wg-*-client-*.conf"))
    assert len(client_configs) >= 1

    # Verify keys structure
    keys = json.loads(keys_file.read_text())
    assert "server" in keys
    assert "clients" in keys
