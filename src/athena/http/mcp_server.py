#!/usr/bin/env python3
"""Athena MCP HTTP Server - Exposes existing MCP server via HTTP transport."""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn

# Ensure athena package is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from athena.mcp.handlers import MemoryMCPServer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DATABASE_PATH = Path.home() / ".athena" / "memory.db"
os.environ.setdefault('ATHENA_DB_PATH', str(DATABASE_PATH))

# Global session manager
session_manager = None


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for Starlette."""
    global session_manager

    logger.info("Starting Athena MCP HTTP Server")
    logger.info(f"Database: {DATABASE_PATH}")
    logger.info(f"Database size: {DATABASE_PATH.stat().st_size / 1024 / 1024:.2f} MB")

    # Initialize the MemoryMCPServer (it has all 31 tools)
    memory_server = MemoryMCPServer(db_path=str(DATABASE_PATH))

    # Create session manager with the MCP server
    session_manager = StreamableHTTPSessionManager(
        app=memory_server.server,  # The underlying MCP SDK Server instance
        event_store=None,  # No persistence for now
        json_response=False,  # Use SSE for streaming
        stateless=False  # Track sessions
    )

    # Start the session manager
    async with session_manager.run():
        logger.info("✓ MCP HTTP server ready on http://0.0.0.0:3000")
        logger.info("✓ All 31 Athena tools available via MCP protocol")
        yield

    logger.info("Shutting down Athena MCP HTTP Server")


async def health_check(request):
    """Simple health check endpoint for Docker."""
    return JSONResponse({"status": "healthy", "service": "athena-mcp-http"})


# Create a simple ASGI app that delegates to session_manager
class MCPApp:
    """ASGI app wrapper for StreamableHTTPSessionManager."""

    async def __call__(self, scope, receive, send):
        """Handle ASGI requests."""
        await session_manager.handle_request(scope, receive, send)


# Create Starlette app with MCP ASGI app mounted
app = Starlette(
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Mount("/", app=MCPApp()),
    ],
    lifespan=lifespan,
)


def main():
    """Run the server."""
    logger.info("Athena MCP HTTP Server starting...")
    uvicorn.run(
        "athena.http.mcp_server:app",
        host="0.0.0.0",
        port=3000,
        log_level="info",
        reload=False
    )


if __name__ == "__main__":
    main()
