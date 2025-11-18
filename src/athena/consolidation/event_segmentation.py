"""Event Segmentation via Bayesian Surprise Detection.

Implements event segmentation using K-L divergence (Bayesian surprise) to detect
boundaries between meaningful episodes in a stream of events.

Based on:
- Event Segmentation Theory (Zacks & Kurby, 2008)
- Bayesian Surprise (Itti & Baldi, 2009)
- Foundational implementation approach (Fountas et al., 2024)

Key Components:
1. EventEncoder - Convert events to feature vectors
2. BayesianSurpriseCalculator - Calculate K-L divergence surprise
3. EventSegmenter - Detect boundaries using surprise + modularity
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..episodic.models import EpisodicEvent


@dataclass
class EventFeatures:
    """Features extracted from an episodic event for surprise calculation."""

    embedding: np.ndarray  # 384-dim semantic vector
    entities: List[str]  # Entity types mentioned
    temporal_delta: float  # Seconds since previous event
    causal_parents: List[int]  # IDs of causally-prior events
    event_type: str  # Event classification
    tags: List[str]  # Semantic tags
    original_event: Optional[EpisodicEvent] = None  # Reference back to source


class EventEncoder:
    """Encode episodic events into comparable feature vectors.

    Converts episodic events into feature representations that enable
    surprise calculation.
    """

    def __init__(self, embedding_model=None):
        """Initialize event encoder.

        Args:
            embedding_model: Optional embedding model (nomic-embed-text, etc.)
        """
        self.embedding_model = embedding_model

    def encode(
        self, event: EpisodicEvent, prev_event_time: Optional[float] = None
    ) -> EventFeatures:
        """Encode event into features for surprise calculation.

        Args:
            event: Episodic event to encode
            prev_event_time: Timestamp of previous event (for temporal delta)

        Returns:
            EventFeatures with all components
        """
        # Embedding: semantic vector of event content
        embedding = self._get_embedding(event.content)

        # Entities: extract from event metadata
        entities = self._extract_entities(event)

        # Temporal delta: seconds since last event
        temporal_delta = self._calculate_temporal_delta(event, prev_event_time)

        # Causal parents: infer from event structure (simplified)
        causal_parents = self._find_causal_parents(event)

        # Event type and tags
        event_type = event.event_type
        tags = getattr(event, "tags", [])

        return EventFeatures(
            embedding=embedding,
            entities=entities,
            temporal_delta=temporal_delta,
            causal_parents=causal_parents,
            event_type=event_type,
            tags=tags,
            original_event=event,
        )

    def _get_embedding(self, content: str) -> np.ndarray:
        """Get semantic embedding of event content.

        Args:
            content: Event text content

        Returns:
            384-dimensional embedding vector
        """
        if self.embedding_model:
            return self.embedding_model.embed(content)
        else:
            # Fallback: random embedding for testing
            # In production, use actual embedding model
            return np.random.randn(384)

    def _extract_entities(self, event: EpisodicEvent) -> List[str]:
        """Extract entity types from event.

        Args:
            event: Episodic event

        Returns:
            List of entity type strings
        """
        # Try to get entities from event metadata
        if hasattr(event, "entities"):
            return event.entities

        # Fallback: extract from content (simplified)
        entities = []
        content = event.content.lower()

        # Pattern matching for common entity types
        if "error" in content or "fail" in content:
            entities.append("error")
        if "success" in content or "complete" in content:
            entities.append("success")
        if "start" in content or "begin" in content:
            entities.append("start")

        return entities

    def _calculate_temporal_delta(
        self, event: EpisodicEvent, prev_event_time: Optional[float] = None
    ) -> float:
        """Calculate time elapsed since previous event.

        Args:
            event: Current event
            prev_event_time: Timestamp of previous event

        Returns:
            Time delta in seconds
        """
        if not hasattr(event, "timestamp") or prev_event_time is None:
            return 0.0

        event_time = event.timestamp if hasattr(event, "timestamp") else 0.0
        return max(0.0, event_time - prev_event_time)

    def _find_causal_parents(self, event: EpisodicEvent) -> List[int]:
        """Find causally-prior events.

        Args:
            event: Event to analyze

        Returns:
            List of parent event IDs
        """
        # Simplified: return empty list
        # In production, analyze causal chains from knowledge graph
        return []


class BayesianSurpriseCalculator:
    """Calculate Bayesian surprise (K-L divergence) between events.

    Surprise quantifies how much an event deviates from expectations
    based on prior event sequences.

    K-L Divergence = Σ P_prior(x) * log(P_prior(x) / P_current(x))
    """

    def __init__(self, embedding_model=None, window_size: int = 5):
        """Initialize surprise calculator.

        Args:
            embedding_model: Optional embedding model
            window_size: Number of prior events for expectation context
        """
        self.embedding_model = embedding_model
        self.window_size = window_size
        self.encoder = EventEncoder(embedding_model)

    def calculate_surprise(
        self, prior_features: List[EventFeatures], current_features: EventFeatures
    ) -> float:
        """Calculate surprise of current event given prior events.

        Args:
            prior_features: Features of prior events (context)
            current_features: Features of current event

        Returns:
            Surprise score (0.0 = expected, >3.0 = very surprising)
        """
        if not prior_features:
            return 0.0

        # Component 1: Embedding-based surprise (60% weight)
        kl_embedding = self._kl_divergence_embedding(prior_features, current_features)

        # Component 2: Entity-based surprise (25% weight)
        kl_entities = self._kl_divergence_entities(prior_features, current_features)

        # Component 3: Temporal surprise (15% weight)
        kl_temporal = self._kl_divergence_temporal(prior_features, current_features)

        # Weighted combination
        surprise = 0.60 * kl_embedding + 0.25 * kl_entities + 0.15 * kl_temporal

        return surprise

    def _kl_divergence_embedding(
        self, prior_features: List[EventFeatures], current_features: EventFeatures
    ) -> float:
        """K-L divergence based on semantic embeddings.

        Uses Gaussian approximation of embedding distributions.

        Args:
            prior_features: Prior event features
            current_features: Current event features

        Returns:
            K-L divergence score
        """
        if not prior_features:
            return 0.0

        prior_embeddings = np.array([f.embedding for f in prior_features])
        current_embedding = current_features.embedding

        # Statistics of prior distribution
        mu_prior = np.mean(prior_embeddings, axis=0)
        sigma_prior = np.std(prior_embeddings, axis=0)

        # Prevent division by zero
        sigma_prior = np.maximum(sigma_prior, 0.001)

        # Predict next embedding (exponential moving average)
        predicted_embedding = self._predict_next_embedding(prior_embeddings)

        # K-L divergence for Gaussians
        # K-L(P || Q) ≈ Σ [(x_P - x_Q)² / σ_Q²]
        kl_divergence = np.sum(
            ((current_embedding - predicted_embedding) ** 2) / (sigma_prior**2 + 1e-8)
        )

        # Normalize by embedding dimension
        kl_divergence = kl_divergence / len(current_embedding)

        return float(kl_divergence)

    def _predict_next_embedding(self, prior_embeddings: np.ndarray) -> np.ndarray:
        """Predict next embedding using exponential moving average.

        Args:
            prior_embeddings: NxD array of prior embeddings

        Returns:
            Predicted next embedding (D,)
        """
        if len(prior_embeddings) == 0:
            return np.zeros(384)

        # Exponential moving average with decay factor
        alpha = 0.3
        predicted = np.zeros_like(prior_embeddings[0])

        for i, emb in enumerate(prior_embeddings):
            weight = alpha * ((1 - alpha) ** (len(prior_embeddings) - i - 1))
            predicted = predicted + emb * weight

        # Normalize
        norm = np.linalg.norm(predicted)
        if norm > 0:
            predicted = predicted / norm

        return predicted

    def _kl_divergence_entities(
        self, prior_features: List[EventFeatures], current_features: EventFeatures
    ) -> float:
        """K-L divergence based on entity types.

        Uses Jaccard distance as proxy for K-L divergence.

        Args:
            prior_features: Prior event features
            current_features: Current event features

        Returns:
            K-L divergence approximation
        """
        # Collect all entities from prior events
        prior_entities = set()
        for feature in prior_features:
            prior_entities.update(feature.entities)

        current_entities = set(current_features.entities)

        # Jaccard similarity
        intersection = len(prior_entities & current_entities)
        union = len(prior_entities | current_entities)

        if union == 0:
            # Both have no entities - no surprise
            return 0.0

        jaccard_sim = intersection / union

        # Convert similarity to surprise (inverse relationship)
        # K-L ≈ -log(similarity)
        kl_approx = -np.log(max(jaccard_sim, 0.01))

        return kl_approx

    def _kl_divergence_temporal(
        self, prior_features: List[EventFeatures], current_features: EventFeatures
    ) -> float:
        """K-L divergence based on temporal features.

        Measures deviation from expected inter-event timing.

        Args:
            prior_features: Prior event features
            current_features: Current event features

        Returns:
            Temporal surprise score
        """
        prior_deltas = [f.temporal_delta for f in prior_features]

        if not prior_deltas:
            return 0.0

        mean_delta = np.mean(prior_deltas)
        std_delta = np.std(prior_deltas)

        if std_delta < 1e-6:
            # No variation in prior timing - can't measure surprise
            return 0.0

        # Z-score of current delta
        z_score = (current_features.temporal_delta - mean_delta) / std_delta

        # K-L approximation: absolute deviation
        kl_approx = abs(z_score)

        return kl_approx

    def calculate_surprise_sequence(
        self, events: List[EpisodicEvent], window_size: Optional[int] = None
    ) -> List[float]:
        """Calculate surprise values for entire event sequence.

        Args:
            events: Ordered list of episodic events
            window_size: Optional override for context window size

        Returns:
            List of surprise values (one per event)
        """
        window = window_size or self.window_size
        surprises = []

        # Encode all events
        features_list = []
        prev_time = None

        for event in events:
            features = self.encoder.encode(event, prev_time)
            features_list.append(features)

            if hasattr(event, "timestamp"):
                prev_time = event.timestamp

        # Calculate surprise for each event
        surprises.append(0.0)  # First event has no prior context

        for i in range(1, len(features_list)):
            # Context window: features_list[max(0, i-window):i]
            prior_start = max(0, i - window)
            prior_features = features_list[prior_start:i]
            current_features = features_list[i]

            surprise = self.calculate_surprise(prior_features, current_features)
            surprises.append(surprise)

        return surprises

    def get_surprise_stats(self, surprises: List[float]) -> Dict:
        """Calculate statistics of surprise distribution.

        Args:
            surprises: List of surprise values

        Returns:
            Dict with mean, stdev, min, max
        """
        if not surprises:
            return {"mean": 0.0, "stdev": 0.0, "min": 0.0, "max": 0.0}

        return {
            "mean": float(np.mean(surprises)),
            "stdev": float(np.std(surprises)),
            "min": float(np.min(surprises)),
            "max": float(np.max(surprises)),
            "median": float(np.median(surprises)),
        }


@dataclass
class SegmentationResult:
    """Result of event segmentation."""

    session_id: str
    segments: List[List[EpisodicEvent]]  # Grouped episodes
    surprises: List[float]  # Surprise per event
    threshold: float  # Boundary threshold
    boundaries: List[int]  # Boundary event indices
    modularity_score: float  # Community structure quality
    stats: Dict = None  # Surprise statistics
    created_at: datetime = None

    def __post_init__(self):
        """Initialize default values."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.stats is None:
            self.stats = {}


