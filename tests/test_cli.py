"""
测试命令行接口
"""

import pytest
import tempfile
import os
import yaml
import shutil
from click.testing import CliRunner
from wg_mesh_gen.cli import cli


class TestCLIBasicFunctions:
    """测试CLI基本功能"""
    
    def setup_method(self):
        """设置测试数据"""
        self.runner = CliRunner()
        
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
    
    def test_cli_help(self):
        """测试CLI帮助信息"""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'WireGuard Mesh Configuration Generator' in result.output
    
    def test_gen_command(self):
        """测试gen命令"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_dir = os.path.join(temp_dir, 'output')
            
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            result = self.runner.invoke(cli, [
                '--nodes-file', nodes_file,
                '--topo-file', topo_file,
                '--output-dir', output_dir,
                'gen'
            ])
            
            assert result.exit_code == 0
            assert os.path.exists(output_dir)
            
            # 检查生成的配置文件
            assert os.path.exists(os.path.join(output_dir, 'A.conf'))
            assert os.path.exists(os.path.join(output_dir, 'B.conf'))
            assert os.path.exists(os.path.join(output_dir, 'A.sh'))
            assert os.path.exists(os.path.join(output_dir, 'B.sh'))
    
    def test_vis_command(self):
        """测试vis命令"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            output_dir = os.path.join(temp_dir, 'output')
            
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            result = self.runner.invoke(cli, [
                '--nodes-file', nodes_file,
                '--topo-file', topo_file,
                '--output-dir', output_dir,
                'vis'
            ])
            
            assert result.exit_code == 0
            
            # 检查生成的可视化文件
            topology_file = os.path.join(output_dir, 'topology.png')
            assert os.path.exists(topology_file)
    
    def test_valid_command(self):
        """测试valid命令"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            result = self.runner.invoke(cli, [
                '--nodes-file', nodes_file,
                '--topo-file', topo_file,
                'valid'
            ])
            
            assert result.exit_code == 0
            assert 'Configuration validation passed.' in result.output
    
    def test_verbose_option(self):
        """测试详细输出选项"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            
            with open(nodes_file, 'w') as f:
                yaml.dump(self.test_nodes, f)
            with open(topo_file, 'w') as f:
                yaml.dump(self.test_topology, f)
            
            # 测试详细模式
            result = self.runner.invoke(cli, [
                '--verbose',
                '--nodes-file', nodes_file,
                '--topo-file', topo_file,
                'valid'
            ])
            
            assert result.exit_code == 0
            # 在verbose模式下，应该有详细的日志输出或成功消息
            assert ('Configuration validation passed.' in result.output or 
                    '配置文件结构验证通过' in result.output or
                    '启用详细日志输出模式' in result.output)


class TestCLIKeyManagement:
    """测试CLI密钥管理功能"""
    
    def setup_method(self):
        """设置测试数据"""
        self.runner = CliRunner()
    
    def test_keys_help(self):
        """测试keys命令帮助"""
        result = self.runner.invoke(cli, ['keys', '--help'])
        assert result.exit_code == 0
        assert '密钥管理命令' in result.output
    
    def test_keys_generate(self):
        """测试密钥生成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            result = self.runner.invoke(cli, [
                'keys', 'generate', 'test_node',
                '--db-path', db_path
            ])
            
            assert result.exit_code == 0
            assert 'Keys generated for node: test_node' in result.output
            assert 'Public key:' in result.output
    
    def test_keys_list(self):
        """测试密钥列表"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            # 先生成一个密钥
            self.runner.invoke(cli, [
                'keys', 'generate', 'test_node',
                '--db-path', db_path
            ])
            
            # 列出密钥
            result = self.runner.invoke(cli, [
                'keys', 'list',
                '--db-path', db_path
            ])
            
            assert result.exit_code == 0
            assert 'test_node' in result.output
    
    def test_keys_show(self):
        """测试显示密钥"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            # 先生成一个密钥
            self.runner.invoke(cli, [
                'keys', 'generate', 'test_node',
                '--db-path', db_path
            ])
            
            # 显示密钥
            result = self.runner.invoke(cli, [
                'keys', 'show', 'test_node',
                '--db-path', db_path
            ])
            
            assert result.exit_code == 0
            assert 'Keys for node: test_node' in result.output
            assert 'Public key:' in result.output


class TestCLIErrorHandling:
    """测试CLI错误处理"""
    
    def setup_method(self):
        """设置测试数据"""
        self.runner = CliRunner()
    
    def test_missing_files(self):
        """测试缺少文件的错误处理"""
        result = self.runner.invoke(cli, [
            '--nodes-file', '/nonexistent/nodes.yaml',
            '--topo-file', '/nonexistent/topology.yaml',
            'gen'
        ])
        
        assert result.exit_code != 0
        assert 'not found' in result.output
    
    def test_invalid_config(self):
        """测试无效配置的错误处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nodes_file = os.path.join(temp_dir, 'nodes.yaml')
            topo_file = os.path.join(temp_dir, 'topology.yaml')
            
            # 写入无效配置
            with open(nodes_file, 'w') as f:
                f.write('invalid: yaml: content: [')
            with open(topo_file, 'w') as f:
                yaml.dump({"peers": []}, f)
            
            result = self.runner.invoke(cli, [
                '--nodes-file', nodes_file,
                '--topo-file', topo_file,
                'valid'
            ])
            
            assert result.exit_code != 0
