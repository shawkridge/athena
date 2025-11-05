"""Advanced Consolidation Metrics - Beyond core compression, recall, consistency, density.

This module implements 6 advanced metrics for measuring consolidation effectiveness:
1. Hallucination Rate - LLM grounding quality
2. Pattern Diversity - Variety of extracted patterns
3. Dual-Process Effectiveness - System 1 vs System 2 comparison
4. Clustering Cohesion - Event grouping quality
5. Pipeline Throughput - Performance metric
6. Search Impact - User-facing improvement

These metrics enable deeper analysis of consolidation quality and help identify
optimization opportunities.
"""

import math
from collections import Counter
from statistics import mean, stdev
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..core.embeddings import cosine_similarity
from ..episodic.models import EpisodicEvent
from ..episodic.store import EpisodicStore
from ..memory.store import MemoryStore


class HallucinationRateCalculator:
    """Measure percentage of patterns with grounding issues.

    Hallucinations occur when patterns are extracted without strong source grounding.
    This metric detects:
    - Patterns with low confidence scores
    - Patterns that don't match source events
    - Novel information not present in source events
    """

    def __init__(self, confidence_threshold_high: float = 0.6,
                 confidence_threshold_medium: float = 0.75):
        """Initialize hallucination calculator.

        Args:
            confidence_threshold_high: Below this = high risk hallucination
            confidence_threshold_medium: Below this = medium risk hallucination
        """
        self.confidence_threshold_high = confidence_threshold_high
        self.confidence_threshold_medium = confidence_threshold_medium

    def calculate(self, patterns: List[Dict]) -> float:
        """Calculate hallucination rate.

        Args:
            patterns: List of extracted patterns with confidence_score

        Returns:
            float (0.0-1.0) representing hallucination rate
        """
        if not patterns:
            return 0.0

        high_risk_count = sum(
            1 for p in patterns
            if p.get('confidence_score', 0.0) < self.confidence_threshold_high
        )
        medium_risk_count = sum(
            1 for p in patterns
            if self.confidence_threshold_high <= p.get('confidence_score', 0.0) < self.confidence_threshold_medium
        )

        # Weight high risk more heavily (2x medium)
        hallucination_count = high_risk_count * 1.0 + medium_risk_count * 0.5
        hallucination_rate = hallucination_count / len(patterns) if patterns else 0.0

        return min(1.0, hallucination_rate)

    def get_risk_breakdown(self, patterns: List[Dict]) -> Dict[str, int]:
        """Get breakdown of risk levels.

        Args:
            patterns: List of extracted patterns

        Returns:
            Dict with high_risk, medium_risk, low_risk counts
        """
        if not patterns:
            return {'high_risk': 0, 'medium_risk': 0, 'low_risk': 0}

        high_risk = sum(
            1 for p in patterns
            if p.get('confidence_score', 0.0) < self.confidence_threshold_high
        )
        medium_risk = sum(
            1 for p in patterns
            if self.confidence_threshold_high <= p.get('confidence_score', 0.0) < self.confidence_threshold_medium
        )
        low_risk = len(patterns) - high_risk - medium_risk

        return {
            'high_risk': high_risk,
            'medium_risk': medium_risk,
            'low_risk': low_risk
        }


class PatternDiversityCalculator:
    """Measure variety of extracted patterns using Shannon entropy.

    Diversity indicates whether consolidation extracts varied pattern types
    (workflows, anti-patterns, best-practices, relationships) or gets stuck
    in a narrow pattern type.

    Higher diversity = better coverage of domain
    """

    def calculate(self, patterns: List[Dict]) -> float:
        """Calculate pattern diversity using Shannon entropy.

        Args:
            patterns: List of extracted patterns with pattern_type

        Returns:
            float (0.0-1.0) where 1.0 = maximum diversity
        """
        if not patterns:
            return 0.0

        # Count pattern types
        type_counts = Counter(p.get('pattern_type', 'unknown') for p in patterns)
        if len(type_counts) == 0:
            return 0.0

        # Calculate Shannon entropy: H = -Σ(p_i * log2(p_i))
        total = len(patterns)
        entropy = 0.0
        for count in type_counts.values():
            if count > 0:
                p_i = count / total
                entropy -= p_i * math.log2(p_i)

        # Normalize by maximum possible entropy (log2 of number of types)
        max_entropy = math.log2(len(type_counts)) if len(type_counts) > 1 else 1.0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        return min(1.0, normalized_entropy)

    def get_type_distribution(self, patterns: List[Dict]) -> Dict[str, int]:
        """Get distribution of pattern types.

        Args:
            patterns: List of extracted patterns

        Returns:
            Dict mapping pattern_type -> count
        """
        return Counter(p.get('pattern_type', 'unknown') for p in patterns)


