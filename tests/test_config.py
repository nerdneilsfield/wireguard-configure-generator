"""
测试配置文件处理的极端情况和边缘情况
"""

import pytest
import tempfile
import os
import json
import yaml
from pathlib import Path
from wg_mesh_gen.file_utils import load_config, save_yaml
from wg_mesh_gen.data_utils import validate_schema
from wg_mesh_gen.loader import load_nodes, load_topology


def safe_unlink(filepath):
    """安全删除文件，忽略Windows权限问题"""
    try:
        os.unlink(filepath)
    except (OSError, PermissionError):
        pass  # 忽略Windows文件权限问题


class TestConfigFileLoading:
    """测试配置文件加载"""

    def test_load_valid_json(self):
        """测试加载有效的JSON文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_data = {"nodes": [{"name": "test", "role": "client"}]}
            json.dump(test_data, f)
            f.flush()
            temp_name = f.name

        try:
            result = load_config(temp_name)
            assert result == test_data
        finally:
            safe_unlink(temp_name)

    def test_load_valid_yaml(self):
        """测试加载有效的YAML文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            test_data = {"nodes": [{"name": "test", "role": "client"}]}
            yaml.dump(test_data, f)
            f.flush()
            temp_name = f.name

        try:
            result = load_config(temp_name)
            assert result == test_data
        finally:
            safe_unlink(temp_name)

    def test_load_invalid_json(self):
        """测试加载无效的JSON文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json content}')  # 无效JSON
            f.flush()
            temp_name = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_config(temp_name)
        finally:
            safe_unlink(temp_name)

    def test_load_invalid_yaml(self):
        """测试加载无效的YAML文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('invalid: yaml: content: [unclosed')  # 无效YAML
            f.flush()
            temp_name = f.name

        try:
            with pytest.raises(yaml.YAMLError):
                load_config(temp_name)
        finally:
            safe_unlink(temp_name)

    def test_load_empty_file(self):
        """测试加载空文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('')  # 空文件
            f.flush()
            temp_name = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_config(temp_name)
        finally:
            safe_unlink(temp_name)

    def test_load_unknown_extension(self):
        """测试加载未知扩展名的文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_data = {"nodes": [{"name": "test"}]}
            json.dump(test_data, f)  # 内容是JSON但扩展名是.txt
            f.flush()
            temp_name = f.name

        try:
            # 应该默认尝试JSON解析
            result = load_config(temp_name)
            assert result == test_data
        finally:
            safe_unlink(temp_name)


