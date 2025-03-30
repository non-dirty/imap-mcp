import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from imap_mcp.tools import process_invite_email, identify_meeting_invite, check_calendar_availability, draft_meeting_reply

@pytest.fixture
def mock_ctx():
    """Create a mock context with IMAP and SMTP clients."""
    ctx = MagicMock()
    ctx.log = MagicMock()
    
    # Mock IMAP client
    imap_client = MagicMock()
    ctx.imap_client = imap_client
    
    # Mock SMTP client
    smtp_client = MagicMock()
    ctx.smtp_client = smtp_client
    
    return ctx

@pytest.fixture
def mock_email():
    """Create a mock email for testing."""
    email = MagicMock()
    email.uid = 12345
    email.subject = "Team Meeting - Project Review"
    email.from_email = "organizer@example.com"
    email.to = ["recipient@example.com"]
    email.text = "Let's meet to discuss project progress."
    email.html = "<p>Let's meet to discuss project progress.</p>"
    email.folder = "INBOX"
    email.flags = []
    return email

@pytest.mark.asyncio
async def test_process_invite_success_accept(mock_ctx, mock_email):
    """Test successful processing of an invite with accept response."""
    # Mock identify_meeting_invite
    mock_identify_result = {
        "is_invite": True,
        "invite_details": {
            "subject": "Team Meeting",
            "organizer": "organizer@example.com",
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "location": "Conference Room A"
        },
        "email": mock_email
    }
    
    # Set up mocks
    with patch('imap_mcp.tools.identify_meeting_invite', new_callable=AsyncMock) as mock_identify, \
         patch('imap_mcp.tools.check_calendar_availability', new_callable=AsyncMock) as mock_check, \
         patch('imap_mcp.tools.draft_meeting_reply', new_callable=AsyncMock) as mock_draft, \
         patch('imap_mcp.tools.get_client_from_context') as mock_get_imap, \
         patch('imap_mcp.tools.get_smtp_client_from_context') as mock_get_smtp:
        
        # Configure mocks
        mock_identify.return_value = mock_identify_result
        mock_check.return_value = True  # Available
        mock_draft.return_value = {
            "reply_subject": "Re: Team Meeting",
            "reply_body": "I'm confirming my attendance..."
        }
        
        # Mock SMTP client create_reply_mime
        mock_smtp = MagicMock()
        mock_smtp.create_reply_mime.return_value = "MIME_MESSAGE_CONTENT"
        mock_get_smtp.return_value = mock_smtp
        
        # Mock IMAP client save_draft_mime
        mock_imap = MagicMock()
        mock_imap.save_draft_mime.return_value = 54321  # Draft UID
        mock_get_imap.return_value = mock_imap
        
        # Call the function
        result = await process_invite_email("INBOX", 12345, mock_ctx)
        
        # Verify function calls
        mock_identify.assert_called_once_with("INBOX", 12345, mock_ctx)
        mock_check.assert_called_once()
        mock_draft.assert_called_once()
        mock_smtp.create_reply_mime.assert_called_once()
        mock_imap.save_draft_mime.assert_called_once_with("MIME_MESSAGE_CONTENT")
        
        # Verify result
        assert result["status"] == "draft_saved"
        assert result["draft_uid"] == 54321
        assert result["reply_type"] == "accept"
        assert "summary" in result

@pytest.mark.asyncio
async def test_process_invite_success_decline(mock_ctx, mock_email):
    """Test successful processing of an invite with decline response."""
    # Mock identify_meeting_invite
    mock_identify_result = {
        "is_invite": True,
        "invite_details": {
            "subject": "Team Meeting",
            "organizer": "organizer@example.com",
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "location": "Conference Room A"
        },
        "email": mock_email
    }
    
    # Set up mocks
    with patch('imap_mcp.tools.identify_meeting_invite', new_callable=AsyncMock) as mock_identify, \
         patch('imap_mcp.tools.check_calendar_availability', new_callable=AsyncMock) as mock_check, \
         patch('imap_mcp.tools.draft_meeting_reply', new_callable=AsyncMock) as mock_draft, \
         patch('imap_mcp.tools.get_client_from_context') as mock_get_imap, \
         patch('imap_mcp.tools.get_smtp_client_from_context') as mock_get_smtp:
        
        # Configure mocks
        mock_identify.return_value = mock_identify_result
        mock_check.return_value = False  # Not available
        mock_draft.return_value = {
            "reply_subject": "Re: Team Meeting",
            "reply_body": "Unfortunately, I'm unavailable..."
        }
        
        # Mock SMTP client create_reply_mime
        mock_smtp = MagicMock()
        mock_smtp.create_reply_mime.return_value = "MIME_MESSAGE_CONTENT"
        mock_get_smtp.return_value = mock_smtp
        
        # Mock IMAP client save_draft_mime
        mock_imap = MagicMock()
        mock_imap.save_draft_mime.return_value = 54321  # Draft UID
        mock_get_imap.return_value = mock_imap
        
        # Call the function
        result = await process_invite_email("INBOX", 12345, mock_ctx)
        
        # Verify result
        assert result["status"] == "draft_saved"
        assert result["draft_uid"] == 54321
        assert result["reply_type"] == "decline"
        assert "summary" in result

