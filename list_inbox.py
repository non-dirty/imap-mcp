#!/usr/bin/env python
"""
Simple script to list messages in Gmail inbox using the IMAP client directly.
"""

import argparse
import logging
import sys
from typing import Dict, List, Optional

from imap_mcp.config import load_config
from imap_mcp.imap_client import ImapClient


def main() -> None:
    """List emails in the inbox."""
    # Configure argument parser
    parser = argparse.ArgumentParser(description="List emails in Gmail inbox")
    parser.add_argument(
        "--config", 
        help="Path to configuration file", 
        default="config.yaml"
    )
    parser.add_argument(
        "--folder",
        help="Folder to list (default: INBOX)",
        default="INBOX"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of emails to display",
        default=10
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("imap_inbox")
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = load_config(args.config)
        
        # Create IMAP client
        logger.info(f"Connecting to {config.imap.host} as {config.imap.username}")
        client = ImapClient(config.imap)
        
        # Connect to IMAP server
        try:
            client.connect()
            logger.info("Successfully connected to IMAP server")
            
            # List available folders
            folders = client.list_folders()
            logger.info(f"Available folders: {', '.join(folders[:5])}{'...' if len(folders) > 5 else ''}")
            
            # Check if the requested folder exists
            if args.folder not in folders:
                logger.error(f"Folder '{args.folder}' does not exist")
                client.disconnect()
                sys.exit(1)
            
            # Search for all emails in the folder
            logger.info(f"Searching for emails in {args.folder}")
            uids = client.search("ALL", folder=args.folder)
            
            if not uids:
                logger.info(f"No emails found in {args.folder}")
                client.disconnect()
                return
            
            # Limit the number of emails to fetch
            uids = uids[:args.limit]
            
            # Fetch emails
            logger.info(f"Fetching {len(uids)} emails")
            emails = client.fetch_emails(uids, folder=args.folder)
            
            # Display emails
            print(f"\nFound {len(emails)} emails in {args.folder}:\n")
            for i, (uid, email) in enumerate(emails.items()):
                if not email:
                    continue
                
                print(f"--- Email {i+1}/{len(emails)} ---")
                print(f"UID: {uid}")
                print(f"From: {email.from_}")
                print(f"To: {', '.join(str(to) for to in email.to)}")
                print(f"Subject: {email.subject}")
                print(f"Date: {email.date}")
                
                # Show flags
                if email.flags:
                    print(f"Flags: {', '.join(email.flags)}")
                    
                # Show body preview
                content = email.content.get_best_content()
                if content:
                    preview = content[:100] + ('...' if len(content) > 100 else '')
                    print(f"Preview: {preview}")
                    
                print()
        finally:
            # Ensure we disconnect
            client.disconnect()
            logger.info("Disconnected from IMAP server")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
