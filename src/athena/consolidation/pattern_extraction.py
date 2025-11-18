"""LLM-based pattern extraction from episodic event clusters.

Uses Claude extended thinking to identify generalizable patterns
from sequences of episodic events.

This is the intelligence layer - where specific episodes become
generalized knowledge through lossy compression.

"Compression = Intelligence" - HN consensus
"""

import json
from dataclasses import dataclass
from typing import List

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from ..episodic.models import EpisodicEvent


def _get_event_type_str(event: EpisodicEvent) -> str:
    """Get event type as string, handling both enum and string cases."""
    return event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)


@dataclass
class Pattern:
    """An extracted pattern from episodic events."""

    description: str
    type: str  # 'pattern', 'decision', 'fact', 'workflow'
    confidence: float  # 0.0 to 1.0
    tags: List[str]
    source_events: List[EpisodicEvent]
    evidence: str  # Why this pattern was extracted

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "description": self.description,
            "type": self.type,
            "confidence": self.confidence,
            "tags": self.tags,
            "evidence": self.evidence,
            "source_event_ids": [e.id for e in self.source_events],
        }


def extract_patterns(
    event_cluster: List[EpisodicEvent],
    use_llm: bool = True,
    min_confidence: float = 0.7,
    max_patterns: int = 3,
) -> List[Pattern]:
    """
    Extract generalizable patterns from a cluster of related events.

    PHASE 1 FIX: Now uses dual-process reasoning + validation.

    Algorithm:
    1. System 1: Try fast heuristics first
    2. Calculate uncertainty
    3. System 2: Use LLM only if uncertainty > threshold
    4. Validate all patterns against source events
    5. Detect hallucinations and adjust confidence
    6. Return only well-grounded patterns

    Args:
        event_cluster: Related episodic events to analyze
        use_llm: Whether to use Claude (True) or simple heuristics (False)
        min_confidence: Minimum confidence threshold
        max_patterns: Maximum patterns to extract per cluster

    Returns:
        List of extracted patterns (validated and grounded)
    """
    from .dual_process import decide_extraction_approach, recommend_system_2_questions
    from .pattern_validation import (
        validate_pattern,
        rank_patterns_by_reliability,
        calculate_cluster_confidence,
    )

    if not event_cluster:
        return []

    if len(event_cluster) < 2:
        # Can't extract patterns from single events
        return []

    # Step 1: Decide extraction approach (System 1 vs System 2)
    approach = decide_extraction_approach(event_cluster)

    # Step 2: Always start with System 1 (heuristics)
    patterns = _extract_patterns_heuristic(event_cluster, min_confidence=0.0)

    # Step 3: If needed, use System 2 (LLM)
    if use_llm and ANTHROPIC_AVAILABLE and approach.use_system_2:
        system_2_questions = recommend_system_2_questions(
            event_cluster,
            [
                Pattern(
                    description=p.description,
                    type=p.pattern_type,
                    confidence=p.confidence,
                    tags=p.tags,
                    source_events=event_cluster,
                    evidence=p.evidence,
                )
                for p in patterns
            ],
        )

        llm_patterns = _extract_patterns_with_llm(
            event_cluster,
            min_confidence=0.0,
            max_patterns=max_patterns,
            system_2_questions=system_2_questions,
        )

        patterns.extend(llm_patterns)

    # Step 4: Validate ALL patterns against source events
    validated_patterns = []
    cluster_confidence_multiplier = calculate_cluster_confidence(event_cluster)

    for pattern in patterns:
        validation = validate_pattern(
            pattern_description=pattern.description,
            pattern_type=pattern.type,
            original_confidence=pattern.confidence,
            source_events=pattern.source_events,
        )

        if not validation.is_valid:
            # Skip invalid patterns (hallucinations)
            continue

        # Create validated pattern with adjusted confidence
        adjusted_confidence = validation.confidence_adjusted * cluster_confidence_multiplier

        validated_pattern = Pattern(
            description=pattern.description,
            type=pattern.type,
            confidence=adjusted_confidence,
            tags=pattern.tags + [f"grounding:{validation.grounding_score:.0%}"],
            source_events=pattern.source_events,
            evidence=pattern.evidence
            + f"\n[Validation: {validation.hallucination_risk} hallucination risk, {len(validation.evidence_matches)} evidence matches]",
        )

        validated_patterns.append(validated_pattern)

    # Step 5: Rank by reliability and filter
    pattern_dicts = [
        {
            "description": p.description,
            "type": p.type,
            "confidence": p.confidence,
            "tags": p.tags,
            "source_events": p.source_events,
            "evidence": p.evidence,
            "validation": validate_pattern(p.description, p.type, p.confidence, p.source_events),
        }
        for p in validated_patterns
    ]

    ranked_patterns = rank_patterns_by_reliability(pattern_dicts, max_patterns=max_patterns)

    # Step 6: Convert back to Pattern objects and filter by min_confidence
    final_patterns = [
        Pattern(
            description=p["description"],
            type=p["type"],
            confidence=max(p["confidence"], min_confidence),  # Ensure minimum confidence
            tags=p["tags"],
            source_events=p["source_events"],
            evidence=p["evidence"],
        )
        for p in ranked_patterns
        if p["confidence"] >= min_confidence
    ]

    return final_patterns


