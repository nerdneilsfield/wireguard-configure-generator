"""
WireGuard Connection Mock Framework

This module provides a simulation framework for testing WireGuard mesh networks
without requiring actual WireGuard interfaces or network connections.
"""

import asyncio
import time
import random
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import networkx as nx
from enum import Enum
from .loader import load_nodes, load_topology
from .logger import get_logger


class ConnectionState(Enum):
    """WireGuard connection states"""
    DISCONNECTED = "disconnected"
    HANDSHAKE_INIT = "handshake_init"
    HANDSHAKE_RESPONSE = "handshake_response"
    CONNECTED = "connected"
    KEY_ROTATION = "key_rotation"
    TIMEOUT = "timeout"


class PacketType(Enum):
    """Types of packets in WireGuard protocol"""
    HANDSHAKE_INIT = "handshake_init"
    HANDSHAKE_RESPONSE = "handshake_response"
    KEEPALIVE = "keepalive"
    DATA = "data"


@dataclass
class NetworkConditions:
    """Simulated network conditions between nodes"""
    latency_ms: float = 10.0  # Base latency in milliseconds
    jitter_ms: float = 2.0    # Latency variation
    packet_loss: float = 0.0  # Packet loss rate (0.0-1.0)
    bandwidth_mbps: float = 100.0  # Bandwidth in Mbps
    
    def get_latency(self) -> float:
        """Get latency with jitter"""
        return max(0, self.latency_ms + random.uniform(-self.jitter_ms, self.jitter_ms))


@dataclass
class MockPacket:
    """Simulated network packet"""
    src: str
    dst: str
    packet_type: PacketType
    payload: Dict[str, Any] = field(default_factory=dict)
    size_bytes: int = 100
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConnectionMetrics:
    """Metrics for a mock connection"""
    packets_sent: int = 0
    packets_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    handshakes_completed: int = 0
    last_handshake: Optional[float] = None
    last_packet: Optional[float] = None
    connection_established: Optional[float] = None


