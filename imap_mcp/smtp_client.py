"""SMTP client implementation for sending emails."""

import email.utils
import logging
from datetime import datetime
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from imap_mcp.models import Email, EmailAddress

logger = logging.getLogger(__name__)


def create_reply_mime(
    original_email: Email,
    reply_to: EmailAddress,
    body: str,
    subject: Optional[str] = None,
    cc: Optional[List[EmailAddress]] = None,
    reply_all: bool = False,
    html_body: Optional[str] = None,
) -> EmailMessage:
    """Create a MIME message for replying to an email.
    
    Args:
        original_email: Original email to reply to
        reply_to: Address to send the reply from
        body: Plain text body of the reply
        subject: Subject for the reply (default: prepend "Re: " to original)
        cc: List of CC recipients (default: none)
        reply_all: Whether to reply to all recipients (default: False)
        html_body: Optional HTML version of the body
        
    Returns:
        MIME message ready for sending
    """
    # Start with a multipart/mixed message
    if html_body:
        message = MIMEMultipart("mixed")
    else:
        message = EmailMessage()
    
    # Set the From header
    message["From"] = str(reply_to)
    
    # Set the To header
    to_recipients = [original_email.from_]
    if reply_all and original_email.to:
        # Add original recipients excluding the sender
        to_recipients.extend([
            recipient for recipient in original_email.to 
            if recipient.address != reply_to.address
        ])
    
    message["To"] = ", ".join(str(recipient) for recipient in to_recipients)
    
    # Set the CC header if applicable
    cc_recipients = []
    if cc:
        cc_recipients.extend(cc)
    elif reply_all and original_email.cc:
        cc_recipients.extend([
            recipient for recipient in original_email.cc 
            if recipient.address != reply_to.address
        ])
    
    if cc_recipients:
        message["Cc"] = ", ".join(str(recipient) for recipient in cc_recipients)
    
    # Set the subject
    if subject:
        message["Subject"] = subject
    else:
        # Add "Re: " prefix if not already present
        original_subject = original_email.subject
        if not original_subject.startswith("Re:"):
            message["Subject"] = f"Re: {original_subject}"
        else:
            message["Subject"] = original_subject
    
    # Set references for threading
    references = []
    if "References" in original_email.headers:
        references.append(original_email.headers["References"])
    if original_email.message_id:
        references.append(original_email.message_id)
    
    if references:
        message["References"] = " ".join(references)
    
    # Set In-Reply-To header
    if original_email.message_id:
        message["In-Reply-To"] = original_email.message_id
    
    # Prepare content
    if html_body:
        # Create multipart/alternative for text and HTML
        alternative = MIMEMultipart("alternative")
        
        # Add plain text part
        plain_text = body
        if original_email.content.text:
            # Quote original plain text
            quoted_original = "\n".join(f"> {line}" for line in original_email.content.text.split("\n"))
            plain_text += f"\n\nOn {email.utils.format_datetime(original_email.date or datetime.now())}, {original_email.from_} wrote:\n{quoted_original}"
        
        text_part = MIMEText(plain_text, "plain", "utf-8")
        alternative.attach(text_part)
        
        # Add HTML part
        html_content = html_body
        if original_email.content.html:
            # Add original HTML with a divider
            html_content += (
                f'\n<div style="border-top: 1px solid #ccc; margin-top: 20px; padding-top: 10px;">'
                f'\n<p>On {email.utils.format_datetime(original_email.date or datetime.now())}, {original_email.from_} wrote:</p>'
                f'\n<blockquote style="margin: 0 0 0 .8ex; border-left: 1px solid #ccc; padding-left: 1ex;">'
                f'\n{original_email.content.html}'
                f'\n</blockquote>'
                f'\n</div>'
            )
        else:
            # Convert plain text to HTML for quoting
            original_text = original_email.content.get_best_content()
            if original_text:
                escaped_text = original_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                escaped_text = escaped_text.replace("\n", "<br>")
                html_content += (
                    f'\n<div style="border-top: 1px solid #ccc; margin-top: 20px; padding-top: 10px;">'
                    f'\n<p>On {email.utils.format_datetime(original_email.date or datetime.now())}, {original_email.from_} wrote:</p>'
                    f'\n<blockquote style="margin: 0 0 0 .8ex; border-left: 1px solid #ccc; padding-left: 1ex;">'
                    f'\n{escaped_text}'
                    f'\n</blockquote>'
                    f'\n</div>'
                )
        
        html_part = MIMEText(html_content, "html", "utf-8")
        alternative.attach(html_part)
        
        # Attach the alternative part to the message
        message.attach(alternative)
    else:
        # Plain text only
        plain_text = body
        if original_email.content.text:
            # Quote original plain text
            quoted_original = "\n".join(f"> {line}" for line in original_email.content.text.split("\n"))
            plain_text += f"\n\nOn {email.utils.format_datetime(original_email.date or datetime.now())}, {original_email.from_} wrote:\n{quoted_original}"
        
        message.set_content(plain_text)
    
    # Add Date header
    message["Date"] = email.utils.formatdate(localtime=True)
    
    return message
