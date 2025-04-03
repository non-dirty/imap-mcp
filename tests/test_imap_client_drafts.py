<<<<<<< Updated upstream
"""Tests for IMAP client draft message handling functionality."""

import email
import imaplib
import unittest
from datetime import datetime
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from imap_mcp.imap_client import ImapClient


class TestImapClientDrafts:
    """Test class for IMAP draft message handling."""

    @pytest.fixture
    def imap_client(self):
        """Create an ImapClient instance for testing."""
        with patch('imapclient.IMAPClient', autospec=True) as mock_imap:
            # Set up basic mock behaviors
            mock_client = MagicMock()
            mock_imap.return_value = mock_client
            
            # Create a mock config
            mock_config = MagicMock()
            mock_config.host = "imap.example.com"
            mock_config.username = "test@example.com"
            mock_config.password = "password"
            mock_config.requires_oauth2 = False
            
            # Create ImapClient with our mocked config
            client = ImapClient(mock_config)
            
            # Replace the client's client with our mock
            client.client = mock_client
            
            # Ensure the connection is considered successful
            client.connected = True
            
            yield client

    @pytest.fixture
    def sample_mime_message(self):
        """Create a sample MIME message for testing."""
        message = MIMEMultipart()
        message["From"] = "test@example.com"
        message["To"] = "recipient@example.com"
        message["Subject"] = "Test Message"
        
        text_part = MIMEText("This is a test message")
        message.attach(text_part)
        
        return message

    def test_get_drafts_folder_gmail(self, imap_client):
        """Test finding drafts folder for Gmail."""
        # Mock the capabilities to indicate it's a Gmail server
        imap_client.client.capabilities.return_value = [b"X-GM-EXT-1"]
        
        # Mock folder list to include Gmail's standard folders
        imap_client.client.list_folders.return_value = [
            ((b'\\HasNoChildren',), b'/', '[Gmail]/All Mail'),
            ((b'\\HasNoChildren',), b'/', '[Gmail]/Drafts'),
            ((b'\\HasNoChildren',), b'/', '[Gmail]/Sent Mail'),
            ((b'\\HasNoChildren',), b'/', 'INBOX')
        ]
        
        drafts_folder = imap_client._get_drafts_folder()
        
        # Should return Gmail's Drafts folder
        assert drafts_folder == "[Gmail]/Drafts"

    def test_get_drafts_folder_standard(self, imap_client):
        """Test finding drafts folder for standard IMAP servers."""
        # No Gmail capabilities
        imap_client.client.capabilities.return_value = [b"IMAP4rev1", b"UIDPLUS"]
        
        # Mock folder list with standard folders
        imap_client.client.list_folders.return_value = [
            ((b'\\HasNoChildren',), b'/', 'Drafts'),
            ((b'\\HasNoChildren',), b'/', 'Sent'),
            ((b'\\HasNoChildren',), b'/', 'INBOX')
        ]
        
        drafts_folder = imap_client._get_drafts_folder()
        
        # Should return standard Drafts folder
        assert drafts_folder == "Drafts"

    def test_get_drafts_folder_fallback(self, imap_client):
        """Test fallback when no standard drafts folder is found."""
        # No Gmail capabilities
        imap_client.client.capabilities.return_value = [b"IMAP4rev1", b"UIDPLUS"]
        
        # Mock folder list without any obvious drafts folder
        imap_client.client.list_folders.return_value = [
            ((b'\\HasNoChildren',), b'/', 'Sent'),
            ((b'\\HasNoChildren',), b'/', 'INBOX')
        ]
        
        drafts_folder = imap_client._get_drafts_folder()
        
        # Should create and return a Drafts folder
        assert drafts_folder == "Drafts"

    def test_save_draft_mime_success(self, imap_client, sample_mime_message):
        """Test successful saving of a draft message."""
        # Set up mock for append
        # The return value format mimics a successful IMAP APPEND response with UID
        # The UIDPLUS response looks like [b'[APPENDUID 1234567890 123]']
        append_result = b'[APPENDUID 1234567890 123]'
        imap_client.client.append.return_value = append_result
        
        # Mock _get_drafts_folder to return a known value
        with patch.object(imap_client, '_get_drafts_folder', return_value="Drafts"):
            uid = imap_client.save_draft_mime(sample_mime_message)
        
        # Verify append was called with correct parameters
        imap_client.client.append.assert_called_once()
        args, kwargs = imap_client.client.append.call_args
        
        # Check folder
        assert args[0] == "Drafts"
        
        # Check message content - should be bytes
        assert isinstance(args[1], bytes)
        
        # Check flags - should include \Draft
        assert "\\Draft" in args[2]
        
        # Verify returned UID matches our mock
        assert uid == 123

    def test_save_draft_mime_failure(self, imap_client, sample_mime_message):
        """Test handling of failure when saving a draft message."""
        # Set up mock for append to return error or None
        imap_client.client.append.return_value = None
        
        # Mock _get_drafts_folder to return a known value
        with patch.object(imap_client, '_get_drafts_folder', return_value="Drafts"):
            uid = imap_client.save_draft_mime(sample_mime_message)
        
        # Should return None on failure
        assert uid is None

    def test_save_draft_mime_no_uid_in_response(self, imap_client, sample_mime_message):
        """Test handling when server doesn't return a UID in APPEND response."""
        # Return a successful response but without UIDPLUS information
        imap_client.client.append.return_value = b'OK'
        
        # Mock _get_drafts_folder to return a known value
        with patch.object(imap_client, '_get_drafts_folder', return_value="Drafts"):
            uid = imap_client.save_draft_mime(sample_mime_message)
        
        # Should return None when UID can't be determined
        assert uid is None

    def test_save_draft_mime_not_connected(self, imap_client, sample_mime_message):
        """Test handling when client is not connected."""
        # Set client as not connected
        imap_client.connected = False
        
        # Attempt to save draft
        uid = imap_client.save_draft_mime(sample_mime_message)
        
        # Should return None when not connected
        assert uid is None
        
        # The append method should not have been called
        imap_client.client.append.assert_not_called()
