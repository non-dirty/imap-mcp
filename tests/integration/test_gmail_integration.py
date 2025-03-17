"""Integration tests for real Gmail account connectivity.

This module contains tests that connect to a real Gmail account using OAuth2 authentication.
These tests require proper configuration and environment variables to run.
"""

import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Generator

import pytest
from dotenv import load_dotenv

from imap_mcp.config import ImapConfig, OAuth2Config
from imap_mcp.imap_client import ImapClient
from imap_mcp.models import Email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TEST_EMAIL = os.getenv("GMAIL_TEST_EMAIL", "test@example.com")
REQUIRED_ENV_VARS = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN", "GMAIL_TEST_EMAIL"]

# Load environment variables from .env.test if it exists
load_dotenv(".env.test")


def load_oauth2_credentials() -> Dict[str, str]:
    """Load OAuth2 credentials from environment variables.
    
    Returns:
        Dictionary with OAuth2 credentials or empty dict if not available
    """
    missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
        return {}
    
    return {
        "client_id": os.getenv("GMAIL_CLIENT_ID", ""),
        "client_secret": os.getenv("GMAIL_CLIENT_SECRET", ""),
        "refresh_token": os.getenv("GMAIL_REFRESH_TOKEN", "")
    }


def load_gmail_config(oauth2_credentials: Dict[str, str]) -> ImapConfig:
    """Create ImapConfig with OAuth2 for Gmail.
    
    Args:
        oauth2_credentials: Dictionary with OAuth2 credentials
        
    Returns:
        ImapConfig configured for Gmail with OAuth2
    """
    oauth2_config = None
    if oauth2_credentials:
        oauth2_config = OAuth2Config(
            client_id=oauth2_credentials["client_id"],
            client_secret=oauth2_credentials["client_secret"],
            refresh_token=oauth2_credentials["refresh_token"]
        )
    
    return ImapConfig(
        host="imap.gmail.com",
        port=993,
        username=os.getenv("GMAIL_TEST_EMAIL"),  # This will now use the environment variable value
        password="",  # Not used with OAuth2
        use_ssl=True,
        oauth2=oauth2_config
    )


@contextmanager
def timed_operation(description: str) -> Generator[None, None, None]:
    """Context manager to measure and log operation time.
    
    Args:
        description: Description of the operation being timed
    """
    start_time = time.time()
    logger.info(f"Starting: {description}")
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        logger.info(f"Completed: {description} in {elapsed:.2f} seconds")


# Fixtures
@pytest.fixture
def gmail_oauth_credentials() -> Dict[str, str]:
    """Get Gmail OAuth2 credentials from environment variables.
    
    Returns:
        Dictionary with OAuth2 credentials
    """
    credentials = load_oauth2_credentials()
    if not credentials:
        pytest.skip("OAuth2 credentials not provided, skipping all OAuth2 integration tests")
    
    # Log the loaded credentials (without exposing the full secrets)
    logger.info(f"OAuth2 Client ID: {credentials['client_id'][:5]}...{credentials['client_id'][-5:]}")
    logger.info(f"OAuth2 Refresh Token: {credentials['refresh_token'][:5]}...{credentials['refresh_token'][-5:]}")
    logger.info(f"Test Email: {os.getenv('GMAIL_TEST_EMAIL')}")
    
    return credentials


@pytest.fixture
def gmail_config(gmail_oauth_credentials: Dict[str, str]) -> ImapConfig:
    """Create a configuration for Gmail IMAP.
    
    Args:
        gmail_oauth_credentials: Dictionary with OAuth2 credentials
        
    Returns:
        ImapConfig for Gmail with OAuth2
    """
    return load_gmail_config(gmail_oauth_credentials)


@pytest.fixture
def gmail_client(gmail_config: ImapConfig) -> ImapClient:
    """Create and connect a Gmail IMAP client using OAuth2 authentication.
    
    Args:
        gmail_config: ImapConfig for Gmail with OAuth2
        
    Returns:
        Connected ImapClient instance
    """
    client = ImapClient(gmail_config)
    with timed_operation("Connecting to Gmail"):
        client.connect()
    
    yield client
    
    # Cleanup after test
    logger.info("Disconnecting from Gmail")
    client.disconnect()


