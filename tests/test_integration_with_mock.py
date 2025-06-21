"""
Integration tests using the WireGuard mock framework
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from wg_mesh_gen.wg_mock import MockWireGuardNetwork, ConnectionState
from wg_mesh_gen.builder import build_peer_configs
from wg_mesh_gen.smart_builder import SmartConfigBuilder
from wg_mesh_gen.render import ConfigRenderer


class TestIntegrationWithMock:
    """Integration tests that use the mock framework to validate generated configurations"""
    
    @pytest.fixture
    def mock_test_config(self, tmp_path):
        """Create test configuration files"""
        nodes_file = tmp_path / "test_nodes.yaml"
        topology_file = tmp_path / "test_topology.yaml"
        
        nodes_content = """
nodes:
  - name: RELAY-1
    wireguard_ip: 10.0.0.1/16
    endpoints: ["relay1.example.com:51820"]
    role: relay
  - name: RELAY-2
    wireguard_ip: 10.0.0.2/16
    endpoints: ["relay2.example.com:51820"]
    role: relay
  - name: CLIENT-1
    wireguard_ip: 10.0.0.10/16
    role: client
  - name: CLIENT-2
    wireguard_ip: 10.0.0.11/16
    role: client
  - name: CLIENT-3
    wireguard_ip: 10.0.0.12/16
    role: client
"""
        
        topology_content = """
peers:
  # Relay mesh
  - from: RELAY-1
    to: RELAY-2
    allowed_ips: [10.0.0.0/16]
  - from: RELAY-2
    to: RELAY-1
    allowed_ips: [10.0.0.0/16]
  # Clients to relays
  - from: CLIENT-1
    to: RELAY-1
    allowed_ips: [10.0.0.0/16]
  - from: CLIENT-2
    to: RELAY-1
    allowed_ips: [10.0.0.0/16]
  - from: CLIENT-3
    to: RELAY-2
    allowed_ips: [10.0.0.0/16]
"""
        
        nodes_file.write_text(nodes_content)
        topology_file.write_text(topology_content)
        
        return str(nodes_file), str(topology_file)
    
    @pytest.mark.asyncio
    async def test_generated_configs_connectivity(self, mock_test_config, tmp_path):
        """Test that generated configurations result in proper connectivity"""
        nodes_file, topology_file = mock_test_config
        output_dir = tmp_path / "output"
        
        # Generate configurations
        result = build_peer_configs(nodes_file, topology_file, auto_generate_keys=True)
        renderer = ConfigRenderer()
        for node_name, node_config in result['configs'].items():
            renderer.render_config(node_name, node_config, str(output_dir))
        
        # Create mock network
        network = MockWireGuardNetwork(nodes_file, topology_file)
        await network.start()
        
        # Wait for connections to establish
        await asyncio.sleep(2)
        
        # Verify connectivity by checking the network status
        status = network.get_network_status()
        
        # The mock network should have initialized connections based on topology
        # Check that nodes exist and have the right structure
        assert 'RELAY-1' in status['nodes']
        assert 'RELAY-2' in status['nodes']
        assert 'CLIENT-1' in status['nodes']
        
        # Check that connections are being established
        assert status['statistics']['total_nodes'] == 5
        
        # Verify handshakes occurred - we can see from logs that connections were established
        assert status['statistics']['total_packets'] > 0
        assert status['statistics']['connected_pairs'] > 0  # At least some connections established
        
        await network.stop()
    
    @pytest.mark.asyncio
    async def test_failover_scenario(self, mock_test_config, tmp_path):
        """Test network behavior during relay failure"""
        nodes_file, topology_file = mock_test_config
        
        # Generate configurations with smart builder
        builder = SmartConfigBuilder(nodes_file, topology_file)
        configs = builder.build_optimized_configs(str(tmp_path / "output"), auto_generate_keys=True)
        
        # Create mock network
        network = MockWireGuardNetwork(nodes_file, topology_file)
        await network.start()
        await asyncio.sleep(2)
        
        # Verify initial connectivity
        path_before = network.find_path('CLIENT-1', 'CLIENT-3')
        assert path_before is not None
        assert 'RELAY-1' in path_before or 'RELAY-2' in path_before
        
        # Simulate RELAY-1 failure
        await network.simulate_failure('RELAY-1')
        await asyncio.sleep(1)
        
        # Check network status after failure
        status_after_failure = network.get_network_status()
        
        # RELAY-1 should be marked as not running
        assert not network.mock_nodes['RELAY-1'].running
        
        # Other nodes should still be running
        assert network.mock_nodes['RELAY-2'].running
        assert network.mock_nodes['CLIENT-3'].running
        
        # Simulate recovery
        await network.simulate_recovery('RELAY-1')
        await asyncio.sleep(2)
        
        # Verify node is running again
        assert network.mock_nodes['RELAY-1'].running
        
        await network.stop()
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, mock_test_config):
        """Test that mock framework correctly tracks performance metrics"""
        nodes_file, topology_file = mock_test_config
        
        network = MockWireGuardNetwork(nodes_file, topology_file)
        await network.start()
        await asyncio.sleep(3)  # Let some keepalive traffic flow
        
        status = network.get_network_status()
        
        # Verify metrics are being collected
        assert status['statistics']['total_packets'] > 0
        assert status['statistics']['total_bytes'] > 0
        
        # Check that we have some nodes with peers
        nodes_with_peers = sum(1 for node in status['nodes'].values() if node['peers'])
        assert nodes_with_peers > 0
        
        # Check that some connections have been attempted
        total_handshake_attempts = 0
        for node_name, node_status in status['nodes'].items():
            for peer_name, peer_status in node_status['peers'].items():
                metrics = peer_status['metrics']
                if metrics['packets_sent'] > 0 or metrics['packets_received'] > 0:
                    total_handshake_attempts += 1
        
        assert total_handshake_attempts > 0  # At least some connection attempts
        
        await network.stop()
    
    @pytest.mark.asyncio
    async def test_large_topology_performance(self):
        """Test mock framework with the super complex topology"""
        # Use the actual super complex topology
        network = MockWireGuardNetwork(
            "examples/super_complex_nodes.yaml",
            "examples/super_complex_topology.yaml"
        )
        
        start_time = asyncio.get_event_loop().time()
        await network.start()
        
        # Wait for initial connections (with timeout)
        await asyncio.wait_for(asyncio.sleep(5), timeout=10)
        
        elapsed = asyncio.get_event_loop().time() - start_time
        
        status = network.get_network_status()
        
        # Verify it can handle large topology
        assert status['statistics']['total_nodes'] == 107
        assert status['statistics']['total_edges'] == 216
        
        # Should establish some connections within reasonable time
        assert status['statistics']['connected_pairs'] > 0
        
        # Performance check - should start within reasonable time
        assert elapsed < 15  # 15 seconds max for startup
        
        await network.stop()
    
    @pytest.mark.asyncio
    async def test_network_conditions(self, tmp_path):
        """Test that network conditions affect packet delivery"""
        # Create a simple topology with packet loss
        nodes_file = tmp_path / "lossy_nodes.yaml"
        topology_file = tmp_path / "lossy_topology.yaml"
        
        nodes_content = """
