"""
Tests for builder module using mock framework to verify generated configurations
"""
import pytest
import asyncio
import yaml
from unittest.mock import patch, MagicMock
from wg_mesh_gen.builder import build_peer_configs, _build_node_config_optimized, _build_peer_map
from wg_mesh_gen.wg_mock import MockWireGuardNode, ConnectionState, MockPacket, PacketType
from wg_mesh_gen.simple_storage import SimpleKeyStorage
import tempfile


class TestBuilderWithMock:
    """Test builder functionality using mock framework"""
    
    @pytest.fixture
    def sample_nodes(self):
        """Sample nodes configuration"""
        return [
            {
                'name': 'HUB',
                'wireguard_ip': '10.0.0.1/24',
                'endpoints': ['hub.example.com:51820'],
                'role': 'relay'
            },
            {
                'name': 'SPOKE-1',
                'wireguard_ip': '10.0.0.10/24',
                'role': 'client'
            },
            {
                'name': 'SPOKE-2',
                'wireguard_ip': '10.0.0.11/24',
                'role': 'client'
            }
        ]
    
    @pytest.fixture
    def sample_peers(self):
        """Sample peer relationships"""
        return [
            {
                'from': 'HUB',
                'to': 'SPOKE-1',
                'allowed_ips': ['10.0.0.0/24']
            },
            {
                'from': 'HUB',
                'to': 'SPOKE-2',
                'allowed_ips': ['10.0.0.0/24']
            },
            {
                'from': 'SPOKE-1',
                'to': 'HUB',
                'allowed_ips': ['10.0.0.0/24']
            },
            {
                'from': 'SPOKE-2',
                'to': 'HUB',
                'allowed_ips': ['10.0.0.0/24']
            }
        ]
    
    @pytest.mark.asyncio
    async def test_generated_config_with_mock_node(self, sample_nodes, sample_peers):
        """Test that generated config works with mock node"""
        # Build config for HUB node
        peer_map = {
            'HUB': [
                {'node': 'SPOKE-1', 'direction': 'outgoing', 'allowed_ips': ['10.0.0.0/24']},
                {'node': 'SPOKE-2', 'direction': 'outgoing', 'allowed_ips': ['10.0.0.0/24']}
            ]
        }
        
        # Add keys to nodes for testing
        sample_nodes[0]['private_key'] = 'hub-private-key'
        sample_nodes[0]['public_key'] = 'hub-public-key'
        sample_nodes[1]['private_key'] = 'spoke1-private-key'
        sample_nodes[1]['public_key'] = 'spoke1-public-key'
        sample_nodes[2]['private_key'] = 'spoke2-private-key'
        sample_nodes[2]['public_key'] = 'spoke2-public-key'
        
        config = _build_node_config_optimized(
            sample_nodes[0],  # HUB
            sample_nodes,
            peer_map
        )
        
        # Create mock node with generated config
        mock_node = MockWireGuardNode('HUB', {
            'wireguard_ip': config['interface']['address'],
            'role': 'relay',
            'private_key': config['interface']['private_key'],
            'public_key': 'hub-public-key'
        })
        
        # Verify mock node initialized correctly
        assert mock_node.ip == '10.0.0.1/24'
        assert mock_node.private_key == 'hub-private-key'
        assert len(config['peers']) == 2
        
        # Test mock node can start
        await mock_node.start()
        assert mock_node.running is True
        
        # Test mock node can initiate connections
        await mock_node.connect_to_peer('SPOKE-1', 'spoke1-public-key')
        assert mock_node.peer_states['SPOKE-1'] == ConnectionState.HANDSHAKE_INIT
        
        await mock_node.stop()
    
    def test_missing_keys_handling_with_mock(self, sample_nodes, sample_peers, tmp_path):
        """Test builder behavior when keys are missing"""
        # Create temporary config files
        nodes_file = tmp_path / "test_nodes.yaml"
        topology_file = tmp_path / "test_topology.yaml"
        
        # Write sample data to files
        import yaml
        with open(nodes_file, 'w') as f:
            yaml.dump({'nodes': sample_nodes}, f)
        with open(topology_file, 'w') as f:
            yaml.dump({'peers': sample_peers}, f)
        
        # Create temporary storage
        storage_path = tmp_path / "test_keys.json"
        
        # Build without auto-generate should fail for nodes without keys
        with pytest.raises(ValueError, match="Node .* missing keys"):
            build_peer_configs(
                str(nodes_file),
                str(topology_file),
                auto_generate_keys=False,
                db_path=str(storage_path)
            )
        
        # Build with auto-generate should succeed
        result = build_peer_configs(
            str(nodes_file),
            str(topology_file),
            auto_generate_keys=True,
            db_path=str(storage_path)
        )
        
        # Verify all nodes have keys
        for node_name, node_config in result['configs'].items():
            assert 'private_key' in node_config['interface']
            assert node_config['interface']['private_key']
            
            # Verify mock node can be created with these keys
            mock_node = MockWireGuardNode(node_name, {
                'wireguard_ip': node_config['interface']['address'],
                'role': 'client',
                'private_key': node_config['interface']['private_key'],
                'public_key': 'test-public-key'
            })
            assert mock_node.private_key == node_config['interface']['private_key']
    
    @pytest.mark.asyncio
    async def test_peer_configuration_validity(self, sample_nodes, sample_peers, tmp_path):
        """Test that peer configurations result in valid connections"""
        # Create temporary config files
        nodes_file = tmp_path / "test_nodes.yaml"
        topology_file = tmp_path / "test_topology.yaml"
        
        # Write sample data to files
        import yaml
        with open(nodes_file, 'w') as f:
            yaml.dump({'nodes': sample_nodes}, f)
        with open(topology_file, 'w') as f:
            yaml.dump({'peers': sample_peers}, f)
        
        # Build complete configuration
        with patch('wg_mesh_gen.crypto.generate_keypair') as mock_gen:
            # Generate predictable keys
            mock_gen.side_effect = [
                ('hub-private', 'hub-public'),
                ('spoke1-private', 'spoke1-public'),
                ('spoke2-private', 'spoke2-public')
            ]
            
            result = build_peer_configs(
                str(nodes_file),
                str(topology_file),
                auto_generate_keys=True,
                db_path=str(tmp_path / "keys.json")
            )
        
        # Create mock nodes for each configuration
        mock_nodes = {}
        for node_name, config in result['configs'].items():
            mock_nodes[node_name] = MockWireGuardNode(node_name, {
                'wireguard_ip': config['interface']['address'],
                'role': 'relay' if node_name == 'HUB' else 'client',
                'private_key': config['interface']['private_key'],
                'public_key': {'HUB': 'hub-public', 'SPOKE-1': 'spoke1-public', 'SPOKE-2': 'spoke2-public'}[node_name]
            })
        
        # Start all nodes
        for node in mock_nodes.values():
            await node.start()
        
        # Verify peer relationships match configuration
        hub_config = result['configs']['HUB']
        assert len(hub_config['peers']) == 2
        assert {p['name'] for p in hub_config['peers']} == {'SPOKE-1', 'SPOKE-2'}
        
        spoke1_config = result['configs']['SPOKE-1']
        assert len(spoke1_config['peers']) == 1
        assert spoke1_config['peers'][0]['name'] == 'HUB'
        
        # Stop all nodes
        for node in mock_nodes.values():
            await node.stop()
    
    def test_complex_topology_building(self, tmp_path):
        """Test building configuration for complex topology"""
        # Create a more complex topology
        nodes = [
            {'name': f'RELAY-{i}', 'wireguard_ip': f'10.0.{i}.1/16', 'endpoints': [f'relay{i}.example.com:51820'], 'role': 'relay'}
            for i in range(1, 4)
        ] + [
            {'name': f'CLIENT-{i}', 'wireguard_ip': f'10.0.10.{i}/16', 'role': 'client'}
            for i in range(1, 6)
        ]
        
        # Full mesh between relays
        peers = []
        for i in range(1, 4):
            for j in range(1, 4):
                if i != j:
                    peers.append({
                        'from': f'RELAY-{i}',
                        'to': f'RELAY-{j}',
                        'allowed_ips': ['10.0.0.0/16']
                    })
        
        # Clients connect to nearest relay
        for i in range(1, 6):
            relay_idx = ((i - 1) % 3) + 1
            peers.append({
                'from': f'CLIENT-{i}',
                'to': f'RELAY-{relay_idx}',
                'allowed_ips': ['10.0.0.0/16']
            })
        
        # Create temporary config files
        nodes_file = tmp_path / "complex_nodes.yaml"
        topology_file = tmp_path / "complex_topology.yaml"
        
        # Write data to files
        import yaml
        with open(nodes_file, 'w') as f:
            yaml.dump({'nodes': nodes}, f)
        with open(topology_file, 'w') as f:
            yaml.dump({'peers': peers}, f)
        
        # Build configuration
        with patch('wg_mesh_gen.crypto.generate_keypair') as mock_gen:
            mock_gen.side_effect = [(f'{n["name"]}-private', f'{n["name"]}-public') for n in nodes]
            
            result = build_peer_configs(
                str(nodes_file),
                str(topology_file),
                auto_generate_keys=True,
                db_path=str(tmp_path / "keys.json")
            )
        
        # Verify relay mesh
        for i in range(1, 4):
            relay_config = result['configs'][f'RELAY-{i}']
            # Each relay should have 2 peers (other relays) + some clients
            relay_peer_names = {p['name'] for p in relay_config['peers']}
            
            # Should connect to other relays
            for j in range(1, 4):
                if i != j:
                    assert f'RELAY-{j}' in relay_peer_names
        
        # Verify client connections
        for i in range(1, 6):
            client_config = result['configs'][f'CLIENT-{i}']
            relay_idx = ((i - 1) % 3) + 1
            assert len(client_config['peers']) == 1
            assert client_config['peers'][0]['name'] == f'RELAY-{relay_idx}'
    
    @pytest.mark.asyncio
    async def test_endpoint_configuration(self, sample_nodes, sample_peers, tmp_path):
        """Test that endpoints are correctly configured"""
        # Create temporary config files
        nodes_file = tmp_path / "test_nodes.yaml"
        topology_file = tmp_path / "test_topology.yaml"
        
        # Write sample data to files
        import yaml
        with open(nodes_file, 'w') as f:
            yaml.dump({'nodes': sample_nodes}, f)
        with open(topology_file, 'w') as f:
            yaml.dump({'peers': sample_peers}, f)
        
        result = build_peer_configs(
            str(nodes_file),
            str(topology_file),
            auto_generate_keys=True,
            db_path=str(tmp_path / "keys.json")
        )
        
        # Check HUB has endpoint
        hub_config = result['configs']['HUB']
        assert hub_config['interface'].get('listen_port') == 51820  # Default port
        
        # Check SPOKE peers have HUB's endpoint
        spoke1_config = result['configs']['SPOKE-1']
        hub_peer = spoke1_config['peers'][0]
        assert hub_peer.get('endpoint') == 'hub.example.com:51820'
        
        # Spokes should not have endpoints in their peer configs (they're clients)
        hub_spoke_peers = [p for p in hub_config['peers'] if p['name'].startswith('SPOKE')]
        for peer in hub_spoke_peers:
            assert 'endpoint' not in peer or peer['endpoint'] is None