class MockWireGuardNode:
    """Mock WireGuard node that simulates protocol behavior"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.ip = config.get('wireguard_ip', '')
        self.role = config.get('role', 'client')
        self.private_key = config.get('private_key', '')
        self.public_key = config.get('public_key', '')
        
        # Connection states
        self.peer_states: Dict[str, ConnectionState] = {}
        self.peer_metrics: Dict[str, ConnectionMetrics] = defaultdict(ConnectionMetrics)
        
        # Packet queues
        self.inbound_queue: asyncio.Queue = asyncio.Queue()
        self.outbound_queue: asyncio.Queue = asyncio.Queue()
        
        # Handshake tracking
        self.handshake_timers: Dict[str, float] = {}
        self.keepalive_timers: Dict[str, float] = {}
        
        self.logger = get_logger()
        self.running = False
    
    async def start(self):
        """Start the mock node"""
        self.running = True
        self.logger.debug(f"Mock node {self.name} started")
        
        # Start background tasks
        asyncio.create_task(self._process_inbound())
        asyncio.create_task(self._process_keepalive())
    
    async def stop(self):
        """Stop the mock node"""
        self.running = False
        self.logger.debug(f"Mock node {self.name} stopped")
    
    async def connect_to_peer(self, peer_name: str, peer_public_key: str):
        """Initiate connection to a peer"""
        self.logger.debug(f"{self.name} initiating connection to {peer_name}")
        
        # Send handshake init
        packet = MockPacket(
            src=self.name,
            dst=peer_name,
            packet_type=PacketType.HANDSHAKE_INIT,
            payload={'public_key': self.public_key}
        )
        
        self.peer_states[peer_name] = ConnectionState.HANDSHAKE_INIT
        self.handshake_timers[peer_name] = time.time()
        
        await self.send_packet(packet)
    
    async def send_packet(self, packet: MockPacket):
        """Send a packet to the network"""
        self.peer_metrics[packet.dst].packets_sent += 1
        self.peer_metrics[packet.dst].bytes_sent += packet.size_bytes
        await self.outbound_queue.put(packet)
    
    async def receive_packet(self, packet: MockPacket):
        """Receive a packet from the network"""
        await self.inbound_queue.put(packet)
    
    async def _process_inbound(self):
        """Process inbound packets"""
        while self.running:
            try:
                packet = await asyncio.wait_for(self.inbound_queue.get(), timeout=0.1)
                
                self.peer_metrics[packet.src].packets_received += 1
                self.peer_metrics[packet.src].bytes_received += packet.size_bytes
                self.peer_metrics[packet.src].last_packet = time.time()
                
                if packet.packet_type == PacketType.HANDSHAKE_INIT:
                    await self._handle_handshake_init(packet)
                elif packet.packet_type == PacketType.HANDSHAKE_RESPONSE:
                    await self._handle_handshake_response(packet)
                elif packet.packet_type == PacketType.KEEPALIVE:
                    await self._handle_keepalive(packet)
                elif packet.packet_type == PacketType.DATA:
                    await self._handle_data(packet)
                    
            except asyncio.TimeoutError:
                continue
    
    async def _handle_handshake_init(self, packet: MockPacket):
        """Handle handshake initiation"""
        peer_name = packet.src
        self.logger.debug(f"{self.name} received handshake init from {peer_name}")
        
        # Send handshake response
        response = MockPacket(
            src=self.name,
            dst=peer_name,
            packet_type=PacketType.HANDSHAKE_RESPONSE,
            payload={'public_key': self.public_key}
        )
        
        self.peer_states[peer_name] = ConnectionState.HANDSHAKE_RESPONSE
        await self.send_packet(response)
    
    async def _handle_handshake_response(self, packet: MockPacket):
        """Handle handshake response"""
        peer_name = packet.src
        self.logger.debug(f"{self.name} received handshake response from {peer_name}")
        
        # Complete handshake
        self.peer_states[peer_name] = ConnectionState.CONNECTED
        self.peer_metrics[peer_name].handshakes_completed += 1
        self.peer_metrics[peer_name].last_handshake = time.time()
        self.peer_metrics[peer_name].connection_established = time.time()
        
        # Start keepalive
        self.keepalive_timers[peer_name] = time.time()
        
        self.logger.info(f"{self.name} established connection with {peer_name}")
    
    async def _handle_keepalive(self, packet: MockPacket):
        """Handle keepalive packet"""
        peer_name = packet.src
        self.keepalive_timers[peer_name] = time.time()
    
    async def _handle_data(self, packet: MockPacket):
        """Handle data packet"""
        # In a real implementation, this would process the data
        pass
    
    async def _process_keepalive(self):
        """Send periodic keepalive packets"""
        while self.running:
            await asyncio.sleep(25)  # WireGuard default keepalive
            
            for peer_name, state in self.peer_states.items():
                if state == ConnectionState.CONNECTED:
                    packet = MockPacket(
                        src=self.name,
                        dst=peer_name,
                        packet_type=PacketType.KEEPALIVE,
                        size_bytes=32
                    )
                    await self.send_packet(packet)
    
    def get_peer_status(self, peer_name: str) -> Dict[str, Any]:
        """Get status of a peer connection"""
        state = self.peer_states.get(peer_name, ConnectionState.DISCONNECTED)
        metrics = self.peer_metrics[peer_name]
        
        return {
            'state': state.value,
            'metrics': {
                'packets_sent': metrics.packets_sent,
                'packets_received': metrics.packets_received,
                'bytes_sent': metrics.bytes_sent,
                'bytes_received': metrics.bytes_received,
                'handshakes': metrics.handshakes_completed,
                'last_handshake': metrics.last_handshake,
                'uptime': time.time() - metrics.connection_established if metrics.connection_established else 0
            }
        }


class MockWireGuardNetwork:
    """Simulates an entire WireGuard mesh network"""
    
    def __init__(self, nodes_file: str, topology_file: str):
        self.logger = get_logger()
        
        # Load configuration
        self.nodes_config = load_nodes(nodes_file)
        self.topology_config = load_topology(topology_file)
        
        # Create network graph
        self.graph = nx.Graph()
        self.mock_nodes: Dict[str, MockWireGuardNode] = {}
        self.network_conditions: Dict[Tuple[str, str], NetworkConditions] = {}
        
        # Initialize network
        self._initialize_network()
        
        # Packet routing
        self.packet_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
    
    def _initialize_network(self):
        """Initialize the network topology"""
        # Create nodes
        for node_config in self.nodes_config:
            name = node_config['name']
            self.graph.add_node(name, **node_config)
            self.mock_nodes[name] = MockWireGuardNode(name, node_config)
        
        # Create edges based on topology
        for peer in self.topology_config:
            from_node = peer['from']
            to_node = peer['to']
            self.graph.add_edge(from_node, to_node, **peer)
            
            # Set network conditions based on geography
            conditions = self._calculate_network_conditions(from_node, to_node)
            self.network_conditions[(from_node, to_node)] = conditions
            self.network_conditions[(to_node, from_node)] = conditions
    
    def _calculate_network_conditions(self, node1: str, node2: str) -> NetworkConditions:
        """Calculate network conditions based on node locations"""
        # Simulate latency based on geographic distance
        region1 = self._get_region(node1)
        region2 = self._get_region(node2)
        
        # Simple latency model
        latency_map = {
            ('US', 'US'): 20,
            ('US', 'EU'): 80,
            ('US', 'ASIA'): 150,
            ('US', 'SA'): 120,
            ('EU', 'EU'): 15,
            ('EU', 'ASIA'): 120,
            ('EU', 'SA'): 180,
            ('ASIA', 'ASIA'): 30,
            ('ASIA', 'SA'): 250,
            ('SA', 'SA'): 40,
        }
        
        key = tuple(sorted([region1, region2]))
        base_latency = latency_map.get(key, 100)
        
        # Add some randomness
        conditions = NetworkConditions(
            latency_ms=base_latency + random.uniform(-10, 10),
            jitter_ms=base_latency * 0.1,
            packet_loss=0.001 if random.random() > 0.95 else 0,  # 5% chance of lossy link
            bandwidth_mbps=1000 if 'CORE' in node1 and 'CORE' in node2 else 100
        )
        
        # Special test cases
        if 'HIGH-LATENCY' in node1 or 'HIGH-LATENCY' in node2:
            conditions.latency_ms = 500
            conditions.jitter_ms = 100
        elif 'PACKET-LOSS' in node1 or 'PACKET-LOSS' in node2:
            conditions.packet_loss = 0.1
        elif 'LOW-BANDWIDTH' in node1 or 'LOW-BANDWIDTH' in node2:
            conditions.bandwidth_mbps = 1
        
        return conditions
    
    def _get_region(self, node_name: str) -> str:
        """Extract region from node name"""
        if 'US' in node_name:
            return 'US'
        elif 'EU' in node_name:
            return 'EU'
        elif 'ASIA' in node_name or 'AP' in node_name:
            return 'ASIA'
        elif 'SA' in node_name:
            return 'SA'
        return 'US'  # Default
    
    async def start(self):
        """Start the network simulation"""
        self.running = True
        self.logger.info("Starting mock WireGuard network simulation")
        
        # Start all nodes
        for node in self.mock_nodes.values():
            await node.start()
        
        # Start packet router
        asyncio.create_task(self._route_packets())
        
        # Establish connections based on topology
        await self._establish_connections()
    
    async def stop(self):
        """Stop the network simulation"""
        self.running = False
        
        # Stop all nodes
        for node in self.mock_nodes.values():
            await node.stop()
        
        self.logger.info("Mock WireGuard network simulation stopped")
    
    async def _establish_connections(self):
        """Establish connections based on topology"""
        for peer in self.topology_config:
            from_node = peer['from']
            to_node = peer['to']
            
            if from_node in self.mock_nodes and to_node in self.mock_nodes:
                from_node_obj = self.mock_nodes[from_node]
                to_node_obj = self.mock_nodes[to_node]
                
                # Initiate connection
                await from_node_obj.connect_to_peer(to_node, to_node_obj.public_key)
    
    async def _route_packets(self):
        """Route packets between nodes with network simulation"""
        while self.running:
            # Collect packets from all nodes
            for node in self.mock_nodes.values():
                try:
                    packet = await asyncio.wait_for(
                        node.outbound_queue.get(), 
                        timeout=0.01
                    )
                    
                    # Apply network conditions
                    conditions = self.network_conditions.get(
                        (packet.src, packet.dst),
                        NetworkConditions()
                    )
                    
                    # Simulate packet loss
                    if random.random() < conditions.packet_loss:
                        self.logger.debug(
                            f"Packet lost: {packet.src} -> {packet.dst} "
                            f"({packet.packet_type.value})"
                        )
                        continue
                    
                    # Simulate latency
                    delay = conditions.get_latency() / 1000.0  # Convert to seconds
                    await asyncio.sleep(delay)
                    
                    # Deliver packet
                    if packet.dst in self.mock_nodes:
                        await self.mock_nodes[packet.dst].receive_packet(packet)
                    
                except asyncio.TimeoutError:
                    continue
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get overall network status"""
        status = {
            'nodes': {},
            'connections': [],
            'statistics': {
                'total_nodes': len(self.mock_nodes),
                'total_edges': self.graph.number_of_edges(),
                'connected_pairs': 0,
                'total_packets': 0,
                'total_bytes': 0
            }
        }
        
        # Collect node status
        for name, node in self.mock_nodes.items():
            node_status = {
                'role': node.role,
                'ip': node.ip,
                'peers': {}
            }
            
            for peer_name in self.graph.neighbors(name):
                if peer_name in node.peer_states:
                    node_status['peers'][peer_name] = node.get_peer_status(peer_name)
                    
                    if node.peer_states[peer_name] == ConnectionState.CONNECTED:
                        status['statistics']['connected_pairs'] += 0.5  # Count each direction
            
            status['nodes'][name] = node_status
            
            # Aggregate statistics
            for metrics in node.peer_metrics.values():
                status['statistics']['total_packets'] += metrics.packets_sent
                status['statistics']['total_bytes'] += metrics.bytes_sent
        
        # Collect connection status
        for edge in self.graph.edges():
            from_node, to_node = edge
            conditions = self.network_conditions.get((from_node, to_node))
            
            connection = {
                'from': from_node,
                'to': to_node,
                'latency_ms': conditions.latency_ms if conditions else 0,
                'packet_loss': conditions.packet_loss if conditions else 0,
                'bandwidth_mbps': conditions.bandwidth_mbps if conditions else 0
            }
            
            # Add connection state
            if from_node in self.mock_nodes:
                state = self.mock_nodes[from_node].peer_states.get(
                    to_node, 
                    ConnectionState.DISCONNECTED
                )
                connection['state'] = state.value
            
            status['connections'].append(connection)
        
        return status
    
    async def simulate_failure(self, node_name: str):
        """Simulate node failure"""
        if node_name in self.mock_nodes:
            self.logger.warning(f"Simulating failure of node {node_name}")
            await self.mock_nodes[node_name].stop()
            
            # Mark all connections as disconnected
            for other_node in self.mock_nodes.values():
                if node_name in other_node.peer_states:
                    other_node.peer_states[node_name] = ConnectionState.DISCONNECTED
    
    async def simulate_recovery(self, node_name: str):
        """Simulate node recovery"""
        if node_name in self.mock_nodes:
            self.logger.info(f"Simulating recovery of node {node_name}")
            await self.mock_nodes[node_name].start()
            
            # Re-establish connections
            for peer in self.topology_config:
                if peer['from'] == node_name:
                    to_node = peer['to']
                    if to_node in self.mock_nodes:
                        await self.mock_nodes[node_name].connect_to_peer(
                            to_node,
                            self.mock_nodes[to_node].public_key
                        )
    
    def find_path(self, src: str, dst: str) -> Optional[List[str]]:
        """Find path between two nodes"""
        try:
            return nx.shortest_path(self.graph, src, dst)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def calculate_path_latency(self, path: List[str]) -> float:
        """Calculate total latency for a path"""
        total_latency = 0
        
        for i in range(len(path) - 1):
            conditions = self.network_conditions.get(
                (path[i], path[i + 1]),
                NetworkConditions()
            )
            total_latency += conditions.latency_ms
        
        return total_latency


