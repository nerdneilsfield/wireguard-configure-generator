"""Shared pytest fixtures for all tests."""

import pytest


@pytest.fixture
def sample_toml_config():
    """Sample TOML configuration for testing."""
    return """
[common]
network_name = "test-vpn"
network_ipv4_addr = "10.0.0.0/24"

[server]
name = "vpn-server"
endpoint = "vpn.example.com"
vlan_ipv4_addr = "10.0.0.1"
port = 51820
interface = "eth0"

[[clients]]
name = "laptop"
vlan_ipv4_addr = "10.0.0.2"
port = 51821
dns1 = "1.1.1.1"
dns2 = "8.8.8.8"
gen_global = true
gen_local = false

[[clients]]
name = "phone"
vlan_ipv4_addr = "10.0.0.3"
port = 51822
gen_global = false
gen_local = true
"""


@pytest.fixture
def sample_toml_dict():
    """Sample TOML configuration as dictionary."""
    return {
        "common": {
            "network_name": "test-vpn",
            "network_ipv4_addr": "10.0.0.0/24",
        },
        "server": {
            "name": "vpn-server",
            "endpoint": "vpn.example.com",
            "vlan_ipv4_addr": "10.0.0.1",
            "port": 51820,
            "interface": "eth0",
        },
        "clients": [
            {
                "name": "laptop",
                "vlan_ipv4_addr": "10.0.0.2",
                "port": 51821,
                "dns1": "1.1.1.1",
                "dns2": "8.8.8.8",
                "gen_global": True,
                "gen_local": False,
            },
            {
                "name": "phone",
                "vlan_ipv4_addr": "10.0.0.3",
                "port": 51822,
                "gen_global": False,
                "gen_local": True,
            },
        ],
    }


@pytest.fixture
def sample_json_config():
    """Sample JSON configuration for migration testing."""
    return {
        "common": {
            "network_name": "old-vpn",
            "network_ipv4_addr": "10.1.0.0/24",
        },
        "server": {
            "name": "vpn-hub",
            "ipv4_addr": "hub.example.com",
            "vlan_ipv4_addr": "10.1.0.1",
            "port": 51820,
            "interface": "eth0",
            "prvkey": "EMBEDDED_PRIVATE_KEY_BASE64_44CHARS_XXXXXXXXXXXX",
            "pubkey": "EMBEDDED_PUBLIC_KEY_BASE64_44CHARS_XXXXXXXXXXXXX",
            "psk": "EMBEDDED_PSK_BASE64_44CHARS_XXXXXXXXXXXXXXXX",
        },
        "clients": [
            {
                "name": "spoke1",
                "vlan_ipv4_addr": "10.1.0.2",
                "port": 51821,
                "dns1": "1.1.1.1",
                "gen_global": True,
                "gen_local": False,
                "prvkey": "CLIENT_PRIVATE_KEY_BASE64_44CHARS_XXXXXXXXXXXXX",
                "pubkey": "CLIENT_PUBLIC_KEY_BASE64_44CHARS_XXXXXXXXXXXXXX",
                "psk": "CLIENT_PSK_BASE64_44CHARS_XXXXXXXXXXXXXXXX",
            }
        ],
    }


@pytest.fixture
def sample_keys():
    """Sample keys JSON structure."""
    # Valid base64 encoded 32-byte keys (real format)
    import base64
    return {
        "version": "1.0",
        "server": {
            "private_key": base64.b64encode(b"a" * 32).decode("ascii"),
            "public_key": base64.b64encode(b"b" * 32).decode("ascii"),
            "preshared_key": base64.b64encode(b"c" * 32).decode("ascii"),
        },
        "clients": {
            "laptop": {
                "private_key": base64.b64encode(b"d" * 32).decode("ascii"),
                "public_key": base64.b64encode(b"e" * 32).decode("ascii"),
                "preshared_key": base64.b64encode(b"f" * 32).decode("ascii"),
            },
            "phone": {
                "private_key": base64.b64encode(b"g" * 32).decode("ascii"),
                "public_key": base64.b64encode(b"h" * 32).decode("ascii"),
                "preshared_key": base64.b64encode(b"i" * 32).decode("ascii"),
            },
        },
    }


@pytest.fixture
def sample_server_config():
    """Sample server configuration for rendering tests."""
    return {
        "server": {
            "name": "vpn-server",
            "endpoint": "vpn.example.com",
            "vlan_ipv4_addr": "10.0.0.1",
            "port": 51820,
            "interface": "eth0",
        },
        "clients": [
            {"name": "laptop", "vlan_ipv4_addr": "10.0.0.2"},
            {"name": "phone", "vlan_ipv4_addr": "10.0.0.3"},
        ],
        "keys": {
            "server": {
                "private_key": "server_priv",
                "public_key": "server_pub",
                "preshared_key": "server_psk",
            },
            "clients": {
                "laptop": {
                    "private_key": "laptop_priv",
                    "public_key": "laptop_pub",
                    "preshared_key": "laptop_psk",
                },
                "phone": {
                    "private_key": "phone_priv",
                    "public_key": "phone_pub",
                    "preshared_key": "phone_psk",
                },
            },
        },
    }


@pytest.fixture
def sample_client_config():
    """Sample client configuration for rendering tests."""
    return {
        "client": {
            "name": "laptop",
            "vlan_ipv4_addr": "10.0.0.2",
            "dns1": "1.1.1.1",
            "dns2": "8.8.8.8",
        },
        "server": {
            "name": "vpn-server",
            "endpoint": "vpn.example.com",
            "port": 51820,
        },
        "keys": {
            "server": {
                "public_key": "server_pub",
            },
            "clients": {
                "laptop": {
                    "private_key": "laptop_priv",
                    "preshared_key": "laptop_psk",
                }
            },
        },
    }


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_key_generation(monkeypatch):
    """Mock key generation to return predictable values."""

    def mock_generate_private_key():
        return "a" * 44

    def mock_derive_public_key(private_key):
        return "b" * 44

    def mock_generate_preshared_key():
        return "c" * 44

    try:
        from wg_mesh_gen import key_manager

        monkeypatch.setattr(
            key_manager, "generate_private_key", mock_generate_private_key
        )
        monkeypatch.setattr(
            key_manager, "derive_public_key", mock_derive_public_key
        )
        monkeypatch.setattr(
            key_manager, "generate_preshared_key", mock_generate_preshared_key
        )
    except ImportError:
        pass  # Module not yet implemented