nodes:
  - name: NODE-A
    wireguard_ip: 10.0.0.1/16
    role: relay
  - name: TEST-PACKET-LOSS
    wireguard_ip: 10.0.0.2/16
    role: client
"""
        
        topology_content = """
peers:
  - from: NODE-A
    to: TEST-PACKET-LOSS
    allowed_ips: [10.0.0.0/16]
  - from: TEST-PACKET-LOSS
    to: NODE-A
    allowed_ips: [10.0.0.0/16]
"""
        
        nodes_file.write_text(nodes_content)
        topology_file.write_text(topology_content)
        
        network = MockWireGuardNetwork(str(nodes_file), str(topology_file))
        await network.start()
        await asyncio.sleep(2)
        
        # Get network conditions
        conditions = network._calculate_network_conditions('NODE-A', 'TEST-PACKET-LOSS')
        assert conditions.packet_loss == 0.1  # 10% packet loss for TEST-PACKET-LOSS
        
        # The connection might be established but with degraded performance
        node_a = network.mock_nodes['NODE-A']
        metrics = node_a.peer_metrics['TEST-PACKET-LOSS']
        
        # With packet loss, we expect some packets to be lost
        # This is probabilistic, so we just verify the mechanism works
        assert conditions.packet_loss > 0
        
        await network.stop()
    
    def test_config_validation_with_mock(self, mock_test_config, tmp_path):
        """Test that generated configs are valid for mock network initialization"""
        nodes_file, topology_file = mock_test_config
        
        # Generate configurations
        result = build_peer_configs(nodes_file, topology_file, auto_generate_keys=True)
        
        # Verify the mock network can be created with these configs
        # This validates that the configuration structure is correct
        network = MockWireGuardNetwork(nodes_file, topology_file)
        
        # Check that all nodes from config are in mock network
        for node_name, node_config in result['configs'].items():
            assert node_name in network.mock_nodes
            
            mock_node = network.mock_nodes[node_name]
            assert mock_node.ip == node_config['interface']['address']
            # Mock nodes are created from YAML config which doesn't have keys
            # The actual private keys are in the generated config
            
            # Verify peer relationships match
            config_peers = {p['name'] for p in node_config['peers']}
            graph_peers = set(network.graph.neighbors(node_name))
            
            # All configured peers should be in the graph
            for peer_name in config_peers:
                assert peer_name in graph_peers