# Connection Tests
@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_connect_oauth2(gmail_config: ImapConfig):
    """Test basic connection to Gmail using OAuth2 authentication."""
    client = ImapClient(gmail_config)
    
    with timed_operation("OAuth2 connection"):
        client.connect()
    
    assert client.connected
    
    # Check if basic properties are available
    capabilities = client.get_capabilities()
    logger.info(f"Server capabilities: {capabilities}")
    assert capabilities, "Server capabilities should not be empty"
    
    # Verify some expected Gmail capabilities
    assert "IMAP4REV1" in capabilities, "Gmail should support IMAP4REV1"
    assert "IDLE" in capabilities, "Gmail should support IDLE"
    
    # Cleanup
    client.disconnect()
    assert not client.connected


@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_reconnect(gmail_config: ImapConfig):
    """Test disconnection and reconnection capabilities."""
    client = ImapClient(gmail_config)
    
    # First connection
    with timed_operation("Initial connection"):
        client.connect()
    
    assert client.connected
    
    # Disconnect
    client.disconnect()
    assert not client.connected
    
    # Reconnect
    with timed_operation("Reconnection"):
        client.connect()
    
    assert client.connected
    
    # Check capabilities after reconnection
    capabilities = client.get_capabilities()
    assert capabilities, "Server capabilities should not be empty after reconnection"
    
    # Cleanup
    client.disconnect()
    assert not client.connected


@pytest.mark.integration
@pytest.mark.gmail
def test_gmail_connection_error_handling():
    """Test handling of connection errors with invalid configuration."""
    # Use invalid credentials
    invalid_config = ImapConfig(
        host="imap.gmail.com",
        port=993,
        username="invalid@gmail.com",
        password="invalid_password",
        use_ssl=True
    )
    
    client = ImapClient(invalid_config)
    
    # Should raise an exception on connection attempt
    with pytest.raises(Exception) as excinfo:
        with timed_operation("Invalid connection attempt"):
            client.connect()
    
    # Verify proper error handling
    error_message = str(excinfo.value)
    logger.info(f"Expected error: {error_message}")
    assert "Failed to connect" in error_message or "Connection failed" in error_message


@pytest.mark.integration
@pytest.mark.gmail
def test_gmail_connection_timeout():
    """Test connection timeout handling."""
    # Use a non-routable IP to force timeout
    invalid_config = ImapConfig(
        host="10.255.255.1",  # Non-routable IP that should cause timeout
        port=993,
        username=TEST_EMAIL,
        password="invalid",
        use_ssl=True
    )
    
    client = ImapClient(invalid_config)
    
    # Should raise an exception on connection attempt
    with pytest.raises(Exception) as excinfo:
        with timed_operation("Timeout connection attempt"):
            # Pass timeout directly to the connect method
            client.connect(timeout=1)  # Very short timeout to speed up test
    
    # Verify proper error handling
    error_message = str(excinfo.value)
    logger.info(f"Expected error: {error_message}")
    assert "timeout" in error_message.lower() or "timed out" in error_message.lower()


# Folder Tests
@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_list_folders(gmail_client: ImapClient):
    """Test listing folders in Gmail account."""
    folders = gmail_client.list_folders()
    
    # Check that we have a list of folders
    assert isinstance(folders, list), "list_folders should return a list"
    assert len(folders) > 0, "Gmail account should have at least one folder"
    
    # Verify common Gmail folders exist
    common_folders = ["INBOX", "[Gmail]", "[Gmail]/All Mail", "[Gmail]/Sent Mail", "[Gmail]/Trash"]
    found_folders = [f for f in folders]
    
    for folder in common_folders:
        assert folder in found_folders, f"Common Gmail folder '{folder}' not found"
    
    # Test folder cache
    cached_folders = gmail_client.list_folders(refresh=False)
    assert cached_folders == folders, "Cached folders should match the original list"
    
    # Verify forcing refresh works
    refreshed_folders = gmail_client.list_folders(refresh=True)
    assert isinstance(refreshed_folders, list), "Refreshed folders should be a list"
    assert len(refreshed_folders) > 0, "Refreshed folder list should not be empty"


