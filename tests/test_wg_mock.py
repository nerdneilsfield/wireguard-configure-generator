"""
Tests for WireGuard Mock Framework
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from wg_mesh_gen.wg_mock import (
    MockWireGuardNode,
    MockWireGuardNetwork,
    ConnectionState,
    PacketType,
    MockPacket,
    NetworkConditions
)


@pytest.fixture
def mock_node_config():
    """Sample node configuration"""
    return {
        'name': 'test-node',
        'wireguard_ip': '10.0.0.1',
        'role': 'client',
        'private_key': 'test-private-key',
        'public_key': 'test-public-key'
    }


@pytest.fixture
def mock_network_config(tmp_path):
    """Create temporary test configuration files"""
    nodes_file = tmp_path / "test_nodes.yaml"
    topology_file = tmp_path / "test_topology.yaml"
    
    nodes_content = """
nodes:
  - name: NODE-A
    wireguard_ip: 10.0.0.1
    role: relay
    public_key: pubkey-a
    private_key: privkey-a
  - name: NODE-B
    wireguard_ip: 10.0.0.2
    role: client
    public_key: pubkey-b
    private_key: privkey-b
  - name: NODE-C
    wireguard_ip: 10.0.0.3
    role: client
    public_key: pubkey-c
    private_key: privkey-c
"""
    
    topology_content = """
peers:
  - from: NODE-A
    to: NODE-B
    allowed_ips: 10.0.0.0/16
  - from: NODE-B
    to: NODE-A
    allowed_ips: 10.0.0.0/16
  - from: NODE-A
    to: NODE-C
    allowed_ips: 10.0.0.0/16
  - from: NODE-C
    to: NODE-A
    allowed_ips: 10.0.0.0/16
