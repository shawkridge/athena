"""Event clustering for consolidation.

Groups episodic events by session ID and spatial context
to identify related memories that should be consolidated together.

Inspired by hippocampal replay mechanisms during sleep.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import List

from ..episodic.models import EpisodicEvent


def _get_event_type_str(event_type) -> str:
    """Safely get event type as string, handling both enum and string types."""
    return event_type.value if hasattr(event_type, "value") else str(event_type)


@dataclass
class EventCluster:
    """A cluster of related episodic events."""

    events: List[EpisodicEvent]
    cluster_type: str  # 'session', 'spatial', 'temporal'
    cohesion_score: float  # How tightly related (0.0-1.0)

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):
        return iter(self.events)


def cluster_events_by_context(
    events: List[EpisodicEvent],
    max_time_gap_minutes: int = 60,
    spatial_similarity_threshold: float = 0.7,
) -> List[List[EpisodicEvent]]:
    """
    Cluster events by session ID and spatial context.

    Algorithm:
    1. Primary clustering: Group by session_id
    2. Secondary clustering: Within sessions, group by spatial proximity
    3. Tertiary clustering: Merge temporally adjacent clusters

    Args:
        events: List of episodic events to cluster
        max_time_gap_minutes: Maximum time between events in same cluster
        spatial_similarity_threshold: Minimum spatial similarity to cluster

    Returns:
        List of event clusters (each cluster is a list of events)
    """
    if not events:
        return []

    # Sort by timestamp
    sorted_events = sorted(events, key=lambda e: e.timestamp)

    # Step 1: Group by session_id
    session_clusters = defaultdict(list)
    for event in sorted_events:
        session_clusters[event.session_id].append(event)

    # Step 2: Within each session, sub-cluster by spatial proximity
    final_clusters = []

    for session_id, session_events in session_clusters.items():
        spatial_subclusters = _cluster_by_spatial_proximity(
            session_events, similarity_threshold=spatial_similarity_threshold
        )

        # Step 3: Merge temporally adjacent clusters
        temporal_clusters = _merge_temporally_adjacent(
            spatial_subclusters, max_gap_minutes=max_time_gap_minutes
        )

        final_clusters.extend(temporal_clusters)

    return final_clusters


def cluster_events_by_surprise(
    events: List[EpisodicEvent], surprise_threshold: float = 3.5, max_time_gap_minutes: int = 60
) -> List[List[EpisodicEvent]]:
    """
    Cluster events using Bayesian surprise as primary signal.

    High-surprise events become cluster centers (event boundaries).
    Related low-surprise events are assigned to nearest high-surprise event.

    Algorithm:
    1. Identify high-surprise events (boundary markers)
    2. Sort by timestamp
    3. Assign each event to nearest high-surprise event temporally
    4. Merge clusters if gap < max_time_gap_minutes

    Args:
        events: List of episodic events with optional surprise scores
        surprise_threshold: Minimum surprise score for boundary markers (default 3.5)
        max_time_gap_minutes: Maximum time between events in same cluster

    Returns:
        List of event clusters using surprise-based boundaries
    """
    if not events:
        return []

    # Sort by timestamp
    sorted_events = sorted(events, key=lambda e: e.timestamp)

    # Find high-surprise events (boundary markers)
    # For events without surprise scores, treat as low-surprise
    high_surprise_events = []
    for event in sorted_events:
        # Check if event has surprise metadata (would be stored in store)
        # For now, we estimate based on event type patterns
        if hasattr(event, "_surprise_score") and event._surprise_score is not None:
            if event._surprise_score >= surprise_threshold:
                high_surprise_events.append(event)
        else:
            # Heuristic: error and decision events are often high-surprise
            event_type_str = (
                event.event_type.value if hasattr(event.event_type, "value") else event.event_type
            )
            if event_type_str in ("error", "decision", "test_run"):
                high_surprise_events.append(event)

    # If no high-surprise events, fall back to standard clustering
    if not high_surprise_events:
        return cluster_events_by_context(events, max_time_gap_minutes)

    # Assign events to nearest high-surprise event
    clusters = []
    cluster_map = {event: [] for event in high_surprise_events}

    for event in sorted_events:
        if event in high_surprise_events:
            continue

        # Find nearest high-surprise event
        nearest = min(
            high_surprise_events,
            key=lambda hs: abs((event.timestamp - hs.timestamp).total_seconds()),
        )

        cluster_map[nearest].append(event)

    # Create final clusters (boundary + assigned events)
    for boundary_event, assigned_events in cluster_map.items():
        cluster = [boundary_event] + assigned_events
        # Sort cluster by timestamp
        cluster.sort(key=lambda e: e.timestamp)
        clusters.append(cluster)

    return clusters


def _cluster_by_spatial_proximity(
    events: List[EpisodicEvent], similarity_threshold: float
) -> List[List[EpisodicEvent]]:
    """
    Cluster events by spatial proximity (shared file paths).

    Events working in the same directory/files are likely related.
    """
    if not events:
        return []

    # Simple greedy clustering
    clusters = []
    assigned = set()

    for i, event1 in enumerate(events):
        if i in assigned:
            continue

        # Start new cluster
        cluster = [event1]
        assigned.add(i)

        # Find spatially similar events
        for j, event2 in enumerate(events[i + 1 :], start=i + 1):
            if j in assigned:
                continue

            similarity = _calculate_spatial_similarity(event1, event2)

            if similarity >= similarity_threshold:
                cluster.append(event2)
                assigned.add(j)

        clusters.append(cluster)

    return clusters


def _calculate_spatial_similarity(event1: EpisodicEvent, event2: EpisodicEvent) -> float:
    """
    Calculate spatial similarity between two events.

    Based on:
    - Shared directory (CWD)
    - Shared files
    - Shared task/phase

    Returns:
        Similarity score between 0.0 and 1.0
    """
    score = 0.0
    weights = []

    # CWD similarity (50% weight)
    if event1.context and event2.context:
        if event1.context.cwd and event2.context.cwd:
            cwd1_parts = event1.context.cwd.split("/")
            cwd2_parts = event2.context.cwd.split("/")

            # Calculate shared path depth
            shared_depth = 0
            for p1, p2 in zip(cwd1_parts, cwd2_parts):
                if p1 == p2:
                    shared_depth += 1
                else:
                    break

            max_depth = max(len(cwd1_parts), len(cwd2_parts))
            cwd_similarity = shared_depth / max_depth if max_depth > 0 else 0.0

            score += 0.5 * cwd_similarity
            weights.append(0.5)

        # File overlap (30% weight)
        files1 = set(event1.context.files or [])
        files2 = set(event2.context.files or [])

        if files1 or files2:
            intersection = files1 & files2
            union = files1 | files2
            file_similarity = len(intersection) / len(union) if union else 0.0

            score += 0.3 * file_similarity
            weights.append(0.3)

        # Task/Phase overlap (20% weight)
        task_match = (
            event1.context.task == event2.context.task
            if event1.context.task and event2.context.task
            else False
        )
        phase_match = (
            event1.context.phase == event2.context.phase
            if event1.context.phase and event2.context.phase
            else False
        )

        if task_match or phase_match:
            score += 0.2
            weights.append(0.2)

    # Normalize by actual weights used
    if weights:
        total_weight = sum(weights)
        return score / total_weight if total_weight > 0 else 0.0

    return 0.0


def _merge_temporally_adjacent(
    clusters: List[List[EpisodicEvent]], max_gap_minutes: int
) -> List[List[EpisodicEvent]]:
    """
    Merge clusters that are temporally adjacent.

    If two clusters have events within max_gap_minutes, merge them.
    """
    if len(clusters) <= 1:
        return clusters

    # Sort clusters by earliest event
    sorted_clusters = sorted(clusters, key=lambda c: min(e.timestamp for e in c))

    merged = []
    current_cluster = sorted_clusters[0]

    for next_cluster in sorted_clusters[1:]:
        # Get latest event in current cluster and earliest in next
        latest_current = max(e.timestamp for e in current_cluster)
        earliest_next = min(e.timestamp for e in next_cluster)

        time_gap_minutes = (earliest_next - latest_current).total_seconds() / 60

        if time_gap_minutes <= max_gap_minutes:
            # Merge clusters
            current_cluster = current_cluster + next_cluster
        else:
            # Save current, start new
            merged.append(current_cluster)
            current_cluster = next_cluster

    # Don't forget the last cluster
    merged.append(current_cluster)

    return merged


def analyze_cluster_quality(cluster: List[EpisodicEvent]) -> dict:
    """
    Analyze the quality/cohesion of an event cluster.

    Returns metrics like:
    - Temporal span (how long the events span)
    - Spatial cohesion (how related the locations are)
    - Causal indicators (errors → fixes, etc.)
    """
    if not cluster:
        return {
            "size": 0,
            "temporal_span_minutes": 0,
            "spatial_cohesion": 0.0,
            "has_causal_chain": False,
        }

    # Temporal span
    timestamps = [e.timestamp for e in cluster]
    temporal_span = (max(timestamps) - min(timestamps)).total_seconds() / 60

    # Spatial cohesion (average pairwise similarity)
    similarities = []
    for i, event1 in enumerate(cluster):
        for event2 in cluster[i + 1 :]:
            sim = _calculate_spatial_similarity(event1, event2)
            similarities.append(sim)

    spatial_cohesion = sum(similarities) / len(similarities) if similarities else 0.0

    # Causal chain detection (error followed by fix)
    has_causal_chain = _detect_causal_chain(cluster)

    return {
        "size": len(cluster),
        "temporal_span_minutes": temporal_span,
        "spatial_cohesion": spatial_cohesion,
        "has_causal_chain": has_causal_chain,
        "event_types": [
            e.event_type.value if hasattr(e.event_type, "value") else e.event_type for e in cluster
        ],
    }


def _detect_causal_chain(cluster: List[EpisodicEvent]) -> bool:
    """
    Detect if cluster contains likely causal relationships.

    Patterns:
    - ERROR → FILE_CHANGE → SUCCESS
    - DECISION → ACTION → SUCCESS
    - TEST_RUN (failure) → FILE_CHANGE → TEST_RUN (success)
    """
    sorted_cluster = sorted(cluster, key=lambda e: e.timestamp)

    for i in range(len(sorted_cluster) - 1):
        current = sorted_cluster[i]
        next_event = sorted_cluster[i + 1]

        # Error → Fix pattern
        current_type = _get_event_type_str(current.event_type)
        if current_type == "error" and next_event.outcome == "success":
            return True

        # Test failure → Fix → Success pattern
        if i < len(sorted_cluster) - 2:
            third = sorted_cluster[i + 2]
            next_type = _get_event_type_str(next_event.event_type)
            third_type = _get_event_type_str(third.event_type)
            if (
                current_type == "test_run"
                and current.outcome == "failure"
                and next_type == "file_change"
                and third_type == "test_run"
                and third.outcome == "success"
            ):
                return True

    return False
