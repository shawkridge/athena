"""Event prioritization for consolidation pipeline.

Implements multi-dimensional event scoring to select high-value events for
consolidation using:
- Surprise (entropy-based deviation from expected patterns)
- Utility (actionability + importance)
- Relevance (recency of usage + activation frequency)
"""

import logging
import math
from typing import Dict, List, Tuple, Any
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class EventPrioritizer:
    """Score episodic events for consolidation priority.

    Prioritizes events that are:
    1. Surprising: Unexpected given recent pattern
    2. Useful: Actionable and important
    3. Relevant: Recently accessed and frequently used
    """

    def __init__(self):
        """Initialize prioritizer with weighting scheme."""
        # Weights for multi-dimensional scoring
        self.surprise_weight = 0.35  # How unexpected is the event?
        self.utility_weight = 0.35  # How actionable/important?
        self.relevance_weight = 0.30  # How recently/frequently used?

    def score_events(
        self,
        events: List[Dict[str, Any]],
        recent_pattern_events: List[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float]]:
        """Score events for consolidation priority.

        Args:
            events: List of episodic events to score
            recent_pattern_events: Optional recent events to establish baseline

        Returns:
            List of (event_id, priority_score) tuples, sorted by priority DESC
        """
        if not events:
            return []

        scores = []

        for event in events:
            try:
                # Calculate individual dimensions
                surprise_score = self._calculate_surprise(event, recent_pattern_events or events)
                utility_score = self._calculate_utility(event)
                relevance_score = self._calculate_relevance(event)

                # Combine into composite priority score
                composite_score = (
                    surprise_score * self.surprise_weight
                    + utility_score * self.utility_weight
                    + relevance_score * self.relevance_weight
                )

                event_id = str(event.get("id", "unknown"))
                scores.append((event_id, composite_score))

            except Exception as e:
                logger.warning(f"Error scoring event: {e}")
                # Default to zero priority if scoring fails
                event_id = str(event.get("id", "unknown"))
                scores.append((event_id, 0.0))

        # Sort by score DESC (highest priority first)
        return sorted(scores, key=lambda x: x[1], reverse=True)

    def _calculate_surprise(
        self,
        event: Dict[str, Any],
        baseline_events: List[Dict[str, Any]],
    ) -> float:
        """Calculate surprise score (0-1, higher = more surprising).

        Surprise measures how unexpected an event is:
        - High surprise: Outcome different from expected (success vs failure)
        - High surprise: Event type not common in baseline
        - Low surprise: Matches expected pattern

        Args:
            event: Event to score
            baseline_events: Events establishing baseline expectation

        Returns:
            Surprise score (0.0-1.0)
        """
        # Get event properties
        event_type = event.get("event_type", "unknown")
        outcome = event.get("outcome", "unknown")

        # Baseline analysis
        if not baseline_events:
            return 0.5  # No baseline, moderate surprise

        baseline_outcomes = {}
        baseline_types = {}

        for evt in baseline_events:
            etype = evt.get("event_type", "unknown")
            outcome_val = evt.get("outcome", "unknown")

            # Count outcome frequencies
            baseline_outcomes[outcome_val] = baseline_outcomes.get(outcome_val, 0) + 1

            # Count event type frequencies
            baseline_types[etype] = baseline_types.get(etype, 0) + 1

        total_events = len(baseline_events)

        # Calculate entropy of expected outcomes
        outcome_probs = [count / total_events for count in baseline_outcomes.values()]
        expected_entropy = -sum(p * math.log(p) for p in outcome_probs if p > 0)

        # Inverse outcome frequency (rare outcomes = surprising)
        outcome_freq = baseline_outcomes.get(outcome, 1) / total_events
        outcome_surprise = 1.0 - min(outcome_freq, 1.0)

        # Event type surprise (rare event types = surprising)
        type_freq = baseline_types.get(event_type, 1) / total_events
        type_surprise = 1.0 - min(type_freq, 1.0)

        # Combine: 50% outcome surprise, 50% type surprise
        combined_surprise = outcome_surprise * 0.5 + type_surprise * 0.5

        return min(combined_surprise, 1.0)

    def _calculate_utility(self, event: Dict[str, Any]) -> float:
        """Calculate utility score (0-1, higher = more useful).

        Utility measures how actionable and important an event is:
        - High utility: Important AND actionable
        - High utility: Has clear next steps
        - Low utility: Blocked or not actionable

        Args:
            event: Event to score

        Returns:
            Utility score (0.0-1.0)
        """
        # Get utility-relevant fields
        importance = float(event.get("importance_score", 0.5))  # 0-1
        actionability = float(event.get("actionability_score", 0.5))  # 0-1
        completeness = float(event.get("context_completeness_score", 0.5))  # 0-1

        # Flags
        has_next_step = bool(event.get("has_next_step", False))
        has_blocker = bool(event.get("has_blocker", False))

        # Core utility from importance + actionability
        core_utility = importance * 0.5 + actionability * 0.5

        # Boost for clear next steps
        if has_next_step:
            core_utility = min(core_utility * 1.2, 1.0)

        # Penalty for blockers
        if has_blocker:
            core_utility = core_utility * 0.7

        # Weight by context completeness
        final_utility = core_utility * completeness

        return min(final_utility, 1.0)

    def _calculate_relevance(self, event: Dict[str, Any]) -> float:
        """Calculate relevance score (0-1, higher = more recently/frequently used).

        Relevance measures how important this event is for current work:
        - High relevance: Frequently accessed (high activation_count)
        - High relevance: Recently accessed (low time since last_activation)
        - Low relevance: Never/rarely accessed

        Args:
            event: Event to score

        Returns:
            Relevance score (0.0-1.0)
        """
        # Get relevance fields
        activation_count = int(event.get("activation_count", 0))
        last_activation = event.get("last_activation")
        created_at = event.get("timestamp")

        # Activation frequency score (decay: max out at 10 activations)
        frequency_score = min(activation_count / 10.0, 1.0)

        # Recency score (exponential decay, half-life = 7 days)
        if last_activation:
            try:
                if isinstance(last_activation, str):
                    # Parse ISO format timestamp
                    last_act_dt = datetime.fromisoformat(last_activation.replace("Z", "+00:00"))
                else:
                    last_act_dt = datetime.fromtimestamp(last_activation)

                hours_since_activation = (datetime.now() - last_act_dt).total_seconds() / 3600
                # Exponential decay: e^(-t / half_life)
                recency_score = math.exp(-hours_since_activation / (7 * 24))  # 7 day half-life
            except (ValueError, TypeError):
                recency_score = 0.5  # Default if parsing fails
        else:
            recency_score = 0.5  # No activation data = moderate relevance

        # Combine: 60% frequency, 40% recency
        combined_relevance = frequency_score * 0.6 + recency_score * 0.4

        return min(combined_relevance, 1.0)

    def filter_by_priority(
        self,
        events: List[Dict[str, Any]],
        min_score: float = 0.3,
        max_events: int = None,
    ) -> List[Dict[str, Any]]:
        """Filter events by priority score.

        Args:
            events: Events to filter
            min_score: Minimum priority score threshold (0-1)
            max_events: Maximum events to return (keep top-N)

        Returns:
            Filtered list of events, sorted by priority DESC
        """
        # Score all events
        scored = self.score_events(events)

        # Filter by minimum score
        filtered = [
            event
            for event in events
            if next((score for eid, score in scored if str(event.get("id")) == eid), 0) >= min_score
        ]

        # Sort by priority
        filtered_with_scores = [
            (event, next((score for eid, score in scored if str(event.get("id")) == eid), 0))
            for event in filtered
        ]
        filtered_with_scores.sort(key=lambda x: x[1], reverse=True)

        # Limit to max_events if specified
        if max_events:
            filtered_with_scores = filtered_with_scores[:max_events]

        return [event for event, _ in filtered_with_scores]

    def get_priority_report(
        self,
        events: List[Dict[str, Any]],
        top_n: int = 10,
    ) -> Dict[str, Any]:
        """Generate a priority report for events.

        Args:
            events: Events to analyze
            top_n: Number of top events to include in report

        Returns:
            Report dict with statistics and rankings
        """
        if not events:
            return {"total_events": 0, "top_events": []}

        scored = self.score_events(events)
        scores_only = [score for _, score in scored]

        # Build top-N list with details
        top_events = []
        for i, (event_id, score) in enumerate(scored[:top_n]):
            event = next((e for e in events if str(e.get("id")) == event_id), None)
            if event:
                top_events.append(
                    {
                        "rank": i + 1,
                        "event_id": event_id,
                        "priority_score": round(score, 3),
                        "event_type": event.get("event_type"),
                        "outcome": event.get("outcome"),
                        "importance": event.get("importance_score"),
                        "actionability": event.get("actionability_score"),
                    }
                )

        return {
            "total_events": len(events),
            "mean_priority": round(np.mean(scores_only), 3) if scores_only else 0,
            "std_priority": round(float(np.std(scores_only)), 3) if scores_only else 0,
            "min_priority": round(min(scores_only), 3) if scores_only else 0,
            "max_priority": round(max(scores_only), 3) if scores_only else 0,
            "top_events": top_events,
        }
