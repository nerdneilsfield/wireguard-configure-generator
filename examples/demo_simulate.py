#!/usr/bin/env python3
"""
Demo script for network simulation functionality
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from wg_mesh_gen.group_network_builder import GroupNetworkBuilder
from wg_mesh_gen.wg_mock import MockWireGuardNetwork
from wg_mesh_gen.logger import get_logger
import json
import tempfile


async def simulate_network(group_config_path: str):
    """Run network simulation"""
    logger = get_logger()
    
    logger.info(f"Loading group configuration: {group_config_path}")
    
    # Build network from group config
    builder = GroupNetworkBuilder(group_config_path)
    nodes, peers = builder.build()
    
    logger.info(f"Built {len(nodes)} nodes and {len(peers)} peer connections")
    
    # Create temporary files for mock network
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as nodes_tmp:
        json.dump({'nodes': nodes}, nodes_tmp)
        nodes_file = nodes_tmp.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as topo_tmp:
        json.dump({'peers': peers}, topo_tmp)
        topo_file = topo_tmp.name
    
    try:
        # Create and start mock network
        logger.info("Creating mock network...")
        network = MockWireGuardNetwork(nodes_file, topo_file)
        
        await network.start()
        logger.info("Network started, waiting for connections to establish...")
        await asyncio.sleep(3)
        
        # Get initial status
        status = network.get_network_status()
        stats = status['statistics']
        logger.info(f"Initial network state: {stats['connected_pairs']} connections established")
        
        # Test connectivity
        logger.info("\n=== Testing Node Connectivity ===")
        nodes_list = list(network.mock_nodes.keys())
        
        reachable = 0
        unreachable = 0
        
        for i, src in enumerate(nodes_list):
            for dst in nodes_list[i+1:]:
                path = network.find_path(src, dst)
                if path:
                    latency = network.calculate_path_latency(path)
                    logger.info(f"{src} -> {dst}: Reachable (path: {' -> '.join(path)}, latency: {latency:.2f}ms)")
                    reachable += 1
                else:
                    logger.warning(f"{src} -> {dst}: Unreachable")
                    unreachable += 1
        
        logger.info(f"\nConnectivity Summary: {reachable} reachable, {unreachable} unreachable")
        
        # Test routing through relays
        logger.info("\n=== Testing Routing Paths ===")
        
        relay_nodes = [name for name, node in network.mock_nodes.items() 
                      if node.ip_forward_enabled]
        
        if relay_nodes:
            logger.info(f"Found {len(relay_nodes)} relay nodes: {', '.join(relay_nodes)}")
            
            # Show some key routing paths
            for relay in relay_nodes[:2]:  # Show first 2 relays
                logger.info(f"\nRoutes through {relay}:")
                routes_shown = 0
                
                for src_name in nodes_list:
                    if src_name == relay:
                        continue
                    
                    for dst_name in nodes_list:
                        if dst_name in [src_name, relay]:
                            continue
                        
                        path = network.find_path(src_name, dst_name)
                        if path and relay in path:
                            logger.info(f"  {src_name} -> {relay} -> {dst_name}")
                            routes_shown += 1
                            
                            if routes_shown >= 5:  # Show max 5 routes per relay
                                logger.info("  ... (more routes omitted)")
                                break
                    
                    if routes_shown >= 5:
                        break
        
        # Simulate failure of a relay node
        if relay_nodes:
            failure_node = relay_nodes[0]
            logger.info(f"\n=== Simulating Failure of Relay Node: {failure_node} ===")
            
            await network.simulate_failure(failure_node)
            await asyncio.sleep(2)
            
            failure_status = network.get_network_status()
            logger.info(f"After failure: {failure_status['statistics']['connected_pairs']} connections active")
            
            # Test impact
            logger.info(f"\nTesting connectivity without {failure_node}:")
            impacted = 0
            for src in nodes_list[:3]:  # Test first 3 nodes
                if src != failure_node:
                    for dst in nodes_list[-3:]:  # To last 3 nodes
                        if dst != failure_node and dst != src:
                            path = network.find_path(src, dst)
                            if not path:
                                logger.warning(f"  {src} -> {dst}: Now unreachable")
                                impacted += 1
                            else:
                                logger.info(f"  {src} -> {dst}: Still reachable via {' -> '.join(path)}")
            
            if impacted > 0:
                logger.warning(f"{impacted} connections impacted by {failure_node} failure")
            
            # Recover
            logger.info(f"\nRecovering {failure_node}...")
            await network.simulate_recovery(failure_node)
            await asyncio.sleep(2)
            
            recovery_status = network.get_network_status()
            logger.info(f"After recovery: {recovery_status['statistics']['connected_pairs']} connections active")
        
        # Final statistics
        await asyncio.sleep(2)
        final_status = network.get_network_status()
        final_stats = final_status['statistics']
        
        logger.info("\n=== Final Network Statistics ===")
        logger.info(f"Total nodes: {final_stats['total_nodes']}")
        logger.info(f"Total edges: {final_stats['total_edges']}")
        logger.info(f"Active connections: {int(final_stats['connected_pairs'])}")
        logger.info(f"Total packets: {final_stats['total_packets']}")
        logger.info(f"Total bytes: {final_stats['total_bytes']}")
        
        # Stop network
        await network.stop()
        logger.info("\nSimulation completed!")
        
    finally:
        # Clean up temp files
        import os
        try:
            os.unlink(nodes_file)
            os.unlink(topo_file)
        except:
            pass


def main():
    """Main function"""
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        # Default to layered routing example
        config_file = "examples/group_layered_routing.yaml"
    
    if not Path(config_file).exists():
        print(f"Error: Configuration file not found: {config_file}")
        sys.exit(1)
    
    print(f"Running network simulation with: {config_file}")
    asyncio.run(simulate_network(config_file))


if __name__ == "__main__":
    main()