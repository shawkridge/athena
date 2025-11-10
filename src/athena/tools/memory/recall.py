"""Recall/query memory tool - retrieve memories from the system."""
from typing import Any, Optional, Dict, List
from athena.tools import BaseTool, ToolMetadata


class RecallMemoryTool(BaseTool):
    """Tool for recalling/querying memories from the system.

    Searches across all memory layers (episodic, semantic, procedural, etc.)
    to retrieve relevant information.
    """

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return ToolMetadata(
            name="recall",
            category="memory",
            description="Recall/search memories from the system",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query or topic",
                    "required": True
                },
                "query_type": {
                    "type": "string",
                    "description": "Type of query (temporal, factual, relational, procedural, prospective, meta, planning)",
                    "required": False,
                    "default": "auto"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "required": False,
                    "default": 10
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Include metadata in results",
                    "required": False,
                    "default": False
                }
            },
            returns={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "query_type": {"type": "string"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "content": {"type": "string"},
                                "relevance": {"type": "number"},
                                "layer": {"type": "string"},
                                "metadata": {"type": "object"}
                            }
                        }
                    },
                    "total_results": {"type": "integer"},
                    "search_time_ms": {"type": "number"}
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
        if "query" not in kwargs or not kwargs["query"].strip():
            raise ValueError("query parameter is required and cannot be empty")

        if "limit" in kwargs:
            limit = kwargs["limit"]
            if not isinstance(limit, int) or limit < 1:
                raise ValueError("limit must be a positive integer")

        if "query_type" in kwargs:
            valid_types = {"temporal", "factual", "relational", "procedural", "prospective", "meta", "planning", "auto"}
            if kwargs["query_type"] not in valid_types:
                raise ValueError(f"query_type must be one of: {valid_types}")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute memory recall/search.

        Args:
            **kwargs: Tool parameters (query, query_type, limit, include_metadata)

        Returns:
            Dictionary with search results and metadata
        """
        self.validate_input(**kwargs)

        query = kwargs["query"]
        query_type = kwargs.get("query_type", "auto")
        limit = kwargs.get("limit", 10)
        include_metadata = kwargs.get("include_metadata", False)

        # For now, return a structured response that matches the interface
        # In actual implementation, this will call the memory manager
        return {
            "query": query,
            "query_type": query_type,
            "results": [],  # Will be populated by actual implementation
            "total_results": 0,
            "search_time_ms": 0.0
        }
