"""Temporal chain creation and causal inference.

Automatically links events in temporal and causal sequences.
"""

from datetime import datetime
from typing import List, Optional

from ..episodic.models import EpisodicEvent
from .models import CausalPattern, EventChain, TemporalRelation


def create_temporal_chains(
    events: List[EpisodicEvent], same_session_only: bool = False
) -> List[EventChain]:
    """
    Create temporal chains from event sequences.

    Groups events into chains based on temporal proximity and session continuity.

    Args:
        events: List of episodic events to chain
        same_session_only: Only chain events from same session

    Returns:
        List of event chains
    """
    if not events:
        return []

    # Sort by timestamp
    sorted_events = sorted(events, key=lambda e: e.timestamp)

    chains = []
    current_chain = [sorted_events[0]]

    for i in range(1, len(sorted_events)):
        prev_event = sorted_events[i - 1]
        curr_event = sorted_events[i]

        # Check if should continue chain
        time_gap_seconds = (curr_event.timestamp - prev_event.timestamp).total_seconds()
        session_matches = prev_event.session_id == curr_event.session_id

        # Chain continues if:
        # - Within 1 hour AND (same session OR not restricted to session)
        should_continue = time_gap_seconds < 3600 and (session_matches or not same_session_only)

        if should_continue:
            current_chain.append(curr_event)
        else:
            # Finalize current chain and start new one
            if len(current_chain) >= 2:
                chains.append(
                    EventChain(
                        events=current_chain,
                        chain_type="temporal",
                        start_time=current_chain[0].timestamp,
                        end_time=current_chain[-1].timestamp,
                        session_id=current_chain[0].session_id,
                    )
                )

            current_chain = [curr_event]

    # Add final chain
    if len(current_chain) >= 2:
        chains.append(
            EventChain(
                events=current_chain,
                chain_type="temporal",
                start_time=current_chain[0].timestamp,
                end_time=current_chain[-1].timestamp,
                session_id=current_chain[0].session_id,
            )
        )

    return chains


def create_temporal_relations(events: List[EpisodicEvent]) -> List[TemporalRelation]:
    """
    Create temporal relations between consecutive events.

    Args:
        events: List of events (will be sorted by timestamp)

    Returns:
        List of temporal relations
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
        if time_gap_seconds < 60:
            relation_type = "immediately_after"
            strength = 0.9
        elif time_gap_seconds < 3600:
            relation_type = "shortly_after"
            strength = 0.7
        else:
            relation_type = "later_after"
            strength = max(0.3, 0.9 - (time_gap_seconds / 86400))  # Decay over 1 day

        relation = TemporalRelation(
            from_event_id=current.id,
            to_event_id=next_event.id,
            relation_type=relation_type,
            strength=strength,
            inferred_at=datetime.now(),
        )

        relations.append(relation)

    return relations


def infer_causal_relations(events: List[EpisodicEvent]) -> List[TemporalRelation]:
    """
    Infer causal relations between events using heuristics.

    Detects patterns like:
    - Error → Fix
    - Test failure → Code change → Test pass
    - Decision → Action

    Args:
        events: List of events (will be sorted by timestamp)

    Returns:
        List of causal relations
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

        # Check if events are temporally close (< 1 hour)
        time_gap = (next_event.timestamp - current.timestamp).total_seconds()
        if time_gap > 3600:
            continue

        # Apply causal heuristics
        if is_likely_causal(current, next_event):
            strength = calculate_causal_strength(current, next_event)

            causal_relation = TemporalRelation(
                from_event_id=current.id,
                to_event_id=next_event.id,
                relation_type="caused",
                strength=strength,
                inferred_at=datetime.now(),
            )

            causal_relations.append(causal_relation)

    return causal_relations


def is_likely_causal(event1: EpisodicEvent, event2: EpisodicEvent) -> bool:
    """
    Determine if event1 likely caused event2.

    Uses simple heuristics based on event types and context.

    Args:
        event1: First event (potential cause)
        event2: Second event (potential effect)

    Returns:
        True if likely causal relationship
    """
    # Helper to get event type as string
    type1 = (
        event1.event_type.value if hasattr(event1.event_type, "value") else str(event1.event_type)
    )
    type2 = (
        event2.event_type.value if hasattr(event2.event_type, "value") else str(event2.event_type)
    )

    # Pattern 1: Error followed by fix/success
    if type1 == "error" and type2 in ["file_change", "success"]:
        # Check file overlap
        if event1.context and event2.context:
            files1 = set(event1.context.files or [])
            files2 = set(event2.context.files or [])
            if files1 & files2:  # Shared files
                return True

    # Pattern 2: Test failure followed by code change
    if event1.outcome == "failure" and type2 == "file_change":
        return True

    # Pattern 3: Code change followed by test pass
    if type1 == "file_change" and type2 == "test_run":
        if event2.outcome == "success":
            return True

    # Pattern 4: Decision followed by action
    if type1 == "decision" and type2 == "action":
        return True

    # Pattern 5: Debugging followed by success
    if type1 == "debugging" and event2.outcome == "success":
        return True

    return False


