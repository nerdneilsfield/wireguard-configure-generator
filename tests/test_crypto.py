"""
测试加密功能
"""

import pytest
import base64
import re
from wg_mesh_gen.crypto import (
    generate_private_key, derive_public_key, generate_preshared_key,
    generate_keypair, _generate_private_key_manual, _derive_public_key_manual
)


class TestKeyGeneration:
    """测试密钥生成功能"""
    
    def test_generate_private_key(self):
        """测试私钥生成"""
        private_key = generate_private_key()
        
        # 验证是有效的base64编码
        try:
            decoded = base64.b64decode(private_key)
            assert len(decoded) == 32  # WireGuard私钥应该是32字节
        except Exception:
            pytest.fail("Generated private key is not valid base64")
        
        # 验证密钥格式
        assert isinstance(private_key, str)
        assert len(private_key) == 44  # base64编码的32字节应该是44字符
        assert private_key.endswith('=')  # base64填充
    
    def test_generate_private_key_manual(self):
        """测试手动私钥生成"""
        private_key = _generate_private_key_manual()
        
        # 验证是有效的base64编码
        try:
            decoded = base64.b64decode(private_key)
            assert len(decoded) == 32
        except Exception:
            pytest.fail("Manually generated private key is not valid base64")
        
        # 验证WireGuard密钥约束（clamping）
        decoded_bytes = base64.b64decode(private_key)
        assert decoded_bytes[0] & 7 == 0  # 低3位应该为0
        assert decoded_bytes[31] & 128 == 0  # 最高位应该为0
        assert decoded_bytes[31] & 64 == 64  # 次高位应该为1
    
    def test_derive_public_key(self):
        """测试公钥派生"""
        private_key = generate_private_key()
        public_key = derive_public_key(private_key)
        
        # 验证是有效的base64编码
        try:
            decoded = base64.b64decode(public_key)
            assert len(decoded) == 32  # WireGuard公钥应该是32字节
        except Exception:
            pytest.fail("Derived public key is not valid base64")
        
        # 验证密钥格式
        assert isinstance(public_key, str)
        assert len(public_key) == 44  # base64编码的32字节应该是44字符
    
    def test_generate_preshared_key(self):
        """测试预共享密钥生成"""
        psk = generate_preshared_key()
        
        # 验证是有效的base64编码
        try:
            decoded = base64.b64decode(psk)
            assert len(decoded) == 32  # PSK应该是32字节
        except Exception:
            pytest.fail("Generated PSK is not valid base64")
        
        # 验证密钥格式
        assert isinstance(psk, str)
        assert len(psk) == 44  # base64编码的32字节应该是44字符
    
    def test_generate_keypair(self):
        """测试密钥对生成"""
        private_key, public_key = generate_keypair()
        
        # 验证私钥
        assert isinstance(private_key, str)
        assert len(private_key) == 44
        
        # 验证公钥
        assert isinstance(public_key, str)
        assert len(public_key) == 44
        
        # 验证公钥是从私钥正确派生的
        derived_public = derive_public_key(private_key)
        assert public_key == derived_public
    
    def test_key_uniqueness(self):
        """测试密钥唯一性"""
        # 生成多个密钥，确保它们都不相同
        private_keys = [generate_private_key() for _ in range(10)]
        public_keys = [derive_public_key(pk) for pk in private_keys]
        psks = [generate_preshared_key() for _ in range(10)]
        
        # 验证私钥唯一性
        assert len(set(private_keys)) == len(private_keys)
        
        # 验证公钥唯一性
        assert len(set(public_keys)) == len(public_keys)
        
        # 验证PSK唯一性
        assert len(set(psks)) == len(psks)
    
    def test_key_consistency(self):
        """测试密钥一致性"""
        # 同一个私钥应该总是派生出相同的公钥
        private_key = generate_private_key()
        
        public_key1 = derive_public_key(private_key)
        public_key2 = derive_public_key(private_key)
        
        assert public_key1 == public_key2


class TestKeyValidation:
    """测试密钥验证功能"""
    
    def test_valid_base64_format(self):
        """测试有效的base64格式"""
        # 生成的密钥应该都是有效的base64
        private_key = generate_private_key()
        public_key = derive_public_key(private_key)
        psk = generate_preshared_key()
        
        # 验证base64格式
        base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
        
        assert base64_pattern.match(private_key)
        assert base64_pattern.match(public_key)
        assert base64_pattern.match(psk)
    
    def test_invalid_private_key_handling(self):
        """测试无效私钥处理"""
        # 测试无效的base64字符串
        invalid_keys = [
            "invalid_base64!",
            "too_short",
            "a" * 100,  # 太长
            "",  # 空字符串
        ]
        
        for invalid_key in invalid_keys:
            try:
                # 这可能会抛出异常，这是预期的
                public_key = derive_public_key(invalid_key)
                # 如果没有抛出异常，至少验证结果是字符串
                assert isinstance(public_key, str)
            except Exception:
                # 抛出异常是可以接受的
                pass


class TestCryptographicProperties:
    """测试加密属性"""
    
    def test_private_key_clamping(self):
        """测试私钥约束（clamping）"""
        # 生成多个私钥并验证它们都满足WireGuard的约束要求
        for _ in range(10):
            private_key = _generate_private_key_manual()
            decoded = base64.b64decode(private_key)
            
            # 验证clamping
            assert decoded[0] & 7 == 0  # 低3位清零
            assert decoded[31] & 128 == 0  # 最高位清零
            assert decoded[31] & 64 == 64  # 次高位置1
    
    def test_key_entropy(self):
        """测试密钥熵"""
        # 生成多个密钥并检查它们的随机性
        keys = [generate_private_key() for _ in range(100)]
        
        # 简单的熵测试：检查字符分布
        all_chars = ''.join(keys)
        char_counts = {}
        for char in all_chars:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # 验证没有字符出现频率过高（简单的随机性检查）
        total_chars = len(all_chars)
        for char, count in char_counts.items():
            frequency = count / total_chars
            # 在base64字符集中，每个字符的期望频率约为1/64
            # 允许一定的偏差
            assert frequency < 0.05, f"Character '{char}' appears too frequently: {frequency}"
