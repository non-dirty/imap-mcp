"""Tests for SMTP client MIME composition functionality."""

import re
import pytest
from datetime import datetime

from imap_mcp.models import Email, EmailAddress, EmailContent
from imap_mcp.smtp_client import create_reply_mime


class TestCreateReplyMime:
    """Tests for create_reply_mime function."""
    
    @pytest.fixture
    def sample_email(self) -> Email:
        """Create a sample email for testing."""
        return Email(
            message_id="<test123@example.com>",
            subject="Test Subject",
            from_=EmailAddress(name="Sender Name", address="sender@example.com"),
            to=[EmailAddress(name="Recipient Name", address="recipient@example.com")],
            cc=[EmailAddress(name="CC Recipient", address="cc@example.com")],
            date=datetime.now(),
            content=EmailContent(text="Original message content\nOn multiple lines.", 
                                html="<p>Original message content</p><p>On multiple lines.</p>"),
            headers={"References": "<previous@example.com>"}
        )
    
    def test_create_basic_reply(self, sample_email: Email):
        """Test creating a basic reply."""
        reply_to = EmailAddress(name="Reply To", address="sender@example.com")
        subject = "Re: Test Subject"
        body = "This is a reply."
        
        mime_message = create_reply_mime(
            original_email=sample_email,
            reply_to=reply_to,
            subject=subject,
            body=body
        )
        
        # Check basic properties
        assert mime_message["To"] == "Sender Name <sender@example.com>"
        assert mime_message["Subject"] == "Re: Test Subject"
        assert mime_message["From"] == "Reply To <sender@example.com>"
        assert mime_message["In-Reply-To"] == "<test123@example.com>"
        assert "<test123@example.com>" in mime_message["References"]
        assert "<previous@example.com>" in mime_message["References"]
        
        # Check content - handle both multipart and non-multipart payloads
        if mime_message.is_multipart():
            payload = mime_message.get_payload(0).get_payload(decode=True).decode()
        else:
            payload = mime_message.get_payload(decode=True).decode()
            
        assert "This is a reply." in payload
        assert "Original message content" in payload

    def test_create_reply_all(self, sample_email: Email):
        """Test creating a reply-all."""
        reply_to = EmailAddress(name="Reply To", address="sender@example.com")
        subject = "Re: Test Subject"
        body = "This is a reply to all."
        
        mime_message = create_reply_mime(
            original_email=sample_email,
            reply_to=reply_to,
            subject=subject,
            body=body,
            reply_all=True
        )
        
        # Check recipients - should include original CCs and sender
        assert mime_message["To"] == "Sender Name <sender@example.com>, Recipient Name <recipient@example.com>"
        assert mime_message["Cc"] == "CC Recipient <cc@example.com>"
        
    def test_create_reply_with_custom_cc(self, sample_email: Email):
        """Test creating a reply with custom CC recipients."""
        reply_to = EmailAddress(name="Reply To", address="sender@example.com")
        subject = "Re: Test Subject"
        body = "This is a reply with custom CC."
        cc = [
            EmailAddress(name="Custom CC", address="custom@example.com"),
            EmailAddress(name="Another CC", address="another@example.com")
        ]
        
        mime_message = create_reply_mime(
            original_email=sample_email,
            reply_to=reply_to,
            subject=subject,
            body=body,
            cc=cc
        )
        
        # Check CC recipients
        assert mime_message["Cc"] == "Custom CC <custom@example.com>, Another CC <another@example.com>"
        
    def test_create_reply_with_subject_prefix(self, sample_email: Email):
        """Test creating a reply with a custom subject prefix."""
        reply_to = EmailAddress(name="Reply To", address="sender@example.com")
        body = "This is a reply with custom subject prefix."
        
        # No prefix provided, but original doesn't start with Re:
        mime_message = create_reply_mime(
            original_email=sample_email,
            reply_to=reply_to,
            body=body
        )
        
        assert mime_message["Subject"].startswith("Re: ")
        
        # Custom subject provided
        custom_subject = "Custom: Test Subject"
        mime_message = create_reply_mime(
            original_email=sample_email,
            reply_to=reply_to,
            body=body,
            subject=custom_subject
        )
        
        assert mime_message["Subject"] == custom_subject
        
        # Original already has Re: prefix
        sample_email.subject = "Re: Already Prefixed"
        mime_message = create_reply_mime(
            original_email=sample_email,
            reply_to=reply_to,
            body=body
        )
        
        assert mime_message["Subject"] == "Re: Already Prefixed"
        
    def test_create_html_reply(self, sample_email: Email):
        """Test creating a reply with HTML content."""
        reply_to = EmailAddress(name="Reply To", address="sender@example.com")
        body = "This is a plain text reply."
        html_body = "<p>This is an <b>HTML</b> reply.</p>"
        
        mime_message = create_reply_mime(
            original_email=sample_email,
            reply_to=reply_to,
            body=body,
            html_body=html_body
        )
        
        # Should be multipart with at least 2 parts
        assert mime_message.is_multipart()
        alternative = mime_message.get_payload(0)
        assert alternative.is_multipart()
        
        # Check HTML part
        html_part = alternative.get_payload(1)
        html_text = html_part.get_payload(decode=True).decode()
        assert "<p>This is an <b>HTML</b> reply.</p>" in html_text
        
    def test_quoting_original_content(self, sample_email: Email):
        """Test proper quoting of original content."""
        reply_to = EmailAddress(name="Reply To", address="sender@example.com")
        body = "This is a reply with original content quoted."
        
        mime_message = create_reply_mime(
            original_email=sample_email,
            reply_to=reply_to,
            body=body
        )
        
        # Check content
        if mime_message.is_multipart():
            payload = mime_message.get_payload(0).get_payload(decode=True).decode()
        else:
            payload = mime_message.get_payload(decode=True).decode()
            
        # Should have quoting prefix (>) and original content
        assert "This is a reply with original content quoted." in payload
        
        # Check for proper quoting
        lines = payload.split("\n")
        quoted_lines = [line for line in lines if line.startswith(">")]
        assert any("> Original message content" in line for line in quoted_lines)
