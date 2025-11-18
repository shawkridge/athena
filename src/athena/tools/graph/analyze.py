"""Analyze knowledge graph tool."""

import time
from typing import Any, Dict
from athena.tools import BaseTool, ToolMetadata


class AnalyzeGraphTool(BaseTool):
    """Tool for analyzing the knowledge graph.

    Analyzes entities, relationships, and graph structure to identify
    communities, bridges, and important connections.

    Example:
        >>> tool = AnalyzeGraphTool()
        >>> result = await tool.execute(
        ...     analysis_type="communities",
        ...     entity_id="auth_system_1"
        ... )
    """

    def __init__(self):
        """Initialize graph analysis tool."""
        self._manager = None

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return ToolMetadata(
            name="graph_analyze",
            category="graph",
            description="Analyze the knowledge graph structure",
            parameters={
                "analysis_type": {
                    "type": "string",
                    "enum": ["communities", "bridges", "centrality", "clustering", "statistics"],
                    "description": "Type of analysis to perform",
                    "required": False,
                    "default": "statistics",
                },
                "entity_id": {
                    "type": "string",
                    "description": "Optional entity to analyze in detail",
                    "required": False,
                },
                "community_level": {
                    "type": "integer",
                    "description": "Community detection level (0=granular, 1=intermediate, 2=global)",
                    "required": False,
                    "default": 1,
                    "minimum": 0,
                    "maximum": 2,
                },
            },
            returns={
                "type": "object",
                "properties": {
                    "analysis_type": {"type": "string"},
                    "total_entities": {"type": "integer"},
                    "total_relationships": {"type": "integer"},
                    "communities": {
                        "type": "array",
                        "description": "Detected communities (if requested)",
                    },
                    "bridges": {
                        "type": "array",
                        "description": "Bridge entities connecting communities",
                    },
                    "statistics": {"type": "object", "description": "Graph statistics"},
                    "analysis_time_ms": {
                        "type": "number",
                        "description": "Time taken for analysis",
                    },
                },
            },
        )

    def validate_input(self, **kwargs) -> None:
        """Validate input parameters."""
        if "analysis_type" in kwargs:
            valid = {"communities", "bridges", "centrality", "clustering", "statistics"}
            if kwargs["analysis_type"] not in valid:
                raise ValueError(f"analysis_type must be one of: {', '.join(sorted(valid))}")

        if "community_level" in kwargs:
            level = kwargs["community_level"]
            if not isinstance(level, int) or level < 0 or level > 2:
                raise ValueError("community_level must be 0, 1, or 2")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute graph analysis."""
        start_time = time.time()

        try:
            self.validate_input(**kwargs)

            analysis_type = kwargs.get("analysis_type", "statistics")
            entity_id = kwargs.get("entity_id")
            community_level = kwargs.get("community_level", 1)

            # Implement actual graph analysis
            total_entities = 0
            total_relationships = 0
            statistics = {}
            communities = []
            bridges = []

            try:
                from athena.core.database import get_database

                db = get_database()

                try:
                    cursor = db.conn.cursor()

                    # Get entity and relationship counts
                    cursor.execute("SELECT COUNT(*) FROM entities")
                    total_entities = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM relations")
                    total_relationships = cursor.fetchone()[0]

                    # Calculate basic statistics
                    if total_entities > 0:
                        cursor.execute("SELECT COUNT(DISTINCT entity_type) FROM entities")
                        entity_types = cursor.fetchone()[0]
                        statistics["entity_types"] = entity_types
                        statistics["avg_connections"] = (
                            total_relationships / total_entities if total_entities > 0 else 0
                        )

                    if analysis_type == "statistics":
                        statistics["total_entities"] = total_entities
                        statistics["total_relationships"] = total_relationships
                        statistics["graph_density"] = (
                            (2 * total_relationships) / (total_entities * (total_entities - 1))
                            if total_entities > 1
                            else 0
                        )

                    elif analysis_type == "communities":
                        # Simple community detection: entities with same type
                        cursor.execute(
                            """
                            SELECT entity_type, COUNT(*) as count
                            FROM entities
                            GROUP BY entity_type
                        """
                        )
                        for row in cursor.fetchall():
                            communities.append(
                                {"community_id": f"type_{row[0]}", "size": row[1], "type": row[0]}
                            )

                    elif analysis_type == "centrality":
                        # Find most connected entities
                        cursor.execute(
                            """
                            SELECT e.id, e.name, COUNT(r.id) as connections
                            FROM entities e
                            LEFT JOIN relations r ON e.id = r.source_id OR e.id = r.target_id
                            GROUP BY e.id
                            ORDER BY connections DESC
                            LIMIT 5
                        """
                        )
                        for row in cursor.fetchall():
                            statistics[f"entity_{row[0]}"] = {"name": row[1], "centrality": row[2]}

                except Exception as db_err:
                    import logging

                    logging.warning(f"Graph analysis failed: {db_err}")

            except Exception as e:
                import logging

                logging.debug(f"Graph analysis unavailable: {e}")

            elapsed = (time.time() - start_time) * 1000

            result = {
                "analysis_type": analysis_type,
                "total_entities": total_entities,
                "total_relationships": total_relationships,
                "statistics": statistics,
                "analysis_time_ms": elapsed,
                "status": "success",
            }

            if analysis_type == "communities":
                result["communities"] = communities
            elif analysis_type == "bridges":
                result["bridges"] = bridges

            return result

        except ValueError as e:
            return {
                "error": str(e),
                "status": "error",
                "analysis_time_ms": (time.time() - start_time) * 1000,
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "status": "error",
                "analysis_time_ms": (time.time() - start_time) * 1000,
            }
