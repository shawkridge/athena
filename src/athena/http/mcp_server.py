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
from athena.http.tools_registry import ToolsRegistry

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


# Tools registry endpoints for code execution pattern
async def discover_tools(request):
    """Discover all available tools organized by category."""
    tools_by_category = ToolsRegistry.discover_tools()
    return JSONResponse({
        "categories": {
            category: {
                "description": ToolsRegistry.get_category_description(category),
                "count": len(tools),
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                    }
                    for tool in tools
                ],
            }
            for category, tools in tools_by_category.items()
        },
        "total_tools": len(ToolsRegistry.list_all_tools()),
    })


async def list_tools(request):
    """List all available tools, optionally filtered by category."""
    category = request.query_params.get("category")

    if category:
        tools_by_category = ToolsRegistry.discover_tools()
        if category not in tools_by_category:
            return JSONResponse({"error": f"Category '{category}' not found"}, status_code=404)
        tools = tools_by_category[category]
        return JSONResponse({
            "category": category,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                }
                for tool in tools
            ],
            "count": len(tools),
        })
    else:
        all_tools = ToolsRegistry.list_all_tools()
        return JSONResponse({"tools": all_tools, "count": len(all_tools)})


async def get_tool_definition(request):
    """Get detailed definition of a specific tool."""
    tool_name = request.path_params.get("tool_name")
    tool = ToolsRegistry.get_tool(tool_name)

    if not tool:
        return JSONResponse({"error": f"Tool '{tool_name}' not found"}, status_code=404)

    return JSONResponse(tool.dict())


# Create a simple ASGI app that delegates to session_manager
class MCPApp:
    """ASGI app wrapper for StreamableHTTPSessionManager."""

    async def __call__(self, scope, receive, send):
        """Handle ASGI requests."""
        await session_manager.handle_request(scope, receive, send)


# Create Starlette app with tools registry routes and MCP ASGI app mounted
app = Starlette(
    routes=[
        Route("/health", health_check, methods=["GET"]),
        Route("/tools/discover", discover_tools, methods=["GET"]),
        Route("/tools/list", list_tools, methods=["GET"]),
        Route("/tools/{tool_name}", get_tool_definition, methods=["GET"]),
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