class TestNodeConfigurationEdgeCases:
    """测试节点配置边缘情况"""

    def test_empty_nodes_list(self):
        """测试空节点列表"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"nodes": []}, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            assert nodes == []
        finally:
            safe_unlink(temp_name)

    def test_missing_nodes_key(self):
        """测试缺少nodes键"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"other_key": "value"}, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            assert nodes == []  # 应该返回空列表
        finally:
            safe_unlink(temp_name)

    def test_node_with_missing_required_fields(self):
        """测试缺少必需字段的节点"""
        test_data = {"nodes": [{"role": "client", "wireguard_ip": "10.0.0.1/24"}]}  # 缺少name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            f.flush()
            temp_name = f.name

        try:
            # 应该抛出ValueError，因为缺少必需的name字段
            with pytest.raises(ValueError, match="missing required 'name' field"):
                load_nodes(temp_name)
        finally:
            safe_unlink(temp_name)

    def test_node_with_invalid_ip_addresses(self):
        """测试无效IP地址的节点"""
        invalid_ips = [
            "256.256.256.256/24",  # 无效IP
            "10.0.0.1/33",         # 无效CIDR
            "not.an.ip.address",   # 完全无效
            "10.0.0.1",            # 缺少CIDR
        ]

        for invalid_ip in invalid_ips:
            test_data = {
                "nodes": [{"name": "test", "role": "client", "wireguard_ip": invalid_ip}]
            }

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(test_data, f)
                f.flush()
                temp_name = f.name

            try:
                # 加载应该成功，IP验证在其他地方进行
                nodes = load_nodes(temp_name)
                assert len(nodes) == 1
                assert nodes[0]["wireguard_ip"] == invalid_ip
            finally:
                safe_unlink(temp_name)

    def test_node_with_empty_endpoints(self):
        """测试空端点列表的节点"""
        test_data = {
            "nodes": [{"name": "test", "role": "relay", "wireguard_ip": "10.0.0.1/24", "endpoints": []}]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            assert len(nodes) == 1
            assert nodes[0]["endpoints"] == []
        finally:
            safe_unlink(temp_name)

    def test_node_with_duplicate_names(self):
        """测试重复节点名称"""
        test_data = {
            "nodes": [
                {"name": "duplicate", "role": "client", "wireguard_ip": "10.0.0.1"},
                {"name": "duplicate", "role": "relay", "wireguard_ip": "10.0.0.2"},
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            f.flush()
            temp_name = f.name

        try:
            nodes = load_nodes(temp_name)
            assert len(nodes) == 2  # 应该加载两个节点，即使名称重复
        finally:
            safe_unlink(temp_name)


class TestTopologyConfigurationEdgeCases:
    """测试拓扑配置边缘情况"""

    def test_empty_peers_list(self):
        """测试空对等列表"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"peers": []}, f)
            f.flush()
            temp_name = f.name

        try:
            peers = load_topology(temp_name)
            assert peers == []
        finally:
            safe_unlink(temp_name)

    def test_missing_peers_key(self):
        """测试缺少peers键"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"other_key": "value"}, f)
            f.flush()
            temp_name = f.name

        try:
            peers = load_topology(temp_name)
            assert peers == []
        finally:
            safe_unlink(temp_name)

    def test_peer_with_missing_required_fields(self):
        """测试缺少必需字段的对等连接"""
        # 测试缺少from字段
        test_data1 = {"peers": [{"to": "B", "endpoint": "test"}]}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data1, f)
            f.flush()
            temp_name1 = f.name

        try:
            with pytest.raises(ValueError, match="missing required 'from' field"):
                load_topology(temp_name1)
        finally:
            safe_unlink(temp_name1)

        # 测试缺少to字段
        test_data2 = {"peers": [{"from": "A", "endpoint": "test"}]}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data2, f)
            f.flush()
            temp_name2 = f.name

        try:
            with pytest.raises(ValueError, match="missing required 'to' field"):
                load_topology(temp_name2)
        finally:
            safe_unlink(temp_name2)

    def test_peer_with_invalid_allowed_ips(self):
        """测试无效allowed_ips的对等连接"""
        invalid_ips_list = [
            ["256.256.256.256/24"],
            ["10.0.0.1/33"],
            ["not.an.ip"],
            ["10.0.0.1/24", "invalid.ip"],
        ]

        for invalid_ips in invalid_ips_list:
            test_data = {
                "peers": [{"from": "A", "to": "B", "endpoint": "test", "allowed_ips": invalid_ips}]
            }

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(test_data, f)
                f.flush()
                temp_name = f.name

            try:
                peers = load_topology(temp_name)
                assert len(peers) == 1
                assert peers[0]["allowed_ips"] == invalid_ips
            finally:
                safe_unlink(temp_name)

    def test_circular_topology(self):
        """测试循环拓扑"""
        test_data = {
            "peers": [
                {"from": "A", "to": "B", "endpoint": "test", "allowed_ips": ["10.0.0.2/32"]},
                {"from": "B", "to": "C", "endpoint": "test", "allowed_ips": ["10.0.0.3/32"]},
                {"from": "C", "to": "A", "endpoint": "test", "allowed_ips": ["10.0.0.1/32"]},
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            f.flush()
            temp_name = f.name

        try:
            peers = load_topology(temp_name)
            assert len(peers) == 3
        finally:
            safe_unlink(temp_name)


class TestYAMLSpecificFeatures:
    """测试YAML特有功能"""

    def test_yaml_comments(self):
        """测试YAML注释"""
        yaml_content = """
# This is a comment
nodes:  # Node list
  - name: test  # Node name
    role: client  # Node role
    # More config...
    wireguard_ip: 10.0.0.1
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            f.flush()
            temp_name = f.name

        try:
            result = load_config(temp_name)
            assert "nodes" in result
            assert len(result["nodes"]) == 1
            assert result["nodes"][0]["name"] == "test"
        finally:
            safe_unlink(temp_name)

    def test_yaml_multiline_strings(self):
        """测试YAML多行字符串"""
        yaml_content = """
nodes:
  - name: test
    role: client
    description: |
      This is a multiline description
      Contains multiple lines
      For testing YAML functionality
    wireguard_ip: 10.0.0.1
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            f.flush()
            temp_name = f.name

        try:
            result = load_config(temp_name)
            description = result["nodes"][0]["description"]
            assert "multiline description" in description
            assert "multiple lines" in description
        finally:
            safe_unlink(temp_name)

    def test_save_yaml_functionality(self):
        """测试保存YAML功能"""
        test_data = {
            "nodes": [
                {"name": "test", "role": "client", "wireguard_ip": "10.0.0.1"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_name = f.name

        try:
            save_yaml(test_data, temp_name)

            # 验证文件被正确保存
            assert os.path.exists(temp_name)

            # 验证内容正确
            loaded_data = load_config(temp_name)
            assert loaded_data == test_data
        finally:
            safe_unlink(temp_name)