def calculate_causal_strength(event1: EpisodicEvent, event2: EpisodicEvent) -> float:
    """
    Calculate strength of causal relationship.

    Considers:
    - Time proximity (closer = stronger)
    - File overlap
    - Session continuity
    - Event type compatibility

    Args:
        event1: First event (cause)
        event2: Second event (effect)

    Returns:
        Strength score [0.0, 1.0]
    """
    strength = 0.5  # Base strength

    # Time proximity bonus (up to +0.2)
    time_gap = (event2.timestamp - event1.timestamp).total_seconds()
    if time_gap < 60:
        strength += 0.2
    elif time_gap < 300:
        strength += 0.1

    # File overlap bonus (up to +0.2)
    if event1.context and event2.context:
        files1 = set(event1.context.files or [])
        files2 = set(event2.context.files or [])

        if files1 and files2:
            overlap = len(files1 & files2)
            union = len(files1 | files2)
            strength += 0.2 * (overlap / union)

    # Same session bonus (+0.1)
    if event1.session_id == event2.session_id:
        strength += 0.1

    return min(strength, 1.0)


def detect_causal_patterns(events: List[EpisodicEvent]) -> List[CausalPattern]:
    """
    Detect common causal patterns in event sequences.

    Patterns:
    - TDD cycle: test → code → test pass
    - Error recovery: error → fix → success
    - Debug session: multiple errors → debugging → fix → success
    - Refactor: multiple file changes in same area

    Args:
        events: List of events to analyze

    Returns:
        List of detected causal patterns
    """
    if len(events) < 3:
        return []

    sorted_events = sorted(events, key=lambda e: e.timestamp)
    patterns = []

    # Sliding window to detect patterns
    for i in range(len(sorted_events) - 2):
        window = sorted_events[i : i + 4]  # Look at 3-4 events

        # TDD pattern: test failure → code change → test pass
        if len(window) >= 3:
            tdd_pattern = _detect_tdd_pattern(window[:3])
            if tdd_pattern:
                patterns.append(tdd_pattern)

        # Error recovery: error → file change → success
        if len(window) >= 3:
            error_fix = _detect_error_fix_pattern(window[:3])
            if error_fix:
                patterns.append(error_fix)

        # Debug session: multiple errors/debugging → fix
        if len(window) >= 4:
            debug_session = _detect_debug_session(window)
            if debug_session:
                patterns.append(debug_session)

    return patterns


def _detect_tdd_pattern(events: List[EpisodicEvent]) -> Optional[CausalPattern]:
    """Detect test-driven development pattern."""
    if len(events) < 3:
        return None

    e1, e2, e3 = events[0], events[1], events[2]

    type1 = e1.event_type.value if hasattr(e1.event_type, "value") else str(e1.event_type)
    type2 = e2.event_type.value if hasattr(e2.event_type, "value") else str(e2.event_type)
    type3 = e3.event_type.value if hasattr(e3.event_type, "value") else str(e3.event_type)

    # Test failure → Code change → Test pass
    if (
        type1 == "test_run"
        and e1.outcome == "failure"
        and type2 == "file_change"
        and type3 == "test_run"
        and e3.outcome == "success"
    ):

        return CausalPattern(
            pattern_type="tdd_cycle",
            events=events,
            confidence=0.85,
            description="Test-driven development: test → code → test pass",
        )

    return None


def _detect_error_fix_pattern(events: List[EpisodicEvent]) -> Optional[CausalPattern]:
    """Detect error recovery pattern."""
    if len(events) < 3:
        return None

    e1, e2, e3 = events[0], events[1], events[2]

    type1 = e1.event_type.value if hasattr(e1.event_type, "value") else str(e1.event_type)
    type2 = e2.event_type.value if hasattr(e2.event_type, "value") else str(e2.event_type)

    # Error → File change → Success
    if type1 == "error" and type2 == "file_change" and e3.outcome == "success":

        return CausalPattern(
            pattern_type="error_fix",
            events=events,
            confidence=0.75,
            description="Error recovery: error → fix → success",
        )

    return None


def _detect_debug_session(events: List[EpisodicEvent]) -> Optional[CausalPattern]:
    """Detect debugging session pattern."""
    if len(events) < 4:
        return None

    # Check for multiple errors/debugging events followed by success
    error_count = sum(
        1
        for e in events[:-1]
        if (e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type))
        in ["error", "debugging"]
    )

    if error_count >= 2 and events[-1].outcome == "success":
        return CausalPattern(
            pattern_type="debug_session",
            events=events,
            confidence=0.7,
            description=f"Debug session: {error_count} errors resolved",
        )

    return None
