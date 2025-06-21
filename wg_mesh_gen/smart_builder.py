"""
Smart WireGuard configuration builder with route optimization
"""

from typing import List, Dict, Any, Optional
from .builder import build_peer_configs
from .route_optimizer import RouteOptimizer
from .loader import load_nodes, load_topology
from .logger import get_logger


class SmartConfigBuilder:
    """Smart configuration builder with route optimization"""
    
    def __init__(self, nodes_file: str, topology_file: str):
        """
        Initialize smart builder.
        
        Args:
            nodes_file: Path to nodes configuration file
            topology_file: Path to topology configuration file
        """
        self.logger = get_logger()
        self.nodes_file = nodes_file
        self.topology_file = topology_file
        
        # Don't load configurations here to avoid duplicate loading
        self.nodes = None
        self.peers = None
        self.optimizer = None
        
    def build_optimized_configs(self, 
                               output_dir: str = "out",
                               auto_generate_keys: bool = True,
                               db_path: str = "wg_keys.json",
                               enable_multipath: bool = False) -> Dict[str, Any]:
        """
        Build optimized WireGuard configurations.
        
        Args:
            output_dir: Output directory for configuration files
            auto_generate_keys: Whether to auto-generate missing keys
            db_path: Path to key storage database
            enable_multipath: Enable multipath routing
            
        Returns:
            Dictionary containing build results with optimization data
        """
        self.logger.info("开始构建优化的WireGuard配置")
        
        # Build basic configurations first - this will load the configurations
        build_result = build_peer_configs(
            nodes_file=self.nodes_file,
            topology_file=self.topology_file,
            output_dir=output_dir,
            auto_generate_keys=auto_generate_keys,
            db_path=db_path
        )
        
        # Now extract the loaded data from build result to avoid duplicate loading
        # build_peer_configs internally loads the configurations, so we reuse them
        if self.nodes is None or self.peers is None:
            # Load configurations only if not already loaded
            self.nodes = load_nodes(self.nodes_file)
            self.peers = load_topology(self.topology_file)
            self.optimizer = RouteOptimizer(self.nodes, self.peers)
        
        # Analyze network performance
        performance_metrics = self.optimizer.analyze_network_performance()
        self.logger.info(f"网络性能指标: {performance_metrics}")
        
        # Detect bottlenecks
        bottlenecks = self.optimizer.detect_bottlenecks()
        if bottlenecks:
            self.logger.warning(f"检测到网络瓶颈: {bottlenecks}")
        
        # Optimize routes
        optimized_routes = self.optimizer.optimize_mesh_routes()
        
        # Apply route optimizations to configurations
        if enable_multipath:
            self._apply_multipath_optimization(build_result, optimized_routes)
        else:
            self._apply_single_path_optimization(build_result, optimized_routes)
        
        # Add optimization data to result
        build_result['optimization'] = {
            'performance_metrics': performance_metrics,
            'bottlenecks': bottlenecks,
            'optimized_routes': optimized_routes,
            'multipath_enabled': enable_multipath
        }
        
        self.logger.info("优化配置构建完成")
        return build_result
    
    def _apply_single_path_optimization(self, 
                                       build_result: Dict[str, Any], 
                                       optimized_routes: Dict[str, Dict[str, List[str]]]):
        """Apply single-path route optimization"""
        self.logger.debug("应用单路径路由优化")
        
        configs = build_result['configs']
        
        for node_name, config in configs.items():
            # Update allowed IPs based on optimal routes
            for peer in config['peers']:
                peer_name = peer['name']
                
                # Find optimal path to this peer
                if node_name in optimized_routes and peer_name in optimized_routes[node_name]:
                    optimal_path = optimized_routes[node_name][peer_name]
                    
                    # If path goes through relays, update allowed IPs accordingly
                    if len(optimal_path) > 2:  # Path has intermediate nodes
                        self._update_allowed_ips_for_path(peer, optimal_path)
    
    def _apply_multipath_optimization(self, 
                                     build_result: Dict[str, Any], 
                                     optimized_routes: Dict[str, Dict[str, List[str]]]):
        """Apply multipath route optimization"""
        self.logger.debug("应用多路径路由优化")
        
        configs = build_result['configs']
        
        for node_name, config in configs.items():
            # Find alternative paths for each peer
            for peer in config['peers']:
                peer_name = peer['name']
                
                # Find all possible paths
                all_paths = self.optimizer.find_all_paths(node_name, peer_name)
                
                if len(all_paths) > 1:
                    # Multiple paths available, configure for load balancing
                    self._configure_multipath_peer(peer, all_paths)
    
    def _update_allowed_ips_for_path(self, peer: Dict[str, Any], path: List[str]):
        """Update allowed IPs for a specific path"""
        # This is a simplified implementation
        # In practice, you might want to be more specific about routing
        if not peer.get('allowed_ips'):
            peer['allowed_ips'] = ['0.0.0.0/0']  # Default route through this peer
    
    def _configure_multipath_peer(self, peer: Dict[str, Any], paths: List[List[str]]):
        """Configure peer for multipath routing"""
        # This is a placeholder for multipath configuration
        # WireGuard doesn't natively support multipath, but you could:
        # 1. Use multiple WireGuard interfaces
        # 2. Use external routing tools
        # 3. Implement custom routing logic
        
        self.logger.debug(f"配置多路径对等节点: {peer['name']}, 路径数: {len(paths)}")
        
        # For now, just add a comment about available paths
        peer['_multipath_info'] = {
            'available_paths': paths,
            'path_count': len(paths)
        }
    
    def suggest_topology_improvements(self) -> Dict[str, Any]:
        """
        Suggest improvements to the network topology.
        
        Returns:
            Dictionary containing improvement suggestions
        """
        self.logger.info("分析拓扑改进建议")
        
        # Ensure optimizer is initialized
        if self.optimizer is None:
            if self.nodes is None or self.peers is None:
                self.nodes = load_nodes(self.nodes_file)
                self.peers = load_topology(self.topology_file)
            self.optimizer = RouteOptimizer(self.nodes, self.peers)
        
        suggestions = {
            'relay_placement': [],
            'additional_connections': [],
            'bottleneck_mitigation': [],
            'performance_improvements': []
        }
        
        # Suggest relay placement
        suggested_relays = self.optimizer.suggest_relay_placement()
        suggestions['relay_placement'] = suggested_relays
        
        # Suggest additional connections to improve connectivity
        performance_metrics = self.optimizer.analyze_network_performance()
        if performance_metrics['average_path_length'] > 3.0:
            suggestions['additional_connections'].append(
                "Consider adding more direct connections to reduce average path length"
            )
        
        # Suggest bottleneck mitigation
        bottlenecks = self.optimizer.detect_bottlenecks()
        for u, v in bottlenecks:
            suggestions['bottleneck_mitigation'].append(
                f"Consider adding alternative paths around bottleneck: {u} <-> {v}"
            )
        
        # General performance improvements
        if performance_metrics['clustering_coefficient'] < 0.3:
            suggestions['performance_improvements'].append(
                "Network has low clustering - consider adding more local connections"
            )
        
        if not performance_metrics['connectivity']:
            suggestions['performance_improvements'].append(
                "Network is not fully connected - some nodes are isolated"
            )
        
        self.logger.info(f"拓扑改进建议生成完成: {len(suggestions)} 类建议")
        return suggestions
    
    def generate_network_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive network analysis report.
        
        Returns:
            Dictionary containing network analysis report
        """
        self.logger.info("生成网络分析报告")
        
        # Ensure optimizer is initialized
        if self.optimizer is None:
            if self.nodes is None or self.peers is None:
                self.nodes = load_nodes(self.nodes_file)
                self.peers = load_topology(self.topology_file)
            self.optimizer = RouteOptimizer(self.nodes, self.peers)
        
        report = {
            'network_overview': {
                'total_nodes': len(self.nodes),
                'total_connections': len(self.peers),
                'relay_nodes': self.optimizer.get_relay_nodes(),
                'client_nodes': [n['name'] for n in self.nodes if n.get('role') == 'client']
            },
            'performance_metrics': self.optimizer.analyze_network_performance(),
            'bottlenecks': self.optimizer.detect_bottlenecks(),
            'topology_suggestions': self.suggest_topology_improvements(),
            'route_analysis': self.optimizer.optimize_mesh_routes()
        }
        
        self.logger.info("网络分析报告生成完成")
        return report
