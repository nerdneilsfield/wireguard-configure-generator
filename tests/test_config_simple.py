"""
简单配置测试
"""

import pytest
import tempfile
import os
import yaml
from wg_mesh_gen.loader import load_nodes, load_topology


def safe_unlink(filepath):
    """安全删除文件，忽略Windows权限问题"""
    try:
        os.unlink(filepath)
    except (OSError, PermissionError):
        pass


class TestSimpleConfigurations:
    """测试简单配置"""
    
    def test_minimal_node_config(self):
        """测试最小节点配置"""
        minimal_config = {
            "nodes": [
                {
                    "name": "test",
                    "role": "client",
                    "wireguard_ip": "10.0.0.1/24"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(minimal_config, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            assert len(nodes) == 1
            assert nodes[0]["name"] == "test"
            assert nodes[0]["role"] == "client"
            assert nodes[0]["wireguard_ip"] == "10.0.0.1/24"
        finally:
            safe_unlink(temp_name)
    
    def test_minimal_topology_config(self):
        """测试最小拓扑配置"""
        minimal_topology = {
            "peers": [
                {
                    "from": "A",
                    "to": "B"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(minimal_topology, f)
            f.flush()
            temp_name = f.name

        try:
            peers = load_topology(temp_name)
            assert len(peers) == 1
            assert peers[0]["from"] == "A"
            assert peers[0]["to"] == "B"
        finally:
            safe_unlink(temp_name)
    
    def test_complete_node_config(self):
        """测试完整节点配置"""
        complete_config = {
            "nodes": [
                {
                    "name": "relay1",
                    "role": "relay",
                    "wireguard_ip": "10.0.0.1/24",
                    "listen_port": 51820,
                    "endpoints": ["relay.example.com:51820"],
                    "dns": ["8.8.8.8", "8.8.4.4"],
                    "mtu": 1420
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(complete_config, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            assert len(nodes) == 1
            node = nodes[0]
            assert node["name"] == "relay1"
            assert node["role"] == "relay"
            assert node["wireguard_ip"] == "10.0.0.1/24"
            assert node["listen_port"] == 51820
            assert node["endpoints"] == ["relay.example.com:51820"]
            assert node["dns"] == ["8.8.8.8", "8.8.4.4"]
            assert node["mtu"] == 1420
        finally:
            safe_unlink(temp_name)
    
    def test_complete_topology_config(self):
        """测试完整拓扑配置"""
        complete_topology = {
            "peers": [
                {
                    "from": "client1",
                    "to": "relay1",
                    "endpoint": "relay.example.com:51820",
                    "allowed_ips": ["10.0.0.0/24", "192.168.1.0/24"],
                    "persistent_keepalive": 25
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(complete_topology, f)
            f.flush()
            temp_name = f.name

        try:
            peers = load_topology(temp_name)
            assert len(peers) == 1
            peer = peers[0]
            assert peer["from"] == "client1"
            assert peer["to"] == "relay1"
            assert peer["endpoint"] == "relay.example.com:51820"
            assert peer["allowed_ips"] == ["10.0.0.0/24", "192.168.1.0/24"]
            assert peer["persistent_keepalive"] == 25
        finally:
            safe_unlink(temp_name)
    
    def test_mesh_topology(self):
        """测试网状拓扑配置"""
        mesh_nodes = {
            "nodes": [
                {"name": "A", "role": "client", "wireguard_ip": "10.0.0.1/24"},
                {"name": "B", "role": "client", "wireguard_ip": "10.0.0.2/24"},
                {"name": "C", "role": "client", "wireguard_ip": "10.0.0.3/24"}
            ]
        }
        
        mesh_topology = {
            "peers": [
                {"from": "A", "to": "B"},
                {"from": "B", "to": "C"},
                {"from": "C", "to": "A"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f1:
            yaml.dump(mesh_nodes, f1)
            f1.flush()
            nodes_file = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f2:
            yaml.dump(mesh_topology, f2)
            f2.flush()
            topo_file = f2.name

        try:
            nodes = load_nodes(nodes_file)
            peers = load_topology(topo_file)
            
            assert len(nodes) == 3
            assert len(peers) == 3
            
            # 验证所有节点都存在
            node_names = {node["name"] for node in nodes}
            assert node_names == {"A", "B", "C"}
            
            # 验证所有连接都存在
            connections = {(peer["from"], peer["to"]) for peer in peers}
            expected_connections = {("A", "B"), ("B", "C"), ("C", "A")}
            assert connections == expected_connections
            
        finally:
            safe_unlink(nodes_file)
            safe_unlink(topo_file)
    
    def test_star_topology(self):
        """测试星形拓扑配置"""
        star_nodes = {
            "nodes": [
                {"name": "hub", "role": "relay", "wireguard_ip": "10.0.0.1/24"},
                {"name": "client1", "role": "client", "wireguard_ip": "10.0.0.2/24"},
                {"name": "client2", "role": "client", "wireguard_ip": "10.0.0.3/24"},
                {"name": "client3", "role": "client", "wireguard_ip": "10.0.0.4/24"}
            ]
        }
        
        star_topology = {
            "peers": [
                {"from": "client1", "to": "hub", "endpoint": "hub.example.com:51820"},
                {"from": "client2", "to": "hub", "endpoint": "hub.example.com:51820"},
                {"from": "client3", "to": "hub", "endpoint": "hub.example.com:51820"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f1:
            yaml.dump(star_nodes, f1)
            f1.flush()
            nodes_file = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f2:
            yaml.dump(star_topology, f2)
            f2.flush()
            topo_file = f2.name

        try:
            nodes = load_nodes(nodes_file)
            peers = load_topology(topo_file)
            
            assert len(nodes) == 4
            assert len(peers) == 3
            
            # 验证hub节点存在且为relay
            hub_node = next(node for node in nodes if node["name"] == "hub")
            assert hub_node["role"] == "relay"
            
            # 验证所有客户端都连接到hub
            for peer in peers:
                assert peer["to"] == "hub"
                assert peer["endpoint"] == "hub.example.com:51820"
            
        finally:
            safe_unlink(nodes_file)
            safe_unlink(topo_file)
