"""Tests for unread message retrieval functionality."""

import pytest
from unittest.mock import MagicMock, patch
from imap_mcp.imap_client import ImapClient
from imap_mcp.config import ImapConfig
from imap_mcp.models import Email, EmailAddress, EmailContent


def test_get_unread_messages_defaults():
    """Test get_unread_messages with default parameters."""
    # Create a mocked client that doesn't try to connect
    client = ImapClient(ImapConfig(host="localhost", port=993, username="test"))
    client.connected = True  # Skip connection
    client.client = MagicMock()  # Mock the IMAPClient
    
    # Mock search to return some UIDs
    client.search = MagicMock(return_value=[101, 102, 103])
    
    # Mock fetch_emails to return Email objects
    emails = {
        101: Email(
            message_id="<msg1@test>",
            subject="Test 1",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-03",
            uid=101
        ),
        102: Email(
            message_id="<msg2@test>",
            subject="Test 2",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-02",
            uid=102
        ),
        103: Email(
            message_id="<msg3@test>",
            subject="Test 3",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-01",
            uid=103
        )
    }
    client.fetch_emails = MagicMock(return_value=emails)
    client.get_capabilities = MagicMock(return_value=["IMAP4REV1"])
    
    # Test with default parameters
    result = client.get_unread_messages()
    
    # Verify correct search was performed
    client.search.assert_called_once_with("UNSEEN", folder="INBOX")
    
    # Verify fetch_emails was called with the search results
    client.fetch_emails.assert_called_once_with([101, 102, 103], folder="INBOX")
    
    # Result should have the same emails, sorted by date descending
    assert list(result.keys()) == [101, 102, 103]
    assert len(result) == 3


def test_get_unread_messages_with_pagination():
    """Test get_unread_messages with pagination."""
    # Create a mocked client that doesn't try to connect
    client = ImapClient(ImapConfig(host="localhost", port=993, username="test"))
    client.connected = True  # Skip connection
    client.client = MagicMock()  # Mock the IMAPClient
    
    # Mock search to return some UIDs
    client.search = MagicMock(return_value=[101, 102, 103, 104, 105])
    
    # Mock fetch_emails to return Email objects
    emails = {
        101: Email(
            message_id="<msg1@test>",
            subject="Test 1",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-05",
            uid=101
        ),
        102: Email(
            message_id="<msg2@test>",
            subject="Test 2",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-04",
            uid=102
        ),
        103: Email(
            message_id="<msg3@test>",
            subject="Test 3",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-03",
            uid=103
        ),
        104: Email(
            message_id="<msg4@test>",
            subject="Test 4",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-02",
            uid=104
        ),
        105: Email(
            message_id="<msg5@test>",
            subject="Test 5",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-01",
            uid=105
        )
    }
    client.fetch_emails = MagicMock(return_value=emails)
    client.get_capabilities = MagicMock(return_value=["IMAP4REV1"])
    
    # Test with pagination (limit=2, offset=1)
    result = client.get_unread_messages(limit=2, offset=1)
    
    # Should return 2 emails starting from offset 1
    assert list(result.keys()) == [102, 103]
    assert len(result) == 2


def test_get_unread_messages_with_custom_sorting():
    """Test get_unread_messages with custom sorting."""
    # Create a mocked client that doesn't try to connect
    client = ImapClient(ImapConfig(host="localhost", port=993, username="test"))
    client.connected = True  # Skip connection
    client.client = MagicMock()  # Mock the IMAPClient
    
    # Mock search to return some UIDs
    client.search = MagicMock(return_value=[101, 102, 103])
    
    # Mock fetch_emails to return Email objects with varying subjects
    emails = {
        101: Email(
            message_id="<msg1@test>",
            subject="Zebra",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-03",
            uid=101
        ),
        102: Email(
            message_id="<msg2@test>",
            subject="Apple",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-02",
            uid=102
        ),
        103: Email(
            message_id="<msg3@test>",
            subject="Banana",
            from_=EmailAddress(name="Sender", address="sender@test.com"),
            to=[EmailAddress(name="Recipient", address="recipient@test.com")],
            date="2023-01-01",
            uid=103
        )
    }
    client.fetch_emails = MagicMock(return_value=emails)
    client.get_capabilities = MagicMock(return_value=["IMAP4REV1"])
    
    # Test sorting by subject ascending
    result = client.get_unread_messages(sort_by="subject", sort_order="asc")
    
    # Should be sorted by subject ascending
    assert list(result.values())[0].subject == "Apple"
    assert list(result.values())[1].subject == "Banana"
    assert list(result.values())[2].subject == "Zebra"


def test_get_unread_messages_empty_folder():
    """Test get_unread_messages with empty folder."""
    # Create a mocked client that doesn't try to connect
    client = ImapClient(ImapConfig(host="localhost", port=993, username="test"))
    client.connected = True  # Skip connection
    client.client = MagicMock()  # Mock the IMAPClient
    
    # Mock search to return empty list
    client.search = MagicMock(return_value=[])
    
    # Mock fetch_emails to return empty dict
    client.fetch_emails = MagicMock(return_value={})
    client.get_capabilities = MagicMock(return_value=["IMAP4REV1"])
    
    # Test with empty folder
    result = client.get_unread_messages()
    
    # Should return empty dict
    assert result == {}
    assert len(result) == 0


def test_get_unread_messages_invalid_params():
    """Test get_unread_messages with invalid parameters."""
    # Create a mocked client that doesn't try to connect
    client = ImapClient(ImapConfig(host="localhost", port=993, username="test"))
    client.connected = True  # Skip connection
    client.client = MagicMock()  # Mock the IMAPClient
    client.get_capabilities = MagicMock(return_value=["IMAP4REV1"])
    
    # Test with invalid sort_by parameter
    with pytest.raises(ValueError):
        client.get_unread_messages(sort_by="invalid")
    
    # Test with invalid sort_order parameter
    with pytest.raises(ValueError):
        client.get_unread_messages(sort_order="invalid")
    
    # Test with negative offset
    with pytest.raises(ValueError):
        client.get_unread_messages(offset=-1)
    
    # Test with zero limit (should use None instead)
    with pytest.raises(ValueError):
        client.get_unread_messages(limit=0)


# This test requires a real Gmail connection, so we'll need to get the fixture from the other test file
@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_get_unread_messages(gmail_client):
    """Test getting unread messages from a real Gmail account."""
    # Fetch unread messages
    messages = gmail_client.get_unread_messages(folder="INBOX", limit=5)
    
    # Verify we got a list of messages (might be empty if inbox is empty)
    assert isinstance(messages, dict)
    
    # If we got messages, verify they have the expected structure
    for message in messages.values():
        assert isinstance(message, Email)
        assert message.folder == "INBOX"
        assert "\\Seen" not in message.flags