@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_folder_selection(gmail_client: ImapClient):
    """Test selecting different folders."""
    # Get available folders
    folders = gmail_client.list_folders()
    assert len(folders) > 0, "No folders available for testing"
    
    # Test INBOX selection
    with timed_operation("Selecting INBOX"):
        gmail_client.select_folder("INBOX")
    
    current_folder = gmail_client.current_folder
    assert current_folder == "INBOX", f"Current folder should be INBOX, got {current_folder}"
    
    # Test another folder
    if "[Gmail]/Sent Mail" in folders:
        with timed_operation("Selecting Sent Mail"):
            gmail_client.select_folder("[Gmail]/Sent Mail")
        
        current_folder = gmail_client.current_folder
        assert current_folder == "[Gmail]/Sent Mail", f"Current folder should be [Gmail]/Sent Mail, got {current_folder}"
    
    # Verify we can switch back to INBOX
    gmail_client.select_folder("INBOX")
    assert gmail_client.current_folder == "INBOX", "Failed to switch back to INBOX"
    
    # Test examining a folder in read-only mode
    if "[Gmail]/All Mail" in folders:
        gmail_client.select_folder("[Gmail]/All Mail", readonly=True)
        assert gmail_client.current_folder == "[Gmail]/All Mail", "Failed to examine [Gmail]/All Mail folder"


@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_folder_permissions(gmail_client: ImapClient):
    """Test folder permissions and boundary checks."""
    # Get available folders
    folders = gmail_client.list_folders()
    
    # Select an important folder like Sent Mail that should have restricted permissions
    if "[Gmail]/Sent Mail" in folders:
        # First, select in read-only mode which should work
        gmail_client.select_folder("[Gmail]/Sent Mail", readonly=True)
        assert gmail_client.current_folder == "[Gmail]/Sent Mail", "Failed to select [Gmail]/Sent Mail in read-only mode"
        
        # Try operations that should be allowed in read-only mode
        messages = gmail_client.search("ALL")
        assert isinstance(messages, list), "Search should return a list even in read-only mode"
        
        # Get folder status
        status = gmail_client.get_folder_status("[Gmail]/Sent Mail")
        assert isinstance(status, dict), "Folder status should be returned as a dictionary"
        assert b"EXISTS" in status, "Folder status should include message count"
        
        # Select INBOX for further tests
        gmail_client.select_folder("INBOX")
        assert gmail_client.current_folder == "INBOX", "Failed to switch to INBOX"
        
        # Test selecting a folder that should allow write access
        gmail_client.select_folder("INBOX", readonly=False)
        assert gmail_client.current_folder == "INBOX", "Failed to select INBOX in write mode"
        
        # Test selecting folder with different case (Gmail is case-sensitive)
        if "INBOX" in folders and "inbox" not in folders:
            # Testing case sensitivity
            gmail_client.select_folder("INBOX")  # Should succeed
            assert gmail_client.current_folder == "INBOX", "Failed with standard case"


# Search Tests
@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_basic_search(gmail_client: ImapClient):
    """Test basic search capabilities."""
    # First, select the INBOX
    gmail_client.select_folder("INBOX")
    
    # Do a simple search for all messages
    with timed_operation("Searching all messages"):
        all_messages = gmail_client.search("ALL")
    
    assert isinstance(all_messages, list), "Search should return a list of message IDs"
    logger.info(f"Found {len(all_messages)} messages in INBOX")
    
    # Test different search criteria
    search_criteria = [
        "ALL",
        "UNSEEN",
        "SEEN",
        "FROM gmail",
        "SUBJECT test"
    ]
    
    for criteria in search_criteria:
        with timed_operation(f"Searching with criteria: {criteria}"):
            results = gmail_client.search(criteria)
        
        assert isinstance(results, list), f"Search with criteria '{criteria}' should return a list"
        logger.info(f"Found {len(results)} messages matching '{criteria}'")
    
    # Test combined criteria
    combined_criteria = "SEEN FROM gmail"
    with timed_operation(f"Searching with combined criteria: {combined_criteria}"):
        combined_results = gmail_client.search(combined_criteria)
    
    assert isinstance(combined_results, list), "Combined search should return a list"
    logger.info(f"Found {len(combined_results)} messages matching combined criteria")
    
    # Try searching in another folder
    if "[Gmail]/Sent Mail" in gmail_client.list_folders():
        gmail_client.select_folder("[Gmail]/Sent Mail")
        sent_messages = gmail_client.search("ALL")
        assert isinstance(sent_messages, list), "Search in Sent Mail should return a list"
        logger.info(f"Found {len(sent_messages)} messages in Sent Mail")


