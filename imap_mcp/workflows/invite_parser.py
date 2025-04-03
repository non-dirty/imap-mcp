"""Meeting invite identification and parsing logic."""

import logging
import re
from datetime import datetime
from typing import Dict, Optional, Any, List, Tuple

from imap_mcp.models import Email, EmailAttachment

logger = logging.getLogger(__name__)


def identify_meeting_invite_details(email_obj: Email) -> Dict[str, Any]:
    """Identify and extract meeting invite details from an email.
    
    Args:
        email_obj: Email object to analyze
        
    Returns:
        Dictionary with keys:
            - is_invite: True if the email is a meeting invite, False otherwise
            - details: Dictionary with meeting details (if is_invite is True)
                - subject: Meeting subject/title
                - start_time: Meeting start time (datetime object)
                - end_time: Meeting end time (datetime object)
                - organizer: Meeting organizer
                - location: Meeting location/venue/link
                - description: Meeting description/body
    """
    # Initialize result
    result = {
        "is_invite": False,
        "details": {}
    }
    
    # Check if this looks like a meeting invite
    if _is_meeting_invite(email_obj):
        result["is_invite"] = True
        result["details"] = _extract_meeting_details(email_obj)
        logger.debug(f"Identified email as meeting invite: {email_obj.subject}")
    
    return result


def _is_meeting_invite(email_obj: Email) -> bool:
    """Check if an email is a meeting invite.
    
    Uses multiple heuristics:
    - Subject line keywords
    - Presence of .ics attachment
    - Calendar method headers
    - Content keywords
    
    Args:
        email_obj: Email object to analyze
        
    Returns:
        True if the email appears to be a meeting invite, False otherwise
    """
    # Check subject line for invite-related keywords
    invite_subject_patterns = [
        r"invitation",
        r"meeting",
        r"invite",
        r"calendar",
        r"appointment",
        r"event",
        r"scheduled",
    ]
    
    subject_lower = email_obj.subject.lower()
    for pattern in invite_subject_patterns:
        if re.search(pattern, subject_lower):
            logger.debug(f"Subject match for invite pattern: {pattern}")
            return True
    
    # Check for .ics attachments
    for attachment in email_obj.attachments:
        if attachment.filename.lower().endswith(".ics") or attachment.content_type == "text/calendar":
            logger.debug("Found calendar attachment")
            return True
    
    # Check for calendar method headers
    if email_obj.headers.get("Method", "").upper() == "REQUEST" or email_obj.headers.get("Content-Type", "").lower().find("method=request") != -1:
        logger.debug("Found calendar method headers")
        return True
    
    # Check email content for invite-related patterns
    content_text = ""
    if email_obj.content.text:
        content_text = email_obj.content.text.lower()
    elif email_obj.content.html:
        # Strip HTML tags for simple text analysis
        content_text = re.sub(r'<[^>]*>', '', email_obj.content.html).lower()
    
    invite_content_patterns = [
        r"has invited you to",
        r"invitation[:\s]+",
        r"when:.*\d{1,2}[:/]\d{1,2}",
        r"date:.*\d{1,2}[:/]\d{1,2}",
        r"location:.*",
        r"join (the )?meeting",
        r"accept\s*\|\s*decline",
    ]
    
    for pattern in invite_content_patterns:
        if re.search(pattern, content_text):
            logger.debug(f"Content match for invite pattern: {pattern}")
            return True
    
    # Not identified as a meeting invite
    return False


def _extract_meeting_details(email_obj: Email) -> Dict[str, Any]:
    """Extract meeting details from an invite email.
    
    Args:
        email_obj: Email object identified as a meeting invite
        
    Returns:
        Dictionary with meeting details
    """
    details = {
        "subject": _extract_meeting_subject(email_obj),
        "organizer": _extract_organizer(email_obj),
        "location": _extract_location(email_obj),
        "description": _extract_description(email_obj),
    }
    
    # Extract start and end times
    start_time, end_time = _extract_meeting_times(email_obj)
    details["start_time"] = start_time
    details["end_time"] = end_time
    
    return details


def _extract_meeting_subject(email_obj: Email) -> str:
    """Extract meeting subject from invite email.
    
    Args:
        email_obj: Email object identified as a meeting invite
        
    Returns:
        Meeting subject/title
    """
    # Use email subject as the default meeting subject
    subject = email_obj.subject
    
    # Remove prefixes like "Invitation:", "Meeting:", etc.
    prefixes = [
        r"^invitation:\s*",
        r"^meeting:\s*",
        r"^invite:\s*",
        r"^event:\s*",
        r"^calendar:\s*",
        r"^meeting invitation:\s*",  
    ]
    
    for prefix in prefixes:
        subject = re.sub(prefix, "", subject, flags=re.IGNORECASE)
    
    return subject.strip()


