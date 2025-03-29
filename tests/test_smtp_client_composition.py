"""Tests for SMTP client message composition functionality."""

import email
import unittest
from datetime import datetime
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from imap_mcp.models import Email, EmailAddress, EmailContent
from imap_mcp.smtp_client import SmtpClient


class TestSmtpClientComposition:
    """Test class for SMTP message composition."""

    @pytest.fixture
    def smtp_client(self):
        """Create a SmtpClient instance for testing."""
        client = SmtpClient("test_user@example.com")
        return client

    @pytest.fixture
    def original_email(self):
        """Create a sample original email for testing replies."""
        return Email(
            message_id="<original-message-id@example.com>",
            subject="Original Subject",
            from_=EmailAddress(name="Sender", address="sender@example.com"),
            to=[EmailAddress(name="Test User", address="test_user@example.com")],
            cc=[EmailAddress(name="CC Person", address="cc@example.com")],
            date=datetime.now(),
            content=EmailContent(text="Original email body text", html="<p>Original email body HTML</p>"),
            headers={"Message-ID": "<original-message-id@example.com>"},
            in_reply_to=None,
            references=[]
        )

    @pytest.fixture
    def original_email_with_references(self):
        """Create a sample original email with References header."""
        return Email(
            message_id="<original-message-id@example.com>",
            subject="Original Subject",
            from_=EmailAddress(name="Sender", address="sender@example.com"),
            to=[EmailAddress(name="Test User", address="test_user@example.com")],
            cc=[EmailAddress(name="CC Person", address="cc@example.com")],
            date=datetime.now(),
            content=EmailContent(text="Original email body text", html="<p>Original email body HTML</p>"),
            headers={"Message-ID": "<original-message-id@example.com>"},
            in_reply_to="<previous-message@example.com>",
            references=["<first-message@example.com>", "<previous-message@example.com>"]
        )

    def test_create_reply_mime_basic(self, smtp_client, original_email):
        """Test creating a basic reply message."""
        reply_text = "This is my reply"
        
        # Create reply
        reply_message = smtp_client.create_reply_mime(original_email, reply_text)
        
        # Verify it's a MIMEMultipart message
        assert isinstance(reply_message, MIMEMultipart)
        
        # Check headers
        assert reply_message["Subject"] == "Re: Original Subject"
        assert reply_message["To"] == "Sender <sender@example.com>"
        assert reply_message["From"] == "test_user@example.com"
        assert reply_message["In-Reply-To"] == "<original-message-id@example.com>"
        assert reply_message["References"] == "<original-message-id@example.com>"
        
        # Check content
        parts = list(reply_message.walk())
        assert len(parts) >= 2  # At least the container and a text part
        
        # Find the text part
        text_part = None
        for part in parts:
            if part.get_content_type() == "text/plain":
                text_part = part
                break
        
        assert text_part is not None
        text_content = text_part.get_payload(decode=True).decode()
        
        # Verify that our new text is included
        assert "This is my reply" in text_content
        
        # Verify that the original message is quoted
        assert "> Original email body text" in text_content

    def test_create_reply_mime_reply_all(self, smtp_client, original_email):
        """Test reply-all message with correct To and Cc fields."""
        reply_text = "This is a reply-all"
        
        # Add another person to the 'to' field of the original email
        original_email.to.append(EmailAddress(name="Another Person", address="another@example.com"))
        
        # Create reply-all
        reply_message = smtp_client.create_reply_mime(original_email, reply_text, reply_all=True)
        
        # Verify To and Cc fields
        to_addresses = reply_message["To"].split(", ")
        cc_addresses = reply_message["Cc"].split(", ")
        
        # To should contain the original sender
        assert "Sender <sender@example.com>" in to_addresses
        
        # To might also contain other original recipients
        for to_addr in original_email.to:
            if to_addr.address != "test_user@example.com":  # Exclude self
                assert f"{to_addr.name} <{to_addr.address}>" in (to_addresses + cc_addresses)
        
        # Cc should contain all original Cc recipients
        for cc_addr in original_email.cc:
            if cc_addr.address != "test_user@example.com":  # Exclude self
                assert f"{cc_addr.name} <{cc_addr.address}>" in cc_addresses

    def test_create_reply_mime_subject_prefix(self, smtp_client, original_email):
        """Test that Re: is properly added to subject."""
        # Test when subject doesn't have Re:
        reply_message = smtp_client.create_reply_mime(original_email, "Reply")
        assert reply_message["Subject"] == "Re: Original Subject"
        
        # Test when subject already has Re:
        original_email.subject = "Re: Original Subject"
        reply_message = smtp_client.create_reply_mime(original_email, "Reply")
        assert reply_message["Subject"] == "Re: Original Subject"  # Should not add another Re:
        
        # Test with different capitalization
        original_email.subject = "re: Original Subject"
        reply_message = smtp_client.create_reply_mime(original_email, "Reply")
        assert reply_message["Subject"] == "re: Original Subject"  # Should not change existing prefix

    def test_create_reply_mime_quoting(self, smtp_client, original_email):
        """Test that original message is properly quoted with attribution."""
        original_email.date = datetime(2025, 3, 28, 10, 0, 0)  # Set a fixed date for testing
        reply_text = "This is my reply"
        
        reply_message = smtp_client.create_reply_mime(original_email, reply_text)
        
        # Extract the text content
        parts = list(reply_message.walk())
        text_part = None
        for part in parts:
            if part.get_content_type() == "text/plain":
                text_part = part
                break
        
        assert text_part is not None
        text_content = text_part.get_payload(decode=True).decode()
        
        # Check for attribution line and quoted content
        assert "On 2025-03-28 10:00:00, Sender <sender@example.com> wrote:" in text_content
        assert "> Original email body text" in text_content
        
        # Verify the new content is before the quoted content
        index_reply = text_content.find(reply_text)
        index_attribution = text_content.find("On ")
        assert index_reply < index_attribution, "Reply text should come before attribution line"

    def test_create_reply_mime_missing_headers(self, smtp_client):
        """Test reply creation when original email is missing headers."""
        # Create an email with minimal headers
        minimal_email = Email(
            message_id="",  # Missing Message-ID
            subject="Subject",
            from_=EmailAddress(name="Sender", address="sender@example.com"),
            to=[EmailAddress(name="Recipient", address="recipient@example.com")],
            content=EmailContent(text="Body")
        )
        
        reply_message = smtp_client.create_reply_mime(minimal_email, "My reply")
        
        # Verify graceful handling of missing Message-ID
        assert "In-Reply-To" not in reply_message
        assert "References" not in reply_message
        
        # Should still create a valid reply otherwise
        assert reply_message["Subject"] == "Re: Subject"
        assert reply_message["To"] == "Sender <sender@example.com>"

    def test_create_reply_mime_with_cc(self, smtp_client, original_email):
        """Test that explicit cc addresses are added correctly."""
        explicit_cc = ["explicit1@example.com", "explicit2@example.com"]
        
        reply_message = smtp_client.create_reply_mime(
            original_email, 
            "Reply with explicit CC", 
            cc=explicit_cc
        )
        
        # Check that explicit CC addresses are included
        cc_header = reply_message["Cc"]
        assert cc_header is not None
        
        for cc_addr in explicit_cc:
            assert cc_addr in cc_header

    def test_create_reply_mime_no_self_reply(self, smtp_client):
        """Test that user's own email is not included in To/Cc."""
        # Create email where the user is both in To and Cc
        self_email = Email(
            message_id="<msg-id@example.com>",
            subject="Subject",
            from_=EmailAddress(name="Sender", address="sender@example.com"),
            to=[
                EmailAddress(name="Test User", address="test_user@example.com"),
                EmailAddress(name="Other", address="other@example.com")
            ],
            cc=[
                EmailAddress(name="Test User", address="test_user@example.com"),
                EmailAddress(name="Cc Person", address="cc_person@example.com")
            ],
            content=EmailContent(text="Body")
        )
        
        # Create reply with reply-all
        reply_message = smtp_client.create_reply_mime(
            self_email, 
            "No self in headers", 
            reply_all=True
        )
        
        # Check To and Cc headers
        to_header = reply_message["To"]
        cc_header = reply_message["Cc"] or ""
        
        # User's own email should not be in either header
        assert "test_user@example.com" not in to_header
        assert "test_user@example.com" not in cc_header
        
        # But other recipients should be included
        assert "other@example.com" in to_header
        assert "cc_person@example.com" in cc_header

    def test_create_reply_mime_with_html(self, smtp_client, original_email):
        """Test creating a reply with both HTML and plain text content."""
        # Create HTML and plain text content for the reply
        plain_text = "This is a plain text reply."
        html_text = "<p>This is an <strong>HTML</strong> reply.</p>"
        
        # Create the reply
        reply = smtp_client.create_reply_mime(
            original_email,
            body_text=plain_text,
            body_html=html_text
        )
        
        # Verify the basic headers
        assert reply['To'] == "Sender <sender@example.com>"
        assert reply['Subject'] == "Re: Original Subject"
        assert reply['In-Reply-To'] == "<original-message-id@example.com>"
        
        # Check content type - should be multipart/related
        assert reply.get_content_type() == "multipart/related"
        
        # Get the parts
        parts = list(reply.walk())
        
        # Find the alternative part
        alternative_part = None
        for part in parts:
            if part.get_content_type() == "multipart/alternative":
                alternative_part = part
                break
        
        assert alternative_part is not None, "multipart/alternative not found"
        
        # Check that alternative part has both text and HTML subparts
        alt_parts = list(alternative_part.walk())
        text_part = None
        html_part = None
        
        for part in alt_parts:
            if part.get_content_type() == "text/plain":
                text_part = part
            elif part.get_content_type() == "text/html":
                html_part = part
        
        assert text_part is not None, "text/plain part not found"
        assert html_part is not None, "text/html part not found"
        
        # Check content of text part
        text_content = text_part.get_payload()
        assert plain_text in text_content
        assert "On " in text_content  # Attribution line
        assert "> Original email body text" in text_content  # Quoted content
        
        # Check content of HTML part
        html_content = html_part.get_payload()
        assert html_text in html_content
        assert "<blockquote" in html_content  # HTML quoting
        assert "<p>On " in html_content  # HTML attribution
