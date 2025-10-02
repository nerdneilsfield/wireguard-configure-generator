"""Data models for WireGuard configuration generator.

This module defines the data structures used for:
- Configuration input (CommonConfig, ServerConfig, ClientConfig)
- Rendered output (RenderedServerConfig, RenderedClientConfig)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CommonConfig:
    """Common network settings."""

    network_name: str  # Network identifier
    network_ipv4_addr: str  # IPv4 CIDR (e.g., "10.0.0.0/24")


@dataclass
class ServerConfig:
    """WireGuard server configuration."""

    name: str  # Server name
    endpoint: str  # Public endpoint (IPv4, IPv6, or hostname)
    vlan_ipv4_addr: str  # VPN internal IP (within network_ipv4_addr)
    port: int  # Listen port (1024-65535)
    interface: str  # Physical network interface for NAT (e.g., "eth0")


@dataclass
class ClientConfig:
    """WireGuard client configuration."""

    name: str  # Client name (unique)
    vlan_ipv4_addr: str  # VPN internal IP (unique, within network_ipv4_addr)
    port: int  # Listen port (1024-65535)
    dns1: Optional[str] = None  # Primary DNS server (IPv4)
    dns2: Optional[str] = None  # Secondary DNS server (IPv4)
    gen_global: bool = True  # Generate config with AllowedIPs = 0.0.0.0/0
    gen_local: bool = True  # Generate config with AllowedIPs = network_ipv4_addr


@dataclass
class ServerPeerConfig:
    """Client as seen by server."""

    name: str  # Client name (comment)
    public_key: str
    preshared_key: str
    allowed_ips: str  # e.g., "10.0.0.2/32"


@dataclass
class RenderedServerConfig:
    """Server WireGuard configuration."""

    interface_address: str  # e.g., "10.0.0.1/24"
    listen_port: int
    private_key: str
    post_up: str  # iptables NAT rules
    post_down: str  # iptables cleanup rules
    peers: list[ServerPeerConfig]  # One per client


@dataclass
class RenderedClientConfig:
    """Client WireGuard configuration."""

    private_key: str
    address: str  # e.g., "10.0.0.2/32"
    dns: str  # e.g., "10.15.44.11,114.114.114.114"
    server_public_key: str
    preshared_key: str
    endpoint: str  # e.g., "vpn.example.com:51820"
    allowed_ips: str  # "0.0.0.0/0" (global) or "10.0.0.0/24" (local)
    persistent_keepalive: int = 25  # Default: 25
