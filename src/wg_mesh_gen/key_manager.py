"""WireGuard key generation and management using Python cryptography.

This module provides functions to generate, load, and save WireGuard keys
using the Curve25519 (X25519) algorithm without requiring the system 'wg' command.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519


@dataclass
class KeyPair:
    """WireGuard key pair (private, public, preshared)."""

    private_key: str  # Base64-encoded (44 chars)
    public_key: str  # Base64-encoded (44 chars)
    preshared_key: str  # Base64-encoded (44 chars)


def generate_private_key() -> str:
    """Generate a new WireGuard private key using Curve25519.

    Returns:
        Base64-encoded private key (44 characters)
    """
    private_key = x25519.X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(private_bytes).decode("ascii")


def derive_public_key(private_key_b64: str) -> str:
    """Derive public key from a private key.

    Args:
        private_key_b64: Base64-encoded private key

    Returns:
        Base64-encoded public key (44 characters)
    """
    private_bytes = base64.b64decode(private_key_b64)
    private_key = x25519.X25519PrivateKey.from_private_bytes(private_bytes)
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(public_bytes).decode("ascii")


def generate_preshared_key() -> str:
    """Generate a new WireGuard preshared key.

    Returns:
        Base64-encoded preshared key (44 characters)
    """
    preshared_bytes = os.urandom(32)
    return base64.b64encode(preshared_bytes).decode("ascii")


def generate_keypair() -> KeyPair:
    """Generate a new WireGuard key pair using Curve25519.

    Returns:
        KeyPair with base64-encoded private, public, and preshared keys

    Note:
        All keys are 32 bytes encoded as 44-character base64 strings
    """
    private_key_str = generate_private_key()
    public_key_str = derive_public_key(private_key_str)
    preshared_key_str = generate_preshared_key()

    return KeyPair(
        private_key=private_key_str,
        public_key=public_key_str,
        preshared_key=preshared_key_str,
    )


def load_keys(file_path: str | Path) -> dict[str, Any]:
    """Load keys from JSON file.

    Args:
        file_path: Path to keys.json file

    Returns:
        Dictionary with 'server' and 'clients' keys

    Raises:
        FileNotFoundError: If the file does not exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    path = Path(file_path)
    with path.open("r") as f:
        return json.load(f)


def save_keys(keys: dict[str, Any], file_path: str | Path) -> None:
    """Save keys to JSON file with 0600 permissions.

    Args:
        keys: Dictionary with 'server' and 'clients' keys
        file_path: Path to save keys.json

    Note:
        File permissions are set to 0600 (owner read/write only) for security
    """
    path = Path(file_path)
    with path.open("w") as f:
        json.dump(keys, f, indent=2)
    # Set restrictive permissions (owner read/write only)
    path.chmod(0o600)


# Alias for backward compatibility with tests
def save_keys_to_json(keys: dict[str, Any], file_path: str | Path) -> None:
    """Alias for save_keys(). Save keys to JSON file with 0600 permissions."""
    save_keys(keys, file_path)


# Alias for backward compatibility with tests
def load_keys_from_json(file_path: str | Path) -> dict[str, Any]:
    """Alias for load_keys(). Load keys from JSON file."""
    return load_keys(file_path)


def generate_all_keys(
    server_name: str,
    client_names: list[str],
    existing_keys: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate keys for server and all clients, preserving existing keys.

    Args:
        server_name: Name of the server
        client_names: List of client names
        existing_keys: Optional existing keys to preserve (from keys.json)

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

    Note:
        If existing_keys is provided, existing keys are reused.
        Only new nodes get new keys generated.
    """
    keys: dict[str, Any] = {
        "version": "1.0",
        "server": {},
        "clients": {},
    }

    # Preserve or generate server keys
    if existing_keys and "server" in existing_keys:
        keys["server"] = existing_keys["server"]
    else:
        server_keys = generate_keypair()
        keys["server"] = {
            "private_key": server_keys.private_key,
            "public_key": server_keys.public_key,
            "preshared_key": server_keys.preshared_key,
        }

    # Preserve or generate client keys
    for client_name in client_names:
        if (
            existing_keys
            and "clients" in existing_keys
            and client_name in existing_keys["clients"]
        ):
            keys["clients"][client_name] = existing_keys["clients"][client_name]
        else:
            client_keys = generate_keypair()
            keys["clients"][client_name] = {
                "private_key": client_keys.private_key,
                "public_key": client_keys.public_key,
                "preshared_key": client_keys.preshared_key,
            }

    return keys


def validate_key_format(key: str) -> bool:
    """Validate that a key is a valid 44-character base64 string.

    Args:
        key: Base64-encoded key string

    Returns:
        True if valid, False otherwise
    """
    if len(key) != 44:
        return False
    try:
        decoded = base64.b64decode(key)
        return len(decoded) == 32
    except Exception:
        return False
