"""Tests for the Gmail authentication module."""

import argparse
import logging
import os
import pytest
from unittest.mock import patch, MagicMock

from imap_mcp.gmail_auth import main


@pytest.mark.skip(reason="Test triggers OAuth2 authentication flow in the browser")
def test_main_with_credentials_file():
    """Test main function with credentials file."""
    test_args = [
        "--credentials-file", "test_credentials.json",
        "--port", "8080",
        "--output", "test_config.yaml"
    ]
    
    with patch("sys.argv", ["gmail_auth.py"] + test_args), \
         patch("imap_mcp.browser_auth.perform_oauth_flow") as mock_oauth_flow:
        
        mock_oauth_flow.return_value = {"imap": {"oauth2": {"refresh_token": "test_token"}}}
        
        # Run the main function
        with patch("sys.exit") as mock_exit:
            main()
            
        # Verify the OAuth flow was called correctly
        mock_oauth_flow.assert_called_once()
        _, kwargs = mock_oauth_flow.call_args
        assert kwargs["credentials_file"] == "test_credentials.json"
        assert kwargs["port"] == 8080
        assert kwargs["config_output"] == "test_config.yaml"
        
        # Verify the program exits successfully
        mock_exit.assert_called_once_with(0)


@pytest.mark.skip(reason="Test triggers OAuth2 authentication flow in the browser")
def test_main_with_client_id_secret():
    """Test main function with client ID and secret."""
    test_args = [
        "--client-id", "test_client_id",
        "--client-secret", "test_client_secret"
    ]
    
    with patch("sys.argv", ["gmail_auth.py"] + test_args), \
         patch("imap_mcp.browser_auth.perform_oauth_flow") as mock_oauth_flow, \
         patch("sys.exit") as mock_exit:
        
        mock_oauth_flow.return_value = {"imap": {"oauth2": {"refresh_token": "test_token"}}}
        
        # Run the main function
        main()
            
        # Verify the OAuth flow was called correctly
        mock_oauth_flow.assert_called_once()
        _, kwargs = mock_oauth_flow.call_args
        assert kwargs["client_id"] == "test_client_id"
        assert kwargs["client_secret"] == "test_client_secret"
        assert kwargs["credentials_file"] is None
        
        # Verify the program exits successfully
        mock_exit.assert_called_once_with(0)


@pytest.mark.skip(reason="Test triggers OAuth2 authentication flow in the browser")
def test_main_with_failure():
    """Test main function with OAuth flow failure."""
    test_args = ["--client-id", "test_client_id"]
    
    with patch("sys.argv", ["gmail_auth.py"] + test_args), \
         patch("imap_mcp.browser_auth.perform_oauth_flow") as mock_oauth_flow, \
         patch("sys.exit") as mock_exit:
        
        # Simulate the OAuth flow failing
        mock_oauth_flow.return_value = None
        
        # Run the main function
        main()
            
        # Verify the program exits with an error
        mock_exit.assert_called_once_with(1)


def test_parse_arguments():
    """Test argument parsing."""
    test_args = [
        "--client-id", "test_client_id",
        "--client-secret", "test_client_secret",
        "--credentials-file", "creds.json",
        "--port", "9000",
        "--output", "output.yaml"
    ]
    
    with patch("sys.argv", ["gmail_auth.py"] + test_args), \
         patch("argparse.ArgumentParser.parse_args") as mock_parse_args, \
         patch("imap_mcp.browser_auth.perform_oauth_flow") as mock_oauth_flow, \
         patch("sys.exit"):
        
        mock_args = argparse.Namespace(
            client_id="test_client_id",
            client_secret="test_client_secret",
            credentials_file="creds.json",
            port=9000,
            output="output.yaml"
        )
        mock_parse_args.return_value = mock_args
        mock_oauth_flow.return_value = {"imap": {"oauth2": {"refresh_token": "test_token"}}}
        
        # Run the main function
        main()
        
        # Verify parse_args was called
        mock_parse_args.assert_called_once()
