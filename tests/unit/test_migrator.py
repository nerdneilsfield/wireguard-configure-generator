"""Unit tests for migrator module."""

import pytest

from wg_mesh_gen import migrator


class TestJsonToTomlMigration:
    """Test JSON to TOML migration."""

    def test_migrate_json_to_toml_preserves_fields(self, sample_json_config):
        """Test that migrate_json_to_toml() preserves all fields."""
        result = migrator.migrate_json_to_toml(sample_json_config)

        assert result["common"] == sample_json_config["common"]
        assert result["server"]["name"] == sample_json_config["server"]["name"]
        assert len(result["clients"]) == len(sample_json_config["clients"])

    def test_migrate_removes_embedded_keys(self, sample_json_config):
        """Test that migration removes embedded keys from TOML."""
        result = migrator.migrate_json_to_toml(sample_json_config)

        assert "prvkey" not in result["server"]
        assert "pubkey" not in result["server"]
        assert "psk" not in result["server"]

        for client in result["clients"]:
            assert "prvkey" not in client
            assert "pubkey" not in client
            assert "psk" not in client

    def test_migrate_handles_legacy_ipv4_addr_field(self):
        """Test that migration handles legacy ipv4_addr field."""
        json_config = {
            "common": {"network_name": "test", "network_ipv4_addr": "10.0.0.0/24"},
            "server": {
                "name": "srv",
                "ipv4_addr": "1.2.3.4",  # Legacy field
                "vlan_ipv4_addr": "10.0.0.1",
                "port": 51820,
                "interface": "eth0",
            },
            "clients": [],
        }

        result = migrator.migrate_json_to_toml(json_config)

        # Should convert to 'endpoint'
        assert result["server"]["endpoint"] == "1.2.3.4"
        assert "ipv4_addr" not in result["server"]


class TestKeyExtraction:
    """Test key extraction from JSON."""

    def test_extract_keys_from_json(self, sample_json_config):
        """Test that extract_keys_from_json() extracts to correct structure."""
        result = migrator.extract_keys_from_json(sample_json_config)

        assert "version" in result
        assert "server" in result
        assert "clients" in result

        # Check server keys
        assert result["server"]["private_key"] == sample_json_config["server"]["prvkey"]
        assert result["server"]["public_key"] == sample_json_config["server"]["pubkey"]
        assert result["server"]["preshared_key"] == sample_json_config["server"]["psk"]

    def test_extract_keys_handles_client_keys(self, sample_json_config):
        """Test that client keys are extracted correctly."""
        result = migrator.extract_keys_from_json(sample_json_config)

        for client in sample_json_config["clients"]:
            client_name = client["name"]
            assert client_name in result["clients"]
            assert (
                result["clients"][client_name]["private_key"] == client["prvkey"]
            )
            assert result["clients"][client_name]["public_key"] == client["pubkey"]
            assert (
                result["clients"][client_name]["preshared_key"] == client["psk"]
            )

    def test_extract_keys_handles_missing_keys(self):
        """Test that extraction handles missing embedded keys."""
        json_config = {
            "common": {"network_name": "test"},
            "server": {"name": "srv"},  # No keys
            "clients": [],
        }

        result = migrator.extract_keys_from_json(json_config)

        assert result["server"]["private_key"] is None
        assert result["server"]["public_key"] is None
        assert result["server"]["preshared_key"] is None
