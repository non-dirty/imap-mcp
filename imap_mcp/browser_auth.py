"""Browser-based OAuth2 authentication for Gmail."""

import base64
import json
import logging
import os
import secrets
import sys
import time
import webbrowser
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs

import yaml
from flask import Flask, request, redirect, url_for

logger = logging.getLogger(__name__)

# Gmail OAuth2 endpoints
GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SCOPES = ["https://mail.google.com/"]

# Local server details
DEFAULT_CALLBACK_PORT = 8080
DEFAULT_CALLBACK_HOST = "localhost"
CALLBACK_PATH = "/oauth2callback"
SUCCESS_PATH = "/success"

# In-memory token storage
auth_tokens = {
    "access_token": None,
    "refresh_token": None,
    "token_expiry": None,
}


def create_oauth_app() -> Flask:
    """Create the Flask app for OAuth2 callback handling."""
    app = Flask(__name__)
    
    @app.route(CALLBACK_PATH)
    def oauth2callback():
        # Get authorization code from query parameters
        code = request.args.get("code")
        if not code:
            return "Error: No authorization code received", 400
        
        # Exchange code for tokens
        client_id = app.config.get("client_id")
        client_secret = app.config.get("client_secret")
        
        # Make token request
        try:
            import requests
            
            token_data = {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": app.config.get("redirect_uri"),
                "grant_type": "authorization_code",
            }
            
            response = requests.post(GMAIL_TOKEN_URL, data=token_data)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            
            tokens = response.json()
            
            # Store tokens in memory
            auth_tokens["access_token"] = tokens.get("access_token")
            auth_tokens["refresh_token"] = tokens.get("refresh_token")
            auth_tokens["token_expiry"] = int(time.time()) + tokens.get("expires_in", 3600)
            
            logger.info("Successfully obtained OAuth2 tokens")
            
            return redirect(url_for("success"))
        
        except Exception as e:
            logger.error(f"Error exchanging authorization code: {e}")
            return f"Error: Failed to exchange authorization code: {e}", 500
    
    @app.route(SUCCESS_PATH)
    def success():
        """Success page shown after successful authentication."""
        return """
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 30px;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .success {
                    background-color: #d4edda;
                    color: #155724;
                    padding: 15px;
                    border-radius: 4px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <h1>Authentication Successful!</h1>
            <div class="success">
                <p>You have successfully authenticated with Gmail.</p>
                <p>You may now close this browser window and return to the application.</p>
            </div>
        </body>
        </html>
        """
    
    return app


def run_local_server(
    client_id: str,
    client_secret: str,
    port: int = DEFAULT_CALLBACK_PORT,
    host: str = DEFAULT_CALLBACK_HOST,
) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """Run a local server to handle the OAuth2 callback.
    
    Args:
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        port: Port for the local server
        host: Host for the local server
        
    Returns:
        Tuple of (access_token, refresh_token, expiry) or (None, None, None) if failed
    """
    app = create_oauth_app()
    
    # Set up the redirect URI
    redirect_uri = f"http://{host}:{port}{CALLBACK_PATH}"
    
    # Store the client credentials in the app config
    app.config.update(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    
    # Set up the authorization URL
    state = secrets.token_urlsafe(16)  # Generate a random state parameter
    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "state": state,
        "prompt": "consent",  # Force consent screen to get refresh token
    }
    auth_url = f"{GMAIL_AUTH_URL}?{urlencode(auth_params)}"
    
    # Clear any previous tokens
    auth_tokens["access_token"] = None
    auth_tokens["refresh_token"] = None
    auth_tokens["token_expiry"] = None
    
    print(f"\nOpening browser for Gmail authentication...")
    webbrowser.open(auth_url)
    
    print(f"\nWaiting for authentication at http://{host}:{port}{CALLBACK_PATH}")
    
    # Run the Flask app for a short period
    # We need to run it in a separate thread to avoid blocking
    import threading
    
    # Flag to signal when the server should stop
    server_should_stop = threading.Event()
    
    def run_server():
        """Run the Flask server until stopped."""
        # Create a custom server that can be stopped
        from werkzeug.serving import make_server
        
        server = make_server(host, port, app, threaded=True)
        server.timeout = 0.5  # Check for stop flag every 0.5 seconds
        
        while not server_should_stop.is_set():
            server.handle_request()
    
    # Start the server thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for authentication to complete (or timeout)
    try:
        # Wait for up to 5 minutes
        max_wait_time = 5 * 60  # 5 minutes in seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            if auth_tokens["access_token"] is not None:
                # Authentication completed successfully
                break
            
            # Check every 1 second
            time.sleep(1)
        
        # Check if we timed out
        if auth_tokens["access_token"] is None:
            print("\nAuthentication timed out. Please try again.")
            return None, None, None
        
    finally:
        # Stop the server
        server_should_stop.set()
        server_thread.join(timeout=5)
    
    return (
        auth_tokens["access_token"],
        auth_tokens["refresh_token"],
        auth_tokens["token_expiry"],
    )


