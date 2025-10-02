"""Integration test for validation error handling (Scenario 5 from quickstart.md)."""

import subprocess
from pathlib import Path

import pytest


def test_validation_error_handling(tmp_path):
    """Test comprehensive error handling for invalid configurations (Scenario 5)."""
    # Invalid config with multiple errors
    invalid_config = """
[common]
network_name = "invalid"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "server1"
endpoint = "vpn.example.com"
vlan_ipv4_addr = "10.0.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "client1"
vlan_ipv4_addr = "10.0.0.2"
port = 70000
gen_global = true
gen_local = false

[[clients]]
name = "client1"
vlan_ipv4_addr = "10.0.0.2"
port = 51821
gen_global = false
gen_local = false
"""

    config_file = tmp_path / "invalid-network.toml"
    config_file.write_text(invalid_config)

    # Validation should fail
    result = subprocess.run(
        ["uv", "run", "wg-mesh-gen", "validate", "-c", str(config_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "❌" in result.stderr or "Error" in result.stderr or "error" in result.stderr.lower()

    # Generation should also fail
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
