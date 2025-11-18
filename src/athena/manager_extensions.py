"""Extensions to UnifiedMemoryManager for confidence scoring and query explanation.

Adds smart confidence scoring and query explanation without modifying core manager.
This module provides wrapper methods for enhanced retrieval with metadata.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .core.confidence_scoring import ConfidenceScorer
from .core.result_models import (
    ConfidenceLevel,
    MemoryWithConfidence,
    QueryExplanation,
)

logger = logging.getLogger(__name__)


class ManagerExtensions:
    """Extensions for UnifiedMemoryManager with confidence and explanation."""

    def __init__(self, manager, meta_store=None):
        """Initialize extensions.

        Args:
            manager: UnifiedMemoryManager instance
            meta_store: Optional MetaMemoryStore for quality metrics
        """
        self.manager = manager
        self.meta_store = meta_store
        self.confidence_scorer = ConfidenceScorer(meta_store=meta_store)

    def retrieve_with_confidence(
        self,
        query: str,
        context: Optional[dict] = None,
        k: int = 5,
        min_confidence: float = 0.3,
        conversation_history: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Retrieve memories with confidence scoring.

        Args:
            query: Search query
            context: Optional context
            k: Number of results
            min_confidence: Minimum confidence threshold (0.3 = include low confidence)
            conversation_history: Optional conversation context

        Returns:
            Dictionary with results and confidence scores
        """
        start_time = time.time()

        # Call base retrieve
        results = self.manager.retrieve(
            query=query,
            context=context,
            k=k,
            conversation_history=conversation_history,
        )

        # Score each result with confidence
        confident_results = {}

        for layer, layer_results in results.items():
            if not layer_results:
                continue

            scored_layer = []

            # Handle list results
            if isinstance(layer_results, list):
                for result in layer_results:
                    # Compute confidence scores
                    memory_id = result.get("id") or result.get("memory_id")
                    content = result.get("content")

                    # Get semantic score if available
                    semantic_score = result.get("score", 0.5)

                    # Compute confidence
                    confidence_breakdown = self.confidence_scorer.score(
                        memory=result,
                        source_layer=layer,
                        semantic_score=semantic_score,
                    )

                    overall_confidence = self.confidence_scorer.aggregate_confidence(
                        confidence_breakdown
                    )

                    # Only include if meets threshold
                    if overall_confidence >= min_confidence:
                        scored_result = MemoryWithConfidence(
                            memory_id=memory_id or f"{layer}:{len(scored_layer)}",
                            content=content or result,
                            confidence=overall_confidence,
                            confidence_level=confidence_breakdown.level(),
                            confidence_breakdown=confidence_breakdown,
                            source_layer=layer,
                        )

                        scored_layer.append(scored_result)

            # Handle dict results
            elif isinstance(layer_results, dict):
                memory_id = layer_results.get("id") or layer_results.get("memory_id")
                semantic_score = layer_results.get("score", 0.5)

                confidence_breakdown = self.confidence_scorer.score(
                    memory=layer_results,
                    source_layer=layer,
                    semantic_score=semantic_score,
                )

                overall_confidence = self.confidence_scorer.aggregate_confidence(
                    confidence_breakdown
                )

                if overall_confidence >= min_confidence:
                    scored_result = MemoryWithConfidence(
                        memory_id=memory_id or layer,
                        content=layer_results.get("content") or layer_results,
                        confidence=overall_confidence,
                        confidence_level=confidence_breakdown.level(),
                        confidence_breakdown=confidence_breakdown,
                        source_layer=layer,
                    )

                    scored_layer.append(scored_result)

            confident_results[layer] = scored_layer

        execution_time = (time.time() - start_time) * 1000  # ms

        return {
            "results": confident_results,
            "execution_time_ms": execution_time,
            "total_results": sum(len(v) for v in confident_results.values()),
        }

    def retrieve_with_explain(
        self,
        query: str,
        context: Optional[dict] = None,
        k: int = 5,
        conversation_history: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Retrieve memories with query explanation.

        Args:
            query: Search query
            context: Optional context
            k: Number of results
            conversation_history: Optional conversation context

        Returns:
            Dictionary with results and query explanation
        """
        start_time = time.time()

        # Classify query
        query_type = self.manager._classify_query(query)

        # Retrieve results
        results = self.manager.retrieve(
            query=query,
            context=context,
            k=k,
            conversation_history=conversation_history,
        )

        # Determine which layers were queried
        layers_queried = list(results.keys())

        # Determine search strategy
        if query_type == "hybrid":
            search_strategy = "Hybrid search across episodic, semantic, and graph"
        else:
            strategy_map = {
                "temporal": "Episodic layer search (time-based)",
                "factual": "Semantic layer search (knowledge-based)",
                "relational": "Graph layer search (relationships)",
                "procedural": "Procedural layer search (workflows)",
                "prospective": "Prospective layer search (tasks/goals)",
                "meta": "Meta-memory layer search (knowledge about knowledge)",
                "planning": "Planning layer search (decomposition)",
            }
            search_strategy = strategy_map.get(query_type, "Unknown strategy")

        # Count total candidates
        total_candidates = sum(len(v) if isinstance(v, list) else 1 for v in results.values() if v)

        # Count returned results
        results_returned = total_candidates

        # Determine filtering applied
        filtering_applied = []
        if context:
            if context.get("files"):
                filtering_applied.append("File path filter")
            if context.get("cwd"):
                filtering_applied.append("Directory context")
            if context.get("task"):
                filtering_applied.append("Task context")

        execution_time = (time.time() - start_time) * 1000  # ms

        # Create explanation
        explanation = QueryExplanation(
            query=query,
            query_type=query_type,
            layers_queried=layers_queried,
            search_strategy=search_strategy,
            total_candidates=total_candidates,
            results_returned=results_returned,
            execution_time_ms=execution_time,
            filtering_applied=filtering_applied,
            ranking_method="Hybrid ranking by layer + semantic relevance",
        )

        return {
            "results": results,
            "explanation": explanation,
        }

    def retrieve_with_all_enhancements(
        self,
        query: str,
        context: Optional[dict] = None,
        k: int = 5,
        min_confidence: float = 0.3,
        conversation_history: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Retrieve memories with both confidence scoring and explanation.

        Args:
            query: Search query
            context: Optional context
            k: Number of results
            min_confidence: Minimum confidence threshold
            conversation_history: Optional conversation context

        Returns:
            Dictionary with results, confidence scores, and explanation
        """
        # Get results with confidence
        confident_response = self.retrieve_with_confidence(
            query=query,
            context=context,
            k=k,
            min_confidence=min_confidence,
            conversation_history=conversation_history,
        )

        # Get explanation
        explain_response = self.retrieve_with_explain(
            query=query,
            context=context,
            k=k,
            conversation_history=conversation_history,
        )

        # Merge results
        return {
            "results": confident_response["results"],
            "confidence": confident_response,
            "explanation": explain_response["explanation"],
            "total_execution_time_ms": confident_response["execution_time_ms"]
            + explain_response["results"].get("execution_time_ms", 0),
        }

    def retrieve_filtered_by_confidence(
        self,
        query: str,
        min_confidence: float = 0.7,
        context: Optional[dict] = None,
        k: int = 5,
        conversation_history: Optional[List[dict]] = None,
    ) -> List[MemoryWithConfidence]:
        """Retrieve only high-confidence results.

        Args:
            query: Search query
            min_confidence: Minimum confidence threshold (0.7 = high confidence only)
            context: Optional context
            k: Number of results
            conversation_history: Optional conversation context

        Returns:
            List of high-confidence results
        """
        response = self.retrieve_with_confidence(
            query=query,
            context=context,
            k=k,
            min_confidence=min_confidence,
            conversation_history=conversation_history,
        )

        # Flatten and sort by confidence
        all_results = []
        for layer_results in response["results"].values():
            if isinstance(layer_results, list):
                all_results.extend(layer_results)

        all_results.sort(key=lambda x: x.confidence, reverse=True)
        return all_results[:k]

    def get_confidence_summary(
        self,
        query: str,
        context: Optional[dict] = None,
        k: int = 5,
        conversation_history: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """Get summary of confidence scores for query results.

        Args:
            query: Search query
            context: Optional context
            k: Number of results
            conversation_history: Optional conversation context

        Returns:
            Dictionary with confidence statistics
        """
        response = self.retrieve_with_confidence(
            query=query,
            context=context,
            k=k,
            conversation_history=conversation_history,
        )

        # Flatten results
        all_results = []
        for layer_results in response["results"].values():
            if isinstance(layer_results, list):
                all_results.extend(layer_results)

        if not all_results:
            return {
                "total": 0,
                "average_confidence": 0.0,
                "max_confidence": 0.0,
                "min_confidence": 0.0,
                "by_level": {
                    "very_high": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "very_low": 0,
                },
            }

        # Calculate stats
        confidences = [r.confidence for r in all_results]

        # Count by level
        by_level = {
            "very_high": sum(
                1 for r in all_results if r.confidence_level == ConfidenceLevel.VERY_HIGH
            ),
            "high": sum(1 for r in all_results if r.confidence_level == ConfidenceLevel.HIGH),
            "medium": sum(1 for r in all_results if r.confidence_level == ConfidenceLevel.MEDIUM),
            "low": sum(1 for r in all_results if r.confidence_level == ConfidenceLevel.LOW),
            "very_low": sum(
                1 for r in all_results if r.confidence_level == ConfidenceLevel.VERY_LOW
            ),
        }

        return {
            "total": len(all_results),
            "average_confidence": sum(confidences) / len(confidences),
            "max_confidence": max(confidences),
            "min_confidence": min(confidences),
            "by_level": by_level,
        }


def create_extended_manager(manager, meta_store=None) -> ManagerExtensions:
    """Create an extended manager with confidence and explanation capabilities.

    Args:
        manager: UnifiedMemoryManager instance
        meta_store: Optional MetaMemoryStore

    Returns:
        ManagerExtensions instance
    """
    return ManagerExtensions(manager, meta_store=meta_store)
