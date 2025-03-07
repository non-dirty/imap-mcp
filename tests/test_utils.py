"""Testing utilities for IMAP MCP."""

import email
import random
import string
from datetime import datetime, timedelta
from email.message import Message
from typing import Dict, List, Optional, Tuple, Union

from imap_mcp.models import Email, EmailAddress, EmailContent, EmailAttachment


def random_string(length: int = 10) -> str:
    """Generate a random string of fixed length."""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))


def random_email_address() -> str:
    """Generate a random email address."""
    username = random_string(8)
    domain = random_string(6) + ".com"
    return f"{username}@{domain}"


def random_name() -> str:
    """Generate a random person name."""
    first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", 
                  "Edward", "Fiona", "George", "Hannah"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", 
                 "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    return f"{random.choice(first_names)} {random.choice(last_names)}"


def generate_test_emails(
    count: int = 10, 
    start_date: Optional[datetime] = None,
    folder: str = "INBOX",
    sender: Optional[str] = None,
    with_attachments: bool = False
) -> List[Email]:
    """Generate a list of test email objects.
    
    Args:
        count: Number of emails to generate
        start_date: Starting date for emails (newest). If None, uses current date.
        folder: Folder to assign to emails
        sender: Optional specific sender email address
        with_attachments: Whether to include attachments
        
    Returns:
        List of Email objects sorted by date (newest first)
    """
    emails = []
    
    if start_date is None:
        start_date = datetime.now()
    
    for i in range(count):
        # Generate from address
        if sender:
            from_address = sender
            from_name = sender.split('@')[0].title()
        else:
            from_address = random_email_address()
            from_name = random_name()
        
        # Generate subject with some variety
        subjects = [
            f"Meeting scheduled for {(start_date - timedelta(days=i)).strftime('%Y-%m-%d')}",
            f"Important update about project {random_string(5).upper()}",
            f"Invitation: Team event on {(start_date - timedelta(days=i+10)).strftime('%Y-%m-%d')}",
            f"Reminder: Deadline approaching for {random_string(8)}",
            f"Follow-up on our conversation about {random_string(6)}",
            f"Weekly report: {(start_date - timedelta(days=i)).strftime('%B %d')} update",
        ]
        
        subject = random.choice(subjects)
        
        # Generate content with some variety
        contents = [
            f"Hello,\n\nThis is email {i+1} of test email generation. "
            f"It was generated on {(start_date - timedelta(days=i)).strftime('%Y-%m-%d')}.\n\n"
            f"Please review the attached documents.\n\nRegards,\n{from_name}",
            
            f"Hi team,\n\nI wanted to update you on the progress of project {random_string(5).upper()}. "
            f"We've completed {random.randint(10, 90)}% of the tasks.\n\n"
            f"Let's discuss this in our next meeting.\n\nBest,\n{from_name}",
            
            f"Hello,\n\nThis is a reminder about the upcoming deadline on "
            f"{(start_date - timedelta(days=i+5)).strftime('%Y-%m-%d')}.\n\n"
            f"Please submit your reports by end of day.\n\nThanks,\n{from_name}",
        ]
        
        content_text = random.choice(contents)
        content_html = f"<html><body><p>{content_text.replace('\n\n', '</p><p>')}</p></body></html>"
        
        # Create email object
        email_obj = Email(
            message_id=f"<test-{random_string(8)}@example.com>",
            subject=subject,
            from_=EmailAddress(name=from_name, address=from_address),
            to=[EmailAddress(name=random_name(), address=random_email_address()) for _ in range(random.randint(1, 3))],
            cc=[EmailAddress(name=random_name(), address=random_email_address()) for _ in range(random.randint(0, 2))],
            date=start_date - timedelta(days=i),
            content=EmailContent(text=content_text, html=content_html),
            folder=folder,
            uid=10000 + i,
            flags=[b"\\Seen"] if random.random() > 0.3 else []
        )
        
        # Add attachments if requested
        if with_attachments and random.random() > 0.5:
            attachment_count = random.randint(1, 3)
            attachment_types = [
                ("pdf", "application/pdf"),
                ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("jpg", "image/jpeg"),
                ("png", "image/png"),
                ("txt", "text/plain"),
            ]
            
            for j in range(attachment_count):
                att_type = random.choice(attachment_types)
                email_obj.attachments.append(
                    EmailAttachment(
                        filename=f"attachment-{j+1}.{att_type[0]}",
                        content_type=att_type[1],
                        size=random.randint(1000, 1000000),
                        content=b"Sample attachment content"
                    )
                )
        
        emails.append(email_obj)
    
    return emails


def parse_message_to_dict(message: Message) -> Dict:
    """Parse an email.message.Message into a simple dictionary."""
    result = {
        "headers": {k: v for k, v in message.items()},
        "content_type": message.get_content_type(),
    }
    
    if message.is_multipart():
        result["parts"] = []
        for part in message.get_payload():
            result["parts"].append(parse_message_to_dict(part))
    else:
        result["body"] = message.get_payload(decode=True).decode(
            message.get_content_charset() or "utf-8", errors="replace")
    
    return result


def assert_email_equals(email1: Email, email2: Email):
    """Assert that two Email objects are equal in relevant properties."""
    assert email1.message_id == email2.message_id
    assert email1.subject == email2.subject
    assert str(email1.from_) == str(email2.from_)
    assert len(email1.to) == len(email2.to)
    for i in range(len(email1.to)):
        assert str(email1.to[i]) == str(email2.to[i])
    assert email1.date == email2.date
    assert email1.uid == email2.uid
    assert email1.folder == email2.folder


def create_mock_folder_list() -> List[Tuple[Tuple[bytes, ...], bytes, str]]:
    """Create a mock folder list as returned by IMAPClient.list_folders()."""
    return [
        ((b"\\HasNoChildren",), b"/", "INBOX"),
        ((b"\\HasChildren", b"\\Noselect"), b"/", "[Gmail]"),
        ((b"\\HasNoChildren", b"\\All"), b"/", "[Gmail]/All Mail"),
        ((b"\\HasNoChildren", b"\\Drafts"), b"/", "[Gmail]/Drafts"),
        ((b"\\HasNoChildren", b"\\Important"), b"/", "[Gmail]/Important"),
        ((b"\\HasNoChildren", b"\\Sent"), b"/", "[Gmail]/Sent Mail"),
        ((b"\\HasNoChildren", b"\\Junk"), b"/", "[Gmail]/Spam"),
        ((b"\\HasNoChildren", b"\\Flagged"), b"/", "[Gmail]/Starred"),
        ((b"\\HasNoChildren", b"\\Trash"), b"/", "[Gmail]/Trash"),
        ((b"\\HasNoChildren",), b"/", "Archive"),
        ((b"\\HasNoChildren",), b"/", "Work"),
        ((b"\\HasChildren",), b"/", "Projects"),
        ((b"\\HasNoChildren",), b"/", "Projects/Alpha"),
        ((b"\\HasNoChildren",), b"/", "Projects/Beta"),
    ]