"""
Route optimization for WireGuard mesh networks
"""

import networkx as nx
from typing import List, Dict, Any, Tuple, Optional
from .logger import get_logger


class RouteOptimizer:
    """Route optimizer for WireGuard mesh networks"""

    def __init__(self, nodes: List[Dict[str, Any]], peers: List[Dict[str, Any]]):
        """
        Initialize route optimizer.

        Args:
            nodes: List of node configurations
            peers: List of peer connections
        """
        self.logger = get_logger()
        self.nodes = nodes
        self.peers = peers
        self.graph = self._build_graph()

    def _build_graph(self) -> nx.Graph:
        """Build network graph from nodes and peers"""
        G = nx.Graph()

        # Add nodes
        for node in self.nodes:
            G.add_node(node['name'], **node)

        # Add edges with weights (latency/cost)
        for peer in self.peers:
            # Default weight is 1, can be customized based on endpoint performance
            weight = peer.get('weight', 1)
            G.add_edge(peer['from'], peer['to'], weight=weight)

        return G

    def find_optimal_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Find optimal path between two nodes.

        Args:
            source: Source node name
            target: Target node name

        Returns:
            List of node names representing the optimal path
        """
        try:
            path = nx.shortest_path(self.graph, source, target, weight='weight')
            self.logger.debug(f"最优路径 {source} -> {target}: {' -> '.join(path)}")
            return path
        except nx.NetworkXNoPath:
            self.logger.warning(f"无法找到路径: {source} -> {target}")
            return None

    def find_all_paths(self, source: str, target: str, max_length: int = 5) -> List[List[str]]:
        """
        Find all possible paths between two nodes.

        Args:
            source: Source node name
            target: Target node name
            max_length: Maximum path length

        Returns:
            List of paths (each path is a list of node names)
        """
        try:
            paths = list(nx.all_simple_paths(self.graph, source, target, cutoff=max_length))
            self.logger.debug(f"找到 {len(paths)} 条路径: {source} -> {target}")
            return paths
        except nx.NetworkXNoPath:
            self.logger.warning(f"无法找到路径: {source} -> {target}")
            return []

    def calculate_path_cost(self, path: List[str]) -> float:
        """
        Calculate total cost of a path.

        Args:
            path: List of node names representing the path

        Returns:
            Total cost of the path
        """
        if len(path) < 2:
            return 0.0

        total_cost = 0.0
        for i in range(len(path) - 1):
            try:
                edge_data = self.graph[path[i]][path[i + 1]]
                total_cost += edge_data.get('weight', 1)
            except KeyError:
                # Edge doesn't exist
                return float('inf')

        return total_cost

    def get_relay_nodes(self) -> List[str]:
        """Get all relay nodes in the network"""
        relay_nodes = []
        for node in self.nodes:
            if node.get('role') == 'relay':
                relay_nodes.append(node['name'])
        return relay_nodes

    def optimize_mesh_routes(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Optimize routes for all node pairs in the mesh.

        Returns:
            Dictionary mapping source -> target -> optimal_path
        """
        self.logger.info("开始优化网状网络路由")

        routes = {}
        node_names = [node['name'] for node in self.nodes]

        for source in node_names:
            routes[source] = {}
            for target in node_names:
                if source != target:
                    optimal_path = self.find_optimal_path(source, target)
                    if optimal_path:
                        routes[source][target] = optimal_path

        self.logger.info(f"路由优化完成，处理了 {len(node_names)} 个节点")
        return routes

    def suggest_relay_placement(self, max_relays: int = 3) -> List[str]:
        """
        Suggest optimal relay node placement.

        Args:
            max_relays: Maximum number of relay nodes to suggest

        Returns:
            List of suggested relay node names
        """
        self.logger.info("分析最优中继节点位置")

        # Calculate betweenness centrality to find nodes that are on many shortest paths
        centrality = nx.betweenness_centrality(self.graph, weight='weight')

        # Sort nodes by centrality (excluding existing relays)
        existing_relays = set(self.get_relay_nodes())
        candidates = [(node, score) for node, score in centrality.items()
                     if node not in existing_relays]
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Return top candidates
        suggestions = [node for node, _ in candidates[:max_relays]]

        self.logger.info(f"建议的中继节点: {suggestions}")
        return suggestions

    def analyze_network_performance(self) -> Dict[str, Any]:
        """
        Analyze network performance metrics.

        Returns:
            Dictionary containing performance metrics
        """
        self.logger.info("分析网络性能指标")

        metrics = {
            'node_count': len(self.nodes),
            'edge_count': len(self.peers),
            'relay_count': len(self.get_relay_nodes()),
            'average_path_length': 0.0,
            'network_diameter': 0,
            'clustering_coefficient': 0.0,
            'connectivity': False
        }

        # 检查连通性，但要处理空图的情况
        if len(self.graph.nodes()) == 0:
            metrics['connectivity'] = True  # 空图被认为是连通的
        else:
            metrics['connectivity'] = nx.is_connected(self.graph)

        if metrics['connectivity'] and len(self.graph.nodes()) > 1:
            metrics['average_path_length'] = nx.average_shortest_path_length(self.graph, weight='weight')
            metrics['network_diameter'] = nx.diameter(self.graph)
            metrics['clustering_coefficient'] = nx.average_clustering(self.graph)

        self.logger.info(f"网络性能分析完成: {metrics}")
        return metrics

    def detect_bottlenecks(self) -> List[Tuple[str, str]]:
        """
        Detect potential bottleneck edges in the network.

        Returns:
            List of edge tuples that are potential bottlenecks
        """
        self.logger.info("检测网络瓶颈")

        # Calculate edge betweenness centrality
        edge_centrality = nx.edge_betweenness_centrality(self.graph, weight='weight')

        # Find edges with high centrality (potential bottlenecks)
        threshold = 0.1  # Adjust as needed
        bottlenecks = [(u, v) for (u, v), centrality in edge_centrality.items()
                      if centrality > threshold]

        self.logger.info(f"检测到 {len(bottlenecks)} 个潜在瓶颈")
        return bottlenecks
