"""MCP resources implementation for email access."""

import json
import logging

from mcp.server.fastmcp import FastMCP, Context

from imap_mcp.imap_client import ImapClient
from imap_mcp.models import Email
import imap_mcp.smtp_client as smtp_client

logger = logging.getLogger(__name__)


def get_client_from_context(ctx: Context) -> ImapClient:
    """Get IMAP client from context.
    
    Args:
        ctx: MCP context
        
    Returns:
        IMAP client
        
    Raises:
        RuntimeError: If IMAP client is not available
    """
    client = ctx.request_context.lifespan_context.get("imap_client")
    if not client:
        raise RuntimeError("IMAP client not available")
    return client


def get_smtp_client_from_context(ctx: Context) -> smtp_client:
    """Get SMTP client from context.
    
    Args:
        ctx: MCP context
        
    Returns:
        SMTP client
        
    Raises:
        RuntimeError: If SMTP client is not available
    """
    client = ctx.request_context.lifespan_context.get("smtp_client")
    if not client:
        raise RuntimeError("SMTP client not available")
    return client


def register_resources(mcp: FastMCP, imap_client: ImapClient) -> None:
    """Register MCP resources.
    
    Args:
        mcp: MCP server
        imap_client: IMAP client
    """
    # Define a wrapper for the folders resource
    async def get_folders_impl(ctx: Context) -> str:
        """Implementation for listing folders."""
        client = get_client_from_context(ctx)
        folders = client.list_folders()
        return json.dumps(folders, indent=2)
    
    # List folders resource
    @mcp.resource("email://folders")
    async def get_folders() -> str:
        """List available email folders.
        
        Returns:
            JSON-formatted list of folders
        """
        # Get context from the global context manager
        ctx = Context.get_current()
        return await get_folders_impl(ctx)
        """List available email folders.
        
        Returns:
            JSON-formatted list of folders
        """
    
    # Define a wrapper for the list emails resource
    async def list_emails_impl(ctx: Context, folder: str) -> str:
        """Implementation for listing emails."""
        client = get_client_from_context(ctx)
        
        try:
            # Search for all emails in folder
            uids = client.search("ALL", folder=folder)
            
            if not uids:
                return json.dumps([])
            
            # Fetch emails with specified UIDs
            emails = client.fetch_emails(uids, folder=folder)
            
            # Convert to list of dictionaries for JSON output
            results = []
            for uid, email in emails.items():
                if not email:
                    continue
                
                results.append({
                    "uid": uid,
                    "folder": folder,
                    "from": str(email.from_),
                    "to": [str(to) for to in email.to],
                    "subject": email.subject,
                    "date": email.date.isoformat() if email.date else None,
                    "snippet": email.get_snippet(100),
                    "flags": email.flags,
                    "has_attachments": bool(email.attachments)
                })
            
            return json.dumps(results, indent=2)
        except Exception as e:
            logging.error(f"Error listing emails: {e}")
            return f"Error: {e}"
    
    # List email summaries in a folder
    @mcp.resource("email://{folder}/list")
    async def list_emails(folder: str) -> str:
        """List emails in a folder.
        
        Args:
            folder: Folder name
            
        Returns:
            JSON-formatted list of email summaries
        """
        # Get context from the global context manager
        ctx = Context.get_current()
        client = get_client_from_context(ctx)
        
        # Search for all emails in the folder
        try:
            uids = client.search("ALL", folder=folder)
            
            # Limit to the 50 most recent emails to avoid overwhelming
            # the LLM with too much context
            uids = sorted(uids, reverse=True)[:50]
            
            # Fetch emails
            emails = client.fetch_emails(uids, folder=folder)
            
            # Create summaries
            summaries = []
            for uid, email_obj in emails.items():
                summaries.append({
                    "uid": uid,
                    "folder": folder,
                    "from": str(email_obj.from_),
                    "to": [str(to) for to in email_obj.to],
                    "subject": email_obj.subject,
                    "date": email_obj.date.isoformat() if email_obj.date else None,
                    "flags": email_obj.flags,
                    "has_attachments": len(email_obj.attachments) > 0,
                })
            
            return json.dumps(summaries, indent=2)
        except Exception as e:
            logger.error(f"Error listing emails: {e}")
            return f"Error: {e}"
    
    # Search emails across folders
    @mcp.resource("email://search/{query}")
    async def search_emails(query: str) -> str:
        """Search for emails across folders.
        
        Args:
            query: Search query (format depends on search mode)
            
        Returns:
            JSON-formatted list of email summaries
        """
        # Get context from the global context manager
        ctx = Context.get_current()
        client = get_client_from_context(ctx)
        
        # Get all folders
        folders = client.list_folders()
        results = []
        
        for folder in folders:
            try:
                # Customize the search criteria based on the query
                if query.lower() in ["all", "unseen", "seen", "today", "week", "month"]:
                    # Predefined searches
                    uids = client.search(query, folder=folder)
                else:
                    # Text search
                    uids = client.search(["TEXT", query], folder=folder)
                
                # Limit results per folder
                uids = sorted(uids, reverse=True)[:10]
                
                if uids:
                    # Fetch emails
                    emails = client.fetch_emails(uids, folder=folder)
                    
                    # Create summaries
                    for uid, email_obj in emails.items():
                        results.append({
                            "uid": uid,
                            "folder": folder,
                            "from": str(email_obj.from_),
                            "to": [str(to) for to in email_obj.to],
                            "subject": email_obj.subject,
                            "date": email_obj.date.isoformat() if email_obj.date else None,
                            "flags": email_obj.flags,
                            "has_attachments": len(email_obj.attachments) > 0,
                        })
            except Exception as e:
                logger.warning(f"Error searching folder {folder}: {e}")
        
        # Sort results by date (newest first)
        results.sort(
            key=lambda x: x.get("date") or "0", 
            reverse=True
        )
        
        return json.dumps(results, indent=2)
    
    # Get a specific email by UID
    @mcp.resource("email://{folder}/{uid}")
    async def get_email(folder: str, uid: str) -> str:
        """Get a specific email.
        
        Args:
            folder: Folder name
            uid: Email UID
            
        Returns:
            Email content in text format
        """
        # Get context from the global context manager
        ctx = Context.get_current()
        client = get_client_from_context(ctx)
        
        try:
            # Fetch email
            email_obj = client.fetch_email(int(uid), folder=folder)
            
            if not email_obj:
                return f"Email with UID {uid} not found in folder {folder}"
            
            # Format email as text
            parts = [
                f"From: {email_obj.from_}",
                f"To: {', '.join(str(to) for to in email_obj.to)}",
            ]
            
            if email_obj.cc:
                parts.append(f"Cc: {', '.join(str(cc) for cc in email_obj.cc)}")
            
            if email_obj.date:
                parts.append(f"Date: {email_obj.date.isoformat()}")
            
            parts.append(f"Subject: {email_obj.subject}")
            parts.append(f"Flags: {', '.join(email_obj.flags)}")
            
            if email_obj.attachments:
                parts.append(f"Attachments: {len(email_obj.attachments)}")
                for i, attachment in enumerate(email_obj.attachments, 1):
                    parts.append(f"  {i}. {attachment.filename} ({attachment.content_type}, {attachment.size} bytes)")
            
            parts.append("")  # Empty line before content
            
            # Add email content
            content = email_obj.content.get_best_content()
            parts.append(content)
            
            return "\n".join(parts)
        except Exception as e:
            logger.error(f"Error fetching email: {e}")
            return f"Error: {e}"
