#!/usr/bin/env python3
"""
WireGuard Mock Framework Demo

This script demonstrates the capabilities of the WireGuard mock framework
with the super complex topology.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wg_mesh_gen.wg_mock import MockWireGuardNetwork
from wg_mesh_gen.logger import get_logger
import time


async def demo_basic_connectivity(network):
    """Demonstrate basic connectivity testing"""
    logger = get_logger()
    logger.info("\n=== Demo: Basic Connectivity ===")
    
    # Test connectivity between different regions
    test_pairs = [
        ("CLIENT-USE-001", "CLIENT-USE-010"),  # Same region
        ("CLIENT-USE-001", "CLIENT-EUC-001"),   # US to EU
        ("CLIENT-USE-001", "CLIENT-AP-001"),    # US to Asia
        ("CLIENT-EUC-001", "CLIENT-SA-001"),    # EU to South America
    ]
    
    for src, dst in test_pairs:
        path = network.find_path(src, dst)
        if path:
            latency = network.calculate_path_latency(path)
            logger.info(f"Path {src} -> {dst}: {' -> '.join(path)}")
            logger.info(f"  Total latency: {latency:.2f} ms")
            logger.info(f"  Hops: {len(path) - 1}")
        else:
            logger.error(f"No path found from {src} to {dst}")


async def demo_failure_scenarios(network):
    """Demonstrate network failure handling"""
    logger = get_logger()
    logger.info("\n=== Demo: Failure Scenarios ===")
    
    # Get initial path
    src, dst = "CLIENT-USE-001", "CLIENT-AP-001"
    initial_path = network.find_path(src, dst)
    initial_latency = network.calculate_path_latency(initial_path)
    logger.info(f"Initial path {src} -> {dst}: {' -> '.join(initial_path)}")
    logger.info(f"Initial latency: {initial_latency:.2f} ms")
    
    # Simulate core node failure
    logger.info("\nSimulating CORE-US-EAST failure...")
    await network.simulate_failure("CORE-US-EAST")
    await asyncio.sleep(1)
    
    # Find alternative path
    alt_path = network.find_path(src, dst)
    if alt_path:
        alt_latency = network.calculate_path_latency(alt_path)
        logger.info(f"Alternative path: {' -> '.join(alt_path)}")
        logger.info(f"Alternative latency: {alt_latency:.2f} ms")
        logger.info(f"Latency increase: {alt_latency - initial_latency:.2f} ms")
    else:
        logger.error("No alternative path found!")
    
    # Simulate multiple failures
    logger.info("\nSimulating cascading failures...")
    await network.simulate_failure("CORE-US-WEST")
    await asyncio.sleep(1)
    
    # Check connectivity
    remaining_path = network.find_path(src, dst)
    if remaining_path:
        logger.info(f"Path still available through: {' -> '.join(remaining_path)}")
    else:
        logger.error("Network partitioned - no path available!")
    
    # Recovery
    logger.info("\nSimulating recovery...")
    await network.simulate_recovery("CORE-US-EAST")
    await network.simulate_recovery("CORE-US-WEST")
    await asyncio.sleep(2)
    
    # Check restored path
    restored_path = network.find_path(src, dst)
    if restored_path:
        logger.info(f"Connectivity restored: {' -> '.join(restored_path)}")


async def demo_performance_metrics(network):
    """Demonstrate performance monitoring"""
    logger = get_logger()
    logger.info("\n=== Demo: Performance Metrics ===")
    
    # Let network run for a bit
    await asyncio.sleep(5)
    
    # Get network status
    status = network.get_network_status()
    stats = status['statistics']
    
    logger.info(f"Network Statistics:")
    logger.info(f"  Total nodes: {stats['total_nodes']}")
    logger.info(f"  Total connections: {stats['total_edges']}")
    logger.info(f"  Connected pairs: {int(stats['connected_pairs'])}")
    logger.info(f"  Total packets sent: {stats['total_packets']}")
    logger.info(f"  Total bytes transferred: {stats['total_bytes']}")
    
    # Sample node metrics
    sample_nodes = ["CORE-US-EAST", "AGG-USE-DC1", "CLIENT-USE-001"]
    for node_name in sample_nodes:
        if node_name in status['nodes']:
            node_info = status['nodes'][node_name]
            logger.info(f"\nNode {node_name} ({node_info['role']}):")
            
            total_sent = 0
            total_received = 0
            connected_peers = 0
            
            for peer_name, peer_status in node_info['peers'].items():
                if peer_status['state'] == 'connected':
                    connected_peers += 1
                    metrics = peer_status['metrics']
                    total_sent += metrics['packets_sent']
                    total_received += metrics['packets_received']
            
            logger.info(f"  Connected peers: {connected_peers}")
            logger.info(f"  Packets sent: {total_sent}")
            logger.info(f"  Packets received: {total_received}")


async def demo_special_nodes(network):
    """Demonstrate special test nodes behavior"""
    logger = get_logger()
    logger.info("\n=== Demo: Special Test Nodes ===")
    
    # Test high latency node
    logger.info("\nTesting HIGH-LATENCY node...")
    path = network.find_path("CLIENT-USE-001", "TEST-HIGH-LATENCY")
    if path:
        latency = network.calculate_path_latency(path)
        logger.info(f"Path to HIGH-LATENCY: {' -> '.join(path)}")
        logger.info(f"Total latency: {latency:.2f} ms (should be very high)")
    
    # Test packet loss node
    logger.info("\nTesting PACKET-LOSS node...")
    conditions = network._calculate_network_conditions("CLIENT-USE-001", "TEST-PACKET-LOSS")
    logger.info(f"Packet loss rate to PACKET-LOSS node: {conditions.packet_loss * 100:.1f}%")
    
    # Test low bandwidth node
    logger.info("\nTesting LOW-BANDWIDTH node...")
    conditions = network._calculate_network_conditions("CLIENT-USE-001", "TEST-LOW-BANDWIDTH")
    logger.info(f"Bandwidth to LOW-BANDWIDTH node: {conditions.bandwidth_mbps} Mbps")


async def demo_redundancy_analysis(network):
    """Analyze network redundancy"""
    logger = get_logger()
    logger.info("\n=== Demo: Redundancy Analysis ===")
    
    # Analyze core node redundancy
    core_nodes = [name for name in network.mock_nodes if "CORE" in name]
    logger.info(f"Core nodes: {len(core_nodes)}")
    
    # Test connectivity with each core node failed
    test_src, test_dst = "CLIENT-USE-001", "CLIENT-AP-001"
    
    for core_node in core_nodes:
        # Temporarily remove node from graph
        neighbors = list(network.graph.neighbors(core_node))
        network.graph.remove_node(core_node)
        
        # Check if path still exists
        path = network.find_path(test_src, test_dst)
        
        # Restore node
        network.graph.add_node(core_node)
        for neighbor in neighbors:
            network.graph.add_edge(core_node, neighbor)
        
        if path:
            logger.info(f"✓ Network survives {core_node} failure")
        else:
            logger.warning(f"✗ Network partitioned if {core_node} fails")


async def main():
    """Run all demos"""
    logger = get_logger()
    
    logger.info("Starting WireGuard Mock Framework Demo")
    logger.info("=====================================")
    
    # Create mock network
    network = MockWireGuardNetwork(
        "examples/super_complex_nodes.yaml",
        "examples/super_complex_topology.yaml"
    )
    
    # Start network
    await network.start()
    logger.info(f"Mock network started with {len(network.mock_nodes)} nodes")
    
    # Wait for initial connections
    logger.info("Establishing initial connections...")
    await asyncio.sleep(3)
    
    # Run demos
    await demo_basic_connectivity(network)
    await demo_performance_metrics(network)
    await demo_failure_scenarios(network)
    await demo_special_nodes(network)
    await demo_redundancy_analysis(network)
    
    # Final statistics
    logger.info("\n=== Final Network Statistics ===")
    final_status = network.get_network_status()
    stats = final_status['statistics']
    logger.info(f"Total packets: {stats['total_packets']}")
    logger.info(f"Total bytes: {stats['total_bytes']}")
    logger.info(f"Connected pairs: {int(stats['connected_pairs'])}")
    
    # Stop network
    await network.stop()
    logger.info("\nDemo completed!")


if __name__ == "__main__":
    asyncio.run(main())