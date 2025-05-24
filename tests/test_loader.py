"""
测试配置加载器
"""

import pytest
import tempfile
import os
import yaml
from wg_mesh_gen.loader import load_nodes, load_topology, validate_configuration


def safe_unlink(filepath):
    """安全删除文件，忽略Windows权限问题"""
    try:
        os.unlink(filepath)
    except (OSError, PermissionError):
        pass


class TestNodeLoader:
    """测试节点加载器"""
    
    def test_load_valid_nodes(self):
        """测试加载有效节点配置"""
        test_nodes = {
            "nodes": [
                {
                    "name": "client1",
                    "role": "client",
                    "wireguard_ip": "10.0.0.1/24"
                },
                {
                    "name": "relay1",
                    "role": "relay",
                    "wireguard_ip": "10.0.0.2/24",
                    "endpoints": ["relay.example.com:51820"]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_nodes, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            
            assert len(nodes) == 2
            assert nodes[0]["name"] == "client1"
            assert nodes[0]["role"] == "client"
            assert nodes[1]["name"] == "relay1"
            assert nodes[1]["role"] == "relay"
            
        finally:
            safe_unlink(temp_name)
    
    def test_load_nodes_missing_role(self):
        """测试加载缺少role的节点配置"""
        test_nodes = {
            "nodes": [
                {
                    "name": "client1",
                    "wireguard_ip": "10.0.0.1/24"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_nodes, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            
            # 应该自动设置为client
            assert len(nodes) == 1
            assert nodes[0]["role"] == "client"
            
        finally:
            safe_unlink(temp_name)
    
    def test_load_nodes_missing_name(self):
        """测试加载缺少name的节点配置"""
        test_nodes = {
            "nodes": [
                {
                    "role": "client",
                    "wireguard_ip": "10.0.0.1/24"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_nodes, f)
            f.flush()
            temp_name = f.name

        try:
            with pytest.raises(ValueError, match="missing required 'name' field"):
                load_nodes(temp_name)
                
        finally:
            safe_unlink(temp_name)
    
    def test_load_empty_nodes(self):
        """测试加载空节点配置"""
        test_nodes = {"nodes": []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_nodes, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            assert nodes == []
            
        finally:
            safe_unlink(temp_name)
    
    def test_load_missing_nodes_key(self):
        """测试加载缺少nodes键的配置"""
        test_data = {"other_key": "value"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            assert nodes == []
            
        finally:
            safe_unlink(temp_name)


class TestTopologyLoader:
    """测试拓扑加载器"""
    
    def test_load_valid_topology(self):
        """测试加载有效拓扑配置"""
        test_topology = {
            "peers": [
                {
                    "from": "client1",
                    "to": "relay1",
                    "endpoint": "relay.example.com:51820",
                    "allowed_ips": ["10.0.0.0/24"]
                },
                {
                    "from": "client2",
                    "to": "relay1",
                    "endpoint": "relay.example.com:51820",
                    "allowed_ips": ["10.0.0.0/24"]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_topology, f)
            f.flush()
            temp_name = f.name

        try:
            peers = load_topology(temp_name)
            
            assert len(peers) == 2
            assert peers[0]["from"] == "client1"
            assert peers[0]["to"] == "relay1"
            assert peers[1]["from"] == "client2"
            assert peers[1]["to"] == "relay1"
            
        finally:
            safe_unlink(temp_name)
    
    def test_load_topology_missing_fields(self):
        """测试加载缺少必需字段的拓扑配置"""
        test_topology = {
            "peers": [
                {
                    "from": "client1",
                    # 缺少 "to" 字段
                    "endpoint": "relay.example.com:51820"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_topology, f)
            f.flush()
            temp_name = f.name

        try:
            with pytest.raises(ValueError, match="missing required 'to' field"):
                load_topology(temp_name)
                
        finally:
            safe_unlink(temp_name)
    
    def test_load_empty_topology(self):
        """测试加载空拓扑配置"""
        test_topology = {"peers": []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_topology, f)
            f.flush()
            temp_name = f.name

        try:
            peers = load_topology(temp_name)
            assert peers == []
            
        finally:
            safe_unlink(temp_name)


class TestConfigurationValidation:
    """测试配置验证"""
    
    def test_valid_configuration(self):
        """测试有效配置验证"""
        nodes = [
            {"name": "client1", "role": "client"},
            {"name": "relay1", "role": "relay"}
        ]
        
        peers = [
            {"from": "client1", "to": "relay1"}
        ]
        
        assert validate_configuration(nodes, peers) == True
    
    def test_invalid_node_reference(self):
        """测试无效节点引用"""
        nodes = [
            {"name": "client1", "role": "client"}
        ]
        
        peers = [
            {"from": "client1", "to": "nonexistent"}
        ]
        
        assert validate_configuration(nodes, peers) == False
    
    def test_empty_configuration(self):
        """测试空配置验证"""
        nodes = []
        peers = []
        
        assert validate_configuration(nodes, peers) == True
