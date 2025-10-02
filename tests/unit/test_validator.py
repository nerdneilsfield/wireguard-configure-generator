"""Unit tests for validator module."""

import pytest
from jsonschema import ValidationError

from wg_mesh_gen import validator


class TestTomlSchemaValidation:
    """Test TOML schema validation."""

    def test_valid_config_passes_schema_validation(self, sample_toml_dict):
        """Test that valid config passes schema validation."""
        # Should not raise
        validator.validate_toml_config(sample_toml_dict)

    def test_missing_required_fields_fails(self):
        """Test that missing required fields fail validation."""
        config = {"common": {"network_name": "test"}}  # Missing many fields

        with pytest.raises(ValidationError):
            validator.validate_toml_config(config)

    def test_invalid_port_range_fails(self):
        """Test that invalid port ranges fail validation."""
        config = {
            "common": {
                "network_name": "test",
                "network_ipv4_addr": "10.0.0.0/24",
            },
            "server": {
                "name": "srv",
                "endpoint": "1.2.3.4",
                "vlan_ipv4_addr": "10.0.0.1",
                "port": 70000,  # Invalid: > 65535
                "interface": "eth0",
            },
            "clients": [],
        }

        with pytest.raises(ValidationError):
            validator.validate_toml_config(config)


class TestBusinessLogicValidation:
    """Test business logic validation."""

    def test_unique_client_names_enforced(self):
        """Test that unique client names are enforced."""
        config = {
            "common": {
                "network_name": "test",
                "network_ipv4_addr": "10.0.0.0/24",
            },
            "server": {
                "name": "srv",
                "endpoint": "1.2.3.4",
                "vlan_ipv4_addr": "10.0.0.1",
                "port": 51820,
                "interface": "eth0",
            },
            "clients": [
                {
                    "name": "client1",
                    "vlan_ipv4_addr": "10.0.0.2",
                    "port": 51821,
                    "gen_global": True,
                    "gen_local": False,
                },
                {
                    "name": "client1",  # Duplicate
                    "vlan_ipv4_addr": "10.0.0.3",
                    "port": 51822,
                    "gen_global": True,
                    "gen_local": False,
                },
            ],
        }

        with pytest.raises(ValueError, match="Duplicate.*name"):
            validator.validate_business_logic(config)

    def test_unique_client_ips_enforced(self):
        """Test that unique client IPs are enforced."""
        config = {
            "common": {
                "network_name": "test",
                "network_ipv4_addr": "10.0.0.0/24",
            },
            "server": {
                "name": "srv",
                "endpoint": "1.2.3.4",
                "vlan_ipv4_addr": "10.0.0.1",
                "port": 51820,
                "interface": "eth0",
            },
            "clients": [
                {
                    "name": "client1",
                    "vlan_ipv4_addr": "10.0.0.2",
                    "port": 51821,
                    "gen_global": True,
                    "gen_local": False,
                },
                {
                    "name": "client2",
                    "vlan_ipv4_addr": "10.0.0.2",  # Duplicate IP
                    "port": 51822,
                    "gen_global": True,
                    "gen_local": False,
                },
            ],
        }

        with pytest.raises(ValueError, match="Duplicate.*IP"):
            validator.validate_business_logic(config)

    def test_ips_within_subnet_enforced(self):
        """Test that all IPs must be within subnet."""
        config = {
            "common": {
                "network_name": "test",
                "network_ipv4_addr": "10.0.0.0/24",
            },
            "server": {
                "name": "srv",
                "endpoint": "1.2.3.4",
                "vlan_ipv4_addr": "10.0.1.1",  # Outside subnet
                "port": 51820,
                "interface": "eth0",
            },
            "clients": [],
        }

        with pytest.raises(ValueError, match="outside.*subnet"):
            validator.validate_business_logic(config)

    def test_gen_global_or_gen_local_required(self):
        """Test that at least one of gen_global or gen_local must be true."""
        config = {
            "common": {
                "network_name": "test",
                "network_ipv4_addr": "10.0.0.0/24",
            },
            "server": {
                "name": "srv",
                "endpoint": "1.2.3.4",
                "vlan_ipv4_addr": "10.0.0.1",
                "port": 51820,
                "interface": "eth0",
            },
            "clients": [
                {
                    "name": "client1",
                    "vlan_ipv4_addr": "10.0.0.2",
                    "port": 51821,
                    "gen_global": False,
                    "gen_local": False,  # Both false - invalid
                }
            ],
        }

        with pytest.raises(ValueError, match="gen_global.*gen_local"):
            validator.validate_business_logic(config)
