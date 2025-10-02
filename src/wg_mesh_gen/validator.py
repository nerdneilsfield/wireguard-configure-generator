"""Configuration validation using JSON Schema and business logic.

This module provides validation for WireGuard configurations including:
- JSON Schema validation for structure
- Business logic validation for uniqueness and subnet rules
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any

import jsonschema

from wg_mesh_gen.models import ClientConfig, CommonConfig, ServerConfig

# JSON Schema for TOML configuration structure
NETWORK_CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["common", "server", "clients"],
    "properties": {
        "common": {
            "type": "object",
            "required": ["network_name", "network_ipv4_addr"],
            "properties": {
                "network_name": {"type": "string", "minLength": 1},
                "network_ipv4_addr": {
                    "type": "string",
                    "pattern": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$",
                },
            },
        },
        "server": {
            "type": "object",
            "required": ["name", "endpoint", "vlan_ipv4_addr", "port", "interface"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "endpoint": {
                    "type": "string",
                    "description": "IPv4, IPv6, or hostname for clients to connect",
                },
                "vlan_ipv4_addr": {"type": "string"},
                "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                "interface": {"type": "string", "minLength": 1},
            },
        },
        "clients": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "vlan_ipv4_addr", "port"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "vlan_ipv4_addr": {"type": "string"},
                    "port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                    "dns1": {"type": "string"},
                    "dns2": {"type": "string"},
                    "gen_global": {"type": "boolean"},
                    "gen_local": {"type": "boolean"},
                },
            },
        },
    },
}


class ValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


def validate_schema(data: dict[str, Any]) -> None:
    """Validate configuration against JSON Schema.

    Args:
        data: Configuration dictionary to validate

    Raises:
        ValidationError: If schema validation fails
    """
    try:
        jsonschema.validate(instance=data, schema=NETWORK_CONFIG_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"Schema validation failed: {e.message}") from e


def validate_ipv4(ip_str: str) -> None:
    """Validate IPv4 address format.

    Args:
        ip_str: IPv4 address string

    Raises:
        ValidationError: If not a valid IPv4 address
    """
    try:
        ipaddress.IPv4Address(ip_str)
    except ValueError as e:
        raise ValidationError(f"Invalid IPv4 address '{ip_str}': {e}") from e


def validate_ipv4_network(network_str: str) -> ipaddress.IPv4Network:
    """Validate IPv4 network CIDR format.

    Args:
        network_str: IPv4 network in CIDR notation (e.g., "10.0.0.0/24")

    Returns:
        IPv4Network object

    Raises:
        ValidationError: If not a valid IPv4 network
    """
    try:
        return ipaddress.IPv4Network(network_str, strict=False)
    except ValueError as e:
        raise ValidationError(f"Invalid IPv4 network '{network_str}': {e}") from e


def validate_business_logic(
    common_or_config: CommonConfig | dict[str, Any],
    server: ServerConfig = None,
    clients: list[ClientConfig] = None,
) -> None:
    """Validate business logic rules.

    Supports two calling conventions:
    1. Dict-based (for tests): validate_business_logic(config_dict)
    2. Typed: validate_business_logic(common, server, clients)

    Rules checked:
    1. Unique client names
    2. Unique client IPs
    3. All IPs within network subnet
    4. Each client has at least one output mode (gen_global or gen_local)

    Raises:
        ValidationError or ValueError: If any business rule is violated
    """
    # Detect calling convention
    if isinstance(common_or_config, dict):
        # Dict-based interface: parse the dict first
        from wg_mesh_gen import loader

        config = common_or_config
        common = loader.parse_common_config(config)
        server = loader.parse_server_config(config)
        clients = loader.parse_client_configs(config)

    else:
        # Typed interface
        common = common_or_config

    # Validate network CIDR
    network = validate_ipv4_network(common.network_ipv4_addr)

    # Determine which exception type to raise (ValueError for dict mode, ValidationError for typed mode)
    is_dict_mode = isinstance(common_or_config, dict)
    ErrorClass = ValueError if is_dict_mode else ValidationError

    # Rule 1: Unique client names
    names = [c.name for c in clients]
    if len(names) != len(set(names)):
        duplicates = [name for name in names if names.count(name) > 1]
        raise ErrorClass(f"Duplicate client names: {set(duplicates)}")

    # Rule 2: Unique client IPs
    client_ips = [c.vlan_ipv4_addr for c in clients]
    if len(client_ips) != len(set(client_ips)):
        duplicates = [ip for ip in client_ips if client_ips.count(ip) > 1]
        raise ErrorClass(f"Duplicate client IPs: {set(duplicates)}")

    # Rule 3: All IPs within network subnet
    # Validate server IP
    validate_ipv4(server.vlan_ipv4_addr)
    server_ip = ipaddress.IPv4Address(server.vlan_ipv4_addr)
    if server_ip not in network:
        raise ErrorClass(
            f"Server IP {server.vlan_ipv4_addr} outside network subnet {common.network_ipv4_addr}"
        )

    # Validate client IPs
    for client in clients:
        validate_ipv4(client.vlan_ipv4_addr)
        client_ip = ipaddress.IPv4Address(client.vlan_ipv4_addr)
        if client_ip not in network:
            raise ErrorClass(
                f"Client '{client.name}' IP {client.vlan_ipv4_addr} outside network subnet {common.network_ipv4_addr}"
            )

    # Rule 4: At least one output mode per client
    for client in clients:
        if not client.gen_global and not client.gen_local:
            raise ErrorClass(
                f"Client '{client.name}' must have gen_global=true OR gen_local=true"
            )

    # Validate DNS if provided
    for client in clients:
        if client.dns1:
            validate_ipv4(client.dns1)
        if client.dns2:
            validate_ipv4(client.dns2)


def validate_toml_config(data: dict[str, Any]) -> None:
    """Validate TOML configuration dictionary (schema + business logic).

    Args:
        data: Configuration dictionary from TOML file

    Raises:
        jsonschema.ValidationError: If schema validation fails
        ValidationError: If business logic validation fails
    """
    # Schema validation (raises jsonschema.ValidationError)
    jsonschema.validate(instance=data, schema=NETWORK_CONFIG_SCHEMA)

    # Business logic validation
    # Parse the dictionary into models
    from wg_mesh_gen import loader

    common = loader.parse_common_config(data)
    server = loader.parse_server_config(data)
    clients = loader.parse_client_configs(data)

    validate_business_logic(common, server, clients)


def validate_config(
    common: CommonConfig,
    server: ServerConfig,
    clients: list[ClientConfig],
) -> None:
    """Validate complete configuration (schema + business logic).

    Args:
        common: Common configuration
        server: Server configuration
        clients: List of client configurations

    Raises:
        ValidationError: If validation fails
    """
    # Business logic validation
    validate_business_logic(common, server, clients)
