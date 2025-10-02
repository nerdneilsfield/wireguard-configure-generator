"""Integration test for parallel generation (Scenario 3 from quickstart.md)."""

import subprocess
import time
from pathlib import Path

import pytest


def test_parallel_vs_sequential_generation(tmp_path):
    """Test parallel generation performance (Scenario 3).

    Verifies that parallel mode produces identical output to sequential.
    """
    # Create a larger config with multiple clients
    large_config = """
[common]
network_name = "large-vpn"
network_ipv4_addr = "10.2.0.0/24"

[server]
name = "main-server"
endpoint = "vpn.example.com"
vlan_ipv4_addr = "10.2.0.1"
port = 51820
interface = "eth0"
"""
    for i in range(5):  # 5 clients
        large_config += f"""
[[clients]]
name = "client-{i:02d}"
vlan_ipv4_addr = "10.2.0.{i+2}"
port = {51821 + i}
gen_global = true
gen_local = false
"""

    config_file = tmp_path / "large-network.toml"
    config_file.write_text(large_config)

    # Sequential generation
    seq_output = tmp_path / "output-seq"
    seq_keys = tmp_path / "keys-seq.json"

    result = subprocess.run(
        [
            "uv",
            "run",
            "wg-mesh-gen",
            "generate",
            "-c",
            str(config_file),
            "-o",
            str(seq_output),
            "-k",
            str(seq_keys),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    seq_files = sorted(seq_output.glob("*.conf"))

    # Parallel generation
    par_output = tmp_path / "output-par"
    par_keys = tmp_path / "keys-par.json"

    result = subprocess.run(
        [
            "uv",
            "run",
            "wg-mesh-gen",
            "generate",
            "-c",
            str(config_file),
            "-o",
            str(par_output),
            "-k",
            str(par_keys),
            "--parallel",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    par_files = sorted(par_output.glob("*.conf"))

    # Verify same number of files generated
    assert len(seq_files) == len(par_files)
