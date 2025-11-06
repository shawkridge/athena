#!/usr/bin/env python3
"""Standalone MCP HTTP server for Athena."""

import asyncio
import os
import sys
from pathlib import Path

# Add source to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp.server.fastmcp import FastMCP

# Setup database path
os.environ.setdefault('ATHENA_DB_PATH', str(Path.home() / ".athena" / "memory.db"))

# Create FastMCP server
mcp = FastMCP("Athena Memory System")


# Import handlers from existing MCP server
from athena.mcp.handlers import MemoryMCPServer
from athena.manager import UnifiedMemoryManager

# Initialize the backend
db_path = os.environ.get('ATHENA_DB_PATH')
manager = UnifiedMemoryManager(db_path=db_path)


@mcp.tool()
async def athena_memory(operation: str, **params) -> dict:
    """Execute Athena memory operations.

    Args:
        operation: Operation name (recall, remember, forget, etc.)
        **params: Operation-specific parameters

    Returns:
        Operation result
    """
    try:
        # Route to the manager
        if operation == "recall":
            query = params.get("query", "")
            k = params.get("k", 5)
            results = manager.recall(query, k=k)
            return {"results": results}
        elif operation == "remember":
            content = params.get("content", "")
            memory_type = params.get("memory_type", "fact")
            tags = params.get("tags", [])
            manager.remember(content, memory_type=memory_type, tags=tags)
            return {"success": True}
        else:
            return {"error": f"Unknown operation: {operation}"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # Run as HTTP server
    import uvicorn

    app = mcp.get_asgi_app()
    uvicorn.run(app, host="0.0.0.0", port=3001)
