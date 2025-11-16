"""Temporal Causality Detection for Episodic Memory

Detects causal relationships between episodic events based on:
1. Temporal proximity (events within 30-minute window)
2. Context overlap (shared files, tasks, phases)
3. Code signals (changes + test failures/successes)

Uses a scoring system to assign confidence to causal links.
Enables "why?" queries: "Why did this fail?" → trace causality chain.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum


class CausalityType(Enum):
    """Types of causal relationships detected."""
    DIRECT_CAUSE = "direct_cause"  # Likely cause-effect
    CONTRIBUTING_FACTOR = "contributing_factor"  # Partial cause
    TEMPORAL_CORRELATION = "temporal_correlation"  # Just correlated in time
    CODE_CHANGE_EFFECT = "code_change_effect"  # Code change → test result


@dataclass
class CausalLink:
    """Represents a causal relationship between two events."""
    source_event_id: int
    target_event_id: int
    causality_type: CausalityType
    confidence: float  # 0-1, higher = more confident
    reasoning: str  # Why we think this is causal

    # Context for explanation
    temporal_proximity_ms: int  # Time between events
    shared_context_score: float  # 0-1, how much context overlap
    code_signal_strength: float  # 0-1, code change strength


@dataclass
class EventSignature:
    """Compact representation of an episodic event for causality analysis."""
    event_id: int
    timestamp: int  # Unix milliseconds
    event_type: str
    outcome: Optional[str]  # success, failure, error, etc.

    # Context fields
    files: Set[str] = None  # Changed/accessed files
    task: Optional[str] = None
    phase: Optional[str] = None
    session_id: Optional[str] = None

    # Code signals
    has_code_change: bool = False
    has_test_result: bool = False
    test_passed: Optional[bool] = None
    error_type: Optional[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.files is None:
            self.files = set()


class TemporalCausalityDetector:
    """Detects temporal causal relationships between episodic events."""

    # Configuration constants
    TEMPORAL_WINDOW_MS = 30 * 60 * 1000  # 30 minutes
    MIN_CONFIDENCE = 0.3  # Only return links with confidence >= 0.3

    # Scoring weights
    TEMPORAL_PROXIMITY_WEIGHT = 0.2
    CONTEXT_OVERLAP_WEIGHT = 0.3
    CODE_SIGNAL_WEIGHT = 0.5

    def __init__(self):
        """Initialize the causality detector."""
        pass

    def detect_causality_chains(self, events: List[EventSignature]) -> List[CausalLink]:
        """Detect causal relationships between events.

        Args:
            events: List of events, sorted by timestamp

        Returns:
            List of detected causal links (confidence >= MIN_CONFIDENCE)
        """
        if len(events) < 2:
            return []

        causal_links = []

        # Check each event pair for causality
        for i, source_event in enumerate(events):
            for j in range(i + 1, len(events)):
                target_event = events[j]

                # Skip if events are too far apart
                time_diff_ms = target_event.timestamp - source_event.timestamp
                if time_diff_ms > self.TEMPORAL_WINDOW_MS:
                    break  # Rest of events are even further apart

                # Calculate causality confidence
                link = self._evaluate_causality(source_event, target_event, time_diff_ms)

                if link and link.confidence >= self.MIN_CONFIDENCE:
                    causal_links.append(link)

        return causal_links

    def _evaluate_causality(
        self,
        source: EventSignature,
        target: EventSignature,
        time_diff_ms: int
    ) -> Optional[CausalLink]:
        """Evaluate if source event caused target event.

        Args:
            source: Earlier event
            target: Later event
            time_diff_ms: Time difference in milliseconds

        Returns:
            CausalLink with confidence score, or None if confidence too low
        """

        # Calculate component scores
        temporal_score = self._score_temporal_proximity(time_diff_ms)
        context_score = self._score_context_overlap(source, target)
        code_signal_score = self._score_code_signals(source, target)

        # Weighted combination
        confidence = (
            temporal_score * self.TEMPORAL_PROXIMITY_WEIGHT +
            context_score * self.CONTEXT_OVERLAP_WEIGHT +
            code_signal_score * self.CODE_SIGNAL_WEIGHT
        )

        if confidence < self.MIN_CONFIDENCE:
            return None

        # Determine causality type
        causality_type = self._determine_causality_type(source, target, confidence)
        reasoning = self._generate_reasoning(source, target, temporal_score, context_score, code_signal_score)

        return CausalLink(
            source_event_id=source.event_id,
            target_event_id=target.event_id,
            causality_type=causality_type,
            confidence=min(confidence, 1.0),
            reasoning=reasoning,
            temporal_proximity_ms=time_diff_ms,
            shared_context_score=context_score,
            code_signal_strength=code_signal_score
        )

    def _score_temporal_proximity(self, time_diff_ms: int) -> float:
        """Score based on how close events are in time.

        Events within 1 minute: 1.0
        Events within 5 minutes: 0.8
        Events within 30 minutes: 0.4

        Args:
            time_diff_ms: Time between events in milliseconds

        Returns:
            Score 0-1 (higher = closer in time)
        """
        if time_diff_ms <= 60 * 1000:  # 1 minute
            return 1.0
        elif time_diff_ms <= 5 * 60 * 1000:  # 5 minutes
            return 0.8
        elif time_diff_ms <= 15 * 60 * 1000:  # 15 minutes
            return 0.6
        else:  # Up to 30 minutes
            return 0.4

    def _score_context_overlap(self, source: EventSignature, target: EventSignature) -> float:
        """Score based on shared context between events.

        Higher score if they share:
        - Same files (strong signal)
        - Same task (medium signal)
        - Same phase (weak signal)
        - Same session (very strong signal)

        Args:
            source: Earlier event
            target: Later event

        Returns:
            Score 0-1 (higher = more overlap)
        """
        if not source.files or not target.files:
            # No file information - small base score
            base_score = 0.1
        else:
            # File overlap is strongest signal
            file_overlap = len(source.files & target.files)
            file_union = len(source.files | target.files)
            base_score = file_overlap / file_union if file_union > 0 else 0.0

        # Session overlap: strongest
        if source.session_id and source.session_id == target.session_id:
            return min(0.95, base_score + 0.5)  # Very high confidence

        # Task overlap: medium boost
        if source.task and source.task == target.task:
            base_score += 0.3

        # Phase overlap: small boost
        if source.phase and source.phase == target.phase:
            base_score += 0.1

        return min(base_score, 1.0)

    def _score_code_signals(self, source: EventSignature, target: EventSignature) -> float:
        """Score based on code-related signals indicating causality.

        High confidence patterns:
        - Code change (source) → test result (target): 0.9
        - Code change (source) → error event (target): 0.85
        - Error (source) → fix/success (target): 0.8

        Args:
            source: Earlier event
            target: Later event

        Returns:
            Score 0-1 (higher = stronger code signal)
        """

        # Pattern: Code change → Test result (very strong)
        if source.has_code_change and target.has_test_result:
            # Test passed after change: positive causality
            if target.test_passed:
                return 0.85  # Change likely helped
            else:
                return 0.9  # Change likely broke something

        # Pattern: Code change → Error (strong)
        if source.has_code_change and target.outcome == "error":
            return 0.85

        # Pattern: Error event → Success event (medium)
        if source.outcome == "error" and target.outcome == "success":
            return 0.7

        # Pattern: Error type match (medium)
        if source.error_type and source.error_type == target.error_type:
            return 0.6

        # No strong code signals
        return 0.0

    def _determine_causality_type(
        self,
        source: EventSignature,
        target: EventSignature,
        confidence: float
    ) -> CausalityType:
        """Determine the type of causal relationship.

        Args:
            source: Earlier event
            target: Later event
            confidence: Overall confidence score

        Returns:
            CausalityType enum value
        """

        # Direct cause: code change leading to test result
        if source.has_code_change and target.has_test_result:
            return CausalityType.CODE_CHANGE_EFFECT

        # Strong temporal + context overlap
        if confidence > 0.7:
            return CausalityType.DIRECT_CAUSE

        # Medium confidence
        if confidence > 0.5:
            return CausalityType.CONTRIBUTING_FACTOR

        # Low confidence (but still >= MIN_CONFIDENCE)
        return CausalityType.TEMPORAL_CORRELATION

    def _generate_reasoning(
        self,
        source: EventSignature,
        target: EventSignature,
        temporal_score: float,
        context_score: float,
        code_signal_score: float
    ) -> str:
        """Generate human-readable reasoning for the causal link.

        Args:
            source: Earlier event
            target: Later event
            temporal_score: Temporal proximity score
            context_score: Context overlap score
            code_signal_score: Code signal score

        Returns:
            String describing why we think these events are causal
        """
        reasons = []

        # Temporal reason
        if temporal_score > 0.8:
            reasons.append("events are very close in time (< 1 min)")
        elif temporal_score > 0.6:
            reasons.append("events are close in time (< 5 min)")
        else:
            reasons.append("events are within causality window (< 30 min)")

        # Context reason
        if context_score > 0.8:
            reasons.append("strong context overlap (shared session/files)")
        elif context_score > 0.5:
            reasons.append("moderate context overlap (same task/phase)")
        elif context_score > 0.0:
            reasons.append("some context overlap")

        # Code signal reason
        if code_signal_score > 0.8:
            reasons.append("strong code signal (change→test/error)")
        elif code_signal_score > 0.5:
            reasons.append("error pattern detected")

        return "; ".join(reasons)


def events_to_signatures(events_dict_list: List[Dict]) -> List[EventSignature]:
    """Convert database event dictionaries to EventSignature objects.

    Args:
        events_dict_list: List of episodic_events table rows

    Returns:
        List of EventSignature objects
    """
    signatures = []

    for event_dict in events_dict_list:
        # Parse files from context_files array
        files = set()
        if event_dict.get('context_files'):
            files = set(event_dict['context_files'])

        signature = EventSignature(
            event_id=event_dict['id'],
            timestamp=event_dict.get('timestamp', 0),
            event_type=event_dict.get('event_type', 'unknown'),
            outcome=event_dict.get('outcome'),
            files=files,
            task=event_dict.get('context_task'),
            phase=event_dict.get('context_phase'),
            session_id=event_dict.get('session_id'),
            has_code_change=(
                event_dict.get('event_type') in ['FILE_CHANGE', 'CODE_EDIT', 'REFACTORING']
                or event_dict.get('files_changed', 0) > 0
            ),
            has_test_result=event_dict.get('event_type') == 'TEST_RUN',
            test_passed=event_dict.get('outcome') == 'success' if event_dict.get('event_type') == 'TEST_RUN' else None,
            error_type=event_dict.get('error_type')
        )
        signatures.append(signature)

    # Sort by timestamp
    signatures.sort(key=lambda s: s.timestamp)
    return signatures
