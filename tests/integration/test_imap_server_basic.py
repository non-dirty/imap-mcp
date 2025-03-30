"""Basic integration tests for IMAP MCP server.

These tests verify the server can start, connect to Gmail via IMAP, and perform operations.
Following the project's integration testing framework, all tests 
are tagged with @pytest.mark.integration and can be run or skipped with
the --skip-integration flag.
"""

import json
import os
import pytest
import subprocess
import time
import logging
import tempfile
import argparse
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

# Define paths and variables
PROJECT_ROOT = Path.cwd()
SERVER_SCRIPT = PROJECT_ROOT / "scripts" / "run_imap_mcp_server.sh"

def run_server_command(args=None):
    """Run the IMAP MCP server with specified arguments and return the result."""
    if args is None:
        args = ["--dev"]
    
    server_cmd = str(SERVER_SCRIPT)
    command = [server_cmd] + args
    
    # Create temporary file for server output
    with tempfile.NamedTemporaryFile(prefix="imap_server_", suffix=".log", delete=False, mode='w') as temp:
        log_path = temp.name
        logger.info(f"Server output will be logged to: {log_path}")
    
    try:
        # Run the server process and wait for it to complete
        logger.info(f"Running command: {' '.join(command)}")
        with open(log_path, 'w') as log_file:
            result = subprocess.run(
                command,
                stdout=log_file,
                stderr=log_file,
                text=True,
                timeout=30  # Set a reasonable timeout
            )
        
        # Read the log file
        with open(log_path, 'r') as f:
            log_content = f.read()
        
        logger.info(f"Command completed with exit code {result.returncode}")
        logger.info(f"Log output: {log_content}")
        
        return result.returncode, log_content
    
    finally:
        # Clean up the log file
        if os.path.exists(log_path):
            try:
                os.unlink(log_path)
            except Exception as e:
                logger.warning(f"Failed to delete log file {log_path}: {e}")

class TestImapMcpServerBasic:
    """Basic tests for the IMAP MCP server functionality."""
    
    def test_server_help_command(self):
        """Test that the server script responds to --help properly."""
        returncode, log_content = run_server_command(["--help"])
        
        # Check exit code
        assert returncode == 0, f"Server exited with non-zero code: {returncode}"
        
        # Check for help content in the output
        assert "usage:" in log_content, "Help output not found"
        assert "--config CONFIG" in log_content, "Config option not found in help"
        assert "--dev" in log_content, "Dev option not found in help"
    
    def test_server_version_command(self):
        """Test that the server script responds to --version properly."""
        returncode, log_content = run_server_command(["--version"])
        
        # Check exit code
        assert returncode == 0, f"Server exited with non-zero code: {returncode}"
        
        # Check for version information
        assert "version" in log_content.lower(), "Version information not found"
    
    def test_server_connects_to_gmail(self):
        """Verify that the server can connect to Gmail."""
        returncode, log_content = run_server_command(["--dev"])
        
        # Check exit code
        assert returncode == 0, f"Server exited with non-zero code: {returncode}"
        
        # Check for successful connection
        assert "Connected to IMAP server imap.gmail.com" in log_content, "Failed to connect to Gmail"
        
        # Check for successful OAuth2 authentication
        assert "Using OAuth2 authentication" in log_content, "Not using OAuth2 authentication"
        assert "Refreshing Gmail access token" in log_content, "Did not refresh Gmail token"
        
        # Verify clean disconnection
        assert "Disconnected from IMAP server" in log_content, "Did not disconnect cleanly"
    
    def test_server_starts_in_dev_mode(self):
        """Verify that the server starts in development mode."""
        returncode, log_content = run_server_command(["--dev"])
        
        # Check exit code
        assert returncode == 0, f"Server exited with non-zero code: {returncode}"
        
        # Verify development mode
        assert "Starting server in development mode" in log_content, "Server not in development mode"
    
    def test_server_config_loading(self):
        """Verify that the server loads its configuration correctly."""
        returncode, log_content = run_server_command(["--dev"])
        
        # Check exit code
        assert returncode == 0, f"Server exited with non-zero code: {returncode}"
        
        # Verify config loading
        assert "Loaded configuration from config.yaml" in log_content, "Failed to load configuration"

    def find_available_tools(self, log_content):
        """Extract available tools from the server log."""
        tools = []
        for line in log_content.splitlines():
            if "Registered tool:" in line:
                tool_name = line.split("Registered tool:")[1].strip()
                tools.append(tool_name)
        return tools

    @pytest.mark.skip("Skip until debug mode is properly configured")
    def test_list_available_tools(self):
        """Test that the server reports its available tools in debug mode."""
        returncode, log_content = run_server_command(["--dev", "--debug"])
        
        # Check exit code
        assert returncode == 0, f"Server exited with non-zero code: {returncode}"
        
        # Find and extract tools
        tools = self.find_available_tools(log_content)
        
        # Verify that we found some tools
        assert len(tools) > 0, "No tools were registered in the server"
        
        # Log the found tools
        logger.info(f"Found registered tools: {tools}")
        
        # Verify some expected tools are present
        expected_tools = ["search_emails", "get_email", "draft_reply"]
        for tool in expected_tools:
            # Check if any tool name contains the expected tool name
            tool_exists = any(t for t in tools if tool in t)
            assert tool_exists, f"Expected tool '{tool}' was not found in registered tools"

    @pytest.mark.skip("Currently, direct tool execution is not supported via command line")
    def test_search_unread_emails(self):
        """Test the search_emails tool for finding unread emails."""
        # Parameters for the search_emails tool
        search_params = {
            "folder": "INBOX",
            "criteria": {
                "seen": False  # Search for unread (unseen) emails
            },
            "limit": 10
        }
        
        # This test is skipped as the server doesn't support direct tool execution via command line
        # Instead, use the mcp-cli to execute tools as shown in test_mcp_cli_integration.py
        pass

class TestEmailToolsIntegration:
    """Tests for the email-related tools in the IMAP MCP server."""
    
    @pytest.mark.skip("Currently, direct tool execution is not supported via command line")
    def test_list_folders(self):
        """Test the get_folders tool."""
        # This test is skipped as the server doesn't support direct tool execution via command line
        # Instead, use the mcp-cli to execute tools as shown in test_mcp_cli_integration.py
        pass

if __name__ == "__main__":
    # Allow running a specific test directly
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="Run IMAP MCP server tests")
        parser.add_argument("--test", choices=["help", "version", "connect", "dev"], 
                            help="Test to run")
        args = parser.parse_args()
        
        test = TestImapMcpServerBasic()
        if args.test == "help":
            test.test_server_help_command()
        elif args.test == "version":
            test.test_server_version_command()
        elif args.test == "connect":
            test.test_server_connects_to_gmail()
        elif args.test == "dev":
            test.test_server_starts_in_dev_mode()
    else:
        print("Use pytest to run the tests")