def _extract_patterns_with_llm(
    event_cluster: List[EpisodicEvent],
    min_confidence: float,
    max_patterns: int,
    system_2_questions: List[str] = None,
) -> List[Pattern]:
    """
    Use Claude to extract patterns from events.

    PHASE 1 FIX: Now uses System 2 questions from dual-process to focus analysis.

    Prompt uses extended thinking for deep analysis, but only for uncertain cases.
    """
    # Format events for LLM
    events_text = _format_events_for_llm(event_cluster)

    # Create prompt, incorporating System 2 questions if provided
    prompt = _build_pattern_extraction_prompt(
        events_text, max_patterns, system_2_questions=system_2_questions
    )

    try:
        # Call Claude with extended thinking
        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2000,
            thinking={
                "type": "enabled",
                "budget_tokens": 5000,  # Extended thinking for pattern analysis
            },
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text response (skip thinking blocks)
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text += block.text

        # Parse JSON response
        patterns_data = json.loads(response_text)

        # Convert to Pattern objects
        patterns = []
        for pattern_dict in patterns_data.get("patterns", []):
            if pattern_dict.get("confidence", 0.0) >= min_confidence:
                pattern = Pattern(
                    description=pattern_dict["description"],
                    type=pattern_dict.get("type", "pattern"),
                    confidence=pattern_dict["confidence"],
                    tags=pattern_dict.get("tags", []),
                    source_events=event_cluster,
                    evidence=pattern_dict.get("evidence", ""),
                )
                patterns.append(pattern)

        return patterns

    except Exception as e:
        print(f"Warning: LLM pattern extraction failed: {e}")
        # Fallback to heuristic extraction
        return _extract_patterns_heuristic(event_cluster, min_confidence)


def _extract_patterns_heuristic(
    event_cluster: List[EpisodicEvent], min_confidence: float
) -> List[Pattern]:
    """
    Fallback: Extract patterns using simple heuristics.

    Patterns detected:
    - TDD workflow (test → code → pass)
    - Error recovery (error → fix → success)
    - Refactoring (multiple changes in same area)
    - Architectural decision (decision event followed by actions)
    """
    patterns = []
    sorted_events = sorted(event_cluster, key=lambda e: e.timestamp)

    # Detect TDD pattern
    if _is_tdd_workflow(sorted_events):
        patterns.append(
            Pattern(
                description="Test-Driven Development workflow: Write failing test, implement feature, verify tests pass",
                type="workflow",
                confidence=0.85,
                tags=["tdd", "testing", "workflow"],
                source_events=event_cluster,
                evidence="Sequence shows test → implementation → success pattern",
            )
        )

    # Detect error recovery
    if _is_error_recovery(sorted_events):
        patterns.append(
            Pattern(
                description="Error recovery workflow: Encountered error, debugged and fixed issue, verified resolution",
                type="workflow",
                confidence=0.80,
                tags=["debugging", "error-handling", "workflow"],
                source_events=event_cluster,
                evidence="Sequence shows error → fix → success pattern",
            )
        )

    # Detect refactoring activity
    if _is_refactoring(sorted_events):
        patterns.append(
            Pattern(
                description="Refactoring activity: Multiple coordinated changes in related files",
                type="pattern",
                confidence=0.75,
                tags=["refactoring", "code-quality"],
                source_events=event_cluster,
                evidence="Multiple file changes in same directory over short time",
            )
        )

    # Detect architectural decision
    decision_events = [e for e in sorted_events if _get_event_type_str(e) == "decision"]
    if decision_events:
        decision = decision_events[0]
        patterns.append(
            Pattern(
                description=f"Architectural decision: {decision.content}",
                type="decision",
                confidence=0.90,
                tags=["architecture", "decision"],
                source_events=event_cluster,
                evidence="Explicit decision event recorded",
            )
        )

    return [p for p in patterns if p.confidence >= min_confidence]


def _format_events_for_llm(events: List[EpisodicEvent]) -> str:
    """Format events as structured text for LLM analysis."""
    sorted_events = sorted(events, key=lambda e: e.timestamp)

    lines = []
    lines.append("Episodic Events to Analyze:")
    lines.append("=" * 60)

    for i, event in enumerate(sorted_events, 1):
        lines.append(f"\nEvent {i}:")
        lines.append(f"  Time: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Type: {_get_event_type_str(event)}")
        lines.append(f"  Content: {event.content}")

        if event.context:
            if event.context.cwd:
                lines.append(f"  Location: {event.context.cwd}")
            if event.context.files:
                lines.append(f"  Files: {', '.join(event.context.files)}")
            if event.context.task:
                lines.append(f"  Task: {event.context.task}")

        if event.outcome:
            lines.append(f"  Outcome: {event.outcome}")

        if event.files_changed:
            lines.append(f"  Files Changed: {event.files_changed}")

    lines.append("\n" + "=" * 60)

    return "\n".join(lines)


