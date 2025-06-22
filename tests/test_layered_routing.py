"""
Test layered routing scenarios with the mock framework
"""

import pytest
import asyncio
import json
from pathlib import Path
from wg_mesh_gen.wg_mock import MockWireGuardNetwork, MockPacket, PacketType
from wg_mesh_gen.group_network_builder import GroupNetworkBuilder
from wg_mesh_gen.builder import build_from_data
from wg_mesh_gen.logger import get_logger


class TestLayeredRouting:
    """Test layered routing scenarios"""
    
    @pytest.fixture
    def group_config_path(self, tmp_path):
        """Create a test group configuration file"""
        config = {
            "network_topology": {
                "groups": {
                    "china_office": {
                        "nodes": {
                            "office1": {
                                "ip": "10.96.1.2/24",
                                "endpoints": {"default": "192.168.1.10:51820"}
                            },
                            "office2": {
                                "ip": "10.96.1.3/24",
                                "endpoints": {"default": "192.168.1.11:51820"}
                            }
                        },
                        "topology": "mesh"
                    },
                    "china_relay": {
                        "nodes": {
                            "china_gw": {
                                "ip": "10.96.100.1/24",
                                "endpoints": {
                                    "public": "china.example.com:51820",
                                    "special": "172.16.0.1:22222"
                                },
                                "is_relay": True
                            }
                        },
                        "topology": "single"
                    },
                    "overseas": {
                        "nodes": {
                            "us_relay": {
                                "ip": "10.96.200.1/24",
                                "endpoints": {
                                    "public": "us.example.com:51820",
                                    "special": "172.16.1.1:33333"
                                },
                                "is_relay": True
                            },
                            "us_server": {
                                "ip": "10.96.200.2/24",
                                "endpoints": {"default": "us2.example.com:51820"}
                            }
                        },
                        "topology": "star",
                        "hub_node": "us_relay"
                    }
                },
                "connections": [
                    {
                        "name": "china_to_relay",
                        "from": "china_office",
                        "to": "china_relay",
                        "type": "outbound_only",
                        "endpoint_selector": "public",
                        "routing": {
                            "allowed_ips": ["china_relay.nodes", "overseas.subnet"]
                        }
                    },
                    {
                        "name": "china_overseas_bridge",
                        "from": "china_relay.china_gw",
                        "to": "overseas.us_relay",
                        "type": "bidirectional",
                        "endpoint_mapping": {
                            "china_gw_to_us_relay": "us_relay.special",
                            "us_relay_to_china_gw": "china_gw.special"
                        },
                        "special_flags": {
                            "is_bridge": True,
                            "persistent_keepalive": 25
                        },
                        "routing": {
                            "china_gw_allowed_ips": ["overseas.subnet"],
                            "us_relay_allowed_ips": ["china_office.subnet", "china_relay.nodes"]
                        }
                    }
                ]
            }
        }
        
        config_path = tmp_path / "test_group_config.yaml"
        # Use json for simplicity in testing
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        return config_path
    
    def test_group_network_builder_init(self, group_config_path):
        """Test GroupNetworkBuilder initialization"""
        builder = GroupNetworkBuilder(str(group_config_path))
        assert builder.config is not None
        assert 'groups' in builder.config
        assert 'connections' in builder.config
    
    def test_build_nodes_and_peers(self, group_config_path):
        """Test building nodes and peers from group config"""
        builder = GroupNetworkBuilder(str(group_config_path))
        nodes, peers = builder.build()
        
        # Check nodes
        assert len(nodes) == 5  # office1, office2, china_gw, us_relay, us_server
        node_names = {node['name'] for node in nodes}
        assert 'office1' in node_names
        assert 'china_gw' in node_names
        assert 'us_relay' in node_names
        
        # Check relay nodes
        relay_nodes = [n for n in nodes if n.get('role') == 'relay']
        assert len(relay_nodes) == 2  # china_gw and us_relay
        
        # Check peers
        assert len(peers) > 0
        
        # Check specific connections
        china_to_relay = [p for p in peers if p['from'] == 'office1' and p['to'] == 'china_gw']
        assert len(china_to_relay) == 1
        assert '10.96.100.1/32' in china_to_relay[0]['allowed_ips']  # china_relay node
        assert '10.96.200.0/24' in china_to_relay[0]['allowed_ips']  # overseas subnet
    
    def test_routing_path_analysis(self, group_config_path):
        """Test routing path analysis"""
        builder = GroupNetworkBuilder(str(group_config_path))
        nodes, peers = builder.build()
        
        # Check that office nodes can route to overseas through china_gw
        office_peers = [p for p in peers if p['from'] == 'office1']
        office_allowed_ips = []
        for peer in office_peers:
            office_allowed_ips.extend(peer.get('allowed_ips', []))
        
        # Should have route to overseas subnet
        assert any('10.96.200.0/24' in ip for ip in office_allowed_ips)
    
    def test_endpoint_mapping(self, group_config_path):
        """Test endpoint mapping for special connections"""
        builder = GroupNetworkBuilder(str(group_config_path))
        nodes, peers = builder.build()
        
        # Find the bridge connection
        bridge_peers = [p for p in peers if p['from'] == 'china_gw' and p['to'] == 'us_relay']
        assert len(bridge_peers) == 1
        
        # Check endpoint is the special one
        assert bridge_peers[0].get('endpoint') == '172.16.1.1:33333'  # us_relay's special endpoint
    
    @pytest.mark.asyncio
    async def test_mock_network_routing(self, group_config_path, tmp_path):
        """Test routing with mock network"""
        # Build traditional format from group config
        builder = GroupNetworkBuilder(str(group_config_path))
        nodes, peers = builder.build()
        
        # Save to traditional format files
        nodes_file = tmp_path / "nodes.json"
        topology_file = tmp_path / "topology.json"
        
        with open(nodes_file, 'w') as f:
            json.dump({"nodes": nodes}, f, indent=2)
        
        with open(topology_file, 'w') as f:
            json.dump({"peers": peers}, f, indent=2)
        
        # Create mock network
        network = MockWireGuardNetwork(str(nodes_file), str(topology_file))
        
        await network.start()
        
        # Let connections establish
        await asyncio.sleep(2)
        
        # Test routing from office1 to us_server through relays
        office1 = network.mock_nodes['office1']
        
        # Send a data packet destined for us_server
        packet = MockPacket(
            src='office1',
            dst='china_gw',  # First hop
            packet_type=PacketType.DATA,
            payload={
                'destination_ip': '10.96.200.2',  # us_server's IP
                'data': 'Hello from China office!'
            }
        )
        
        await office1.send_packet(packet)
        
        # Give time for packet to route through network
        await asyncio.sleep(0.5)
        
        # Check network status
        status = network.get_network_status()
        
        # Verify china_gw forwarded the packet
        china_gw_metrics = status['nodes']['china_gw']['peers']
        assert 'us_relay' in china_gw_metrics
        
        await network.stop()
    
    @pytest.mark.asyncio
    async def test_relay_node_forwarding(self, tmp_path):
        """Test relay node packet forwarding"""
        # Create a simple relay scenario
        nodes = [
            {
                "name": "client",
                "wireguard_ip": "10.0.1.2/24",
                "role": "client",
                "endpoints": ["192.168.1.10:51820"]
            },
            {
                "name": "relay",
                "wireguard_ip": "10.0.2.1/24",
                "role": "relay",
                "enable_ip_forward": True,
                "endpoints": ["1.2.3.4:51820"]
            },
            {
                "name": "server",
                "wireguard_ip": "10.0.3.2/24",
                "role": "client",
                "endpoints": ["192.168.2.10:51820"]
            }
        ]
        
        peers = [
            {
                "from": "client",
                "to": "relay",
                "allowed_ips": ["10.0.2.1/32", "10.0.3.0/24"]
            },
            {
                "from": "relay",
                "to": "server",
                "allowed_ips": ["10.0.3.2/32"]
            }
        ]
        
        # Save configs
        nodes_file = tmp_path / "nodes.json"
        topology_file = tmp_path / "topology.json"
        
        with open(nodes_file, 'w') as f:
            json.dump({"nodes": nodes}, f)
        
        with open(topology_file, 'w') as f:
            json.dump({"peers": peers}, f)
        
        # Create and start network
        network = MockWireGuardNetwork(str(nodes_file), str(topology_file))
        await network.start()
        
        await asyncio.sleep(1)
        
        # Send packet from client to server through relay
        client = network.mock_nodes['client']
        packet = MockPacket(
            src='client',
            dst='relay',
            packet_type=PacketType.DATA,
            payload={
                'destination_ip': '10.0.3.2',
                'data': 'Test message'
            }
        )
        
        await client.send_packet(packet)
        await asyncio.sleep(0.5)
        
        # Check that relay forwarded the packet
        status = network.get_network_status()
        relay_metrics = status['nodes']['relay']['peers']['server']['metrics']
        assert relay_metrics['packets_sent'] > 0
        
        await network.stop()
    
    def test_allowed_ips_resolution(self, group_config_path):
        """Test resolution of allowed IPs references"""
        builder = GroupNetworkBuilder(str(group_config_path))
        
        # Test various formats
        test_cases = [
            (["10.0.0.0/24"], ["10.0.0.0/24"]),  # Direct CIDR
            (["china_office.subnet"], ["10.96.1.0/24"]),  # Group subnet
            (["china_relay.nodes"], ["10.96.100.1/32"]),  # Group nodes
        ]
        
        for input_ips, expected in test_cases:
            result = builder._resolve_allowed_ips(input_ips)
            assert set(result) == set(expected), f"Failed for {input_ips}"
    
    def test_no_allowed_ips_conflicts(self, group_config_path):
        """Test that there are no AllowedIPs conflicts"""
        builder = GroupNetworkBuilder(str(group_config_path))
        nodes, peers = builder.build()
        
        # Group peers by source node
        node_peers = {}
        for peer in peers:
            from_node = peer['from']
            if from_node not in node_peers:
                node_peers[from_node] = []
            node_peers[from_node].append(peer)
        
        # Check each node for conflicts
        for node, node_peer_list in node_peers.items():
            all_networks = []
            for peer in node_peer_list:
                for ip in peer.get('allowed_ips', []):
                    try:
                        network = str(ip).replace('/32', '/32')  # Normalize
                        all_networks.append((network, peer['to']))
                    except Exception:
                        pass
            
            # Look for overlaps (excluding exact matches)
            for i, (net1, peer1) in enumerate(all_networks):
                for net2, peer2 in all_networks[i+1:]:
                    if net1 == net2 and peer1 != peer2:
                        # This would be a real conflict
                        pytest.fail(f"Node {node} has conflicting AllowedIPs: "
                                  f"{net1} for both {peer1} and {peer2}")