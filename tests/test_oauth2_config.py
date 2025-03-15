"""
Tests for the OAuth2 configuration module.
"""

import json
import os
import tempfile
from unittest import mock
from pathlib import Path

import pytest

from imap_mcp.config import ServerConfig
from imap_mcp.oauth2_config import OAuth2Config


@pytest.fixture
def sample_client_config():
    """Return a sample client configuration dictionary."""
    return {
        "installed": {
            "client_id": "test-client-id.apps.googleusercontent.com",
            "client_secret": "test-client-secret",
            "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


@pytest.fixture
def temp_credentials_file(sample_client_config):
    """Create a temporary credentials file with test data."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump(sample_client_config, f)
        temp_file_path = f.name
    
    yield temp_file_path
    
    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


def test_oauth2_config_init():
    """Test OAuth2Config initialization."""
    config = OAuth2Config(
        credentials_file="test.json",
        token_file="token.json",
        scopes=["https://mail.google.com/"],
        client_id="test_id",
        client_secret="test_secret"
    )
    
    assert config.credentials_file == "test.json"
    assert config.token_file == "token.json"
    assert config.scopes == ["https://mail.google.com/"]
    assert config.client_id == "test_id"
    assert config.client_secret == "test_secret"


def test_from_server_config():
    """Test creating OAuth2Config from ServerConfig."""
    # Create a mock ServerConfig object with the oauth2 property
    server_config = mock.MagicMock(spec=ServerConfig)
    server_config.oauth2 = {
        "credentials_file": "client_secret.json", 
        "token_file": "custom_token.json",
        "scopes": ["https://mail.google.com/", "custom_scope"]
    }
    server_config.password = "test_password"
    
    oauth2_config = OAuth2Config.from_server_config(server_config)
    
    assert oauth2_config.credentials_file == "client_secret.json"
    assert oauth2_config.token_file == "custom_token.json"
    assert oauth2_config.scopes == ["https://mail.google.com/", "custom_scope"]


def test_from_server_config_defaults():
    """Test creating OAuth2Config with default values when not in ServerConfig."""
    # Create a mock ServerConfig object without the oauth2 property
    server_config = mock.MagicMock(spec=ServerConfig)
    server_config.oauth2 = None
    server_config.password = "test_password"
    
    oauth2_config = OAuth2Config.from_server_config(server_config)
    
    assert oauth2_config.credentials_file == ""
    assert oauth2_config.token_file == "gmail_token.json"
    assert oauth2_config.scopes == ["https://mail.google.com/"]


def test_from_server_config_with_env_vars():
    """Test that environment variables override config values."""
    # Create a mock ServerConfig object with the oauth2 property
    server_config = mock.MagicMock(spec=ServerConfig)
    server_config.oauth2 = {
        "credentials_file": "client_secret.json",
        "token_file": "token.json",
        "scopes": ["https://mail.google.com/"]
    }
    server_config.password = "test_password"
    
    with mock.patch.dict(os.environ, {
        "GMAIL_CLIENT_ID": "env_client_id",
        "GMAIL_CLIENT_SECRET": "env_client_secret"
    }):
        oauth2_config = OAuth2Config.from_server_config(server_config)
        
        assert oauth2_config.client_id == "env_client_id"
        assert oauth2_config.client_secret == "env_client_secret"


def test_load_client_config(temp_credentials_file, sample_client_config):
    """Test loading client config from a file."""
    config = OAuth2Config(
        credentials_file=temp_credentials_file,
        token_file="token.json",
        scopes=["https://mail.google.com/"]
    )
    
    client_config = config.load_client_config()
    
    assert client_config == sample_client_config
    assert config.client_id == sample_client_config["installed"]["client_id"]
    assert config.client_secret == sample_client_config["installed"]["client_secret"]


def test_load_client_config_with_direct_credentials():
    """Test that directly provided credentials are used instead of file."""
    config = OAuth2Config(
        credentials_file="nonexistent.json",
        token_file="token.json",
        scopes=["https://mail.google.com/"],
        client_id="direct_client_id",
        client_secret="direct_client_secret"
    )
    
    client_config = config.load_client_config()
    
    assert client_config["installed"]["client_id"] == "direct_client_id"
    assert client_config["installed"]["client_secret"] == "direct_client_secret"
    assert config.client_id == "direct_client_id"
    assert config.client_secret == "direct_client_secret"


def test_missing_credentials_file():
    """Test error handling for missing credentials file."""
    config = OAuth2Config(
        credentials_file="nonexistent.json",
        token_file="token.json",
        scopes=["https://mail.google.com/"]
    )
    
    with pytest.raises(FileNotFoundError):
        config.load_client_config()


def test_invalid_credentials_file():
    """Test error handling for invalid JSON in credentials file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        f.write("This is not valid JSON")
        temp_file_path = f.name
    
    config = OAuth2Config(
        credentials_file=temp_file_path,
        token_file="token.json",
        scopes=["https://mail.google.com/"]
    )
    
    try:
        with pytest.raises(ValueError):
            config.load_client_config()
    finally:
        # Clean up
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def test_no_credentials_file_or_direct_credentials():
    """Test error handling when no credentials source is provided."""
    config = OAuth2Config(
        credentials_file="",
        token_file="token.json",
        scopes=["https://mail.google.com/"]
    )
    
    with pytest.raises(ValueError, match="No credentials file specified"):
        config.load_client_config()
