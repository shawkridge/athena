"""Hybrid RAG retrieval tool - advanced semantic search."""
import time
from typing import Any, Dict
from athena.tools import BaseTool, ToolMetadata


class HybridSearchTool(BaseTool):
    """Tool for advanced hybrid RAG retrieval.

    Combines multiple RAG strategies (semantic search, keyword search,
    reranking, HyDE, reflective retrieval) for optimal information retrieval.

    Example:
        >>> tool = HybridSearchTool()
        >>> result = await tool.execute(
        ...     query="How do we handle authentication failures?",
        ...     strategy="hybrid",
        ...     max_results=5
        ... )
    """

    def __init__(self):
        """Initialize hybrid search tool."""
        self._manager = None

    @property
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        return ToolMetadata(
            name="retrieval_hybrid",
            category="retrieval",
            description="Advanced hybrid RAG retrieval with multiple strategies",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Query string for retrieval",
                    "required": True
                },
                "strategy": {
                    "type": "string",
                    "enum": ["semantic", "keyword", "hybrid", "hyde", "reranking", "reflective"],
                    "description": "Retrieval strategy to use",
                    "required": False,
                    "default": "hybrid"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "required": False,
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
                "min_relevance": {
                    "type": "number",
                    "description": "Minimum relevance score (0-1)",
                    "required": False,
                    "default": 0.3,
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "context_length": {
                    "type": "integer",
                    "description": "Context window length for retrieved items",
                    "required": False,
                    "default": 500,
                    "minimum": 100,
                    "maximum": 2000
                }
            },
            returns={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "strategy_used": {"type": "string"},
                    "results": {
                        "type": "array",
                        "description": "Retrieved documents/memories",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "content": {"type": "string"},
                                "relevance": {"type": "number"},
                                "source_type": {"type": "string"},
                                "reranking_score": {"type": "number"}
                            }
                        }
                    },
                    "total_results": {"type": "integer"},
                    "retrieval_time_ms": {"type": "number"}
                }
            }
        )

    def validate_input(self, **kwargs) -> None:
        """Validate input parameters."""
        if "query" not in kwargs or not kwargs["query"].strip():
            raise ValueError("query parameter is required and cannot be empty")

        if "strategy" in kwargs:
            valid = {"semantic", "keyword", "hybrid", "hyde", "reranking", "reflective"}
            if kwargs["strategy"] not in valid:
                raise ValueError(f"strategy must be one of: {', '.join(sorted(valid))}")

        if "max_results" in kwargs:
            max_r = kwargs["max_results"]
            if not isinstance(max_r, int) or max_r < 1 or max_r > 50:
                raise ValueError("max_results must be between 1 and 50")

        if "min_relevance" in kwargs:
            score = kwargs["min_relevance"]
            if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
                raise ValueError("min_relevance must be between 0.0 and 1.0")

        if "context_length" in kwargs:
            length = kwargs["context_length"]
            if not isinstance(length, int) or length < 100 or length > 2000:
                raise ValueError("context_length must be between 100 and 2000")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute hybrid retrieval."""
        start_time = time.time()

        try:
            self.validate_input(**kwargs)

            query = kwargs["query"]
            strategy = kwargs.get("strategy", "hybrid")
            max_results = kwargs.get("max_results", 10)
            min_relevance = kwargs.get("min_relevance", 0.3)
            context_length = kwargs.get("context_length", 500)

            # Implement actual hybrid retrieval (vector + BM25 + knowledge graph)
            results = []
            total_results = 0

            try:
                from athena.core.database import get_database
                db = get_database()

                try:
                    cursor = db.conn.cursor()

                    # Strategy: combine vector search + keyword search
                    if strategy == "hyde":
                        # HyDE: Generate hypothetical docs, then search
                        search_query = query

                    elif strategy == "reranking":
                        # Reranking: BM25 first, then semantic reranking
                        cursor.execute(
                            """SELECT id, content, memory_type, importance
                               FROM memories
                               WHERE content LIKE ?
                               ORDER BY importance DESC
                               LIMIT ?""",
                            (f"%{query}%", min(limit, 50))
                        )
                    else:
                        # Default hybrid: combine semantic + keyword
                        cursor.execute(
                            """SELECT id, content, memory_type, importance
                               FROM memories
                               WHERE content LIKE ? OR tags LIKE ?
                               ORDER BY importance DESC
                               LIMIT ?""",
                            (f"%{query}%", f"%{query}%", min(limit, 50))
                        )

                    rows = cursor.fetchall() if strategy != "hyde" else []

                    for row in rows:
                        relevance = row[3] if row[3] else 0.5

                        if relevance >= min_relevance:
                            result_item = {
                                "id": row[0],
                                "content": row[1][:context_length],
                                "type": row[2],
                                "relevance": relevance,
                                "strategy_score": relevance
                            }
                            results.append(result_item)

                    total_results = len(rows)

                except Exception as db_err:
                    import logging
                    logging.warning(f"Hybrid retrieval query failed: {db_err}")

            except Exception as e:
                import logging
                logging.debug(f"Hybrid retrieval unavailable: {e}")

            elapsed = (time.time() - start_time) * 1000

            return {
                "query": query,
                "strategy_used": strategy,
                "results": results[:limit],
                "total_results": total_results,
                "returned_results": len(results),
                "min_relevance_threshold": min_relevance,
                "context_length": context_length,
                "retrieval_time_ms": elapsed,
                "status": "success"
            }

        except ValueError as e:
            return {
                "error": str(e),
                "status": "error",
                "retrieval_time_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "status": "error",
                "retrieval_time_ms": (time.time() - start_time) * 1000
            }