class DualProcessEffectivenessCalculator:
    """Compare System 1 (heuristics) vs System 2 (LLM) pattern quality.

    System 1: Fast heuristic extraction (uses patterns, rules)
    System 2: Slow LLM-based extraction (uses extended thinking)

    This metric determines which approach works better for the given task.
    """

    def calculate(self, patterns: List[Dict]) -> Dict[str, float]:
        """Calculate dual-process effectiveness.

        Args:
            patterns: List of patterns with extraction_method and confidence_score

        Returns:
            Dict with effectiveness metrics
        """
        if not patterns:
            return {
                'system1_pattern_count': 0,
                'system2_pattern_count': 0,
                'system2_effectiveness_score': 0.0,
                'system1_avg_confidence': 0.0,
                'system2_avg_confidence': 0.0,
                'system2_preferred': False
            }

        system1 = [p for p in patterns if p.get('extraction_method') == 'system1_heuristics']
        system2 = [p for p in patterns if p.get('extraction_method') == 'system2_llm']

        # Calculate average confidence for each system
        s1_confidences = [p.get('confidence_score', 0.0) for p in system1]
        s2_confidences = [p.get('confidence_score', 0.0) for p in system2]

        s1_avg_conf = mean(s1_confidences) if s1_confidences else 0.0
        s2_avg_conf = mean(s2_confidences) if s2_confidences else 0.0

        # System 2 effectiveness: percentage with high confidence (>0.85)
        s2_high_conf = sum(1 for conf in s2_confidences if conf > 0.85)
        s2_effectiveness = s2_high_conf / len(system2) if system2 else 0.0

        return {
            'system1_pattern_count': len(system1),
            'system2_pattern_count': len(system2),
            'system2_effectiveness_score': s2_effectiveness,
            'system1_avg_confidence': s1_avg_conf,
            'system2_avg_confidence': s2_avg_conf,
            'system2_preferred': s2_effectiveness > 0.85
        }

    def get_confidence_distribution(self, patterns: List[Dict]) -> Dict[str, Dict]:
        """Get confidence distribution by system.

        Args:
            patterns: List of patterns

        Returns:
            Dict with system1 and system2 confidence stats
        """
        system1 = [p.get('confidence_score', 0.0) for p in patterns
                   if p.get('extraction_method') == 'system1_heuristics']
        system2 = [p.get('confidence_score', 0.0) for p in patterns
                   if p.get('extraction_method') == 'system2_llm']

        def get_stats(confidences):
            if not confidences:
                return {'count': 0, 'mean': 0.0, 'stdev': 0.0, 'min': 0.0, 'max': 0.0}
            return {
                'count': len(confidences),
                'mean': mean(confidences),
                'stdev': stdev(confidences) if len(confidences) > 1 else 0.0,
                'min': min(confidences),
                'max': max(confidences)
            }

        return {
            'system1': get_stats(system1),
            'system2': get_stats(system2)
        }


