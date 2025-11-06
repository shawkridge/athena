"""Mount MCP protocol endpoint to HTTP server."""

import logging
from pathlib import Path
from starlette.routing import Mount
from mcp.server.fastmcp import FastMCP

from ..mcp.handlers import MemoryMCPServer

logger = logging.getLogger(__name__)

# Database path
DATABASE_PATH = Path.home() / ".athena" / "memory.db"


def create_mcp_app() -> FastMCP:
    """Create FastMCP server with all Athena tools.

    Returns:
        FastMCP server instance that can be mounted
    """
    mcp = FastMCP("Athena Memory System")

    # Initialize the actual MCP server with handlers
    server = MemoryMCPServer(db_path=str(DATABASE_PATH))

    # Get all tool definitions from the server
    # The MemoryMCPServer already has all 31 tools defined via @server.tool() decorators
    # We need to expose them through FastMCP

    # Since MemoryMCPServer uses the standard MCP SDK, we can't directly copy decorators
    # Instead, we'll create wrapper tools that call the MCP server's operations

    @mcp.tool()
    async def memory_tools(operation: str, **kwargs) -> dict:
        """Execute memory operations.

        Args:
            operation: Operation name (recall, remember, forget, etc.)
            **kwargs: Operation-specific parameters

        Returns:
            Operation result
        """
        try:
            # Call the MCP server's operation handler
            result = await server.handle_operation(operation, kwargs)
            return result
        except Exception as e:
            logger.error(f"Memory operation failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def episodic_tools(operation: str, **kwargs) -> dict:
        """Execute episodic memory operations."""
        return await memory_tools(operation="episodic_" + operation, **kwargs)

    @mcp.tool()
    async def graph_tools(operation: str, **kwargs) -> dict:
        """Execute knowledge graph operations."""
        return await memory_tools(operation="graph_" + operation, **kwargs)

    @mcp.tool()
    async def planning_tools(operation: str, **kwargs) -> dict:
        """Execute planning operations."""
        return await memory_tools(operation="planning_" + operation, **kwargs)

    @mcp.tool()
    async def task_management_tools(operation: str, **kwargs) -> dict:
        """Execute task and goal management operations."""
        return await memory_tools(operation="task_" + operation, **kwargs)

    @mcp.tool()
    async def monitoring_tools(operation: str, **kwargs) -> dict:
        """Execute monitoring and health operations."""
        return await memory_tools(operation="monitoring_" + operation, **kwargs)

    return mcp


def get_mcp_mount():
    """Get MCP HTTP app for mounting.

    Returns:
        FastAPI app configured with MCP Streamable HTTP transport
    """
    mcp = create_mcp_app()
    return mcp.streamable_http_app()
