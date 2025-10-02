"""JSON-to-TOML migration for legacy configurations.

This module provides functions to migrate legacy JSON configurations
to the new TOML format with separate key storage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import tomli_w

from wg_mesh_gen.loader import load_json


def extract_keys_from_json(json_config: dict[str, Any]) -> dict[str, Any]:
    """Extract embedded keys from legacy JSON config to separate storage.

    Args:
        json_config: Legacy JSON configuration with embedded keys

    Returns:
        Dictionary with structure:
        {
            "version": "1.0",
            "server": {
                "private_key": "...",
                "public_key": "...",
                "preshared_key": "..."
            },
            "clients": {
                "client1": {...},
                "client2": {...}
            }
        }
    """
    keys: dict[str, Any] = {
        "version": "1.0",
        "server": {
            "private_key": json_config["server"].get("prvkey"),
            "public_key": json_config["server"].get("pubkey"),
            "preshared_key": json_config["server"].get("psk"),
        },
        "clients": {},
    }

    for client in json_config["clients"]:
        client_name = client["name"]
        keys["clients"][client_name] = {
            "private_key": client.get("prvkey"),
            "public_key": client.get("pubkey"),
            "preshared_key": client.get("psk"),
        }

    return keys


def migrate_json_to_toml(json_config: dict[str, Any]) -> dict[str, Any]:
    """Convert legacy JSON config to TOML format.

    Removes embedded keys (prvkey, pubkey, psk) from the configuration.
    Keys should be extracted separately using extract_keys_from_json().

    Args:
        json_config: Legacy JSON configuration

    Returns:
        TOML-compatible dictionary without embedded keys
    """
    # Remove embedded keys from server
    server_config = {
        k: v
        for k, v in json_config["server"].items()
        if k not in ["prvkey", "pubkey", "psk"]
    }

    # Rename ipv4_addr to endpoint for new TOML format
    if "ipv4_addr" in server_config:
        server_config["endpoint"] = server_config.pop("ipv4_addr")

    # Remove embedded keys from clients
    clients_config = [
        {k: v for k, v in client.items() if k not in ["prvkey", "pubkey", "psk"]}
        for client in json_config["clients"]
    ]

    return {
        "common": json_config["common"],
        "server": server_config,
        "clients": clients_config,
    }


def save_toml(data: dict[str, Any], file_path: str | Path) -> None:
    """Save configuration to TOML file.

    Args:
        data: Configuration dictionary
        file_path: Path to save TOML file
    """
    path = Path(file_path)
    with path.open("wb") as f:
        tomli_w.dump(data, f)


def migrate_config_file(
    input_json_path: str | Path,
    output_toml_path: str | Path,
    output_keys_path: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Migrate a legacy JSON config file to TOML + separate keys.

    Args:
        input_json_path: Path to legacy JSON config
        output_toml_path: Path to save TOML config
        output_keys_path: Path to save keys.json

    Returns:
        Tuple of (toml_config, keys_dict)

    Raises:
        FileNotFoundError: If input file does not exist
        json.JSONDecodeError: If input is not valid JSON
    """
    # Load legacy JSON
    json_config = load_json(input_json_path)

    # Extract keys
    keys = extract_keys_from_json(json_config)

    # Migrate to TOML format
    toml_config = migrate_json_to_toml(json_config)

    # Save TOML config
    save_toml(toml_config, output_toml_path)

    # Save keys (will be saved with 0600 permissions by key_manager.save_keys)
    # For now, just return them; the CLI will use key_manager.save_keys()

    return toml_config, keys
