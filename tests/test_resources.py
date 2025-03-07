"""Tests for MCP resources implementation."""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from typing import Dict, List, Any

from mcp.server.fastmcp import Context
from imap_mcp.resources import get_client_from_context, register_resources
from imap_mcp.models import Email, EmailAddress, EmailContent, EmailAttachment


class TestResources:
    """Test suite for MCP resources."""

    def test_get_client_from_context(self):
        """Test getting IMAP client from context."""
        # Create mock context with client
        mock_client = MagicMock()
        mock_context = MagicMock()
        mock_context.request_context.lifespan_context = {"imap_client": mock_client}

        # Test successful client retrieval
        client = get_client_from_context(mock_context)
        assert client == mock_client

        # Test client not available
        mock_context.request_context.lifespan_context = {}
        with pytest.raises(RuntimeError, match="IMAP client not available"):
            get_client_from_context(mock_context)

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server."""
        mock = MagicMock()
        # Store decorated functions for testing
        mock.resources = {}
        
        # Mock the resource decorator to capture the functions
        def resource_decorator(path):
            def wrapper(func):
                mock.resources[path] = func
                return func
            return wrapper
        
        mock.resource = resource_decorator
        return mock

    @pytest.fixture
    def mock_imap_client(self):
        """Create a mock IMAP client."""
        mock = MagicMock()
        
        # Setup some default returns
        mock.list_folders.return_value = ["INBOX", "Sent", "Drafts", "Trash"]
        
        # Default email creation helper
        def create_mock_email(uid, folder="INBOX"):
            return Email(
                message_id=f"<msg{uid}@example.com>",
                subject=f"Test Email {uid}",
                from_=EmailAddress(name="Test Sender", address="sender@example.com"),
                to=[EmailAddress(name="Test Recipient", address="recipient@example.com")],
                date=datetime.now(),
                content=EmailContent(text=f"This is test email {uid}"),
                folder=folder,
                uid=uid
            )
        
        # Setup search to return some UIDs
        mock.search.return_value = [101, 102, 103]
        
        # Setup fetch_emails to return mock emails
        def mock_fetch_emails(uids, folder=None):
            return {uid: create_mock_email(uid, folder) for uid in uids}
        
        mock.fetch_emails.side_effect = mock_fetch_emails
        
        # Setup fetch_email to return a single mock email
        def mock_fetch_email(uid, folder=None):
            return create_mock_email(uid, folder)
        
        mock.fetch_email.side_effect = mock_fetch_email
        
        return mock

    @pytest.fixture
    def mock_context(self, mock_imap_client):
        """Create a mock context with IMAP client."""
        mock = MagicMock()
        mock.request_context.lifespan_context = {"imap_client": mock_imap_client}
        return mock

    def test_register_resources(self, mock_mcp, mock_imap_client):
        """Test registration of MCP resources."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Check if all expected resources are registered
        assert "email://folders" in mock_mcp.resources
        assert "email://{folder}/list" in mock_mcp.resources
        assert "email://search/{query}" in mock_mcp.resources
        assert "email://{folder}/{uid}" in mock_mcp.resources

    @pytest.mark.asyncio
    async def test_get_folders(self, mock_mcp, mock_imap_client, mock_context):
        """Test get_folders resource."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Get the function and call it
        get_folders = mock_mcp.resources["email://folders"]
        result = await get_folders(mock_context)
        
        # Check result
        folders = json.loads(result)
        assert isinstance(folders, list)
        assert "INBOX" in folders
        assert "Sent" in folders
        assert "Drafts" in folders
        assert "Trash" in folders
        
        # Verify client call
        mock_imap_client.list_folders.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_emails(self, mock_mcp, mock_imap_client, mock_context):
        """Test list_emails resource."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Get the function and call it
        list_emails = mock_mcp.resources["email://{folder}/list"]
        result = await list_emails("INBOX", mock_context)
        
        # Check result
        emails = json.loads(result)
        assert isinstance(emails, list)
        assert len(emails) == 3  # Based on our mock setup
        
        # Check email properties
        for email in emails:
            assert "uid" in email
            assert "folder" in email
            assert "from" in email
            assert "to" in email
            assert "subject" in email
            assert "date" in email
            assert "flags" in email
            assert "has_attachments" in email
        
        # Verify client calls
        mock_imap_client.search.assert_called_with("ALL", folder="INBOX")
        mock_imap_client.fetch_emails.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_emails(self, mock_mcp, mock_imap_client, mock_context):
        """Test search_emails resource."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Get the function and call it
        search_emails = mock_mcp.resources["email://search/{query}"]
        
        # Test with predefined query
        result = await search_emails("all", mock_context)
        emails = json.loads(result)
        assert isinstance(emails, list)
        
        # Test with text search
        result = await search_emails("important", mock_context)
        emails = json.loads(result)
        assert isinstance(emails, list)
        
        # Verify client calls - should be called for each folder
        assert mock_imap_client.search.call_count >= 4  # At least once per folder

    @pytest.mark.asyncio
    async def test_get_email(self, mock_mcp, mock_imap_client, mock_context):
        """Test get_email resource."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Get the function and call it
        get_email = mock_mcp.resources["email://{folder}/{uid}"]
        result = await get_email("INBOX", "101", mock_context)
        
        # Check result
        assert "From:" in result
        assert "To:" in result
        assert "Subject:" in result
        assert "Date:" in result
        assert "Test Email 101" in result
        
        # Verify client call
        mock_imap_client.fetch_email.assert_called_with(101, folder="INBOX")

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_mcp, mock_imap_client, mock_context):
        """Test error handling in resources."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Setup client to raise exception
        mock_imap_client.fetch_email.side_effect = Exception("Test error")
        
        # Test get_email error handling
        get_email = mock_mcp.resources["email://{folder}/{uid}"]
        result = await get_email("INBOX", "101", mock_context)
        assert "Error:" in result

        # Setup search to raise exception
        mock_imap_client.search.side_effect = Exception("Search error")
        
        # Test list_emails error handling
        list_emails = mock_mcp.resources["email://{folder}/list"]
        result = await list_emails("INBOX", mock_context)
        assert "Error:" in result