def _build_pattern_extraction_prompt(
    events_text: str, max_patterns: int, system_2_questions: List[str] = None
) -> str:
    """Build prompt for pattern extraction using Claude.

    PHASE 1 FIX: Now includes System 2 questions to focus deep analysis.
    """
    questions_section = ""
    if system_2_questions:
        questions_section = f"""
Additionally, specifically investigate these questions (from System 1 uncertainty analysis):
{chr(10).join(f"- {q}" for q in system_2_questions)}

These questions highlight areas where fast heuristics were uncertain and need deep analysis.
"""

    return f"""You are analyzing a sequence of software development events to extract generalizable patterns.

{events_text}

Your task: Identify patterns, workflows, decisions, or facts that can be extracted from these events.

Extract up to {max_patterns} patterns. For each pattern, provide:

1. **Description**: A clear, concise description (1-3 sentences) of the pattern
2. **Type**: One of: 'pattern', 'decision', 'fact', 'workflow'
3. **Confidence**: How confident you are (0.0 to 1.0)
4. **Tags**: Relevant keywords (technologies, practices, concepts)
5. **Evidence**: Brief explanation of why this pattern exists in the events

Focus on:
- **Patterns**: Recurring workflows or conventions (e.g., "always run tests after auth code changes")
- **Decisions**: Architectural choices made (e.g., "chose PostgreSQL for JSONB support")
- **Facts**: Concrete discoveries (e.g., "authentication uses JWT with 24h expiry")
- **Workflows**: Process sequences (e.g., "TDD: test → implement → verify")

Quality criteria:
- Generalizable (applies beyond these specific events)
- Actionable (useful for future work)
- Non-obvious (not just restating what happened)
- High confidence (>0.7) based on clear evidence
- **CRITICAL**: Only claim patterns that are actually present in the events above. Do not make up claims.

{questions_section}

Respond ONLY with valid JSON in this exact format:

{{
  "patterns": [
    {{
      "description": "Pattern description here",
      "type": "pattern",
      "confidence": 0.85,
      "tags": ["tag1", "tag2"],
      "evidence": "Why this pattern was identified"
    }}
  ]
}}

If no strong patterns found, return empty list: {{"patterns": []}}
"""


# Pattern detection heuristics


def _is_tdd_workflow(events: List[EpisodicEvent]) -> bool:
    """Detect test-driven development pattern."""
    if len(events) < 3:
        return False

    # Look for: test → code → success pattern
    for i in range(len(events) - 2):
        e1, e2, e3 = events[i], events[i + 1], events[i + 2]

        if (
            "test" in e1.content.lower()
            and _get_event_type_str(e2) in ["file_change", "action"]
            and e3.outcome == "success"
        ):
            return True

    return False


def _is_error_recovery(events: List[EpisodicEvent]) -> bool:
    """Detect error recovery pattern."""
    for i in range(len(events) - 1):
        current, next_event = events[i], events[i + 1]

        if _get_event_type_str(current) == "error" and next_event.outcome == "success":
            return True

    return False


def _is_refactoring(events: List[EpisodicEvent]) -> bool:
    """Detect refactoring pattern (multiple changes, same area)."""
    if len(events) < 3:
        return False

    file_changes = [e for e in events if _get_event_type_str(e) == "file_change"]

    if len(file_changes) >= 3:
        # Check if changes are in related locations
        cwds = [e.context.cwd for e in file_changes if e.context and e.context.cwd]

        if len(set(cwds)) <= 2:  # Changes concentrated in 1-2 directories
            return True

    return False


def extract_common_tags(events: List[EpisodicEvent]) -> List[str]:
    """Extract common tags/keywords from event cluster."""
    # Extract from file paths
    paths = []
    for event in events:
        if event.context and event.context.cwd:
            paths.extend(event.context.cwd.split("/"))
        if event.context and event.context.files:
            for file in event.context.files:
                paths.extend(file.split("/"))

    # Extract from content
    content_words = []
    for event in events:
        words = event.content.lower().split()
        content_words.extend(words)

    # Find common meaningful terms
    common_terms = []

    # Technology indicators
    tech_keywords = [
        "auth",
        "test",
        "database",
        "api",
        "frontend",
        "backend",
        "jwt",
        "sql",
        "react",
        "python",
        "typescript",
        "docker",
    ]

    for keyword in tech_keywords:
        if any(keyword in word for word in content_words + paths):
            common_terms.append(keyword)

    # File type indicators
    if any(".py" in path for path in paths):
        common_terms.append("python")
    if any(".ts" in path or ".js" in path for path in paths):
        common_terms.append("javascript")

    return list(set(common_terms))[:5]  # Return up to 5 tags
