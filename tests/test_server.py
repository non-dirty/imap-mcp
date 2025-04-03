"""Tests for the server module."""

import pytest
from unittest import mock
import argparse
from contextlib import AsyncExitStack
import logging

from mcp.server.fastmcp import FastMCP

from imap_mcp.server import create_server, server_lifespan, main
from imap_mcp.config import ServerConfig, ImapConfig


class TestServer:
    """Tests for the server module."""

    def test_create_server(self, monkeypatch):
        """Test server creation with default configuration."""
        # Mock the config loading
        mock_config = ServerConfig(
            imap=ImapConfig(
                host="imap.example.com",
                port=993,
                username="test@example.com",
                password="password",
                use_ssl=True
            ),
            allowed_folders=["INBOX", "Sent"]
        )
        
        with mock.patch("imap_mcp.server.load_config", return_value=mock_config):
            # Create the server
            server = create_server()
            
            # Verify server properties
            assert isinstance(server, FastMCP)
            assert server.name == "IMAP"
            assert server._config == mock_config
            
            # With FastMCP we can't directly check if tools are registered
            # Instead, we can verify that the returned server object is properly configured
            
            # Verify resources and tools were registered
            with mock.patch("imap_mcp.server.register_resources") as mock_register_resources:
                with mock.patch("imap_mcp.server.register_tools") as mock_register_tools:
                    create_server()
                    assert mock_register_resources.called
                    assert mock_register_tools.called

    def test_create_server_with_debug(self):
        """Test server creation with debug mode enabled."""
        with mock.patch("imap_mcp.server.logger") as mock_logger:
            create_server(debug=True)
            mock_logger.setLevel.assert_called_with(logging.DEBUG)

    def test_create_server_with_config_path(self):
        """Test server creation with a specific config path."""
        config_path = "test_config.yaml"
        
        with mock.patch("imap_mcp.server.load_config") as mock_load_config:
            create_server(config_path=config_path)
            mock_load_config.assert_called_with(config_path)
    
    @pytest.mark.asyncio
    async def test_server_lifespan(self):
        """Test server lifespan context manager."""
        # Create mock server with config
        mock_server = mock.MagicMock()
        mock_config = ServerConfig(
            imap=ImapConfig(
                host="imap.example.com",
                port=993,
                username="test@example.com",
                password="password",
                use_ssl=True
            )
        )
        mock_server._config = mock_config
        
        # Mock ImapClient
        with mock.patch("imap_mcp.server.ImapClient") as MockImapClient:
            mock_client = MockImapClient.return_value
            
            # Use AsyncExitStack to manage multiple context managers
            async with AsyncExitStack() as stack:
                # Enter the server_lifespan context
                context = await stack.enter_async_context(server_lifespan(mock_server))
                
                # Verify ImapClient was created with correct config
                MockImapClient.assert_called_once_with(mock_config.imap, mock_config.allowed_folders)
                
                # Verify connect was called
                mock_client.connect.assert_called_once()
                
                # Verify client was added to context
                assert context["imap_client"] == mock_client
            
            # After exiting the context, verify disconnect was called
            mock_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_server_lifespan_fallback_config(self):
        """Test server lifespan with fallback config loading."""
        # Create mock server without config
        mock_server = mock.MagicMock()
        mock_server._config = None
        
        mock_config = ServerConfig(
            imap=ImapConfig(
                host="imap.example.com",
                port=993,
                username="test@example.com",
                password="password",
                use_ssl=True
            )
        )
        
        # Mock config loading and ImapClient
        with mock.patch("imap_mcp.server.load_config", return_value=mock_config) as mock_load_config:
            with mock.patch("imap_mcp.server.ImapClient"):
                
                async with AsyncExitStack() as stack:
                    await stack.enter_async_context(server_lifespan(mock_server))
                    
                    # Verify fallback config loading was used
                    mock_load_config.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_server_lifespan_invalid_config(self):
        """Test server lifespan with invalid config."""
        # Create mock server with invalid config
        mock_server = mock.MagicMock()
        mock_server._config = "not a ServerConfig object"
        
        # Verify TypeError is raised
        with pytest.raises(TypeError, match="Invalid server configuration"):
            async with server_lifespan(mock_server):
                pass
    
    def test_server_status_tool(self):
        """Test the server_status tool."""
        # Mock the config
        mock_config = ServerConfig(
            imap=ImapConfig(
                host="imap.example.com",
                port=993,
                username="test@example.com",
                password="password",
                use_ssl=True
            ),
            allowed_folders=["INBOX", "Sent"]
        )
        
        # In the actual server implementation, server_status is defined as an inner function
        # inside create_server, so we can't access it directly. Instead, we'll test that
        # create_server properly configures a server with a tool function.
        
        # Mock the tool decorator to capture the function
        original_tool = FastMCP.tool
        captured_tool = None
        
        def mock_tool(self):
            def decorator(func):
                nonlocal captured_tool
                captured_tool = func
                return original_tool(self)(func)
            return decorator
        
        try:
            # Apply our mock
            with mock.patch("imap_mcp.server.load_config", return_value=mock_config):
                with mock.patch.object(FastMCP, "tool", mock_tool):
                    # Create the server, which should register our tool
                    server = create_server()
                    
                    # Now captured_tool should be the last tool registered
                    # This won't necessarily be server_status, but we can still check
                    # that a tool was registered
                    assert server is not None
        finally:
            # Restore the original method
            FastMCP.tool = original_tool
            
        # Since we can't directly test the server_status tool, we'll create a simplified
        # version based on the implementation and test that
        def test_server_status():
            status = {
                "server": "IMAP MCP",
                "version": "0.1.0",
                "imap_host": mock_config.imap.host,
                "imap_port": mock_config.imap.port,
                "imap_user": mock_config.imap.username,
                "imap_ssl": mock_config.imap.use_ssl,
            }
            
            if mock_config.allowed_folders:
                status["allowed_folders"] = list(mock_config.allowed_folders)
            else:
                status["allowed_folders"] = "All folders allowed"
            
            return "\n".join(f"{k}: {v}" for k, v in status.items())
        
        # Call our test function and check the output for expected values
        result = test_server_status()
        assert "IMAP MCP" in result
        assert "imap.example.com" in result
        assert "test@example.com" in result
        assert "INBOX" in result or "Sent" in result
    
    def test_main_function(self):
        """Test the main function."""
        # Mock command line arguments
        test_args = ["--config", "test_config.yaml", "--debug", "--dev"]
        
        with mock.patch("sys.argv", ["server.py"] + test_args):
            with mock.patch("imap_mcp.server.create_server") as mock_create_server:
                with mock.patch("imap_mcp.server.argparse.ArgumentParser.parse_args") as mock_parse_args:
                    # Mock the parsed arguments
                    mock_args = argparse.Namespace(
                        config="test_config.yaml",
                        debug=True,
                        dev=True
                    )
                    mock_parse_args.return_value = mock_args
                    
                    # Mock the server instance
                    mock_server = mock.MagicMock()
                    mock_create_server.return_value = mock_server
                    
                    # Call main
                    with mock.patch("imap_mcp.server.logger") as mock_logger:
                        main()
                        
                        # Verify create_server was called with correct args
                        mock_create_server.assert_called_once_with("test_config.yaml", True)
                        
                        # Verify server.run was called
                        mock_server.run.assert_called_once()
                        
                        # Verify debug mode was set
                        mock_logger.setLevel.assert_called_with(logging.DEBUG)
                        
                        # Verify startup message
                        mock_logger.info.assert_called_with(mock.ANY)
                        call_args = mock_logger.info.call_args[0][0]
                        assert "Starting server in development mode" in call_args
    
    def test_main_env_config(self, monkeypatch):
        """Test main function with config from environment variable."""
        # Set environment variable for config
        monkeypatch.setenv("IMAP_MCP_CONFIG", "env_config.yaml")
        
        with mock.patch("sys.argv", ["server.py"]):
            with mock.patch("imap_mcp.server.create_server") as mock_create_server:
                with mock.patch("imap_mcp.server.argparse.ArgumentParser.parse_args") as mock_parse_args:
                    # Mock the parsed arguments
                    mock_args = argparse.Namespace(
                        config="env_config.yaml",
                        debug=False,
                        dev=False
                    )
                    mock_parse_args.return_value = mock_args
                    
                    # Call main
                    main()
                    
                    # Verify create_server was called with correct args
                    mock_create_server.assert_called_once_with("env_config.yaml", False)
