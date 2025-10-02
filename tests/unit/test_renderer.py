"""Unit tests for renderer module."""

import pytest

from wg_mesh_gen import renderer


class TestServerConfigRendering:
    """Test server config rendering."""

    def test_render_server_config_generates_correct_format(self, sample_server_config):
        """Test that render_server_config() generates correct WireGuard format."""
        server = sample_server_config["server"]
        clients = sample_server_config["clients"]
        keys = sample_server_config["keys"]
        network_name = "my-vpn"

        config = renderer.render_server_config(server, clients, keys, network_name)

        assert "[Interface]" in config
        assert f"Address = {server['vlan_ipv4_addr']}/24" in config
        assert f"ListenPort = {server['port']}" in config
        assert "PrivateKey" in config
        assert "PostUp" in config
        assert "PostDown" in config

    def test_server_config_includes_iptables_rules(self, sample_server_config):
        """Test that server config includes PostUp/PostDown iptables rules."""
        server = sample_server_config["server"]
        clients = sample_server_config["clients"]
        keys = sample_server_config["keys"]
        network_name = "my-vpn"

        config = renderer.render_server_config(server, clients, keys, network_name)

        assert "iptables -A FORWARD" in config
        assert "iptables -t nat -A POSTROUTING" in config
        assert "iptables -D FORWARD" in config  # PostDown

    def test_server_config_includes_all_clients(self, sample_server_config):
        """Test that server config includes all clients as peers."""
        server = sample_server_config["server"]
        clients = sample_server_config["clients"]
        keys = sample_server_config["keys"]
        network_name = "my-vpn"

        config = renderer.render_server_config(server, clients, keys, network_name)

        for client in clients:
            assert f"### Client {client['name']}" in config
            assert "[Peer]" in config


class TestClientConfigRendering:
    """Test client config rendering."""

    def test_render_client_config_with_gen_global(self, sample_client_config):
        """Test client config with gen_global (AllowedIPs=0.0.0.0/0)."""
        client = sample_client_config["client"]
        server = sample_client_config["server"]
        keys = sample_client_config["keys"]
        allowed_ips = "0.0.0.0/0"

        config = renderer.render_client_config(client, server, keys, allowed_ips)

        assert "[Interface]" in config
        assert "PrivateKey" in config
        assert f"Address = {client['vlan_ipv4_addr']}/32" in config
        assert "AllowedIPs = 0.0.0.0/0" in config

    def test_render_client_config_with_gen_local(self, sample_client_config):
        """Test client config with gen_local (AllowedIPs=network_subnet)."""
        client = sample_client_config["client"]
        server = sample_client_config["server"]
        keys = sample_client_config["keys"]
        allowed_ips = "10.0.0.0/24"

        config = renderer.render_client_config(client, server, keys, allowed_ips)

        assert "AllowedIPs = 10.0.0.0/24" in config

    def test_client_config_dns_rendering_both(self):
        """Test DNS field rendering with dns1 and dns2."""
        client = {
            "name": "test",
            "vlan_ipv4_addr": "10.0.0.2",
            "dns1": "1.1.1.1",
            "dns2": "8.8.8.8",
        }
        server = {"name": "srv", "endpoint": "1.2.3.4", "port": 51820}
        keys = {
            "server": {"public_key": "srvpub"},
            "clients": {"test": {"private_key": "priv", "preshared_key": "psk"}},
        }

        config = renderer.render_client_config(client, server, keys, "0.0.0.0/0")

        assert "DNS = 1.1.1.1,8.8.8.8" in config

    def test_client_config_dns_rendering_dns1_only(self):
        """Test DNS field rendering with dns1 only."""
        client = {
            "name": "test",
            "vlan_ipv4_addr": "10.0.0.2",
            "dns1": "1.1.1.1",
        }
        server = {"name": "srv", "endpoint": "1.2.3.4", "port": 51820}
        keys = {
            "server": {"public_key": "srvpub"},
            "clients": {"test": {"private_key": "priv", "preshared_key": "psk"}},
        }

        config = renderer.render_client_config(client, server, keys, "0.0.0.0/0")

        assert "DNS = 1.1.1.1" in config
        assert "8.8.8.8" not in config

    def test_client_config_no_dns(self):
        """Test client config without DNS."""
        client = {"name": "test", "vlan_ipv4_addr": "10.0.0.2"}
        server = {"name": "srv", "endpoint": "1.2.3.4", "port": 51820}
        keys = {
            "server": {"public_key": "srvpub"},
            "clients": {"test": {"private_key": "priv", "preshared_key": "psk"}},
        }

        config = renderer.render_client_config(client, server, keys, "0.0.0.0/0")

        assert "DNS" not in config
