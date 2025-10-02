"""Unit tests for loader module."""

import json
from pathlib import Path

import pytest
import tomllib

from wg_mesh_gen import loader


class TestLoadToml:
    """Test load_toml function."""

    def test_load_toml_parses_valid_toml(self, tmp_path, sample_toml_config):
        """Test that load_toml() parses valid TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(sample_toml_config)

        result = loader.load_toml(config_file)

        assert isinstance(result, dict)
        assert "common" in result
        assert "server" in result
        assert "clients" in result

    def test_load_toml_raises_error_on_invalid_toml(self, tmp_path):
        """Test that load_toml() raises error on invalid TOML."""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text("[broken\nsyntax")

        with pytest.raises(tomllib.TOMLDecodeError):
            loader.load_toml(config_file)

    def test_load_toml_handles_missing_file(self, tmp_path):
        """Test that load_toml() handles missing file."""
        config_file = tmp_path / "missing.toml"

        with pytest.raises(FileNotFoundError):
            loader.load_toml(config_file)


class TestWriteToml:
    """Test write_toml function."""

    def test_write_toml_creates_valid_file(self, tmp_path):
        """Test that write_toml() creates valid TOML file."""
        config_file = tmp_path / "output.toml"
        data = {
            "common": {"network_name": "test"},
            "server": {"name": "srv"},
        }

        loader.write_toml(data, config_file)

        assert config_file.exists()
        # Verify it's valid TOML by loading it back
        loaded = loader.load_toml(config_file)
        assert loaded == data
