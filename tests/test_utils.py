"""
测试工具函数
"""

import pytest
import tempfile
import os
import json
import yaml
from wg_mesh_gen.file_utils import (
    ensure_dir, load_json, load_yaml, load_config, save_yaml, write_file
)
from wg_mesh_gen.data_utils import (
    validate_schema, flatten, chunk_list
)
from wg_mesh_gen.string_utils import (
    sanitize_filename, mask_sensitive_info
)


def safe_unlink(filepath):
    """安全删除文件，忽略Windows权限问题"""
    try:
        os.unlink(filepath)
    except (OSError, PermissionError):
        pass  # 忽略Windows文件权限问题


class TestDirectoryUtils:
    """测试目录工具函数"""
    
    def test_ensure_dir(self):
        """测试目录创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = os.path.join(temp_dir, 'test', 'nested', 'dir')
            
            # 目录不应该存在
            assert not os.path.exists(test_dir)
            
            # 创建目录
            ensure_dir(test_dir)
            
            # 目录应该存在
            assert os.path.exists(test_dir)
            assert os.path.isdir(test_dir)


class TestFileLoaders:
    """测试文件加载器"""
    
    def test_load_json(self):
        """测试JSON加载"""
        test_data = {"test": "data", "number": 42}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            f.flush()

            try:
                result = load_json(f.name)
                assert result == test_data
            finally:
                safe_unlink(f.name)
    
    def test_load_yaml(self):
        """测试YAML加载"""
        test_data = {"test": "data", "number": 42}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            f.flush()

            try:
                result = load_yaml(f.name)
                assert result == test_data
            finally:
                safe_unlink(f.name)
    
    def test_load_config_json(self):
        """测试配置加载 - JSON"""
        test_data = {"test": "data", "number": 42}
        
        # 测试JSON自动检测
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            f.flush()

            try:
                result = load_config(f.name)
                assert result == test_data
            finally:
                safe_unlink(f.name)

        # 测试YAML自动检测
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            f.flush()

            try:
                result = load_config(f.name)
                assert result == test_data
            finally:
                safe_unlink(f.name)
    
    def test_load_config_unknown_extension(self):
        """测试未知扩展名的配置加载"""
        test_data = {"test": "data", "number": 42}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            json.dump(test_data, f)
            f.flush()

            try:
                # 应该默认尝试JSON解析
                result = load_config(f.name)
                assert result == test_data
            finally:
                safe_unlink(f.name)


class TestFileWriters:
    """测试文件写入器"""
    
    def test_save_yaml(self):
        """测试YAML保存"""
        test_data = {"test": "data", "number": 42}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            try:
                save_yaml(test_data, f.name)
                
                # 验证文件被正确保存
                assert os.path.exists(f.name)
                
                # 验证内容正确
                with open(f.name, 'r', encoding='utf-8') as read_f:
                    loaded_data = yaml.safe_load(read_f)
                    assert loaded_data == test_data
            finally:
                safe_unlink(f.name)
    
    def test_write_file(self):
        """测试文件写入"""
        test_content = "This is test content\nWith multiple lines"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            try:
                write_file(test_content, f.name)
                
                # 验证文件内容
                with open(f.name, 'r', encoding='utf-8') as read_f:
                    content = read_f.read()
                    assert content == test_content
            finally:
                safe_unlink(f.name)


class TestErrorHandling:
    """测试错误处理"""
    
    def test_load_invalid_json(self):
        """测试加载无效JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json content}')
            f.flush()

            try:
                with pytest.raises(json.JSONDecodeError):
                    load_json(f.name)
            finally:
                safe_unlink(f.name)
    
    def test_load_invalid_yaml(self):
        """测试加载无效YAML"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('invalid: yaml: content: [unclosed')
            f.flush()

            try:
                with pytest.raises(yaml.YAMLError):
                    load_yaml(f.name)
            finally:
                safe_unlink(f.name)


class TestUtilityFunctions:
    """测试实用工具函数"""
    
    def test_sanitize_filename(self):
        """测试文件名清理"""
        test_cases = [
            ("normal_filename", "normal_filename"),
            ("file with spaces", "file with spaces"),
            ("file.with.dots", "file.with.dots"),
            ("file_with_underscores", "file_with_underscores"),
            ("file/with\\invalid:chars", "file_with_invalid_chars"),  # 替换无效字符为下划线
            ("file<>|?*chars", "file_____chars"),  # 替换无效字符为下划线
            ("   leading_trailing_spaces   ", "leading_trailing_spaces"),  # 移除前后空格
        ]

        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Expected '{expected}' but got '{result}' for input '{input_name}'"
    
    def test_flatten(self):
        """测试列表展平"""
        test_cases = [
            ([[1, 2], [3, 4], [5]], [1, 2, 3, 4, 5]),
            ([[], [1], [2, 3]], [1, 2, 3]),
            ([[]], []),
            ([], [])
        ]

        for input_list, expected in test_cases:
            result = flatten(input_list)
            assert result == expected
    
    def test_chunk_list(self):
        """测试列表分块"""
        # 正常分块
        result = chunk_list([1, 2, 3, 4, 5, 6, 7], 3)
        expected = [[1, 2, 3], [4, 5, 6], [7]]
        assert result == expected
        
        # 完整分块
        result = chunk_list([1, 2, 3, 4], 2)
        expected = [[1, 2], [3, 4]]
        assert result == expected
        
        # 空列表
        result = chunk_list([], 3)
        expected = []
        assert result == expected
        
        # 单个元素
        result = chunk_list([1], 3)
        expected = [[1]]
        assert result == expected
        
        # 无效块大小
        with pytest.raises(ValueError):
            chunk_list([1, 2, 3], 0)
        
        with pytest.raises(ValueError):
            chunk_list([1, 2, 3], -1)
    
    def test_mask_sensitive_info(self):
        """测试敏感信息遮蔽"""
        # 测试空字符串
        assert mask_sensitive_info("") == ""
        
        # 测试非常短的字符串（特殊保护）
        assert mask_sensitive_info("a") == "*"
        assert mask_sensitive_info("ab") == "**"
        assert mask_sensitive_info("abc") == "***"
        assert mask_sensitive_info("abcd") == "****"
        assert mask_sensitive_info("abcde") == "*****"
        assert mask_sensitive_info("abcdef") == "******"
        
        # 测试短字符串
        # 对于长度 <= show_chars * 2 + 3 的字符串，动态调整显示字符数
        # 7个字符: (7-3)//2 = 2，显示前后2个
        assert mask_sensitive_info("abcdefg") == "ab...fg"
        # 8个字符: (8-3)//2 = 2，显示前后2个
        assert mask_sensitive_info("abcdefgh") == "ab...gh"
        # 9个字符: (9-3)//2 = 3，显示前后3个
        assert mask_sensitive_info("abcdefghi") == "abc...ghi"
        # 10个字符: (10-3)//2 = 3，显示前后3个
        assert mask_sensitive_info("abcdefghij") == "abc...hij"
        # 11个字符: (11-3)//2 = 4，但默认show_chars=4，所以显示前后4个
        assert mask_sensitive_info("abcdefghijk") == "abcd...hijk"
        
        # 测试正常长度字符串
        assert mask_sensitive_info("abcdefghijklmnop") == "abcd...mnop"
        
        # 测试WireGuard密钥长度的字符串（44字符）
        wg_key = "YMEbQjglenvTMTSn25tnACGdw7phNht4Io87ECW1ckA="
        masked = mask_sensitive_info(wg_key)
        assert masked.startswith("YMEb")
        assert masked.endswith("ckA=")
        assert "..." in masked
        assert len(masked) < len(wg_key)
        
        # 测试自定义显示字符数
        assert mask_sensitive_info("abcdefghijklmnop", 2) == "ab...op"
        assert mask_sensitive_info("abcdefghijklmnop", 6) == "abcdef...klmnop"
