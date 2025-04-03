"""Tests for the test infrastructure itself."""

import email
import os
import pytest
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from imap_mcp.models import Email, EmailAddress
from tests.test_utils import (
    assert_email_equals,
    create_mock_folder_list,
    generate_test_emails,
    parse_message_to_dict,
    random_email_address,
    random_name,
    random_string,
)


class TestTestUtils:
    """Test the test utilities."""

    def test_random_string(self):
        """Test random string generation."""
        # Test default length
        s1 = random_string()
        assert len(s1) == 10
        assert isinstance(s1, str)

        # Test custom length
        s2 = random_string(5)
        assert len(s2) == 5
        assert isinstance(s2, str)

        # Test randomness
        s3 = random_string(20)
        s4 = random_string(20)
        assert s3 != s4  # This could theoretically fail but very unlikely

    def test_random_email_address(self):
        """Test random email address generation."""
        email1 = random_email_address()
        assert "@" in email1
        username, domain = email1.split("@")
        assert len(username) == 8
        assert domain.endswith(".com")
        assert len(domain) == 10  # 6 chars + ".com"

        # Test randomness
        email2 = random_email_address()
        assert email1 != email2

    def test_random_name(self):
        """Test random name generation."""
        name1 = random_name()
        assert " " in name1  # Should have first and last name
        first, last = name1.split(" ")
        assert len(first) > 0
        assert len(last) > 0

    def test_generate_test_emails(self):
        """Test generating a list of test emails."""
        # Test with default parameters
        emails = generate_test_emails(count=5)
        assert len(emails) == 5
        assert all(isinstance(email, Email) for email in emails)
        assert all(email.folder == "INBOX" for email in emails)

        # Test with custom parameters
        emails = generate_test_emails(
            count=3,
            folder="Sent",
            sender="test@example.com",
            with_attachments=True
        )
        assert len(emails) == 3
        assert all(email.folder == "Sent" for email in emails)
        assert all(email.from_.address == "test@example.com" for email in emails)
        # At least one email should have attachments (not guaranteed due to randomization)
        has_attachments = any(len(email.attachments) > 0 for email in emails)
        assert has_attachments

    def test_parse_message_to_dict(self):
        """Test parsing an email message to a dictionary."""
        # Create a simple message
        msg = MIMEText("This is a test message")
        msg["Subject"] = "Test Subject"
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"
        
        parsed = parse_message_to_dict(msg)
        assert parsed["headers"]["Subject"] == "Test Subject"
        assert parsed["headers"]["From"] == "sender@example.com"
        assert parsed["headers"]["To"] == "recipient@example.com"
        assert parsed["content_type"] == "text/plain"
        assert parsed["body"] == "This is a test message"
        
        # Create a multipart message
        multipart_msg = MIMEMultipart()
        multipart_msg["Subject"] = "Multipart Test"
        multipart_msg["From"] = "sender@example.com"
        multipart_msg["To"] = "recipient@example.com"
        
        text_part = MIMEText("Plain text content")
        html_part = MIMEText("<p>HTML content</p>", "html")
        multipart_msg.attach(text_part)
        multipart_msg.attach(html_part)
        
        parsed = parse_message_to_dict(multipart_msg)
        assert parsed["headers"]["Subject"] == "Multipart Test"
        assert parsed["content_type"] == "multipart/mixed"
        assert "parts" in parsed
        assert len(parsed["parts"]) == 2
        assert parsed["parts"][0]["content_type"] == "text/plain"
        assert parsed["parts"][0]["body"] == "Plain text content"
        assert parsed["parts"][1]["content_type"] == "text/html"
        assert parsed["parts"][1]["body"] == "<p>HTML content</p>"

    def test_assert_email_equals(self):
        """Test asserting that two Email objects are equal."""
        email1 = Email(
            message_id="<test-123@example.com>",
            subject="Test Email",
            from_=EmailAddress(name="Test Sender", address="sender@example.com"),
            to=[EmailAddress(name="Test Recipient", address="recipient@example.com")],
            date=email.utils.parsedate_to_datetime("Thu, 01 Jan 2023 12:00:00 +0000"),
            folder="INBOX",
            uid=12345
        )
        
        # Create an identical email
        email2 = Email(
            message_id="<test-123@example.com>",
            subject="Test Email",
            from_=EmailAddress(name="Test Sender", address="sender@example.com"),
            to=[EmailAddress(name="Test Recipient", address="recipient@example.com")],
            date=email.utils.parsedate_to_datetime("Thu, 01 Jan 2023 12:00:00 +0000"),
            folder="INBOX",
            uid=12345
        )
        
        # This should not raise an assertion error
        assert_email_equals(email1, email2)
        
        # Create a different email
        email3 = Email(
            message_id="<test-456@example.com>",  # Different ID
            subject="Test Email",
            from_=EmailAddress(name="Test Sender", address="sender@example.com"),
            to=[EmailAddress(name="Test Recipient", address="recipient@example.com")],
            date=email.utils.parsedate_to_datetime("Thu, 01 Jan 2023 12:00:00 +0000"),
            folder="INBOX",
            uid=12345
        )
        
        # This should raise an assertion error
        with pytest.raises(AssertionError):
            assert_email_equals(email1, email3)

    def test_create_mock_folder_list(self):
        """Test creating a mock folder list."""
        folders = create_mock_folder_list()
        assert isinstance(folders, list)
        assert len(folders) > 0
        
        # Check structure
        for folder in folders:
            assert len(folder) == 3
            assert isinstance(folder[0], tuple)
            assert isinstance(folder[1], bytes)
            assert isinstance(folder[2], str)
        
        # Check for expected folders
        folder_names = [f[2] for f in folders]
        assert "INBOX" in folder_names
        assert "[Gmail]/Sent Mail" in folder_names
        assert "Projects/Alpha" in folder_names


