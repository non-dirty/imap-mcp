"""
Test the OAuth2 Gmail authentication with the IMAP client.
"""

import logging
import os
import pytest
from pathlib import Path

from imap_mcp.config import load_config
from imap_mcp.imap_client import ImapClient


@pytest.fixture
def config_path():
    """
    Fixture to provide the config path.
    
    Returns:
        Path to the configuration file if it exists, otherwise None
    """
    # Look for config in common locations
    possible_paths = [
        os.environ.get("IMAP_CONFIG_PATH"),
        Path("./config.yaml"),
        Path("./tests/test_config.yaml"),
        Path.home() / ".config/imap-mcp/config.yaml"
    ]
    
    for path in possible_paths:
        if path and Path(path).exists():
            return str(path)
    
    return None


@pytest.mark.skipif(
    os.environ.get("GMAIL_CLIENT_ID") is None or 
    os.environ.get("GMAIL_CLIENT_SECRET") is None,
    reason="Gmail OAuth2 credentials are required for this test"
)
def test_oauth2_gmail_connection(config_path):
    """
    Test connecting to Gmail using OAuth2 authentication.
    
    Args:
        config_path: Path to the configuration file
    """
    # Skip if no config path is found
    if config_path is None:
        pytest.skip("No configuration file found")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from {config_path}")
        config = load_config(config_path)
        
        # Create IMAP client
        logger.info(f"Connecting to {config.imap.host}:{config.imap.port} as {config.imap.username}")
        client = ImapClient(config.imap)
        
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
        assert True
    except Exception as e:
        logger.error(f"Error: {e}")
        pytest.fail(f"Failed to connect using OAuth2: {e}")
