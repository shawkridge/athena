"""Dual-process reasoning for pattern extraction.

Implements System 1 (fast heuristics) → System 2 (slow LLM reasoning) pipeline.

Research finding (Li et al., 2025): LLMs work best with dual-process reasoning:
- System 1: Quick pattern matching using heuristics (reliable, fast)
- System 2: Deep analysis using extended thinking (slow, prone to brittleness)

Key insight: Use System 1 for high-confidence cases, System 2 only for uncertain cases.
This avoids CoT brittleness while maintaining accuracy.
"""

from dataclasses import dataclass
from typing import List

from ..episodic.models import EpisodicEvent


@dataclass
class ExtractionApproach:
    """Decision on how to extract patterns."""

    use_system_1: bool  # Use fast heuristics
    use_system_2: bool  # Use LLM extended thinking
    uncertainty: float  # 0.0 (certain) to 1.0 (very uncertain)
    reason: str  # Why this approach was chosen


@dataclass
class HeuristicPattern:
    """Pattern extracted using System 1 (heuristics)."""

    description: str
    pattern_type: str
    confidence: float
    tags: List[str]
    evidence: str


def decide_extraction_approach(
    cluster: List[EpisodicEvent],
    use_llm_threshold: float = 0.5
) -> ExtractionApproach:
    """
    Decide whether to use System 1 (heuristics) or System 2 (LLM).

    Algorithm:
    1. Try System 1 (fast heuristics)
    2. Calculate uncertainty score
    3. If uncertainty <= threshold: use System 1 only (high confidence)
    4. If uncertainty > threshold: use System 2 (need deep reasoning)

    Args:
        cluster: Event cluster to analyze
        use_llm_threshold: Uncertainty threshold above which to use LLM

    Returns:
        ExtractionApproach decision
    """
    if not cluster:
        return ExtractionApproach(
            use_system_1=False,
            use_system_2=False,
            uncertainty=1.0,
            reason="No events in cluster"
        )

    # System 1: Try fast heuristics first
    heuristic_patterns = _extract_heuristic_patterns(cluster)
    uncertainty = _calculate_uncertainty(cluster, heuristic_patterns)

    if uncertainty <= use_llm_threshold:
        # Heuristics are confident enough
        return ExtractionApproach(
            use_system_1=True,
            use_system_2=False,
            uncertainty=uncertainty,
            reason=f"System 1 confident (uncertainty: {uncertainty:.2f})"
        )
    else:
        # Uncertain: use both systems
        return ExtractionApproach(
            use_system_1=True,
            use_system_2=True,
            uncertainty=uncertainty,
            reason=f"System 2 needed (uncertainty: {uncertainty:.2f})"
        )


def _extract_heuristic_patterns(cluster: List[EpisodicEvent]) -> List[HeuristicPattern]:
    """
    Extract patterns using fast System 1 (heuristics).

    These are reliable, conservative patterns based on clear event sequences.
    """
    patterns = []
    sorted_events = sorted(cluster, key=lambda e: e.timestamp)

    # Pattern 1: TDD workflow (test → code → success)
    if _is_tdd_workflow(sorted_events):
        patterns.append(HeuristicPattern(
            description="Test-Driven Development workflow: Write failing test, implement feature, verify tests pass",
            pattern_type="workflow",
            confidence=0.85,
            tags=["tdd", "testing", "workflow"],
            evidence="Sequence shows test → implementation → success pattern"
        ))

    # Pattern 2: Error recovery (error → fix → success)
    if _is_error_recovery(sorted_events):
        patterns.append(HeuristicPattern(
            description="Error recovery workflow: Encountered error, debugged and fixed issue, verified resolution",
            pattern_type="workflow",
            confidence=0.80,
            tags=["debugging", "error-handling", "workflow"],
            evidence="Sequence shows error → fix → success pattern"
        ))

    # Pattern 3: Refactoring activity (multiple related file changes)
    if _is_refactoring(sorted_events):
        patterns.append(HeuristicPattern(
            description="Refactoring activity: Multiple coordinated changes in related files",
            pattern_type="pattern",
            confidence=0.75,
            tags=["refactoring", "code-quality"],
            evidence="Multiple file changes in same directory over short time"
        ))

    # Pattern 4: Explicit decision
    decision_events = [e for e in sorted_events if "decision" in str(e.event_type).lower()]
    if decision_events:
        decision = decision_events[0]
        patterns.append(HeuristicPattern(
            description=f"Architectural decision: {decision.content}",
            pattern_type="decision",
            confidence=0.90,
            tags=["architecture", "decision"],
            evidence="Explicit decision event recorded"
        ))

    # Pattern 5: Deployment pattern (multiple events leading to deployment)
    if _is_deployment_pattern(sorted_events):
        patterns.append(HeuristicPattern(
            description="Deployment workflow: Code changes tested, reviewed, and deployed to production",
            pattern_type="workflow",
            confidence=0.80,
            tags=["deployment", "production", "workflow"],
            evidence="Sequence shows development → testing → deployment"
        ))

    return patterns


