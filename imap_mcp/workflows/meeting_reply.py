"""Meeting invite reply generation functionality."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def generate_meeting_reply_content(
    invite_details: Dict[str, Any], 
    availability_status: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate meeting reply content based on invite details and availability.
    
    Args:
        invite_details: Dictionary with meeting invite details (from invite_parser)
        availability_status: Dictionary with availability details (from calendar_mock)
    
    Returns:
        Dictionary with reply details:
            - reply_subject: Subject line for the reply
            - reply_body: Body text for the reply
            - reply_type: "accept" or "decline"
    """
    # Validate input
    if not isinstance(invite_details, dict) or not isinstance(availability_status, dict):
        logger.error(f"Invalid input types: invite_details={type(invite_details)}, availability_status={type(availability_status)}")
        return {
            "reply_subject": "Error: Invalid Meeting Invite",
            "reply_body": "Could not process the meeting invite due to invalid data.",
            "reply_type": "error"
        }
    
    # Extract key details
    subject = invite_details.get("subject", "Meeting")
    start_time = invite_details.get("start_time")
    end_time = invite_details.get("end_time")
    organizer = invite_details.get("organizer", "Meeting Organizer")
    location = invite_details.get("location", "Not specified")
    
    # Format date/time for display
    formatted_time = _format_meeting_time(start_time, end_time)
    
    # Check if available
    is_available = availability_status.get("available", False)
    decline_reason = availability_status.get("reason", "Schedule conflict") if not is_available else ""
    
    # Generate reply based on availability
    if is_available:
        return _generate_accept_reply(subject, formatted_time, organizer, location)
    else:
        return _generate_decline_reply(subject, formatted_time, organizer, location, decline_reason)


def _format_meeting_time(
    start_time: Optional[datetime], 
    end_time: Optional[datetime]
) -> str:
    """Format meeting time for display in reply.
    
    Args:
        start_time: Meeting start time
        end_time: Meeting end time
    
    Returns:
        Formatted time string
    """
    if not start_time:
        return "scheduled time"
    
    # Format just the start time if no end time
    if not end_time:
        return start_time.strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Check if same day
    same_day = start_time.date() == end_time.date()
    
    if same_day:
        # Format as "Monday, January 1, 2025 from 10:00 AM to 11:00 AM"
        return (
            f"{start_time.strftime('%A, %B %d, %Y')} from "
            f"{start_time.strftime('%I:%M %p')} to {end_time.strftime('%I:%M %p')}"
        )
    else:
        # Format as "Monday, January 1, 2025 at 10:00 AM to Tuesday, January 2, 2025 at 11:00 AM"
        return (
            f"{start_time.strftime('%A, %B %d, %Y')} at {start_time.strftime('%I:%M %p')} to "
            f"{end_time.strftime('%A, %B %d, %Y')} at {end_time.strftime('%I:%M %p')}"
        )


def _generate_accept_reply(
    subject: str, 
    formatted_time: str, 
    organizer: str, 
    location: str
) -> Dict[str, Any]:
    """Generate reply content for accepting a meeting invite.
    
    Args:
        subject: Meeting subject
        formatted_time: Formatted meeting time string
        organizer: Meeting organizer
        location: Meeting location
    
    Returns:
        Dictionary with reply details
    """
    reply_subject = f"Accepted: {subject}"
    
    reply_body = (
        f"I'll attend the meeting: \"{subject}\" on {formatted_time}.\n\n"
        f"Location: {location}\n"
        "\n"
        "Thank you for the invitation.\n"
        "\n"
        "Best regards,"
    )
    
    logger.debug(f"Generated accept reply for meeting: {subject}")
    
    return {
        "reply_subject": reply_subject,
        "reply_body": reply_body,
        "reply_type": "accept"
    }


def _generate_decline_reply(
    subject: str, 
    formatted_time: str, 
    organizer: str, 
    location: str,
    reason: str
) -> Dict[str, Any]:
    """Generate reply content for declining a meeting invite.
    
    Args:
        subject: Meeting subject
        formatted_time: Formatted meeting time string
        organizer: Meeting organizer
        location: Meeting location
        reason: Reason for declining
    
    Returns:
        Dictionary with reply details
    """
    reply_subject = f"Declined: {subject}"
    
    reply_body = (
        f"I'm unable to attend the meeting: \"{subject}\" on {formatted_time}.\n\n"
        f"Reason: {reason}\n"
        "\n"
        "Thank you for the invitation. Please let me know if there's an alternative time "
        "that might work or if I can contribute in another way.\n"
        "\n"
        "Best regards,"
    )
    
    logger.debug(f"Generated decline reply for meeting: {subject}")
    
    return {
        "reply_subject": reply_subject,
        "reply_body": reply_body,
        "reply_type": "decline"
    }
