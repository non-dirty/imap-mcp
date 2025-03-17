"""
Test the OAuth2 Gmail authentication with the IMAP client.
"""

import logging
import os
import pytest
from dotenv import load_dotenv

from imap_mcp.config import ImapConfig, OAuth2Config
from imap_mcp.imap_client import ImapClient

# Load environment variables from .env.test if it exists
load_dotenv(".env.test")

# Required environment variables for OAuth2 testing
REQUIRED_ENV_VARS = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN", "GMAIL_TEST_EMAIL"]

@pytest.mark.skipif(
    any(os.environ.get(var) is None for var in REQUIRED_ENV_VARS),
    reason="Gmail OAuth2 credentials are required for this test"
)
def test_oauth2_gmail_connection():
    """
    Test connecting to Gmail using OAuth2 authentication.
    """
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Create ImapConfig with OAuth2 settings from environment variables
        logger.info("Setting up OAuth2 configuration from environment variables")
        config = ImapConfig(
            host="imap.gmail.com",
            port=993,
            username=os.environ.get("GMAIL_TEST_EMAIL"),
            password=None,  # No password for OAuth2
            use_ssl=True,
            oauth2=OAuth2Config(
                client_id=os.environ.get("GMAIL_CLIENT_ID"),
                client_secret=os.environ.get("GMAIL_CLIENT_SECRET"),
                refresh_token=os.environ.get("GMAIL_REFRESH_TOKEN"),
            )
        )
        
        # Create and connect IMAP client
        logger.info(f"Connecting to {config.host}:{config.port} as {config.username}")
        client = ImapClient(config)
        
        # Test connection
        logger.info("Connecting to IMAP server")
        client.connect()
        
        # List folders to verify connection
        folders = client.list_folders()
        logger.info(f"Found {len(folders)} folders")
        
        # Disconnect
        logger.info("Disconnecting")
        client.disconnect()
        
        # If we got here, the test passed
        assert True, "Successfully connected to Gmail with OAuth2"
    except Exception as e:
        logger.error(f"Error: {e}")
        pytest.fail(f"Failed to connect using OAuth2: {e}")
