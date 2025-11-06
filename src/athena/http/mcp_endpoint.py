"""MCP Streamable HTTP transport endpoint for Athena."""

import logging
from typing import Any

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from ..manager import UnifiedMemoryManager

logger = logging.getLogger(__name__)


class AthenaMCPEndpoint:
    """MCP HTTP endpoint wrapper for Athena memory system."""

    def __init__(self, db_path: str):
        """Initialize MCP endpoint.

        Args:
            db_path: Path to Athena database
        """
        self.db_path = db_path
        self.manager = UnifiedMemoryManager(db_path=db_path)

        # Create low-level MCP server
        self.server = Server("athena-memory")

        # Setup tools
        self._setup_tools()

        # Create session manager (stateless mode for simplicity)
        self.session_manager = StreamableHTTPSessionManager(
            app=self.server,
            json_response=True,  # JSON responses (stateless)
            stateless=True,      # No session persistence
        )

    def _setup_tools(self):
        """Setup MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            """List all available Athena memory tools."""
            return [
                types.Tool(
                    name="recall",
                    description="Search and retrieve memories using advanced RAG",
                    inputSchema={
                        "type": "object",
                        "required": ["query"],
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "k": {
                                "type": "integer",
                                "default": 5,
                                "description": "Number of results"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="remember",
                    description="Store new memory or knowledge",
                    inputSchema={
                        "type": "object",
                        "required": ["content"],
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Memory content"
                            },
                            "memory_type": {
                                "type": "string",
                                "enum": ["fact", "pattern", "decision", "context"],
                                "description": "Type of memory"
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags for categorization"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="forget",
                    description="Delete a memory",
                    inputSchema={
                        "type": "object",
                        "required": ["memory_id"],
                        "properties": {
                            "memory_id": {
                                "type": "integer",
                                "description": "Memory ID to delete"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="memory_health",
                    description="Get memory system health report",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "boolean",
                                "default": False,
                                "description": "Include detailed metrics"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="consolidate",
                    description="Run consolidation to extract patterns from episodic events",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "strategy": {
                                "type": "string",
                                "enum": ["balanced", "speed", "quality", "minimal"],
                                "default": "balanced",
                                "description": "Consolidation strategy"
                            }
                        }
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.ContentBlock]:
            """Execute Athena memory tool."""
            try:
                result = None

                if name == "recall":
                    query = arguments.get("query")
                    k = arguments.get("k", 5)
                    result = await self._recall(query, k)

                elif name == "remember":
                    content = arguments.get("content")
                    memory_type = arguments.get("memory_type", "fact")
                    tags = arguments.get("tags", [])
                    result = await self._remember(content, memory_type, tags)

                elif name == "forget":
                    memory_id = arguments.get("memory_id")
                    result = await self._forget(memory_id)

                elif name == "memory_health":
                    detail = arguments.get("detail", False)
                    result = await self._memory_health(detail)

                elif name == "consolidate":
                    strategy = arguments.get("strategy", "balanced")
                    result = await self._consolidate(strategy)

                else:
                    result = {"error": f"Unknown tool: {name}"}

                # Convert result to text
                import json
                result_text = json.dumps(result, indent=2, default=str)

                return [types.TextContent(type="text", text=result_text)]

            except Exception as e:
                logger.error(f"Tool execution failed for '{name}': {e}", exc_info=True)
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async def _recall(self, query: str, k: int = 5) -> dict:
        """Recall memories matching query."""
        try:
            # Use manager's recall functionality
            results = self.manager.recall(query, k=k)
            return {
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _remember(self, content: str, memory_type: str, tags: list) -> dict:
        """Store new memory."""
        try:
            memory_id = self.manager.remember(content, memory_type=memory_type, tags=tags)
            return {
                "success": True,
                "memory_id": memory_id,
                "memory_type": memory_type,
                "content_length": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _forget(self, memory_id: int) -> dict:
        """Delete memory."""
        try:
            self.manager.forget(memory_id)
            return {
                "success": True,
                "memory_id": memory_id,
                "message": f"Memory {memory_id} deleted"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _memory_health(self, detail: bool = False) -> dict:
        """Get memory system health."""
        try:
            health = self.manager.get_memory_health(detail=detail)
            return {
                "success": True,
                "health": health
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _consolidate(self, strategy: str = "balanced") -> dict:
        """Run consolidation."""
        try:
            result = self.manager.consolidate(strategy=strategy)
            return {
                "success": True,
                "strategy": strategy,
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def handle_request(self, scope, receive, send):
        """Handle MCP HTTP request."""
        await self.session_manager.handle_request(scope, receive, send)
