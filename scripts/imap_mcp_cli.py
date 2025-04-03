#!/usr/bin/env python3
"""
MCP Command Line Interface for IMAP operations.

This script provides a command-line interface to interact with the IMAP MCP system,
allowing users to perform operations such as listing emails, processing meeting invites,
and managing drafts.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Add project root to path so we can import imap_mcp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from imap_mcp.config import load_config
from imap_mcp.imap_client import ImapClient
from imap_mcp.workflows.invite_parser import identify_meeting_invite_details
from imap_mcp.workflows.calendar_mock import check_mock_availability
from imap_mcp.workflows.meeting_reply import generate_meeting_reply_content
from imap_mcp.smtp_client import create_reply_mime
from imap_mcp.models import EmailAddress


def setup_logging(verbose=False):
    """Set up logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def create_imap_client(config_path=None):
    """Create and return an IMAP client using the specified or default config."""
    try:
        config = load_config(config_path)
        return ImapClient(config.imap)
    except Exception as e:
        logging.error(f"Failed to create IMAP client: {e}")
        sys.exit(1)


def list_folders(args):
    """List available folders in the IMAP account."""
    client = create_imap_client(args.config)
    try:
        client.connect()
        folders = client.list_folders(True)  # Force refresh
        print("Available folders:")
        for folder in folders:
            print(f"- {folder}")
    finally:
        client.disconnect()


def list_emails(args):
    """List emails in the specified folder."""
    client = create_imap_client(args.config)
    try:
        client.connect()
        print(f"Fetching latest {args.count} emails from {args.folder}...")
        emails = client.list_emails(args.folder, max_count=args.count)
        
        if not emails:
            print(f"No emails found in {args.folder}.")
            return
            
        # Print as a formatted table
        print(f"\n{'UID':<10} {'Date':<20} {'From':<30} {'Subject':<50}")
        print("-" * 110)
        
        for email in emails:
            sender = str(email.from_)
            if len(sender) > 28:
                sender = sender[:25] + "..."
                
            subject = email.subject
            if len(subject) > 48:
                subject = subject[:45] + "..."
                
            print(f"{email.uid:<10} {email.date.strftime('%Y-%m-%d %H:%M'):<20} {sender:<30} {subject:<50}")
    finally:
        client.disconnect()


def process_invite(args):
    """Process a meeting invite email and create a draft reply."""
    client = create_imap_client(args.config)
    try:
        client.connect()
        
        # Step 1: Fetch the original email
        print(f"Fetching email UID {args.uid} from folder {args.folder}")
        email_obj = client.fetch_email(args.uid, args.folder)
        
        if not email_obj:
            print(f"Error: Email with UID {args.uid} not found in folder {args.folder}")
            return 1
        
        # Step 2: Identify if it's a meeting invite
        print(f"Analyzing email for meeting invite details: {email_obj.subject}")
        invite_result = identify_meeting_invite_details(email_obj)
        
        if not invite_result["is_invite"]:
            print("Error: The email is not a meeting invite")
            return 1
        
        invite_details = invite_result["details"]
        print("\nMeeting details found:")
        print(f"  Subject: {invite_details.get('subject', 'N/A')}")
        print(f"  Organizer: {invite_details.get('organizer', 'N/A')}")
        print(f"  Start time: {invite_details.get('start_time', 'N/A')}")
        print(f"  End time: {invite_details.get('end_time', 'N/A')}")
        print(f"  Location: {invite_details.get('location', 'N/A')}")
        
        # Step 3: Check calendar availability
        print(f"\nChecking calendar availability using mode: {args.availability_mode}")
        availability_result = check_mock_availability(
            invite_details.get("start_time"),
            invite_details.get("end_time"),
            args.availability_mode
        )
        
        print(f"Availability result: {'Available' if availability_result['available'] else 'Busy'}")
        print(f"Reason: {availability_result.get('reason', 'No reason provided')}")
        
        # Step 4: Generate reply content
        action = "accept" if availability_result["available"] else "decline"
        print(f"\nGenerating {action} reply content...")
        reply_content = generate_meeting_reply_content(invite_details, availability_result)
        
        # Step 5: Create MIME message for reply
        print("Creating MIME message for the reply...")
        # Determine sender for the reply (use original recipient if available)
        if email_obj.to and len(email_obj.to) > 0:
            reply_from = email_obj.to[0]
        else:
            # Fallback to config username if no 'To' field in original email
            reply_from = EmailAddress(
                name="Me",
                address=client.config.username
            )
        
        mime_message = create_reply_mime(
            original_email=email_obj,
            reply_to=reply_from,
            body=reply_content["reply_body"],
            subject=reply_content["reply_subject"],
            reply_all=False # Meeting replies usually go only to organizer
        )
        
        # Step 6: Save as draft or show dry run info
        if args.dry_run:
            print("\n--- DRY RUN --- (No draft will be saved)")
            print(f"Reply type: {reply_content['reply_type']}")
            print(f"Subject: {reply_content['reply_subject']}")
            print("Body preview:")
            print(reply_content['reply_body'])
            print("---")
            return 0
        
        print("Saving reply as a draft...")
        draft_uid = client.save_draft_mime(mime_message)
        
        if draft_uid:
            drafts_folder = client._get_drafts_folder()
            print(f"\nSuccess! Draft reply saved:")
            print(f"  Type: {reply_content['reply_type']}")
            print(f"  Folder: {drafts_folder}")
            print(f"  UID: {draft_uid}")
            return 0
        else:
            print("\nError: Failed to save the draft email.")
            return 1
            
    except Exception as e:
        logging.exception("Error during meeting invite processing:")
        print(f"An unexpected error occurred: {e}")
        return 1
    finally:
        client.disconnect()


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="IMAP MCP Command Line Interface")
    parser.add_argument("--config", "-c", help="Path to configuration file (e.g., config.toml)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")
    
    # List folders command
    list_folders_parser = subparsers.add_parser("list-folders", help="List available IMAP folders")
    list_folders_parser.set_defaults(func=list_folders)
    
    # List emails command
    list_emails_parser = subparsers.add_parser("list-emails", help="List emails in a specified folder")
    list_emails_parser.add_argument("folder", help="Folder to list emails from (e.g., INBOX)")
    list_emails_parser.add_argument("--count", "-n", type=int, default=10, help="Maximum number of emails to list")
    list_emails_parser.set_defaults(func=list_emails)
    
    # Process invite command
    process_invite_parser = subparsers.add_parser("process-invite", help="Process a meeting invite and create a draft reply")
    process_invite_parser.add_argument("folder", help="Folder containing the invite email (e.g., INBOX)")
    process_invite_parser.add_argument("uid", type=int, help="UID of the invite email")
    process_invite_parser.add_argument("--availability-mode", "-a", default="random", 
                                      choices=["random", "always_available", "always_busy", "business_hours", "weekdays"],
                                      help="Mock availability mode for calendar check")
    process_invite_parser.add_argument("--dry-run", "-d", action="store_true", 
                                      help="Perform all steps except saving the draft")
    process_invite_parser.set_defaults(func=process_invite)
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    logging.info(f"Executing command: {args.command}")
    exit_code = args.func(args)
    logging.info(f"Command finished with exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
