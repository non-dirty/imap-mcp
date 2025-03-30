import pytest
from datetime import datetime, timedelta
import json
from unittest.mock import patch, MagicMock

from imap_mcp.tools import draft_meeting_reply

# Create a mock Context
@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    return ctx

# Generate test invite details
@pytest.fixture
def sample_invite_details():
    now = datetime.now()
    start_time = (now + timedelta(days=1)).isoformat()
    end_time = (now + timedelta(days=1, hours=1)).isoformat()
    
    return {
        "subject": "Team Sync Meeting",
        "start_time": start_time,
        "end_time": end_time,
        "organizer": "organizer@example.com",
        "location": "Conference Room A"
    }

@pytest.mark.asyncio  # Add this decorator
async def test_draft_reply_accept(mock_ctx, sample_invite_details):
    """Test generating an acceptance reply."""
    result = await draft_meeting_reply(sample_invite_details, True, mock_ctx)
    
    assert isinstance(result, dict)
    assert "reply_subject" in result
    assert "reply_body" in result
    assert result["reply_subject"] == "Re: Team Sync Meeting"
    assert "confirming my attendance" in result["reply_body"]
    assert "Conference Room A" in result["reply_body"]

@pytest.mark.asyncio  # Add this decorator
async def test_draft_reply_decline(mock_ctx, sample_invite_details):
    """Test generating a decline reply."""
    result = await draft_meeting_reply(sample_invite_details, False, mock_ctx)
    
    assert isinstance(result, dict)
    assert "reply_subject" in result
    assert "reply_body" in result
    assert result["reply_subject"] == "Re: Team Sync Meeting"
    assert "Unfortunately" in result["reply_body"]
    assert "won't be able to attend" in result["reply_body"]

@pytest.mark.asyncio  # Add this decorator
async def test_draft_reply_missing_details(mock_ctx):
    """Test handling of missing required fields."""
    incomplete_details = {
        "subject": "Incomplete Meeting",
        # Missing start_time, end_time, organizer
    }
    
    with pytest.raises(ValueError) as excinfo:
        await draft_meeting_reply(incomplete_details, True, mock_ctx)
    
    assert "Missing required fields" in str(excinfo.value)

@pytest.mark.asyncio  # Add this decorator
async def test_draft_reply_subject_already_re(mock_ctx, sample_invite_details):
    """Test subject handling when original subject already starts with 'Re:'."""
    sample_invite_details["subject"] = "Re: Previous Discussion"
    
    result = await draft_meeting_reply(sample_invite_details, True, mock_ctx)
    
    assert result["reply_subject"] == "Re: Previous Discussion"
    # Should not be "Re: Re: Previous Discussion"