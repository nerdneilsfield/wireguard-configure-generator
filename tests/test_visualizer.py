"""
测试网络拓扑可视化功能
"""

import pytest
import tempfile
import os
import yaml

# 设置matplotlib使用非交互式后端，避免tkinter问题
import matplotlib
matplotlib.use('Agg')

from wg_mesh_gen.visualizer import visualize, calculate_layout_params, choose_best_layout, create_hierarchical_layout
import networkx as nx


class TestNetworkVisualizer:
    """测试网络可视化器"""
    
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
                    "role": "relay",
                    "wireguard_ip": "10.0.0.2/24"
                },
                {
                    "name": "C",
                    "role": "client",
                    "wireguard_ip": "10.0.0.3/24"
                }
            ]
        }
        
        self.test_topology = {
            "peers": [
                {
                    "from": "A",
                    "to": "B",
                    "endpoint": "relay"
                },
                {
                    "from": "C",
                    "to": "B",
                    "endpoint": "relay"
                }
            ]
        }
        
        # 复杂网络测试数据
        self.complex_nodes = {
            "nodes": [
                {"name": f"node_{i}", "role": "client" if i % 3 == 0 else ("gateway" if i % 3 == 1 else "relay"), 
                 "wireguard_ip": f"10.0.0.{i}/24"}
                for i in range(1, 21)  # 20个节点
            ]
        }
        
        self.complex_topology = {
            "peers": [
                {"from": f"node_{i}", "to": f"node_{i+1}", "endpoint": "main"}
                for i in range(1, 20)
            ] + [
                {"from": "node_1", "to": "node_10", "endpoint": "backup"},
                {"from": "node_5", "to": "node_15", "endpoint": "cross"},
                {"from": "node_8", "to": "node_18", "endpoint": "mesh"},
            ]
        }
    
    def test_visualize_basic(self):
        """测试基本可视化功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_file = os.path.join(temp_dir, 'topology.png')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            # 生成可视化
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file,
                layout='spring'
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0  # 文件不为空
    
    def test_visualize_auto_layout(self):
        """测试自动布局选择"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_file = os.path.join(temp_dir, 'topology.png')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            # 生成可视化 - 使用auto布局
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file,
                layout='auto'
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
    
    def test_visualize_different_layouts(self):
        """测试不同布局算法"""
        layouts = ['auto', 'spring', 'circular', 'shell', 'hierarchical', 'kamada_kawai']
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            # 测试每种布局
            for layout in layouts:
                output_file = os.path.join(temp_dir, f'topology_{layout}.png')
                
                # 生成可视化
                visualize(
                    nodes_path=nodes_file,
                    topology_path=topo_file,
                    output_path=output_file,
                    layout=layout
                )
                
                # 检查输出文件
                assert os.path.exists(output_file)
                assert os.path.getsize(output_file) > 0
    
    def test_visualize_with_edge_labels(self):
        """测试边标签显示控制"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            # 测试显示边标签
            output_file1 = os.path.join(temp_dir, 'topology_with_labels.png')
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file1,
                show_edge_labels=True
            )
            assert os.path.exists(output_file1)
            assert os.path.getsize(output_file1) > 0
            
            # 测试不显示边标签
            output_file2 = os.path.join(temp_dir, 'topology_no_labels.png')
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file2,
                show_edge_labels=False
            )
            assert os.path.exists(output_file2)
            assert os.path.getsize(output_file2) > 0
    
    def test_visualize_dpi_settings(self):
        """测试DPI设置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            # 测试高DPI
            output_file1 = os.path.join(temp_dir, 'topology_high_dpi.png')
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file1,
                high_dpi=True
            )
            assert os.path.exists(output_file1)
            
            # 测试低DPI
            output_file2 = os.path.join(temp_dir, 'topology_low_dpi.png')
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file2,
                high_dpi=False
            )
            assert os.path.exists(output_file2)
            
            # 高DPI文件应该更大
            high_dpi_size = os.path.getsize(output_file1)
            low_dpi_size = os.path.getsize(output_file2)
            assert high_dpi_size > low_dpi_size
    
    def test_visualize_empty_topology(self):
        """测试空拓扑可视化"""
        empty_topology = {"peers": []}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_file = os.path.join(temp_dir, 'topology.png')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(empty_topology, f)
            
            # 生成可视化
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
    
    def test_visualize_single_node(self):
        """测试单节点可视化"""
        single_node = {
            "nodes": [
                {
                    "name": "A",
                    "role": "client",
                    "wireguard_ip": "10.0.0.1/24"
                }
            ]
        }
        
        empty_topology = {"peers": []}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_file = os.path.join(temp_dir, 'topology.png')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(single_node, f)
            with open(topo_file, 'w') as f:
                yaml.dump(empty_topology, f)
            
            # 生成可视化
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
    
    def test_visualize_complex_network(self):
        """测试复杂网络可视化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_file = os.path.join(temp_dir, 'topology.png')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.complex_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.complex_topology, f)
            
            # 生成可视化 - 应该自动选择合适的参数
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file,
                layout='auto'
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0


class TestVisualizerUtilityFunctions:
    """测试可视化器工具函数"""
    
    def test_calculate_layout_params(self):
        """测试布局参数计算"""
        # 小型网络
        params_small = calculate_layout_params(5, 8)
        assert params_small['node_size'] > 500
        assert params_small['font_size'] >= 8
        
        # 中型网络
        params_medium = calculate_layout_params(25, 40)
        assert params_medium['scale_factor'] > 1.0
        assert params_medium['layout_k'] >= 2
        
        # 大型网络
        params_large = calculate_layout_params(80, 150)
        assert params_large['node_size'] < params_small['node_size']
        assert params_large['edge_alpha'] < 0.8
        assert params_large['scale_factor'] >= 1.5
        
        # 超大型网络
        params_xlarge = calculate_layout_params(150, 300)
        assert params_xlarge['scale_factor'] >= 2.0
        assert params_xlarge['iterations'] >= 200
    
    def test_choose_best_layout(self):
        """测试布局选择逻辑"""
        # 创建测试图
        G = nx.Graph()
        G.add_nodes_from(['A', 'B', 'C'])
        G.add_edges_from([('A', 'B'), ('B', 'C')])
        
        # 为节点添加角色属性
        for node in G.nodes():
            G.nodes[node]['role'] = 'client'
        
        # 测试小型网络
        pos_small = choose_best_layout(G, 3, 'auto')
        assert len(pos_small) == 3
        assert all(node in pos_small for node in G.nodes())
        
        # 测试指定布局
        pos_spring = choose_best_layout(G, 3, 'spring')
        assert len(pos_spring) == 3
        
        pos_circular = choose_best_layout(G, 3, 'circular')
        assert len(pos_circular) == 3
    
    def test_create_hierarchical_layout(self):
        """测试分层布局创建"""
        # 创建包含不同角色的测试图
        G = nx.Graph()
        nodes = [
            ('R1', 'relay'),
            ('R2', 'relay'),
            ('GW1', 'gateway'),
            ('GW2', 'gateway'),
            ('C1', 'client'),
            ('C2', 'client'),
            ('C3', 'client')
        ]
        
        for name, role in nodes:
            G.add_node(name, role=role)
        
        # 添加一些边
        G.add_edges_from([('R1', 'GW1'), ('R2', 'GW2'), ('GW1', 'C1'), ('GW2', 'C2')])
        
        # 测试分层布局
        pos = create_hierarchical_layout(G)
        
        # 检查所有节点都有位置
        assert len(pos) == len(nodes)
        assert all(node in pos for node, _ in nodes)
        
        # 检查位置是二维坐标
        for node_pos in pos.values():
            assert len(node_pos) == 2
            assert all(isinstance(coord, (int, float)) for coord in node_pos)


class TestVisualizerEdgeCases:
    """测试可视化器边缘情况"""
    
    def test_visualize_with_unicode_names(self):
        """测试包含Unicode字符的节点名称"""
        unicode_nodes = {
            "nodes": [
                {
                    "name": "节点甲",
                    "role": "client",
                    "wireguard_ip": "10.0.0.1/24"
                },
                {
                    "name": "中继🔐",
                    "role": "relay",
                    "wireguard_ip": "10.0.0.2/24"
                },
                {
                    "name": "网关-测试",
                    "role": "gateway",
                    "wireguard_ip": "10.0.0.3/24"
                }
            ]
        }
        
        unicode_topology = {
            "peers": [
                {
                    "from": "节点甲",
                    "to": "中继🔐",
                    "endpoint": "relay"
                },
                {
                    "from": "网关-测试",
                    "to": "中继🔐",
                    "endpoint": "main"
                }
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_file = os.path.join(temp_dir, 'topology.png')
            
            # 写入测试文件
            with open(nodes_file, 'w', encoding='utf-8') as f:
                yaml.dump(unicode_nodes, f, allow_unicode=True)
            with open(topo_file, 'w', encoding='utf-8') as f:
                yaml.dump(unicode_topology, f, allow_unicode=True)
            
            # 生成可视化（可能会有字体警告，但应该能成功）
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file,
                layout='auto'
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
    
    def test_visualize_large_network_auto_optimization(self):
        """测试大型网络的自动优化"""
        # 创建一个大型网络（100个节点）
        large_nodes = {
            "nodes": [
                {"name": f"node_{i:03d}", "role": "client" if i % 4 != 0 else "relay", 
                 "wireguard_ip": f"10.0.{i//254}.{i%254}/24"}
                for i in range(1, 101)
            ]
        }
        
        # 创建大量连接
        large_topology = {
            "peers": [
                {"from": f"node_{i:03d}", "to": f"node_{(i+1):03d}", "endpoint": "main"}
                for i in range(1, 100)
            ] + [
                {"from": f"node_{i:03d}", "to": f"node_{(i+10):03d}", "endpoint": "backup"}
                for i in range(1, 91)
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_file = os.path.join(temp_dir, 'topology.png')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(large_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(large_topology, f)
            
            # 生成可视化 - 应该自动优化参数
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file,
                layout='auto'
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
    
    def test_visualize_mixed_roles(self):
        """测试混合角色网络"""
        mixed_nodes = {
            "nodes": [
                {"name": "relay1", "role": "relay", "wireguard_ip": "10.0.0.1/24"},
                {"name": "relay2", "role": "relay", "wireguard_ip": "10.0.0.2/24"},
                {"name": "gw1", "role": "gateway", "wireguard_ip": "10.0.0.10/24"},
                {"name": "gw2", "role": "gateway", "wireguard_ip": "10.0.0.11/24"},
                {"name": "client1", "role": "client", "wireguard_ip": "10.0.0.20/24"},
                {"name": "client2", "role": "client", "wireguard_ip": "10.0.0.21/24"},
                {"name": "unknown", "role": "unknown", "wireguard_ip": "10.0.0.30/24"},
            ]
        }
        
        mixed_topology = {
            "peers": [
                {"from": "relay1", "to": "relay2", "endpoint": "main"},
                {"from": "gw1", "to": "relay1", "endpoint": "uplink"},
                {"from": "gw2", "to": "relay2", "endpoint": "uplink"},
                {"from": "client1", "to": "gw1", "endpoint": "local"},
                {"from": "client2", "to": "gw2", "endpoint": "local"},
                {"from": "unknown", "to": "relay1", "endpoint": "misc"},
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_file = os.path.join(temp_dir, 'topology.png')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(mixed_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(mixed_topology, f)
            
            # 测试分层布局
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file,
                layout='hierarchical'
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
