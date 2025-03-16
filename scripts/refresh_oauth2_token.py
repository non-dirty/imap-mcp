#!/usr/bin/env python3
"""
Gmail OAuth2 Token Refresher Utility

This script helps refresh OAuth2 tokens for Gmail integration testing by:
1. Reading credentials from config.yaml
2. Opening a browser for authentication
3. Handling the callback
4. Updating tokens in the config

Usage:
    python refresh_oauth2_token.py [--config CONFIG_PATH]

Requirements:
    pip install google-auth google-auth-oauthlib pyyaml
"""

import argparse
import json
import logging
import os
import sys
import webbrowser
from pathlib import Path
from typing import Dict, Optional

import yaml
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gmail OAuth2 scopes
SCOPES = ['https://mail.google.com/']


def load_config(config_path: str) -> Dict:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to the config file
        
    Returns:
        Dictionary with configuration
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            return config
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        sys.exit(1)


def save_config(config_path: str, config: Dict) -> None:
    """Save configuration to YAML file.
    
    Args:
        config_path: Path to the config file
        config: Configuration dictionary to save
    """
    # Create a backup of the original config
    backup_path = f"{config_path}.bak"
    try:
        with open(config_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        logger.info(f"Created backup at {backup_path}")
    except Exception as e:
        logger.warning(f"Failed to create backup: {e}")
    
    # Save the updated config
    try:
        with open(config_path, 'w') as file:
            yaml.dump(config, file, default_flow_style=False)
        logger.info(f"Updated configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {e}")
        sys.exit(1)


def extract_oauth2_credentials(config: Dict) -> Dict:
    """Extract OAuth2 credentials from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary with client_id and client_secret
    """
    try:
        imap_config = config.get('imap', {})
        oauth2_config = imap_config.get('oauth2', {})
        
        client_id = oauth2_config.get('client_id')
        client_secret = oauth2_config.get('client_secret')
        
        if not client_id or not client_secret:
            logger.error("OAuth2 credentials not found in config")
            sys.exit(1)
        
        return {
            'client_id': client_id,
            'client_secret': client_secret
        }
    except Exception as e:
        logger.error(f"Failed to extract OAuth2 credentials: {e}")
        sys.exit(1)


def refresh_token(credentials: Dict) -> Dict:
    """Refresh OAuth2 token using Google's OAuth2 flow.
    
    Args:
        credentials: Dictionary with client_id and client_secret
        
    Returns:
        Dictionary with new tokens
    """
    # Create client config expected by google-auth-oauthlib
    client_config = {
        'installed': {
            'client_id': credentials['client_id'],
            'client_secret': credentials['client_secret'],
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': ['urn:ietf:wg:oauth:2.0:oob', 'http://localhost']
        }
    }
    
    try:
        # Create OAuth2 flow
        flow = InstalledAppFlow.from_client_config(
            client_config, 
            scopes=SCOPES,
            redirect_uri='http://localhost:8080'
        )
        
        # Enable offline access to get a refresh token
        flow.oauth2session.scope = SCOPES
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent'  # Force re-consent to get a new refresh token
        )
        
        # Open browser for user authentication
        logger.info("Opening browser for authentication...")
        webbrowser.open(authorization_url)
        
        # Local server will handle the redirect and get the authorization response
        flow.run_local_server(port=8080)
        
        # Get credentials including the refresh token
        credentials = flow.credentials
        
        return {
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'refresh_token': credentials.refresh_token,
            'access_token': credentials.token,
            'token_expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        sys.exit(1)


def update_config_with_new_tokens(config: Dict, new_tokens: Dict) -> Dict:
    """Update configuration with new OAuth2 tokens.
    
    Args:
        config: Original configuration dictionary
        new_tokens: Dictionary with new tokens
        
    Returns:
        Updated configuration dictionary
    """
    try:
        # Make sure the OAuth2 section exists
        if 'imap' not in config:
            config['imap'] = {}
        if 'oauth2' not in config['imap']:
            config['imap']['oauth2'] = {}
        
        # Update tokens
        config['imap']['oauth2']['client_id'] = new_tokens['client_id']
        config['imap']['oauth2']['client_secret'] = new_tokens['client_secret']
        config['imap']['oauth2']['refresh_token'] = new_tokens['refresh_token']
        
        # Only update access token if it's used in the config
        if 'access_token' in config['imap']['oauth2']:
            config['imap']['oauth2']['access_token'] = new_tokens['access_token']
        
        # Only update token expiry if it's used in the config
        if 'token_expiry' in config['imap']['oauth2']:
            config['imap']['oauth2']['token_expiry'] = new_tokens['token_expiry']
        
        return config
    except Exception as e:
        logger.error(f"Failed to update config with new tokens: {e}")
        sys.exit(1)


def main():
    """Main function to refresh OAuth2 token."""
    parser = argparse.ArgumentParser(description='Refresh Gmail OAuth2 tokens for integration testing')
    parser.add_argument('--config', type=str, default='config.yaml',
                        help='Path to config.yaml file (default: config.yaml)')
    args = parser.parse_args()
    
    config_path = args.config
    
    logger.info(f"Loading configuration from {config_path}")
    config = load_config(config_path)
    
    logger.info("Extracting OAuth2 credentials")
    credentials = extract_oauth2_credentials(config)
    
    logger.info("Starting OAuth2 authentication flow")
    new_tokens = refresh_token(credentials)
    
    logger.info("Updating configuration with new tokens")
    updated_config = update_config_with_new_tokens(config, new_tokens)
    
    # Output key information for verification
    logger.info("New OAuth2 tokens obtained:")
    logger.info(f"Refresh Token: {new_tokens['refresh_token'][:10]}...{new_tokens['refresh_token'][-10:]}")
    
    # Ask for confirmation before saving
    save_choice = input("Save updated tokens to config.yaml? (y/n): ").lower()
    if save_choice == 'y':
        save_config(config_path, updated_config)
        logger.info("Configuration updated successfully")
    else:
        print("New tokens:")
        print(json.dumps(new_tokens, indent=2))
        logger.info("Configuration not updated as per user choice")


if __name__ == "__main__":
    main()
