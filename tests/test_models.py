"""Tests for email models."""

import email
import unittest
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from imap_mcp.models import Email, EmailAddress, decode_mime_header


class TestModels(unittest.TestCase):
    """Test cases for email models."""
    
    def test_decode_mime_header(self):
        """Test MIME header decoding."""
        # Test ASCII header
        self.assertEqual(decode_mime_header("Hello"), "Hello")
        
        # Test encoded header
        encoded_header = Header("Héllö Wörld", "utf-8").encode()
        self.assertEqual(decode_mime_header(encoded_header), "Héllö Wörld")
        
        # Test empty header
        self.assertEqual(decode_mime_header(None), "")
        self.assertEqual(decode_mime_header(""), "")
    
    def test_email_address_parse(self):
        """Test email address parsing."""
        # Test name + address
        addr = EmailAddress.parse("John Doe <john@example.com>")
        self.assertEqual(addr.name, "John Doe")
        self.assertEqual(addr.address, "john@example.com")
        
        # Test quoted name
        addr = EmailAddress.parse('"Smith, John" <john@example.com>')
        self.assertEqual(addr.name, "Smith, John")
        self.assertEqual(addr.address, "john@example.com")
        
        # Test address only
        addr = EmailAddress.parse("jane@example.com")
        self.assertEqual(addr.name, "")
        self.assertEqual(addr.address, "jane@example.com")
        
        # Test string conversion
        addr = EmailAddress("Jane Smith", "jane@example.com")
        self.assertEqual(str(addr), "Jane Smith <jane@example.com>")
        addr = EmailAddress("", "jane@example.com")
        self.assertEqual(str(addr), "jane@example.com")
    
    def test_email_from_message(self):
        """Test creating email from message."""
        # Create a multipart email
        msg = MIMEMultipart()
        msg["From"] = "John Doe <john@example.com>"
        msg["To"] = "Jane Smith <jane@example.com>, bob@example.com"
        msg["Subject"] = "Test Email"
        msg["Message-ID"] = "<test123@example.com>"
        msg["Date"] = email.utils.formatdate()
        
        # Add plain text part
        text_part = MIMEText("Hello, this is a test email.", "plain")
        msg.attach(text_part)
        
        # Add HTML part
        html_part = MIMEText("<p>Hello, this is a <b>test</b> email.</p>", "html")
        msg.attach(html_part)
        
        # Parse email
        email_obj = Email.from_message(msg, uid=1234, folder="INBOX")
        
        # Check basic fields
        self.assertEqual(email_obj.message_id, "<test123@example.com>")
        self.assertEqual(email_obj.subject, "Test Email")
        self.assertEqual(str(email_obj.from_), "John Doe <john@example.com>")
        self.assertEqual(len(email_obj.to), 2)
        self.assertEqual(str(email_obj.to[0]), "Jane Smith <jane@example.com>")
        self.assertEqual(str(email_obj.to[1]), "bob@example.com")
        self.assertEqual(email_obj.folder, "INBOX")
        self.assertEqual(email_obj.uid, 1234)
        
        # Check content
        self.assertEqual(email_obj.content.text, "Hello, this is a test email.")
        self.assertEqual(
            email_obj.content.html, "<p>Hello, this is a <b>test</b> email.</p>"
        )
        
        # Check summary
        summary = email_obj.summary()
        self.assertIn("From: John Doe <john@example.com>", summary)
        self.assertIn("Subject: Test Email", summary)


if __name__ == "__main__":
    unittest.main()
