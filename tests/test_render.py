"""
测试配置渲染器
"""

import pytest
import tempfile
import os
from wg_mesh_gen.render import ConfigRenderer


class TestConfigRenderer:
    """测试配置渲染器"""
    
    def setup_method(self):
        """设置测试数据"""
        self.test_config = {
            'interface': {
                'private_key': 'test_private_key',
                'address': '10.0.0.1/24',
                'listen_port': 51820,
                'dns': '8.8.8.8',
                'mtu': 1420
            },
            'peers': [
                {
                    'name': 'peer1',
                    'public_key': 'test_public_key_1',
                    'endpoint': 'peer1.example.com:51820',
                    'allowed_ips': ['10.0.0.2/32'],
                    'persistent_keepalive': 25
                },
                {
                    'name': 'peer2',
                    'public_key': 'test_public_key_2',
                    'endpoint': None,
                    'allowed_ips': ['10.0.0.3/32'],
                    'persistent_keepalive': None
                }
            ]
        }
    
    def test_renderer_initialization(self):
        """测试渲染器初始化"""
        # 使用默认模板目录
        renderer = ConfigRenderer()
        assert renderer.template_dir.exists()
        assert renderer.env is not None
    
    def test_render_config(self):
        """测试配置文件渲染"""
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = ConfigRenderer()
            
            # 渲染配置
            renderer.render_config('test_node', self.test_config, temp_dir)
            
            # 检查输出文件
            config_file = os.path.join(temp_dir, 'test_node.conf')
            assert os.path.exists(config_file)
            
            # 检查文件内容
            with open(config_file, 'r') as f:
                content = f.read()
                
                # 验证接口部分
                assert 'PrivateKey = test_private_key' in content
                assert 'Address = 10.0.0.1/24' in content
                assert 'ListenPort = 51820' in content
                assert 'DNS = 8.8.8.8' in content
                assert 'MTU = 1420' in content
                
                # 验证对等节点部分
                assert 'PublicKey = test_public_key_1' in content
                assert 'Endpoint = peer1.example.com:51820' in content
                assert 'AllowedIPs = 10.0.0.2/32' in content
                assert 'PersistentKeepalive = 25' in content
                
                assert 'PublicKey = test_public_key_2' in content
                assert 'AllowedIPs = 10.0.0.3/32' in content
    
    def test_render_script(self):
        """测试脚本文件渲染"""
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = ConfigRenderer()
            
            # 渲染脚本
            renderer.render_script('test_node', self.test_config, temp_dir)
            
            # 检查输出文件
            script_file = os.path.join(temp_dir, 'test_node.sh')
            assert os.path.exists(script_file)
            
            # 检查文件内容
            with open(script_file, 'r') as f:
                content = f.read()
                
                # 验证脚本内容
                assert '#!/bin/bash' in content
                assert 'INTERFACE_NAME="test_node"' in content
                assert 'wg-quick up' in content
                assert 'wg-quick down' in content
    
    def test_render_all(self):
        """测试渲染所有配置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = ConfigRenderer()
            
            # 准备构建结果
            build_result = {
                'configs': {
                    'node1': self.test_config,
                    'node2': self.test_config
                },
                'output_dir': temp_dir
            }
            
            # 渲染所有配置
            renderer.render_all(build_result)
            
            # 检查输出文件
            for node_name in ['node1', 'node2']:
                config_file = os.path.join(temp_dir, f'{node_name}.conf')
                script_file = os.path.join(temp_dir, f'{node_name}.sh')
                
                assert os.path.exists(config_file)
                assert os.path.exists(script_file)
    
    def test_render_minimal_config(self):
        """测试最小配置渲染"""
        minimal_config = {
            'interface': {
                'private_key': 'test_private_key',
                'address': '10.0.0.1/24'
            },
            'peers': []
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            renderer = ConfigRenderer()
            
            # 渲染配置
            renderer.render_config('minimal_node', minimal_config, temp_dir)
            
            # 检查输出文件
            config_file = os.path.join(temp_dir, 'minimal_node.conf')
            assert os.path.exists(config_file)
            
            # 检查文件内容
            with open(config_file, 'r') as f:
                content = f.read()
                
                # 验证基本内容
                assert 'PrivateKey = test_private_key' in content
                assert 'Address = 10.0.0.1/24' in content
                
                # 不应该有可选字段
                assert 'ListenPort' not in content
                assert 'DNS' not in content
                assert 'MTU' not in content
    
    def test_invalid_template_directory(self):
        """测试无效模板目录"""
        with pytest.raises(FileNotFoundError):
            ConfigRenderer(template_dir='/nonexistent/directory')
