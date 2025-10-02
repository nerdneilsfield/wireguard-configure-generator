"""Unit tests for key_manager module."""

import base64
import json
from pathlib import Path

import pytest

from wg_mesh_gen import key_manager


class TestKeyGeneration:
    """Test key generation functions."""

    def test_generate_private_key_returns_valid_base64(self):
        """Test that generate_private_key() returns valid 44-char base64."""
        private_key = key_manager.generate_private_key()

        assert len(private_key) == 44
        # Verify it's valid base64
        decoded = base64.b64decode(private_key)
        assert len(decoded) == 32  # 32 bytes

    def test_derive_public_key_from_private(self):
        """Test that derive_public_key() derives from private key."""
        private_key = key_manager.generate_private_key()
        public_key = key_manager.derive_public_key(private_key)

        assert len(public_key) == 44
        # Verify it's valid base64
        decoded = base64.b64decode(public_key)
        assert len(decoded) == 32

    def test_generate_preshared_key_returns_valid_base64(self):
        """Test that generate_preshared_key() returns valid 44-char base64."""
        psk = key_manager.generate_preshared_key()

        assert len(psk) == 44
        # Verify it's valid base64
        decoded = base64.b64decode(psk)
        assert len(decoded) == 32

    def test_keys_are_wireguard_compatible(self):
        """Test that generated keys are WireGuard compatible format."""
        private_key = key_manager.generate_private_key()
        public_key = key_manager.derive_public_key(private_key)
        psk = key_manager.generate_preshared_key()

        # All should be base64-encoded 32-byte values
        for key in [private_key, public_key, psk]:
            assert len(key) == 44
            assert base64.b64decode(key)  # Should not raise


class TestKeyStorage:
    """Test key storage functions."""

    def test_save_keys_to_json(self, tmp_path):
        """Test that save_keys_to_json() creates valid JSON file."""
        keys_file = tmp_path / "keys.json"
        keys = {
            "version": "1.0",
            "server": {
                "private_key": "test1",
                "public_key": "test2",
                "preshared_key": "test3",
            },
            "clients": {},
        }

        key_manager.save_keys_to_json(keys, keys_file)

        assert keys_file.exists()
        loaded = json.loads(keys_file.read_text())
        assert loaded == keys

    def test_load_keys_from_json(self, tmp_path):
        """Test that load_keys_from_json() loads JSON correctly."""
        keys_file = tmp_path / "keys.json"
        keys = {
            "version": "1.0",
            "server": {"private_key": "test"},
            "clients": {},
        }
        keys_file.write_text(json.dumps(keys))

        loaded = key_manager.load_keys_from_json(keys_file)

        assert loaded == keys

    def test_load_keys_handles_missing_file(self, tmp_path):
        """Test that load_keys_from_json() handles missing file."""
        keys_file = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            key_manager.load_keys_from_json(keys_file)

    def test_keys_file_has_0600_permissions(self, tmp_path):
        """Test that saved keys file has 0600 permissions."""
        import os

        keys_file = tmp_path / "keys.json"
        keys = {"version": "1.0", "server": {}, "clients": {}}

        key_manager.save_keys_to_json(keys, keys_file)

        file_mode = os.stat(keys_file).st_mode & 0o777
        assert file_mode == 0o600