"""
    
    nodes_file.write_text(nodes_content)
    topology_file.write_text(topology_content)
    
    return str(nodes_file), str(topology_file)


class TestMockWireGuardNode:
    """Test MockWireGuardNode functionality"""
    
    def test_node_initialization(self, mock_node_config):
        """Test node initialization with config"""
        node = MockWireGuardNode('test-node', mock_node_config)
        
        assert node.name == 'test-node'
        assert node.ip == '10.0.0.1'
        assert node.role == 'client'
        assert node.private_key == 'test-private-key'
        assert node.public_key == 'test-public-key'
        assert node.running is False
        assert len(node.peer_states) == 0
    
    @pytest.mark.asyncio
    async def test_node_start_stop(self, mock_node_config):
        """Test starting and stopping a node"""
        node = MockWireGuardNode('test-node', mock_node_config)
        
        # Start node
        await node.start()
        assert node.running is True
        
        # Stop node
        await node.stop()
        assert node.running is False
    
    @pytest.mark.asyncio
    async def test_connect_to_peer(self, mock_node_config):
        """Test initiating connection to peer"""
        node = MockWireGuardNode('test-node', mock_node_config)
        await node.start()
        
        # Connect to peer
        await node.connect_to_peer('peer-node', 'peer-public-key')
        
        # Check state
        assert node.peer_states['peer-node'] == ConnectionState.HANDSHAKE_INIT
        assert 'peer-node' in node.handshake_timers
        
        # Check packet was queued
        assert node.outbound_queue.qsize() == 1
        packet = await node.outbound_queue.get()
        assert packet.packet_type == PacketType.HANDSHAKE_INIT
        assert packet.dst == 'peer-node'
        
        await node.stop()
    
    @pytest.mark.asyncio
    async def test_handshake_flow(self, mock_node_config):
        """Test complete handshake flow"""
        node_a = MockWireGuardNode('node-a', mock_node_config)
        node_b = MockWireGuardNode('node-b', {
            **mock_node_config,
            'name': 'node-b',
            'wireguard_ip': '10.0.0.2'
        })
        
        await node_a.start()
        await node_b.start()
        
        # Node A initiates connection
        await node_a.connect_to_peer('node-b', 'node-b-pubkey')
        
        # Get handshake init packet
        init_packet = await node_a.outbound_queue.get()
        
        # Node B receives handshake init
        await node_b.receive_packet(init_packet)
        await asyncio.sleep(0.2)  # Allow processing
        
        # Node B should send response
        assert node_b.outbound_queue.qsize() == 1
        response_packet = await node_b.outbound_queue.get()
        assert response_packet.packet_type == PacketType.HANDSHAKE_RESPONSE
        
        # Node A receives response
        await node_a.receive_packet(response_packet)
        await asyncio.sleep(0.2)  # Allow processing
        
        # Check connection established
        assert node_a.peer_states['node-b'] == ConnectionState.CONNECTED
        assert node_a.peer_metrics['node-b'].handshakes_completed == 1
        
        await node_a.stop()
        await node_b.stop()
    
    def test_get_peer_status(self, mock_node_config):
        """Test getting peer connection status"""
        node = MockWireGuardNode('test-node', mock_node_config)
        
        # Set up some peer state
        node.peer_states['peer-1'] = ConnectionState.CONNECTED
        node.peer_metrics['peer-1'].packets_sent = 100
        node.peer_metrics['peer-1'].packets_received = 95
        
        status = node.get_peer_status('peer-1')
        
        assert status['state'] == 'connected'
        assert status['metrics']['packets_sent'] == 100
        assert status['metrics']['packets_received'] == 95


class TestNetworkConditions:
    """Test NetworkConditions class"""
    
    def test_default_conditions(self):
        """Test default network conditions"""
        conditions = NetworkConditions()
        
        assert conditions.latency_ms == 10.0
        assert conditions.jitter_ms == 2.0
        assert conditions.packet_loss == 0.0
        assert conditions.bandwidth_mbps == 100.0
    
    def test_get_latency_with_jitter(self):
        """Test latency calculation with jitter"""
        conditions = NetworkConditions(latency_ms=50.0, jitter_ms=10.0)
        
        # Test multiple times to check jitter
        latencies = [conditions.get_latency() for _ in range(100)]
        
        assert all(40.0 <= l <= 60.0 for l in latencies)
        assert min(latencies) < 45.0  # Should have some low values
        assert max(latencies) > 55.0  # Should have some high values


class TestMockWireGuardNetwork:
    """Test MockWireGuardNetwork functionality"""
    
    def test_network_initialization(self, mock_network_config):
        """Test network initialization from config files"""
        nodes_file, topology_file = mock_network_config
        network = MockWireGuardNetwork(nodes_file, topology_file)
        
        assert len(network.mock_nodes) == 3
        assert 'NODE-A' in network.mock_nodes
        assert 'NODE-B' in network.mock_nodes
        assert 'NODE-C' in network.mock_nodes
        
        assert network.graph.number_of_nodes() == 3
        assert network.graph.number_of_edges() == 2
    
    def test_calculate_network_conditions(self, mock_network_config):
        """Test network condition calculation"""
        nodes_file, topology_file = mock_network_config
        network = MockWireGuardNetwork(nodes_file, topology_file)
        
        # Test same region
        conditions = network._calculate_network_conditions('NODE-A', 'NODE-B')
        assert 10 <= conditions.latency_ms <= 30  # Same region default
        
        # Test special cases
        high_latency_node = 'HIGH-LATENCY-NODE'
        conditions = network._calculate_network_conditions(high_latency_node, 'NODE-A')
        assert conditions.latency_ms == 500
        assert conditions.jitter_ms == 100
    
    @pytest.mark.asyncio
    async def test_network_start_stop(self, mock_network_config):
        """Test starting and stopping network simulation"""
        nodes_file, topology_file = mock_network_config
        network = MockWireGuardNetwork(nodes_file, topology_file)
        
        await network.start()
        assert network.running is True
        
        # Check all nodes started
        for node in network.mock_nodes.values():
            assert node.running is True
        
        await network.stop()
        assert network.running is False
        
        # Check all nodes stopped
        for node in network.mock_nodes.values():
            assert node.running is False
    
    @pytest.mark.asyncio
    async def test_packet_routing(self, mock_network_config):
        """Test packet routing between nodes"""
        nodes_file, topology_file = mock_network_config
        network = MockWireGuardNetwork(nodes_file, topology_file)
        
        await network.start()
        
        # Send packet from NODE-A to NODE-B
        packet = MockPacket(
            src='NODE-A',
            dst='NODE-B',
            packet_type=PacketType.DATA,
            payload={'test': 'data'}
        )
        
        # Check initial metrics
        initial_received = network.mock_nodes['NODE-B'].peer_metrics['NODE-A'].packets_received
        
        await network.mock_nodes['NODE-A'].send_packet(packet)
        
        # Allow routing and processing
        await asyncio.sleep(0.5)
        
        # Check NODE-B received packet by checking metrics
        final_received = network.mock_nodes['NODE-B'].peer_metrics['NODE-A'].packets_received
        assert final_received > initial_received
        
        await network.stop()
    
    @pytest.mark.asyncio
    async def test_simulate_failure_recovery(self, mock_network_config):
        """Test node failure and recovery simulation"""
        nodes_file, topology_file = mock_network_config
        network = MockWireGuardNetwork(nodes_file, topology_file)
        
        await network.start()
        await asyncio.sleep(0.5)  # Let connections establish
        
        # Simulate NODE-A failure
        await network.simulate_failure('NODE-A')
        assert network.mock_nodes['NODE-A'].running is False
        
        # Check other nodes marked NODE-A as disconnected
        assert network.mock_nodes['NODE-B'].peer_states.get('NODE-A') == ConnectionState.DISCONNECTED
        
        # Simulate recovery
        await network.simulate_recovery('NODE-A')
        assert network.mock_nodes['NODE-A'].running is True
        
        await network.stop()
    
    def test_find_path(self, mock_network_config):
        """Test path finding between nodes"""
        nodes_file, topology_file = mock_network_config
        network = MockWireGuardNetwork(nodes_file, topology_file)
        
        # Direct path
        path = network.find_path('NODE-B', 'NODE-C')
        assert path == ['NODE-B', 'NODE-A', 'NODE-C']
        
        # No path to non-existent node
        path = network.find_path('NODE-A', 'NODE-X')
        assert path is None
    
    def test_calculate_path_latency(self, mock_network_config):
        """Test path latency calculation"""
        nodes_file, topology_file = mock_network_config
        network = MockWireGuardNetwork(nodes_file, topology_file)
        
        path = ['NODE-B', 'NODE-A', 'NODE-C']
        latency = network.calculate_path_latency(path)
        
        assert latency > 0  # Should have some latency
        assert latency < 1000  # Should be reasonable
    
    def test_get_network_status(self, mock_network_config):
        """Test getting network status"""
        nodes_file, topology_file = mock_network_config
        network = MockWireGuardNetwork(nodes_file, topology_file)
        
        status = network.get_network_status()
        
        assert 'nodes' in status
        assert 'connections' in status
        assert 'statistics' in status
        
        assert status['statistics']['total_nodes'] == 3
        assert status['statistics']['total_edges'] == 2
        
        # Check node details
        assert 'NODE-A' in status['nodes']
        assert status['nodes']['NODE-A']['role'] == 'relay'
        assert status['nodes']['NODE-A']['ip'] == '10.0.0.1'


@pytest.mark.asyncio
async def test_integration_complex_topology():
    """Integration test with complex topology simulation"""
    # This test would use the actual super_complex topology files
    # For unit tests, we'll use a simpler version
    
    # Create a simple test network
    network = MockWireGuardNetwork(
        'examples/super_complex_nodes.yaml',
        'examples/super_complex_topology.yaml'
    )
    
    # Just check it initializes without error
    assert len(network.mock_nodes) > 100  # Super complex has 107 nodes
    assert network.graph.number_of_edges() > 200  # Has 216 connections
    
    # Test finding path across regions
    path = network.find_path('CLIENT-USE-001', 'CLIENT-AP-001')
    assert path is not None
    assert len(path) > 2  # Should go through multiple hops
    
    # Calculate cross-region latency
    latency = network.calculate_path_latency(path)
    assert latency > 100  # Cross-region should have high latency