"""MCP tools implementation for email operations."""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context

from imap_mcp.imap_client import ImapClient
from imap_mcp.resources import get_client_from_context, get_smtp_client_from_context

from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Define the path for storing tasks
TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tasks.json")

def register_tools(mcp: FastMCP, imap_client: ImapClient) -> None:
    """Register MCP tools.
    
    Args:
        mcp: MCP server
        imap_client: IMAP client
    """

    # Using decorator pattern to register tools
    @mcp.tool()
    async def draft_meeting_reply_tool(invite_details: Dict[str, Any], availability_status: bool, ctx: Context) -> Dict[str, str]:
        """Drafts a meeting reply (accept/decline) based on calendar invite details and availability.
        
        Args:
            invite_details: Dictionary containing invite details (subject, start_time, end_time, organizer, location)
            availability_status: Whether the user is available for the meeting (True=available/accept, False=unavailable/decline)
            ctx: MCP context
            
        Returns:
            Dictionary with reply text and additional metadata
        """
        return await draft_meeting_reply(invite_details, availability_status, ctx)
    
    @mcp.tool()
    async def identify_meeting_invite_tool(folder: str, uid: int, ctx: Context) -> Dict[str, Any]:
        """Identifies if an email is a meeting invite and extracts relevant details.
        
        Args:
            folder: Email folder name
            uid: Email UID
            ctx: MCP context
            
        Returns:
            Dictionary with invite details if it's a meeting invite, or status information if not
        """
        return await identify_meeting_invite(folder, uid, ctx)
    
    @mcp.tool()
    async def check_calendar_availability_tool(start_time: str, end_time: str, ctx: Context) -> Dict[str, Any]:
        """Checks calendar availability for a given time slot.
        
        Args:
            start_time: Meeting start time (ISO format)
            end_time: Meeting end time (ISO format)
            ctx: MCP context
            
        Returns:
            Dictionary with availability status and additional information
        """
        return await check_calendar_availability(start_time, end_time, ctx)
    
    @mcp.tool()
    async def process_invite_email_tool(folder: str, uid: int, ctx: Context) -> Dict[str, Any]:
        """Processes a meeting invitation email: identifies invite, checks availability, drafts reply, saves draft.
        
        Args:
            folder: Email folder name
            uid: Email UID
            ctx: MCP context
            
        Returns:
            Dictionary with processing results and status information
        """
        return await process_invite_email(folder, uid, ctx)
    
    @mcp.tool()
    async def create_task(description: str, ctx: Context, due_date: Optional[str] = None, 
                          priority: Optional[int] = None) -> str:
        """Creates a new task and saves it to a local file.
        
        Args:
            description: Task description
            ctx: MCP context
            due_date: Optional due date in ISO format
            priority: Optional priority (1=high, 2=medium, 3=low)
            
        Returns:
            Success message or error information
        """
        # Call the internal implementation
        return await _create_task_impl(description, ctx, due_date, priority)
    
    @mcp.tool()
    async def draft_reply_tool(folder: str, uid: int, reply_body: str, ctx: Context,
                           reply_all: bool = False, cc: Optional[List[str]] = None,
                           body_html: Optional[str] = None) -> Dict[str, Any]:
        """Creates a draft reply to an email and saves it to the drafts folder.
        
        Args:
            folder: Email folder name
            uid: Email UID
            reply_body: Reply text content
            ctx: MCP context
            reply_all: Whether to reply to all recipients
            cc: Optional CC recipients
            body_html: Optional HTML version of the reply
            
        Returns:
            Dictionary with status and the UID of the created draft
        """
        # Avoid recursion by calling the internal implementation
        return await _draft_reply_impl(folder, uid, reply_body, ctx, reply_all, cc, body_html)
    
    # Move email to a different folder
    @mcp.tool()
    async def move_email(
        folder: str, 
        uid: int, 
        target_folder: str,
        ctx: Context,
    ) -> str:
        """Move email to another folder.
        
        Args:
            folder: Source folder
            uid: Email UID
            target_folder: Target folder
            ctx: MCP context
            
        Returns:
            Success message or error message
        """
        client = get_client_from_context(ctx)
        
        try:
            success = client.move_email(uid, folder, target_folder)
            if success:
                return f"Email moved from {folder} to {target_folder}"
            else:
                return f"Failed to move email"
        except Exception as e:
            logger.error(f"Error moving email: {e}")
            return f"Error: {e}"
    
    # Mark email as read
    @mcp.tool()
    async def mark_as_read(
        folder: str,
        uid: int,
        ctx: Context,
    ) -> str:
        """Mark email as read.
        
        Args:
            folder: Folder name
            uid: Email UID
            ctx: MCP context
            
        Returns:
            Success message or error message
        """
        client = get_client_from_context(ctx)
        
        try:
            success = client.mark_email(uid, folder, r"\Seen", True)
            if success:
                return f"Email marked as read"
            else:
                return f"Failed to mark email as read"
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return f"Error: {e}"
    
    # Mark email as unread
    @mcp.tool()
    async def mark_as_unread(
        folder: str,
        uid: int,
        ctx: Context,
    ) -> str:
        """Mark email as unread.
        
        Args:
            folder: Folder name
            uid: Email UID
            ctx: MCP context
            
        Returns:
            Success message or error message
        """
        client = get_client_from_context(ctx)
        
        try:
            success = client.mark_email(uid, folder, r"\Seen", False)
            if success:
                return f"Email marked as unread"
            else:
                return f"Failed to mark email as unread"
        except Exception as e:
            logger.error(f"Error marking email as unread: {e}")
            return f"Error: {e}"
    
    # Flag email (important/starred)
    @mcp.tool()
    async def flag_email(
        folder: str,
        uid: int,
        ctx: Context,
        flag: bool = True,
    ) -> str:
        """Flag or unflag email.
        
        Args:
            folder: Folder name
            uid: Email UID
            flag: True to flag, False to unflag
            ctx: MCP context
            
        Returns:
            Success message or error message
        """
        client = get_client_from_context(ctx)
        
        try:
            success = client.mark_email(uid, folder, r"\Flagged", flag)
            if success:
                return f"Email {'flagged' if flag else 'unflagged'}"
            else:
                return f"Failed to {'flag' if flag else 'unflag'} email"
        except Exception as e:
            logger.error(f"Error flagging email: {e}")
            return f"Error: {e}"
    
    # Delete email
    @mcp.tool()
    async def delete_email(
        folder: str,
        uid: int,
        ctx: Context,
    ) -> str:
        """Delete email.
        
        Args:
            folder: Folder name
            uid: Email UID
            ctx: MCP context
            
        Returns:
            Success message or error message
        """
        client = get_client_from_context(ctx)
        
        try:
            success = client.delete_email(uid, folder)
            if success:
                return f"Email deleted"
            else:
                return f"Failed to delete email"
        except Exception as e:
            logger.error(f"Error deleting email: {e}")
            return f"Error: {e}"
    
    # Search for emails
    @mcp.tool()
    async def search_emails(
        query: str,
        ctx: Context,
        folder: Optional[str] = None,
        criteria: str = "text",
        limit: int = 10,
    ) -> str:
        """Search for emails.
        
        Args:
            query: Search query
            folder: Folder to search in (None for all folders)
            criteria: Search criteria (text, from, to, subject, all, unseen, seen)
            limit: Maximum number of results
            ctx: MCP context
            
        Returns:
            JSON-formatted list of search results
        """
        client = get_client_from_context(ctx)
        
        # Define search criteria
        search_criteria_map = {
            "text": ["TEXT", query],
            "from": ["FROM", query],
            "to": ["TO", query],
            "subject": ["SUBJECT", query],
            "all": "ALL",
            "unseen": "UNSEEN",
            "seen": "SEEN",
            "today": "today",
            "week": "week",
            "month": "month",
        }
        
        if criteria.lower() not in search_criteria_map:
            return f"Invalid search criteria: {criteria}"
        
        search_criteria = search_criteria_map[criteria.lower()]
        
        folders_to_search = [folder] if folder else client.list_folders()
        results = []
        
        for current_folder in folders_to_search:
            try:
                # Search for emails
                uids = client.search(search_criteria, folder=current_folder)
                
                # Limit results and sort by newest first
                uids = sorted(uids, reverse=True)[:limit]
                
                if uids:
                    # Fetch emails
                    emails = client.fetch_emails(uids, folder=current_folder)
                    
                    # Create summaries
                    for uid, email_obj in emails.items():
                        results.append({
                            "uid": uid,
                            "folder": current_folder,
                            "from": str(email_obj.from_),
                            "to": [str(to) for to in email_obj.to],
                            "subject": email_obj.subject,
                            "date": email_obj.date.isoformat() if email_obj.date else None,
                            "flags": email_obj.flags,
                            "has_attachments": len(email_obj.attachments) > 0,
                        })
            except Exception as e:
                logger.warning(f"Error searching folder {current_folder}: {e}")
        
        # Sort results by date (newest first)
        results.sort(
            key=lambda x: x.get("date") or "0", 
            reverse=True
        )
        
        # Apply global limit
        results = results[:limit]
        
        return json.dumps(results, indent=2)
    
    # Process email interactive session
    @mcp.tool()
    async def process_email(
        folder: str,
        uid: int,
        action: str,
        ctx: Context,
        notes: Optional[str] = None,
        target_folder: Optional[str] = None,
    ) -> str:
        """Process an email with specified action.
        
        This is a higher-level tool that combines multiple actions and records
        the decision for learning purposes.
        
        Args:
            folder: Folder name
            uid: Email UID
            action: Action to take (move, read, unread, flag, unflag, delete)
            notes: Optional notes about the decision
            target_folder: Target folder for move action
            ctx: MCP context
            
        Returns:
            Success message or error message
        """
        client = get_client_from_context(ctx)
        
        # Fetch the email first to have context for learning
        email_obj = client.fetch_email(uid, folder)
        if not email_obj:
            return f"Email with UID {uid} not found in folder {folder}"
        
        # Process the action
        result = ""
        try:
            if action.lower() == "move":
                if not target_folder:
                    return "Target folder must be specified for move action"
                success = client.move_email(uid, folder, target_folder)
                result = f"Email moved from {folder} to {target_folder}"
            elif action.lower() == "read":
                success = client.mark_email(uid, folder, r"\Seen", True)
                result = "Email marked as read"
            elif action.lower() == "unread":
                success = client.mark_email(uid, folder, r"\Seen", False)
                result = "Email marked as unread"
            elif action.lower() == "flag":
                success = client.mark_email(uid, folder, r"\Flagged", True)
                result = "Email flagged"
            elif action.lower() == "unflag":
                success = client.mark_email(uid, folder, r"\Flagged", False)
                result = "Email unflagged"
            elif action.lower() == "delete":
                success = client.delete_email(uid, folder)
                result = "Email deleted"
            else:
                return f"Invalid action: {action}"
            
            # TODO: Record the action for learning in a separate module
            
            return result
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            return f"Error: {e}"
    
    @mcp.tool()
    async def list_emails(
        folder: str,
        ctx: Context,
        limit: int = 10,
        offset: int = 0,
        unread_only: bool = False,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> str:
        """List emails in a folder with pagination.
        
        Args:
            folder: Folder name
            limit: Maximum number of emails to return
            offset: Offset for pagination
            unread_only: Whether to return only unread emails
            sort_by: Field to sort by (date, from, subject)
            sort_order: Sort order (asc, desc)
            ctx: MCP context
            
        Returns:
            JSON-formatted list of emails with pagination metadata
        """
        client = get_client_from_context(ctx)
        
        # Determine search criteria
        search_criteria = "ALL"
        if unread_only:
            search_criteria = "UNSEEN"
        
        # Search for emails
        uids = client.search(search_criteria, folder=folder)
        
        # Get total count for pagination
        total_count = len(uids)
        
        # Apply pagination and fetch the emails
        # Ensure proper sorting before pagination
        if sort_order.lower() == "desc":
            uids = sorted(uids, reverse=True)  # Newest first
        else:
            uids = sorted(uids)  # Oldest first
            
        # Apply offset and limit
        paginated_uids = uids[offset:offset+limit] if uids else []
        
        # Fetch the emails
        emails = {}
        if paginated_uids:
            emails = client.fetch_emails(paginated_uids, folder=folder)
        
        # Create response
        results = []
        for uid, email_obj in emails.items():
            email_data = {
                "uid": uid,
                "folder": folder,
                "from": str(email_obj.from_),
                "to": [str(to) for to in email_obj.to],
                "subject": email_obj.subject,
                "date": email_obj.date.isoformat() if email_obj.date else None,
                "flags": email_obj.flags,
                "has_attachments": len(email_obj.attachments) > 0,
                "is_read": '\\Seen' in email_obj.flags,
            }
            results.append(email_data)
            
        # Apply custom sorting if needed (beyond date which is already handled by UID sorting)
        if sort_by.lower() == "from":
            results.sort(key=lambda x: x.get("from", "").lower(), 
                         reverse=(sort_order.lower() == "desc"))
        elif sort_by.lower() == "subject":
            results.sort(key=lambda x: x.get("subject", "").lower(), 
                         reverse=(sort_order.lower() == "desc"))
        
        # Create pagination metadata
        pagination = {
            "total": total_count,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total_count
        }
        
        # Create final response
        response = {
            "emails": results,
            "pagination": pagination,
            "folder": folder,
            "filters": {
                "unread_only": unread_only
            },
            "sorting": {
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
        
        return json.dumps(response)
        
    @mcp.tool()
    async def list_unread_emails(
        ctx: Context,
        folder: str = "INBOX",
        limit: int = 10,
        offset: int = 0,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> str:
        """List unread emails with pagination.
        
        This is a convenience wrapper around list_emails with unread_only=True.
        
        Args:
            folder: Folder name (defaults to INBOX)
            limit: Maximum number of emails to return
            offset: Offset for pagination
            sort_by: Field to sort by (date, from, subject)
            sort_order: Sort order (asc, desc)
            ctx: MCP context
            
        Returns:
            JSON-formatted list of unread emails with pagination metadata
        """
        # Call list_emails with unread_only=True
        return await list_emails(
            folder=folder,
            ctx=ctx,
            limit=limit,
            offset=offset,
            unread_only=True,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
async def draft_meeting_reply(
    invite_details: Dict[str, str], 
    availability_status: bool, 
    ctx: Context
) -> Dict[str, str]:
    """
    Draft a meeting reply based on invite details and availability status.
    
    Args:
        invite_details: Dictionary containing meeting details like subject, start_time, end_time, and organizer
        availability_status: Boolean indicating if the user is available for the meeting
        ctx: MCP context
        
    Returns:
        Dictionary with reply_subject and reply_body
        
    Raises:
        ValueError: If required fields are missing from invite_details
    """
    # Validate required fields
    required_fields = ["subject", "start_time", "end_time", "organizer"]
    missing_fields = [field for field in required_fields if field not in invite_details]
    
    if missing_fields:
        raise ValueError(f"Missing required fields in invite_details: {', '.join(missing_fields)}")
    
    # Extract invite details
    subject = invite_details["subject"]
    start_time = invite_details["start_time"]
    end_time = invite_details["end_time"]
    organizer = invite_details["organizer"]
    location = invite_details.get("location", "")
    
    # Format date and time for the reply
    try:
        # Handle ISO format or other standard formats
        start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        date_str = start_datetime.strftime("%A, %B %d, %Y")
        time_str = f"{start_datetime.strftime('%I:%M %p')} - {datetime.fromisoformat(end_time.replace('Z', '+00:00')).strftime('%I:%M %p')}"
    except (ValueError, TypeError):
        # Fallback if format is unexpected
        date_str = start_time.split('T')[0] if 'T' in start_time else start_time
        time_str = f"{start_time} - {end_time}"
    
    # Create subject line (ensure we don't duplicate "Re: " prefix)
    if subject.startswith("Re: "):
        reply_subject = subject
    else:
        reply_subject = f"Re: {subject}"
    
    # Generate reply body based on availability
    if availability_status:
        # Acceptance message
        reply_body = f"Hi {organizer.split('@')[0]},\n\n"
        reply_body += f"I'm confirming my attendance for the meeting \"{subject}\" on {date_str} at {time_str}."
        
        if location:
            reply_body += f" I've noted the location: {location}."
            
        reply_body += "\n\nLooking forward to it!\n\nBest regards,"
    else:
        # Decline message
        reply_body = f"Hi {organizer.split('@')[0]},\n\n"
        reply_body += f"Thank you for the invitation to \"{subject}\" on {date_str} at {time_str}."
        reply_body += " Unfortunately, I have a scheduling conflict during this time and won't be able to attend."
        reply_body += "\n\nPlease let me know if there are alternative times we could consider."
        reply_body += "\n\nBest regards,"
    
    return {
        "reply_subject": reply_subject,
        "reply_body": reply_body
    }

async def identify_meeting_invite(folder: str, uid: int, ctx: Context) -> Dict[str, Any]:
    """
    Identify if an email is a meeting invitation and extract meeting details.
    
    Args:
        folder: Email folder name
        uid: Email UID
        ctx: MCP context
        
    Returns:
        Dictionary with is_invite (bool) and if True, meeting details
        
    Raises:
        ValueError: If email cannot be found or accessed
    """
    client = get_client_from_context(ctx)
    if not client:
        raise ValueError("IMAP client not available")
    
    try:
        # Fetch the email
        email = client.fetch_email(uid, folder)
        if not email:
            raise ValueError(f"Email with UID {uid} not found in folder {folder}")
        
        # Check if this is a calendar invitation
        # In a real implementation, would check for calendar MIME parts, iCalendar content, etc.
        # For MVP, we'll use simple heuristics
        is_invite = False
        invite_details = {}
        
        # Simple heuristic: Check subject and body for invite-related terms
        subject_lower = email.subject.lower() if email.subject else ""
        body_lower = email.text.lower() if hasattr(email, "text") and email.text else ""
        
        invite_keywords = ["meeting", "invite", "calendar", "appointment", "scheduled", "event"]
        if any(keyword in subject_lower for keyword in invite_keywords) or \
           any(keyword in body_lower for keyword in invite_keywords):
            is_invite = True
            
            # Extract details - in a real implementation, would parse iCalendar data
            # For MVP, we'll use simple extraction from subject/body
            invite_details = {
                "subject": email.subject or "Meeting Invitation",
                "organizer": email.from_email or "unknown@example.com",
                # Simulate extracting dates, times, location
                "start_time": datetime.now().replace(hour=10, minute=0, second=0, microsecond=0).isoformat(),
                "end_time": datetime.now().replace(hour=11, minute=0, second=0, microsecond=0).isoformat(),
                "location": "Conference Room A",
                "original_email": email  # Include the original email for reply generation
            }
        
        return {
            "is_invite": is_invite,
            "invite_details": invite_details if is_invite else {},
            "email": email  # Include the original email for use in other functions
        }
    
    except Exception as e:
        logger.error(f"Error identifying meeting invite: {e}")
        raise ValueError(f"Error identifying meeting invite: {e}")

async def check_calendar_availability(
    start_time: str, 
    end_time: str, 
    ctx: Context
) -> bool:
    """
    Check if a time slot is available in the user's calendar.
    This is a mock implementation that simulates calendar availability checking.
    
    Args:
        start_time: Start time in ISO format
        end_time: End time in ISO format
        ctx: MCP context
        
    Returns:
        Boolean indicating if the time slot is available
    """
    # Mock implementation - in a real implementation, would check actual calendar
    # For MVP, simulate 70% chance of availability
    import random
    return random.random() < 0.7

async def process_invite_email(folder: str, uid: int, ctx: Context) -> Dict[str, Any]:
    """
    Process a meeting invitation email:
    1. Identify if it's a meeting invite
    2. Check calendar availability (mocked)
    3. Draft appropriate reply
    4. Save draft
    
    Args:
        folder: Email folder name
        uid: Email UID
        ctx: MCP context
        
    Returns:
        Dictionary with status and additional information
    """
    logger.info(f"Processing potential meeting invite: folder={folder}, uid={uid}")
    
    try:
        # Step 1: Identify if this is a meeting invite
        invite_result = await identify_meeting_invite(folder, uid, ctx)
        
        if not invite_result["is_invite"]:
            return {
                "status": "not_invite", 
                "message": "Email was not identified as a meeting invitation."
            }
        
        # It's an invite, extract details
        invite_details = invite_result["invite_details"]
        original_email = invite_result["email"]
        
        logger.info(f"Identified meeting invite: {invite_details['subject']}")
        
        # Step 2: Check calendar availability
        try:
            availability_status = await check_calendar_availability(
                invite_details["start_time"], 
                invite_details["end_time"], 
                ctx
            )
            logger.info(f"Calendar availability for meeting: {availability_status}")
        except Exception as e:
            logger.error(f"Error checking calendar availability: {e}")
            return {
                "status": "error",
                "message": f"Error checking calendar availability: {e}"
            }
        
        # Step 3: Draft reply based on availability
        try:
            reply_result = await draft_meeting_reply(invite_details, availability_status, ctx)
            reply_subject = reply_result["reply_subject"]
            reply_body = reply_result["reply_body"]
            logger.info(f"Reply drafted: {reply_subject}")
        except Exception as e:
            logger.error(f"Error drafting reply: {e}")
            return {
                "status": "error",
                "message": f"Error drafting reply: {e}"
            }
        
        # Step 4: Create reply MIME and save as draft
        try:
            # Get SMTP client
            smtp_client = get_smtp_client_from_context(ctx)
            if not smtp_client:
                raise ValueError("SMTP client not available")
            
            # Create reply MIME
            mime_message = smtp_client.create_reply_mime(
                original_email=original_email,
                body_text=reply_body,
                subject=reply_subject
            )
            
            # Save as draft
            imap_client = get_client_from_context(ctx)
            if not imap_client:
                raise ValueError("IMAP client not available")
            
            draft_uid = imap_client.save_draft_mime(mime_message)
            if not draft_uid:
                raise ValueError("Failed to save draft message")
            
            logger.info(f"Draft saved with UID: {draft_uid}")
            
            return {
                "status": "draft_saved",
                "draft_uid": draft_uid,
                "reply_type": "accept" if availability_status else "decline",
                "summary": reply_body[:100] + "..." if len(reply_body) > 100 else reply_body
            }
        except Exception as e:
            logger.error(f"Error creating or saving draft: {e}")
            return {
                "status": "error",
                "message": f"Error creating or saving draft: {e}"
            }
    
    except Exception as e:
        logger.error(f"Error processing invite email: {e}")
        return {
            "status": "error",
            "message": f"Error processing invite email: {e}"
        }

# Create task (mock implementation)
async def _create_task_impl(
    description: str,
    ctx: Context,
    due_date: Optional[str] = None,
    priority: Optional[int] = None,
) -> str:
    """Create a new task.
    
    This is a mock implementation that logs the task details
    and saves them to a local file (tasks.json).
    
    Args:
        description: Task description
        due_date: Optional due date in format YYYY-MM-DD
        priority: Optional priority level (1-3, where 1 is highest)
        ctx: MCP context
        
    Returns:
        Success message or error message
    """
    # Validate inputs
    if not description:
        return "Error: Task description is required"
    
    # Validate due_date format if provided
    if due_date:
        try:
            # Attempt to parse the date to validate format
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            return "Error: Due date must be in format YYYY-MM-DD"
    
    # Validate priority if provided
    if priority is not None:
        if not isinstance(priority, int):
            return "Error: Priority must be an integer"
        if priority < 1 or priority > 3:
            return "Error: Priority must be between 1 and 3"
    
    # Create task object
    task = {
        "description": description,
        "created_at": datetime.now().isoformat(),
    }
    
    # Add optional fields if provided
    if due_date:
        task["due_date"] = due_date
    if priority is not None:
        task["priority"] = priority
            
    # Log the task details
    logger.info(f"New task created: {json.dumps(task)}")
    
    # Save task to file
    try:
        # Load existing tasks or create empty list
        existing_tasks = []
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, "r") as f:
                existing_tasks = json.load(f)
        
        # Append new task
        existing_tasks.append(task)
        
        # Write back to file
        with open(TASKS_FILE, "w") as f:
            json.dump(existing_tasks, f, indent=2)
                
        return json.dumps({
            "status": "success",
            "message": "Task added successfully",
            "task_description": description
        }, indent=2)
            
    except Exception as e:
        logger.error(f"Error saving task: {e}")
        return f"Error saving task: {e}"

# Draft reply to email
async def _draft_reply_impl(
    folder: str,
    uid: int,
    reply_body: str,
    ctx: Context,
    reply_all: bool = False,
    cc: Optional[List[str]] = None,
    body_html: Optional[str] = None,
) -> str:
    """Create a draft reply to an email and save it to the drafts folder.
    
    This tool combines email composition and draft saving functionality to create 
    a properly formatted reply to an existing email and save it as a draft message.
    The reply includes proper headers (In-Reply-To, References, Subject with "Re:" prefix)
    and formatting (quoted original message).
    
    The tool performs the following steps:
    1. Fetches the original email using its UID and folder
    2. Creates a properly formatted reply MIME message
    3. Saves the message to the user's drafts folder
    4. Returns the status and UID of the newly created draft
        
    The reply can be either to the original sender only (default) or to all recipients
    (reply_all=True). Additional CC recipients can be specified with the cc parameter.
    
    HTML Support:
    If body_html is provided, the email will be created with both plain text and HTML
    versions (multipart/alternative), allowing email clients to display the most 
    appropriate version. The HTML part will include properly formatted quoted content
    from the original email.
    
    Example 1 - Basic Reply:
        ```python
        result = await draft_reply_tool(
            folder="INBOX",
            uid=12345,
            reply_body="Thank you for your email. I'll get back to you soon.",
            ctx=context
        )
        ```
            
    Example 2 - Reply All with CC:
        ```python
        result = await draft_reply_tool(
            folder="INBOX",
            uid=12345,
            reply_body="Thanks for including everyone in this discussion.",
            reply_all=True,
            cc=["supervisor@example.com"],
            ctx=context
        )
        ```
            
    Example 3 - Reply with HTML Content:
        ```python
        result = await draft_reply_tool(
            folder="INBOX",
            uid=12345,
            reply_body="Plain text version of the reply.",
            body_html="<p><strong>HTML version</strong> of the reply with formatting.</p>",
            ctx=context
        )
        ```
        
    Args:
        folder: Folder containing the original email (e.g., "INBOX")
        uid: UID of the original email to reply to
        reply_body: Body text for the reply (plain text version)
        ctx: MCP context containing client connections
        reply_all: Whether to reply to all recipients (default: False)
        cc: Additional CC recipients (optional)
        body_html: Optional HTML version of the reply body
            
    Returns:
        JSON-formatted string with the result:
        - Success: {"status": "success", "message": "Draft reply created", "draft_uid": uid}
        - Failure: {"status": "error", "message": "Error message"}
    """
    # Get the IMAP client
    imap_client = get_client_from_context(ctx)
        
    try:
        # Fetch the original email
        original_email = imap_client.fetch_email(uid, folder=folder)
            
        if not original_email:
            error_msg = f"Original email with UID {uid} not found in folder {folder}"
            logger.error(error_msg)
            return json.dumps({
                "status": "error",
                "message": error_msg
            })
            
        # Get the SMTP client
        smtp_client = get_smtp_client_from_context(ctx)
            
        # Create the reply MIME message
        if body_html:
            mime_message = smtp_client.create_reply_mime(
                original_email, 
                reply_body, 
                reply_all=reply_all, 
                cc=cc,
                body_html=body_html
            )
        else:
            mime_message = smtp_client.create_reply_mime(
                original_email, 
                reply_body, 
                reply_all=reply_all, 
                cc=cc
            )
            
        # Save the draft
        draft_uid = imap_client.save_draft_mime(mime_message)
            
        if draft_uid:
            logger.info(f"Draft reply created with UID {draft_uid}")
            return json.dumps({
                "status": "success",
                "message": "Draft reply created",
                "draft_uid": draft_uid
            })
        else:
            error_msg = "Failed to save draft reply"
            logger.error(error_msg)
            return json.dumps({
                "status": "error",
                "message": error_msg
            })
                
    except Exception as e:
        error_msg = f"Error creating draft reply: {e}"
        logger.error(error_msg)
        return json.dumps({
            "status": "error",
            "message": error_msg
        })
