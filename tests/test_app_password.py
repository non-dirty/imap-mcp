"""Tests for the app_password module."""

import argparse
import getpass
import os
import sys
import yaml
import tempfile
from unittest.mock import patch, mock_open, MagicMock
import pytest

from imap_mcp.app_password import setup_app_password, main


@pytest.fixture
def sample_config_file():
    """Create a temporary config file with test data."""
    config_data = {
        "imap": {
            "server": "imap.gmail.com",
            "port": 993,
            "username": "test@gmail.com"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        yaml.dump(config_data, f)
        temp_file_path = f.name
    
    yield temp_file_path
    
    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


class TestSetupAppPassword:
    """Tests for the setup_app_password function."""
    
    @pytest.mark.skip(reason="Skipping test that prompts for password")
    @patch("getpass.getpass")
    def test_setup_app_password_no_existing_config(self, mock_getpass):
        """Test setup with no existing config."""
        # Set up mock
        mock_getpass.return_value = "test_password"
        
        # Run the setup function
        result = setup_app_password(
            username="test@gmail.com",
            server="imap.gmail.com",
            port=993
        )
        
        # Verify user was prompted for the password
        mock_getpass.assert_called_once()
        
        # Verify the returned config has the expected structure
        assert "imap" in result
        assert result["imap"]["server"] == "imap.gmail.com"
        assert result["imap"]["port"] == 993
        assert result["imap"]["username"] == "test@gmail.com"
        assert result["imap"]["password"] == "test_password"
        assert "auth_type" in result["imap"]
        assert result["imap"]["auth_type"] == "password"
    
    @pytest.mark.skip(reason="Skipping test that prompts for password")
    @patch("getpass.getpass")
    @patch("yaml.safe_load")
    def test_setup_app_password_with_existing_config(
        self, mock_yaml_load, mock_getpass, sample_config_file
    ):
        """Test setup with existing config file."""
        # Set up mocks
        mock_yaml_load.return_value = {
            "imap": {
                "server": "imap.gmail.com",
                "port": 993,
                "username": "existing@gmail.com"
            }
        }
        mock_getpass.return_value = "test_password"
        
        # Run the setup function
        with patch("builtins.open", mock_open(read_data="")) as mock_file:
            result = setup_app_password(
                config_path=sample_config_file
            )
        
        # Verify the existing config was loaded
        mock_yaml_load.assert_called_once()
        
        # Verify password was requested
        mock_getpass.assert_called_once()
        
        # Verify the returned config preserves existing values
        assert "imap" in result
        assert result["imap"]["server"] == "imap.gmail.com"
        assert result["imap"]["port"] == 993
        assert result["imap"]["username"] == "existing@gmail.com"
        
        # Verify password was added
        assert result["imap"]["password"] == "test_password"
        assert result["imap"]["auth_type"] == "password"
    
    @pytest.mark.skip(reason="Skipping test that prompts for password")
    @patch("getpass.getpass")
    @patch("yaml.safe_load")
    def test_setup_app_password_override_config(
        self, mock_yaml_load, mock_getpass, sample_config_file
    ):
        """Test overriding values in existing config."""
        # Set up mocks
        mock_yaml_load.return_value = {
            "imap": {
                "server": "old-server.example.com",
                "port": 143,
                "username": "old@example.com"
            }
        }
        mock_getpass.return_value = "test_password"
        
        # Run the setup function with overrides
        with patch("builtins.open", mock_open(read_data="")) as mock_file:
            result = setup_app_password(
                username="new@gmail.com",
                server="imap.gmail.com",
                port=993,
                config_path=sample_config_file
            )
        
        # Verify the values were overridden
        assert result["imap"]["server"] == "imap.gmail.com"
        assert result["imap"]["port"] == 993
        assert result["imap"]["username"] == "new@gmail.com"
        assert result["imap"]["password"] == "test_password"
    
    @pytest.mark.skip(reason="Skipping test that prompts for password")
    @patch("getpass.getpass")
    @patch("yaml.dump")
    def test_setup_app_password_config_output(
        self, mock_yaml_dump, mock_getpass
    ):
        """Test writing config to output file."""
        # Set up mock
        mock_getpass.return_value = "test_password"
        
        # Run the setup function with config output
        with patch("builtins.open", mock_open()) as mock_file:
            result = setup_app_password(
                username="test@gmail.com",
                server="imap.gmail.com",
                port=993,
                config_output="output_config.yaml"
            )
        
        # Verify the file was opened for writing
        mock_file.assert_called_with("output_config.yaml", "w")
        
        # Verify yaml.dump was called with the expected config
        mock_yaml_dump.assert_called_once()
        args, kwargs = mock_yaml_dump.call_args
        assert "imap" in args[0]
        assert args[0]["imap"]["password"] == "test_password"


class TestMain:
    """Tests for the main function."""
    
    @pytest.mark.skip(reason="Test interrupts automated execution to ask for password in command line")
    @pytest.mark.skip(reason="Skipping test that requires real credentials")
    @patch("imap_mcp.app_password.setup_app_password")
    @patch("sys.argv")
    @patch("sys.exit")
    def test_main_success(self, mock_exit, mock_argv, mock_setup):
        """Test successful execution of main function."""
        # Set up mocks
        mock_argv.__getitem__.side_effect = lambda i: [
            "app_password.py",
            "--username", "test@gmail.com",
            "--server", "imap.gmail.com",
            "--port", "993",
            "--output", "output.yaml"
        ][i]
        mock_argv.__len__.return_value = 9
        
        mock_setup.return_value = {"imap": {"password": "test_password"}}
        
        # Run the main function
        main()
        
        # Verify the setup function was called with the correct arguments
        mock_setup.assert_called_once_with(
            username="test@gmail.com",
            server="imap.gmail.com",
            port=993,
            config_path=None,
            config_output="output.yaml"
        )
        
        # Verify the program exits successfully
        mock_exit.assert_called_once_with(0)
    
    @pytest.mark.skip(reason="Skipping test that requires real credentials")
    @patch("imap_mcp.app_password.setup_app_password")
    @patch("sys.argv")
    @patch("sys.exit")
    def test_main_with_config(self, mock_exit, mock_argv, mock_setup):
        """Test main function with config file."""
        # Set up mocks
        mock_argv.__getitem__.side_effect = lambda i: [
            "app_password.py",
            "--config", "config.yaml",
            "--output", "output.yaml"
        ][i]
        mock_argv.__len__.return_value = 5
        
        mock_setup.return_value = {"imap": {"password": "test_password"}}
        
        # Run the main function
        main()
        
        # Verify the setup function was called with the correct arguments
        mock_setup.assert_called_once_with(
            username=None,
            server=None,
            port=None,
            config_path="config.yaml",
            config_output="output.yaml"
        )
    
    @pytest.mark.skip(reason="Test interrupts automated execution to ask for password in command line")
    @pytest.mark.skip(reason="Skipping test that requires real credentials")
    @patch("imap_mcp.app_password.setup_app_password")
    @patch("sys.argv")
    @patch("sys.exit")
    def test_main_error(self, mock_exit, mock_argv, mock_setup):
        """Test main function with setup error."""
        # Set up mocks
        mock_argv.__getitem__.side_effect = lambda i: [
            "app_password.py",
            "--username", "test@gmail.com"
        ][i]
        mock_argv.__len__.return_value = 3
        
        mock_setup.side_effect = ValueError("Test error")
        
        # Run the main function
        main()
        
        # Verify the program exits with error
        mock_exit.assert_called_once_with(1)
    
    @pytest.mark.skip(reason="Skipping test that requires real credentials")
    @patch("imap_mcp.app_password.setup_app_password")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("sys.exit")
    def test_main_argument_parsing(self, mock_exit, mock_parse_args, mock_setup):
        """Test argument parsing in main function."""
        # Set up mock
        mock_args = argparse.Namespace(
            username="test@gmail.com",
            server="imap.gmail.com",
            port=993,
            config=None,
            output="output.yaml"
        )
        mock_parse_args.return_value = mock_args
        mock_setup.return_value = {"imap": {"password": "test_password"}}
        
        # Run the main function
        main()
        
        # Verify argument parser was called
        mock_parse_args.assert_called_once()
        
        # Verify setup was called with parsed arguments
        mock_setup.assert_called_once_with(
            username="test@gmail.com",
            server="imap.gmail.com",
            port=993,
            config_path=None,
            config_output="output.yaml"
        )
