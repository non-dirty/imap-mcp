"""Main server implementation for IMAP MCP."""

import argparse
import asyncio
import logging
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.types import Context

from imap_mcp.config import load_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("imap_mcp")


def create_server(config_path: Optional[str] = None, debug: bool = False) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        config_path: Path to configuration file
        debug: Enable debug mode

    Returns:
        Configured MCP server instance
    """
    # Set up logging level
    if debug:
        logger.setLevel(logging.DEBUG)
        
    # Create MCP server
    server = FastMCP(
        "IMAP",
        description="IMAP Model Context Protocol server for email processing",
        version="0.1.0",
    )
    
    # Load configuration
    config = load_config(config_path)
    
    # TODO: Add IMAP client setup
    
    # TODO: Register resources
    
    # TODO: Register tools
    
    # Example hello world tool for initial testing
    @server.tool()
    def hello(name: str) -> str:
        """Say hello to the user."""
        return f"Hello, {name}! This is the IMAP MCP server."
    
    return server


def main() -> None:
    """Run the IMAP MCP server."""
    parser = argparse.ArgumentParser(description="IMAP MCP Server")
    parser.add_argument(
        "--config", 
        help="Path to configuration file",
        default=os.environ.get("IMAP_MCP_CONFIG"),
    )
    parser.add_argument(
        "--dev", 
        action="store_true", 
        help="Enable development mode",
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging",
    )
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    server = create_server(args.config, args.debug)
    
    if args.dev:
        # Development mode runs the server with the inspector
        logger.info("Starting server in development mode...")
        server.run_dev()
    else:
        # Production mode
        logger.info("Starting server...")
        server.run()
    
    
if __name__ == "__main__":
    main()
