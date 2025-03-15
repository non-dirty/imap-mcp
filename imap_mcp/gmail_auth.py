"""Gmail authentication setup command-line tool."""

import argparse
import logging
import os
import sys

from imap_mcp.browser_auth import perform_oauth_flow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run the Gmail authentication tool."""
    parser = argparse.ArgumentParser(description="Gmail authentication setup tool")
    parser.add_argument(
        "--client-id", 
        help="OAuth2 client ID (optional, will be loaded from credentials file if provided)",
    )
    parser.add_argument(
        "--client-secret", 
        help="OAuth2 client secret (optional, will be loaded from credentials file if provided)",
    )
    parser.add_argument(
        "--credentials-file",
        help="Path to the OAuth2 client credentials JSON file downloaded from Google Cloud Console",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for the callback server (default: 8080)",
    )
    parser.add_argument(
        "--config", 
        help="Path to existing config file to update",
    )
    parser.add_argument(
        "--output", 
        help="Path to save the updated config file (default: config.yaml)",
        default="config.yaml",
    )
    
    args = parser.parse_args()
    
    try:
        # Run the OAuth flow
        perform_oauth_flow(
            client_id=args.client_id,
            client_secret=args.client_secret,
            credentials_file=args.credentials_file,
            port=args.port,
            config_path=args.config,
            config_output=args.output,
        )
        logger.info("Gmail authentication setup completed successfully")
    except KeyboardInterrupt:
        logger.info("Gmail authentication setup canceled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Gmail authentication setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
