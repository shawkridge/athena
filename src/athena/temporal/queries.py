"""Temporal query patterns for event sequence matching."""

from datetime import datetime, timedelta
from typing import List

from ..episodic.models import EpisodicEvent
from ..episodic.store import EpisodicStore
from .models import EventSequence, TemporalQuery, TemporalRelation


def query_by_temporal_pattern(
    query: TemporalQuery, episodic_store: EpisodicStore
) -> List[EventSequence]:
    """
    Find event sequences matching temporal patterns.

    Supported patterns:
    - "error then fix" → ERROR → FILE_CHANGE → SUCCESS
    - "tdd cycle" → TEST_FAILURE → FILE_CHANGE → TEST_PASS
    - "debug session" → ERROR* → DEBUGGING → SUCCESS
    - "refactor" → FILE_CHANGE+

    Args:
        query: Temporal query with pattern and parameters
        episodic_store: Store to query events from

    Returns:
        List of matching event sequences
    """
    # Get events from lookback period
    start_date = datetime.now() - timedelta(days=query.lookback_days)
    all_events = episodic_store.get_events_by_date(
        project_id=query.project_id, start_date=start_date, end_date=datetime.now()
    )

    if not all_events:
        return []

    # Sort by timestamp
    sorted_events = sorted(all_events, key=lambda e: e.timestamp)

    # Parse pattern and find matches
    pattern_matcher = _get_pattern_matcher(query.pattern)
    sequences = pattern_matcher(sorted_events, query.min_confidence)

    return sequences


def _get_pattern_matcher(pattern: str):
    """Get appropriate pattern matcher function."""
    pattern_lower = pattern.lower()

    if "error" in pattern_lower and "fix" in pattern_lower:
        return _match_error_fix_pattern

    elif "tdd" in pattern_lower or ("test" in pattern_lower and "code" in pattern_lower):
        return _match_tdd_pattern

    elif "debug" in pattern_lower:
        return _match_debug_pattern

    elif "refactor" in pattern_lower:
        return _match_refactor_pattern

    else:
        # Generic sequential matcher
        return _match_generic_pattern


def _match_error_fix_pattern(
    events: List[EpisodicEvent], min_confidence: float
) -> List[EventSequence]:
    """Match ERROR → FILE_CHANGE → SUCCESS pattern."""
    sequences = []

    for i in range(len(events) - 2):
        e1, e2, e3 = events[i], events[i + 1], events[i + 2]

        type1 = _get_event_type_str(e1)
        type2 = _get_event_type_str(e2)

        # Check pattern match
        if type1 == "error" and type2 == "file_change" and e3.outcome == "success":

            # Calculate confidence
            time_span = (e3.timestamp - e1.timestamp).total_seconds()
            confidence = _calculate_sequence_confidence([e1, e2, e3], time_span, file_overlap=True)

            if confidence >= min_confidence:
                # Create temporal relations
                relations = [
                    TemporalRelation(e1.id, e2.id, "immediately_after", 0.8, datetime.now()),
                    TemporalRelation(e2.id, e3.id, "caused", confidence, datetime.now()),
                ]

                sequences.append(
                    EventSequence(
                        events=[e1, e2, e3],
                        pattern="error_fix",
                        match_confidence=confidence,
                        temporal_relations=relations,
                    )
                )

    return sequences


def _match_tdd_pattern(events: List[EpisodicEvent], min_confidence: float) -> List[EventSequence]:
    """Match TEST_FAILURE → FILE_CHANGE → TEST_PASS pattern."""
    sequences = []

    for i in range(len(events) - 2):
        e1, e2, e3 = events[i], events[i + 1], events[i + 2]

        type1 = _get_event_type_str(e1)
        type2 = _get_event_type_str(e2)
        type3 = _get_event_type_str(e3)

        # Check TDD pattern
        if (
            type1 == "test_run"
            and e1.outcome == "failure"
            and type2 == "file_change"
            and type3 == "test_run"
            and e3.outcome == "success"
        ):

            time_span = (e3.timestamp - e1.timestamp).total_seconds()
            confidence = _calculate_sequence_confidence([e1, e2, e3], time_span, file_overlap=True)

            if confidence >= min_confidence:
                relations = [
                    TemporalRelation(e1.id, e2.id, "caused", 0.9, datetime.now()),
                    TemporalRelation(e2.id, e3.id, "caused", 0.9, datetime.now()),
                ]

                sequences.append(
                    EventSequence(
                        events=[e1, e2, e3],
                        pattern="tdd_cycle",
                        match_confidence=confidence,
                        temporal_relations=relations,
                    )
                )

    return sequences


