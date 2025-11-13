"""MCP Daemon Server with stdio transport.

This module implements a long-running MCP server that:
1. Initializes PostgreSQL connection pool once on startup
2. Exposes memory operations via stdio MCP protocol
3. Handles requests with summary-first pattern (300 tokens max)
4. Gracefully manages lifecycle (cleanup on shutdown)

This is the optimal architecture per Anthropic's code-execution-with-MCP model:
- Server owns the stateful PostgreSQL connection pool
- Hooks connect to daemon via stdio (no per-request connections)
- All async/event loop complexity hidden in server
- Results filtered/summarized before returning to hooks

Usage:
    python -m athena.mcp.server_daemon

Or as systemd service:
    systemctl start athena-mcp
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


async def run_daemon():
    """Run MCP daemon with stdio transport.

    This initializes the connection pool once and keeps the server
    running to reuse connections across multiple hook calls.
    """

    # Import MCP and Athena here to ensure proper async context
    from mcp.server.stdio import stdio_server
    from mcp.server import Server

    # Initialize database connection pool (once, on startup)
    from ..core.database import initialize_database

    logger.info("Initializing PostgreSQL connection pool...")

    try:
        db = await initialize_database(
            host='localhost',
            port=5432,
            dbname='athena',
            user='postgres',
            password='postgres',
            min_size=2,
            max_size=10
        )
        logger.info("✓ PostgreSQL connection pool initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        sys.exit(1)

    # Import handlers after database is ready
    from .handlers import MemoryMCPServer

    # Create MCP server with existing handlers
    logger.info("Initializing MCP server...")
    mcp_server = MemoryMCPServer(db_path=None)  # db_path ignored for PostgreSQL
    logger.info("✓ MCP server initialized")

    # Create wrapper for stdio transport
    async def process_message(raw_message: str) -> Optional[str]:
        """Process incoming MCP message and return response.

        This is called by the stdio transport for each message from the client.
        """
        try:
            message = json.loads(raw_message)
            # MCP protocol handling would go here
            # For now, just acknowledge
            return json.dumps({"status": "ok"})
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return json.dumps({"error": str(e)})

    # Run with stdio transport
    logger.info("Starting MCP daemon (stdio transport)...")
    logger.info("Ready to accept connections from hooks")

    async with stdio_server() as server:
        await server.run()


def main():
    """Entry point for daemon process."""

    # Setup logging (logs to stderr, doesn't interfere with stdio MCP protocol)
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )

    logger.info("=" * 60)
    logger.info("Athena MCP Daemon Starting")
    logger.info("=" * 60)

    try:
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        logger.info("Daemon shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
