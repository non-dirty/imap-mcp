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

logger = logging.getLogger(__name__)

# Define the path for storing tasks
TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tasks.json")


def register_tools(mcp: FastMCP, imap_client: ImapClient) -> None:
    """Register MCP tools.
    
    Args:
        mcp: MCP server
        imap_client: IMAP client
    """
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
    
    # Create task (mock implementation)
    @mcp.tool()
    async def create_task(
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
    @mcp.tool()
    async def draft_reply_tool(
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