def load_client_credentials(credentials_file: str) -> Tuple[str, str]:
    """
    Load client credentials from the downloaded JSON file.
    
    Args:
        credentials_file: Path to the credentials JSON file
        
    Returns:
        Tuple of (client_id, client_secret)
        
    Raises:
        FileNotFoundError: If the credentials file doesn't exist
        ValueError: If the credentials file is invalid
    """
    if not credentials_file:
        raise ValueError("No credentials file specified")
        
    credentials_path = Path(credentials_file)
    if not credentials_path.exists():
        raise FileNotFoundError(f"Credentials file not found: {credentials_file}")
        
    try:
        with open(credentials_path) as f:
            credentials = json.load(f)
            
        if "installed" in credentials:
            client_config = credentials["installed"]
        elif "web" in credentials:
            client_config = credentials["web"]
        else:
            raise ValueError(f"Invalid credentials format in {credentials_file}")
            
        client_id = client_config.get("client_id")
        client_secret = client_config.get("client_secret")
        
        if not client_id or not client_secret:
            raise ValueError(f"Missing client_id or client_secret in {credentials_file}")
            
        return client_id, client_secret
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in credentials file: {credentials_file}")


def perform_oauth_flow(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    credentials_file: Optional[str] = None,
    port: int = DEFAULT_CALLBACK_PORT,
    config_path: Optional[str] = None,
    config_output: Optional[str] = None,
) -> Dict:
    """Run the OAuth flow to get Gmail access and refresh tokens.
    
    Args:
        client_id: OAuth2 client ID (optional, will prompt if not provided)
        client_secret: OAuth2 client secret (optional, will prompt if not provided)
        port: Port for the local server
        config_path: Path to existing config file to update (optional)
        config_output: Path to save the updated config file (optional)
        
    Returns:
        Updated configuration dictionary
    """
    # Try to load credentials from file first if provided
    if credentials_file and not (client_id and client_secret):
        try:
            logger.info(f"Attempting to load credentials from {credentials_file}")
            loaded_client_id, loaded_client_secret = load_client_credentials(credentials_file)
            client_id = client_id or loaded_client_id
            client_secret = client_secret or loaded_client_secret
            logger.info("Successfully loaded credentials from file")
        except Exception as e:
            logger.warning(f"Failed to load credentials from file: {e}")
    
    # Use environment variables if not provided
    client_id = client_id or os.environ.get("GMAIL_CLIENT_ID")
    client_secret = client_secret or os.environ.get("GMAIL_CLIENT_SECRET")
    
    # Prompt for client_id and client_secret if not provided
    if not client_id:
        client_id = input("Enter your Google OAuth2 client ID: ").strip()
    
    if not client_secret:
        client_secret = input("Enter your Google OAuth2 client secret: ").strip()
    
    if not client_id or not client_secret:
        print("Error: Client ID and secret are required.")
        sys.exit(1)
    
    # Run the OAuth flow
    print("Starting OAuth2 authentication flow...")
    access_token, refresh_token, expiry = run_local_server(
        client_id=client_id,
        client_secret=client_secret,
        port=port,
    )
    
    if not access_token or not refresh_token:
        print("Error: Failed to obtain OAuth2 tokens.")
        sys.exit(1)
    
    print("Authentication successful!")
    
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
    
    print("\nOAuth2 configuration:")
    print(json.dumps(oauth2_data, indent=2, default=str))
    
    print("\nTo use these credentials, add them to your config.yaml file under the imap.oauth2 key.")
    print("Alternatively, you can set the following environment variables:")
    print(f"  GMAIL_CLIENT_ID={client_id}")
    print(f"  GMAIL_CLIENT_SECRET={client_secret}")
    print(f"  GMAIL_REFRESH_TOKEN={refresh_token}")
    
    return config_data


def main():
    """Run the browser-based OAuth2 setup tool."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Browser-based OAuth2 authentication for Gmail")
    parser.add_argument(
        "--client-id", 
        help="Google OAuth2 client ID",
        default=os.environ.get("GMAIL_CLIENT_ID"),
    )
    parser.add_argument(
        "--client-secret", 
        help="Google OAuth2 client secret",
        default=os.environ.get("GMAIL_CLIENT_SECRET"),
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for the local callback server",
        default=DEFAULT_CALLBACK_PORT,
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
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    perform_oauth_flow(
        client_id=args.client_id,
        client_secret=args.client_secret,
        port=args.port,
        config_path=args.config,
        config_output=args.output,
    )


if __name__ == "__main__":
    main()
