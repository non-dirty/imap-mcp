"""OAuth2 utilities for IMAP authentication."""

import base64
import json
import logging
import time
from typing import Optional, Tuple

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from imap_mcp.config import OAuth2Config

logger = logging.getLogger(__name__)

# Gmail OAuth2 endpoints
GMAIL_TOKEN_URI = "https://oauth2.googleapis.com/token"
GMAIL_AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/auth"
GMAIL_SCOPES = ["https://mail.google.com/"]


def get_access_token(oauth2_config: OAuth2Config) -> Tuple[str, int]:
    """Get a valid access token for Gmail.
    
    Uses the refresh token to get a new access token if needed.
    
    Args:
        oauth2_config: OAuth2 configuration
        
    Returns:
        Tuple of (access_token, expiry_timestamp)
        
    Raises:
        ValueError: If unable to get an access token
    """
    # Check if we already have a valid access token
    current_time = int(time.time())
    
    # Handle token_expiry as either int timestamp or datetime string
    token_expiry = 0
    if oauth2_config.token_expiry:
        try:
            # Try to convert to int directly
            token_expiry = int(oauth2_config.token_expiry)
        except (ValueError, TypeError):
            # If it's a datetime string, try to parse it
            try:
                # Handle ISO format datetime strings
                from datetime import datetime
                expiry_dt = datetime.fromisoformat(str(oauth2_config.token_expiry).replace('Z', '+00:00'))
                token_expiry = int(expiry_dt.timestamp())
            except (ValueError, TypeError):
                # If parsing fails, force token refresh
                token_expiry = 0
    
    if (
        oauth2_config.access_token 
        and token_expiry > current_time + 300  # 5 min buffer
    ):
        return oauth2_config.access_token, token_expiry
    
    # Otherwise, use refresh token to get a new access token
    if not oauth2_config.refresh_token:
        raise ValueError("Refresh token is required for OAuth2 authentication")
    
    logger.info("Refreshing Gmail access token")
    
    # Exchange refresh token for access token
    data = {
        "client_id": oauth2_config.client_id,
        "client_secret": oauth2_config.client_secret,
        "refresh_token": oauth2_config.refresh_token,
        "grant_type": "refresh_token",
    }
    
    response = requests.post(GMAIL_TOKEN_URI, data=data)
    if response.status_code != 200:
        logger.error(f"Failed to refresh token: {response.text}")
        raise ValueError(f"Failed to refresh token: {response.status_code} - {response.text}")
    
    token_data = response.json()
    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
    expiry = int(time.time()) + expires_in
    
    # Update the config with the new token
    oauth2_config.access_token = access_token
    oauth2_config.token_expiry = expiry
    
    return access_token, expiry


def generate_oauth2_string(username: str, access_token: str) -> str:
    """Generate the SASL XOAUTH2 string for IMAP authentication.
    
    Args:
        username: Email address
        access_token: OAuth2 access token
        
    Returns:
        Base64-encoded XOAUTH2 string for IMAP authentication
    """
    auth_string = f"user={username}\1auth=Bearer {access_token}\1\1"
    return base64.b64encode(auth_string.encode()).decode()


def get_authorization_url(oauth2_config: OAuth2Config) -> str:
    """Generate the URL for the OAuth2 authorization flow.
    
    Args:
        oauth2_config: OAuth2 configuration
        
    Returns:
        URL to redirect the user to for authorization
    """
    params = {
        "client_id": oauth2_config.client_id,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",  # Desktop app flow
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # Force to get refresh_token
    }
    
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GMAIL_AUTH_BASE_URL}?{query_string}"


def exchange_code_for_tokens(oauth2_config: OAuth2Config, code: str) -> Tuple[str, str, int]:
    """Exchange authorization code for access and refresh tokens.
    
    Args:
        oauth2_config: OAuth2 configuration
        code: Authorization code from the redirect
        
    Returns:
        Tuple of (access_token, refresh_token, expiry_timestamp)
        
    Raises:
        ValueError: If unable to exchange the code
    """
    data = {
        "client_id": oauth2_config.client_id,
        "client_secret": oauth2_config.client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",  # Desktop app flow
    }
    
    response = requests.post(GMAIL_TOKEN_URI, data=data)
    if response.status_code != 200:
        raise ValueError(f"Failed to exchange code: {response.status_code} - {response.text}")
    
    token_data = response.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
    expiry = int(time.time()) + expires_in
    
    return access_token, refresh_token, expiry