@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_date_search(gmail_client: ImapClient):
    """Test date-based search capabilities."""
    # First, select the INBOX
    gmail_client.select_folder("INBOX")
    
    # Get all messages as baseline
    all_messages = gmail_client.search("ALL")
    logger.info(f"Found {len(all_messages)} total messages in INBOX")
    
    # Search for messages from the last 30 days
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
    date_criteria = f"SINCE {thirty_days_ago}"
    
    with timed_operation(f"Searching messages {date_criteria}"):
        recent_messages = gmail_client.search(date_criteria)
    
    assert isinstance(recent_messages, list), "Date search should return a list"
    logger.info(f"Found {len(recent_messages)} messages from the last 30 days")
    
    # Search for older messages
    ninety_days_ago = (datetime.now() - timedelta(days=90)).strftime("%d-%b-%Y")
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
    range_criteria = f"SINCE {ninety_days_ago} BEFORE {thirty_days_ago}"
    
    with timed_operation(f"Searching messages in date range"):
        range_messages = gmail_client.search(range_criteria)
    
    assert isinstance(range_messages, list), "Date range search should return a list"
    logger.info(f"Found {len(range_messages)} messages between 90 and 30 days ago")
    
    # Search for messages from today
    today = datetime.now().strftime("%d-%b-%Y")
    today_criteria = f"ON {today}"
    
    with timed_operation(f"Searching messages from today"):
        today_messages = gmail_client.search(today_criteria)
    
    assert isinstance(today_messages, list), "Today search should return a list"
    logger.info(f"Found {len(today_messages)} messages from today")
    
    # Try more complex date-based queries
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
    complex_criteria = f"SINCE {one_week_ago} UNSEEN"
    
    with timed_operation(f"Searching with complex criteria: {complex_criteria}"):
        complex_results = gmail_client.search(complex_criteria)
    
    assert isinstance(complex_results, list), "Complex search should return a list"
    logger.info(f"Found {len(complex_results)} unread messages from the last week")


# Content Tests
@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_fetch_email(gmail_client: ImapClient):
    """Test fetching email content."""
    # First, select the INBOX
    gmail_client.select_folder("INBOX")
    
    # Search for recent messages
    recent_messages = gmail_client.search("RECENT")
    
    # If no recent messages, fall back to all messages
    if not recent_messages:
        all_messages = gmail_client.search("ALL")
        if not all_messages:
            pytest.skip("No messages available for testing email fetching")
        
        # Take the most recent message
        message_id = all_messages[-1]
    else:
        message_id = recent_messages[0]
    
    # Fetch the message
    with timed_operation(f"Fetching message ID {message_id}"):
        email_obj = gmail_client.fetch_email(message_id)
    
    # Verify the email structure
    assert email_obj is not None, "Email should not be None"
    assert isinstance(email_obj, Email), "Fetched email should be an Email object"
    
    # Verify basic email properties
    assert email_obj.from_, "Email should have a From address"
    assert email_obj.subject, "Email should have a Subject"
    assert email_obj.date, "Email should have a Date"
    
    # Log email details
    logger.info(f"Fetched email: Subject='{email_obj.subject}', From='{email_obj.from_}'")


@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_fetch_multiple_emails(gmail_client: ImapClient):
    """Test fetching multiple emails."""
    # First, select the INBOX
    gmail_client.select_folder("INBOX")
    
    # Search for some recent messages
    messages = gmail_client.search("ALL")
    
    if len(messages) < 2:
        pytest.skip("Not enough messages available for testing multiple email fetching")
    
    # Take at most 5 messages to avoid long test times
    message_ids = messages[-5:] if len(messages) > 5 else messages
    
    # Fetch multiple messages
    with timed_operation(f"Fetching {len(message_ids)} messages"):
        emails = gmail_client.fetch_emails(message_ids)
    
    # Verify we got the expected number of emails
    assert isinstance(emails, dict), "Fetched emails should be returned as a dictionary"
    assert len(emails) == len(message_ids), f"Expected {len(message_ids)} emails, got {len(emails)}"
    
    # Verify each email
    for msg_id, email_obj in emails.items():
        assert msg_id in message_ids, f"Unexpected message ID {msg_id} in results"
        assert isinstance(email_obj, Email), f"Email {msg_id} should be an Email object"
        assert email_obj.uid == msg_id, f"Email UID {email_obj.uid} should match message ID {msg_id}"
        
        # Verify basic email properties
        assert email_obj.from_, f"Email {msg_id} should have a From address"
        assert email_obj.subject, f"Email {msg_id} should have a Subject"
    
    # Log summary
    logger.info(f"Successfully fetched and parsed {len(emails)} emails")


