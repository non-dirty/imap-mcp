#!/usr/bin/env python
"""
Script to read messages from Gmail inbox using the IMAP MCP server.
"""

import argparse
import json
import sys
from typing import Dict, List, Optional

import requests


def list_folders() -> None:
    """List all available email folders."""
    response = requests.get("http://localhost:8000/folders")
    if response.status_code == 200:
        folders = response.json()
        print("\nAvailable folders:")
        for folder in folders:
            print(f"  - {folder}")
    else:
        print(f"Error listing folders: {response.status_code} - {response.text}")


def get_emails(folder: str = "INBOX", limit: int = 10) -> None:
    """Get emails from a specific folder.
    
    Args:
        folder: Folder name (default: INBOX)
        limit: Maximum number of emails to retrieve
    """
    params = {"limit": limit}
    response = requests.get(f"http://localhost:8000/emails/{folder}", params=params)
    
    if response.status_code == 200:
        emails = response.json()
        if not emails:
            print(f"\nNo emails found in {folder}")
            return
            
        print(f"\nFound {len(emails)} emails in {folder}:")
        for i, email in enumerate(emails):
            print(f"\n--- Email {i+1}/{len(emails)} ---")
            print(f"UID: {email.get('uid')}")
            print(f"From: {email.get('from')}")
            print(f"To: {email.get('to')}")
            print(f"Subject: {email.get('subject')}")
            print(f"Date: {email.get('date')}")
            print(f"Has Attachments: {'Yes' if email.get('has_attachments') else 'No'}")
            
            # Print flags
            flags = email.get('flags', [])
            if flags:
                flag_str = ', '.join(flags)
                print(f"Flags: {flag_str}")
                
            # Show preview of body
            body = email.get('body', '')
            if body:
                preview = body[:200] + ('...' if len(body) > 200 else '')
                print(f"\nPreview: {preview}")
    else:
        print(f"Error fetching emails: {response.status_code} - {response.text}")


def get_email_detail(folder: str, uid: int) -> None:
    """Get detailed information about a specific email.
    
    Args:
        folder: Folder name
        uid: Email UID
    """
    response = requests.get(f"http://localhost:8000/email/{folder}/{uid}")
    
    if response.status_code == 200:
        email = response.json()
        print("\n--- Email Details ---")
        print(f"UID: {email.get('uid')}")
        print(f"From: {email.get('from')}")
        print(f"To: {email.get('to')}")
        print(f"Subject: {email.get('subject')}")
        print(f"Date: {email.get('date')}")
        print(f"Has Attachments: {'Yes' if email.get('has_attachments') else 'No'}")
        
        # Print flags
        flags = email.get('flags', [])
        if flags:
            flag_str = ', '.join(flags)
            print(f"Flags: {flag_str}")
            
        # Show full body
        body = email.get('body', '')
        if body:
            print("\nBody:")
            print(body)
    else:
        print(f"Error fetching email: {response.status_code} - {response.text}")


def search_emails(query: str, folder: Optional[str] = None, criteria: str = "text") -> None:
    """Search for emails.
    
    Args:
        query: Search query
        folder: Folder to search in (None for all folders)
        criteria: Search criteria (text, from, to, subject)
    """
    params = {
        "query": query,
        "criteria": criteria,
    }
    
    if folder:
        params["folder"] = folder
        
    response = requests.get("http://localhost:8000/search", params=params)
    
    if response.status_code == 200:
        results = response.json()
        if not results:
            print(f"\nNo emails found matching '{query}'")
            return
            
        print(f"\nFound {len(results)} emails matching '{query}':")
        for i, result in enumerate(results):
            print(f"\n--- Result {i+1}/{len(results)} ---")
            print(f"UID: {result.get('uid')}")
            print(f"Folder: {result.get('folder')}")
            print(f"From: {result.get('from')}")
            print(f"Subject: {result.get('subject')}")
            print(f"Date: {result.get('date')}")
    else:
        print(f"Error searching emails: {response.status_code} - {response.text}")


def main() -> None:
    """Run the email reader script."""
    parser = argparse.ArgumentParser(description="Read emails from IMAP MCP server")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List folders command
    folders_parser = subparsers.add_parser("folders", help="List available folders")
    
    # List emails command
    list_parser = subparsers.add_parser("list", help="List emails in a folder")
    list_parser.add_argument("--folder", "-f", default="INBOX", help="Folder to list emails from")
    list_parser.add_argument("--limit", "-l", type=int, default=10, help="Maximum number of emails to retrieve")
    
    # View email command
    view_parser = subparsers.add_parser("view", help="View a specific email")
    view_parser.add_argument("--folder", "-f", default="INBOX", help="Folder containing the email")
    view_parser.add_argument("--uid", "-u", type=int, required=True, help="UID of the email to view")
    
    # Search emails command
    search_parser = subparsers.add_parser("search", help="Search for emails")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--folder", "-f", help="Folder to search in (default: all folders)")
    search_parser.add_argument("--criteria", "-c", default="text", 
                              choices=["text", "from", "to", "subject"],
                              help="Search criteria")
    
    args = parser.parse_args()
    
    # Default command if none specified
    if not args.command:
        list_folders()
        get_emails()
        return
        
    # Execute selected command
    if args.command == "folders":
        list_folders()
    elif args.command == "list":
        get_emails(args.folder, args.limit)
    elif args.command == "view":
        get_email_detail(args.folder, args.uid)
    elif args.command == "search":
        search_emails(args.query, args.folder, args.criteria)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the IMAP MCP server. Make sure it's running on http://localhost:8000.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
