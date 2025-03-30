"""Integration tests for direct tool usage with the IMAP MCP client.

These tests directly import and use the IMAP tool functions to test their functionality
with a real Gmail account. This approach bypasses the server API and CLI interfaces
to focus on testing the core email search functionality.
"""

import asyncio
import json
import logging
import os
import pytest
from typing import Dict, List, Optional, Any, Callable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

# Import the IMAP client and tools
from imap_mcp.imap_client import ImapClient
from imap_mcp.config import Config
from imap_mcp.models import Context
from imap_mcp.tools import search_emails as search_emails_tool


class TestDirectToolsIntegration:
    """Test direct usage of IMAP MCP tools without going through the server or CLI."""
    
    @pytest.fixture(scope="class")
    async def imap_client(self):
        """Create and yield an IMAP client connected to Gmail."""
        # Load config from the default location
        config = Config.load_config()
        
        # Create IMAP client
        client = ImapClient(config.email)
        
        # Connect to the server
        client.connect()
        
        try:
            yield client
        finally:
            # Disconnect when done
            client.disconnect()

    @pytest.fixture(scope="class")
    async def context(self, imap_client):
        """Create a context object with the IMAP client for use with tools."""
        # Create a minimal context object compatible with the tools
        ctx = Context(client=imap_client)
        return ctx
    
    @pytest.mark.asyncio
    async def test_list_folders(self, imap_client):
        """Test listing folders directly from the IMAP client."""
        # Get list of folders
        folders = imap_client.list_folders()
        
        # Check that we got some folders
        assert len(folders) > 0, "No folders returned from IMAP server"
        
        # Check that INBOX is present
        assert "INBOX" in folders, "INBOX not found in folder list"
        
        # Log the folders for reference
        logger.info(f"Found {len(folders)} folders: {folders}")
    
    @pytest.mark.asyncio
    async def test_search_unread_emails(self, imap_client, context):
        """Test searching for unread emails using the search_emails tool directly."""
        # Search for unread emails in INBOX
        results = await search_emails_tool(
            query="",
            ctx=context,
            folder="INBOX",
            criteria="unseen",
            limit=10
        )
        
        # Parse the JSON result
        try:
            results_dict = json.loads(results)
            logger.info(f"Search results: {json.dumps(results_dict, indent=2)}")
            
            # Verify the result structure
            assert isinstance(results_dict, list), "Expected list of results"
            
            # Log the number of unread emails found
            logger.info(f"Found {len(results_dict)} unread emails in INBOX")
            
            # Check the fields in each result if there are any results
            if results_dict:
                first_email = results_dict[0]
                expected_fields = ["uid", "folder", "from", "subject", "date"]
                for field in expected_fields:
                    assert field in first_email, f"Field '{field}' missing from email result"
                
                # Verify that emails are marked as unread
                assert "\\Seen" not in first_email.get("flags", []), "Email should be unread (no \\Seen flag)"
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse search results: {e}")
            logger.error(f"Raw results: {results}")
            pytest.fail(f"Invalid JSON returned from search_emails tool: {e}")
    
    @pytest.mark.asyncio
    async def test_search_with_different_criteria(self, imap_client, context):
        """Test searching with different criteria using the search_emails tool."""
        # Test cases with different search criteria
        test_cases = [
            ("", "all", "all emails"),
            ("", "today", "emails from today"),
            ("test", "subject", "emails with 'test' in subject"),
        ]
        
        for query, criteria, description in test_cases:
            logger.info(f"Testing search for {description}")
            
            results = await search_emails_tool(
                query=query,
                ctx=context,
                folder="INBOX",
                criteria=criteria,
                limit=5
            )
            
            # Parse and validate results
            try:
                results_dict = json.loads(results)
                logger.info(f"Found {len(results_dict)} {description}")
                
                # Basic validation
                assert isinstance(results_dict, list), f"Expected list of results for {description}"
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse search results for {description}: {e}")
                logger.error(f"Raw results: {results}")
                pytest.fail(f"Invalid JSON returned from search_emails tool for {description}: {e}")

if __name__ == "__main__":
    # Enable running the tests directly
    pytest.main(["-xvs", __file__])