def _calculate_uncertainty(
    cluster: List[EpisodicEvent],
    heuristic_patterns: List[HeuristicPattern]
) -> float:
    """
    Calculate uncertainty in heuristic pattern extraction.

    Factors:
    - Cluster size (larger = more confident)
    - Pattern count (more patterns = less uncertain)
    - Event type diversity (varied types = uncertain)
    - Average event confidence

    Returns:
        Uncertainty score (0.0 = certain, 1.0 = very uncertain)
    """
    if not cluster:
        return 1.0

    # Factor 1: Cluster size
    # 1-2 events: high uncertainty (0.5)
    # 3-4 events: moderate (0.3)
    # 5+ events: low (0.1)
    size_uncertainty = max(0.1, 1.0 - (len(cluster) / 5.0))

    # Factor 2: Pattern count
    # No patterns: high uncertainty (0.5)
    # 1 pattern: moderate (0.3)
    # 2+ patterns: low (0.1)
    pattern_uncertainty = max(0.1, 0.5 - (len(heuristic_patterns) * 0.2))

    # Factor 3: Event type diversity
    event_types = set(str(e.event_type) for e in cluster)
    # All same type: low uncertainty (too uniform)
    # Multiple types: high uncertainty (hard to pattern)
    type_diversity = len(event_types) / 10.0  # Normalize to 0.0-1.0
    diversity_uncertainty = 0.5 if type_diversity > 0.5 else 0.1

    # Factor 4: Average event confidence
    avg_confidence = sum(e.confidence for e in cluster) / len(cluster)
    confidence_uncertainty = 1.0 - avg_confidence

    # Composite uncertainty
    uncertainty = (
        0.3 * size_uncertainty +
        0.3 * pattern_uncertainty +
        0.2 * diversity_uncertainty +
        0.2 * confidence_uncertainty
    )

    return min(1.0, max(0.0, uncertainty))


def _is_tdd_workflow(events: List[EpisodicEvent]) -> bool:
    """Detect test-driven development pattern."""
    from ..episodic.models import EventType, EventOutcome

    if len(events) < 3:
        return False

    for i in range(len(events) - 2):
        e1, e2, e3 = events[i], events[i + 1], events[i + 2]

        # e1: test event, e2: file change/action, e3: success
        is_test = ("test" in e1.content.lower() or e1.event_type == EventType.TEST_RUN)
        is_change = e2.event_type in [EventType.FILE_CHANGE, EventType.ACTION]
        is_success = e3.outcome == EventOutcome.SUCCESS

        if is_test and is_change and is_success:
            return True

    return False


def _is_error_recovery(events: List[EpisodicEvent]) -> bool:
    """Detect error recovery pattern."""
    from ..episodic.models import EventType, EventOutcome

    if len(events) < 2:
        return False

    for i in range(len(events) - 1):
        current, next_event = events[i], events[i + 1]

        is_error = current.event_type == EventType.ERROR
        is_success = next_event.outcome == EventOutcome.SUCCESS

        if is_error and is_success:
            return True

    return False


def _is_refactoring(events: List[EpisodicEvent]) -> bool:
    """Detect refactoring pattern (multiple changes, same area)."""
    from ..episodic.models import EventType

    if len(events) < 3:
        return False

    file_changes = [e for e in events if e.event_type == EventType.FILE_CHANGE]

    if len(file_changes) >= 3:
        # Check if changes are in related locations
        cwds = [e.context.cwd for e in file_changes if e.context and e.context.cwd]

        if len(set(cwds)) <= 2:  # Changes concentrated in 1-2 directories
            return True

    return False


def _is_deployment_pattern(events: List[EpisodicEvent]) -> bool:
    """Detect deployment pattern."""
    from ..episodic.models import EventType

    event_types = [e.event_type for e in events]

    # Look for: file changes + tests + deployment
    has_file_change = EventType.FILE_CHANGE in event_types
    has_test = EventType.TEST_RUN in event_types
    has_deployment = EventType.DEPLOYMENT in event_types

    return has_file_change and has_test and has_deployment


def recommend_system_2_questions(
    cluster: List[EpisodicEvent],
    heuristic_patterns: List[HeuristicPattern]
) -> List[str]:
    """
    Generate questions for System 2 (LLM) to investigate.

    System 2 should focus on areas where System 1 is uncertain.
    """
    if not cluster:
        return []

    questions = []

    # If no patterns found, ask for deeper analysis
    if not heuristic_patterns:
        questions.append("What patterns or workflows are present in these events?")
        questions.append("Are there implicit relationships between events?")

    # If only one type of pattern, ask for others
    pattern_types = set(p.pattern_type for p in heuristic_patterns)
    if len(pattern_types) == 1:
        questions.append("Beyond the identified workflow, are there architectural decisions or best practices?")
        questions.append("What anti-patterns or risks can be identified?")

    # If very few events, ask for implicit patterns
    if len(cluster) <= 2:
        questions.append("Are there implicit causality relationships in these events?")

    # If high type diversity, ask for unifying patterns
    event_types = set(str(e.event_type) for e in cluster)
    if len(event_types) > 3:
        questions.append("What unifies these diverse event types into a cohesive pattern?")
        questions.append("What is the underlying intent or goal?")

    return questions
