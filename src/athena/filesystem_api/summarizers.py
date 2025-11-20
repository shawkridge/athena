"""
Result Summarizers for Filesystem API

Converts full datasets into summaries (<500 tokens) for model context.
Philosophy: Return metrics, counts, IDs, and top-N items, never full objects.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import statistics
from datetime import datetime


@dataclass
class SummaryStats:
    """Statistics summary for any dataset."""

    total_count: int
    filtered_count: int
    avg_score: Optional[float] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    date_range: Optional[tuple] = None
    top_ids: Optional[List[Any]] = None
    categories: Optional[Dict[str, int]] = None


class BaseSummarizer:
    """Base class for all result summarizers."""

    @staticmethod
    def summarize_list(
        items: List[Dict[str, Any]],
        score_field: Optional[str] = None,
        id_field: str = "id",
        filter_fn=None,
        limit: int = 3,
    ) -> Dict[str, Any]:
        """
        Summarize a list of items.

        Args:
            items: List of dictionaries
            score_field: Field to compute statistics on
            id_field: Field to extract IDs from
            filter_fn: Optional filter function
            limit: Number of top IDs to include

        Returns:
            Summary dict with counts and metrics
        """
        if not items:
            return {"total": 0, "filtered": 0, "empty": True}

        # Filter if needed
        filtered = items
        if filter_fn:
            filtered = [item for item in items if filter_fn(item)]

        summary = {
            "total": len(items),
            "filtered": len(filtered),
            "top_ids": [item.get(id_field) for item in filtered[:limit]],
        }

        # Add score statistics if available
        if score_field:
            scores = [item.get(score_field) for item in filtered if score_field in item]
            if scores:
                summary["avg_score"] = statistics.mean(scores)
                summary["min_score"] = min(scores)
                summary["max_score"] = max(scores)

        return summary

    @staticmethod
    def summarize_temporal(
        items: List[Dict[str, Any]], timestamp_field: str = "timestamp"
    ) -> Dict[str, Any]:
        """Summarize time-based data."""
        if not items:
            return {"total": 0, "time_range": None}

        timestamps = [item.get(timestamp_field) for item in items if timestamp_field in item]

        if not timestamps:
            return {"total": len(items)}

        return {
            "total": len(items),
            "earliest": min(timestamps),
            "latest": max(timestamps),
            "time_span_days": (
                (max(timestamps) - min(timestamps)).days
                if isinstance(timestamps[0], datetime)
                else None
            ),
        }

    @staticmethod
    def summarize_graph(
        entities: List[Dict[str, Any]], relations: List[Dict[str, Any]] = None, id_field: str = "id"
    ) -> Dict[str, Any]:
        """Summarize graph structure."""
        summary = {
            "entity_count": len(entities),
            "entity_types": {},
            "top_entity_ids": [e.get(id_field) for e in entities[:5]],
        }

        # Count by type
        for entity in entities:
            entity_type = entity.get("type", "unknown")
            summary["entity_types"][entity_type] = summary["entity_types"].get(entity_type, 0) + 1

        if relations:
            summary["relation_count"] = len(relations)
            summary["relation_types"] = {}
            for rel in relations:
                rel_type = rel.get("type", "unknown")
                summary["relation_types"][rel_type] = summary["relation_types"].get(rel_type, 0) + 1

            # Calculate connectivity
            summary["avg_connections_per_entity"] = len(relations) / max(1, len(entities))

        return summary

    @staticmethod
    def summarize_distribution(
        items: List[Dict[str, Any]], category_field: str, score_field: Optional[str] = None
    ) -> Dict[str, Any]:
        """Summarize distribution across categories."""
        distribution = {}
        scores_by_category = {}

        for item in items:
            category = item.get(category_field, "unknown")
            distribution[category] = distribution.get(category, 0) + 1

            if score_field and score_field in item:
                if category not in scores_by_category:
                    scores_by_category[category] = []
                scores_by_category[category].append(item[score_field])

        summary = {"distribution": distribution}

        if scores_by_category:
            summary["avg_score_by_category"] = {
                cat: statistics.mean(scores) for cat, scores in scores_by_category.items()
            }

        return summary


class EpisodicSummarizer(BaseSummarizer):
    """Summarizer for episodic memory events."""

    @staticmethod
    def summarize_events(
        events: List[Dict[str, Any]], confidence_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Summarize episodic events by filtering and statistics."""
        high_conf = [e for e in events if e.get("confidence", 0) > confidence_threshold]

        return {
            "total_found": len(events),
            "high_confidence_count": len(high_conf),
            "avg_confidence": statistics.mean([e.get("confidence", 0) for e in events]),
            "confidence_distribution": {
                "high": len([e for e in events if e.get("confidence", 0) > 0.8]),
                "medium": len([e for e in events if 0.5 < e.get("confidence", 0) <= 0.8]),
                "low": len([e for e in events if e.get("confidence", 0) <= 0.5]),
            },
            "top_3_ids": [e.get("id") for e in high_conf[:3]],
            "event_types": EpisodicSummarizer._count_by_field(events, "event_type"),
        }

    @staticmethod
    def _count_by_field(items: List[Dict], field: str) -> Dict[str, int]:
        """Count items by field value."""
        counts = {}
        for item in items:
            key = item.get(field, "unknown")
            counts[key] = counts.get(key, 0) + 1
        return counts


