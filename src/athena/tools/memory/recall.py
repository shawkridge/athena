"""Recall/query memory tool - retrieve memories from the system."""
import time
from typing import Any, Optional, Dict, List
from athena.tools import BaseTool, ToolMetadata


class RecallMemoryTool(BaseTool):
    """Tool for recalling/querying memories from the system.

    Searches across all memory layers (episodic, semantic, procedural, etc.)
    to retrieve relevant information. Supports multiple query types for
    targeted searches.

    Example:
        >>> tool = RecallMemoryTool()
        >>> result = await tool.execute(
        ...     query="What did we discuss about authentication?",
        ...     query_type="factual",
        ...     limit=5
        ... )
    """

    def __init__(self):
        """Initialize recall tool."""
        self._manager = None

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return ToolMetadata(
            name="recall",
            category="memory",
            description="Recall/search memories from the system across all layers",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query or topic to find related memories",
                    "required": True
                },
                "query_type": {
                    "type": "string",
                    "enum": ["temporal", "factual", "relational", "procedural", "prospective", "meta", "planning", "auto"],
                    "description": "Type of query to optimize search strategy",
                    "required": False,
                    "default": "auto"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "required": False,
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Include full metadata in results",
                    "required": False,
                    "default": False
                },
                "min_relevance": {
                    "type": "number",
                    "description": "Minimum relevance score (0-1) for results",
                    "required": False,
                    "default": 0.0,
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            returns={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query that was executed"
                    },
                    "query_type": {
                        "type": "string",
                        "description": "The query type used"
                    },
                    "results": {
                        "type": "array",
                        "description": "List of matching memories",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "Unique memory identifier"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Memory content"
                                },
                                "relevance": {
                                    "type": "number",
                                    "description": "Relevance score (0-1)"
                                },
                                "layer": {
                                    "type": "string",
                                    "description": "Memory layer (episodic, semantic, etc.)"
                                },
                                "timestamp": {
                                    "type": "string",
                                    "description": "When the memory was created"
                                },
                                "metadata": {
                                    "type": "object",
                                    "description": "Additional memory metadata (if requested)"
                                }
                            }
                        }
                    },
                    "total_results": {
                        "type": "integer",
                        "description": "Total number of matching memories"
                    },
                    "returned_results": {
                        "type": "integer",
                        "description": "Number of results returned"
                    },
                    "search_time_ms": {
                        "type": "number",
                        "description": "Time taken to execute search"
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
        if "query" not in kwargs or not kwargs["query"].strip():
            raise ValueError("query parameter is required and cannot be empty")

        if len(kwargs["query"]) > 10000:
            raise ValueError("query must be less than 10,000 characters")

        if "limit" in kwargs:
            limit = kwargs["limit"]
            if not isinstance(limit, int) or limit < 1 or limit > 100:
                raise ValueError("limit must be an integer between 1 and 100")

        if "query_type" in kwargs:
            valid_types = {
                "temporal", "factual", "relational",
                "procedural", "prospective", "meta", "planning", "auto"
            }
            if kwargs["query_type"] not in valid_types:
                raise ValueError(
                    f"query_type must be one of: {', '.join(sorted(valid_types))}"
                )

        if "min_relevance" in kwargs:
            score = kwargs["min_relevance"]
            if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
                raise ValueError("min_relevance must be a number between 0.0 and 1.0")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute memory recall/search.

        Args:
            **kwargs: Tool parameters (query, query_type, limit, include_metadata, min_relevance)

        Returns:
            Dictionary with search results and metadata

        Raises:
            ValueError: If input validation fails
        """
        start_time = time.time()

        try:
            self.validate_input(**kwargs)

            query = kwargs["query"]
            query_type = kwargs.get("query_type", "auto")
            limit = kwargs.get("limit", 10)
            include_metadata = kwargs.get("include_metadata", False)
            min_relevance = kwargs.get("min_relevance", 0.0)

            # Implement actual memory recall from database
            results = []
            total_results = 0

            try:
                # Query database for matching memories
                from athena.core.database import get_database
                db = get_database()

                # Build query based on query_type
                if query_type == "auto":
                    # Search across all memory types
                    search_where = "content LIKE ? OR tags LIKE ?"
                    search_params = (f"%{query}%", f"%{query}%")
                else:
                    # Search specific memory type
                    search_where = "(content LIKE ? OR tags LIKE ?) AND memory_type = ?"
                    search_params = (f"%{query}%", f"%{query}%", query_type)

                # Execute search
                try:
                    cursor = db.conn.cursor()
                    cursor.execute(
                        f"""SELECT id, content, memory_type, importance, created_at, tags
                           FROM memories
                           WHERE {search_where}
                           ORDER BY importance DESC
                           LIMIT ?""",
                        (*search_params, limit) if query_type == "auto" else (*search_params, limit)
                    )
                    rows = cursor.fetchall()

                    for row in rows:
                        # Calculate relevance (simplified: importance score)
                        relevance = row[3] if row[3] else 0.5  # importance

                        if relevance >= min_relevance:
                            result = {
                                "memory_id": row[0],
                                "content": row[1][:200],  # Truncate content
                                "memory_type": row[2],
                                "relevance": relevance,
                                "timestamp": row[4]
                            }

                            if include_metadata:
                                result["full_content"] = row[1]
                                result["tags"] = row[5].split(',') if row[5] else []

                            results.append(result)

                    total_results = len(rows)

                except Exception as db_err:
                    import logging
                    logging.warning(f"Database search failed: {db_err}")

            except Exception as e:
                import logging
                logging.debug(f"Memory recall unavailable: {e}")

            elapsed = (time.time() - start_time) * 1000  # Convert to ms

            return {
                "query": query,
                "query_type": query_type,
                "results": results[:limit],  # Return only requested limit
                "total_results": total_results,
                "returned_results": len(results),
                "search_time_ms": elapsed,
                "min_relevance_filter": min_relevance,
                "status": "success"
            }

        except ValueError as e:
            return {
                "error": str(e),
                "status": "error",
                "search_time_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "status": "error",
                "search_time_ms": (time.time() - start_time) * 1000
            }
