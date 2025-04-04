"""Data models for email handling."""

import email
import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from email.header import decode_header
from email.message import Message
from typing import Dict, List, Optional


def decode_mime_header(header_value: Optional[str]) -> str:
    """Decode a MIME header value.
    
    Args:
        header_value: MIME header value
        
    Returns:
        Decoded header value
    """
    if not header_value:
        return ""
    
    decoded_parts = []
    for part, encoding in decode_header(header_value):
        if isinstance(part, bytes):
            if encoding:
                try:
                    decoded_parts.append(part.decode(encoding))
                except LookupError:
                    # If the encoding is not recognized, try with utf-8
                    decoded_parts.append(part.decode("utf-8", errors="replace"))
            else:
                decoded_parts.append(part.decode("utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    
    return "".join(decoded_parts)


@dataclass
class EmailAddress:
    """Email address representation."""
    
    name: str
    address: str
    
    @classmethod
    def parse(cls, address_str: str) -> "EmailAddress":
        """Parse email address string.
        
        Args:
            address_str: Email address string (e.g., "John Doe <john@example.com>")
            
        Returns:
            EmailAddress object
        """
        # For the special case of just an email address without brackets
        if '@' in address_str and '<' not in address_str:
            return cls(name="", address=address_str.strip())
            
        # Extract name and address with angle brackets
        match = re.match(r'"?([^"<]*)"?\s*<([^>]*)>', address_str.strip())
        if match:
            name, address = match.groups()
            return cls(name=name.strip(), address=address.strip())
            
        # Fallback: treat the whole string as an address
        return cls(name="", address=address_str.strip())
    
    def __str__(self) -> str:
        """Return string representation."""
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address


@dataclass
class EmailAttachment:
    """Email attachment representation."""
    
    filename: str
    content_type: str
    size: int
    content_id: Optional[str] = None
    content: Optional[bytes] = None
    
    @classmethod
    def from_part(cls, part: Message) -> "EmailAttachment":
        """Create attachment from email part.
        
        Args:
            part: Email message part
            
        Returns:
            EmailAttachment object
        """
        filename = part.get_filename()
        if not filename:
            # Generate a filename based on content type
            ext = part.get_content_type().split("/")[-1]
            filename = f"attachment.{ext}"
        
        content = part.get_payload(decode=True)
        content_type = part.get_content_type()
        
        # Extract Content-ID properly, removing angle brackets if present
        content_id = part.get("Content-ID")
        if content_id:
            content_id = content_id.strip("<>")
        
        # If there's no Content-ID but there is a Content-Disposition with filename,
        # the attachment might be referenced in HTML via the filename
        if not content_id and filename:
            cdisp = part.get("Content-Disposition", "")
            if "inline" in cdisp and filename:
                # Some clients use the filename as a reference
                content_id = filename
        
        return cls(
            filename=decode_mime_header(filename),
            content_type=content_type,
            size=len(content) if content else 0,
            content_id=content_id,
            content=content,
        )


@dataclass
class EmailContent:
    """Email content representation."""
    
    text: Optional[str] = None
    html: Optional[str] = None
    
    def get_best_content(self) -> str:
        """Return the best available content."""
        if self.text:
            return self.text
        if self.html:
            # Convert HTML to plain text (simple approach)
            text = re.sub(r"<[^>]*>", "", self.html)
            return html.unescape(text)
        return ""


@dataclass
class Email:
    """Email message representation."""
    
    message_id: str
    subject: str
    from_: EmailAddress
    to: List[EmailAddress]
    cc: List[EmailAddress] = field(default_factory=list)
    bcc: List[EmailAddress] = field(default_factory=list)
    date: Optional[datetime] = None
    content: EmailContent = field(default_factory=EmailContent)
    attachments: List[EmailAttachment] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    folder: Optional[str] = None
    uid: Optional[int] = None
    in_reply_to: Optional[str] = None
    references: List[str] = field(default_factory=list)
    
    @classmethod
    def from_message(
        cls, message: Message, uid: Optional[int] = None, folder: Optional[str] = None
    ) -> "Email":
        """Create email from email.message.Message.
        
        Args:
            message: Email message
            uid: IMAP UID
            folder: IMAP folder
            
        Returns:
            Email object
        """
        # Parse headers
        subject = decode_mime_header(message.get("Subject", ""))
        from_str = decode_mime_header(message.get("From", ""))
        to_str = decode_mime_header(message.get("To", ""))
        cc_str = decode_mime_header(message.get("Cc", ""))
        bcc_str = decode_mime_header(message.get("Bcc", ""))
        date_str = message.get("Date")
        message_id = message.get("Message-ID", "")
        if message_id:
            message_id = message_id.strip()
        
        # Get thread-related headers
        in_reply_to = message.get("In-Reply-To", "")
        if in_reply_to:
            in_reply_to = in_reply_to.strip()
        
        references_str = message.get("References", "")
        references = []
        if references_str:
            # Extract all message IDs from References header
            references = [ref.strip() for ref in re.findall(r'<[^>]+>', references_str)]
        
        # Parse addresses
        from_ = EmailAddress.parse(from_str)
        to = [EmailAddress.parse(addr.strip()) for addr in to_str.split(",") if addr.strip()]
        cc = [EmailAddress.parse(addr.strip()) for addr in cc_str.split(",") if addr.strip()]
        bcc = [EmailAddress.parse(addr.strip()) for addr in bcc_str.split(",") if addr.strip()]
        
        # Parse date
        date = None
        if date_str:
            try:
                date = email.utils.parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                pass
        
        # Build headers dictionary
        headers = {}
        for name, value in message.items():
            headers[name] = decode_mime_header(value)
        
        # Parse content and attachments
        content = EmailContent()
        attachments = []
        
        # Process the email body
        if message.is_multipart():
            # Create a recursive function to handle nested multipart messages
            def process_part(part, content, attachments):
                if part.is_multipart():
                    # Recursively process each subpart
                    for subpart in part.get_payload():
                        process_part(subpart, content, attachments)
                else:
                    content_type = part.get_content_type()
                    content_disposition = part.get("Content-Disposition", "")
                    
                    # Handle attachments (both explicit and inline)
                    if ("attachment" in content_disposition or 
                        "inline" in content_disposition or
                        content_type.startswith("image/") or
                        content_type.startswith("application/") or
                        "name=" in part.get("Content-Type", "")):
                        
                        attachments.append(EmailAttachment.from_part(part))
                    # Handle text content
                    elif content_type == "text/plain":
                        # Only replace existing text if it's empty
                        if not content.text:
                            try:
                                charset = part.get_content_charset() or "utf-8"
                                text = part.get_payload(decode=True).decode(charset, errors="replace")
                                content.text = text
                            except Exception as e:
                                content.text = f"[Error decoding plain text content: {e}]"
                    # Handle HTML content
                    elif content_type == "text/html":
                        # Only replace existing HTML if it's empty
                        if not content.html:
                            try:
                                charset = part.get_content_charset() or "utf-8"
                                html_content = part.get_payload(decode=True).decode(charset, errors="replace")
                                content.html = html_content
                            except Exception as e:
                                content.html = f"[Error decoding HTML content: {e}]"
            
            # Start processing parts
            process_part(message, content, attachments)
        else:
            # Single part message
            content_type = message.get_content_type()
            
            if content_type == "text/plain":
                try:
                    charset = message.get_content_charset() or "utf-8"
                    content.text = message.get_payload(decode=True).decode(charset, errors="replace")
                except Exception as e:
                    content.text = f"[Error decoding plain text content: {e}]"
            elif content_type == "text/html":
                try:
                    charset = message.get_content_charset() or "utf-8"
                    content.html = message.get_payload(decode=True).decode(charset, errors="replace")
                except Exception as e:
                    content.html = f"[Error decoding HTML content: {e}]"
            else:
                # If not plain text or HTML, treat as attachment
                attachments.append(EmailAttachment.from_part(message))
        
        return cls(
            message_id=message_id,
            subject=subject,
            from_=from_,
            to=to,
            cc=cc,
            bcc=bcc,
            date=date,
            content=content,
            attachments=attachments,
            headers=headers,
            folder=folder,
            uid=uid,
            in_reply_to=in_reply_to,
            references=references,
        )
    
    def summary(self) -> str:
        """Return a summary of the email."""
        date_str = f"{self.date:%Y-%m-%d %H:%M:%S}" if self.date else "Unknown date"
        thread_info = ""
        if self.in_reply_to or self.references:
            thread_info = "\nThread: " + (
                f"Reply to {self.in_reply_to}" if self.in_reply_to else 
                f"References {len(self.references)} previous messages"
            )
        
        return (
            f"From: {self.from_}\n"
            f"To: {', '.join(str(a) for a in self.to)}\n"
            f"Date: {date_str}\n"
            f"Subject: {self.subject}\n"
            f"Attachments: {len(self.attachments)}"
            f"{thread_info}"
        )
