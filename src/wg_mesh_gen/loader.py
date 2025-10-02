"""Configuration file loader for TOML and JSON formats.

This module provides functions to load and parse configuration files
in both TOML (new format) and JSON (legacy format).
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from wg_mesh_gen.models import ClientConfig, CommonConfig, ServerConfig


def load_toml(file_path: str | Path) -> dict[str, Any]:
    """Load and parse a TOML configuration file.

    Args:
        file_path: Path to the TOML file

    Returns:
        Dictionary containing the parsed configuration

    Raises:
        FileNotFoundError: If the file does not exist
        tomllib.TOMLDecodeError: If the TOML syntax is invalid
    """
    path = Path(file_path)
    with path.open("rb") as f:
        return tomllib.load(f)


def load_json(file_path: str | Path) -> dict[str, Any]:
    """Load and parse a JSON configuration file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary containing the parsed configuration

    Raises:
        FileNotFoundError: If the file does not exist
        json.JSONDecodeError: If the JSON syntax is invalid
    """
    path = Path(file_path)
    with path.open("r") as f:
        return json.load(f)


def write_toml(data: dict[str, Any], file_path: str | Path) -> None:
    """Write configuration to a TOML file.

    Args:
        data: Configuration dictionary to write
        file_path: Path to the TOML file

    Raises:
        TypeError: If data cannot be serialized to TOML
    """
    path = Path(file_path)
    with path.open("wb") as f:
        tomli_w.dump(data, f)


def parse_common_config(data: dict[str, Any]) -> CommonConfig:
    """Parse common configuration from loaded data.

    Args:
        data: Configuration dictionary with 'common' key

    Returns:
        CommonConfig instance

    Raises:
        KeyError: If required fields are missing
    """
    common = data["common"]
    return CommonConfig(
        network_name=common["network_name"],
        network_ipv4_addr=common["network_ipv4_addr"],
    )


def parse_server_config(data: dict[str, Any]) -> ServerConfig:
    """Parse server configuration from loaded data.

    Args:
        data: Configuration dictionary with 'server' key

    Returns:
        ServerConfig instance

    Raises:
        KeyError: If required fields are missing
    """
    server = data["server"]
    return ServerConfig(
        name=server["name"],
        endpoint=server["endpoint"],
        vlan_ipv4_addr=server["vlan_ipv4_addr"],
        port=server["port"],
        interface=server["interface"],
    )


def parse_client_configs(data: dict[str, Any]) -> list[ClientConfig]:
    """Parse client configurations from loaded data.

    Args:
        data: Configuration dictionary with 'clients' key

    Returns:
        List of ClientConfig instances

    Raises:
        KeyError: If required fields are missing
    """
    clients = []
    for client_data in data["clients"]:
        clients.append(
            ClientConfig(
                name=client_data["name"],
                vlan_ipv4_addr=client_data["vlan_ipv4_addr"],
                port=client_data["port"],
                dns1=client_data.get("dns1"),
                dns2=client_data.get("dns2"),
                gen_global=client_data.get("gen_global", True),
                gen_local=client_data.get("gen_local", True),
            )
        )
    return clients


def load_config(
    file_path: str | Path,
) -> tuple[CommonConfig, ServerConfig, list[ClientConfig]]:
    """Load and parse a TOML configuration file into typed models.

    Args:
        file_path: Path to the TOML configuration file

    Returns:
        Tuple of (CommonConfig, ServerConfig, list[ClientConfig])

    Raises:
        FileNotFoundError: If the file does not exist
        tomllib.TOMLDecodeError: If the TOML syntax is invalid
        KeyError: If required fields are missing
    """
    data = load_toml(file_path)
    return (
        parse_common_config(data),
        parse_server_config(data),
        parse_client_configs(data),
    )
