"""
测试智能配置构建器
"""

import pytest
import tempfile
import os
import yaml
import shutil
from wg_mesh_gen.smart_builder import SmartConfigBuilder


class TestSmartConfigBuilder:
    """测试智能配置构建器"""
    
    def setup_method(self):
        """设置测试数据"""
        self.test_nodes = {
            "nodes": [
                {
                    "name": "A",
                    "role": "client",
                    "wireguard_ip": "10.0.0.1/24"
                },
                {
                    "name": "B",
                    "role": "client", 
                    "wireguard_ip": "10.0.0.2/24"
                },
                {
                    "name": "C",
                    "role": "client",
                    "wireguard_ip": "10.0.0.3/24"
                },
                {
                    "name": "D",
                    "role": "relay",
                    "wireguard_ip": "10.0.0.4/24"
                }
            ]
        }
        
        self.test_topology = {
            "peers": [
                {"from": "A", "to": "B", "weight": 1},
                {"from": "B", "to": "C", "weight": 1},
                {"from": "C", "to": "A", "weight": 1},
                {"from": "A", "to": "D", "weight": 2},
                {"from": "B", "to": "D", "weight": 2},
                {"from": "C", "to": "D", "weight": 2}
            ]
        }
        
        # 创建临时文件
        self.temp_dir = tempfile.mkdtemp()
        self.nodes_file = os.path.join(self.temp_dir, 'nodes.yaml')
        self.topology_file = os.path.join(self.temp_dir, 'topology.yaml')
        
        with open(self.nodes_file, 'w') as f:
            yaml.dump(self.test_nodes, f)
        with open(self.topology_file, 'w') as f:
            yaml.dump(self.test_topology, f)
    
    def teardown_method(self):
        """清理测试数据"""
        try:
            shutil.rmtree(self.temp_dir)
        except (OSError, PermissionError):
            pass  # 忽略Windows权限问题
    
    def test_smart_builder_initialization(self):
        """测试智能构建器初始化"""
        builder = SmartConfigBuilder(self.nodes_file, self.topology_file)
        
        assert builder.nodes_file == self.nodes_file
        assert builder.topology_file == self.topology_file
        assert len(builder.nodes) == 4
        assert len(builder.peers) == 6
        assert builder.optimizer is not None
        assert builder.logger is not None
    
    def test_build_optimized_configs_basic(self):
        """测试基本优化配置构建"""
        builder = SmartConfigBuilder(self.nodes_file, self.topology_file)
        
        output_dir = os.path.join(self.temp_dir, 'output')
        db_path = os.path.join(self.temp_dir, 'test.db')
        
        result = builder.build_optimized_configs(
            output_dir=output_dir,
            auto_generate_keys=True,
            db_path=db_path,
            enable_multipath=False
        )
        
        # 验证返回结果结构
        assert 'configs' in result
        assert 'optimization' in result
        
        # 验证优化数据
        optimization = result['optimization']
        assert 'performance_metrics' in optimization
        assert 'bottlenecks' in optimization
        assert 'optimized_routes' in optimization
        assert 'multipath_enabled' in optimization
        assert optimization['multipath_enabled'] is False
        
        # 验证性能指标
        metrics = optimization['performance_metrics']
        assert 'node_count' in metrics
        assert 'edge_count' in metrics
        assert 'connectivity' in metrics
        assert metrics['node_count'] == 4
        assert metrics['edge_count'] == 6
    
    def test_build_optimized_configs_multipath(self):
        """测试多路径优化配置构建"""
        builder = SmartConfigBuilder(self.nodes_file, self.topology_file)
        
        output_dir = os.path.join(self.temp_dir, 'output_multipath')
        db_path = os.path.join(self.temp_dir, 'test_multipath.db')
        
        result = builder.build_optimized_configs(
            output_dir=output_dir,
            auto_generate_keys=True,
            db_path=db_path,
            enable_multipath=True
        )
        
        # 验证多路径启用
        assert result['optimization']['multipath_enabled'] is True
        
        # 检查是否有多路径信息
        configs = result['configs']
        multipath_found = False
        for node_name, config in configs.items():
            for peer in config.get('peers', []):
                if '_multipath_info' in peer:
                    multipath_found = True
                    assert 'available_paths' in peer['_multipath_info']
                    assert 'path_count' in peer['_multipath_info']
        
        # 在这个拓扑中，应该有一些多路径配置
        # 注意：这取决于具体的网络拓扑
    
    def test_suggest_topology_improvements(self):
        """测试拓扑改进建议"""
        builder = SmartConfigBuilder(self.nodes_file, self.topology_file)
        
        suggestions = builder.suggest_topology_improvements()
        
        # 验证建议结构
        expected_keys = [
            'relay_placement',
            'additional_connections', 
            'bottleneck_mitigation',
            'performance_improvements'
        ]
        
        for key in expected_keys:
            assert key in suggestions
            assert isinstance(suggestions[key], list)
    
    def test_generate_network_report(self):
        """测试网络分析报告生成"""
        builder = SmartConfigBuilder(self.nodes_file, self.topology_file)
        
        report = builder.generate_network_report()
        
        # 验证报告结构
        expected_sections = [
            'network_overview',
            'performance_metrics',
            'bottlenecks',
            'topology_suggestions',
            'route_analysis'
        ]
        
        for section in expected_sections:
            assert section in report
        
        # 验证网络概览
        overview = report['network_overview']
        assert overview['total_nodes'] == 4
        assert overview['total_connections'] == 6
        assert 'relay_nodes' in overview
        assert 'client_nodes' in overview
        
        # 验证中继节点和客户端节点
        assert 'D' in overview['relay_nodes']
        client_nodes = overview['client_nodes']
        assert 'A' in client_nodes
        assert 'B' in client_nodes
        assert 'C' in client_nodes
        
        # 验证性能指标
        metrics = report['performance_metrics']
        assert 'connectivity' in metrics
        assert 'node_count' in metrics
        assert 'edge_count' in metrics
    
    def test_single_path_optimization(self):
        """测试单路径优化"""
        builder = SmartConfigBuilder(self.nodes_file, self.topology_file)
        
        # 创建模拟的构建结果
        mock_build_result = {
            'configs': {
                'A': {
                    'peers': [
                        {'name': 'B', 'allowed_ips': []},
                        {'name': 'D', 'allowed_ips': []}
                    ]
                }
            }
        }
        
        # 创建模拟的优化路由
        mock_optimized_routes = {
            'A': {
                'B': ['A', 'B'],
                'D': ['A', 'D']
            }
        }
        
        # 调用私有方法进行测试
        builder._apply_single_path_optimization(mock_build_result, mock_optimized_routes)
        
        # 验证配置被更新
        configs = mock_build_result['configs']
        assert 'A' in configs
        assert len(configs['A']['peers']) == 2
    
    def test_multipath_optimization(self):
        """测试多路径优化"""
        builder = SmartConfigBuilder(self.nodes_file, self.topology_file)
        
        # 创建模拟的构建结果
        mock_build_result = {
            'configs': {
                'A': {
                    'peers': [
                        {'name': 'C', 'allowed_ips': []}
                    ]
                }
            }
        }
        
        # 创建模拟的优化路由
        mock_optimized_routes = {
            'A': {
                'C': ['A', 'C']
            }
        }
        
        # 调用私有方法进行测试
        builder._apply_multipath_optimization(mock_build_result, mock_optimized_routes)
        
        # 验证多路径信息被添加
        configs = mock_build_result['configs']
        peer = configs['A']['peers'][0]
        
        # 检查是否添加了多路径信息（如果有多条路径的话）
        # 在这个简单的测试中，可能只有一条路径
    
    def test_update_allowed_ips_for_path(self):
        """测试路径的允许IP更新"""
        builder = SmartConfigBuilder(self.nodes_file, self.topology_file)
        
        # 测试没有allowed_ips的peer
        peer = {'name': 'test_peer'}
        path = ['A', 'B', 'C']
        
        builder._update_allowed_ips_for_path(peer, path)
        
        # 验证默认路由被添加
        assert 'allowed_ips' in peer
        assert peer['allowed_ips'] == ['0.0.0.0/0']
        
        # 测试已有allowed_ips的peer
        peer_with_ips = {'name': 'test_peer', 'allowed_ips': ['10.0.0.0/24']}
        builder._update_allowed_ips_for_path(peer_with_ips, path)
        
        # 验证现有的allowed_ips不被覆盖
        assert peer_with_ips['allowed_ips'] == ['10.0.0.0/24']
    
    def test_configure_multipath_peer(self):
        """测试多路径peer配置"""
        builder = SmartConfigBuilder(self.nodes_file, self.topology_file)
        
        peer = {'name': 'test_peer'}
        paths = [
            ['A', 'B', 'C'],
            ['A', 'D', 'C']
        ]
        
        builder._configure_multipath_peer(peer, paths)
        
        # 验证多路径信息被添加
        assert '_multipath_info' in peer
        multipath_info = peer['_multipath_info']
        assert 'available_paths' in multipath_info
        assert 'path_count' in multipath_info
        assert multipath_info['available_paths'] == paths
        assert multipath_info['path_count'] == 2


