"""
Tests for simple key storage
"""

import pytest
import tempfile
import os
from pathlib import Path
from wg_mesh_gen.simple_storage import SimpleKeyStorage


class TestSimpleKeyStorage:
    """Test simple key storage functionality"""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_storage_initialization(self, temp_storage):
        """Test storage initialization"""
        storage = SimpleKeyStorage(temp_storage)
        assert storage.storage_path == Path(temp_storage)
        assert os.path.exists(temp_storage)
        storage.close()
    
    def test_store_and_retrieve_keypair(self, temp_storage):
        """Test storing and retrieving keypair"""
        storage = SimpleKeyStorage(temp_storage)
        
        # Store keypair
        node_name = "test_node"
        private_key = "private_key_123"
        public_key = "public_key_456"
        
        success = storage.store_keypair(node_name, private_key, public_key)
        assert success
        
        # Retrieve keypair
        keys = storage.get_keypair(node_name)
        assert keys is not None
        assert keys[0] == private_key
        assert keys[1] == public_key
        
        storage.close()
    
    def test_update_existing_keypair(self, temp_storage):
        """Test updating existing keypair"""
        storage = SimpleKeyStorage(temp_storage)
        
        node_name = "test_node"
        
        # Store initial keypair
        storage.store_keypair(node_name, "old_private", "old_public")
        
        # Update with new keypair
        storage.store_keypair(node_name, "new_private", "new_public")
        
        # Verify updated
        keys = storage.get_keypair(node_name)
        assert keys[0] == "new_private"
        assert keys[1] == "new_public"
        
        storage.close()
    
    def test_get_nonexistent_keypair(self, temp_storage):
        """Test getting non-existent keypair"""
        storage = SimpleKeyStorage(temp_storage)
        
        keys = storage.get_keypair("nonexistent_node")
        assert keys is None
        
        storage.close()
    
    def test_list_keys(self, temp_storage):
        """Test listing all keys"""
        storage = SimpleKeyStorage(temp_storage)
        
        # Store multiple keypairs
        storage.store_keypair("node1", "priv1", "pub1")
        storage.store_keypair("node2", "priv2", "pub2")
        storage.store_keypair("node3", "priv3", "pub3")
        
        # List keys
        keys = storage.list_keys()
        assert len(keys) == 3
        
        node_names = [k['node_name'] for k in keys]
        assert "node1" in node_names
        assert "node2" in node_names
        assert "node3" in node_names
        
        # Check key info
        node1_info = next(k for k in keys if k['node_name'] == 'node1')
        assert node1_info['public_key'] == 'pub1'
        assert 'created_at' in node1_info
        
        storage.close()
    
    def test_delete_keypair(self, temp_storage):
        """Test deleting keypair"""
        storage = SimpleKeyStorage(temp_storage)
        
        # Store keypair
        node_name = "test_node"
        storage.store_keypair(node_name, "private", "public")
        
        # Verify exists
        assert storage.has_keypair(node_name)
        
        # Delete
        success = storage.delete_keypair(node_name)
        assert success
        
        # Verify deleted
        assert not storage.has_keypair(node_name)
        assert storage.get_keypair(node_name) is None
        
        storage.close()
    
    def test_delete_nonexistent_keypair(self, temp_storage):
        """Test deleting non-existent keypair"""
        storage = SimpleKeyStorage(temp_storage)
        
        success = storage.delete_keypair("nonexistent")
        assert not success
        
        storage.close()
    
    def test_has_keypair(self, temp_storage):
        """Test checking if keypair exists"""
        storage = SimpleKeyStorage(temp_storage)
        
        node_name = "test_node"
        
        # Check before storing
        assert not storage.has_keypair(node_name)
        
        # Store and check
        storage.store_keypair(node_name, "private", "public")
        assert storage.has_keypair(node_name)
        
        # Delete and check
        storage.delete_keypair(node_name)
        assert not storage.has_keypair(node_name)
        
        storage.close()
    
    def test_concurrent_access(self, temp_storage):
        """Test concurrent access to storage"""
        # Create two storage instances
        storage1 = SimpleKeyStorage(temp_storage)
        storage2 = SimpleKeyStorage(temp_storage)
        
        # Store from first instance
        storage1.store_keypair("node1", "priv1", "pub1")
        
        # Read from second instance
        keys = storage2.get_keypair("node1")
        assert keys is not None
        assert keys[0] == "priv1"
        
        storage1.close()
        storage2.close()
    
    def test_corrupted_file_handling(self, temp_storage):
        """Test handling of corrupted JSON file"""
        # Write invalid JSON
        with open(temp_storage, 'w') as f:
            f.write("invalid json{")
        
        # Should handle gracefully
        storage = SimpleKeyStorage(temp_storage)
        keys = storage.list_keys()
        assert keys == []
        
        # Should be able to store new data
        success = storage.store_keypair("node1", "priv1", "pub1")
        assert success
        
        storage.close()