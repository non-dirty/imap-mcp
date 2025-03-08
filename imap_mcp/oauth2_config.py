"""
OAuth2 configuration handling for Gmail authentication.

This module provides utilities for loading and validating OAuth2 configuration
from either config files or environment variables.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from .config import ServerConfig


class OAuth2Config:
    """Handles OAuth2 configuration for Gmail authentication."""

    def __init__(
        self,
        credentials_file: str,
        token_file: str,
        scopes: list[str],
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize OAuth2 configuration.

        Args:
            credentials_file: Path to the client credentials JSON file
            token_file: Path to store the OAuth2 tokens
            scopes: List of OAuth2 scopes to request
            client_id: Optional client ID (overrides credentials file)
            client_secret: Optional client secret (overrides credentials file)
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = scopes
        self._client_id = client_id
        self._client_secret = client_secret
        self._client_config = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuth2Config":
        """
        Create OAuth2Config from a dictionary.

        Args:
            data: Dictionary with OAuth2 configuration

        Returns:
            OAuth2Config instance with values from the dictionary
        """
        if not data:
            return cls(
                credentials_file="",
                token_file="gmail_token.json",
                scopes=["https://mail.google.com/"]
            )
            
        credentials_file = data.get("credentials_file", "")
        token_file = data.get("token_file", "gmail_token.json")
        scopes = data.get("scopes", ["https://mail.google.com/"])
        
        # Environment variables override config file
        client_id = os.environ.get("GMAIL_CLIENT_ID")
        client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
        
        return cls(
            credentials_file=credentials_file,
            token_file=token_file,
            scopes=scopes,
            client_id=client_id,
            client_secret=client_secret,
        )
        
    @classmethod
    def from_server_config(cls, config: ServerConfig) -> "OAuth2Config":
        """
        Create OAuth2Config from ServerConfig.

        Args:
            config: The server configuration object

        Returns:
            OAuth2Config instance with values from server config
        """
        # Get values from config.oauth2 if present
        if hasattr(config, "oauth2") and config.oauth2:
            oauth2_config = config.oauth2
            credentials_file = oauth2_config.get("credentials_file", "")
            token_file = oauth2_config.get("token_file", "gmail_token.json")
            scopes = oauth2_config.get("scopes", ["https://mail.google.com/"])
        else:
            credentials_file = ""
            token_file = "gmail_token.json"
            scopes = ["https://mail.google.com/"]

        # Environment variables override config file
        client_id = os.environ.get("GMAIL_CLIENT_ID")
        client_secret = os.environ.get("GMAIL_CLIENT_SECRET")

        return cls(
            credentials_file=credentials_file,
            token_file=token_file,
            scopes=scopes,
            client_id=client_id,
            client_secret=client_secret,
        )

    def load_client_config(self) -> Dict[str, Any]:
        """
        Load the client configuration from the credentials file.

        Returns:
            Dict containing the client configuration
        
        Raises:
            FileNotFoundError: If the credentials file doesn't exist
            ValueError: If the credentials file is invalid
        """
        if self._client_config:
            return self._client_config

        # If client ID and secret are provided directly, create the config structure
        if self._client_id and self._client_secret:
            self._client_config = {
                "installed": {
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
            return self._client_config

        # Otherwise load from the credentials file
        if not self.credentials_file:
            raise ValueError("No credentials file specified and no client ID/secret provided")

        credentials_path = Path(self.credentials_file)
        if not credentials_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")

        try:
            with open(credentials_path) as f:
                self._client_config = json.load(f)
            return self._client_config
        except json.JSONDecodeError:
            raise ValueError(f"Invalid credentials file: {self.credentials_file}")

    @property
    def client_id(self) -> str:
        """Get the client ID from the configuration."""
        if self._client_id:
            return self._client_id
        
        config = self.load_client_config()
        return config.get("installed", {}).get("client_id", "")

    @property
    def client_secret(self) -> str:
        """Get the client secret from the configuration."""
        if self._client_secret:
            return self._client_secret
        
        config = self.load_client_config()
        return config.get("installed", {}).get("client_secret", "")
