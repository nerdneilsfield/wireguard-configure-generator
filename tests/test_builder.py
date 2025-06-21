"""
测试配置构建器
"""

import pytest
import tempfile
import os
import yaml
from wg_mesh_gen.builder import build_peer_configs
from wg_mesh_gen.simple_storage import SimpleKeyStorage


def safe_unlink(filepath):
    """安全删除文件，忽略Windows权限问题"""
    try:
        os.unlink(filepath)
    except (OSError, PermissionError):
        pass


class TestPeerConfigBuilder:
    """测试对等配置构建器"""
    
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
                    "wireguard_ip": "10.0.0.2/24",
                    "endpoints": ["relay.example.com:51820"]
                }
            ]
        }
        
        self.test_topology = {
            "peers": [
                {
                    "from": "A",
                    "to": "B",
                    "endpoint": "relay.example.com:51820",
                    "allowed_ips": ["10.0.0.0/24"]
                }
            ]
        }
    
    def test_build_peer_configs_basic(self):
        """测试基本配置构建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_dir = os.path.join(temp_dir, 'output')
            db_path = os.path.join(temp_dir, 'test.json')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            # 构建配置
            result = build_peer_configs(
                nodes_file=nodes_file,
                topology_file=topo_file,
                output_dir=output_dir,
                auto_generate_keys=True,
                db_path=db_path
            )
            
            # 验证结果
            assert 'configs' in result
            assert 'A' in result['configs']
            assert 'B' in result['configs']
            
            # 验证节点A的配置
            config_a = result['configs']['A']
            assert 'interface' in config_a
            assert 'peers' in config_a
            assert config_a['interface']['address'] == "10.0.0.1/24"
            
            # 验证节点B的配置
            config_b = result['configs']['B']
            assert 'interface' in config_b
            assert 'peers' in config_b
            assert config_b['interface']['address'] == "10.0.0.2/24"
    
    def test_build_peer_configs_with_existing_keys(self):
        """测试使用已存在密钥的配置构建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_dir = os.path.join(temp_dir, 'output')
            db_path = os.path.join(temp_dir, 'test.json')
            
            # 预先存储密钥
            key_storage = SimpleKeyStorage(db_path)
            key_storage.store_keypair("A", "private_key_A", "public_key_A")
            key_storage.store_keypair("B", "private_key_B", "public_key_B")
            key_storage.close()
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            # 构建配置
            result = build_peer_configs(
                nodes_file=nodes_file,
                topology_file=topo_file,
                output_dir=output_dir,
                auto_generate_keys=True,
                db_path=db_path
            )
            
            # 验证使用了已存在的密钥
            nodes = result['nodes']
            node_a = next(n for n in nodes if n['name'] == 'A')
            node_b = next(n for n in nodes if n['name'] == 'B')
            
            assert node_a['private_key'] == "private_key_A"
            assert node_a['public_key'] == "public_key_A"
            assert node_b['private_key'] == "private_key_B"
            assert node_b['public_key'] == "public_key_B"
    
    def test_build_peer_configs_auto_key_generation(self):
        """测试自动密钥生成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_dir = os.path.join(temp_dir, 'output')
            db_path = os.path.join(temp_dir, 'test.json')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            # 构建配置
            result = build_peer_configs(
                nodes_file=nodes_file,
                topology_file=topo_file,
                output_dir=output_dir,
                auto_generate_keys=True,
                db_path=db_path
            )
            
            # 验证生成了密钥
            nodes = result['nodes']
            for node in nodes:
                assert 'private_key' in node
                assert 'public_key' in node
                assert node['private_key'] is not None
                assert node['public_key'] is not None
    
    def test_build_peer_configs_empty_topology(self):
        """测试空拓扑配置构建"""
        empty_topology = {"peers": []}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_dir = os.path.join(temp_dir, 'output')
            db_path = os.path.join(temp_dir, 'test.json')
            
            # 写入测试文件
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(empty_topology, f)
            
            # 构建配置
            result = build_peer_configs(
                nodes_file=nodes_file,
                topology_file=topo_file,
                output_dir=output_dir,
                auto_generate_keys=True,
                db_path=db_path
            )
            
            # 验证结果 - 应该有节点但没有对等连接
            assert 'configs' in result
            assert 'A' in result['configs']
            assert 'B' in result['configs']
            
            # 每个节点应该没有对等连接
            for node_name, config in result['configs'].items():
                assert len(config['peers']) == 0
    
    def test_build_peer_configs_invalid_files(self):
        """测试无效文件处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = os.path.join(temp_dir, 'nonexistent.yaml')
            output_dir = os.path.join(temp_dir, 'output')
            db_path = os.path.join(temp_dir, 'test.json')
            
            # 应该抛出异常
            with pytest.raises(FileNotFoundError):
                build_peer_configs(
                    nodes_file=nonexistent_file,
                    topology_file=nonexistent_file,
                    output_dir=output_dir,
                    auto_generate_keys=True,
                    db_path=db_path
                )