class EventSegmenter:
    """Segment events into coherent episodes using Bayesian surprise.

    Detects event boundaries where surprise exceeds adaptive threshold.
    Refines boundaries using graph-theoretic modularity optimization.
    """

    def __init__(
        self,
        surprise_calculator: BayesianSurpriseCalculator,
        min_event_size: int = 8,
        max_event_size: int = 128,
    ):
        """Initialize event segmenter.

        Args:
            surprise_calculator: Surprise metric calculator
            min_event_size: Minimum tokens per segment
            max_event_size: Maximum tokens per segment
        """
        self.surprise_calculator = surprise_calculator
        self.min_event_size = min_event_size
        self.max_event_size = max_event_size

    def segment_events(
        self, events: List[EpisodicEvent], adaptive_gamma: float = 1.0, session_id: str = "unknown"
    ) -> SegmentationResult:
        """Segment events into episodes using Bayesian surprise.

        Args:
            events: Ordered list of episodic events
            adaptive_gamma: Threshold multiplier (1.0 = mean + 1*std)
            session_id: Session identifier

        Returns:
            SegmentationResult with segments, boundaries, metrics
        """
        if len(events) < 2:
            return SegmentationResult(
                session_id=session_id,
                segments=[events],
                surprises=[0.0] * len(events),
                threshold=0.0,
                boundaries=[0, len(events) - 1],
                modularity_score=1.0,
                stats={"num_events": len(events)},
            )

        # Stage 1: Calculate surprise for each event
        surprises = self.surprise_calculator.calculate_surprise_sequence(events)

        # Stage 2: Calculate adaptive threshold
        threshold = self._calculate_adaptive_threshold(surprises, gamma=adaptive_gamma)

        # Stage 3: Detect boundaries based on threshold
        boundaries = self._detect_boundaries(surprises, threshold)

        # Stage 4: Refine boundaries with modularity optimization
        boundaries = self._refine_with_modularity(events, surprises, boundaries)

        # Stage 5: Create segments and enforce size constraints
        segments = self._create_segments(events, boundaries)
        segments = self._enforce_size_constraints(segments)

        # Calculate modularity score
        modularity = self._calculate_modularity(events, surprises, boundaries)

        # Gather statistics
        stats = self.surprise_calculator.get_surprise_stats(surprises)
        stats["num_segments"] = len(segments)
        stats["threshold"] = threshold
        stats["adaptive_gamma"] = adaptive_gamma

        return SegmentationResult(
            session_id=session_id,
            segments=segments,
            surprises=surprises,
            threshold=threshold,
            boundaries=boundaries,
            modularity_score=modularity,
            stats=stats,
        )

    def _calculate_adaptive_threshold(self, surprises: List[float], gamma: float = 1.0) -> float:
        """Calculate adaptive threshold: mean + gamma * stdev.

        Args:
            surprises: Surprise values for all events
            gamma: Threshold multiplier

        Returns:
            Adaptive threshold
        """
        mean_surprise = np.mean(surprises)
        std_surprise = np.std(surprises)

        threshold = mean_surprise + gamma * std_surprise

        return float(threshold)

    def _detect_boundaries(self, surprises: List[float], threshold: float) -> List[int]:
        """Detect event boundaries where surprise exceeds threshold.

        Args:
            surprises: Surprise values
            threshold: Boundary threshold

        Returns:
            List of boundary indices
        """
        boundaries = [0]  # Always start with event 0

        for i in range(1, len(surprises)):
            if surprises[i] > threshold:
                boundaries.append(i)

        # Always include last event
        if boundaries[-1] != len(surprises) - 1:
            boundaries.append(len(surprises) - 1)

        return boundaries

    def _refine_with_modularity(
        self, events: List[EpisodicEvent], surprises: List[float], boundaries: List[int]
    ) -> List[int]:
        """Refine boundaries using graph-theoretic modularity.

        Args:
            events: List of events
            surprises: Surprise values
            boundaries: Initial boundaries

        Returns:
            Refined boundaries
        """
        # Build edge list with similarity weights
        edges = []
        for i in range(len(events) - 1):
            # Similarity is inverse of surprise (low surprise = high similarity)
            similarity = 1.0 / (1.0 + surprises[i + 1])
            edges.append((i, i + 1, similarity))

        # Run greedy modularity optimization
        communities = self._greedy_modularity_optimization(edges, len(events))

        # Extract boundaries from community structure
        refined_boundaries = [0]
        for i in range(1, len(communities)):
            if communities[i] != communities[i - 1]:
                refined_boundaries.append(i)

        if refined_boundaries[-1] != len(events) - 1:
            refined_boundaries.append(len(events) - 1)

        return refined_boundaries

    def _greedy_modularity_optimization(self, edges: List[Tuple], num_nodes: int) -> List[int]:
        """Simple greedy modularity optimization (Louvain approximation).

        Args:
            edges: List of (node_i, node_j, weight) edges
            num_nodes: Number of nodes

        Returns:
            Community assignment for each node
        """
        # Initialize: each node is its own community
        communities = list(range(num_nodes))

        # Greedy merging iterations
        improved = True
        iterations = 0
        max_iterations = 10

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            current_modularity = self._calculate_modularity_score(communities, edges)

            # Try merging adjacent communities
            for i in range(num_nodes - 1):
                if communities[i] != communities[i + 1]:
                    # Merge communities[i+1] into communities[i]
                    old_comm = communities[i + 1]
                    new_comm = communities[i]
                    communities[i + 1] = new_comm

                    new_modularity = self._calculate_modularity_score(communities, edges)

                    if new_modularity > current_modularity * 1.001:  # Small improvement threshold
                        current_modularity = new_modularity
                        improved = True
                    else:
                        # Revert
                        communities[i + 1] = old_comm

        return communities

    def _calculate_modularity_score(self, communities: List[int], edges: List[Tuple]) -> float:
        """Calculate modularity Q for community assignment.

        Args:
            communities: Community assignment per node
            edges: Edge list with weights

        Returns:
            Modularity score (0-1)
        """
        if len(set(communities)) == 0:
            return 0.0

        # Sum edges within communities
        internal_weight = sum(weight for u, v, weight in edges if communities[u] == communities[v])

        # Total weight
        total_weight = sum(weight for _, _, weight in edges)

        if total_weight == 0:
            return 0.0

        return internal_weight / total_weight

    def _calculate_modularity(
        self, events: List[EpisodicEvent], surprises: List[float], boundaries: List[int]
    ) -> float:
        """Calculate modularity of final segmentation.

        Args:
            events: List of events
            surprises: Surprise values
            boundaries: Final boundaries

        Returns:
            Modularity score
        """
        # Similar to modularity score but for final segments
        if len(boundaries) <= 1:
            return 0.0

        # Internal similarity (low surprise within segments)
        internal_surprises = []
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            segment_surprises = surprises[start:end]
            if segment_surprises:
                internal_surprises.extend(segment_surprises)

        # External surprise (high surprise at boundaries)
        boundary_surprises = [surprises[b] for b in boundaries[1:-1]]

        if not boundary_surprises:
            return 1.0

        # Modularity = (low internal) / (high boundary)
        mean_internal = np.mean(internal_surprises) if internal_surprises else 0.0
        mean_boundary = np.mean(boundary_surprises)

        if mean_boundary > 0:
            modularity = mean_internal / mean_boundary
        else:
            modularity = 0.0

        return min(1.0, modularity)  # Clamp to [0, 1]

    def _create_segments(
        self, events: List[EpisodicEvent], boundaries: List[int]
    ) -> List[List[EpisodicEvent]]:
        """Create event segments from boundaries.

        Args:
            events: List of events
            boundaries: Boundary indices

        Returns:
            List of event segments
        """
        segments = []

        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1] + 1
            segment = events[start:end]
            if segment:
                segments.append(segment)

        return segments

    def _enforce_size_constraints(
        self,
        segments: List[List[EpisodicEvent]],
    ) -> List[List[EpisodicEvent]]:
        """Enforce min/max size constraints.

        Args:
            segments: Event segments

        Returns:
            Segments with size constraints applied
        """
        result = []

        for segment in segments:
            token_count = sum(len(e.content.split()) for e in segment if hasattr(e, "content"))

            if token_count < self.min_event_size:
                # Merge with previous segment
                if result:
                    result[-1].extend(segment)
                else:
                    result.append(segment)
            elif token_count > self.max_event_size:
                # Split large segment
                splits = self._split_segment(segment)
                result.extend(splits)
            else:
                result.append(segment)

        return result

    def _split_segment(self, segment: List[EpisodicEvent]) -> List[List[EpisodicEvent]]:
        """Split oversized segment.

        Args:
            segment: Event segment to split

        Returns:
            List of smaller segments
        """
        if len(segment) <= 1:
            return [segment]

        # Split at midpoint
        mid = len(segment) // 2
        return [segment[:mid], segment[mid:]]
