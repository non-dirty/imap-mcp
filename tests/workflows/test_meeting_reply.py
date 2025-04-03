"""Tests for meeting reply generation functionality."""

import pytest
from datetime import datetime
from unittest.mock import patch

from imap_mcp.workflows.meeting_reply import (
    generate_meeting_reply_content,
    _format_meeting_time,
    _generate_accept_reply,
    _generate_decline_reply
)


class TestMeetingReply:
    """Tests for meeting reply functions."""
    
    @pytest.fixture
    def sample_invite_details(self):
        """Create sample invite details for testing."""
        return {
            "subject": "Project Planning Meeting",
            "start_time": datetime(2025, 4, 1, 10, 0, 0),
            "end_time": datetime(2025, 4, 1, 11, 0, 0),
            "organizer": "John Smith <john@example.com>",
            "location": "Conference Room A",
            "description": "Weekly project planning session"
        }
    
    @pytest.fixture
    def sample_availability_accept(self):
        """Create sample availability status for accepting."""
        return {
            "available": True,
            "reason": "Time slot is available",
            "alternative_times": []
        }
    
    @pytest.fixture
    def sample_availability_decline(self):
        """Create sample availability status for declining."""
        return {
            "available": False,
            "reason": "Calendar is busy during this time",
            "alternative_times": []
        }
    
    def test_format_meeting_time_same_day(self):
        """Test formatting meeting time for same day."""
        start_time = datetime(2025, 4, 1, 10, 0, 0)
        end_time = datetime(2025, 4, 1, 11, 0, 0)
        
        result = _format_meeting_time(start_time, end_time)
        
        assert "Tuesday, April 01, 2025" in result
        assert "from 10:00 AM to 11:00 AM" in result
    
    def test_format_meeting_time_different_days(self):
        """Test formatting meeting time for different days."""
        start_time = datetime(2025, 4, 1, 10, 0, 0)
        end_time = datetime(2025, 4, 2, 11, 0, 0)
        
        result = _format_meeting_time(start_time, end_time)
        
        assert "Tuesday, April 01, 2025" in result
        assert "Wednesday, April 02, 2025" in result
    
    def test_format_meeting_time_missing_end(self):
        """Test formatting meeting time with missing end time."""
        start_time = datetime(2025, 4, 1, 10, 0, 0)
        
        result = _format_meeting_time(start_time, None)
        
        assert "Tuesday, April 01, 2025 at 10:00 AM" == result
    
    def test_format_meeting_time_missing_both(self):
        """Test formatting meeting time with both times missing."""
        result = _format_meeting_time(None, None)
        
        assert result == "scheduled time"
    
    def test_generate_accept_reply(self):
        """Test generating an acceptance reply."""
        subject = "Project Meeting"
        formatted_time = "Tuesday, April 01, 2025 from 10:00 AM to 11:00 AM"
        organizer = "John Smith <john@example.com>"
        location = "Conference Room A"
        
        result = _generate_accept_reply(subject, formatted_time, organizer, location)
        
        assert isinstance(result, dict)
        assert "reply_subject" in result
        assert "reply_body" in result
        assert "reply_type" in result
        assert result["reply_type"] == "accept"
        assert "Accepted: Project Meeting" == result["reply_subject"]
        assert "I'll attend the meeting" in result["reply_body"]
        assert formatted_time in result["reply_body"]
        assert location in result["reply_body"]
    
    def test_generate_decline_reply(self):
        """Test generating a decline reply."""
        subject = "Project Meeting"
        formatted_time = "Tuesday, April 01, 2025 from 10:00 AM to 11:00 AM"
        organizer = "John Smith <john@example.com>"
        location = "Conference Room A"
        reason = "Schedule conflict"
        
        result = _generate_decline_reply(subject, formatted_time, organizer, location, reason)
        
        assert isinstance(result, dict)
        assert "reply_subject" in result
        assert "reply_body" in result
        assert "reply_type" in result
        assert result["reply_type"] == "decline"
        assert "Declined: Project Meeting" == result["reply_subject"]
        assert "I'm unable to attend" in result["reply_body"]
        assert formatted_time in result["reply_body"]
        assert reason in result["reply_body"]
    
    def test_generate_meeting_reply_content_accept(self, sample_invite_details, sample_availability_accept):
        """Test generating meeting reply content for an accepted meeting."""
        result = generate_meeting_reply_content(sample_invite_details, sample_availability_accept)
        
        assert isinstance(result, dict)
        assert "reply_subject" in result
        assert "reply_body" in result
        assert "reply_type" in result
        assert result["reply_type"] == "accept"
        assert "Accepted:" in result["reply_subject"]
        assert sample_invite_details["subject"] in result["reply_subject"]
        assert "I'll attend" in result["reply_body"]
        assert sample_invite_details["location"] in result["reply_body"]
    
    def test_generate_meeting_reply_content_decline(self, sample_invite_details, sample_availability_decline):
        """Test generating meeting reply content for a declined meeting."""
        result = generate_meeting_reply_content(sample_invite_details, sample_availability_decline)
        
        assert isinstance(result, dict)
        assert "reply_subject" in result
        assert "reply_body" in result
        assert "reply_type" in result
        assert result["reply_type"] == "decline"
        assert "Declined:" in result["reply_subject"]
        assert sample_invite_details["subject"] in result["reply_subject"]
        assert "I'm unable to attend" in result["reply_body"]
        assert sample_availability_decline["reason"] in result["reply_body"]
    
    def test_generate_meeting_reply_content_invalid_input(self):
        """Test generating meeting reply content with invalid input."""
        # Test with non-dict invite details
        result1 = generate_meeting_reply_content("not a dict", {"available": True})
        assert result1["reply_type"] == "error"
        assert "Error:" in result1["reply_subject"]
        
        # Test with non-dict availability status
        result2 = generate_meeting_reply_content({"subject": "Test"}, "not a dict")
        assert result2["reply_type"] == "error"
        assert "Error:" in result2["reply_subject"]
    
    def test_generate_meeting_reply_content_missing_fields(self):
        """Test generating meeting reply content with missing fields."""
        # Minimal invite details
        minimal_invite = {"subject": "Minimal Meeting"}
        availability = {"available": True}
        
        result = generate_meeting_reply_content(minimal_invite, availability)
        
        assert isinstance(result, dict)
        assert "reply_subject" in result
        assert "reply_body" in result
        assert result["reply_type"] == "accept"
        assert "Minimal Meeting" in result["reply_subject"]
        assert "scheduled time" in result["reply_body"]  # fallback for missing datetime
        assert "Not specified" in result["reply_body"]  # fallback for missing location
