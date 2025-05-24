"""
测试密钥存储功能
"""

import pytest
import tempfile
import os
from wg_mesh_gen.storage import KeyStorage
from wg_mesh_gen.crypto import generate_keypair, generate_preshared_key


class TestKeyStorage:
    """测试密钥存储功能"""
    
    def test_storage_initialization(self):
        """测试存储初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            with KeyStorage(db_path) as storage:
                assert storage.db_path == db_path
                assert storage.engine is not None
                assert storage.session is not None
    
    def test_store_and_retrieve_keypair(self):
        """测试存储和检索密钥对"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            private_key, public_key = generate_keypair()
            psk = generate_preshared_key()
            
            with KeyStorage(db_path) as storage:
                # 存储密钥对
                storage.store_keypair("test_node", private_key, public_key, psk)
                
                # 检索密钥对
                retrieved = storage.get_keypair("test_node")
                
                assert retrieved is not None
                assert retrieved['private_key'] == private_key
                assert retrieved['public_key'] == public_key
                assert retrieved['psk'] == psk
    
    def test_store_keypair_without_psk(self):
        """测试存储不带PSK的密钥对"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            private_key, public_key = generate_keypair()
            
            with KeyStorage(db_path) as storage:
                # 存储不带PSK的密钥对
                storage.store_keypair("test_node", private_key, public_key)
                
                # 检索密钥对
                retrieved = storage.get_keypair("test_node")
                
                assert retrieved is not None
                assert retrieved['private_key'] == private_key
                assert retrieved['public_key'] == public_key
                assert retrieved['psk'] is None
    
    def test_update_existing_keypair(self):
        """测试更新已存在的密钥对"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            # 第一组密钥
            private_key1, public_key1 = generate_keypair()
            psk1 = generate_preshared_key()
            
            # 第二组密钥
            private_key2, public_key2 = generate_keypair()
            psk2 = generate_preshared_key()
            
            with KeyStorage(db_path) as storage:
                # 存储第一组密钥
                storage.store_keypair("test_node", private_key1, public_key1, psk1)
                
                # 更新为第二组密钥
                storage.store_keypair("test_node", private_key2, public_key2, psk2)
                
                # 检索密钥对，应该是第二组
                retrieved = storage.get_keypair("test_node")
                
                assert retrieved is not None
                assert retrieved['private_key'] == private_key2
                assert retrieved['public_key'] == public_key2
                assert retrieved['psk'] == psk2
    
    def test_get_nonexistent_keypair(self):
        """测试获取不存在的密钥对"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            with KeyStorage(db_path) as storage:
                retrieved = storage.get_keypair("nonexistent_node")
                assert retrieved is None
    
    def test_list_keys(self):
        """测试列出密钥"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            with KeyStorage(db_path) as storage:
                # 初始状态应该为空
                keys = storage.list_keys()
                assert keys == []
                
                # 添加一些密钥
                for i, node_name in enumerate(['node1', 'node2', 'node3']):
                    private_key, public_key = generate_keypair()
                    storage.store_keypair(node_name, private_key, public_key)
                
                # 列出密钥
                keys = storage.list_keys()
                assert len(keys) == 3
                assert set(keys) == {'node1', 'node2', 'node3'}
    
    def test_delete_keypair(self):
        """测试删除密钥对"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            private_key, public_key = generate_keypair()
            
            with KeyStorage(db_path) as storage:
                # 存储密钥对
                storage.store_keypair("test_node", private_key, public_key)
                
                # 验证存在
                assert storage.get_keypair("test_node") is not None
                
                # 删除密钥对
                success = storage.delete_keypair("test_node")
                assert success is True
                
                # 验证已删除
                assert storage.get_keypair("test_node") is None
    
    def test_delete_nonexistent_keypair(self):
        """测试删除不存在的密钥对"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            with KeyStorage(db_path) as storage:
                # 尝试删除不存在的密钥对
                success = storage.delete_keypair("nonexistent_node")
                assert success is False
    
    def test_multiple_storage_instances(self):
        """测试多个存储实例"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            private_key, public_key = generate_keypair()
            
            # 第一个实例存储
            with KeyStorage(db_path) as storage1:
                storage1.store_keypair("test_node", private_key, public_key)
            
            # 第二个实例检索
            with KeyStorage(db_path) as storage2:
                retrieved = storage2.get_keypair("test_node")
                assert retrieved is not None
                assert retrieved['private_key'] == private_key
                assert retrieved['public_key'] == public_key
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            private_key, public_key = generate_keypair()
            
            # 使用上下文管理器
            with KeyStorage(db_path) as storage:
                storage.store_keypair("test_node", private_key, public_key)
                retrieved = storage.get_keypair("test_node")
                assert retrieved is not None
            
            # 上下文管理器应该自动关闭连接
            # 重新打开应该仍然能访问数据
            with KeyStorage(db_path) as storage:
                retrieved = storage.get_keypair("test_node")
                assert retrieved is not None
                assert retrieved['private_key'] == private_key
