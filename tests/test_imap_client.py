"""Tests for the IMAP client."""

import email
import email.utils
import pytest
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch, call

from imap_mcp.config import ImapConfig, ServerConfig
from imap_mcp.imap_client import ImapClient
from imap_mcp.models import Email, EmailAddress

from imapclient.response_types import SearchIds


class TestImapClient:
    """Test the IMAP client."""

    def test_init(self):
        """Test initializing the client."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        assert client.config == config
        assert client.allowed_folders is None
        assert client.client is None
        assert client.folder_cache == {}
        assert client.connected is False
        
        # Test with allowed folders
        allowed_folders = ["INBOX", "Sent"]
        client = ImapClient(config, allowed_folders=allowed_folders)
        assert client.allowed_folders == set(allowed_folders)

    def test_connect_success(self, mock_imap_client):
        """Test successful connection."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            client.connect()
            
            # Verify connection was established with correct parameters
            mock_client_class.assert_called_once_with(
                "imap.example.com", 
                port=993, 
                ssl=True
            )
            
            # Verify login was called with correct credentials
            mock_imap_client.login.assert_called_once_with("test@example.com", "password")
            
            # Verify client is connected
            assert client.connected is True
            assert client.client is mock_imap_client

    def test_connect_failure(self):
        """Test connection failure."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.side_effect = ConnectionError("Connection failed")
            
            # Verify that the correct exception is raised
            with pytest.raises(ConnectionError) as excinfo:
                client.connect()
            
            # Verify error message
            assert "Failed to connect to IMAP server" in str(excinfo.value)
            
            # Verify client is not connected
            assert client.connected is False
            assert client.client is None

    def test_disconnect(self, mock_imap_client):
        """Test disconnection."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        # Simulate connected state
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            client.connect()
            
            # Now disconnect
            client.disconnect()
            
            # Verify logout was called
            mock_imap_client.logout.assert_called_once()
            
            # Verify client is disconnected
            assert client.connected is False
            assert client.client is None

    def test_disconnect_with_exception(self, mock_imap_client):
        """Test disconnection with exception."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        # Simulate connected state
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            client.connect()
            
            # Make logout raise an exception
            mock_imap_client.logout.side_effect = Exception("Logout failed")
            
            # Disconnect should handle the exception
            client.disconnect()
            
            # Verify logout was called
            mock_imap_client.logout.assert_called_once()
            
            # Verify client is still disconnected despite the exception
            assert client.connected is False
            assert client.client is None

    def test_ensure_connected_when_not_connected(self, mock_imap_client):
        """Test ensuring connection when not connected."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Client starts not connected
            assert client.connected is False
            
            # Ensure connected should call connect
            client.ensure_connected()
            
            # Verify connect was called
            mock_client_class.assert_called_once()
            mock_imap_client.login.assert_called_once()
            
            # Verify client is now connected
            assert client.connected is True

    def test_ensure_connected_when_already_connected(self, mock_imap_client):
        """Test ensuring connection when already connected."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Connect first
            client.connect()
            mock_client_class.reset_mock()
            mock_imap_client.login.reset_mock()
            
            # Now ensure_connected should do nothing
            client.ensure_connected()
            
            # Verify connect was not called again
            mock_client_class.assert_not_called()
            mock_imap_client.login.assert_not_called()
            
            # Verify client is still connected
            assert client.connected is True

    def test_list_folders_from_cache(self, mock_imap_client):
        """Test listing folders from cache."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        # Manually populate folder cache
        client.folder_cache = {
            "INBOX": [b"\\HasNoChildren"],
            "Sent": [b"\\HasNoChildren"],
            "Trash": [b"\\HasNoChildren"],
        }
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Connect first
            client.connect()
            mock_imap_client.list_folders.reset_mock()
            
            # List folders should use cache
            folders = client.list_folders(refresh=False)
            
            # Verify list_folders was not called
            mock_imap_client.list_folders.assert_not_called()
            
            # Verify correct folders were returned
            assert set(folders) == {"INBOX", "Sent", "Trash"}

    def test_list_folders_refresh(self, mock_imap_client):
        """Test listing folders with refresh."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        # Manually populate folder cache with old data
        client.folder_cache = {
            "INBOX": [b"\\HasNoChildren"],
            "OldFolder": [b"\\HasNoChildren"],
        }
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock response for list_folders
            mock_imap_client.list_folders.return_value = [
                ((b"\\HasNoChildren",), b"/", "INBOX"),
                ((b"\\HasNoChildren",), b"/", "Sent"),
                ((b"\\HasNoChildren",), b"/", "Drafts"),
            ]
            
            # Connect first
            client.connect()
            
            # Clear the folder cache to force fresh data
            client.folder_cache = {}
            
            # List folders with refresh
            folders = client.list_folders(refresh=True)
            
            # Verify list_folders was called
            mock_imap_client.list_folders.assert_called_once()
            
            # Verify correct folders were returned
            assert set(folders) == {"INBOX", "Sent", "Drafts"}
            
            # Verify cache was updated
            assert set(client.folder_cache.keys()) == {"INBOX", "Sent", "Drafts"}

    def test_list_folders_with_allowed_folders(self, mock_imap_client):
        """Test listing folders with allowed folders filter."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        allowed_folders = ["INBOX", "Sent"]
        client = ImapClient(config, allowed_folders=allowed_folders)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock response for list_folders
            mock_imap_client.list_folders.return_value = [
                ((b"\\HasNoChildren",), b"/", "INBOX"),
                ((b"\\HasNoChildren",), b"/", "Sent"),
                ((b"\\HasNoChildren",), b"/", "Drafts"),
                ((b"\\HasNoChildren",), b"/", "Trash"),
            ]
            
            # Connect first
            client.connect()
            
            # List folders
            folders = client.list_folders()
            
            # Verify list_folders was called
            mock_imap_client.list_folders.assert_called_once()
            
            # Verify only allowed folders were returned
            assert set(folders) == {"INBOX", "Sent"}
            
            # Verify only allowed folders were cached
            assert set(client.folder_cache.keys()) == {"INBOX", "Sent"}

    def test_select_folder(self, mock_imap_client):
        """Test selecting a folder."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock response for select_folder
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            
            # Connect first
            client.connect()
            
            # Select folder
            result = client.select_folder("INBOX")
            
            # Verify select_folder was called with correct folder
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify result is correct
            assert result == {b"EXISTS": 10}

    def test_select_folder_not_allowed(self, mock_imap_client):
        """Test selecting a folder that's not allowed."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        allowed_folders = ["INBOX", "Sent"]
        client = ImapClient(config, allowed_folders=allowed_folders)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Connect first
            client.connect()
            
            # Attempt to select a non-allowed folder
            with pytest.raises(ValueError) as excinfo:
                client.select_folder("Trash")
            
            # Verify error message
            assert "Folder 'Trash' is not allowed" in str(excinfo.value)
            
            # Verify select_folder was not called
            mock_imap_client.select_folder.assert_not_called()

    def test_search_with_string_criteria(self, mock_imap_client):
        """Test searching with string criteria."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            mock_imap_client.search.return_value = [1, 2, 3]
            
            # Connect first
            client.connect()
            
            # Search with predefined string criteria
            result = client.search("unseen", folder="INBOX")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify search was called with correct criteria
            mock_imap_client.search.assert_called_once_with("UNSEEN", charset=None)
            
            # Verify result is correct
            assert result == [1, 2, 3]
            
            # Reset mocks
            mock_imap_client.select_folder.reset_mock()
            mock_imap_client.search.reset_mock()
            
            # Test another predefined criteria
            result = client.search("today", folder="INBOX")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify search was called with correct criteria (SINCE today's date)
            mock_imap_client.search.assert_called_once()
            args = mock_imap_client.search.call_args[0][0]
            assert args[0] == "SINCE"
            # Since we can't predict the exact type, we'll just check it's a date-like object
            assert hasattr(args[1], 'year') and hasattr(args[1], 'month') and hasattr(args[1], 'day')

    def test_search_with_complex_criteria(self, mock_imap_client):
        """Test searching with complex criteria."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            mock_imap_client.search.return_value = [4, 5, 6]
            
            # Connect first
            client.connect()
            
            # Search with complex criteria
            complex_criteria = ["FROM", "test@example.com", "SUBJECT", "test"]
            result = client.search(complex_criteria, folder="Sent")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("Sent")
            
            # Verify search was called with correct criteria
            mock_imap_client.search.assert_called_once_with(complex_criteria, charset=None)
            
            # Verify result is correct
            assert result == [4, 5, 6]

    def test_fetch_email(self, mock_imap_client, test_email_response_data):
        """Test fetching a single email."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            mock_imap_client.fetch.return_value = {12345: test_email_response_data}
            
            # Connect first
            client.connect()
            
            # Fetch email
            email_obj = client.fetch_email(12345, folder="INBOX")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify fetch was called with correct parameters
            mock_imap_client.fetch.assert_called_once_with([12345], ["BODY.PEEK[]", "FLAGS"])
            
            # Verify result is a valid Email object
            assert isinstance(email_obj, Email)
            assert email_obj.uid == 12345
            assert email_obj.folder == "INBOX"
            assert "Test Email" in email_obj.subject
            assert "Test Sender" in email_obj.from_.name
            assert "sender@example.com" in email_obj.from_.address

    def test_fetch_email_not_found(self, mock_imap_client):
        """Test fetching an email that doesn't exist."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            mock_imap_client.fetch.return_value = {}  # Empty result
            
            # Connect first
            client.connect()
            
            # Fetch non-existent email
            email_obj = client.fetch_email(99999, folder="INBOX")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify fetch was called with correct parameters
            mock_imap_client.fetch.assert_called_once_with([99999], ["BODY.PEEK[]", "FLAGS"])
            
            # Verify result is None
            assert email_obj is None

    def test_fetch_emails(self, mock_imap_client, make_test_email_response_data):
        """Test fetching multiple emails."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            
            # Create response data for multiple emails
            response_data = {
                101: make_test_email_response_data(
                    uid=101, 
                    headers={"Subject": "Email 1", "From": "sender@example.com", "To": "recipient@example.com"}
                ),
                102: make_test_email_response_data(
                    uid=102, 
                    headers={"Subject": "Email 2", "From": "sender@example.com", "To": "recipient@example.com"}
                ),
                103: make_test_email_response_data(
                    uid=103, 
                    headers={"Subject": "Email 3", "From": "sender@example.com", "To": "recipient@example.com"}
                ),
            }
            mock_imap_client.fetch.return_value = response_data
            
            # Connect first
            client.connect()
            
            # Fetch emails
            emails = client.fetch_emails([101, 102, 103], folder="INBOX")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify fetch was called with correct parameters
            mock_imap_client.fetch.assert_called_once_with([101, 102, 103], ["BODY.PEEK[]", "FLAGS"])
            
            # Verify result contains all emails
            assert len(emails) == 3
            assert isinstance(emails, dict)
            assert all(isinstance(email, Email) for email in emails.values())
            assert 101 in emails
            assert 102 in emails
            assert 103 in emails
            assert emails[101].subject == "Email 1"
            assert emails[102].subject == "Email 2"
            assert emails[103].subject == "Email 3"

    def test_fetch_emails_with_limit(self, mock_imap_client, make_test_email_response_data):
        """Test fetching emails with a limit."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            
            # Create response data for multiple emails
            response_data = {
                101: make_test_email_response_data(
                    uid=101, 
                    headers={"Subject": "Email 1", "From": "sender@example.com", "To": "recipient@example.com"}
                ),
                102: make_test_email_response_data(
                    uid=102, 
                    headers={"Subject": "Email 2", "From": "sender@example.com", "To": "recipient@example.com"}
                ),
            }
            mock_imap_client.fetch.return_value = response_data
            
            # Connect first
            client.connect()
            
            # Fetch emails with limit
            emails = client.fetch_emails([101, 102, 103, 104, 105], folder="INBOX", limit=2)
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify fetch was called with correct parameters (only first 2 UIDs)
            mock_imap_client.fetch.assert_called_once_with([101, 102], ["BODY.PEEK[]", "FLAGS"])
            
            # Verify result contains only limited emails
            assert len(emails) == 2
            assert 101 in emails
            assert 102 in emails

    def test_mark_email(self, mock_imap_client):
        """Test marking an email with a flag."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            
            # Connect first
            client.connect()
            
            # Mark email as seen
            result = client.mark_email(12345, folder="INBOX", flag=r"\Seen", value=True)
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify add_flags was called with correct parameters
            mock_imap_client.add_flags.assert_called_once_with([12345], r"\Seen")
            
            # Verify result is success
            assert result is True
            
            # Reset mocks
            mock_imap_client.select_folder.reset_mock()
            mock_imap_client.add_flags.reset_mock()
            
            # Mark email as not seen
            result = client.mark_email(12345, folder="INBOX", flag=r"\Seen", value=False)
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify remove_flags was called with correct parameters
            mock_imap_client.remove_flags.assert_called_once_with([12345], r"\Seen")
            
            # Verify result is success
            assert result is True

    def test_mark_email_failure(self, mock_imap_client):
        """Test marking an email with a flag when operation fails."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            mock_imap_client.add_flags.side_effect = Exception("Failed to add flag")
            
            # Connect first
            client.connect()
            
            # Mark email should fail but not raise exception
            result = client.mark_email(12345, folder="INBOX", flag=r"\Seen", value=True)
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify add_flags was called with correct parameters
            mock_imap_client.add_flags.assert_called_once_with([12345], r"\Seen")
            
            # Verify result is failure
            assert result is False

    def test_move_email(self, mock_imap_client):
        """Test moving an email to another folder."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            
            # Connect first
            client.connect()
            
            # Move email
            result = client.move_email(12345, source_folder="INBOX", target_folder="Archive")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify copy was called with correct parameters
            mock_imap_client.copy.assert_called_once_with([12345], "Archive")
            
            # Verify add_flags was called to mark as deleted
            mock_imap_client.add_flags.assert_called_once_with([12345], r"\Deleted")
            
            # Verify expunge was called
            mock_imap_client.expunge.assert_called_once()
            
            # Verify result is success
            assert result is True

    def test_move_email_with_allowed_folders(self, mock_imap_client):
        """Test moving an email with allowed folders restriction."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        allowed_folders = ["INBOX", "Archive"]
        client = ImapClient(config, allowed_folders=allowed_folders)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            
            # Connect first
            client.connect()
            
            # Move email between allowed folders should succeed
            result = client.move_email(12345, source_folder="INBOX", target_folder="Archive")
            
            # Verify operations were called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            mock_imap_client.copy.assert_called_once()
            
            # Verify result is success
            assert result is True
            
            # Reset mocks
            mock_imap_client.select_folder.reset_mock()
            mock_imap_client.copy.reset_mock()
            
            # Move email to non-allowed folder should fail
            with pytest.raises(ValueError) as excinfo:
                client.move_email(12345, source_folder="INBOX", target_folder="Trash")
            
            # Verify error message
            assert "Target folder 'Trash' is not allowed" in str(excinfo.value)
            
            # Verify no operations were called
            mock_imap_client.select_folder.assert_not_called()
            mock_imap_client.copy.assert_not_called()

    def test_move_email_failure(self, mock_imap_client):
        """Test moving an email when operation fails."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            mock_imap_client.copy.side_effect = Exception("Failed to copy email")
            
            # Connect first
            client.connect()
            
            # Move email should fail but not raise exception
            result = client.move_email(12345, source_folder="INBOX", target_folder="Archive")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify copy was called with correct parameters
            mock_imap_client.copy.assert_called_once_with([12345], "Archive")
            
            # Verify result is failure
            assert result is False

    def test_delete_email(self, mock_imap_client):
        """Test deleting an email."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            
            # Connect first
            client.connect()
            
            # Delete email
            result = client.delete_email(12345, folder="INBOX")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify add_flags was called to mark as deleted
            mock_imap_client.add_flags.assert_called_once_with([12345], r"\Deleted")
            
            # Verify expunge was called
            mock_imap_client.expunge.assert_called_once()
            
            # Verify result is success
            assert result is True

    def test_delete_email_failure(self, mock_imap_client):
        """Test deleting an email when operation fails."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True,
        )
        client = ImapClient(config)
        
        with patch("imapclient.IMAPClient") as mock_client_class:
            mock_client_class.return_value = mock_imap_client
            
            # Set up mock responses
            mock_imap_client.select_folder.return_value = {b"EXISTS": 10}
            mock_imap_client.add_flags.side_effect = Exception("Failed to add flag")
            
            # Connect first
            client.connect()
            
            # Delete email should fail but not raise exception
            result = client.delete_email(12345, folder="INBOX")
            
            # Verify select_folder was called
            mock_imap_client.select_folder.assert_called_once_with("INBOX")
            
            # Verify add_flags was called
            mock_imap_client.add_flags.assert_called_once_with([12345], r"\Deleted")
            
            # Verify result is failure
            assert result is False