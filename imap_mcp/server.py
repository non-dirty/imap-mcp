"""Main server implementation for IMAP MCP."""

import argparse
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Optional

from mcp.server.fastmcp import FastMCP, Context

from imap_mcp.config import ServerConfig, load_config
from imap_mcp.imap_client import ImapClient
from imap_mcp.resources import register_resources
from imap_mcp.tools import register_tools
from imap_mcp.mcp_protocol import extend_server

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("imap_mcp")


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict]:
    """Server lifespan manager to handle IMAP client lifecycle.
    
    Args:
        server: MCP server instance
        
    Yields:
        Context dictionary containing IMAP client
    """
    # Access the config that was set in create_server
    # The config is stored in the server's state
    config = getattr(server, "_config", None)
    if not config:
        # This is a fallback in case we can't find the config
        config = load_config()
    
    if not isinstance(config, ServerConfig):
        raise TypeError("Invalid server configuration")
    
    imap_client = ImapClient(config.imap, config.allowed_folders)
    
    try:
        # Connect to IMAP server
        logger.info("Connecting to IMAP server...")
        imap_client.connect()
        
        # Yield the context with the IMAP client
        yield {"imap_client": imap_client}
    finally:
        # Disconnect from IMAP server
        logger.info("Disconnecting from IMAP server...")
        imap_client.disconnect()


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
        
    # Load configuration
    config = load_config(config_path)
    
    # Create MCP server with all the necessary capabilities
    server = FastMCP(
        "IMAP",
        description="IMAP Model Context Protocol server for email processing",
        version="0.1.0",
        lifespan=server_lifespan,
    )
    
    # Store config for access in the lifespan
    server._config = config
    
    # Create IMAP client for setup (will be recreated in lifespan)
    imap_client = ImapClient(config.imap, config.allowed_folders)
    
    # Register resources and tools
    register_resources(server, imap_client)
    register_tools(server, imap_client)
    
    # Add server status tool
    @server.tool()
    def server_status() -> str:
        """Get server status and configuration info."""
        status = {
            "server": "IMAP MCP",
            "version": "0.1.0",
            "imap_host": config.imap.host,
            "imap_port": config.imap.port,
            "imap_user": config.imap.username,
            "imap_ssl": config.imap.use_ssl,
        }
        
        if config.allowed_folders:
            status["allowed_folders"] = list(config.allowed_folders)
        else:
            status["allowed_folders"] = "All folders allowed"
        
        return "\n".join(f"{k}: {v}" for k, v in status.items())
    
    # Apply MCP protocol extension for Claude Desktop compatibility
    server = extend_server(server)
    
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
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information and exit",
    )
    args = parser.parse_args()
    
    if args.version:
        print("IMAP MCP Server version 0.1.0")
        return
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    server = create_server(args.config, args.debug)
    
    # Start the server
    logger.info("Starting server{}...".format(" in development mode" if args.dev else ""))
    server.run()
    
    
if __name__ == "__main__":
    main()