def _match_debug_pattern(events: List[EpisodicEvent], min_confidence: float) -> List[EventSequence]:
    """Match debug session pattern: ERROR+ → DEBUGGING → FIX → SUCCESS."""
    sequences = []

    # Look for windows with multiple errors followed by success
    for i in range(len(events) - 3):
        window = events[i : i + 6]  # Look at up to 6 events

        # Count errors at start
        error_count = 0
        for e in window[:4]:
            type_str = _get_event_type_str(e)
            if type_str in ["error", "debugging"]:
                error_count += 1
            else:
                break

        if error_count >= 2:
            # Look for success after errors
            for j in range(error_count, len(window)):
                if window[j].outcome == "success":
                    debug_sequence = window[: j + 1]

                    time_span = (
                        debug_sequence[-1].timestamp - debug_sequence[0].timestamp
                    ).total_seconds()
                    confidence = min(0.7 + (error_count * 0.05), 0.95)

                    if confidence >= min_confidence:
                        # Create relations
                        relations = []
                        for k in range(len(debug_sequence) - 1):
                            relations.append(
                                TemporalRelation(
                                    debug_sequence[k].id,
                                    debug_sequence[k + 1].id,
                                    "shortly_after",
                                    0.7,
                                    datetime.now(),
                                )
                            )

                        sequences.append(
                            EventSequence(
                                events=debug_sequence,
                                pattern="debug_session",
                                match_confidence=confidence,
                                temporal_relations=relations,
                            )
                        )
                    break

    return sequences


def _match_refactor_pattern(
    events: List[EpisodicEvent], min_confidence: float
) -> List[EventSequence]:
    """Match refactoring pattern: Multiple file changes in same area."""
    sequences = []

    # Group events by session
    from collections import defaultdict

    session_events = defaultdict(list)

    for event in events:
        type_str = _get_event_type_str(event)
        if type_str == "file_change":
            session_events[event.session_id].append(event)

    # Find refactoring sessions (3+ file changes in same area)
    for session_id, session_files in session_events.items():
        if len(session_files) < 3:
            continue

        # Check if changes are in same directory
        cwds = [e.context.cwd for e in session_files if e.context and e.context.cwd]

        if cwds:
            # Calculate directory overlap
            common_prefix = _longest_common_prefix(cwds)

            if len(common_prefix) > 0:
                time_span = (
                    session_files[-1].timestamp - session_files[0].timestamp
                ).total_seconds()

                # Refactoring typically takes < 2 hours
                if time_span < 7200:
                    confidence = min(0.6 + (len(session_files) * 0.05), 0.9)

                    if confidence >= min_confidence:
                        relations = []
                        for k in range(len(session_files) - 1):
                            relations.append(
                                TemporalRelation(
                                    session_files[k].id,
                                    session_files[k + 1].id,
                                    "shortly_after",
                                    0.8,
                                    datetime.now(),
                                )
                            )

                        sequences.append(
                            EventSequence(
                                events=session_files,
                                pattern="refactor",
                                match_confidence=confidence,
                                temporal_relations=relations,
                            )
                        )

    return sequences


def _match_generic_pattern(
    events: List[EpisodicEvent], min_confidence: float
) -> List[EventSequence]:
    """Generic pattern matcher for custom sequences."""
    # For now, return empty - this would be extended for custom patterns
    return []


def _get_event_type_str(event: EpisodicEvent) -> str:
    """Get event type as string."""
    return event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)


def _calculate_sequence_confidence(
    events: List[EpisodicEvent], time_span_seconds: float, file_overlap: bool = False
) -> float:
    """Calculate confidence score for event sequence."""
    confidence = 0.5

    # Time proximity bonus
    if time_span_seconds < 300:  # < 5 minutes
        confidence += 0.3
    elif time_span_seconds < 3600:  # < 1 hour
        confidence += 0.2
    else:
        confidence += 0.1

    # File overlap bonus
    if file_overlap:
        confidence += 0.2

    # Same session bonus
    if len(set(e.session_id for e in events)) == 1:
        confidence += 0.1

    return min(confidence, 1.0)


def _longest_common_prefix(paths: List[str]) -> str:
    """Find longest common prefix in paths."""
    if not paths:
        return ""

    prefix = paths[0]
    for path in paths[1:]:
        while not path.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""

    return prefix