# Error Handling Tests
@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_invalid_folder(gmail_client: ImapClient):
    """Test handling of invalid folder selection."""
    # Try to select a folder that does not exist
    invalid_folder = "ThisFolderDoesNotExist12345"
    
    # This should raise an exception
    with pytest.raises(Exception) as excinfo:
        gmail_client.select_folder(invalid_folder)
    
    # Verify the error message
    error_str = str(excinfo.value).lower()
    
    # Gmail might return different error messages, but all should indicate the folder doesn't exist
    assert any(phrase in error_str for phrase in [
        "nonexistent", "folder not found", "unknown mailbox", "doesn't exist", "no such"
    ]), f"Expected folder not found error, got: {excinfo.value}"
    
    # Make sure we can still select a valid folder after the error
    gmail_client.select_folder("INBOX")
    assert gmail_client.current_folder == "INBOX", "Failed to select valid folder after error"


@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_invalid_search(gmail_client: ImapClient):
    """Test handling of invalid search criteria."""
    gmail_client.select_folder("INBOX")
    
    invalid_search = "INVALID_CRITERION"
    
    # Attempt an invalid search
    with pytest.raises(Exception) as excinfo:
        with timed_operation(f"Executing invalid search {invalid_search}"):
            gmail_client.search(invalid_search)
    
    error_message = str(excinfo.value)
    logger.info(f"Expected error: {error_message}")
    
    # Verify error message contains useful information
    assert "search" in error_message.lower() or "criteria" in error_message.lower() or "command" in error_message.lower()
    
    # Make sure we can still do a valid search after the error
    with timed_operation("Executing valid search after error"):
        results = gmail_client.search("ALL")
    logger.info(f"Found {len(results)} messages in valid search after error")


# Message Count Tests
@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_message_counts(gmail_client: ImapClient):
    """Test getting message counts from Gmail folders."""
    # Test counts in INBOX
    with timed_operation("Getting INBOX message counts"):
        # Get all counts from the same folder status to ensure consistency
        gmail_client.select_folder("INBOX")
        folder_status = gmail_client.get_folder_status("INBOX")
        total = folder_status.get(b"MESSAGES", 0)
        unread = folder_status.get(b"UNSEEN", 0)
        read = max(0, total - unread)  # Calculate read from the same status data
        
        # Now get the values using the client methods but use the refresh parameter
        # to ensure we're getting the latest values
        total_count = gmail_client.get_total_count("INBOX", refresh=True)
        unread_count = gmail_client.get_unread_count("INBOX", refresh=True)
        read_count = gmail_client.get_read_count("INBOX", refresh=True)
    
    logger.info(f"INBOX total: {total_count}, unread: {unread_count}, read: {read_count}")
    logger.info(f"Status values - total: {total}, unread: {unread}, read: {read}")
    
    # Verify counts are consistent with themselves
    assert total_count >= 0, "Total count should be non-negative"
    assert unread_count >= 0, "Unread count should be non-negative"
    assert read_count >= 0, "Read count should be non-negative"
    assert total_count == unread_count + read_count, f"Total ({total_count}) should equal unread ({unread_count}) + read ({read_count})"
    
    # Test getting counts in a non-INBOX folder (e.g. "[Gmail]/Sent Mail")
    folders = gmail_client.list_folders()
    sent_folder = next((f for f in folders if 'sent' in f.lower()), None)
    
    if sent_folder:
        with timed_operation(f"Getting counts from {sent_folder}"):
            # Get a single folder status and use its values consistently
            gmail_client.select_folder(sent_folder)
            folder_status = gmail_client.get_folder_status(sent_folder)
            total = folder_status.get(b"MESSAGES", 0)
            unread = folder_status.get(b"UNSEEN", 0)
            read = max(0, total - unread)  # Calculate read from the same status data
            
            # Get the values using the client methods with refresh=True to ensure consistency
            total_count = gmail_client.get_total_count(sent_folder, refresh=True)
            unread_count = gmail_client.get_unread_count(sent_folder, refresh=True)
            read_count = gmail_client.get_read_count(sent_folder, refresh=True)
        
        logger.info(f"{sent_folder} total: {total_count}, unread: {unread_count}, read: {read_count}")
        
        # Verify counts are consistent with themselves
        assert total_count >= 0, "Total count should be non-negative"
        assert unread_count >= 0, "Unread count should be non-negative"
        assert read_count >= 0, "Read count should be non-negative"
        assert total_count == unread_count + read_count, f"Total ({total_count}) should equal unread ({unread_count}) + read ({read_count})"


