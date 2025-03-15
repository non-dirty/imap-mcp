"""Gmail app password authentication setup."""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)


def setup_app_password(
    username: str,
    password: str,
    config_path: Optional[str] = None,
    config_output: Optional[str] = None,
) -> Dict:
    """Set up Gmail with an app password.
    
    Args:
        username: Gmail email address
        password: App password generated from Google Account
        config_path: Path to existing config file to update (optional)
        config_output: Path to save the updated config file (optional)
        
    Returns:
        Updated configuration dictionary
    """
    # Load existing config if specified
    config_data = {}
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded existing configuration from {config_path}")
    
    # Update config with Gmail settings using app password
    if "imap" not in config_data:
        config_data["imap"] = {}
    
    config_data["imap"].update({
        "host": "imap.gmail.com",
        "port": 993,
        "username": username,
        "password": password,
        "use_ssl": True
    })
    
    # Remove any oauth2 config if it exists
    if "oauth2" in config_data["imap"]:
        del config_data["imap"]["oauth2"]
    
    # Save updated config if output path specified
    if config_output:
        output_file = Path(config_output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)
            logger.info(f"Saved updated configuration to {config_output}")
    
    print("\nConfiguration updated for Gmail using app password")
    print("\nTo use these credentials, add them to your config.yaml file or set environment variables:")
    print(f"  IMAP_PASSWORD={password}")
    
    return config_data


def main():
    """Run the Gmail app password setup tool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Configure Gmail with app password")
    parser.add_argument(
        "--username", 
        help="Gmail email address",
        default=os.environ.get("GMAIL_USERNAME"),
    )
    parser.add_argument(
        "--password", 
        help="App password from Google Account",
        default=os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("IMAP_PASSWORD"),
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
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Prompt for username if not provided
    username = args.username
    if not username:
        username = input("Enter your Gmail address: ").strip()
        if not username:
            print("Error: Gmail address is required")
            sys.exit(1)
    
    # Prompt for password if not provided
    password = args.password
    if not password:
        import getpass
        password = getpass.getpass("Enter your Gmail app password: ").strip()
        if not password:
            print("Error: App password is required")
            sys.exit(1)
    
    try:
        setup_app_password(
            username=username,
            password=password,
            config_path=args.config,
            config_output=args.output,
        )
        logger.info("Gmail app password setup completed successfully")
    except Exception as e:
        logger.error(f"Gmail app password setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