def _extract_meeting_times(email_obj: Email) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Extract meeting start and end times from invite email.
    
    Args:
        email_obj: Email object identified as a meeting invite
        
    Returns:
        Tuple of (start_time, end_time) as datetime objects, or None if not found
    """
    start_time = None
    end_time = None
    
    # First check if we have a date in the email to use as a fallback
    default_date = email_obj.date
    
    # Check email text content for time patterns
    content_text = ""
    if email_obj.content.text:
        content_text = email_obj.content.text
    elif email_obj.content.html:
        # Strip HTML tags
        content_text = re.sub(r'<[^>]*>', '', email_obj.content.html)
    
    # Look for common date and time patterns in email content
    # Pattern for "When: Monday, January 1, 2023 10:00 AM - 11:00 AM"
    when_pattern = r"when:[\s]*(.*?)(?:[\r\n]|$)"
    when_match = re.search(when_pattern, content_text, re.IGNORECASE)
    
    if when_match:
        when_text = when_match.group(1).strip()
        # Extract times from the "when" line
        time_range_pattern = r"(\d{1,2}[:]\d{2}\s*(?:AM|PM))\s*-\s*(\d{1,2}[:]\d{2}\s*(?:AM|PM))"
        time_match = re.search(time_range_pattern, when_text, re.IGNORECASE)
        
        if time_match and default_date:
            # We have times but need to combine with the email date
            start_time_str, end_time_str = time_match.groups()
            
            # This is a simple approach - a more robust solution would parse the full date from the when_text
            try:
                # Parse time strings and combine with email date
                start_hour, start_minute = map(int, re.search(r"(\d{1,2})[:](\d{2})", start_time_str).groups())
                is_start_pm = "PM" in start_time_str.upper() and start_hour < 12
                if is_start_pm:
                    start_hour += 12
                
                end_hour, end_minute = map(int, re.search(r"(\d{1,2})[:](\d{2})", end_time_str).groups())
                is_end_pm = "PM" in end_time_str.upper() and end_hour < 12
                if is_end_pm:
                    end_hour += 12
                
                # Create datetime objects
                start_time = default_date.replace(hour=start_hour, minute=start_minute)
                end_time = default_date.replace(hour=end_hour, minute=end_minute)
            except (ValueError, AttributeError):
                logger.warning(f"Could not parse meeting times from: {when_text}")
    
    # If we still don't have times, use email date as fallback for start time
    # and add 1 hour for end time
    if not start_time and default_date:
        start_time = default_date
        end_time = start_time.replace(hour=start_time.hour + 1)
    
    return start_time, end_time


def _extract_organizer(email_obj: Email) -> str:
    """Extract meeting organizer from invite email.
    
    Args:
        email_obj: Email object identified as a meeting invite
        
    Returns:
        Meeting organizer name/email
    """
    # Use the sender as the default organizer
    organizer = str(email_obj.from_)
    
    # Check for explicit organizer in content
    content_text = ""
    if email_obj.content.text:
        content_text = email_obj.content.text
    elif email_obj.content.html:
        content_text = re.sub(r'<[^>]*>', '', email_obj.content.html)
    
    # Look for "Organizer:" pattern
    organizer_pattern = r"organizer:[\s]*(.*?)(?:[\r\n]|$)"
    organizer_match = re.search(organizer_pattern, content_text, re.IGNORECASE)
    
    if organizer_match:
        organizer = organizer_match.group(1).strip()
    
    return organizer


def _extract_location(email_obj: Email) -> str:
    """Extract meeting location from invite email.
    
    Args:
        email_obj: Email object identified as a meeting invite
        
    Returns:
        Meeting location/venue/link
    """
    # Default location
    location = "Not specified"
    
    # Check content for location information
    content_text = ""
    if email_obj.content.text:
        content_text = email_obj.content.text
    elif email_obj.content.html:
        content_text = re.sub(r'<[^>]*>', '', email_obj.content.html)
    
    # Look for "Location:" pattern
    location_pattern = r"location:[\s]*(.*?)(?:[\r\n]|$)"
    location_match = re.search(location_pattern, content_text, re.IGNORECASE)
    
    if location_match:
        location = location_match.group(1).strip()
        
        # Look for online meeting links in the location
        if re.search(r"https?://", location, re.IGNORECASE):
            # This is an online meeting
            pass
        elif location.lower() in ["online", "virtual", "zoom", "teams", "meet", "webex"]:
            # This is an online meeting with a generic location
            pass
    
    return location


def _extract_description(email_obj: Email) -> str:
    """Extract meeting description from invite email.
    
    Args:
        email_obj: Email object identified as a meeting invite
        
    Returns:
        Meeting description/body
    """
    # Use email content as the meeting description
    if email_obj.content.text:
        return email_obj.content.text
    
    # Fall back to HTML content if text is not available
    if email_obj.content.html:
        # Simple HTML to text conversion
        return re.sub(r'<[^>]*>', '', email_obj.content.html)
    
    return "No description available"
