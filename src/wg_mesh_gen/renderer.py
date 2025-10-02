"""Jinja2 template rendering for WireGuard configurations.

This module provides functions to render WireGuard server and client
configurations using Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template

from wg_mesh_gen.models import ClientConfig, CommonConfig, ServerConfig

# Get templates directory (relative to this file)
TEMPLATES_DIR = Path(__file__).parent / "templates"


def get_jinja_env() -> Environment:
    """Get configured Jinja2 environment.

    Returns:
        Jinja2 Environment with FileSystemLoader for templates directory
    """
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_server_config(
    server_or_common: dict[str, Any] | CommonConfig | ServerConfig,
    clients_or_server: list[dict[str, Any]] | list[ClientConfig] | ServerConfig = None,
    keys_or_clients: dict[str, Any] | list[ClientConfig] = None,
    network_name_or_keys: str | dict[str, Any] = None,
) -> str:
    """Render WireGuard server configuration.

    Supports two calling conventions:
    1. Dict-based (for tests): render_server_config(server_dict, clients_list, keys, network_name)
    2. Typed (for CLI): render_server_config(common, server, clients, keys)

    Returns:
        Rendered server configuration string
    """
    # Detect calling convention
    if isinstance(server_or_common, dict):
        # Dict-based interface: (server_dict, clients_list, keys, network_name)
        server = server_or_common
        clients = clients_or_server
        keys = keys_or_clients
        network_name = network_name_or_keys

        env = get_jinja_env()
        template = env.get_template("server.conf.j2")

        # Prepare client data for template
        client_data = []
        for client in clients:
            client_name = client["name"]
            client_keys = keys["clients"][client_name]
            client_data.append(
                {
                    "name": client_name,
                    "public_key": client_keys["public_key"],
                    "preshared_key": client_keys["preshared_key"],
                    "vlan_ipv4_addr": client["vlan_ipv4_addr"],
                }
            )

        return template.render(
            network_name=network_name,
            server={
                "vlan_ipv4_addr": server["vlan_ipv4_addr"],
                "port": server["port"],
                "private_key": keys["server"]["private_key"],
                "interface": server["interface"],
            },
            clients=client_data,
        )
    else:
        # Typed interface: (common, server, clients, keys)
        common = server_or_common
        server = clients_or_server
        clients = keys_or_clients
        keys = network_name_or_keys

        env = get_jinja_env()
        template = env.get_template("server.conf.j2")

        # Prepare client data for template
        client_data = []
        for client in clients:
            client_keys = keys["clients"][client.name]
            client_data.append(
                {
                    "name": client.name,
                    "public_key": client_keys["public_key"],
                    "preshared_key": client_keys["preshared_key"],
                    "vlan_ipv4_addr": client.vlan_ipv4_addr,
                }
            )

        return template.render(
            network_name=common.network_name,
            server={
                "vlan_ipv4_addr": server.vlan_ipv4_addr,
                "port": server.port,
                "private_key": keys["server"]["private_key"],
                "interface": server.interface,
            },
            clients=client_data,
        )


def render_client_config(
    client_or_common: dict[str, Any] | CommonConfig | ClientConfig,
    server_or_server: dict[str, Any] | ServerConfig = None,
    keys_or_client: dict[str, Any] | ClientConfig = None,
    allowed_ips_or_keys: str | dict[str, Any] = None,
    mode: str = None,
) -> str:
    """Render WireGuard client configuration.

    Supports two calling conventions:
    1. Dict-based (for tests): render_client_config(client_dict, server_dict, keys, allowed_ips)
    2. Typed (for CLI): render_client_config(common, server, client, keys, mode)

    Returns:
        Rendered client configuration string
    """
    env = get_jinja_env()
    template = env.get_template("client.conf.j2")

    # Detect calling convention
    if isinstance(client_or_common, dict):
        # Dict-based interface: (client_dict, server_dict, keys, allowed_ips)
        client = client_or_common
        server = server_or_server
        keys = keys_or_client
        allowed_ips = allowed_ips_or_keys

        client_name = client["name"]
        client_keys = keys["clients"][client_name]

        return template.render(
            client={
                "private_key": client_keys["private_key"],
                "vlan_ipv4_addr": client["vlan_ipv4_addr"],
                "dns1": client.get("dns1"),
                "dns2": client.get("dns2"),
                "preshared_key": client_keys["preshared_key"],
            },
            server={
                "name": server["name"],
                "public_key": keys["server"]["public_key"],
                "endpoint": server["endpoint"],
                "port": server["port"],
            },
            allowed_ips=allowed_ips,
        )
    else:
        # Typed interface: (common, server, client, keys, mode)
        common = client_or_common
        server = server_or_server
        client = keys_or_client
        keys = allowed_ips_or_keys

        if mode not in ("global", "local"):
            raise ValueError(f"Invalid mode '{mode}', must be 'global' or 'local'")

        # Determine AllowedIPs based on mode
        allowed_ips = "0.0.0.0/0" if mode == "global" else common.network_ipv4_addr

        client_keys = keys["clients"][client.name]

        return template.render(
            client={
                "private_key": client_keys["private_key"],
                "vlan_ipv4_addr": client.vlan_ipv4_addr,
                "dns1": client.dns1,
                "dns2": client.dns2,
                "preshared_key": client_keys["preshared_key"],
            },
            server={
                "name": server.name,
                "public_key": keys["server"]["public_key"],
                "endpoint": server.endpoint,
                "port": server.port,
            },
            allowed_ips=allowed_ips,
        )


def generate_config_filename(
    network_name: str,
    node_type: str,
    node_name: str,
    mode: str | None = None,
) -> str:
    """Generate WireGuard configuration filename.

    Args:
        network_name: Network name from common config
        node_type: "server" or "client"
        node_name: Name of the server/client
        mode: Optional "global" or "local" for client configs

    Returns:
        Filename string (e.g., "wg-my-network-server-vpn-server.conf")

    Examples:
        >>> generate_config_filename("my-vpn", "server", "main-server")
        'wg-my-vpn-server-main-server.conf'

        >>> generate_config_filename("my-vpn", "client", "laptop", "global")
        'wg-my-vpn-client-laptop-global.conf'
    """
    if node_type == "server":
        return f"wg-{network_name}-server-{node_name}.conf"
    elif node_type == "client" and mode:
        return f"wg-{network_name}-client-{node_name}-{mode}.conf"
    else:
        raise ValueError(
            f"Invalid node_type '{node_type}' or missing mode for client"
        )
