"""
测试路由优化器
"""

import pytest
from wg_mesh_gen.route_optimizer import RouteOptimizer


class TestRouteOptimizer:
    """测试路由优化器"""
    
    def setup_method(self):
        """设置测试数据"""
        self.simple_nodes = [
            {"name": "A", "role": "client"},
            {"name": "B", "role": "relay"},
            {"name": "C", "role": "client"}
        ]
        
        self.simple_peers = [
            {"from": "A", "to": "B", "weight": 1},
            {"from": "B", "to": "C", "weight": 1}
        ]
        
        self.complex_nodes = [
            {"name": "A", "role": "client"},
            {"name": "B", "role": "client"},
            {"name": "C", "role": "client"},
            {"name": "D", "role": "relay"},
            {"name": "E", "role": "client"},
            {"name": "F", "role": "client"},
            {"name": "H", "role": "relay"}
        ]
        
        self.complex_peers = [
            # A-B-C mesh
            {"from": "A", "to": "B", "weight": 1},
            {"from": "B", "to": "C", "weight": 1},
            {"from": "C", "to": "A", "weight": 1},
            # Relay connections
            {"from": "A", "to": "D", "weight": 2},
            {"from": "B", "to": "D", "weight": 2},
            {"from": "C", "to": "D", "weight": 2},
            {"from": "D", "to": "H", "weight": 3},
            {"from": "H", "to": "E", "weight": 2},
            {"from": "H", "to": "F", "weight": 2},
            {"from": "E", "to": "F", "weight": 1}
        ]
    
    def test_optimizer_initialization(self):
        """测试优化器初始化"""
        optimizer = RouteOptimizer(self.simple_nodes, self.simple_peers)
        
        assert optimizer.nodes == self.simple_nodes
        assert optimizer.peers == self.simple_peers
        assert optimizer.graph is not None
        assert len(optimizer.graph.nodes()) == 3
        assert len(optimizer.graph.edges()) == 2
    
    def test_find_optimal_path(self):
        """测试寻找最优路径"""
        optimizer = RouteOptimizer(self.simple_nodes, self.simple_peers)
        
        # 测试直接连接
        path = optimizer.find_optimal_path("A", "B")
        assert path == ["A", "B"]
        
        # 测试间接连接
        path = optimizer.find_optimal_path("A", "C")
        assert path == ["A", "B", "C"]
        
        # 测试不存在的路径
        isolated_nodes = [{"name": "X", "role": "client"}, {"name": "Y", "role": "client"}]
        isolated_peers = []
        isolated_optimizer = RouteOptimizer(isolated_nodes, isolated_peers)
        
        path = isolated_optimizer.find_optimal_path("X", "Y")
        assert path is None
    
    def test_find_all_paths(self):
        """测试寻找所有路径"""
        optimizer = RouteOptimizer(self.complex_nodes, self.complex_peers)
        
        # 寻找A到F的所有路径
        paths = optimizer.find_all_paths("A", "F", max_length=5)
        
        assert len(paths) > 0
        # 验证每条路径都是有效的
        for path in paths:
            assert path[0] == "A"
            assert path[-1] == "F"
            assert len(path) <= 6  # max_length + 1
    
    def test_calculate_path_cost(self):
        """测试计算路径成本"""
        optimizer = RouteOptimizer(self.simple_nodes, self.simple_peers)
        
        # 测试单跳路径
        cost = optimizer.calculate_path_cost(["A", "B"])
        assert cost == 1
        
        # 测试多跳路径
        cost = optimizer.calculate_path_cost(["A", "B", "C"])
        assert cost == 2
        
        # 测试无效路径
        cost = optimizer.calculate_path_cost(["A", "X"])
        assert cost == float('inf')
        
        # 测试空路径
        cost = optimizer.calculate_path_cost([])
        assert cost == 0.0
        
        # 测试单节点路径
        cost = optimizer.calculate_path_cost(["A"])
        assert cost == 0.0
    
    def test_get_relay_nodes(self):
        """测试获取中继节点"""
        optimizer = RouteOptimizer(self.complex_nodes, self.complex_peers)
        
        relay_nodes = optimizer.get_relay_nodes()
        assert set(relay_nodes) == {"D", "H"}
    
    def test_optimize_mesh_routes(self):
        """测试优化网状路由"""
        optimizer = RouteOptimizer(self.simple_nodes, self.simple_peers)
        
        routes = optimizer.optimize_mesh_routes()
        
        # 验证路由结构
        assert isinstance(routes, dict)
        assert "A" in routes
        assert "B" in routes
        assert "C" in routes
        
        # 验证A到C的路由
        assert routes["A"]["C"] == ["A", "B", "C"]
        
        # 验证B到A的路由
        assert routes["B"]["A"] == ["B", "A"]
    
    def test_suggest_relay_placement(self):
        """测试建议中继节点位置"""
        optimizer = RouteOptimizer(self.complex_nodes, self.complex_peers)
        
        suggestions = optimizer.suggest_relay_placement(max_relays=2)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 2
        # 建议的节点不应该是已有的中继节点
        existing_relays = {"D", "H"}
        for suggestion in suggestions:
            assert suggestion not in existing_relays
    
    def test_analyze_network_performance(self):
        """测试分析网络性能"""
        optimizer = RouteOptimizer(self.simple_nodes, self.simple_peers)
        
        metrics = optimizer.analyze_network_performance()
        
        # 验证指标结构
        required_keys = [
            'node_count', 'edge_count', 'relay_count',
            'average_path_length', 'network_diameter',
            'clustering_coefficient', 'connectivity'
        ]
        
        for key in required_keys:
            assert key in metrics
        
        # 验证基本指标
        assert metrics['node_count'] == 3
        assert metrics['edge_count'] == 2
        assert metrics['relay_count'] == 1
        assert metrics['connectivity'] is True
    
    def test_detect_bottlenecks(self):
        """测试检测网络瓶颈"""
        optimizer = RouteOptimizer(self.simple_nodes, self.simple_peers)
        
        bottlenecks = optimizer.detect_bottlenecks()
        
        assert isinstance(bottlenecks, list)
        # 在简单的线性拓扑中，中间的边可能是瓶颈
        # 具体结果取决于网络结构和阈值


