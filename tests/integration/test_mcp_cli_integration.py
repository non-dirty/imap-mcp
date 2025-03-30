"""Integration tests for MCP CLI with IMAP server integration.

This test verifies the basics of server configuration and proper CLI interaction with the IMAP MCP server.
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
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

# Define paths and variables
PROJECT_ROOT = Path.cwd()
MCP_CLI_DIR = PROJECT_ROOT / "mcp-cli"
SERVER_CONFIG_FILE = MCP_CLI_DIR / "server_config.json"

def run_mcp_cli_command(cmd_args, input_text=None, timeout=60):
    """Run an mcp-cli command with the specified arguments and return the result."""
    # First, ensure we're in the mcp-cli directory and dependencies are installed
    os.chdir(MCP_CLI_DIR)
    
    # The command needs to be run from the mcp-cli directory with proper Python path
    base_cmd = ["python", "-m", "cli.main"]
    full_cmd = base_cmd + cmd_args
    
    # Create temporary file for command output
    with tempfile.NamedTemporaryFile(prefix="mcp_cli_", suffix=".log", delete=False, mode='w') as temp:
        log_path = temp.name
        logger.info(f"Command output will be logged to: {log_path}")
    
    try:
        # Run the command and wait for it to complete
        logger.info(f"Running command from {os.getcwd()}: {' '.join(full_cmd)}")
        process = subprocess.run(
            full_cmd,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env=dict(os.environ, PYTHONPATH=str(MCP_CLI_DIR))
        )
        
        # Log the results
        with open(log_path, 'w') as log_file:
            log_file.write(f"STDOUT:\n{process.stdout}\n\nSTDERR:\n{process.stderr}")
        
        logger.info(f"Command completed with exit code {process.returncode}")
        
        # Return both process result and log path for reference
        return process, log_path
    
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout} seconds")
        return None, log_path
    
    except Exception as e:
        logger.error(f"Error running command: {e}")
        with open(log_path, 'w') as log_file:
            log_file.write(f"ERROR: {str(e)}")
        return None, log_path
    
    finally:
        # Return to the project root directory
        os.chdir(PROJECT_ROOT)

class TestImapMcpServerConfig:
    """Test the IMAP MCP server configuration and basic CLI functionality."""
    
    def test_server_config_exists(self):
        """Test that server_config.json exists and contains imap server entry."""
        assert SERVER_CONFIG_FILE.exists(), f"server_config.json not found at {SERVER_CONFIG_FILE}"
        
        with open(SERVER_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Verify expected section and keys
        assert "mcpServers" in config, "mcpServers section missing from config"
        assert "imap" in config["mcpServers"], "imap server not defined in config"
        
        # Verify command is set properly
        imap_config = config["mcpServers"]["imap"]
        assert "command" in imap_config, "imap server missing command"
        assert "args" in imap_config, "imap server missing args"
        
        # Check that command points to a file that exists
        command_path = Path(imap_config["command"])
        assert command_path.exists(), f"Command does not exist: {command_path}"
    
    def test_wrapper_script_exists(self):
        """Test that the IMAP MCP server wrapper script exists and is executable."""
        with open(SERVER_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Get the command from the config
        command_path = Path(config["mcpServers"]["imap"]["command"])
        assert command_path.exists(), f"Server command not found: {command_path}"
        
        # Verify the script has expected content
        with open(command_path, 'r') as f:
            script_content = f.read()
        
        # Check for key indicators this is the correct script
        expected_indicators = ["Starting IMAP MCP Server", "PYTHONPATH"]
        for indicator in expected_indicators:
            assert indicator in script_content, f"Expected content '{indicator}' not found in script"
    
    def test_wrapper_script_help(self):
        """Test that the wrapper script responds to --help."""
        with open(SERVER_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        script_path = config["mcpServers"]["imap"]["command"]
        
        # Run the script with --help
        result = subprocess.run(
            [script_path, "--help"],
            capture_output=True,
            text=True
        )
        
        # Verify it exits successfully and contains expected help output
        assert result.returncode == 0, f"Script --help failed with code {result.returncode}"
        assert "usage:" in result.stdout or "usage:" in result.stderr, "Help output not found"

@pytest.mark.skip("Skipping direct MCP CLI tests until they can be properly configured for CI")
class TestMcpCliImapIntegration:
    """Test the MCP CLI's ability to interact with the IMAP server."""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_mcp_cli(self):
        """Ensure MCP CLI dependencies are installed."""
        # Save current directory
        original_dir = os.getcwd()
        
        try:
            # Change to mcp-cli directory
            os.chdir(MCP_CLI_DIR)
            
            # Run uv sync --reinstall to ensure dependencies are installed
            logger.info("Installing/updating MCP CLI dependencies...")
            subprocess.run(
                ["uv", "sync", "--reinstall"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            yield
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install MCP CLI dependencies: {e}")
            pytest.skip("Failed to install MCP CLI dependencies")
        
        finally:
            # Return to original directory
            os.chdir(original_dir)
    
    def test_mcp_cli_list_servers(self):
        """Test that MCP CLI can list servers and includes the IMAP server."""
        process, log_path = run_mcp_cli_command(["servers"])
        
        assert process is not None, "Command failed to execute"
        assert process.returncode == 0, f"Command failed with code {process.returncode}"
        
        # Check that the output includes our IMAP server
        assert "imap" in process.stdout, "IMAP server not listed in servers command output"
    
    def test_tool_list_with_imap_server(self):
        """Test getting tool list from the IMAP server through mcp-cli."""
        # Non-interactive command to list available tools for the IMAP server
        process, log_path = run_mcp_cli_command(["tools", "--server", "imap"])
        
        assert process is not None, "Command failed to execute"  
        assert process.returncode == 0, f"Command failed with code {process.returncode}"
        
        # Check expected tools are listed
        expected_tools = ["search_emails", "get_email"]
        stdout = process.stdout.lower()
        
        for tool in expected_tools:
            assert tool.lower() in stdout, f"Expected tool '{tool}' not found in tools list"
        
        # Verify tool list has the right format
        assert "[" in process.stdout and "]" in process.stdout, "Tool list not in expected format"
        
        # Try to parse the tool list as JSON if it's valid JSON format
        try:
            # Extract JSON part from the output (may be mixed with other text)
            json_part = process.stdout[process.stdout.find("["):process.stdout.rfind("]")+1]
            tools = json.loads(json_part)
            assert isinstance(tools, list), "Tools output not a valid list"
            assert len(tools) > 0, "No tools found in output"
            
            # Log the tools for reference
            logger.info(f"Found {len(tools)} tools from IMAP server")
            
        except (json.JSONDecodeError, ValueError) as e:
            # If not valid JSON, check that tool names are present in text format
            logger.warning(f"Could not parse tools as JSON: {e}")
            for tool in expected_tools:
                assert tool.lower() in stdout, f"Expected tool '{tool}' not found in tools list"

@pytest.mark.skip("Skipping direct tool calls until they can be properly configured for CI")
def test_direct_email_search_command():
    """Test searching for unread emails using a direct CLI command."""
    # Use the CLI in command mode to execute a tool directly
    search_args = [
        "tools",
        "call",
        "--server", "imap",
        "--tool", "search_emails", 
        "--args", json.dumps({
            "query": "",
            "folder": "INBOX",
            "criteria": "unseen",
            "limit": 5
        })
    ]
    
    process, log_path = run_mcp_cli_command(search_args, timeout=30)
    
    # Check command executed successfully
    assert process is not None, "Command failed to execute"
    
    # We can't strictly assert return code as it depends on whether emails exist
    # instead check that the output looks reasonable
    stdout = process.stdout
    
    # It should either contain email data or an appropriate message
    assert "uid" in stdout.lower() or "subject" in stdout.lower() or "no emails found" in stdout.lower() or "results" in stdout.lower(), \
        "Email search results do not contain expected output"
    
    # Log the search results
    logger.info(f"Email search completed with output: {stdout[:500]}...")  # Truncate for logs
    
    # Check for JSON-formatted response
    if "{" in stdout and "}" in stdout:
        try:
            # Try to extract and parse JSON from the output
            json_part = stdout[stdout.find("{"):stdout.rfind("}")+1]
            result = json.loads(json_part)
            
            # Verify result structure if it's a valid result
            if isinstance(result, dict):
                logger.info(f"Successfully parsed search results as JSON")
                # Success!
        except json.JSONDecodeError:
            logger.warning("Could not parse search results as JSON")
