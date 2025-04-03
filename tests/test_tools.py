"""Tests for MCP tools implementation."""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from mcp.server.fastmcp import FastMCP, Context

from imap_mcp.imap_client import ImapClient
from imap_mcp.models import Email, EmailAddress, EmailContent
from imap_mcp.tools import register_tools


# Patch the get_client_from_context function to use our mock client
@pytest.fixture(autouse=True)
def patch_get_client():
    with patch('imap_mcp.tools.get_client_from_context') as mock_get_client:
        yield mock_get_client


class TestTools:
    """Test class for MCP tools."""

    @pytest.fixture
    def mock_email(self):
        """Create a mock email object."""
        email = Email(
            message_id="<test123@example.com>",
            subject="Test Email",
            from_=EmailAddress(name="Sender", address="sender@example.com"),
            to=[EmailAddress(name="Recipient", address="recipient@example.com")],
            cc=[],
            bcc=[],
            date=datetime.now(),
            content=EmailContent(text="Test content", html="<p>Test content</p>"),
            attachments=[],
            flags=["\\Seen"],
            headers={},
            folder="INBOX",
            uid=1
        )
        return email

    @pytest.fixture
    def mock_client(self, mock_email):
        """Create a mock IMAP client."""
        client = MagicMock(spec=ImapClient)
        # Configure default return values
        client.move_email.return_value = True
        client.mark_email.return_value = True
        client.delete_email.return_value = True
        client.list_folders.return_value = ["INBOX", "Sent", "Archive", "Trash"]
        client.search.return_value = [1, 2, 3]
        client.fetch_emails.return_value = {1: mock_email, 2: mock_email, 3: mock_email}
        client.fetch_email.return_value = mock_email
        return client

    @pytest.fixture
    def tools(self, mock_client):
        """Set up tools for testing."""
        # Create a mock MCP server
        mcp = MagicMock(spec=FastMCP)
        
        # Make tool decorator store and return the decorated function
        stored_tools = {}
        
        def mock_tool_decorator():
            def decorator(func):
                stored_tools[func.__name__] = func
                return func
            return decorator
        
        mcp.tool = mock_tool_decorator
        
        # Register tools with our mock
        register_tools(mcp, mock_client)
        
        # Return the tools dictionary
        return stored_tools

    @pytest.fixture
    def mock_context(self, mock_client, patch_get_client):
        """Create a mock context and configure get_client_from_context."""
        context = MagicMock(spec=Context)
        patch_get_client.return_value = mock_client
        return context

    @pytest.mark.asyncio
    async def test_move_email(self, tools, mock_client, mock_context):
        """Test moving an email from one folder to another."""
        # Get the move_email function
        move_email = tools["move_email"]
        
        # Call the move_email function
        result = await move_email("INBOX", 123, "Archive", mock_context)
        
        # Check the client was called correctly
        mock_client.move_email.assert_called_once_with(123, "INBOX", "Archive")
        
        # Check the result
        assert "Email moved from INBOX to Archive" in result

        # Test error handling
        mock_client.move_email.side_effect = Exception("Connection error")
        result = await move_email("INBOX", 123, "Archive", mock_context)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_mark_as_read(self, tools, mock_client, mock_context):
        """Test marking an email as read."""
        # Get the mark_as_read function
        mark_as_read = tools["mark_as_read"]
        
        # Call the function
        result = await mark_as_read("INBOX", 123, mock_context)
        
        # Check the client was called correctly
        mock_client.mark_email.assert_called_once_with(123, "INBOX", "\\Seen", True)
        
        # Check the result
        assert "Email marked as read" in result
        
        # Test failure case
        mock_client.mark_email.return_value = False
        result = await mark_as_read("INBOX", 123, mock_context)
        assert "Failed to mark email as read" in result

    @pytest.mark.asyncio
    async def test_mark_as_unread(self, tools, mock_client, mock_context):
        """Test marking an email as unread."""
        # Get the mark_as_unread function
        mark_as_unread = tools["mark_as_unread"]
        
        # Reset mock for this test
        mock_client.mark_email.reset_mock()
        mock_client.mark_email.return_value = True
        
        # Call the function
        result = await mark_as_unread("INBOX", 123, mock_context)
        
        # Check the client was called correctly
        mock_client.mark_email.assert_called_once_with(123, "INBOX", "\\Seen", False)
        
        # Check the result
        assert "Email marked as unread" in result
        
        # Test error handling
        mock_client.mark_email.side_effect = Exception("Server error")
        result = await mark_as_unread("INBOX", 123, mock_context)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_flag_email(self, tools, mock_client, mock_context):
        """Test flagging and unflagging an email."""
        # Get the flag_email function
        flag_email = tools["flag_email"]
        
        # Reset mock for this test
        mock_client.mark_email.reset_mock()
        mock_client.mark_email.return_value = True
        
        # Test flagging
        result = await flag_email("INBOX", 123, mock_context, True)
        mock_client.mark_email.assert_called_once_with(123, "INBOX", "\\Flagged", True)
        assert "Email flagged" in result
        
        # Reset mock
        mock_client.mark_email.reset_mock()
        
        # Test unflagging
        result = await flag_email("INBOX", 123, mock_context, False)
        mock_client.mark_email.assert_called_once_with(123, "INBOX", "\\Flagged", False)
        assert "Email unflagged" in result

    @pytest.mark.asyncio
    async def test_delete_email(self, tools, mock_client, mock_context):
        """Test deleting an email."""
        # Get the delete_email function
        delete_email = tools["delete_email"]
        
        # Call the function
        result = await delete_email("INBOX", 123, mock_context)
        
        # Check the client was called correctly
        mock_client.delete_email.assert_called_once_with(123, "INBOX")
        
        # Check the result
        assert "Email deleted" in result
        
        # Test failure case
        mock_client.delete_email.return_value = False
        result = await delete_email("INBOX", 123, mock_context)
        assert "Failed to delete" in result
        
        # Test error handling
        mock_client.delete_email.side_effect = Exception("Permission denied")
        result = await delete_email("INBOX", 123, mock_context)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_search_emails(self, tools, mock_client, mock_context, mock_email):
        """Test searching for emails."""
        # Get the search_emails function
        search_emails = tools["search_emails"]
        
        # Test searching with default parameters
        result = await search_emails("test query", mock_context)
        result_data = json.loads(result)
        
        # Assert client methods were called properly
        mock_client.list_folders.assert_called_once()
        assert mock_client.search.call_count > 0 
        
        # Check result structure
        assert isinstance(result_data, list)
        assert len(result_data) > 0
        assert "uid" in result_data[0]
        assert "folder" in result_data[0]
        assert "subject" in result_data[0]
        
        # Reset mocks
        mock_client.list_folders.reset_mock()
        mock_client.search.reset_mock()
        mock_client.fetch_emails.reset_mock()
        
        # Test searching with specific folder
        result = await search_emails("test query", mock_context, folder="INBOX")
        
        # Assert client methods were called properly
        mock_client.list_folders.assert_not_called()
        mock_client.search.assert_called_once()
        
        # Test with different criteria
        criteria_tests = ["from", "to", "subject", "all", "unseen", "seen"]
        for criteria in criteria_tests:
            mock_client.search.reset_mock()
            result = await search_emails("test query", mock_context, criteria=criteria)
            assert mock_client.search.called
        
        # Test with invalid criteria
        result = await search_emails("test query", mock_context, criteria="invalid")
        assert "Invalid search criteria" in result

    @pytest.mark.asyncio
    async def test_process_email(self, tools, mock_client, mock_context):
        """Test processing an email with multiple actions."""
        # Get the process_email function
        process_email = tools["process_email"]
        
        # Test move action
        mock_client.move_email.reset_mock()
        mock_client.move_email.return_value = True
        
        result = await process_email(
            "INBOX", 123, "move", mock_context, target_folder="Archive"
        )
        
        mock_client.move_email.assert_called_once_with(123, "INBOX", "Archive")
        assert "Email moved" in result
        
        # Test move action without target folder
        result = await process_email("INBOX", 123, "move", mock_context)
        assert "Target folder must be specified" in result
        
        # Test read action
        mock_client.mark_email.reset_mock()
        mock_client.mark_email.return_value = True
        
        result = await process_email("INBOX", 123, "read", mock_context)
        
        mock_client.mark_email.assert_called_once_with(123, "INBOX", "\\Seen", True)
        assert "Email marked as read" in result
        
        # Test unread action
        mock_client.mark_email.reset_mock()
        mock_client.mark_email.return_value = True
        
        result = await process_email("INBOX", 123, "unread", mock_context)
        
        mock_client.mark_email.assert_called_once_with(123, "INBOX", "\\Seen", False)
        assert "Email marked as unread" in result
        
        # Test flag action
        mock_client.mark_email.reset_mock()
        mock_client.mark_email.return_value = True
        
        result = await process_email("INBOX", 123, "flag", mock_context)
        
        mock_client.mark_email.assert_called_once_with(123, "INBOX", "\\Flagged", True)
        assert "Email flagged" in result
        
        # Test delete action
        mock_client.delete_email.reset_mock()
        mock_client.delete_email.return_value = True
        
        result = await process_email("INBOX", 123, "delete", mock_context)
        
        mock_client.delete_email.assert_called_once_with(123, "INBOX")
        assert "Email deleted" in result
        
        # Test invalid action
        result = await process_email("INBOX", 123, "invalid_action", mock_context)
        assert "Invalid action" in result
        
        # Test email not found
        mock_client.fetch_email.return_value = None
        result = await process_email("INBOX", 123, "read", mock_context)
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, tools, mock_client, mock_context):
        """Test error handling in tools."""
        # Get tools to test
        move_email = tools["move_email"]
        mark_as_read = tools["mark_as_read"]
        search_emails = tools["search_emails"]
        
        # Test move_email error handling
        mock_client.move_email.side_effect = Exception("Network error")
        result = await move_email("INBOX", 123, "Archive", mock_context)
        assert "Error" in result
        
        # Test mark_as_read error handling
        mock_client.mark_email.side_effect = Exception("Server timeout")
        result = await mark_as_read("INBOX", 123, mock_context)
        assert "Error" in result
        
        # Test search_emails error handling
        mock_client.search.side_effect = Exception("Search failed")
        result = await search_emails("test", mock_context)
        # Search should continue with other folders and return an empty list
        assert "[]" in result or result == "[]"

    @pytest.mark.asyncio
    async def test_tool_parameter_validation(self, tools, mock_client, mock_context):
        """Test parameter validation in tools."""
        # Get tools to test
        search_emails = tools["search_emails"]
        process_email = tools["process_email"]
        
        # Test search_emails with invalid criteria
        result = await search_emails("test", mock_context, criteria="invalid_criteria")
        assert "Invalid search criteria" in result
        
        # Test process_email with missing target folder for move action
        result = await process_email("INBOX", 123, "move", ctx=mock_context)
        assert "Target folder must be specified" in result
        
        # Test process_email with invalid action
        result = await process_email("INBOX", 123, "nonexistent_action", ctx=mock_context)
        assert "Invalid action" in result
