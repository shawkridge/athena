"""Unified temporal inference engine for event linking and causal reasoning.

Consolidates temporal reasoning logic across all memory layers.
Provides:
- Temporal relation classification (immediately_after, shortly_after, later_after)
- Causal strength calculation (4-factor scoring)
- Event chain creation
- Causal pattern detection
"""

from datetime import datetime
from typing import List, Tuple

# Type stubs - import at runtime to avoid circular dependencies
# These will be injected via factory methods


class TemporalInferenceEngine:
    """Unified temporal reasoning for event sequences."""

    # Time window constants
    IMMEDIATELY_AFTER_SECONDS = 60
    SHORTLY_AFTER_SECONDS = 3600
    SAME_SESSION_TIMEOUT = 3600
    CAUSAL_LOOKAHEAD_SECONDS = 3600

    @staticmethod
    def classify_temporal_relation(time_gap_seconds: float) -> Tuple[str, float]:
        """Classify temporal relation based on time gap.

        Args:
            time_gap_seconds: Time difference in seconds

        Returns:
            Tuple of (relation_type, base_strength)
            - immediately_after: <60s, strength 0.9
            - shortly_after: 60s-3600s, strength 0.7
            - later_after: >3600s, strength 0.3-0.9 (decaying)
        """
        if time_gap_seconds < TemporalInferenceEngine.IMMEDIATELY_AFTER_SECONDS:
            return "immediately_after", 0.9
        elif time_gap_seconds < TemporalInferenceEngine.SHORTLY_AFTER_SECONDS:
            return "shortly_after", 0.7
        else:
            # Decay over 1 day
            decay_factor = max(0.0, 1.0 - (time_gap_seconds / 86400))
            strength = max(0.3, 0.9 * decay_factor)
            return "later_after", strength

    @staticmethod
    def calculate_causal_strength(
        cause_event, effect_event  # EpisodicEvent  # EpisodicEvent
    ) -> float:
        """Calculate causal strength between two events.

        Uses 4-factor scoring:
        - Time proximity (base 0.5, up to +0.2)
        - File overlap (up to +0.2)
        - Session continuity (up to +0.1)
        - Event type compatibility (already handled by is_likely_causal)

        Args:
            cause_event: Potential cause event
            effect_event: Potential effect event

        Returns:
            Strength score [0.0, 1.0]
        """
        strength = 0.5  # Base strength

        # Factor 1: Time proximity (up to +0.2)
        time_gap = (effect_event.timestamp - cause_event.timestamp).total_seconds()
        if time_gap < 60:
            strength += 0.2
        elif time_gap < 300:
            strength += 0.1

        # Factor 2: File overlap (up to +0.2)
        if cause_event.context and effect_event.context:
            files1 = set(cause_event.context.files or [])
            files2 = set(effect_event.context.files or [])

            if files1 and files2:
                overlap = len(files1 & files2)
                union = len(files1 | files2)
                if union > 0:
                    strength += 0.2 * (overlap / union)

        # Factor 3: Session continuity (up to +0.1)
        if cause_event.session_id == effect_event.session_id:
            strength += 0.1

        # Factor 4: Semantic compatibility (would use embeddings)
        # - Currently handled in event type matching

        return min(strength, 1.0)

    @staticmethod
    def is_likely_causal(event1, event2) -> bool:  # EpisodicEvent  # EpisodicEvent
        """Determine if event1 likely caused event2.

        Uses heuristics based on event types:
        - Error → Fix/Success: High probability
        - Test Failure → Code Change → Test Pass: TDD pattern
        - Decision → Action: Causal pattern
        - Debug → Fix: Debugging pattern

        Args:
            event1: First event (potential cause)
            event2: Second event (potential effect)

        Returns:
            True if likely causal relationship
        """
        # Get event type as string
        type1 = (
            event1.event_type.value
            if hasattr(event1.event_type, "value")
            else str(event1.event_type)
        )
        type2 = (
            event2.event_type.value
            if hasattr(event2.event_type, "value")
            else str(event2.event_type)
        )

        # Pattern 1: Error followed by fix/success
        if type1 == "error" and type2 in ["file_change", "success"]:
            if event1.context and event2.context:
                files1 = set(event1.context.files or [])
                files2 = set(event2.context.files or [])
                return bool(files1 & files2)  # File overlap required
            return True

        # Pattern 2: Code change followed by test success
        if type1 == "file_change" and type2 == "test_run":
            if event1.context and event2.context:
                files1 = set(event1.context.files or [])
                files2 = set(event2.context.files or [])
                return bool(files1 & files2)  # File overlap required
            return True

        # Pattern 3: Decision followed by action
        if type1 == "decision" and type2 == "action":
            return True

        # Pattern 4: Debugging followed by fix
        if type1 == "debugging" and type2 in ["file_change", "success"]:
            return True

        # Pattern 5: Test failure followed by investigation
        if type1 == "test_run" and type2 in ["debugging", "file_change"]:
            return True

        return False

    @staticmethod
    def link_events(events: List) -> List:
        """Link events into temporal relations.

        Creates temporal relations between consecutive events based on:
        - Time proximity
        - Session continuity
        - Causal heuristics

        Args:
            events: List of EpisodicEvent objects (will be sorted)

        Returns:
            List of TemporalRelation objects
        """
        if len(events) < 2:
            return []

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        relations = []

        for i in range(len(sorted_events) - 1):
            current = sorted_events[i]
            next_event = sorted_events[i + 1]

            # Calculate time gap
            time_gap_seconds = (next_event.timestamp - current.timestamp).total_seconds()

            # Determine relation type and strength based on time gap
            relation_type, strength = TemporalInferenceEngine.classify_temporal_relation(
                time_gap_seconds
            )

            # Import TemporalRelation here to avoid circular import
            from ..temporal.models import TemporalRelation

            relation = TemporalRelation(
                from_event_id=current.id,
                to_event_id=next_event.id,
                relation_type=relation_type,
                strength=strength,
                inferred_at=datetime.now(),
            )

            relations.append(relation)

        return relations

    @staticmethod
    def infer_causal_relations(events: List) -> List:
        """Infer causal relations between events.

        Only considers events within same session and <1 hour apart.

        Args:
            events: List of EpisodicEvent objects (will be sorted)

        Returns:
            List of TemporalRelation objects with relation_type='caused'
        """
        if len(events) < 2:
            return []

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        causal_relations = []

        for i in range(len(sorted_events) - 1):
            current = sorted_events[i]
            next_event = sorted_events[i + 1]

            # Only infer causality within same session
            if current.session_id != next_event.session_id:
                continue

            # Check if events are temporally close
            time_gap = (next_event.timestamp - current.timestamp).total_seconds()
            if time_gap > TemporalInferenceEngine.CAUSAL_LOOKAHEAD_SECONDS:
                continue

            # Apply causal heuristics
            if TemporalInferenceEngine.is_likely_causal(current, next_event):
                strength = TemporalInferenceEngine.calculate_causal_strength(current, next_event)

                # Import TemporalRelation here to avoid circular import
                from ..temporal.models import TemporalRelation

                causal_relation = TemporalRelation(
                    from_event_id=current.id,
                    to_event_id=next_event.id,
                    relation_type="caused",
                    strength=strength,
                    inferred_at=datetime.now(),
                )

                causal_relations.append(causal_relation)

        return causal_relations
