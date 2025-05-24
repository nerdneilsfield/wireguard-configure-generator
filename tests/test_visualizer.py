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

from wg_mesh_gen.visualizer import visualize


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
                    "endpoint": "relay.example.com:51820"
                },
                {
                    "from": "C",
                    "to": "B",
                    "endpoint": "relay.example.com:51820"
                }
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
    
    def test_visualize_different_layouts(self):
        """测试不同布局算法"""
        layouts = ['spring', 'circular', 'shell', 'kamada_kawai']
        
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
                }
            ]
        }
        
        unicode_topology = {
            "peers": [
                {
                    "from": "节点甲",
                    "to": "中继🔐",
                    "endpoint": "relay.example.com:51820"
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
                output_path=output_file
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
    
    def test_visualize_complex_topology(self):
        """测试复杂拓扑可视化"""
        complex_nodes = {
            "nodes": [
                {"name": f"node_{i}", "role": "client" if i % 2 == 0 else "relay", 
                 "wireguard_ip": f"10.0.0.{i}/24"}
                for i in range(1, 8)
            ]
        }
        
        complex_topology = {
            "peers": [
                {"from": "node_1", "to": "node_2"},
                {"from": "node_2", "to": "node_3"},
                {"from": "node_3", "to": "node_4"},
                {"from": "node_4", "to": "node_5"},
                {"from": "node_5", "to": "node_6"},
                {"from": "node_6", "to": "node_7"},
                {"from": "node_1", "to": "node_7"},  # 形成环
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_file = os.path.join(temp_dir, 'topology.png')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(complex_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(complex_topology, f)
            
            # 生成可视化
            visualize(
                nodes_path=nodes_file,
                topology_path=topo_file,
                output_path=output_file,
                layout='spring'
            )
            
            # 检查输出文件
            assert os.path.exists(output_file)
            assert os.path.getsize(output_file) > 0
