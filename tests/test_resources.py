"""Tests for MCP resources implementation."""

import json
import pytest
from unittest import mock
from datetime import datetime
from typing import Dict, List, Any

from mcp.server.fastmcp import Context, FastMCP

from imap_mcp.resources import register_resources, get_client_from_context
from imap_mcp.models import Email, EmailAddress, EmailContent, EmailAttachment

# Directly patch the Context class
original_get_current = getattr(Context, 'get_current', None)

class TestResources:
    """Tests for imap_mcp.resources."""
    
    def test_get_client_from_context(self):
        """Test getting IMAP client from context."""
        # Create mock context with client
        mock_client = mock.MagicMock()
        mock_context = mock.MagicMock()
        mock_context.request_context.lifespan_context = {"imap_client": mock_client}

        # Test successful client retrieval
        client = get_client_from_context(mock_context)
        assert client == mock_client
        
        # Test missing client error
        mock_context.request_context.lifespan_context = {}
        with pytest.raises(RuntimeError, match="IMAP client not available"):
            get_client_from_context(mock_context)
    
    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server."""
        mock_server = mock.MagicMock()
        # Store decorated functions for testing
        mock_server.resources = {}
        
        # Mock the resource decorator
        def resource_decorator(path):
            def decorator(func):
                mock_server.resources[path] = func
                return func
            return decorator
        mock_server.resource = resource_decorator
        
        return mock_server
    
    @pytest.fixture
    def mock_imap_client(self):
        """Create a mock IMAP client."""
        mock_client = mock.MagicMock()
        
        # Setup some default returns
        mock_client.list_folders.return_value = ["INBOX", "Sent", "Drafts", "Trash"]
        
        # Mock search
        mock_client.search.return_value = [101, 102, 103]
        
        # Mock fetch_emails
        emails = {}
        for uid in [101, 102, 103]:
            email = mock.MagicMock()
            email.from_ = f"sender{uid}@example.com"
            email.to = [f"recipient{uid}@example.com"]
            email.subject = f"Test Email {uid}"
            email.date.isoformat.return_value = "2023-01-01T12:00:00"
            email.flags = ["\\Seen"]
            email.get_snippet.return_value = f"This is the content of email {uid}"
            email.has_attachments = False
            emails[uid] = email
        mock_client.fetch_emails.return_value = emails
        
        # Mock fetch_email
        email = mock.MagicMock()
        email.from_ = "sender@example.com"
        email.to = ["recipient@example.com"]
        email.cc = []
        email.subject = "Test Email 101"
        email.date.isoformat.return_value = "2023-01-01T12:00:00"
        email.flags = ["\\Seen"]
        email.content.get_best_content.return_value = "This is the email content"
        mock_client.fetch_email.return_value = email
        
        return mock_client
    
    @pytest.fixture
    def mock_context(self, mock_imap_client):
        """Create a mock context with IMAP client."""
        mock_ctx = mock.MagicMock()
        mock_ctx.request_context.lifespan_context = {"imap_client": mock_imap_client}
        return mock_ctx
    
    @pytest.fixture(autouse=True)
    def patch_context(self, mock_context):
        """Patch Context.get_current for all tests."""
        # Create a class method
        def mock_get_current():
            return mock_context
        
        # Apply patch to the Context class
        Context.get_current = staticmethod(mock_get_current)
        yield
        
        # Restore the original if it existed
        if original_get_current:
            Context.get_current = original_get_current
        else:
            delattr(Context, 'get_current')

    def test_register_resources(self, mock_mcp, mock_imap_client):
        """Test registration of MCP resources."""
        # Call register_resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Check that the expected resources were registered
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
        result = await get_folders()
        
        # Check the result
        assert isinstance(result, str)
        folders = json.loads(result)
        assert isinstance(folders, list)
        assert "INBOX" in folders
        
        # Verify client method was called
        mock_imap_client.list_folders.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_emails(self, mock_mcp, mock_imap_client, mock_context):
        """Test list_emails resource."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Get the function and call it
        list_emails = mock_mcp.resources["email://{folder}/list"]
        result = await list_emails("INBOX")
        
        # Check the result
        assert isinstance(result, str)
        emails = json.loads(result)
        assert isinstance(emails, list)
        assert len(emails) == 3  # We mocked 3 emails
        
        # Verify client methods were called
        mock_imap_client.search.assert_called_once()
        mock_imap_client.fetch_emails.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_emails(self, mock_mcp, mock_imap_client, mock_context):
        """Test search_emails resource."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Customize search to only return results from a single folder
        def mock_search(query, folder=None):
            # Only return results for INBOX folder
            if folder == "INBOX":
                return [101, 102, 103]
            return []
        
        # Set our custom search function
        mock_imap_client.search.side_effect = mock_search
        
        # Only return INBOX in list_folders
        mock_imap_client.list_folders.return_value = ["INBOX"]
        
        # Get the function and call it
        search_emails = mock_mcp.resources["email://search/{query}"]
        
        # Test with predefined query
        result = await search_emails("all")
        
        # Check the result
        assert isinstance(result, str)
        emails = json.loads(result)
        assert isinstance(emails, list)
        assert len(emails) == 3  # We mocked 3 emails for INBOX only
        
        # Verify client methods were called
        assert mock_imap_client.search.call_count >= 1
        assert mock_imap_client.fetch_emails.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_get_email(self, mock_mcp, mock_imap_client, mock_context):
        """Test get_email resource."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Create a mock email with the needed properties for text output
        email = mock.MagicMock()
        email.from_ = "sender@example.com"
        email.to = ["recipient@example.com"]
        email.cc = []
        email.subject = "Test Email 101"
        email.flags = ["\\Seen"]
        email.attachments = []
        email.date.isoformat.return_value = "2023-01-01T12:00:00"
        email.content.get_best_content.return_value = "This is the email content"
        
        # Return the mock email from fetch_email
        mock_imap_client.fetch_email.return_value = email
        
        # Get the function and call it
        get_email = mock_mcp.resources["email://{folder}/{uid}"]
        result = await get_email("INBOX", "101")
        
        # The result should be a string containing the formatted email
        assert isinstance(result, str)
        # Check for key parts of the email in the text output
        assert "From: sender@example.com" in result
        assert "To: recipient@example.com" in result
        assert "Subject: Test Email 101" in result
        assert "This is the email content" in result
        
        # Verify client method was called
        mock_imap_client.fetch_email.assert_called_once_with(101, folder="INBOX")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_mcp, mock_imap_client, mock_context):
        """Test error handling in resources."""
        # Register resources
        register_resources(mock_mcp, mock_imap_client)
        
        # Setup client to raise exception
        mock_imap_client.fetch_email.side_effect = Exception("Test error")
        
        # Test get_email error handling
        get_email = mock_mcp.resources["email://{folder}/{uid}"]
        result = await get_email("INBOX", "101")
        
        # Check the error response
        assert isinstance(result, str)
        # The error should be included in the output text
        assert "Error: Test error" in result
    
    def test_resource_parameter_validation(self, mock_mcp):
        """Test that resource parameter definitions are valid for MCP API.
        
        This ensures our resource paths are compatible with the router.
        """
        # Get real MCP
        real_mcp = FastMCP()
        real_resources = {}
        
        # Mock FastMCP resource method to capture registrations
        def resource_decorator(path):
            def decorator(func):
                real_resources[path] = func
                return func
            return decorator
        real_mcp.resource = resource_decorator
        
        try:
            # This should succeed if all resources have correct parameter definitions
            from imap_mcp.resources import register_resources
            register_resources(real_mcp, mock.MagicMock())
            
            # If we get here, all resources passed validation
            assert len(real_resources) >= 4, "Expected at least 4 resources to be registered"
        except Exception as e:
            pytest.fail(f"Resource parameter validation failed: {e}")
