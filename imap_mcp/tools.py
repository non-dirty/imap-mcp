"""MCP tools implementation for email operations."""

import json
import logging
from typing import Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP
from mcp.server.types import Context

from imap_mcp.imap_client import ImapClient
from imap_mcp.resources import get_client_from_context

logger = logging.getLogger(__name__)


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
        flag: bool = True,
        ctx: Context,
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
        folder: Optional[str] = None,
        criteria: str = "text",
        limit: int = 10,
        ctx: Context,
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
        notes: Optional[str] = None,
        target_folder: Optional[str] = None,
        ctx: Context,
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
