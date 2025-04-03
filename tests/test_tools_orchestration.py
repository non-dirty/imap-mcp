<<<<<<< Updated upstream
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
=======
"""Tests for the meeting invite orchestration tool."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from email.message import EmailMessage

from mcp.server.fastmcp import Context

from imap_mcp.models import Email, EmailAddress, EmailContent
from imap_mcp.imap_client import ImapClient
from imap_mcp.config import ImapConfig
from imap_mcp.tools import register_tools


class TestMeetingInviteOrchestration:
    """Tests for the meeting invite orchestration functionality."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = MagicMock(spec=Context)
        ctx.kwargs = {"client": None}
        return ctx
    
    @pytest.fixture
    def mock_imap_client(self):
        """Create a mock IMAP client."""
        config = ImapConfig(
            host="imap.example.com",
            port=993,
            username="test@example.com",
            password="password",
            use_ssl=True
        )
        client = ImapClient(config)
        
        # Mock necessary methods
        client.fetch_email = MagicMock()
        client.save_draft_mime = MagicMock()
        client._get_drafts_folder = MagicMock(return_value="Drafts")
        
        return client
    
    @pytest.fixture
    def mock_invite_email(self):
        """Create a mock meeting invite email."""
        return Email(
            message_id="<invite123@example.com>",
            subject="Meeting Invitation: Team Sync",
            from_=EmailAddress(name="Organizer", address="organizer@example.com"),
            to=[EmailAddress(name="Me", address="me@example.com")],
            date=datetime(2025, 4, 1, 10, 0, 0),
            content=EmailContent(
                text="You are invited to a team sync meeting.\nWhen: Tuesday, April 1, 2025 10:00 AM - 11:00 AM"
            ),
            headers={"Content-Type": "text/calendar; method=REQUEST"}
        )
    
    @pytest.fixture
    def mock_non_invite_email(self):
        """Create a mock non-invite email."""
        return Email(
            message_id="<message123@example.com>",
            subject="Regular Email",
            from_=EmailAddress(name="Sender", address="sender@example.com"),
            to=[EmailAddress(name="Me", address="me@example.com")],
            date=datetime(2025, 4, 1, 9, 0, 0),
            content=EmailContent(
                text="This is a regular email, not a meeting invite."
            ),
            headers={}
        )
    
    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server."""
        mcp = MagicMock()
        mcp.tool = lambda: lambda func: func
        return mcp
    
    @patch("imap_mcp.workflows.invite_parser.identify_meeting_invite_details")
    @patch("imap_mcp.workflows.calendar_mock.check_mock_availability")
    @patch("imap_mcp.workflows.meeting_reply.generate_meeting_reply_content")
    @patch("imap_mcp.smtp_client.create_reply_mime")
    @patch("imap_mcp.resources.get_client_from_context")
    async def test_process_meeting_invite_success(
        self,
        mock_get_client,
        mock_create_reply_mime,
        mock_generate_reply,
        mock_check_availability,
        mock_identify_invite,
        mock_context,
        mock_imap_client,
        mock_invite_email
    ):
        """Test successful processing of a meeting invite."""
        # Setup mocks
        mock_get_client.return_value = mock_imap_client
        mock_imap_client.fetch_email.return_value = mock_invite_email
        
        # Mock invite identification
        mock_identify_invite.return_value = {
            "is_invite": True,
            "details": {
                "subject": "Team Sync",
                "start_time": datetime(2025, 4, 1, 10, 0, 0),
                "end_time": datetime(2025, 4, 1, 11, 0, 0),
                "organizer": "Organizer <organizer@example.com>",
                "location": "Conference Room"
            }
        }
        
        # Mock availability check
        mock_check_availability.return_value = {
            "available": True,
            "reason": "Time slot is available",
            "alternative_times": []
        }
        
        # Mock reply generation
        mock_generate_reply.return_value = {
            "reply_subject": "Accepted: Team Sync",
            "reply_body": "I'll attend the meeting...",
            "reply_type": "accept"
        }
        
        # Mock MIME message creation
        mock_mime_message = MagicMock(spec=EmailMessage)
        mock_create_reply_mime.return_value = mock_mime_message
        
        # Mock draft saving
        mock_imap_client.save_draft_mime.return_value = 123
        
        # Register tools and get the process_meeting_invite function
        mock_mcp = self.mock_mcp()
        register_tools(mock_mcp, mock_imap_client)
        process_meeting_invite = mock_mcp.tool.return_value
        
        # Call the function
        result = await process_meeting_invite(
            folder="INBOX",
            uid=456,
            ctx=mock_context,
            availability_mode="always_available"
        )
        
        # Assertions
        assert result["status"] == "success"
        assert "draft_uid" in result
        assert result["draft_uid"] == 123
        assert result["draft_folder"] == "Drafts"
        assert result["availability"] is True
        
        # Verify the mock calls
        mock_imap_client.fetch_email.assert_called_once_with(456, "INBOX")
        mock_identify_invite.assert_called_once_with(mock_invite_email)
        mock_check_availability.assert_called_once()
        mock_generate_reply.assert_called_once()
        mock_create_reply_mime.assert_called_once()
        mock_imap_client.save_draft_mime.assert_called_once_with(mock_mime_message)
        mock_imap_client._get_drafts_folder.assert_called_once()
    
    @patch("imap_mcp.workflows.invite_parser.identify_meeting_invite_details")
    @patch("imap_mcp.resources.get_client_from_context")
    async def test_process_non_invite_email(
        self,
        mock_get_client,
        mock_identify_invite,
        mock_context,
        mock_imap_client,
        mock_non_invite_email
    ):
        """Test processing a non-invite email."""
        # Setup mocks
        mock_get_client.return_value = mock_imap_client
        mock_imap_client.fetch_email.return_value = mock_non_invite_email
        
        # Mock invite identification
        mock_identify_invite.return_value = {
            "is_invite": False,
            "details": {}
        }
        
        # Register tools and get the process_meeting_invite function
        mock_mcp = self.mock_mcp()
        register_tools(mock_mcp, mock_imap_client)
        process_meeting_invite = mock_mcp.tool.return_value
        
        # Call the function
        result = await process_meeting_invite(
            folder="INBOX",
            uid=456,
            ctx=mock_context
        )
        
        # Assertions
        assert result["status"] == "not_invite"
        assert "The email is not a meeting invite" in result["message"]
        
        # Verify the mock calls
        mock_imap_client.fetch_email.assert_called_once_with(456, "INBOX")
        mock_identify_invite.assert_called_once_with(mock_non_invite_email)
    
    @patch("imap_mcp.resources.get_client_from_context")
    async def test_process_meeting_invite_email_not_found(
        self,
        mock_get_client,
        mock_context,
        mock_imap_client
    ):
        """Test handling when the email is not found."""
        # Setup mocks
        mock_get_client.return_value = mock_imap_client
        mock_imap_client.fetch_email.return_value = None
        
        # Register tools and get the process_meeting_invite function
        mock_mcp = self.mock_mcp()
        register_tools(mock_mcp, mock_imap_client)
        process_meeting_invite = mock_mcp.tool.return_value
        
        # Call the function
        result = await process_meeting_invite(
            folder="INBOX",
            uid=456,
            ctx=mock_context
        )
        
        # Assertions
        assert result["status"] == "error"
        assert "not found" in result["message"]
        
        # Verify the mock calls
        mock_imap_client.fetch_email.assert_called_once_with(456, "INBOX")
    
    @patch("imap_mcp.workflows.invite_parser.identify_meeting_invite_details")
    @patch("imap_mcp.workflows.calendar_mock.check_mock_availability")
    @patch("imap_mcp.workflows.meeting_reply.generate_meeting_reply_content")
    @patch("imap_mcp.smtp_client.create_reply_mime")
    @patch("imap_mcp.resources.get_client_from_context")
    async def test_process_meeting_invite_save_draft_failure(
        self,
        mock_get_client,
        mock_create_reply_mime,
        mock_generate_reply,
        mock_check_availability,
        mock_identify_invite,
        mock_context,
        mock_imap_client,
        mock_invite_email
    ):
        """Test handling when saving the draft fails."""
        # Setup mocks
        mock_get_client.return_value = mock_imap_client
        mock_imap_client.fetch_email.return_value = mock_invite_email
        
        # Mock invite identification
        mock_identify_invite.return_value = {
            "is_invite": True,
            "details": {
                "subject": "Team Sync",
                "start_time": datetime(2025, 4, 1, 10, 0, 0),
                "end_time": datetime(2025, 4, 1, 11, 0, 0),
                "organizer": "Organizer <organizer@example.com>",
                "location": "Conference Room"
            }
        }
        
        # Mock availability check
        mock_check_availability.return_value = {
            "available": False,
            "reason": "Calendar is busy during this time",
            "alternative_times": []
        }
        
        # Mock reply generation
        mock_generate_reply.return_value = {
            "reply_subject": "Declined: Team Sync",
            "reply_body": "I'm unable to attend the meeting...",
            "reply_type": "decline"
        }
        
        # Mock MIME message creation
        mock_mime_message = MagicMock(spec=EmailMessage)
        mock_create_reply_mime.return_value = mock_mime_message
        
        # Mock draft saving failure
        mock_imap_client.save_draft_mime.return_value = None
        
        # Register tools and get the process_meeting_invite function
        mock_mcp = self.mock_mcp()
        register_tools(mock_mcp, mock_imap_client)
        process_meeting_invite = mock_mcp.tool.return_value
        
        # Call the function
        result = await process_meeting_invite(
            folder="INBOX",
            uid=456,
            ctx=mock_context,
            availability_mode="always_busy"
        )
        
        # Assertions
        assert result["status"] == "error"
        assert "Failed to save draft" in result["message"]
        assert result["availability"] is False
        
        # Verify the mock calls
        mock_imap_client.fetch_email.assert_called_once_with(456, "INBOX")
        mock_identify_invite.assert_called_once_with(mock_invite_email)
        mock_check_availability.assert_called_once()
        mock_generate_reply.assert_called_once()
        mock_create_reply_mime.assert_called_once()
        mock_imap_client.save_draft_mime.assert_called_once_with(mock_mime_message)
>>>>>>> Stashed changes