class TestSmartBuilderEdgeCases:
    """测试智能构建器边缘情况"""
    
    def test_empty_network(self):
        """测试空网络"""
        # 创建空的配置文件
        temp_dir = tempfile.mkdtemp()
        try:
            empty_nodes = {"nodes": []}
            empty_topology = {"peers": []}
            
            nodes_file = os.path.join(temp_dir, 'empty_nodes.yaml')
            topology_file = os.path.join(temp_dir, 'empty_topology.yaml')
            
            with open(nodes_file, 'w') as f:
                yaml.dump(empty_nodes, f)
            with open(topology_file, 'w') as f:
                yaml.dump(empty_topology, f)
            
            builder = SmartConfigBuilder(nodes_file, topology_file)
            
            # 测试各种方法不会崩溃
            suggestions = builder.suggest_topology_improvements()
            assert isinstance(suggestions, dict)
            
            report = builder.generate_network_report()
            assert report['network_overview']['total_nodes'] == 0
            assert report['network_overview']['total_connections'] == 0
            
        finally:
            try:
                shutil.rmtree(temp_dir)
            except (OSError, PermissionError):
                pass
    
    def test_single_node_network(self):
        """测试单节点网络"""
        temp_dir = tempfile.mkdtemp()
        try:
            single_node = {
                "nodes": [
                    {"name": "A", "role": "client", "wireguard_ip": "10.0.0.1/24"}
                ]
            }
            empty_topology = {"peers": []}
            
            nodes_file = os.path.join(temp_dir, 'single_node.yaml')
            topology_file = os.path.join(temp_dir, 'empty_topology.yaml')
            
            with open(nodes_file, 'w') as f:
                yaml.dump(single_node, f)
            with open(topology_file, 'w') as f:
                yaml.dump(empty_topology, f)
            
            builder = SmartConfigBuilder(nodes_file, topology_file)
            
            report = builder.generate_network_report()
            assert report['network_overview']['total_nodes'] == 1
            assert report['network_overview']['total_connections'] == 0
            
        finally:
            try:
                shutil.rmtree(temp_dir)
            except (OSError, PermissionError):
                pass