class SemanticSummarizer(BaseSummarizer):
    """Summarizer for semantic memory."""

    @staticmethod
    def summarize_search_results(
        memories: List[Dict[str, Any]], confidence_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Summarize semantic search results."""
        high_conf = [m for m in memories if m.get("confidence", 0) > confidence_threshold]

        return {
            "total_results": len(memories),
            "high_confidence_count": len(high_conf),
            "avg_confidence": (
                statistics.mean([m.get("confidence", 0) for m in memories]) if memories else 0
            ),
            "confidence_percentiles": {
                "p10": (
                    sorted([m.get("confidence", 0) for m in memories])[len(memories) // 10]
                    if memories
                    else 0
                ),
                "p50": (
                    sorted([m.get("confidence", 0) for m in memories])[len(memories) // 2]
                    if memories
                    else 0
                ),
                "p90": (
                    sorted([m.get("confidence", 0) for m in memories])[len(memories) * 9 // 10]
                    if memories
                    else 0
                ),
            },
            "top_5_ids": [m.get("id") for m in high_conf[:5]],
            "memory_types": SemanticSummarizer._count_by_field(memories, "type"),
            "domains": SemanticSummarizer._count_by_field(memories, "domain"),
        }


class GraphSummarizer(BaseSummarizer):
    """Summarizer for knowledge graph data."""

    @staticmethod
    def summarize_traversal(
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        communities: Optional[List[List[str]]] = None,
    ) -> Dict[str, Any]:
        """Summarize graph traversal results."""
        summary = GraphSummarizer.summarize_graph(entities, relations)

        if communities:
            summary["community_count"] = len(communities)
            summary["avg_community_size"] = statistics.mean([len(c) for c in communities])
            summary["largest_community_size"] = (
                max(len(c) for c in communities) if communities else 0
            )

            # Find bridges (entities in multiple communities)
            all_entities = set()
            for c in communities:
                all_entities.update(c)
            summary["total_entities_in_communities"] = len(all_entities)

        return summary


class ConsolidationSummarizer(BaseSummarizer):
    """Summarizer for consolidation results."""

    @staticmethod
    def summarize_patterns(patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize extracted patterns."""
        if not patterns:
            return {"total_patterns": 0, "empty": True}

        confidences = [p.get("confidence", 0) for p in patterns]
        supports = [p.get("support", 0) for p in patterns]

        return {
            "total_patterns": len(patterns),
            "pattern_types": ConsolidationSummarizer._count_by_field(patterns, "type"),
            "avg_confidence": statistics.mean(confidences),
            "confidence_range": (min(confidences), max(confidences)),
            "avg_support": statistics.mean(supports),
            "top_5_by_confidence": [
                {"type": p.get("type"), "confidence": p.get("confidence"), "id": p.get("id")}
                for p in sorted(patterns, key=lambda x: x.get("confidence", 0), reverse=True)[:5]
            ],
        }


class PlanningSummarizer(BaseSummarizer):
    """Summarizer for planning results."""

    @staticmethod
    def summarize_decomposition(
        tasks: List[Dict[str, Any]], depth_levels: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Summarize task decomposition."""
        if not tasks:
            return {"total_tasks": 0, "empty": True}

        return {
            "total_tasks": len(tasks),
            "status_distribution": PlanningSummarizer._count_by_field(tasks, "status"),
            "priority_distribution": PlanningSummarizer._count_by_field(tasks, "priority"),
            "avg_estimated_effort": statistics.mean(
                [t.get("estimated_effort", 0) for t in tasks if "estimated_effort" in t]
            ),
            "depth_levels": depth_levels,
            "critical_path_length": max([t.get("depth", 0) for t in tasks]) if tasks else 0,
        }

    @staticmethod
    def summarize_validation(validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize plan validation results."""
        return {
            "valid": validation_results.get("valid", False),
            "passed_properties": [
                p for p in validation_results.get("properties", []) if p.get("passed")
            ],
            "failed_properties": [
                p for p in validation_results.get("properties", []) if not p.get("passed")
            ],
            "confidence_score": validation_results.get("confidence_score", 0),
            "total_checks": len(validation_results.get("properties", [])),
        }
