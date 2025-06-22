"""
Network simulation functionality for WireGuard configurations
"""

import asyncio
import json
import tempfile
import os
from typing import Optional, Dict, Any
from pathlib import Path

from .wg_mock import MockWireGuardNetwork
from .group_network_builder import GroupNetworkBuilder
from .logger import get_logger


class NetworkSimulator:
    """Simulate WireGuard network connectivity and routing"""
    
    def __init__(self):
        self.logger = get_logger()
    
    async def simulate_network(
        self,
        nodes_file: Optional[str] = None,
        topo_file: Optional[str] = None,
        group_config: Optional[str] = None,
        test_routes: bool = False,
        test_connectivity: bool = False,
        duration: int = 10,
        failure_node: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run network simulation
        
        Args:
            nodes_file: Path to nodes configuration file
            topo_file: Path to topology configuration file
            group_config: Path to group configuration file
            test_routes: Whether to test routing paths
            test_connectivity: Whether to test node connectivity
            duration: Simulation duration in seconds
            failure_node: Node to simulate failure for
            
        Returns:
            Simulation results
        """
        temp_files = []
        
        try:
            # Handle group config
            if group_config:
                self.logger.info("使用组网络配置模式")
                
                if not os.path.exists(group_config):
                    raise FileNotFoundError(f"Group config file not found: {group_config}")
                
                # Convert group config
                builder = GroupNetworkBuilder(group_config)
                nodes, peers = builder.build()
                
                # Create temporary files
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as nodes_tmp:
                    json.dump({'nodes': nodes}, nodes_tmp)
                    nodes_file = nodes_tmp.name
                    temp_files.append(nodes_file)
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as topo_tmp:
                    json.dump({'peers': peers}, topo_tmp)
                    topo_file = topo_tmp.name
                    temp_files.append(topo_file)
            else:
                # Traditional mode
                if not nodes_file or not topo_file:
                    raise ValueError("Please provide nodes-file and topo-file or group-config")
                
                if not os.path.exists(nodes_file):
                    raise FileNotFoundError(f"Nodes file not found: {nodes_file}")
                
                if not os.path.exists(topo_file):
                    raise FileNotFoundError(f"Topology file not found: {topo_file}")
            
            # Create mock network
            self.logger.info("创建模拟网络...")
            network = MockWireGuardNetwork(nodes_file, topo_file)
            
            # Start network
            await network.start()
            self.logger.info("网络启动完成，等待连接建立...")
            await asyncio.sleep(3)
            
            # Get initial status
            initial_status = network.get_network_status()
            self.logger.info(f"网络初始状态: {initial_status['statistics']['connected_pairs']} 个连接已建立")
            
            results = {
                'initial_status': initial_status,
                'connectivity_tests': [],
                'routing_tests': [],
                'failure_tests': []
            }
            
            # Test connectivity if requested
            if test_connectivity:
                self.logger.info("\n=== 测试节点连通性 ===")
                results['connectivity_tests'] = await self._test_connectivity(network)
            
            # Test routes if requested
            if test_routes:
                self.logger.info("\n=== 测试路由路径 ===")
                results['routing_tests'] = await self._test_routes(network)
            
            # Simulate failure if requested
            if failure_node:
                self.logger.info(f"\n=== 模拟节点故障: {failure_node} ===")
                results['failure_tests'] = await self._test_failure(network, failure_node)
            
            # Run for specified duration
            self.logger.info(f"\n运行模拟 {duration} 秒...")
            await asyncio.sleep(duration)
            
            # Final statistics
            final_status = network.get_network_status()
            stats = final_status['statistics']
            
            self.logger.info("\n=== 最终统计 ===")
            self.logger.info(f"总节点数: {stats['total_nodes']}")
            self.logger.info(f"总连接数: {stats['total_edges']}")
            self.logger.info(f"活动连接: {int(stats['connected_pairs'])}")
            self.logger.info(f"总数据包: {stats['total_packets']}")
            self.logger.info(f"总字节数: {stats['total_bytes']}")
            
            results['final_status'] = final_status
            
            # Stop network
            await network.stop()
            
            self.logger.info("\n模拟完成!")
            
            return results
            
        finally:
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
    
    async def _test_connectivity(self, network: MockWireGuardNetwork) -> list:
        """Test connectivity between all node pairs"""
        nodes_list = list(network.mock_nodes.keys())
        results = []
        
        for i, src in enumerate(nodes_list):
            for dst in nodes_list[i+1:]:
                path = network.find_path(src, dst)
                if path:
                    latency = network.calculate_path_latency(path)
                    self.logger.info(f"{src} -> {dst}: 可达 (路径: {' -> '.join(path)}, 延迟: {latency:.2f}ms)")
                    results.append({
                        'src': src,
                        'dst': dst,
                        'reachable': True,
                        'path': path,
                        'latency': latency
                    })
                else:
                    self.logger.warning(f"{src} -> {dst}: 不可达")
                    results.append({
                        'src': src,
                        'dst': dst,
                        'reachable': False
                    })
        
        reachable = len([r for r in results if r['reachable']])
        unreachable = len([r for r in results if not r['reachable']])
        self.logger.info(f"\n连通性汇总: {reachable} 可达, {unreachable} 不可达")
        
        return results
    
    async def _test_routes(self, network: MockWireGuardNetwork) -> list:
        """Test routing paths through relay nodes"""
        results = []
        
        # Find relay nodes
        relay_nodes = [name for name, node in network.mock_nodes.items() 
                      if node.ip_forward_enabled]
        
        if relay_nodes:
            self.logger.info(f"发现 {len(relay_nodes)} 个中继节点: {', '.join(relay_nodes)}")
            
            # Test routing through relays
            for relay in relay_nodes:
                self.logger.info(f"\n通过 {relay} 的路由:")
                relay_routes = []
                
                nodes_list = list(network.mock_nodes.keys())
                for src_name in nodes_list:
                    if src_name == relay:
                        continue
                    
                    for dst_name in nodes_list:
                        if dst_name in [src_name, relay]:
                            continue
                        
                        path = network.find_path(src_name, dst_name)
                        if path and relay in path:
                            self.logger.info(f"  {src_name} -> {relay} -> {dst_name}")
                            relay_routes.append({
                                'src': src_name,
                                'relay': relay,
                                'dst': dst_name,
                                'path': path
                            })
                
                results.append({
                    'relay': relay,
                    'routes': relay_routes
                })
        else:
            self.logger.info("未发现中继节点")
        
        return results
    
    async def _test_failure(self, network: MockWireGuardNetwork, failure_node: str) -> dict:
        """Test network behavior when a node fails"""
        result = {
            'failed_node': failure_node,
            'before_failure': {},
            'during_failure': {},
            'after_recovery': {}
        }
        
        if failure_node not in network.mock_nodes:
            self.logger.warning(f"节点 {failure_node} 不存在")
            return result
        
        # Before failure status
        before_status = network.get_network_status()
        result['before_failure'] = {
            'connected_pairs': before_status['statistics']['connected_pairs']
        }
        
        # Simulate failure
        await network.simulate_failure(failure_node)
        await asyncio.sleep(2)
        
        failure_status = network.get_network_status()
        self.logger.info(f"故障后连接数: {failure_status['statistics']['connected_pairs']}")
        result['during_failure'] = {
            'connected_pairs': failure_status['statistics']['connected_pairs']
        }
        
        # Test connectivity during failure
        self.logger.info("\n故障后连通性:")
        impacted_connections = []
        
        for name, node in network.mock_nodes.items():
            if name != failure_node:
                connected_peers = [p for p, s in node.peer_states.items() 
                                 if str(s.value) == 'connected']
                self.logger.info(f"  {name}: {len(connected_peers)} 个活动连接")
                
                # Check if this node was connected to the failed node
                if failure_node in node.peer_states:
                    impacted_connections.append(name)
        
        result['during_failure']['impacted_nodes'] = impacted_connections
        
        # Recover
        self.logger.info(f"\n恢复节点 {failure_node}...")
        await network.simulate_recovery(failure_node)
        await asyncio.sleep(2)
        
        recovery_status = network.get_network_status()
        self.logger.info(f"恢复后连接数: {recovery_status['statistics']['connected_pairs']}")
        result['after_recovery'] = {
            'connected_pairs': recovery_status['statistics']['connected_pairs']
        }
        
        return result


def run_simulation(
    nodes_file: Optional[str] = None,
    topo_file: Optional[str] = None,
    group_config: Optional[str] = None,
    test_routes: bool = False,
    test_connectivity: bool = False,
    duration: int = 10,
    failure_node: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for network simulation
    
    Returns:
        Simulation results
    """
    simulator = NetworkSimulator()
    
    return asyncio.run(simulator.simulate_network(
        nodes_file=nodes_file,
        topo_file=topo_file,
        group_config=group_config,
        test_routes=test_routes,
        test_connectivity=test_connectivity,
        duration=duration,
        failure_node=failure_node
    ))