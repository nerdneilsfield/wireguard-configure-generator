"""
Demo script for layered routing with group network configuration

This demonstrates the cross-border network scenario with proper routing
through relay nodes when direct connections are blocked (e.g., by GFW).
"""

import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from wg_mesh_gen.group_network_builder import GroupNetworkBuilder
from wg_mesh_gen.builder import build_from_data
from wg_mesh_gen.render import ConfigRenderer
from wg_mesh_gen.wg_mock import MockWireGuardNetwork, MockPacket, PacketType
from wg_mesh_gen.logger import get_logger


async def simulate_layered_routing():
    """Simulate the layered routing scenario"""
    logger = get_logger()
    
    # Use the layered routing configuration
    config_file = Path(__file__).parent / "group_layered_routing.yaml"
    
    logger.info("=== Building configurations from group network ===")
    
    # Build nodes and peers from group config
    builder = GroupNetworkBuilder(str(config_file))
    nodes, peers = builder.build()
    
    logger.info(f"Generated {len(nodes)} nodes and {len(peers)} peer connections")
    
    # Show routing summary
    logger.info("\n=== Routing Summary ===")
    
    # Group nodes by their groups
    groups = {}
    for node in nodes:
        group = node.get('group', 'unknown')
        if group not in groups:
            groups[group] = []
        groups[group].append(node['name'])
    
    for group_name, group_nodes in groups.items():
        logger.info(f"\n{group_name}: {', '.join(group_nodes)}")
    
    # Show key routing paths
    logger.info("\n=== Key Routing Paths ===")
    
    # Find office -> overseas path
    office_peers = [p for p in peers if p['from'] in groups.get('office', [])]
    logger.info("\nOffice nodes can reach:")
    for peer in office_peers:
        logger.info(f"  {peer['from']} -> {peer['to']}: {peer['allowed_ips']}")
    
    # Find the bridge connection
    bridge_peers = [p for p in peers if 'G' in p['from'] and 'H' in p['to']]
    if bridge_peers:
        logger.info(f"\nCross-border bridge: {bridge_peers[0]['from']} <-> {bridge_peers[0]['to']}")
        logger.info(f"  Using special endpoints for tunneling")
    
    # Generate configurations
    logger.info("\n=== Generating WireGuard Configurations ===")
    
    output_dir = Path("/tmp/layered_routing_demo")
    output_dir.mkdir(exist_ok=True)
    
    # Build configurations
    build_result = build_from_data({"nodes": nodes}, {"peers": peers}, output_dir)
    
    # Render configurations to files
    renderer = ConfigRenderer()
    renderer.render_all(build_result)
    
    logger.info(f"Generated {len(build_result['configs'])} configuration files in {output_dir}")
    
    # Show relay nodes
    relay_nodes = [n for n in nodes if n.get('role') == 'relay']
    if relay_nodes:
        relay_node = relay_nodes[0]
        logger.info(f"\nSample relay configuration ({relay_node['name']}):")
        if relay_node.get('post_up'):
            logger.info("  PostUp scripts:")
            for script in relay_node.get('post_up', []):
                logger.info(f"    {script}")
    
    # Simulate with mock network
    logger.info("\n=== Simulating Network Traffic ===")
    
    # Save nodes and peers for mock network
    import json
    nodes_file = output_dir / "mock_nodes.json"
    topology_file = output_dir / "mock_topology.json"
    
    with open(nodes_file, 'w') as f:
        json.dump({"nodes": nodes}, f, indent=2)
    
    with open(topology_file, 'w') as f:
        json.dump({"peers": peers}, f, indent=2)
    
    # Create mock network
    network = MockWireGuardNetwork(str(nodes_file), str(topology_file))
    
    await network.start()
    logger.info("Mock network started, establishing connections...")
    
    # Let connections establish
    await asyncio.sleep(3)
    
    # Test routing from office to overseas
    logger.info("\n=== Testing Cross-Border Routing ===")
    
    # Find an office node and overseas node
    office_node = next((n for n in nodes if n['name'] in groups.get('office', [])), None)
    overseas_node = next((n for n in nodes if n['name'] in groups.get('overseas', []) and 'relay' not in n.get('role', '')), None)
    
    if office_node and overseas_node:
        logger.info(f"\nSending packet from {office_node['name']} to {overseas_node['name']}")
        logger.info(f"  Source IP: {office_node['wireguard_ip']}")
        logger.info(f"  Destination IP: {overseas_node['wireguard_ip']}")
        
        # Extract IPs
        import ipaddress
        dest_ip = str(ipaddress.ip_interface(overseas_node['wireguard_ip']).ip)
        
        # Send packet
        mock_office = network.mock_nodes[office_node['name']]
        packet = MockPacket(
            src=office_node['name'],
            dst='G',  # First hop to China relay
            packet_type=PacketType.DATA,
            payload={
                'destination_ip': dest_ip,
                'data': 'Hello from China office!',
                'trace_route': [office_node['name']]
            }
        )
        
        await mock_office.send_packet(packet)
        
        # Give time for packet to route
        await asyncio.sleep(1)
        
        # Check network status
        status = network.get_network_status()
        
        # Show routing hops
        logger.info("\nExpected routing path:")
        logger.info(f"  1. {office_node['name']} -> G (China relay)")
        logger.info(f"  2. G -> H (Cross-border via special tunnel)")
        logger.info(f"  3. H -> {overseas_node['name']} (Overseas destination)")
    
    # Test failure scenario
    logger.info("\n=== Testing Failure Scenario ===")
    logger.info("Simulating China relay (G) failure...")
    
    await network.simulate_failure('G')
    await asyncio.sleep(1)
    
    logger.info("With G down, office nodes cannot reach overseas (as expected)")
    
    # Recovery
    logger.info("\nSimulating recovery...")
    await network.simulate_recovery('G')
    await asyncio.sleep(2)
    
    logger.info("Connections re-established after recovery")
    
    # Final status
    final_status = network.get_network_status()
    logger.info(f"\nFinal network statistics:")
    logger.info(f"  Total packets: {final_status['statistics']['total_packets']}")
    logger.info(f"  Connected pairs: {int(final_status['statistics']['connected_pairs'])}")
    
    await network.stop()
    logger.info("\nSimulation completed!")


def main():
    """Run the demo"""
    # Run simulation
    asyncio.run(simulate_layered_routing())


if __name__ == "__main__":
    main()