class TestFixtures:
    """Test the pytest fixtures."""

    def test_mock_imap_client(self, mock_imap_client):
        """Test the mock IMAP client fixture."""
        assert mock_imap_client is not None
        
        # Test pre-configured responses
        folders = mock_imap_client.list_folders()
        assert len(folders) == 4
        assert folders[0][2] == "INBOX"
        
        exists_response = mock_imap_client.select_folder("INBOX")
        assert exists_response[b"EXISTS"] == 5
        
        search_response = mock_imap_client.search()
        assert search_response == [1, 2, 3, 4, 5]
        
        # Test modifying responses
        mock_imap_client.search.return_value = [10, 20, 30]
        assert mock_imap_client.search() == [10, 20, 30]

    def test_test_email_message_simple(self, test_email_message_simple):
        """Test the simple email message fixture."""
        assert test_email_message_simple is not None
        assert test_email_message_simple["Subject"] == "Simple Test Email"
        assert test_email_message_simple["From"] == "Test Sender <sender@example.com>"
        assert test_email_message_simple["To"] == "Test Recipient <recipient@example.com>"
        assert test_email_message_simple["Message-ID"] == "<simple-test-123@example.com>"
        assert not test_email_message_simple.is_multipart()
        assert test_email_message_simple.get_content_type() == "text/plain"

    def test_test_email_message_multipart(self, test_email_message_multipart):
        """Test the multipart email message fixture."""
        assert test_email_message_multipart is not None
        assert test_email_message_multipart["Subject"] == "Multipart Test Email"
        assert test_email_message_multipart.is_multipart()
        
        # Check parts
        parts = test_email_message_multipart.get_payload()
        assert len(parts) == 2
        assert parts[0].get_content_type() == "text/plain"
        assert parts[1].get_content_type() == "text/html"

    def test_test_email_message_with_attachment(self, test_email_message_with_attachment):
        """Test the email message with attachment fixture."""
        assert test_email_message_with_attachment is not None
        assert test_email_message_with_attachment["Subject"] == "Email with Attachment"
        assert test_email_message_with_attachment.is_multipart()
        
        # Check parts
        parts = test_email_message_with_attachment.get_payload()
        assert len(parts) == 2
        
        # Check attachment
        attachment_part = parts[1]
        assert attachment_part.get_content_type() == "application/octet-stream"
        disposition = attachment_part.get("Content-Disposition", "")
        assert "attachment" in disposition
        assert "test.txt" in disposition

    def test_test_email_message_encoded_headers(self, test_email_message_encoded_headers):
        """Test the email message with encoded headers fixture."""
        assert test_email_message_encoded_headers is not None
        
        # Headers should be encoded
        from_header = test_email_message_encoded_headers["From"]
        assert "=?utf-8?" in from_header or "john@example.com" in from_header
        
        to_header = test_email_message_encoded_headers["To"]
        assert "=?utf-8?" in to_header or "maria@example.com" in to_header
        
        subject_header = test_email_message_encoded_headers["Subject"]
        assert "=?utf-8?" in subject_header

    def test_make_test_email_message(self, make_test_email_message):
        """Test the factory fixture for creating email messages."""
        # Test with default parameters
        msg = make_test_email_message()
        assert msg["From"] == "Test Sender <sender@example.com>"
        assert msg["Subject"] == "Test Email"
        
        # Test with custom parameters
        custom_msg = make_test_email_message(
            from_addr="custom@example.com",
            from_name="Custom Sender",
            to_addrs=[("recipient1@example.com", "Recipient One"), 
                     ("recipient2@example.com", "Recipient Two")],
            cc_addrs=[("cc@example.com", "CC Person")],
            subject="Custom Subject",
            body_text="Custom body text",
            body_html="<p>Custom HTML</p>",
            attachments=[("test.txt", b"Text content", "text/plain")],
            headers={"X-Custom-Header": "Custom Value"}
        )
        
        assert custom_msg["From"] == "Custom Sender <custom@example.com>"
        assert custom_msg["To"] == "Recipient One <recipient1@example.com>, Recipient Two <recipient2@example.com>"
        assert custom_msg["Cc"] == "CC Person <cc@example.com>"
        assert custom_msg["Subject"] == "Custom Subject"
        assert custom_msg["X-Custom-Header"] == "Custom Value"
        assert custom_msg.is_multipart()
        
        # Check parts
        parts = custom_msg.get_payload()
        assert len(parts) == 3  # text, html, attachment
        assert parts[0].get_content_type() == "text/plain"
        assert parts[0].get_payload(decode=True).decode() == "Custom body text"
        assert parts[1].get_content_type() == "text/html"
        assert parts[1].get_payload(decode=True).decode() == "<p>Custom HTML</p>"
        assert "text/plain" in parts[2].get_content_type() or parts[2].get_content_type() == "application/octet-stream"
        assert "test.txt" in parts[2].get("Content-Disposition", "")

    def test_test_email_response_data(self, test_email_response_data):
        """Test the IMAP email response data fixture."""
        assert test_email_response_data is not None
        assert b"BODY[]" in test_email_response_data
        assert b"FLAGS" in test_email_response_data
        assert b"UID" in test_email_response_data
        assert test_email_response_data[b"UID"] == 12345
        assert b"\\Seen" in test_email_response_data[b"FLAGS"]
        
        # Body should contain email content
        body_data = test_email_response_data[b"BODY[]"]
        assert b"From: Test Sender <sender@example.com>" in body_data
        assert b"To: Test Recipient <recipient@example.com>" in body_data
        assert b"Subject: Test Email" in body_data
        assert b"This is a test email body." in body_data

    def test_make_test_email_response_data(self, make_test_email_response_data):
        """Test the factory fixture for creating IMAP response data."""
        # Test with default parameters
        data = make_test_email_response_data()
        assert data[b"UID"] == 12345
        assert b"\\Seen" in data[b"FLAGS"]
        
        # Test with custom parameters
        custom_data = make_test_email_response_data(
            uid=54321,
            flags=(b"\\Seen", b"\\Flagged"),
            internal_date="15-Mar-2023 08:30:00 +0000",
            headers={
                "From": "Custom <custom@example.com>",
                "Subject": "Custom Subject",
                "To": "recipient@example.com",
            },
            body_text="Custom body text"
        )
        
        assert custom_data[b"UID"] == 54321
        assert b"\\Seen" in custom_data[b"FLAGS"]
        assert b"\\Flagged" in custom_data[b"FLAGS"]
        assert custom_data[b"INTERNALDATE"] == "15-Mar-2023 08:30:00 +0000"
        
        # Body should contain custom content
        body_data = custom_data[b"BODY[]"]
        assert b"From: Custom <custom@example.com>" in body_data
        assert b"Subject: Custom Subject" in body_data
        assert b"Custom body text" in body_data

    def test_test_email_model(self, test_email_model):
        """Test the Email model fixture."""
        assert test_email_model is not None
        assert test_email_model.message_id == "<test-123@example.com>"
        assert test_email_model.subject == "Test Email"
        assert test_email_model.from_.name == "Test Sender"
        assert test_email_model.from_.address == "sender@example.com"
        assert len(test_email_model.to) == 1
        assert test_email_model.to[0].name == "Test Recipient"
        assert test_email_model.to[0].address == "recipient@example.com"
        assert test_email_model.folder == "INBOX"
        assert test_email_model.uid == 12345

    def test_configure_test_env(self, configure_test_env):
        """Test the environment configuration fixture."""
        assert "IMAP_SERVER" in os.environ
        assert os.environ["IMAP_SERVER"] == "imap.example.com"
        assert os.environ["IMAP_PORT"] == "993"
        assert os.environ["IMAP_USERNAME"] == "test@example.com"
        assert os.environ["IMAP_PASSWORD"] == "test_password"
        assert os.environ["MCP_SERVER_PORT"] == "3000"