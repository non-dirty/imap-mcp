"""Integration tests for MCP CLI chat mode with IMAP server.

These tests use the mcp-cli in chat mode to interact with the IMAP server
and verify that the new email listing tools work correctly.
"""

import json
import os
import pytest
import subprocess
import time
import logging
import tempfile
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

# Define paths and variables
PROJECT_ROOT = Path.cwd()
MCP_CLI_DIR = PROJECT_ROOT / "mcp-cli"
SERVER_CONFIG_FILE = MCP_CLI_DIR / "server_config.json"

class ChatSession:
    """Helper class to manage an interactive chat session with mcp-cli."""
    
    def __init__(self, server="imap", model="llama3.2", provider="ollama"):
        """Initialize chat session with specified server and model."""
        self.server = server
        self.model = model
        self.provider = provider
        self.process = None
        self.log_path = None
        self.outputs = []
        self.timeout = 60  # Default timeout in seconds
    
    def start(self) -> bool:
        """Start the chat session."""
        # Save current directory and change to mcp-cli directory
        original_dir = os.getcwd()
        os.chdir(MCP_CLI_DIR)
        
        try:
            # Prepare command
            cmd = [
                "python", "-m", "cli.main", "chat",
                "--server", self.server,
                "--provider", self.provider,
                "--model", f"{self.model}:latest"
            ]
            
            # Create log file
            with tempfile.NamedTemporaryFile(prefix="mcp_chat_", suffix=".log", delete=False, mode='w') as temp:
                self.log_path = temp.name
                logger.info(f"Chat session output will be logged to: {self.log_path}")
            
            # Start process
            logger.info(f"Starting chat session: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=dict(os.environ, PYTHONPATH=str(MCP_CLI_DIR))
            )
            
            # Wait for initialization (look for welcome message)
            start_time = time.time()
            initialized = False
            
            while time.time() - start_time < 30:  # 30 seconds timeout for initialization
                if self.process.poll() is not None:
                    # Process exited
                    logger.error(f"Chat process exited with code {self.process.returncode}")
                    stderr = self.process.stderr.read() if self.process.stderr else ""
                    logger.error(f"Error output: {stderr}")
                    return False
                
                # Check if there's any output
                output = self._read_output(timeout=0.5)
                if output and ("Welcome" in output or "How can I help" in output):
                    initialized = True
                    break
                
                time.sleep(0.5)
            
            if not initialized:
                logger.error("Chat session initialization timed out")
                self.stop()
                return False
            
            logger.info("Chat session initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting chat session: {e}")
            if self.process and self.process.poll() is None:
                self.process.terminate()
            return False
            
        finally:
            # Return to original directory
            os.chdir(original_dir)
    
    def send_command(self, command: str, timeout: Optional[int] = None) -> str:
        """Send a command to the chat session and return the response."""
        if not self.process or self.process.poll() is not None:
            logger.error("Chat session is not running")
            return ""
        
        timeout = timeout or self.timeout
        
        try:
            # Send command
            logger.info(f"Sending command: {command}")
            self.process.stdin.write(f"{command}\n")
            self.process.stdin.flush()
            
            # Read response
            response = self._read_output(timeout=timeout)
            logger.info(f"Received response: {response[:500]}...")  # Truncate long responses
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return ""
    
    def _read_output(self, timeout: float) -> str:
        """Read output from the chat session with timeout."""
        if not self.process:
            return ""
        
        output = ""
        start_time = time.time()
        
        # Use non-blocking reads to capture output within timeout
        while time.time() - start_time < timeout:
            # Check if process is still running
            if self.process.poll() is not None:
                break
                
            # Try to read a line from stdout
            line = self._read_nonblocking(self.process.stdout)
            if line:
                output += line
                
            # Also check stderr
            err_line = self._read_nonblocking(self.process.stderr)
            if err_line:
                logger.warning(f"Error output: {err_line}")
                
            # Small delay to avoid high CPU usage
            time.sleep(0.1)
            
            # Check for "end of conversation" markers
            if output and any(marker in output for marker in [
                "Human: ", "USER: ", "You: ", "> ", ">> "
            ]):
                # Found prompt for next input, stop reading
                break
        
        # Log complete output to file
        if self.log_path and output:
            with open(self.log_path, 'a') as log_file:
                log_file.write(f"\n--- COMMAND OUTPUT ---\n{output}\n")
        
        self.outputs.append(output)
        return output
    
    def _read_nonblocking(self, stream) -> str:
        """Non-blocking read from a stream."""
        import select
        
        if not stream:
            return ""
            
        output = ""
        # Use select to check if there's data to read
        r, _, _ = select.select([stream], [], [], 0)
        if stream in r:
            # There's data to read
            line = stream.readline()
            if line:
                output += line
                
        return output
    
    def stop(self) -> None:
        """Stop the chat session."""
        if self.process and self.process.poll() is None:
            logger.info("Stopping chat session")
            
            try:
                # Try to exit gracefully
                self.process.stdin.write("/exit\n")
                self.process.stdin.flush()
                
                # Give it a moment to exit
                time.sleep(1)
                
                # If still running, terminate
                if self.process.poll() is None:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                    
            except Exception as e:
                logger.error(f"Error stopping chat session: {e}")
                # Force kill if needed
                if self.process.poll() is None:
                    self.process.kill()
            
            # Log final output
            if self.log_path:
                try:
                    final_stdout = self.process.stdout.read() if self.process.stdout else ""
                    final_stderr = self.process.stderr.read() if self.process.stderr else ""
                    
                    with open(self.log_path, 'a') as log_file:
                        log_file.write(f"\n--- FINAL OUTPUT ---\nSTDOUT:\n{final_stdout}\nSTDERR:\n{final_stderr}\n")
                        
                except Exception as e:
                    logger.error(f"Error logging final output: {e}")
        
        self.process = None

