# IMAP MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to check email, process messages, and learn user preferences through interaction.

## Overview

This project implements an MCP server that interfaces with IMAP email servers to provide the following capabilities:

- Email browsing and searching
- Email organization (moving, tagging, marking)
- Interactive email processing and learning user preferences
- Automated email summarization and categorization
- Support for multiple IMAP providers

The IMAP MCP server is designed to work with Claude or any other MCP-compatible assistant, allowing them to act as intelligent email assistants that learn your preferences over time.

## Features

- **Email Authentication**: Secure access to IMAP servers with various authentication methods
- **Email Browsing**: List folders and messages with filtering options ✓
- **Email Content**: Read message contents including text, HTML, and attachments ✓
- **Email Actions**: Move, delete, mark as read/unread, flag messages ✓
- **Search**: Basic search capabilities across folders ✓
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
- An IMAP-enabled email account
- [uv](https://docs.astral.sh/uv/) - Python package installer
- Claude Desktop (or another MCP-compatible client)

### Installation

See [INSTALLATION.md](INSTALLATION.md) for detailed installation instructions.

Quick start:

1. Install the uv tool from [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

2. Clone the repository:
   ```bash
   git clone https://github.com/non-dirty/imap-mcp.git
   cd imap-mcp
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Configure your email account:
   ```bash
   cp examples/config.yaml.example config.yaml
   # Edit config.yaml with your email settings
   ```

### Usage

#### Starting the Server

```bash
# Basic usage
python -m imap_mcp.server

# With specific config file
python -m imap_mcp.server --config /path/to/config.yaml

# For development
python -m imap_mcp.server --dev
```

#### Integrating with Claude Desktop

Add the following to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "imap": {
      "command": "python",
      "args": ["-m", "imap_mcp.server", "--config", "/path/to/config.yaml"],
      "env": {
        "IMAP_PASSWORD": "your_secure_password"
      }
    }
  }
}
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