class TestRouteOptimizerEdgeCases:
    """测试路由优化器边缘情况"""
    
    def test_empty_network(self):
        """测试空网络"""
        optimizer = RouteOptimizer([], [])
        
        routes = optimizer.optimize_mesh_routes()
        assert routes == {}
        
        metrics = optimizer.analyze_network_performance()
        assert metrics['node_count'] == 0
        assert metrics['edge_count'] == 0
        assert metrics['connectivity'] is True  # 空图被认为是连通的
    
    def test_single_node_network(self):
        """测试单节点网络"""
        single_node = [{"name": "A", "role": "client"}]
        optimizer = RouteOptimizer(single_node, [])
        
        routes = optimizer.optimize_mesh_routes()
        assert "A" in routes
        assert routes["A"] == {}  # 没有其他节点可以路由到
        
        metrics = optimizer.analyze_network_performance()
        assert metrics['node_count'] == 1
        assert metrics['edge_count'] == 0
    
    def test_disconnected_network(self):
        """测试断开的网络"""
        disconnected_nodes = [
            {"name": "A", "role": "client"},
            {"name": "B", "role": "client"},
            {"name": "C", "role": "client"},
            {"name": "D", "role": "client"}
        ]
        
        disconnected_peers = [
            {"from": "A", "to": "B"},
            {"from": "C", "to": "D"}
        ]
        
        optimizer = RouteOptimizer(disconnected_nodes, disconnected_peers)
        
        # A应该无法到达C或D
        path = optimizer.find_optimal_path("A", "C")
        assert path is None
        
        path = optimizer.find_optimal_path("A", "D")
        assert path is None
        
        # 但A应该能到达B
        path = optimizer.find_optimal_path("A", "B")
        assert path == ["A", "B"]
        
        metrics = optimizer.analyze_network_performance()
        assert metrics['connectivity'] is False