class ClusteringCohesionCalculator:
    """Measure how well events are grouped by semantic similarity.

    Cohesion indicates whether the clustering algorithm successfully grouped
    related events together. High cohesion = similar events in same cluster.

    This metric uses semantic similarity to evaluate cluster quality.
    """

    def __init__(self, semantic_store: Optional[MemoryStore] = None):
        """Initialize clustering cohesion calculator.

        Args:
            semantic_store: Optional semantic memory store for similarity calculation
        """
        self.semantic_store = semantic_store

    def calculate(self, clusters: List[List[EpisodicEvent]],
                  embeddings: Optional[Dict[int, np.ndarray]] = None) -> float:
        """Calculate clustering cohesion.

        Args:
            clusters: List of event clusters
            embeddings: Optional dict mapping event_id -> embedding vector

        Returns:
            float (0.0-1.0) where 1.0 = perfect cohesion
        """
        if not clusters:
            return 0.0

        cohesion_scores = []
        for cluster in clusters:
            if len(cluster) < 2:
                # Single-item clusters are perfectly cohesive
                cohesion_scores.append(1.0)
                continue

            # Calculate pairwise similarities within cluster
            similarities = []
            for i, event1 in enumerate(cluster):
                for event2 in cluster[i+1:]:
                    # If embeddings provided, use them; otherwise use semantic similarity
                    if embeddings and event1.id in embeddings and event2.id in embeddings:
                        sim = cosine_similarity(
                            embeddings[event1.id],
                            embeddings[event2.id]
                        )
                    else:
                        # Fallback: text-based similarity
                        sim = self._text_similarity(event1, event2)
                    similarities.append(sim)

            cluster_cohesion = mean(similarities) if similarities else 0.0
            cohesion_scores.append(cluster_cohesion)

        return mean(cohesion_scores) if cohesion_scores else 0.0


    def _text_similarity(self, event1: EpisodicEvent, event2: EpisodicEvent) -> float:
        """Calculate text-based similarity between events.

        Simple implementation: Jaccard similarity of words

        Args:
            event1: First episodic event
            event2: Second episodic event

        Returns:
            Similarity score (0.0-1.0)
        """
        content1 = event1.content.split() if hasattr(event1, 'content') else []
        content2 = event2.content.split() if hasattr(event2, 'content') else []

        if not content1 or not content2:
            return 0.0

        set1 = set(content1)
        set2 = set(content2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    def get_cluster_stats(self, clusters: List[List[EpisodicEvent]]) -> Dict:
        """Get statistics about clustering.

        Args:
            clusters: List of event clusters

        Returns:
            Dict with cluster statistics
        """
        cluster_sizes = [len(c) for c in clusters]

        return {
            'num_clusters': len(clusters),
            'total_events': sum(cluster_sizes),
            'avg_cluster_size': mean(cluster_sizes) if cluster_sizes else 0.0,
            'min_cluster_size': min(cluster_sizes) if cluster_sizes else 0,
            'max_cluster_size': max(cluster_sizes) if cluster_sizes else 0,
            'stdev_cluster_size': stdev(cluster_sizes) if len(cluster_sizes) > 1 else 0.0
        }


class PipelineThroughputCalculator:
    """Measure pipeline performance (patterns extracted per second).

    Throughput indicates how efficient the consolidation pipeline is.
    Higher throughput = can consolidate more events in same time.
    """

    def __init__(self):
        """Initialize throughput tracker."""
        self.stage_times = {}
        self.pattern_count = 0

    def record_stage_duration(self, stage_name: str, duration_seconds: float):
        """Record time spent in a pipeline stage.

        Args:
            stage_name: Name of pipeline stage (e.g., 'clustering', 'extraction')
            duration_seconds: Time spent in stage
        """
        if stage_name not in self.stage_times:
            self.stage_times[stage_name] = []
        self.stage_times[stage_name].append(duration_seconds)

    def record_patterns_extracted(self, count: int):
        """Record number of patterns extracted.

        Args:
            count: Number of patterns extracted
        """
        self.pattern_count += count

    def calculate_throughput(self) -> float:
        """Calculate patterns per second.

        Returns:
            Patterns per second (higher is better)
        """
        total_time = sum(sum(times) for times in self.stage_times.values())
        if total_time <= 0:
            return 0.0

        return self.pattern_count / total_time

    def get_stage_breakdown(self) -> Dict[str, float]:
        """Get time breakdown by stage.

        Returns:
            Dict mapping stage_name -> percentage of total time
        """
        total_time = sum(sum(times) for times in self.stage_times.values())
        if total_time <= 0:
            return {}

        return {
            stage: (sum(times) / total_time * 100)
            for stage, times in self.stage_times.items()
        }

    def get_stage_stats(self) -> Dict[str, Dict[str, float]]:
        """Get detailed stats for each stage.

        Returns:
            Dict with stats for each stage (count, min, max, mean, total)
        """
        stats = {}
        for stage, times in self.stage_times.items():
            if times:
                stats[stage] = {
                    'count': len(times),
                    'min_seconds': min(times),
                    'max_seconds': max(times),
                    'mean_seconds': mean(times),
                    'total_seconds': sum(times)
                }
        return stats


class SearchImpactCalculator:
    """Measure user-facing improvement from consolidation.

    Compares search result quality before and after consolidation to determine
    the actual impact on user queries.
    """

    def measure_impact(self, test_queries: List[str],
                      before_results: List[List[Dict]],
                      after_results: List[List[Dict]]) -> Dict:
        """Measure search quality improvement from consolidation.

        Args:
            test_queries: List of test queries
            before_results: Search results before consolidation
            after_results: Search results after consolidation

        Returns:
            Dict with impact metrics
        """
        if not test_queries:
            return {
                'queries_tested': 0,
                'relevance_improvement': 0.0,
                'queries_improved': 0,
                'queries_degraded': 0
            }

        improvements = []
        for i, query in enumerate(test_queries):
            before_quality = self._rank_result_quality(before_results[i] if i < len(before_results) else [])
            after_quality = self._rank_result_quality(after_results[i] if i < len(after_results) else [])

            if before_quality > 0:
                improvement = (after_quality - before_quality) / before_quality
            else:
                improvement = 1.0 if after_quality > 0 else 0.0

            improvements.append(improvement)

        improved_count = sum(1 for i in improvements if i > 0.01)  # >1% improvement
        degraded_count = sum(1 for i in improvements if i < -0.01)  # >1% degradation

        return {
            'queries_tested': len(test_queries),
            'relevance_improvement': mean(improvements) if improvements else 0.0,
            'queries_improved': improved_count,
            'queries_degraded': degraded_count,
            'queries_unchanged': len(test_queries) - improved_count - degraded_count
        }

    def _rank_result_quality(self, results: List[Dict]) -> float:
        """Calculate quality score of search results.

        Weights top results more heavily using DCG (Discounted Cumulative Gain).

        Args:
            results: List of search results with relevance_score

        Returns:
            Quality score (0.0-1.0)
        """
        if not results:
            return 0.0

        quality_score = 0.0
        for i, result in enumerate(results[:5]):
            relevance = result.get('relevance_score', 0.0)
            # DCG: weight = 1 / log2(position + 1)
            position_weight = 1.0 / math.log2(i + 2) if i < 5 else 0.0
            quality_score += relevance * position_weight

        return quality_score

    def get_per_query_metrics(self, test_queries: List[str],
                             before_results: List[List[Dict]],
                             after_results: List[List[Dict]]) -> List[Dict]:
        """Get detailed metrics for each query.

        Args:
            test_queries: List of test queries
            before_results: Before consolidation results
            after_results: After consolidation results

        Returns:
            List of dicts with per-query metrics
        """
        metrics = []
        for i, query in enumerate(test_queries):
            before_quality = self._rank_result_quality(before_results[i] if i < len(before_results) else [])
            after_quality = self._rank_result_quality(after_results[i] if i < len(after_results) else [])

            improvement = (after_quality - before_quality) / max(before_quality, 0.01)

            metrics.append({
                'query': query,
                'before_quality': before_quality,
                'after_quality': after_quality,
                'improvement_delta': improvement,
                'status': 'improved' if improvement > 0.01 else ('degraded' if improvement < -0.01 else 'unchanged')
            })

        return metrics
