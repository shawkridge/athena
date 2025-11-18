"""Result aggregator for intelligent merging of results from multiple sources.

This module handles combining results from different execution paths:
- Cache results (fast, verified)
- Parallel execution results (fresh, per-layer)
- Distributed execution results (comprehensive)

It resolves conflicts using confidence scores and freshness, ensuring
the best available results are returned to the user.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SourceConfidence:
    """Confidence scores for different result sources."""

    cache_confidence: float = 0.9  # Cache results are usually fresh
    parallel_confidence: float = 0.95  # Real-time parallel execution
    distributed_confidence: float = 0.92  # Distributed execution quality
    sequential_confidence: float = 0.85  # Sequential fallback


class ResultAggregator:
    """Intelligently merges results from multiple execution sources.

    Handles:
    - Cache hits (fast, use if available)
    - Partial cache (merge with fresh results)
    - Conflict resolution (pick best when we have dupes)
    - Result merging (combine from multiple layers)
    - Confidence scoring

    Example:
        aggregator = ResultAggregator(confidence_scorer)

        # Merge results from different sources
        final_results, confidence = aggregator.aggregate_results(
            cache_results={"semantic": [...]},
            parallel_results={"episodic": [...], "procedural": [...]},
            distributed_results=None,
            confidence_scores={"semantic": 0.95, "episodic": 0.90},
        )
    """

    def __init__(self, confidence_scorer=None):
        """Initialize result aggregator.

        Args:
            confidence_scorer: Optional confidence scorer for quality assessment
        """
        self.confidence_scorer = confidence_scorer
        self.source_confidence = SourceConfidence()

        # Statistics
        self.aggregations_performed = 0
        self.conflicts_resolved = 0
        self.cache_contribution = 0

        logger.info("ResultAggregator initialized")

    def aggregate_results(
        self,
        cache_results: Optional[Dict[str, Any]],
        parallel_results: Dict[str, Any],
        distributed_results: Optional[Dict[str, Any]] = None,
        confidence_scores: Optional[Dict[str, float]] = None,
    ) -> Tuple[Dict[str, Any], float]:
        """Intelligently merge results from multiple sources.

        Strategy:
        1. Use cache results if available (most likely fresh)
        2. Fill gaps with parallel results
        3. Fill remaining gaps with distributed results
        4. Handle conflicts with confidence-based selection

        Args:
            cache_results: Results from cross-layer cache (if hit)
            parallel_results: Results from parallel layer execution
            distributed_results: Results from distributed execution (optional)
            confidence_scores: Per-layer confidence scores

        Returns:
            Tuple of (merged_results, overall_confidence)
        """
        self.aggregations_performed += 1

        if confidence_scores is None:
            confidence_scores = {}

        # Start with best available base
        if cache_results and len(cache_results) > 0:
            merged = dict(cache_results)
            base_confidence = self.source_confidence.cache_confidence
            self.cache_contribution += len(cache_results)
            logger.debug(f"Starting merge with cache results: {list(cache_results.keys())}")
        else:
            merged = {}
            base_confidence = 0.5

        # Fill gaps with parallel results
        if parallel_results:
            for layer, results in parallel_results.items():
                if layer not in merged:
                    merged[layer] = results
                    logger.debug(f"Added parallel results for layer: {layer}")
                elif results and merged[layer] is None:
                    # Replace None with actual results
                    merged[layer] = results
                else:
                    # Conflict resolution
                    merged_value, confidence = self._resolve_conflict(
                        layer=layer,
                        cache_value=merged.get(layer),
                        fresh_value=results,
                        cache_age_seconds=0,  # If we got here, cache was recent
                        fresh_confidence=confidence_scores.get(layer, 0.9),
                    )
                    merged[layer] = merged_value
                    self.conflicts_resolved += 1

        # Fill remaining gaps with distributed results
        if distributed_results:
            for layer, results in distributed_results.items():
                if layer not in merged:
                    merged[layer] = results
                    logger.debug(f"Added distributed results for layer: {layer}")
                elif results and merged[layer] is None:
                    merged[layer] = results

        # Calculate overall confidence
        if confidence_scores:
            layer_confidences = [
                conf for layer, conf in confidence_scores.items() if layer in merged
            ]
            if layer_confidences:
                overall_confidence = sum(layer_confidences) / len(layer_confidences)
            else:
                overall_confidence = base_confidence
        else:
            overall_confidence = base_confidence

        # Apply confidence scorer if available
        if self.confidence_scorer:
            try:
                overall_confidence = self.confidence_scorer.score_results(
                    merged, overall_confidence
                )
            except Exception as e:
                logger.warning(f"Confidence scorer failed: {e}")

        logger.debug(
            f"Aggregation complete: {len(merged)} layers, confidence={overall_confidence:.2f}"
        )

        return merged, overall_confidence

    def _resolve_conflict(
        self,
        layer: str,
        cache_value: Any,
        fresh_value: Any,
        cache_age_seconds: float,
        fresh_confidence: float,
    ) -> Tuple[Any, float]:
        """Resolve conflict when we have multiple values for same layer.

        Args:
            layer: Layer name
            cache_value: Value from cache
            fresh_value: Value from fresh execution
            cache_age_seconds: Age of cached value
            fresh_confidence: Confidence in fresh value

        Returns:
            Tuple of (chosen_value, confidence_score)
        """
        # Simple strategy: prefer fresh if significantly different
        # Otherwise prefer cache (already warm and validated)

        if cache_value is None:
            return fresh_value, fresh_confidence

        if fresh_value is None:
            return cache_value, self.source_confidence.cache_confidence

        # For simple comparisons
        try:
            if isinstance(cache_value, (list, dict)) and isinstance(fresh_value, (list, dict)):
                cache_size = len(cache_value)
                fresh_size = len(fresh_value)

                # If sizes differ significantly, prefer fresh (likely more complete)
                if fresh_size > cache_size * 1.2:  # Fresh is >20% larger
                    logger.debug(
                        f"Layer {layer}: preferring fresh results "
                        f"(fresh={fresh_size} > cache={cache_size})"
                    )
                    return fresh_value, fresh_confidence

                # Otherwise prefer cache (shorter age, already in system)
                cache_confidence = max(
                    self.source_confidence.cache_confidence - (cache_age_seconds / 1000.0),
                    0.7,
                )
                logger.debug(
                    f"Layer {layer}: preferring cached results "
                    f"(fresh={fresh_size}, cache={cache_size}, age={cache_age_seconds}s)"
                )
                return cache_value, cache_confidence
        except Exception as e:
            logger.warning(f"Conflict resolution failed for {layer}: {e}")

        # Fallback: prefer fresh
        return fresh_value, fresh_confidence

    def merge_layer_results(
        self,
        layer_name: str,
        partial_results: List[Dict[str, Any]],
        full_results: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Intelligently merge partial and full results from same layer.

        Args:
            layer_name: Name of layer
            partial_results: Partial results (e.g., from cache)
            full_results: Full results (e.g., from fresh query)

        Returns:
            Tuple of (merged_results, confidence)
        """
        if not partial_results:
            return full_results, 0.95

        if not full_results:
            return partial_results, 0.85

        # Merge strategy: take union, with full results having priority
        full_ids = {r.get("id") for r in full_results if "id" in r}
        partial_ids = {r.get("id") for r in partial_results if "id" in r}

        # Results only in partial (from cache)
        cache_only = [r for r in partial_results if r.get("id") not in full_ids]

        # Combine: full results first (fresh), then cache-only
        merged = list(full_results) + cache_only

        # Calculate confidence: higher if both agree, lower if significant difference
        if len(full_ids) > 0:
            agreement = len(full_ids & partial_ids) / len(full_ids | partial_ids)
        else:
            agreement = 0.5

        confidence = 0.9 + (agreement * 0.05)  # 0.9-0.95 range
        confidence = min(confidence, 1.0)

        logger.debug(
            f"Layer {layer_name}: merged {len(merged)} results "
            f"(full={len(full_results)}, cache_only={len(cache_only)}, "
            f"agreement={agreement:.1%})"
        )

        return merged, confidence

    def deduplicate_results(
        self, results: List[Dict[str, Any]], id_field: str = "id"
    ) -> List[Dict[str, Any]]:
        """Remove duplicate results based on ID field.

        Args:
            results: List of result dictionaries
            id_field: Field to use for deduplication

        Returns:
            Deduplicated results list
        """
        seen = set()
        deduplicated = []

        for result in results:
            result_id = result.get(id_field)
            if result_id and result_id not in seen:
                seen.add(result_id)
                deduplicated.append(result)
            elif not result_id:
                # No ID, include it
                deduplicated.append(result)

        if len(deduplicated) < len(results):
            logger.debug(
                f"Deduplicated: removed {len(results) - len(deduplicated)} "
                f"duplicates from {len(results)} results"
            )

        return deduplicated

    def sort_results(
        self, results: List[Dict[str, Any]], key_field: str = "confidence", reverse: bool = True
    ) -> List[Dict[str, Any]]:
        """Sort results by a key field.

        Args:
            results: List of results
            key_field: Field to sort by
            reverse: If True, sort descending

        Returns:
            Sorted results
        """
        try:
            return sorted(results, key=lambda x: x.get(key_field, 0), reverse=reverse)
        except Exception as e:
            logger.warning(f"Sort failed: {e}")
            return results

    def get_aggregation_statistics(self) -> Dict[str, Any]:
        """Get statistics about aggregation performance.

        Returns:
            Dictionary with stats
        """
        return {
            "aggregations_performed": self.aggregations_performed,
            "conflicts_resolved": self.conflicts_resolved,
            "cache_contribution": self.cache_contribution,
            "conflict_resolution_rate": (
                self.conflicts_resolved / max(self.aggregations_performed, 1)
            ),
            "avg_cache_per_aggregation": (
                self.cache_contribution / max(self.aggregations_performed, 1)
            ),
        }

    def reset(self) -> None:
        """Reset statistics (for testing)."""
        self.aggregations_performed = 0
        self.conflicts_resolved = 0
        self.cache_contribution = 0
        logger.info("ResultAggregator reset")