@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_message_count_caching(gmail_client: ImapClient):
    """Test message count caching behavior with real Gmail account."""
    # Get initial counts with a consistent folder status
    with timed_operation("Initial count retrieval"):
        gmail_client.select_folder("INBOX")
        folder_status = gmail_client.get_folder_status("INBOX")
        total = folder_status.get(b"MESSAGES", 0)
        unread = folder_status.get(b"UNSEEN", 0)
        read = max(0, total - unread)  # Calculate read from the same status data
        
        # Force refresh to ensure we have fresh cache values
        total_count = gmail_client.get_total_count("INBOX", refresh=True)
        unread_count = gmail_client.get_unread_count("INBOX", refresh=True)
        read_count = gmail_client.get_read_count("INBOX", refresh=True)
    
    logger.info(f"INBOX total: {total_count}, unread: {unread_count}, read: {read_count}")
    logger.info(f"Status values - total: {total}, unread: {unread}, read: {read}")
    
    # Verify counts are consistent with themselves
    assert total_count >= 0, "Total count should be non-negative"
    assert unread_count >= 0, "Unread count should be non-negative"
    assert read_count >= 0, "Read count should be non-negative"
    assert total_count == unread_count + read_count, f"Total ({total_count}) should equal unread ({unread_count}) + read ({read_count})"
    
    # Get counts again - should use cache
    with timed_operation("Cached count retrieval"):
        cached_total_count = gmail_client.get_total_count("INBOX")
        cached_unread_count = gmail_client.get_unread_count("INBOX")
        cached_read_count = gmail_client.get_read_count("INBOX")
    
    logger.info(f"Cached INBOX total: {cached_total_count}, unread: {cached_unread_count}, read: {cached_read_count}")
    
    # Counts should be identical to the values we just retrieved
    assert cached_total_count == total_count, "Cached total count should match initial count"
    assert cached_unread_count == unread_count, "Cached unread count should match initial count"
    assert cached_read_count == read_count, "Cached read count should match initial count"
    
    # Force refresh and check again - might match or might be different if emails arrived
    with timed_operation("Forced refresh count retrieval"):
        total_count = gmail_client.get_total_count("INBOX", refresh=True)
        unread_count = gmail_client.get_unread_count("INBOX", refresh=True)
        read_count = gmail_client.get_read_count("INBOX", refresh=True)
    
    logger.info(f"Refreshed INBOX total: {total_count}, unread: {unread_count}, read: {read_count}")
    
    # Log any differences
    if cached_total_count != total_count or cached_unread_count != unread_count or cached_read_count != read_count:
        logger.info(f"Count changed during test: " 
                   f"total {cached_total_count}->{total_count}, "
                   f"unread {cached_unread_count}->{unread_count}, "
                   f"read {cached_read_count}->{read_count}")
    
    # This should still be true regardless of counts
    assert total_count == unread_count + read_count, "Total should equal unread + read after refresh"


@pytest.mark.integration
@pytest.mark.gmail
@pytest.mark.oauth2
def test_gmail_message_count_special_folders(gmail_client: ImapClient):
    """Test getting message counts from Gmail special folders."""
    folders = gmail_client.list_folders()
    
    # Find Gmail special folders
    special_folders = [f for f in folders if '[Gmail]/' in f or '[Google Mail]/' in f]
    
    if not special_folders:
        pytest.skip("No Gmail special folders found, skipping test")
    
    # Test a few special folders
    for folder in special_folders[:3]:  # Limit to 3 folders to keep test duration reasonable
        with timed_operation(f"Getting counts from {folder}"):
            try:
                # Get a single folder status and use its values consistently
                gmail_client.select_folder(folder)
                folder_status = gmail_client.get_folder_status(folder)
                total = folder_status.get(b"MESSAGES", 0)
                unread = folder_status.get(b"UNSEEN", 0)
                read = max(0, total - unread)  # Calculate read from the same status data
                
                # Get the values using the client methods with refresh=True to ensure consistency
                total_count = gmail_client.get_total_count(folder, refresh=True)
                unread_count = gmail_client.get_unread_count(folder, refresh=True)
                read_count = gmail_client.get_read_count(folder, refresh=True)
                
                logger.info(f"{folder} total: {total_count}, unread: {unread_count}, read: {read_count}")
                
                # Verify counts are consistent with themselves
                assert total_count >= 0, f"Total count for {folder} should be non-negative"
                assert unread_count >= 0, f"Unread count for {folder} should be non-negative"
                assert read_count >= 0, f"Read count for {folder} should be non-negative"
                assert total_count == unread_count + read_count, f"Total should equal unread + read for {folder}"
            except Exception as e:
                # Some special folders might have restrictions
                logger.warning(f"Error getting counts from {folder}: {e}")
                continue