# Skip these tests in CI since they require interactive sessions
@pytest.mark.skip("Skip in CI - requires interactive mcp-cli chat session")
class TestMcpCliChatMode:
    """Test the mcp-cli in chat mode with the IMAP server."""
    
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
    
    @pytest.fixture(scope="function")
    def chat_session(self):
        """Initialize and tear down a chat session for each test."""
        session = ChatSession(server="imap")
        
        if not session.start():
            pytest.skip("Failed to start chat session")
        
        yield session
        
        session.stop()
    
    def test_server_and_tool_commands(self, chat_session):
        """Test /servers and /tools commands in chat mode."""
        # Check servers command
        servers_output = chat_session.send_command("/servers")
        assert "imap" in servers_output, "IMAP server not found in /servers output"
        
        # Check tools command
        tools_output = chat_session.send_command("/tools --all")
        
        # Check for the email listing tools
        email_tools = ["list_emails", "list_unread_emails", "get_folders"]
        for tool in email_tools:
            assert tool in tools_output, f"Tool '{tool}' not found in /tools output"
    
    def test_natural_language_email_listing(self, chat_session):
        """Test natural language request to list unread emails."""
        # First make sure we're using the IMAP server
        chat_session.send_command("/server imap")
        
        # Use natural language to request unread emails
        response = chat_session.send_command("List my unread emails please")
        
        # Verify response contains email information or appropriate message
        email_indicators = ["subject", "from", "date", "unread", "inbox"]
        assert any(indicator in response.lower() for indicator in email_indicators), \
            "Response doesn't appear to contain email information"
        
        # Check if the response contains the expected structure
        # (either a formatted table, a list, or a message about no unread emails)
        table_patterns = [
            r"(\+[-+]+\+)|(│.*│)",  # ASCII table patterns
            r"(\|.*\|)",  # Simple pipe-based table
            r"^(\s*\d+\.\s+.*subject.*from.*date)",  # Numbered list with headers
            r"(no unread emails|inbox is empty)",  # No emails message
        ]
        
        pattern_found = False
        for pattern in table_patterns:
            if re.search(pattern, response, re.IGNORECASE | re.MULTILINE):
                pattern_found = True
                break
                
        assert pattern_found, "Response doesn't contain expected email list format"
    
    def test_email_pagination(self, chat_session):
        """Test email pagination functionality."""
        # First make sure we're using the IMAP server
        chat_session.send_command("/server imap")
        
        # Request emails with pagination
        first_page = chat_session.send_command("Show me the first 5 emails")
        
        # Request next page
        second_page = chat_session.send_command("Show me the next 5 emails")
        
        # Check that both responses contain email information
        email_indicators = ["subject", "from", "date"]
        assert any(indicator in first_page.lower() for indicator in email_indicators), \
            "First page doesn't appear to contain email information"
        assert any(indicator in second_page.lower() for indicator in email_indicators), \
            "Second page doesn't appear to contain email information"
        
        # Ideally, we'd verify the emails are different between pages,
        # but that would require parsing the output which might be complex
    
    def test_direct_tool_call(self, chat_session):
        """Test calling list_unread_emails tool directly."""
        # First make sure we're using the IMAP server
        chat_session.send_command("/server imap")
        
        # Use tool command to directly execute the tool
        tool_command = "/tool_call list_unread_emails --folder INBOX --limit 10"
        response = chat_session.send_command(tool_command)
        
        # Verify response contains email information or appropriate message
        assert "list_unread_emails" in response, "Tool name not found in response"
        
        # Look for JSON-formatted response in the output
        json_pattern = r'({.*})'
        json_matches = re.findall(json_pattern, response, re.DOTALL)
        
        if json_matches:
            try:
                # Try to parse the JSON to verify format
                json_data = json.loads(json_matches[0])
                
                # Verify expected fields
                assert "emails" in json_data, "Missing 'emails' field in JSON response"
                assert "pagination" in json_data, "Missing 'pagination' field in JSON response"
                
                # Log summary information
                logger.info(f"Found {len(json_data['emails'])} emails in response")
                logger.info(f"Pagination: {json.dumps(json_data['pagination'])}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw JSON: {json_matches[0]}")
