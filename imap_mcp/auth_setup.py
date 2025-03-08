"""Command-line tool for setting up OAuth2 authentication for Gmail."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from imap_mcp.config import OAuth2Config
from imap_mcp.browser_auth import load_client_credentials
from imap_mcp.oauth2 import get_authorization_url, exchange_code_for_tokens

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_gmail_oauth2(
    client_id: Optional[str] = None, 
    client_secret: Optional[str] = None,
    credentials_file: Optional[str] = None,
    config_path: Optional[str] = None,
    config_output: Optional[str] = None,
) -> Dict[str, Any]:
    """Set up OAuth2 authentication for Gmail.
    
    Args:
        client_id: Google API client ID
        client_secret: Google API client secret
        config_path: Path to existing config file to update (optional)
        config_output: Path to save the updated config file (optional)
        
    Returns:
        Updated configuration dictionary
    """
    # Load credentials from file if provided
    if credentials_file and not (client_id and client_secret):
        try:
            logger.info(f"Loading credentials from {credentials_file}")
            client_id, client_secret = load_client_credentials(credentials_file)
            logger.info("Successfully loaded credentials from file")
        except Exception as e:
            logger.error(f"Failed to load credentials from file: {e}")
            sys.exit(1)
    
    # Verify we have the required credentials
    if not client_id or not client_secret:
        logger.error("Client ID and Client Secret are required")
        print("\nYou must provide either:")
        print("  1. Client ID and Client Secret directly, or")
        print("  2. Path to the credentials JSON file downloaded from Google Cloud Console")
        sys.exit(1)
    
    # Create temporary OAuth2 config
    oauth2_config = OAuth2Config(
        client_id=client_id,
        client_secret=client_secret,
    )
    
    # Generate authorization URL
    auth_url = get_authorization_url(oauth2_config)
    
    print(f"\n\n1. Open the following URL in your browser:\n\n{auth_url}\n")
    print("2. Sign in with your Google account and grant access to your Gmail")
    print("3. Copy the authorization code that Google provides after authorization\n")
    
    # Get authorization code from user
    auth_code = input("Enter the authorization code: ").strip()
    
    # Exchange authorization code for tokens
    try:
        access_token, refresh_token, expiry = exchange_code_for_tokens(oauth2_config, auth_code)
        logger.info("Successfully obtained access and refresh tokens")
    except Exception as e:
        logger.error(f"Failed to obtain tokens: {e}")
        sys.exit(1)
    
    # Build OAuth2 configuration
    oauth2_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "access_token": access_token,
        "token_expiry": expiry,
    }
    
    # Load existing config if specified
    config_data = {}
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded existing configuration from {config_path}")
    
    # Update config with OAuth2 data
    if "imap" not in config_data:
        config_data["imap"] = {}
    
    config_data["imap"]["oauth2"] = oauth2_data
    
    # Save updated config if output path specified
    if config_output:
        output_file = Path(config_output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)
            logger.info(f"Saved updated configuration to {config_output}")
    
    print("\nConfiguration:")
    print(json.dumps(oauth2_data, indent=2))
    print("\nTo use these credentials, add them to your config.yaml file under the imap.oauth2 key.")
    print("Alternatively, you can set the following environment variables:")
    print(f"  GMAIL_CLIENT_ID={client_id}")
    print(f"  GMAIL_CLIENT_SECRET={client_secret}")
    print(f"  GMAIL_REFRESH_TOKEN={refresh_token}")
    
    return config_data


def main() -> None:
    """Run the OAuth2 setup tool."""
    parser = argparse.ArgumentParser(description="Set up OAuth2 authentication for Gmail")
    parser.add_argument(
        "--client-id", 
        help="Google API client ID (optional if credentials file is provided)",
        default=os.environ.get("GMAIL_CLIENT_ID"),
    )
    parser.add_argument(
        "--client-secret", 
        help="Google API client secret (optional if credentials file is provided)",
        default=os.environ.get("GMAIL_CLIENT_SECRET"),
    )
    parser.add_argument(
        "--credentials-file",
        help="Path to the OAuth2 client credentials JSON file downloaded from Google Cloud Console",
    )
    parser.add_argument(
        "--config", 
        help="Path to existing config file to update",
        default=None,
    )
    parser.add_argument(
        "--output", 
        help="Path to save the updated config file",
        default="config.yaml",
    )
    
    args = parser.parse_args()
    
    # We'll check credentials in setup_gmail_oauth2 after trying to load from the credentials file
    
    setup_gmail_oauth2(
        client_id=args.client_id,
        client_secret=args.client_secret,
        credentials_file=args.credentials_file,
        config_path=args.config,
        config_output=args.output,
    )


if __name__ == "__main__":
    main()
