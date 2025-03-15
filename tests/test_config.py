"""Tests for the config module."""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch

import pytest
import yaml

from imap_mcp.config import ImapConfig, ServerConfig, load_config


class TestImapConfig:
    """Test cases for the ImapConfig class."""

    def test_init(self):
        """Test ImapConfig initialization."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password"
        )
        
        assert config.host == "imap.example.com"
        assert config.port == 993
        assert config.username == "test@example.com"
        assert config.password == "password"
        assert config.use_ssl is True  # Default value
        
        # Test with custom SSL setting
        config = ImapConfig(
            host="imap.example.com",
            port=143,
            username="test@example.com",
            password="password",
            use_ssl=False
        )
        assert config.use_ssl is False

    def test_from_dict(self):
        """Test creating ImapConfig from a dictionary."""
        data = {
            "host": "imap.example.com",
            "port": 993,
            "username": "test@example.com",
            "password": "password",
            "use_ssl": True
        }
        
        config = ImapConfig.from_dict(data)
        assert config.host == "imap.example.com"
        assert config.port == 993
        assert config.username == "test@example.com"
        assert config.password == "password"
        assert config.use_ssl is True
        
        # Test with minimal data and defaults
        minimal_data = {
            "host": "imap.example.com",
            "username": "test@example.com",
            "password": "password"
        }
        
        config = ImapConfig.from_dict(minimal_data)
        assert config.host == "imap.example.com"
        assert config.port == 993  # Default with SSL
        assert config.username == "test@example.com"
        assert config.password == "password"
        assert config.use_ssl is True  # Default
        
        # Test with non-SSL port default
        non_ssl_data = {
            "host": "imap.example.com",
            "username": "test@example.com",
            "password": "password",
            "use_ssl": False
        }
        
        config = ImapConfig.from_dict(non_ssl_data)
        assert config.port == 143  # Default non-SSL port

    def test_from_dict_with_env_password(self, monkeypatch):
        """Test creating ImapConfig with password from environment variable."""
        # Set environment variable
        monkeypatch.setenv("IMAP_PASSWORD", "env_password")
        
        data = {
            "host": "imap.example.com",
            "username": "test@example.com",
            # No password in dict
        }
        
        config = ImapConfig.from_dict(data)
        assert config.password == "env_password"
        
        # Test that dict password takes precedence
        data_with_password = {
            "host": "imap.example.com",
            "username": "test@example.com",
            "password": "dict_password"
        }
        
        config = ImapConfig.from_dict(data_with_password)
        assert config.password == "dict_password"

    def test_from_dict_missing_password(self, monkeypatch):
        """Test error when password is missing from both dict and environment."""
        # Ensure environment variable is not set
        monkeypatch.delenv("IMAP_PASSWORD", raising=False)
        
        data = {
            "host": "imap.example.com",
            "username": "test@example.com",
            # No password
        }
        
        with pytest.raises(ValueError) as excinfo:
            ImapConfig.from_dict(data)
        
        assert "IMAP password must be specified" in str(excinfo.value)

    def test_from_dict_missing_required_fields(self):
        """Test error when required fields are missing."""
        # Missing host
        with pytest.raises(KeyError):
            ImapConfig.from_dict({"username": "test@example.com", "password": "password"})
        
        # Missing username
        with pytest.raises(KeyError):
            ImapConfig.from_dict({"host": "imap.example.com", "password": "password"})


class TestServerConfig:
    """Test cases for the ServerConfig class."""

    def test_init(self):
        """Test ServerConfig initialization."""
        imap_config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password"
        )
        
        # Test without allowed folders
        server_config = ServerConfig(imap=imap_config)
        assert server_config.imap == imap_config
        assert server_config.allowed_folders is None
        
        # Test with allowed folders
        allowed_folders = ["INBOX", "Sent", "Archive"]
        server_config = ServerConfig(imap=imap_config, allowed_folders=allowed_folders)
        assert server_config.imap == imap_config
        assert server_config.allowed_folders == allowed_folders

    def test_from_dict(self, monkeypatch):
        """Test creating ServerConfig from a dictionary."""
        data = {
            "imap": {
                "host": "imap.example.com",
                "port": 993,
                "username": "test@example.com",
                "password": "password"
            },
            "allowed_folders": ["INBOX", "Sent"]
        }
        
        config = ServerConfig.from_dict(data)
        assert config.imap.host == "imap.example.com"
        assert config.imap.port == 993
        assert config.imap.username == "test@example.com"
        assert config.imap.password == "password"
        assert config.allowed_folders == ["INBOX", "Sent"]
        
        # Test with minimal data (no allowed_folders)
        minimal_data = {
            "imap": {
                "host": "imap.example.com",
                "username": "test@example.com",
                "password": "password"
            }
        }
        
        config = ServerConfig.from_dict(minimal_data)
        assert config.imap.host == "imap.example.com"
        assert config.allowed_folders is None
        
        # Test with empty dict (needs env password)
        monkeypatch.setenv("IMAP_PASSWORD", "env_password")
        with pytest.raises(KeyError):
            # Should fail because host is required
            ServerConfig.from_dict({})


class TestLoadConfig:
    """Test cases for the load_config function."""

    def test_load_from_file(self):
        """Test loading configuration from a file."""
        config_data = {
            "imap": {
                "host": "imap.example.com",
                "port": 993,
                "username": "test@example.com",
                "password": "password"
            },
            "allowed_folders": ["INBOX", "Sent"]
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+") as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file.flush()
            
            # Load config from the temp file
            config = load_config(temp_file.name)
            
            # Verify config data
            assert config.imap.host == "imap.example.com"
            assert config.imap.port == 993
            assert config.imap.username == "test@example.com"
            assert config.imap.password == "password"
            assert config.allowed_folders == ["INBOX", "Sent"]

    def test_load_from_default_locations(self, monkeypatch, tmp_path):
        """Test loading configuration from default locations."""
        # Clear any environment variables that might affect the test
        for env_var in [
            "IMAP_HOST", "IMAP_PORT", "IMAP_USERNAME", "IMAP_PASSWORD",
            "IMAP_USE_SSL", "IMAP_ALLOWED_FOLDERS"
        ]:
            monkeypatch.delenv(env_var, raising=False)
            
        config_data = {
            "imap": {
                "host": "imap.example.com",
                "username": "test@example.com",
                "password": "password"
            }
        }
        
        # Create a temporary config file in one of the default locations
        temp_dir = tmp_path / ".config" / "imap-mcp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / "config.yaml"
        
        with open(temp_file, "w") as f:
            yaml.dump(config_data, f)
        
        # Monkeypatch Path.expanduser to return our temp path
        original_expanduser = Path.expanduser
        def mock_expanduser(self):
            if str(self) == "~/.config/imap-mcp/config.yaml":
                return temp_file
            return original_expanduser(self)
        
        monkeypatch.setattr(Path, "expanduser", mock_expanduser)
        
        # Monkeypatch to ensure no other config file is found
        def mock_exists(path):
            if path == temp_file:
                return True
            return False
        
        monkeypatch.setattr(Path, "exists", mock_exists)
        
        # Load config without specifying path (should find default)
        config = load_config()
        
        # Verify config data
        assert config.imap.host == "imap.example.com"
        assert config.imap.username == "test@example.com"
        assert config.imap.password == "password"

    def test_load_from_env_variables(self, monkeypatch):
        """Test loading configuration from environment variables."""
        # Set environment variables
        monkeypatch.setenv("IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("IMAP_PORT", "993")
        monkeypatch.setenv("IMAP_USERNAME", "test@example.com")
        monkeypatch.setenv("IMAP_PASSWORD", "env_password")
        monkeypatch.setenv("IMAP_USE_SSL", "true")
        monkeypatch.setenv("IMAP_ALLOWED_FOLDERS", "INBOX,Sent,Archive")
        
        # Mock open to raise FileNotFoundError
        original_open = open
        def mock_open(*args, **kwargs):
            if args[0] == "nonexistent_file.yaml":
                raise FileNotFoundError(f"No such file: {args[0]}")
            return original_open(*args, **kwargs)
        
        # Need to patch the built-in open function
        with patch("builtins.open", side_effect=mock_open):
            # Load config (will use env variables since file doesn't exist)
            config = load_config("nonexistent_file.yaml")
            
            # Verify config data
            assert config.imap.host == "imap.example.com"
            assert config.imap.port == 993
            assert config.imap.username == "test@example.com"
            assert config.imap.password == "env_password"
            assert config.imap.use_ssl is True
            assert config.allowed_folders == ["INBOX", "Sent", "Archive"]
            
            # Test with non-SSL setting
            monkeypatch.setenv("IMAP_USE_SSL", "false")
            config = load_config("nonexistent_file.yaml")
            assert config.imap.use_ssl is False

    def test_load_missing_required_env(self, monkeypatch):
        """Test error when required environment variables are missing."""
        # Ensure IMAP_HOST is not set
        monkeypatch.delenv("IMAP_HOST", raising=False)
        
        # Mock open to raise FileNotFoundError
        original_open = open
        def mock_open(*args, **kwargs):
            if args[0] == "nonexistent_file.yaml":
                raise FileNotFoundError(f"No such file: {args[0]}")
            return original_open(*args, **kwargs)
        
        # Need to patch the built-in open function
        with patch("builtins.open", side_effect=mock_open):
            with pytest.raises(ValueError) as excinfo:
                load_config("nonexistent_file.yaml")
            
            assert "IMAP_HOST environment variable not set" in str(excinfo.value)

    def test_invalid_config(self):
        """Test error when config is invalid."""
        # Create a config file with invalid data
        config_data = {
            "imap": {
                # Missing required host
                "username": "test@example.com",
                "password": "password"
            }
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w+") as temp_file:
            yaml.dump(config_data, temp_file)
            temp_file.flush()
            
            # Load should raise ValueError
            with pytest.raises(ValueError) as excinfo:
                load_config(temp_file.name)
            
            assert "Missing required configuration" in str(excinfo.value)