async def run_simulation_demo():
    """Demo simulation of the super complex network"""
    logger = get_logger()
    
    # Create mock network
    network = MockWireGuardNetwork(
        "examples/super_complex_nodes.yaml",
        "examples/super_complex_topology.yaml"
    )
    
    # Start simulation
    await network.start()
    logger.info("Network simulation started")
    
    # Let connections establish
    await asyncio.sleep(5)
    
    # Get initial status
    status = network.get_network_status()
    logger.info(f"Network status: {status['statistics']}")
    
    # Test path finding
    path = network.find_path("CLIENT-USE-001", "CLIENT-AP-001")
    if path:
        latency = network.calculate_path_latency(path)
        logger.info(f"Path from CLIENT-USE-001 to CLIENT-AP-001: {' -> '.join(path)}")
        logger.info(f"Total latency: {latency:.2f} ms")
    
    # Simulate node failure
    await network.simulate_failure("CORE-US-EAST")
    await asyncio.sleep(2)
    
    # Check alternative path
    path = network.find_path("CLIENT-USE-001", "CLIENT-AP-001")
    if path:
        latency = network.calculate_path_latency(path)
        logger.info(f"Alternative path after CORE-US-EAST failure: {' -> '.join(path)}")
        logger.info(f"New latency: {latency:.2f} ms")
    
    # Simulate recovery
    await network.simulate_recovery("CORE-US-EAST")
    await asyncio.sleep(2)
    
    # Final status
    final_status = network.get_network_status()
    logger.info(f"Final network status: {final_status['statistics']}")
    
    # Stop simulation
    await network.stop()


if __name__ == "__main__":
    # Run the demo
    asyncio.run(run_simulation_demo())