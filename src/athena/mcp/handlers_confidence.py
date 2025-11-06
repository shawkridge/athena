"""MCP tool handlers for confidence scoring and query explanation.

Exposes confidence scoring and query explanation as MCP tools:
- recall_with_confidence: Get results with confidence scores
- recall_with_explain: Get results with query explanation
- query_confidence_summary: Get confidence statistics
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConfidenceToolHandlers:
    """MCP tool handlers for confidence and explanation."""

    def __init__(self, server, manager_extensions):
        """Initialize confidence tool handlers.

        Args:
            server: MCP server instance
            manager_extensions: ManagerExtensions instance with enhanced retrieval
        """
        self.server = server
        self.manager_extensions = manager_extensions

    def register_tools(self) -> None:
        """Register confidence and explain tools with MCP server."""
        if not hasattr(self.server, "tool"):
            logger.warning("MCP server does not have tool registration method")
            return

        # Register recall_with_confidence tool
        @self.server.tool()
        def recall_with_confidence(
            query: str,
            min_confidence: float = 0.3,
            k: int = 5,
        ) -> Dict[str, Any]:
            """Recall memories with confidence scores.

            Each result includes a confidence score (0-1) based on:
            - Semantic relevance (35%)
            - Source quality (25%)
            - Recency (15%)
            - Consistency (15%)
            - Completeness (10%)

            Args:
                query: Search query
                min_confidence: Minimum confidence threshold (0.3=include low, 0.7=only high)
                k: Maximum results to return

            Returns:
                Dictionary with results grouped by layer, each with confidence scores
            """
            try:
                response = self.manager_extensions.retrieve_with_confidence(
                    query=query,
                    k=k,
                    min_confidence=min_confidence,
                )

                # Convert to JSON-serializable format
                results = {}
                for layer, layer_results in response["results"].items():
                    results[layer] = []
                    for result in layer_results:
                        results[layer].append({
                            "memory_id": result.memory_id,
                            "content": str(result.content)[:200],  # Truncate
                            "confidence": round(result.confidence, 3),
                            "confidence_level": result.confidence_level,
                            "source_layer": result.source_layer,
                            "breakdown": {
                                "semantic_relevance": round(
                                    result.confidence_breakdown.semantic_relevance, 3
                                ),
                                "source_quality": round(
                                    result.confidence_breakdown.source_quality, 3
                                ),
                                "recency": round(result.confidence_breakdown.recency, 3),
                                "consistency": round(
                                    result.confidence_breakdown.consistency, 3
                                ),
                                "completeness": round(
                                    result.confidence_breakdown.completeness, 3
                                ),
                            },
                        })

                return {
                    "status": "success",
                    "results": results,
                    "execution_time_ms": response["execution_time_ms"],
                    "total_results": response["total_results"],
                }

            except Exception as e:
                logger.error(f"Error in recall_with_confidence: {e}")
                return {"status": "error", "error": str(e)}

        # Register recall_with_explain tool
        @self.server.tool()
        def recall_with_explain(
            query: str,
            k: int = 5,
        ) -> Dict[str, Any]:
            """Recall memories with query explanation.

            Returns detailed explanation of how the query was processed:
            - Query type classification
            - Layers queried
            - Search strategy used
            - Filtering applied
            - Ranking method

            Args:
                query: Search query
                k: Maximum results to return

            Returns:
                Dictionary with results and query explanation
            """
            try:
                response = self.manager_extensions.retrieve_with_explain(
                    query=query,
                    k=k,
                )

                explanation = response["explanation"]

                return {
                    "status": "success",
                    "query": explanation.query,
                    "classification": {
                        "query_type": explanation.query_type,
                        "layers_queried": explanation.layers_queried,
                    },
                    "strategy": {
                        "search_strategy": explanation.search_strategy,
                        "ranking_method": explanation.ranking_method,
                    },
                    "execution": {
                        "total_candidates": explanation.total_candidates,
                        "results_returned": explanation.results_returned,
                        "execution_time_ms": round(explanation.execution_time_ms, 2),
                    },
                    "filtering": {
                        "filters_applied": explanation.filtering_applied,
                    },
                    "results_summary": {
                        layer: len(results) if isinstance(results, list) else 1
                        for layer, results in response["results"].items()
                    },
                }

            except Exception as e:
                logger.error(f"Error in recall_with_explain: {e}")
                return {"status": "error", "error": str(e)}

        # Register query_confidence_summary tool
        @self.server.tool()
        def query_confidence_summary(
            query: str,
            k: int = 5,
        ) -> Dict[str, Any]:
            """Get confidence statistics for query results.

            Provides summary of confidence scores:
            - Average confidence
            - Min/max confidence
            - Distribution by confidence level

            Args:
                query: Search query
                k: Maximum results to analyze

            Returns:
                Dictionary with confidence statistics
            """
            try:
                summary = self.manager_extensions.get_confidence_summary(
                    query=query,
                    k=k,
                )

                return {
                    "status": "success",
                    "query": query,
                    "statistics": {
                        "total_results": summary["total"],
                        "average_confidence": round(summary["average_confidence"], 3),
                        "max_confidence": round(summary["max_confidence"], 3),
                        "min_confidence": round(summary["min_confidence"], 3),
                    },
                    "by_confidence_level": {
                        "very_high": summary["by_level"]["very_high"],
                        "high": summary["by_level"]["high"],
                        "medium": summary["by_level"]["medium"],
                        "low": summary["by_level"]["low"],
                        "very_low": summary["by_level"]["very_low"],
                    },
                }

            except Exception as e:
                logger.error(f"Error in query_confidence_summary: {e}")
                return {"status": "error", "error": str(e)}

        # Register recall_high_confidence tool
        @self.server.tool()
        def recall_high_confidence(
            query: str,
            k: int = 5,
        ) -> List[Dict[str, Any]]:
            """Recall only high-confidence results (confidence >= 0.7).

            Filters results to only include high-confidence matches.
            Useful when you need reliable, well-supported information.

            Args:
                query: Search query
                k: Maximum results to return

            Returns:
                List of high-confidence results
            """
            try:
                results = self.manager_extensions.retrieve_filtered_by_confidence(
                    query=query,
                    min_confidence=0.7,
                    k=k,
                )

                return [
                    {
                        "memory_id": result.memory_id,
                        "content": str(result.content)[:500],
                        "confidence": round(result.confidence, 3),
                        "confidence_level": result.confidence_level,
                        "source_layer": result.source_layer,
                    }
                    for result in results
                ]

            except Exception as e:
                logger.error(f"Error in recall_high_confidence: {e}")
                return []

    def register_with_operation_router(self, router) -> None:
        """Register handlers with operation router.

        Args:
            router: OperationRouter instance
        """
        handlers_map = {
            "recall_with_confidence": self._handle_recall_with_confidence,
            "recall_with_explain": self._handle_recall_with_explain,
            "query_confidence_summary": self._handle_query_confidence_summary,
            "recall_high_confidence": self._handle_recall_high_confidence,
        }

        for operation, handler in handlers_map.items():
            router.register(operation, handler)

    def _handle_recall_with_confidence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle recall_with_confidence operation."""
        query = params.get("query", "")
        min_confidence = float(params.get("min_confidence", 0.3))
        k = int(params.get("k", 5))

        response = self.manager_extensions.retrieve_with_confidence(
            query=query,
            k=k,
            min_confidence=min_confidence,
        )

        # Convert to JSON-serializable format
        results = {}
        for layer, layer_results in response["results"].items():
            results[layer] = []
            for result in layer_results:
                results[layer].append({
                    "memory_id": result.memory_id,
                    "content": str(result.content)[:200],
                    "confidence": round(result.confidence, 3),
                    "confidence_level": result.confidence_level,
                })

        return {
            "status": "success",
            "results": results,
            "total_results": response["total_results"],
        }

    def _handle_recall_with_explain(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle recall_with_explain operation."""
        query = params.get("query", "")
        k = int(params.get("k", 5))

        response = self.manager_extensions.retrieve_with_explain(
            query=query,
            k=k,
        )

        explanation = response["explanation"]

        return {
            "status": "success",
            "query_type": explanation.query_type,
            "layers_queried": explanation.layers_queried,
            "search_strategy": explanation.search_strategy,
            "execution_time_ms": round(explanation.execution_time_ms, 2),
        }

    def _handle_query_confidence_summary(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle query_confidence_summary operation."""
        query = params.get("query", "")
        k = int(params.get("k", 5))

        summary = self.manager_extensions.get_confidence_summary(query=query, k=k)

        return {
            "status": "success",
            "average_confidence": round(summary["average_confidence"], 3),
            "total_results": summary["total"],
            "by_level": summary["by_level"],
        }

    def _handle_recall_high_confidence(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle recall_high_confidence operation."""
        query = params.get("query", "")
        k = int(params.get("k", 5))

        results = self.manager_extensions.retrieve_filtered_by_confidence(
            query=query,
            min_confidence=0.7,
            k=k,
        )

        return [
            {
                "memory_id": result.memory_id,
                "confidence": round(result.confidence, 3),
                "content": str(result.content)[:200],
            }
            for result in results
        ]
