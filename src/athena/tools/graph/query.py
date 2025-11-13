"""Query knowledge graph tool."""
import time
from typing import Any, Dict
from athena.tools import BaseTool, ToolMetadata


class QueryGraphTool(BaseTool):
    """Tool for querying the knowledge graph.

    Searches for entities, relationships, and patterns in the knowledge
    graph using various query types and filters.

    Example:
        >>> tool = QueryGraphTool()
        >>> result = await tool.execute(
        ...     query="authentication systems",
        ...     query_type="entity_search",
        ...     max_results=10
        ... )
    """

    def __init__(self):
        """Initialize graph query tool."""
        self._manager = None

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return ToolMetadata(
            name="graph_query",
            category="graph",
            description="Query the knowledge graph",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Query string or entity name",
                    "required": True
                },
                "query_type": {
                    "type": "string",
                    "enum": ["entity_search", "relationship", "community", "path", "similarity"],
                    "description": "Type of graph query",
                    "required": False,
                    "default": "entity_search"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "required": False,
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Include full entity metadata",
                    "required": False,
                    "default": False
                }
            },
            returns={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "query_type": {"type": "string"},
                    "entities_found": {
                        "type": "integer",
                        "description": "Number of entities found"
                    },
                    "results": {
                        "type": "array",
                        "description": "Found entities and relationships"
                    },
                    "query_time_ms": {
                        "type": "number",
                        "description": "Time taken to execute query"
                    }
                }
            }
        )

    def validate_input(self, **kwargs) -> None:
        """Validate input parameters."""
        if "query" not in kwargs or not kwargs["query"].strip():
            raise ValueError("query parameter is required and cannot be empty")

        if "query_type" in kwargs:
            valid = {"entity_search", "relationship", "community", "path", "similarity"}
            if kwargs["query_type"] not in valid:
                raise ValueError(f"query_type must be one of: {', '.join(sorted(valid))}")

        if "max_results" in kwargs:
            max_r = kwargs["max_results"]
            if not isinstance(max_r, int) or max_r < 1 or max_r > 100:
                raise ValueError("max_results must be between 1 and 100")

        if "include_metadata" in kwargs and not isinstance(kwargs["include_metadata"], bool):
            raise ValueError("include_metadata must be boolean")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute graph query."""
        start_time = time.time()

        try:
            self.validate_input(**kwargs)

            query = kwargs["query"]
            query_type = kwargs.get("query_type", "entity_search")
            max_results = kwargs.get("max_results", 10)
            include_metadata = kwargs.get("include_metadata", False)

            # Implement actual graph query
            results = []
            entities_found = 0

            try:
                from athena.core.database import get_database
                db = get_database()

                try:
                    cursor = db.conn.cursor()

                    # Query graph entities based on query_type
                    if query_type == "entity_search":
                        # Search for entities by name/label
                        cursor.execute(
                            "SELECT id, name, entity_type, weight FROM entities WHERE name LIKE ? LIMIT ?",
                            (f"%{query}%", max_results)
                        )
                    elif query_type == "relationship":
                        # Find relationships involving entity
                        cursor.execute(
                            """SELECT DISTINCT r.source_id, r.target_id, r.relation_type, e1.name, e2.name
                               FROM relations r
                               JOIN entities e1 ON r.source_id = e1.id
                               JOIN entities e2 ON r.target_id = e2.id
                               WHERE e1.name LIKE ? OR e2.name LIKE ?
                               LIMIT ?""",
                            (f"%{query}%", f"%{query}%", max_results)
                        )
                    else:
                        # Default: entity search
                        cursor.execute(
                            "SELECT id, name, entity_type, weight FROM entities WHERE name LIKE ? LIMIT ?",
                            (f"%{query}%", max_results)
                        )

                    rows = cursor.fetchall()
                    entities_found = len(rows)

                    for row in rows:
                        result_item = {
                            "id": row[0],
                            "name": row[1] if len(row) > 1 else "",
                            "type": row[2] if len(row) > 2 else "unknown"
                        }
                        if include_metadata and len(row) > 3:
                            result_item["weight"] = row[3]
                        results.append(result_item)

                except Exception as db_err:
                    import logging
                    logging.warning(f"Graph query failed: {db_err}")

            except Exception as e:
                import logging
                logging.debug(f"Graph query unavailable: {e}")

            elapsed = (time.time() - start_time) * 1000

            return {
                "query": query,
                "query_type": query_type,
                "entities_found": entities_found,
                "results": results,
                "query_time_ms": elapsed,
                "status": "success"
            }

        except ValueError as e:
            return {
                "error": str(e),
                "status": "error",
                "query_time_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "status": "error",
                "query_time_ms": (time.time() - start_time) * 1000
            }
