# IMAP MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to check email, process messages, and learn user preferences through interaction.

## Overview

This project implements an MCP server that interfaces with IMAP email servers to provide the following capabilities:

- Email browsing and searching
- Email organization (moving, tagging, marking)
- Email composition and replies
- Interactive email processing and learning user preferences
- Automated email summarization and categorization
- Support for multiple IMAP providers

The IMAP MCP server is designed to work with Claude or any other MCP-compatible assistant, allowing them to act as intelligent email assistants that learn your preferences over time.

## Features

- **Email Authentication**: Secure access to IMAP servers with various authentication methods
- **Email Browsing**: List folders and messages with filtering options 
- **Email Content**: Read message contents including text, HTML, and attachments 
- **Email Actions**: Move, delete, mark as read/unread, flag messages 
- **Email Composition**: Draft and save replies to messages with proper formatting
  - Support for plain text and HTML replies
  - Reply-all functionality with CC support
  - Proper threading with In-Reply-To and References headers
  - Save drafts to appropriate folders
- **Search**: Basic search capabilities across folders 
- **Interaction Patterns**: Structured patterns for processing emails and learning preferences (planned)
- **Learning Layer**: Record and analyze user decisions to predict future actions (planned)

## Current Project Structure

The project is currently organized as follows:

```
.
├── examples/              # Example configurations
│   └── config.yaml.example
├── imap_mcp/              # Source code
│   ├── __init__.py
│   ├── config.py          # Configuration handling
│   ├── imap_client.py     # IMAP client implementation
│   ├── models.py          # Data models
│   ├── resources.py       # MCP resources implementation
│   ├── server.py          # Main server implementation
│   └── tools.py           # MCP tools implementation
├── tests/                 # Test suite
│   ├── __init__.py
│   └── test_models.py
├── INSTALLATION.md        # Detailed installation guide
├── pyproject.toml         # Project configuration
└── README.md              # This file
```

## Getting Started

### Prerequisites

- Python 3.8 or higher
- An IMAP-enabled email account (Gmail recommended)
- [uv](https://docs.astral.sh/uv/) for package management and running Python scripts

### Installation

1. Install uv if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone and install the package:
   ```bash
   git clone https://github.com/non-dirty/imap-mcp.git
   cd imap-mcp
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```

### Gmail Configuration

1. Create a config file:
   ```bash
   cp config.sample.yaml config.yaml
   ```

2. Set up Gmail OAuth2 credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Gmail API
   - Create OAuth2 credentials (Desktop Application type)
   - Download the client configuration

3. Update `config.yaml` with your Gmail settings:
   ```yaml
   imap:
     host: imap.gmail.com
     port: 993
     username: your-email@gmail.com
     use_ssl: true
     oauth2:
       client_id: YOUR_CLIENT_ID
       client_secret: YOUR_CLIENT_SECRET
       refresh_token: YOUR_REFRESH_TOKEN
   ```

### Usage

#### Checking Email

To list emails in your inbox:
```bash
uv run list_inbox.py --config config.yaml --folder INBOX --limit 10
```

Available options:
- `--folder`: Specify which folder to check (default: INBOX)
- `--limit`: Maximum number of emails to display (default: 10)
- `--verbose`: Enable detailed logging output

#### Starting the MCP Server

To start the IMAP MCP server:
```bash
uv run imap_mcp.server --config config.yaml
```

For development mode with debugging:
```bash
uv run imap_mcp.server --dev
```

#### Managing OAuth2 Tokens

To refresh your OAuth2 token:
```bash
uv run imap_mcp.auth_setup refresh-token --config config.yaml
```

To generate a new OAuth2 token:
```bash
uv run imap_mcp.auth_setup generate-token --config config.yaml
```

## Development

### Setting Up Development Environment

```bash
# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

## Security Considerations

This MCP server requires access to your email account, which contains sensitive personal information. Please be aware of the following security considerations:

- Store email credentials securely using environment variables or secure credential storage
- Consider using app-specific passwords instead of your main account password
- Limit folder access to only what's necessary for your use case
- Review the permissions granted to the server in your email provider's settings

## Project Roadmap

- [x] Project initialization and repository setup
- [x] Basic IMAP integration
- [x] Email resource implementation
- [x] Email tool implementation
- [x] Email reply and draft functionality
- [ ] User preference learning implementation
- [ ] Advanced search capabilities
- [ ] Multi-account support
- [ ] Integration with major email providers

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Model Context Protocol](https://modelcontextprotocol.io/) for providing the framework
- [Anthropic](https://www.anthropic.com/) for developing Claude
- Various Python IMAP libraries that make this project possible
