"""Integration test for JSON-to-TOML migration (Scenario 2 from quickstart.md)."""

import json
import subprocess
from pathlib import Path

import pytest


def test_migrate_json_to_toml_workflow(tmp_path, sample_json_config):
    """Test migration workflow: JSON → TOML + keys.json → generate.

    This implements Scenario 2 from quickstart.md.
    """
    # Step 1: Create legacy JSON config
    input_file = tmp_path / "legacy-config.json"
    input_file.write_text(json.dumps(sample_json_config))

    # Step 2: Migrate to TOML
    output_file = tmp_path / "migrated-config.toml"
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

    # Step 3: Verify migrated TOML
    assert output_file.exists()
    assert keys_file.exists()

    # Verify keys extracted
    keys = json.loads(keys_file.read_text())
    assert "server" in keys
    assert keys["server"]["private_key"] == sample_json_config["server"]["prvkey"]

    # Step 4: Generate from migrated config
    gen_output_dir = tmp_path / "output-migrated"

    result = subprocess.run(
        [
            "uv",
            "run",
            "wg-mesh-gen",
            "generate",
            "-c",
            str(output_file),
            "-o",
            str(gen_output_dir),
            "-k",
            str(keys_file),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert gen_output_dir.exists()
