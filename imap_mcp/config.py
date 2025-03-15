"""Configuration handling for IMAP MCP server."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
load_dotenv()


@dataclass
class OAuth2Config:
    """OAuth2 configuration for IMAP authentication."""
    
    client_id: str
    client_secret: str
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    token_expiry: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["OAuth2Config"]:
        """Create OAuth2 configuration from dictionary."""
        if not data:
            return None
            
        # OAuth2 credentials can be specified in environment variables
        client_id = data.get("client_id") or os.environ.get("GMAIL_CLIENT_ID")
        client_secret = data.get("client_secret") or os.environ.get("GMAIL_CLIENT_SECRET")
        refresh_token = data.get("refresh_token") or os.environ.get("GMAIL_REFRESH_TOKEN")
        
        if not client_id or not client_secret:
            return None
            
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            access_token=data.get("access_token"),
            token_expiry=data.get("token_expiry"),
        )


@dataclass
class ImapConfig:
    """IMAP server configuration."""
    
    host: str
    port: int
    username: str
    password: Optional[str] = None
    oauth2: Optional[OAuth2Config] = None
    use_ssl: bool = True
    
    @property
    def is_gmail(self) -> bool:
        """Check if this is a Gmail configuration."""
        return self.host.endswith("gmail.com") or self.host.endswith("googlemail.com")
    
    @property
    def requires_oauth2(self) -> bool:
        """Check if this configuration requires OAuth2."""
        return self.is_gmail and self.oauth2 is not None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImapConfig":
        """Create configuration from dictionary."""
        # Create OAuth2 config if present
        oauth2_config = OAuth2Config.from_dict(data.get("oauth2", {}))
        
        # Password can be specified in environment variable
        password = data.get("password") or os.environ.get("IMAP_PASSWORD")
        
        # For Gmail, we need either password (for app-specific password) or OAuth2 credentials
        host = data.get("host", "")
        is_gmail = host.endswith("gmail.com") or host.endswith("googlemail.com")
        
        if is_gmail and not oauth2_config and not password:
            raise ValueError(
                "Gmail requires either an app-specific password or OAuth2 credentials"
            )
        elif not is_gmail and not password:
            raise ValueError(
                "IMAP password must be specified in config or IMAP_PASSWORD environment variable"
            )
        
        return cls(
            host=data["host"],
            port=data.get("port", 993 if data.get("use_ssl", True) else 143),
            username=data["username"],
            password=password,
            oauth2=oauth2_config,
            use_ssl=data.get("use_ssl", True),
        )


@dataclass
class ServerConfig:
    """MCP server configuration."""
    
    imap: ImapConfig
    allowed_folders: Optional[List[str]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerConfig":
        """Create configuration from dictionary."""
        return cls(
            imap=ImapConfig.from_dict(data.get("imap", {})),
            allowed_folders=data.get("allowed_folders"),
        )


def load_config(config_path: Optional[str] = None) -> ServerConfig:
    """Load configuration from file or environment variables.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Server configuration
    
    Raises:
        FileNotFoundError: If configuration file is not found
        ValueError: If configuration is invalid
    """
    # Default locations to check for config file
    default_locations = [
        Path("config.yaml"),
        Path("config.yml"),
        Path("~/.config/imap-mcp/config.yaml"),
        Path("/etc/imap-mcp/config.yaml"),
    ]
    
    # Load from specified path or try default locations
    config_data = {}
    if config_path:
        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {config_path}")
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {config_path}")
    else:
        for path in default_locations:
            expanded_path = path.expanduser()
            if expanded_path.exists():
                with open(expanded_path, "r") as f:
                    config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {expanded_path}")
                break
    
    # If environment variables are set, they take precedence
    if not config_data:
        logger.info("No configuration file found, using environment variables")
        if not os.environ.get("IMAP_HOST"):
            raise ValueError(
                "No configuration file found and IMAP_HOST environment variable not set"
            )
        
        config_data = {
            "imap": {
                "host": os.environ.get("IMAP_HOST"),
                "port": int(os.environ.get("IMAP_PORT", "993")),
                "username": os.environ.get("IMAP_USERNAME"),
                "password": os.environ.get("IMAP_PASSWORD"),
                "use_ssl": os.environ.get("IMAP_USE_SSL", "true").lower() == "true",
            }
        }
        
        if os.environ.get("IMAP_ALLOWED_FOLDERS"):
            config_data["allowed_folders"] = os.environ.get("IMAP_ALLOWED_FOLDERS").split(",")
    
    # Create config object
    try:
        return ServerConfig.from_dict(config_data)
    except KeyError as e:
        raise ValueError(f"Missing required configuration: {e}")