=======
"""Tests for IMAP client draft saving functionality."""

import pytest
from unittest.mock import MagicMock, patch
from email.message import EmailMessage

from imap_mcp.config import ImapConfig
from imap_mcp.imap_client import ImapClient


class TestDraftsFunctionality:
    """Tests for drafts folder functionality."""
    
    @pytest.fixture
    def mock_imap_client(self):
        """Create a mock IMAP client with the necessary methods."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            use_ssl=True,
            username="test@example.com",
            password="password"
        )
        
        # Create a mock IMAP client
        client = ImapClient(config)
        client.client = MagicMock()
        client.connected = True
        
        # Mock list_folders method
        client.list_folders = MagicMock()
        
        return client
    
    @pytest.fixture
    def sample_mime_message(self):
        """Create a sample MIME message for testing."""
        message = EmailMessage()
        message["From"] = "sender@example.com"
        message["To"] = "recipient@example.com"
        message["Subject"] = "Draft Email"
        message.set_content("This is a draft email")
        
        return message
    
    def test_get_drafts_folder_standard(self, mock_imap_client):
        """Test getting the drafts folder for standard IMAP server."""
        # Mock list_folders to return standard folders
        mock_imap_client.list_folders.return_value = ["INBOX", "Sent", "Drafts", "Trash"]
        
        # Test drafts folder detection
        drafts_folder = mock_imap_client._get_drafts_folder()
        assert drafts_folder == "Drafts"
        
        # Test with different casing
        mock_imap_client.list_folders.return_value = ["INBOX", "Sent", "drafts", "Trash"]
        drafts_folder = mock_imap_client._get_drafts_folder()
        assert drafts_folder == "drafts"
    
    def test_get_drafts_folder_gmail(self, mock_imap_client):
        """Test getting the drafts folder for Gmail."""
        # Configure as Gmail
        mock_imap_client.config.host = "imap.gmail.com"
        
        # Mock list_folders to return Gmail folders
        mock_imap_client.list_folders.return_value = [
            "INBOX", "[Gmail]/Sent Mail", "[Gmail]/Drafts", "[Gmail]/All Mail", "[Gmail]/Trash"
        ]
        
        # Test drafts folder detection
        drafts_folder = mock_imap_client._get_drafts_folder()
        assert drafts_folder == "[Gmail]/Drafts"
    
    def test_get_drafts_folder_fallback(self, mock_imap_client):
        """Test fallback behavior when no drafts folder is found."""
        # Mock list_folders to return folders without a drafts folder
        mock_imap_client.list_folders.return_value = ["INBOX", "Sent", "Trash"]
        
        # Test drafts folder detection with fallback
        drafts_folder = mock_imap_client._get_drafts_folder()
        assert drafts_folder == "INBOX"
    
    @patch("imap_mcp.imap_client.logger")
    def test_save_draft_mime_success(self, mock_logger, mock_imap_client, sample_mime_message):
        """Test saving a draft MIME message successfully."""
        # Mock behavior
        mock_imap_client._get_drafts_folder = MagicMock(return_value="Drafts")
        mock_imap_client.client.append.return_value = b'[APPENDUID 1234 5678]'
        
        # Call save_draft_mime
        uid = mock_imap_client.save_draft_mime(sample_mime_message)
        
        # Verify behavior
        mock_imap_client.client.append.assert_called_once()
        assert uid == 5678
        mock_logger.debug.assert_called_with("Draft saved with UID: 5678")
    
    @patch("imap_mcp.imap_client.logger")
    def test_save_draft_mime_no_appenduid(self, mock_logger, mock_imap_client, sample_mime_message):
        """Test saving a draft without APPENDUID in response."""
        # Mock behavior
        mock_imap_client._get_drafts_folder = MagicMock(return_value="Drafts")
        mock_imap_client.client.append.return_value = b'OK'
        
        # Call save_draft_mime
        uid = mock_imap_client.save_draft_mime(sample_mime_message)
        
        # Verify behavior
        mock_imap_client.client.append.assert_called_once()
        assert uid is None
        mock_logger.warning.assert_called_with("Could not extract UID from append response: b'OK'")
    
    @patch("imap_mcp.imap_client.logger")
    def test_save_draft_mime_error(self, mock_logger, mock_imap_client, sample_mime_message):
        """Test error handling when saving a draft fails."""
        # Mock behavior
        mock_imap_client._get_drafts_folder = MagicMock(return_value="Drafts")
        mock_imap_client.client.append.side_effect = Exception("IMAP error")
        
        # Call save_draft_mime
        uid = mock_imap_client.save_draft_mime(sample_mime_message)
        
        # Verify behavior
        mock_imap_client.client.append.assert_called_once()
        assert uid is None
        mock_logger.error.assert_called()
>>>>>>> Stashed changes
