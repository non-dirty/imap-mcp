"""SMTP client implementation for email composition and sending."""

import email
import logging
import re
import smtplib
from datetime import datetime
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Set, Union

from imap_mcp.models import Email, EmailAddress

logger = logging.getLogger(__name__)


class SmtpClient:
    """Client for SMTP operations."""
    
    def __init__(self, user_email, smtp_host=None, smtp_port=587, use_tls=True):
        """Initialize SMTP client.
        
        Args:
            user_email: User's email address
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            use_tls: Whether to use TLS
        """
        self.user_email = user_email
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.use_tls = use_tls
        self.connected = False
        self.client = None
    
    def create_reply_mime(
        self, 
        original_email: Email, 
        body_text: str, 
        reply_all: bool = False, 
        cc: Optional[List[str]] = None,
        body_html: Optional[str] = None
    ) -> Message:
        """Create a properly formatted MIME message for an email reply.
        
        This method constructs a new email as a reply to the original email with proper
        headers (In-Reply-To, References, Subject with "Re:" prefix) and formatting
        (quoted original message).
        
        The reply can be either to the original sender only (default) or to all recipients
        (reply_all=True). Additional CC recipients can be specified with the cc parameter.
        
        The user's own email address is automatically excluded from the recipients.
        
        HTML Support:
        If body_html is provided, the method creates a multipart/alternative message
        with both plain text and HTML versions, allowing email clients to display
        the most appropriate version. The HTML version should contain the full reply
        content including any quoted text.
        
        Example:
            ```python
            # Fetch an email to reply to
            original = imap_client.fetch_email(uid, folder)
            
            # Create a plain text reply
            reply_body = "Thank you for your message. I will respond shortly."
            mime_message = smtp_client.create_reply_mime(original, reply_body)
            
            # Create a reply with both plain text and HTML
            reply_html = "<p>Thank you for your message.</p><p>I will respond shortly.</p>"
            mime_message = smtp_client.create_reply_mime(
                original, reply_body, body_html=reply_html
            )
            
            # Create a reply-all with additional CC recipients
            cc_list = ["supervisor@example.com"]
            mime_message = smtp_client.create_reply_mime(
                original, reply_body, reply_all=True, cc=cc_list
            )
            ```
        
        Args:
            original_email: The original Email object to reply to
            body_text: The new message text for the reply (plain text)
            reply_all: If True, include all original recipients in To/Cc fields.
                       If False (default), reply only to the original sender.
            cc: Optional list of additional email addresses to CC
            body_html: Optional HTML version of the reply body. If provided,
                       the email will include both plain text and HTML versions.
            
        Returns:
            email.message.Message: A properly formatted MIME message ready for sending
            or saving as a draft
        """
        # Create a new message
        mime_message = MIMEMultipart('related')
        
        # Set From field to the user's email
        mime_message['From'] = self.user_email
        
        # Determine To and Cc recipients
        to_addrs = []
        cc_addrs = []
        
        # Always add the original sender to the To field
        if original_email.from_:
            to_addrs.append(str(original_email.from_))
        
        # If reply_all, add other recipients from To and Cc fields
        if reply_all:
            # Add original To recipients (except ourselves)
            if original_email.to:
                for addr in original_email.to:
                    if addr.address.lower() != self.user_email.lower() and str(addr) not in to_addrs:
                        to_addrs.append(str(addr))
            
            # Add original Cc recipients (except ourselves)
            if original_email.cc:
                for addr in original_email.cc:
                    if addr.address.lower() != self.user_email.lower() and str(addr) not in to_addrs:
                        cc_addrs.append(str(addr))
        
        # Add explicit CC addresses
        if cc:
            for addr in cc:
                if addr.lower() != self.user_email.lower() and addr not in to_addrs and addr not in cc_addrs:
                    cc_addrs.append(addr)
        
        # Set the headers
        mime_message['To'] = ', '.join(to_addrs)
        if cc_addrs:
            mime_message['Cc'] = ', '.join(cc_addrs)
        
        # Set the subject (add Re: if not already present)
        subject = original_email.subject or ""
        if not subject.lower().startswith('re:'):
            subject = f"Re: {subject}"
        mime_message['Subject'] = subject
        
        # Set In-Reply-To header if original has Message-ID
        if original_email.message_id:
            mime_message['In-Reply-To'] = original_email.message_id
        
        # Set References header (append original Message-ID to existing References)
        references = []
        if original_email.references:
            references.extend(original_email.references)
        if original_email.message_id and original_email.message_id not in references:
            references.append(original_email.message_id)
        
        if references:
            mime_message['References'] = ' '.join(references)
        
        # Create the attribution line
        date_str = original_email.date.strftime('%Y-%m-%d %H:%M:%S') if original_email.date else "unknown date"
        from_str = str(original_email.from_) if original_email.from_ else "unknown sender"
        attribution = f"On {date_str}, {from_str} wrote:\n\n"
        
        # Quote the original message (prefix each line with ">")
        original_text = original_email.content.text or ""
        quoted_body = '\n'.join([f"> {line}" for line in original_text.split('\n')])
        
        # Full text of the reply with attribution and quoted text
        full_body_text = f"{body_text}\n\n{attribution}{quoted_body}"
        
        # Handle HTML if provided
        if body_html:
            # Create a multipart/alternative container
            msg_alternative = MIMEMultipart('alternative')
            mime_message.attach(msg_alternative)
            
            # Attach the plain text version
            plain_part = MIMEText(full_body_text, 'plain')
            msg_alternative.attach(plain_part)
            
            # Create HTML attribution and quoting
            html_attribution = f"<p>On {date_str}, {from_str} wrote:</p>"
            
            # Quote original in HTML format
            original_html = original_email.content.html or original_email.content.text or ""
            quoted_html = f"<blockquote style='border-left: 1px solid #ccc; margin-left: 10px; padding-left: 10px;'>{original_html}</blockquote>"
            
            # Combine the HTML reply with attribution and quoted content
            full_html = f"{body_html}\n\n{html_attribution}\n{quoted_html}"
            
            # Attach the HTML version
            html_part = MIMEText(full_html, 'html')
            msg_alternative.attach(html_part)
        else:
            # Plain text only
            text_part = MIMEText(full_body_text, 'plain')
            mime_message.attach(text_part)
        
        return mime_message
    
    def connect(self) -> bool:
        """Connect to SMTP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        # Implementation
        pass
    
    def send_email(self, message: Message) -> bool:
        """Send an email message.
        
        Args:
            message: Email message to send
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Implementation
        pass
    
    def close(self) -> None:
        """Close the SMTP connection."""
        # Implementation
        pass
