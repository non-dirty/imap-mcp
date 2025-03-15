# Setting up Gmail Authentication for IMAP MCP

There are two ways to authenticate with Gmail for IMAP MCP:

1. **App Password** (recommended, simpler): Uses a special password generated specifically for your app
2. **OAuth2 Authentication**: Uses Google's OAuth2 protocol (requires Google Cloud Platform setup)

## Option 1: Using App Passwords (Recommended)

This is the simplest approach and requires just a few steps:

1. Enable 2-Step Verification for your Google account:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Turn on 2-Step Verification if not already enabled

2. Generate an App Password:
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" as the app and choose a device name (e.g., "IMAP MCP")
   - Click "Generate" and copy the 16-character password

3. Set up IMAP MCP with your app password:

```bash
# Run the Gmail app password setup tool
uv run -m imap_mcp.app_password --username your.email@gmail.com
```

You'll be prompted to enter your app password, and the tool will configure IMAP MCP to use Gmail with your app password.

## App Password Command-Line Options

The Gmail app password tool supports several options:

```bash
uv run -m imap_mcp.app_password --help
```

Common options include:

- `--username`: Your Gmail address
- `--password`: Your app password (will prompt securely if not provided)
- `--config`: Path to existing config file to update
- `--output`: Path to save the updated config file (default: config.yaml)

## Manual Configuration with App Password

After setting up with an app password, your `config.yaml` file will look like this:

```yaml
imap:
  host: imap.gmail.com
  port: 993
  username: your-email@gmail.com
  password: your-16-character-app-password
  use_ssl: true
```

You can also set the following environment variables:
- `IMAP_PASSWORD`: Your app password

## Option 2: OAuth2 Authentication (Advanced)

If you need OAuth2 authentication instead of app passwords:

1. Create a Google Cloud Platform project
2. Enable the Gmail API
3. Create OAuth2 credentials (client ID and secret)
4. Configure IMAP MCP with those credentials

This method is more complex but available if needed. See our OAuth2 documentation for details.

## Using App-Specific Passwords (Alternative)

If you prefer not to use OAuth2, you can still use Gmail with an app-specific password:

1. Enable 2-Step Verification for your Google account
2. Generate an app-specific password in your Google account security settings
3. Use this password in your `config.yaml` file:

```yaml
imap:
  host: imap.gmail.com
  port: 993
  username: your-email@gmail.com
  password: your-app-specific-password
  use_ssl: true
```

Or set the `IMAP_PASSWORD` environment variable to your app-specific password.

## Troubleshooting

- **Invalid Credentials**: Make sure your client ID, client secret, and refresh token are correct
- **Authentication Failed**: Your refresh token may have expired. Run the auth_setup tool again to generate new tokens
- **Permission Denied**: Make sure you have granted all necessary permissions during the OAuth2 flow
