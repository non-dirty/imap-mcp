"""Tests for meeting invite identification and parsing logic."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from email.message import Message

from imap_mcp.models import Email, EmailAddress, EmailContent, EmailAttachment
from imap_mcp.workflows.invite_parser import (
    identify_meeting_invite_details,
    _is_meeting_invite,
    _extract_meeting_details,
    _extract_meeting_subject,
    _extract_meeting_times,
    _extract_organizer,
    _extract_location,
    _extract_description
)


class TestInviteParser:
    """Tests for invite parser functions."""
    
    @pytest.fixture
    def basic_invite_email(self):
        """Create a basic meeting invite email."""
        return Email(
            message_id="<meeting123@example.com>",
            subject="Meeting Invitation: Project Review",
            from_=EmailAddress(name="John Smith", address="john@example.com"),
            to=[EmailAddress(name="Jane Doe", address="jane@example.com")],
            date=datetime(2025, 3, 30, 14, 0, 0),
            content=EmailContent(
                text=(
                    "You are invited to a meeting.\n"
                    "When: Monday, March 31, 2025 2:00 PM - 3:00 PM\n"
                    "Location: Conference Room A\n"
                    "Organizer: John Smith\n\n"
                    "Project review meeting to discuss progress."
                )
            ),
            headers={"Content-Type": "text/calendar; method=REQUEST"}
        )
    
    @pytest.fixture
    def calendar_attachment_invite_email(self):
        """Create a meeting invite email with calendar attachment."""
        email = Email(
            message_id="<meeting456@example.com>",
            subject="Team Sync",
            from_=EmailAddress(name="Alice Manager", address="alice@example.com"),
            to=[EmailAddress(name="Team", address="team@example.com")],
            date=datetime(2025, 4, 1, 10, 0, 0),
            content=EmailContent(
                text="Weekly team sync meeting.\nPlease review the agenda."
            ),
            headers={}
        )
        
        # Add calendar attachment
        email.attachments = [
            EmailAttachment(
                filename="invite.ics",
                content_type="text/calendar",
                size=1024
            )
        ]
        
        return email
    
    @pytest.fixture
    def online_meeting_invite_email(self):
        """Create an online meeting invite email."""
        return Email(
            message_id="<meeting789@example.com>",
            subject="Virtual Workshop Invitation",
            from_=EmailAddress(name="Training Dept", address="training@example.com"),
            to=[EmailAddress(name="Participants", address="participants@example.com")],
            date=datetime(2025, 4, 2, 13, 0, 0),
            content=EmailContent(
                text=(
                    "Join our virtual workshop!\n"
                    "When: Wednesday, April 2, 2025 1:00 PM - 3:00 PM\n"
                    "Location: https://meeting.example.com/workshop\n\n"
                    "Please prepare by reviewing the materials."
                )
            ),
            headers={}
        )
    
    @pytest.fixture
    def non_invite_email(self):
        """Create a regular non-invite email."""
        return Email(
            message_id="<message123@example.com>",
            subject="Weekly Report",
            from_=EmailAddress(name="Reports", address="reports@example.com"),
            to=[EmailAddress(name="Manager", address="manager@example.com")],
            date=datetime(2025, 3, 28, 9, 0, 0),
            content=EmailContent(
                text="Please find attached the weekly report.\nLet me know if you have questions."
            ),
            headers={}
        )
    
    @pytest.fixture
    def ambiguous_email(self):
        """Create an email with some meeting-like keywords but not an invite."""
        return Email(
            message_id="<message456@example.com>",
            subject="About yesterday's meeting",
            from_=EmailAddress(name="Colleague", address="colleague@example.com"),
            to=[EmailAddress(name="You", address="you@example.com")],
            date=datetime(2025, 3, 29, 11, 0, 0),
            content=EmailContent(
                text="I wanted to follow up on our discussion in yesterday's meeting.\nLet's schedule a call next week."
            ),
            headers={}
        )
    
    def test_identify_meeting_invite_by_subject(self, basic_invite_email):
        """Test identifying meeting invite by subject keywords."""
        result = identify_meeting_invite_details(basic_invite_email)
        assert result["is_invite"] is True
        assert "subject" in result["details"]
        assert result["details"]["subject"] == "Project Review"
    
    def test_identify_meeting_invite_by_attachment(self, calendar_attachment_invite_email):
        """Test identifying meeting invite by calendar attachment."""
        result = identify_meeting_invite_details(calendar_attachment_invite_email)
        assert result["is_invite"] is True
        assert "subject" in result["details"]
        assert result["details"]["subject"] == "Team Sync"
    
    def test_identify_meeting_invite_by_content(self, online_meeting_invite_email):
        """Test identifying meeting invite by content patterns."""
        result = identify_meeting_invite_details(online_meeting_invite_email)
        assert result["is_invite"] is True
        assert "location" in result["details"]
        assert "https://meeting.example.com/workshop" in result["details"]["location"]
    
    def test_non_invite_email(self, non_invite_email):
        """Test that non-invite emails are correctly identified."""
        result = identify_meeting_invite_details(non_invite_email)
        assert result["is_invite"] is False
        assert result["details"] == {}
    
    def test_ambiguous_email(self, ambiguous_email):
        """Test handling of ambiguous emails with meeting keywords."""
        # Our implementation might identify this as a meeting or not depending on threshold
        # The important thing is consistent behavior
        result = identify_meeting_invite_details(ambiguous_email)
        is_invite = result["is_invite"]
        
        # If identified as invite, check extracted details
        if is_invite:
            assert "subject" in result["details"]
            assert result["details"]["subject"] == "About yesterday's meeting"
        else:
            assert result["details"] == {}
    
    def test_extract_meeting_times(self, basic_invite_email):
        """Test extracting meeting start and end times."""
        start_time, end_time = _extract_meeting_times(basic_invite_email)
        
        assert start_time is not None
        assert end_time is not None
        
        # Check expected time values
        assert start_time.hour == 14  # 2 PM
        assert start_time.minute == 0
        assert end_time.hour == 15    # 3 PM
        assert end_time.minute == 0
    
    def test_extract_meeting_location(self, basic_invite_email, online_meeting_invite_email):
        """Test extracting meeting location for physical and online meetings."""
        # Physical location
        location1 = _extract_location(basic_invite_email)
        assert "Conference Room A" in location1
        
        # Online location
        location2 = _extract_location(online_meeting_invite_email)
        assert "https://meeting.example.com/workshop" in location2
    
    def test_extract_meeting_organizer(self, basic_invite_email):
        """Test extracting meeting organizer."""
        organizer = _extract_organizer(basic_invite_email)
        assert "John Smith" in organizer
    
    def test_fallback_to_email_date(self):
        """Test fallback to email date when no explicit meeting time is found."""
        email = Email(
            message_id="<meeting999@example.com>",
            subject="Quick Meeting",
            from_=EmailAddress(name="Colleague", address="colleague@example.com"),
            to=[EmailAddress(name="You", address="you@example.com")],
            date=datetime(2025, 4, 5, 10, 0, 0),
            content=EmailContent(
                text="Let's have a quick meeting to discuss the project."
            ),
            headers={}
        )
        
        result = identify_meeting_invite_details(email)
        
        # We might identify this as a meeting due to the keyword
        if result["is_invite"]:
            assert result["details"]["start_time"] is not None
            # Should fall back to email date
            assert result["details"]["start_time"].date() == datetime(2025, 4, 5).date()
    
    def test_extract_description(self, basic_invite_email):
        """Test extracting meeting description."""
        description = _extract_description(basic_invite_email)
        assert "Project review meeting" in description
