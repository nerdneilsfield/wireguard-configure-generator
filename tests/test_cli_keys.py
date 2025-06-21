"""
Tests for CLI keys commands
"""

import pytest
import tempfile
import os
import json
from click.testing import CliRunner
from wg_mesh_gen.cli import cli
from wg_mesh_gen.simple_storage import SimpleKeyStorage


class TestCLIKeysCommands:
    """Test CLI keys command group"""
    
    @pytest.fixture
    def runner(self):
        """Create a CLI runner"""
        return CliRunner()
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database path"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_keys_generate_command(self, runner, temp_db):
        """Test keys generate subcommand"""
        node_name = "test_node"
        
        result = runner.invoke(cli, [
            'keys', 'generate', node_name,
            '--db-path', temp_db
        ])
        
        assert result.exit_code == 0
        assert f"Keys generated for node: {node_name}" in result.output
        assert "Public key:" in result.output
        
        # Verify keys were actually stored
        storage = SimpleKeyStorage(temp_db)
        keys = storage.get_keypair(node_name)
        assert keys is not None
        assert len(keys) == 2  # (private_key, public_key)
        storage.close()
    
    def test_keys_generate_with_verbose(self, runner, temp_db):
        """Test keys generate with verbose output"""
        result = runner.invoke(cli, [
            'keys', 'generate', 'verbose_node',
            '--db-path', temp_db,
            '--verbose'
        ])
        
        assert result.exit_code == 0
        # Just check that command succeeded
        assert "Keys generated for node: verbose_node" in result.output
    
    def test_keys_list_empty(self, runner, temp_db):
        """Test listing keys when storage is empty"""
        result = runner.invoke(cli, [
            'keys', 'list',
            '--db-path', temp_db
        ])
        
        assert result.exit_code == 0
        assert "No keys stored" in result.output
    
    def test_keys_list_with_keys(self, runner, temp_db):
        """Test listing keys with stored keys"""
        # Pre-populate storage
        storage = SimpleKeyStorage(temp_db)
        storage.store_keypair("node1", "priv1", "pub1")
        storage.store_keypair("node2", "priv2", "pub2")
        storage.close()
        
        result = runner.invoke(cli, [
            'keys', 'list',
            '--db-path', temp_db
        ])
        
        assert result.exit_code == 0
        assert "Stored keys:" in result.output
        assert "node1" in result.output
        assert "node2" in result.output
        assert "(Public: pub1" in result.output
        assert "(Public: pub2" in result.output
    
    def test_keys_show_existing(self, runner, temp_db):
        """Test showing existing key"""
        # Pre-populate storage
        storage = SimpleKeyStorage(temp_db)
        storage.store_keypair("show_node", "private_key_123", "public_key_456")
        storage.close()
        
        result = runner.invoke(cli, [
            'keys', 'show', 'show_node',
            '--db-path', temp_db
        ])
        
        assert result.exit_code == 0
        assert "Keys for node: show_node" in result.output
        assert "Public key: public_key_456" in result.output
        assert "Private key:" in result.output
        # Check that private key is masked (shows only part of it)
        assert "priv" in result.output  # First 4 chars
        assert "_123" in result.output  # Last 4 chars
        assert "private_key_123" not in result.output  # Should not show full private key
    
    def test_keys_show_nonexistent(self, runner, temp_db):
        """Test showing non-existent key"""
        result = runner.invoke(cli, [
            'keys', 'show', 'nonexistent_node',
            '--db-path', temp_db
        ])
        
        assert result.exit_code == 0
        assert "No keys found for node: nonexistent_node" in result.output
    
    def test_keys_delete_existing(self, runner, temp_db):
        """Test deleting existing key"""
        # Pre-populate storage
        storage = SimpleKeyStorage(temp_db)
        storage.store_keypair("delete_node", "priv", "pub")
        storage.close()
        
        # Test delete with confirmation
        result = runner.invoke(cli, [
            'keys', 'delete', 'delete_node',
            '--db-path', temp_db
        ], input='y\n')
        
        assert result.exit_code == 0
        assert "Keys deleted for node: delete_node" in result.output
        
        # Verify key was actually deleted
        storage = SimpleKeyStorage(temp_db)
        assert storage.get_keypair("delete_node") is None
        storage.close()
    
    def test_keys_delete_nonexistent(self, runner, temp_db):
        """Test deleting non-existent key"""
        result = runner.invoke(cli, [
            'keys', 'delete', 'nonexistent_node',
            '--db-path', temp_db
        ], input='y\n')
        
        assert result.exit_code == 0
        assert "No keys found for node: nonexistent_node" in result.output
    
    def test_keys_delete_cancelled(self, runner, temp_db):
        """Test cancelling key deletion"""
        # Pre-populate storage
        storage = SimpleKeyStorage(temp_db)
        storage.store_keypair("cancel_node", "priv", "pub")
        storage.close()
        
        # Test delete with cancellation
        result = runner.invoke(cli, [
            'keys', 'delete', 'cancel_node',
            '--db-path', temp_db
        ], input='n\n')
        
        assert result.exit_code == 1  # Should abort
        
        # Verify key was NOT deleted
        storage = SimpleKeyStorage(temp_db)
        assert storage.get_keypair("cancel_node") is not None
        storage.close()
    
    def test_keys_with_log_file(self, runner, temp_db):
        """Test keys command with log file"""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
            log_file = f.name
        
        try:
            result = runner.invoke(cli, [
                'keys', 'generate', 'log_test',
                '--db-path', temp_db,
                '--log-file', log_file
            ])
            
            assert result.exit_code == 0
            
            # Check log file was created and contains content
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "生成密钥对" in log_content or "generating" in log_content.lower()
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_keys_generate_duplicate(self, runner, temp_db):
        """Test generating keys for existing node (should overwrite)"""
        node_name = "duplicate_node"
        
        # Generate first time
        result1 = runner.invoke(cli, [
            'keys', 'generate', node_name,
            '--db-path', temp_db
        ])
        assert result1.exit_code == 0
        
        # Get first public key
        storage = SimpleKeyStorage(temp_db)
        keys1 = storage.get_keypair(node_name)
        pub_key1 = keys1[1]
        storage.close()
        
        # Generate second time (should overwrite)
        result2 = runner.invoke(cli, [
            'keys', 'generate', node_name,
            '--db-path', temp_db
        ])
        assert result2.exit_code == 0
        
        # Get second public key
        storage = SimpleKeyStorage(temp_db)
        keys2 = storage.get_keypair(node_name)
        pub_key2 = keys2[1]
        storage.close()
        
        # Keys should be different
        assert pub_key1 != pub_key2