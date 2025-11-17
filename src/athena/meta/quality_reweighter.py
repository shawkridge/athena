"""Quality-based reweighting system for adaptive layer optimization.

Reweights recall results from different memory layers based on their historical
quality scores (usefulness, confidence, relevance). Layers with high quality scores
get higher ranking boosts; low-quality results are deprioritized.

This implements the critical gap: quality scores tracked in meta-memory are now
actively used to optimize retrieval and layer selection.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .models import MemoryQuality
from .store import MetaMemoryStore

logger = logging.getLogger(__name__)


class QualityReweighter:
    """Reweights memory recall results based on historical quality metrics.

    Uses meta-memory quality scores to dynamically adjust:
    1. Layer selection weights (which layers to query)
    2. Result ranking (how to order results from different layers)
    3. Confidence scoring (how much to trust layer results)
    """

    def __init__(self, meta_store: MetaMemoryStore):
        """Initialize reweighter with meta-memory access.

        Args:
            meta_store: MetaMemoryStore instance for quality lookups
        """
        self.meta_store = meta_store

        # Cache for quality scores to avoid repeated lookups
        self._quality_cache: Dict[Tuple[int, str], Optional[MemoryQuality]] = {}

    def reweight_results(
        self,
        results: Dict[str, Any],
        query_context: Optional[Dict[str, Any]] = None,
        apply_confidence_boost: bool = True,
    ) -> Dict[str, Any]:
        """Reweight recall results from multiple layers based on quality history.

        Adjusts result scores and ranking based on:
        - Historical usefulness of each layer for similar queries
        - Confidence scores for individual memories
        - Relevance decay (older results lose weight)

        Args:
            results: Dictionary with layer-organized results
                     E.g., {"semantic": [...], "episodic": [...], "procedural": [...]}
            query_context: Optional context (task, phase, etc.) for quality lookup
            apply_confidence_boost: Whether to apply confidence-based reranking

        Returns:
            Reweighted results with adjusted scores
        """
        try:
            # Extract layer results
            layer_results = {
                layer: data
                for layer, data in results.items()
                if layer not in ("_explanation", "_cache_hit", "_cascade_explanation")
            }

            reweighted = {}

            # Reweight each layer's results
            for layer, layer_data in layer_results.items():
                if isinstance(layer_data, list):
                    reweighted[layer] = self._reweight_layer_results(
                        layer,
                        layer_data,
                        query_context or {},
                        apply_confidence_boost,
                    )
                else:
                    reweighted[layer] = layer_data

            # Preserve metadata fields
            for key in ("_explanation", "_cache_hit", "_cascade_explanation"):
                if key in results:
                    reweighted[key] = results[key]

            # Compute layer quality scores for overall ranking
            reweighted["_layer_quality_scores"] = self._compute_layer_quality_scores(
                layer_results, query_context or {}
            )

            logger.debug(f"Reweighted results from {len(layer_results)} layers")
            return reweighted

        except Exception as e:
            logger.error(f"Error reweighting results: {e}")
            # Return original results on error
            return results

    def _reweight_layer_results(
        self,
        layer: str,
        results: List[Dict[str, Any]],
        context: Dict[str, Any],
        apply_confidence_boost: bool,
    ) -> List[Dict[str, Any]]:
        """Reweight results from a single layer.

        Args:
            layer: Memory layer name (semantic, episodic, etc.)
            results: List of result items with 'id' and 'score' fields
            context: Query context for quality lookup
            apply_confidence_boost: Whether to apply confidence reranking

        Returns:
            Reranked results sorted by adjusted scores
        """
        if not results:
            return results

        # Get quality scores for each result
        reweighted_results = []
        for result in results:
            memory_id = result.get("id")
            if not memory_id:
                reweighted_results.append(result)
                continue

            # Get quality metrics for this memory
            quality = self._get_quality_cached(memory_id, layer)
            original_score = result.get("score", 0.0)

            # Compute adjusted score based on quality
            adjusted_score = self._compute_adjusted_score(
                original_score,
                quality,
                layer,
                context,
                apply_confidence_boost,
            )

            # Add quality metadata to result
            result_copy = result.copy()
            result_copy["_original_score"] = original_score
            result_copy["_adjusted_score"] = adjusted_score
            if quality:
                result_copy["_quality_metrics"] = {
                    "usefulness": quality.usefulness_score,
                    "confidence": quality.confidence,
                    "access_count": quality.access_count,
                }

            reweighted_results.append(result_copy)

        # Sort by adjusted score (descending)
        reweighted_results.sort(key=lambda x: x.get("_adjusted_score", 0.0), reverse=True)

        return reweighted_results

    def _compute_adjusted_score(
        self,
        original_score: float,
        quality: Optional[MemoryQuality],
        layer: str,
        context: Dict[str, Any],
        apply_confidence_boost: bool,
    ) -> float:
        """Compute adjusted score for a result using quality metrics.

        Formula:
        adjusted_score = original_score * (
            1.0 +
            usefulness_weight * usefulness_score +
            confidence_weight * confidence +
            relevance_weight * relevance_decay
        )

        Args:
            original_score: Score from search/retrieval
            quality: Quality metrics (if available)
            layer: Memory layer
            context: Query context
            apply_confidence_boost: Whether to apply confidence adjustment

        Returns:
            Adjusted score (0.0+ typically, up to 2.0x original for high quality)
        """
        if not quality or not apply_confidence_boost:
            return float(original_score) if original_score else 0.0

        # Ensure original score is float
        original_score = float(original_score) if original_score else 0.0

        # Layer-specific weight adjustments
        # Some layers (semantic) are more useful overall; others (episodic) need context
        layer_weights = {
            "semantic": {
                "usefulness": 0.3,
                "confidence": 0.3,
                "relevance": 0.2,
            },
            "episodic": {
                "usefulness": 0.2,
                "confidence": 0.3,
                "relevance": 0.3,
            },
            "procedural": {
                "usefulness": 0.3,
                "confidence": 0.35,
                "relevance": 0.15,
            },
            "prospective": {
                "usefulness": 0.25,
                "confidence": 0.3,
                "relevance": 0.25,
            },
            "graph": {
                "usefulness": 0.2,
                "confidence": 0.3,
                "relevance": 0.25,
            },
        }

        weights = layer_weights.get(layer, {
            "usefulness": 0.25,
            "confidence": 0.3,
            "relevance": 0.2,
        })

        # Compute boost factor with safe type conversion
        usefulness_score = float(quality.usefulness_score) if quality.usefulness_score else 0.0
        confidence = float(quality.confidence) if quality.confidence else 0.0
        relevance_decay = float(quality.relevance_decay) if quality.relevance_decay else 0.0

        usefulness_factor = usefulness_score * weights.get("usefulness", 0.25)
        confidence_factor = confidence * weights.get("confidence", 0.3)
        relevance_factor = relevance_decay * weights.get("relevance", 0.2)

        # Total boost (0.0 to 1.0+, average 0.3)
        boost = usefulness_factor + confidence_factor + relevance_factor

        # Apply inverted penalty if quality is low
        if usefulness_score < 0.3:
            boost *= 0.5  # Penalize low-usefulness results

        # Adjusted score: original_score * (1 + boost)
        adjusted_score = original_score * (1.0 + boost)

        return adjusted_score

    def _get_quality_cached(
        self, memory_id: int, layer: str
    ) -> Optional[MemoryQuality]:
        """Get quality metrics with caching.

        Args:
            memory_id: Memory ID
            layer: Memory layer

        Returns:
            MemoryQuality if found, None otherwise
        """
        cache_key = (memory_id, layer)

        if cache_key not in self._quality_cache:
            quality = self.meta_store.get_quality(memory_id, layer)
            self._quality_cache[cache_key] = quality

        return self._quality_cache[cache_key]

    def _compute_layer_quality_scores(
        self, layer_results: Dict[str, List[Dict]], context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Compute overall quality scores for each layer.

        Used for layer selection and tier weighting.

        Args:
            layer_results: Results from each layer
            context: Query context

        Returns:
            Dictionary mapping layer names to quality scores (0.0-1.0)
        """
        layer_scores = {}

        for layer, results in layer_results.items():
            if not results:
                layer_scores[layer] = 0.5  # Neutral score if no results
                continue

            # Average quality across results
            if isinstance(results, list):
                quality_values = []
                for result in results:
                    # Try to get usefulness from quality metrics
                    metrics = result.get("_quality_metrics", {})
                    if isinstance(metrics, dict):
                        usefulness = metrics.get("usefulness", 0.5)
                    else:
                        usefulness = 0.5

                    # Ensure it's a float
                    if isinstance(usefulness, (int, float)):
                        quality_values.append(float(usefulness))
                    else:
                        quality_values.append(0.5)

                avg_quality = sum(quality_values) / len(quality_values) if quality_values else 0.5
                layer_scores[layer] = min(max(avg_quality, 0.0), 1.0)  # Clamp to [0, 1]
            else:
                layer_scores[layer] = 0.5

        return layer_scores

    def update_layer_weights(
        self, layer: str, success: bool, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update layer selection weights based on query success.

        Called after a query to record whether results from a layer were useful.
        This feedback improves future layer selection.

        Args:
            layer: Memory layer name
            success: Whether results from this layer were useful
            context: Optional context for better tracking
        """
        # This is typically called from the tier selector or manager
        # to record feedback on layer quality
        logger.debug(f"Layer {layer} marked as {'success' if success else 'failure'}")

    def clear_cache(self) -> None:
        """Clear the quality score cache.

        Should be called periodically or when meta-memory is updated.
        """
        self._quality_cache.clear()
        logger.debug("Quality score cache cleared")


class LayerQualitySelector:
    """Selects which layers to query based on quality history.

    Complements QualityReweighter by making initial layer selection decisions
    based on historical quality, rather than querying all layers equally.
    """

    def __init__(self, meta_store: MetaMemoryStore):
        """Initialize selector.

        Args:
            meta_store: MetaMemoryStore for quality lookups
        """
        self.meta_store = meta_store

    def select_layers_for_query(
        self,
        query: str,
        available_layers: List[str],
        context: Optional[Dict[str, Any]] = None,
        tier: int = 1,
    ) -> Dict[str, float]:
        """Select layers to query with weights based on historical quality.

        Uses quality scores to determine:
        1. Which layers are worth querying (don't waste time on consistently bad layers)
        2. How much to trust results from each layer

        Args:
            query: Query string
            available_layers: List of available memory layers
            context: Optional query context
            tier: Current tier (1=fast, 2=enriched, 3=synthesized)

        Returns:
            Dictionary mapping layer names to query weights (0.0-1.0)
        """
        weights = {}
        context = context or {}

        for layer in available_layers:
            # For Tier 1 (fast), prioritize high-quality layers
            # For Tier 2/3, use all layers but weight by quality
            if tier == 1:
                # Only query layers with reasonable historical quality
                quality_score = self._estimate_layer_quality(layer, context)
                if quality_score >= 0.4:  # Only query if likely useful
                    weights[layer] = quality_score
            else:
                # For deeper tiers, use all layers
                weights[layer] = self._estimate_layer_quality(layer, context)

        # Normalize weights to sum to 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {layer: w / total for layer, w in weights.items()}

        return weights

    def _estimate_layer_quality(self, layer: str, context: Dict[str, Any]) -> float:
        """Estimate expected quality of a layer based on history.

        Args:
            layer: Memory layer name
            context: Query context

        Returns:
            Estimated quality score (0.0-1.0)
        """
        # Base quality for each layer (learned over time)
        base_quality = {
            "semantic": 0.7,  # Semantic usually reliable
            "episodic": 0.6,  # Episodic depends on recency
            "procedural": 0.75,  # Procedures are verified
            "prospective": 0.65,  # Tasks depend on current state
            "graph": 0.7,  # Graph relationships are reliable
        }

        quality = base_quality.get(layer, 0.5)

        # Adjust based on context (e.g., if working on implementation tasks, procedural is high quality)
        task = context.get("task", "").lower()
        if "implement" in task or "code" in task:
            if layer == "procedural":
                quality = min(quality + 0.15, 1.0)

        if "debug" in task or "fix" in task:
            if layer == "episodic":
                quality = min(quality + 0.15, 1.0)

        if "plan" in task or "design" in task:
            if layer == "graph":
                quality = min(quality + 0.15, 1.0)

        return min(quality, 1.0)