@pytest.mark.asyncio
async def test_process_invite_not_invite(mock_ctx):
    """Test handling of non-invite emails."""
    # Mock identify_meeting_invite to return not an invite
    with patch('imap_mcp.tools.identify_meeting_invite', new_callable=AsyncMock) as mock_identify:
        mock_identify.return_value = {
            "is_invite": False,
            "invite_details": {},
            "email": MagicMock()
        }
        
        # Call the function
        result = await process_invite_email("INBOX", 12345, mock_ctx)
        
        # Verify result
        assert result["status"] == "not_invite"
        assert "message" in result

@pytest.mark.asyncio
async def test_process_invite_identify_error(mock_ctx):
    """Test error handling when identification fails."""
    # Mock identify_meeting_invite to raise an exception
    with patch('imap_mcp.tools.identify_meeting_invite', new_callable=AsyncMock) as mock_identify:
        mock_identify.side_effect = ValueError("Failed to fetch email")
        
        # Call the function
        result = await process_invite_email("INBOX", 12345, mock_ctx)
        
        # Verify result
        assert result["status"] == "error"
        assert "Failed to fetch email" in result["message"]

@pytest.mark.asyncio
async def test_process_invite_calendar_error(mock_ctx, mock_email):
    """Test error handling when calendar availability check fails."""
    # Set up mocks
    with patch('imap_mcp.tools.identify_meeting_invite', new_callable=AsyncMock) as mock_identify, \
         patch('imap_mcp.tools.check_calendar_availability', new_callable=AsyncMock) as mock_check:
        
        # Configure mocks
        mock_identify.return_value = {
            "is_invite": True,
            "invite_details": {
                "subject": "Team Meeting",
                "organizer": "organizer@example.com",
                "start_time": datetime.now().isoformat(),
                "end_time": (datetime.now() + timedelta(hours=1)).isoformat()
            },
            "email": mock_email
        }
        mock_check.side_effect = Exception("Calendar API error")
        
        # Call the function
        result = await process_invite_email("INBOX", 12345, mock_ctx)
        
        # Verify result
        assert result["status"] == "error"
        assert "Calendar API error" in result["message"]

@pytest.mark.asyncio
async def test_process_invite_draft_reply_error(mock_ctx, mock_email):
    """Test error handling when drafting reply fails."""
    # Set up mocks
    with patch('imap_mcp.tools.identify_meeting_invite', new_callable=AsyncMock) as mock_identify, \
         patch('imap_mcp.tools.check_calendar_availability', new_callable=AsyncMock) as mock_check, \
         patch('imap_mcp.tools.draft_meeting_reply', new_callable=AsyncMock) as mock_draft:
        
        # Configure mocks
        mock_identify.return_value = {
            "is_invite": True,
            "invite_details": {
                "subject": "Team Meeting",
                "organizer": "organizer@example.com",
                "start_time": datetime.now().isoformat(),
                "end_time": (datetime.now() + timedelta(hours=1)).isoformat()
            },
            "email": mock_email
        }
        mock_check.return_value = True
        mock_draft.side_effect = ValueError("Missing required fields")
        
        # Call the function
        result = await process_invite_email("INBOX", 12345, mock_ctx)
        
        # Verify result
        assert result["status"] == "error"
        assert "Missing required fields" in result["message"]

@pytest.mark.asyncio
async def test_process_invite_save_draft_error(mock_ctx, mock_email):
    """Test error handling when saving draft fails."""
    # Set up mocks
    with patch('imap_mcp.tools.identify_meeting_invite', new_callable=AsyncMock) as mock_identify, \
         patch('imap_mcp.tools.check_calendar_availability', new_callable=AsyncMock) as mock_check, \
         patch('imap_mcp.tools.draft_meeting_reply', new_callable=AsyncMock) as mock_draft, \
         patch('imap_mcp.tools.get_client_from_context') as mock_get_imap, \
         patch('imap_mcp.tools.get_smtp_client_from_context') as mock_get_smtp:
        
        # Configure mocks
        mock_identify.return_value = {
            "is_invite": True,
            "invite_details": {
                "subject": "Team Meeting",
                "organizer": "organizer@example.com",
                "start_time": datetime.now().isoformat(),
                "end_time": (datetime.now() + timedelta(hours=1)).isoformat()
            },
            "email": mock_email
        }
        mock_check.return_value = True
        mock_draft.return_value = {
            "reply_subject": "Re: Team Meeting",
            "reply_body": "I'm confirming my attendance..."
        }
        
        # Mock SMTP client
        mock_smtp = MagicMock()
        mock_smtp.create_reply_mime.return_value = "MIME_MESSAGE_CONTENT"
        mock_get_smtp.return_value = mock_smtp
        
        # Mock IMAP client to fail when saving draft
        mock_imap = MagicMock()
        mock_imap.save_draft_mime.return_value = None  # Failed to save
        mock_get_imap.return_value = mock_imap
        
        # Call the function
        result = await process_invite_email("INBOX", 12345, mock_ctx)
        
        # Verify result
        assert result["status"] == "error"
        assert "Failed to save draft message" in result["message"]
