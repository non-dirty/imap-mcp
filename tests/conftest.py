"""Pytest fixtures for IMAP MCP tests."""

import datetime
import email
import email.utils
import os
import re
import time
import logging
from contextlib import contextmanager
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Generator
from unittest.mock import MagicMock, patch

import pytest
try:
    from imapclient.response_types import Address, BodyData, Envelope
except ImportError:
    # Mock these classes if not available
    class Address: pass
    class BodyData: pass
    class Envelope: pass

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda x=None: None

from imap_mcp.models import Email, EmailAddress, EmailAttachment, EmailContent
from imap_mcp.config import ImapConfig, OAuth2Config
from imap_mcp.imap_client import ImapClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption(
        "--skip-integration",
        action="store_true",
        default=False,
        help="Skip integration tests that require real services",
    )


def pytest_configure(config):
    """Configure pytest with additional markers."""
    config.addinivalue_line(
        "markers", "integration: tests that require connection to real services"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if --skip-integration is provided."""
    if config.getoption("--skip-integration"):
        skip_integration = pytest.mark.skip(reason="Integration tests skipped with --skip-integration")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture
def mock_imap_client():
    """Create a mock IMAPClient for testing."""
    with patch("imapclient.IMAPClient") as mock_client:
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        
        # Set up standard responses
        client_instance.list_folders.return_value = [
            ((b"\\HasNoChildren",), b"/", "INBOX"),
            ((b"\\HasNoChildren",), b"/", "Sent"),
            ((b"\\HasNoChildren",), b"/", "Drafts"),
            ((b"\\HasNoChildren",), b"/", "Trash"),
        ]
        client_instance.select_folder.return_value = {b"EXISTS": 5}
        client_instance.search.return_value = [1, 2, 3, 4, 5]
        
        yield client_instance


@pytest.fixture
def test_email_message_simple():
    """Create a simple test email message."""
    msg = MIMEText("This is a simple test email.")
    msg["From"] = "Test Sender <sender@example.com>"
    msg["To"] = "Test Recipient <recipient@example.com>"
    msg["Subject"] = "Simple Test Email"
    msg["Message-ID"] = "<simple-test-123@example.com>"
    msg["Date"] = email.utils.formatdate()
    return msg


@pytest.fixture
def test_email_message_multipart():
    """Create a multipart test email message with text and HTML parts."""
    msg = MIMEMultipart()
    msg["From"] = "Test Sender <sender@example.com>"
    msg["To"] = "Test Recipient <recipient@example.com>, cc-person@example.com"
    msg["Cc"] = "Another Person <another@example.com>"
    msg["Subject"] = "Multipart Test Email"
    msg["Message-ID"] = "<multipart-test-123@example.com>"
    msg["Date"] = email.utils.formatdate()
    
    # Add text part
    text_part = MIMEText("This is the plain text content.", "plain")
    msg.attach(text_part)
    
    # Add HTML part
    html_part = MIMEText("<p>This is the <b>HTML</b> content.</p>", "html")
    msg.attach(html_part)
    
    return msg


@pytest.fixture
def test_email_message_with_attachment():
    """Create a test email message with an attachment."""
    msg = MIMEMultipart()
    msg["From"] = "Test Sender <sender@example.com>"
    msg["To"] = "Test Recipient <recipient@example.com>"
    msg["Subject"] = "Email with Attachment"
    msg["Message-ID"] = "<attachment-test-123@example.com>"
    msg["Date"] = email.utils.formatdate()
    
    # Add text part
    text_part = MIMEText("This email has an attachment.", "plain")
    msg.attach(text_part)
    
    # Add attachment
    attachment = MIMEApplication(b"This is attachment content")
    attachment.add_header("Content-Disposition", "attachment", filename="test.txt")
    msg.attach(attachment)
    
    return msg


@pytest.fixture
def test_email_message_encoded_headers():
    """Create a test email message with encoded headers."""
    msg = MIMEMultipart()
    msg["From"] = str(Header("Jöhn Döe", "utf-8")) + " <john@example.com>"
    msg["To"] = str(Header("Märíä Smith", "utf-8")) + " <maria@example.com>"
    msg["Subject"] = Header("Tést Émàil with Éncödëd Headers", "utf-8").encode()
    msg["Message-ID"] = "<encoded-test-123@example.com>"
    msg["Date"] = email.utils.formatdate()
    
    # Add text part
    text_part = MIMEText("This email has encoded headers.", "plain")
    msg.attach(text_part)
    
    return msg


@pytest.fixture
def make_test_email_message():
    """Factory fixture to create customized test email messages."""
    def _make_test_email_message(
        from_addr: str = "sender@example.com",
        from_name: str = "Test Sender",
        to_addrs: List[Tuple[str, str]] = [("recipient@example.com", "Test Recipient")],
        cc_addrs: List[Tuple[str, str]] = [],
        bcc_addrs: List[Tuple[str, str]] = [],
        subject: str = "Test Email",
        body_text: str = "This is a test email.",
        body_html: Optional[str] = None,
        attachments: List[Tuple[str, bytes, str]] = [],  # [(filename, content, content_type)]
        date: Optional[datetime.datetime] = None,
        message_id: Optional[str] = None,
        headers: Dict[str, str] = {},
    ) -> MIMEMultipart:
        """Create a customized email message for testing.
        
        Args:
            from_addr: Sender email address
            from_name: Sender name
            to_addrs: List of (email, name) tuples for To: recipients
            cc_addrs: List of (email, name) tuples for Cc: recipients
            bcc_addrs: List of (email, name) tuples for Bcc: recipients
            subject: Email subject
            body_text: Plain text body content
            body_html: HTML body content (optional)
            attachments: List of (filename, content, content_type) tuples
            date: Email date (defaults to current time)
            message_id: Custom Message-ID (default: auto-generated)
            headers: Additional headers as dict
            
        Returns:
            Email message object
        """
        # Create multipart message
        msg = MIMEMultipart() if body_html or attachments else MIMEText(body_text)
        
        # Add basic headers
        msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
        msg["To"] = ", ".join(f"{name} <{addr}>" if name else addr for addr, name in to_addrs)
        
        if cc_addrs:
            msg["Cc"] = ", ".join(f"{name} <{addr}>" if name else addr for addr, name in cc_addrs)
        if bcc_addrs:
            msg["Bcc"] = ", ".join(f"{name} <{addr}>" if name else addr for addr, name in bcc_addrs)
            
        msg["Subject"] = subject
        
        # Add date
        if date:
            msg["Date"] = email.utils.format_datetime(date)
        else:
            msg["Date"] = email.utils.formatdate()
            
        # Add Message-ID
        if message_id:
            msg["Message-ID"] = message_id
        else:
            msg["Message-ID"] = f"<test-{hash(subject)}-{hash(from_addr)}@example.com>"
            
        # Add additional headers
        for name, value in headers.items():
            msg[name] = value
            
        # If multipart, add parts
        if isinstance(msg, MIMEMultipart):
            # Add text part
            text_part = MIMEText(body_text, "plain")
            msg.attach(text_part)
            
            # Add HTML part if provided
            if body_html:
                html_part = MIMEText(body_html, "html")
                msg.attach(html_part)
                
            # Add attachments
            for filename, content, content_type in attachments:
                attachment = MIMEApplication(content)
                attachment.add_header("Content-Disposition", "attachment", filename=filename)
                attachment.add_header("Content-Type", content_type)
                msg.attach(attachment)
                
        return msg
    
    return _make_test_email_message


@pytest.fixture
def test_email_response_data():
    """Create test IMAP email response data."""
    return {
        b"BODY[]": b"""From: Test Sender <sender@example.com>
To: Test Recipient <recipient@example.com>
Subject: Test Email
Date: Thu, 01 Jan 2023 12:00:00 +0000
Message-ID: <test-123@example.com>

This is a test email body.
""",
        b"FLAGS": (b"\\Seen",),
        b"UID": 12345,
        b"INTERNALDATE": "01-Jan-2023 12:00:00 +0000"
    }


@pytest.fixture
def make_test_email_response_data():
    """Factory fixture to create customized IMAP email response data."""
    def _make_response_data(
        uid: int = 12345,
        flags: Tuple[bytes, ...] = (b"\\Seen",),
        internal_date: str = "01-Jan-2023 12:00:00 +0000",
        body: Optional[bytes] = None,
        headers: Dict[str, str] = {
            "From": "Test Sender <sender@example.com>",
            "To": "Test Recipient <recipient@example.com>",
            "Subject": "Test Email",
            "Date": "Thu, 01 Jan 2023 12:00:00 +0000",
            "Message-ID": "<test-123@example.com>"
        },
        body_text: str = "This is a test email body."
    ) -> Dict[bytes, Any]:
        """Create customized IMAP response data for testing."""
        if body is None:
            # Construct body from headers and body_text
            header_lines = [f"{k}: {v}" for k, v in headers.items()]
            header_text = "\r\n".join(header_lines)
            body = f"{header_text}\r\n\r\n{body_text}".encode("utf-8")

        return {
            b"BODY[]": body,
            b"FLAGS": flags,
            b"UID": uid,
            b"INTERNALDATE": internal_date
        }
    
    return _make_response_data


@pytest.fixture
def test_email_model():
    """Create a test Email model instance."""
    return Email(
        message_id="<test-123@example.com>",
        subject="Test Email",
        from_=EmailAddress(name="Test Sender", address="sender@example.com"),
        to=[EmailAddress(name="Test Recipient", address="recipient@example.com")],
        date=datetime.datetime(2023, 1, 1, 12, 0, 0),
        content=EmailContent(text="This is a test email body."),
        folder="INBOX",
        uid=12345
    )


@pytest.fixture
def configure_test_env():
    """Configure environment variables for testing."""
    # Save original environment
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ["IMAP_SERVER"] = "imap.example.com"
    os.environ["IMAP_PORT"] = "993"
    os.environ["IMAP_USERNAME"] = "test@example.com"
    os.environ["IMAP_PASSWORD"] = "test_password"
    os.environ["MCP_SERVER_PORT"] = "3000"
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Load environment variables from .env.test if it exists
load_dotenv(".env.test")

# Constants for Gmail integration tests
TEST_EMAIL = os.getenv("GMAIL_TEST_EMAIL", "test@example.com")
REQUIRED_ENV_VARS = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN", "GMAIL_TEST_EMAIL"]


@contextmanager
def timed_operation(description: str) -> Generator[None, None, None]:
    """Context manager to measure and log operation time.
    
    Args:
        description: Description of the operation being timed
    """
    logger.info(f"Starting: {description}")
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        logger.info(f"Completed: {description} in {elapsed:.2f} seconds")


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


@pytest.fixture
def gmail_oauth_credentials() -> Dict[str, str]:
    """Get Gmail OAuth2 credentials from environment variables.
    
    Returns:
        Dictionary with OAuth2 credentials
    """
    credentials = load_oauth2_credentials()
    if not credentials:
        pytest.skip("Gmail OAuth2 credentials not available in environment variables")
    return credentials


@pytest.fixture
def gmail_config(gmail_oauth_credentials: Dict[str, str]) -> ImapConfig:
    """Create a configuration for Gmail IMAP.
    
    Args:
        gmail_oauth_credentials: Dictionary with OAuth2 credentials
        
    Returns:
        ImapConfig for Gmail with OAuth2
    """
    oauth2_config = OAuth2Config(**gmail_oauth_credentials)
    return ImapConfig(
        host="imap.gmail.com",
        port=993,
        username=TEST_EMAIL,
        use_ssl=True,
        oauth2=oauth2_config
    )


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