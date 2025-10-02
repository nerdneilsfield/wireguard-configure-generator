"""Integration test for key preservation (Scenario 4 from quickstart.md)."""

import json
import subprocess
from pathlib import Path

import pytest


def test_key_preservation_on_regeneration(tmp_path, sample_toml_config):
    """Test that existing keys are preserved when adding new clients (Scenario 4)."""
    # Step 1: Initial generation
    config_file = tmp_path / "network.toml"
    config_file.write_text(sample_toml_config)
    output_dir = tmp_path / "output"
    keys_file = tmp_path / "keys.json"

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

    # Step 2: Add new client to config
    updated_config = sample_toml_config + """
[[clients]]
name = "tablet"
vlan_ipv4_addr = "10.0.0.4"
port = 51823
gen_global = true
gen_local = true
"""
    config_file.write_text(updated_config)

    # Step 3: Regenerate
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

    # Step 4: Verify existing keys preserved
    new_keys = json.loads(keys_file.read_text())

    # Server keys should be identical
    assert new_keys["server"] == original_keys["server"]

    # Original client keys should be identical
    for client_name in original_keys["clients"]:
        assert new_keys["clients"][client_name] == original_keys["clients"][client_name]

    # New client should have keys
    assert "tablet" in new_keys["clients"]
    assert "tablet" not in original_keys["clients"]
