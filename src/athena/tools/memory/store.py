"""Store/remember memory tool - save new memories to the system."""
import time
from typing import Any, Dict, Optional
from athena.tools import BaseTool, ToolMetadata


class StoreMemoryTool(BaseTool):
    """Tool for storing/remembering new memories in the system.

    Adds new memories to appropriate layers (episodic, semantic, procedural)
    based on content and metadata. Supports structured memory creation with
    optional tags, categories, and relationships.

    Example:
        >>> tool = StoreMemoryTool()
        >>> result = await tool.execute(
        ...     content="User prefers authentication via OAuth",
        ...     memory_type="semantic",
        ...     tags=["authentication", "oauth"],
        ...     importance=0.8
        ... )
    """

    def __init__(self):
        """Initialize store tool."""
        self._manager = None

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return ToolMetadata(
            name="store",
            category="memory",
            description="Store/remember new memories in the system",
            parameters={
                "content": {
                    "type": "string",
                    "description": "Memory content to store",
                    "required": True
                },
                "memory_type": {
                    "type": "string",
                    "enum": ["episodic", "semantic", "procedural", "prospective", "auto"],
                    "description": "Type of memory layer to store in",
                    "required": False,
                    "default": "auto"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorizing the memory",
                    "required": False,
                    "default": []
                },
                "importance": {
                    "type": "number",
                    "description": "Importance score (0-1)",
                    "required": False,
                    "default": 0.5,
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "context": {
                    "type": "object",
                    "description": "Additional context metadata",
                    "required": False,
                    "default": {}
                },
                "relationships": {
                    "type": "array",
                    "description": "IDs of related memories",
                    "required": False,
                    "default": []
                }
            },
            returns={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Unique ID of stored memory"
                    },
                    "content": {
                        "type": "string",
                        "description": "The stored content"
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Memory layer used"
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "When memory was created"
                    },
                    "store_time_ms": {
                        "type": "number",
                        "description": "Time taken to store memory"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["success", "error"],
                        "description": "Operation status"
                    }
                }
            }
        )

    def validate_input(self, **kwargs) -> None:
        """Validate input parameters.

        Args:
            **kwargs: Tool parameters

        Raises:
            ValueError: If required parameters missing or invalid
        """
        if "content" not in kwargs or not kwargs["content"].strip():
            raise ValueError("content parameter is required and cannot be empty")

        if len(kwargs["content"]) > 50000:
            raise ValueError("content must be less than 50,000 characters")

        if "memory_type" in kwargs:
            valid_types = {"episodic", "semantic", "procedural", "prospective", "auto"}
            if kwargs["memory_type"] not in valid_types:
                raise ValueError(f"memory_type must be one of: {', '.join(sorted(valid_types))}")

        if "importance" in kwargs:
            importance = kwargs["importance"]
            if not isinstance(importance, (int, float)) or not (0.0 <= importance <= 1.0):
                raise ValueError("importance must be a number between 0.0 and 1.0")

        if "tags" in kwargs:
            tags = kwargs["tags"]
            if not isinstance(tags, list):
                raise ValueError("tags must be a list of strings")
            if any(not isinstance(t, str) for t in tags):
                raise ValueError("all tags must be strings")

        if "relationships" in kwargs:
            rels = kwargs["relationships"]
            if not isinstance(rels, list):
                raise ValueError("relationships must be a list of IDs")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute memory store operation.

        Args:
            **kwargs: Tool parameters (content, memory_type, tags, importance, context, relationships)

        Returns:
            Dictionary with stored memory info

        Raises:
            ValueError: If input validation fails
        """
        start_time = time.time()

        try:
            self.validate_input(**kwargs)

            content = kwargs["content"]
            memory_type = kwargs.get("memory_type", "auto")
            tags = kwargs.get("tags", [])
            importance = kwargs.get("importance", 0.5)
            context = kwargs.get("context", {})
            relationships = kwargs.get("relationships", [])

            # TODO: Implement actual memory storage
            # This will delegate to UnifiedMemoryManager.store()
            # For now, return structured stub response

            elapsed = (time.time() - start_time) * 1000  # Convert to ms

            return {
                "memory_id": f"mem_{int(time.time() * 1000)}",
                "content": content[:100],  # Show first 100 chars
                "memory_type": memory_type,
                "timestamp": time.isoformat(),
                "store_time_ms": elapsed,
                "status": "success",
                "tags_count": len(tags),
                "importance": importance
            }

        except ValueError as e:
            return {
                "error": str(e),
                "status": "error",
                "store_time_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "status": "error",
                "store_time_ms": (time.time() - start_time) * 1000
            }
