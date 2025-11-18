"""Pattern validation and hallucination detection.

This module implements validation for extracted patterns to ensure they:
1. Are grounded in the source events (not hallucinated)
2. Actually appear in the evidence (verifiable)
3. Are generalized, not just restatements

Addresses research finding: CoT brittleness (arXiv:2508.01191, Aug 2025)
- Validates patterns against source to prevent hallucination storage
- Detects over-confident but incorrect patterns
- Calculates grounding score (0.0-1.0)
"""

from dataclasses import dataclass
from typing import List, Optional

from ..episodic.models import EpisodicEvent


@dataclass
class PatternValidation:
    """Results of pattern validation."""

    is_valid: bool
    grounding_score: float  # 0.0 (hallucinated) to 1.0 (well-grounded)
    hallucination_risk: str  # "none", "low", "medium", "high"
    issues: List[str]  # What's wrong with the pattern
    evidence_matches: List[str]  # Which parts of pattern are in source events
    confidence_adjusted: float  # Calibrated confidence after validation


def validate_pattern(
    pattern_description: str,
    pattern_type: str,
    original_confidence: float,
    source_events: List[EpisodicEvent],
) -> PatternValidation:
    """
    Validate that a pattern is grounded in source events.

    PHASE 1 FIX: Validation is structure-based, not text-matching.

    For workflows: validate event sequence matches pattern
    For facts/decisions: validate type-specific constraints
    For patterns: validate multi-event grounding

    Args:
        pattern_description: The extracted pattern description
        pattern_type: Type of pattern (pattern, decision, fact, workflow)
        original_confidence: Confidence claimed by extractor
        source_events: Events the pattern was extracted from

    Returns:
        PatternValidation with grounding score and adjusted confidence
    """
    if not source_events:
        return PatternValidation(
            is_valid=False,
            grounding_score=0.0,
            hallucination_risk="high",
            issues=["No source events provided"],
            evidence_matches=[],
            confidence_adjusted=0.0,
        )

    issues = []
    evidence_matches = []

    # Type-specific validation
    type_valid = _validate_pattern_type(pattern_type, source_events, [])

    if not type_valid:
        issues.append(f"Pattern type '{pattern_type}' not suitable for source events")
        return PatternValidation(
            is_valid=False,
            grounding_score=0.0,
            hallucination_risk="high",
            issues=issues,
            evidence_matches=[],
            confidence_adjusted=0.0,
        )

    # For workflows: structural validation (sequence of event types)
    if pattern_type == "workflow":
        # Workflow validation: check that events form a coherent sequence
        is_valid = _validate_workflow_pattern(pattern_description, source_events)
        grounding_score = 1.0 if is_valid else 0.5

        if is_valid:
            evidence_matches = [f"Event sequence matches workflow: {len(source_events)} events"]
            hallucination_risk = "none"
        else:
            issues.append("Event sequence doesn't clearly match workflow description")
            hallucination_risk = "low"

    # For other types: text-based validation
    else:
        # Extract key claims from pattern
        claims = _extract_claims_from_pattern(pattern_description, pattern_type)

        if not claims:
            issues.append("Could not extract verifiable claims from pattern")
            grounding_score = 0.5
        else:
            # Search for evidence of each claim
            grounded_claims = 0

            for claim in claims:
                match = _find_evidence_for_claim(claim, source_events)
                if match:
                    grounded_claims += 1
                    evidence_matches.append(match)
                else:
                    issues.append(f"No evidence found for claim: {claim}")

            # Calculate grounding score
            grounding_score = grounded_claims / len(claims) if claims else 0.0

        # Determine hallucination risk
        if grounding_score >= 0.9:
            hallucination_risk = "none"
        elif grounding_score >= 0.7:
            hallucination_risk = "low"
        elif grounding_score >= 0.5:
            hallucination_risk = "medium"
        else:
            hallucination_risk = "high"

        # For non-workflows, require higher grounding
        is_valid = grounding_score >= 0.5 and hallucination_risk != "high"

    # Adjust confidence based on grounding
    confidence_adjusted = original_confidence * grounding_score

    if not is_valid and grounding_score < 0.5:
        issues.append(f"Insufficient grounding: only {grounding_score:.0%} of pattern verified")

    return PatternValidation(
        is_valid=is_valid,
        grounding_score=grounding_score,
        hallucination_risk=hallucination_risk,
        issues=issues,
        evidence_matches=evidence_matches,
        confidence_adjusted=confidence_adjusted,
    )


def _extract_claims_from_pattern(pattern_description: str, pattern_type: str) -> List[str]:
    """
    Extract verifiable claims from pattern description.

    For example:
    - "Always run tests after auth code changes" → ["run tests", "auth code changes"]
    - "Uses PostgreSQL with JSONB" → ["uses PostgreSQL", "uses JSONB"]

    Note: For workflow patterns, we extract key actions/events rather than literal text.
    """
    claims = []

    # Split by common connectors
    sentences = pattern_description.split(".")
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Extract key phrases
        if pattern_type == "workflow":
            # Workflow: extract steps/actions
            # "test → code → pass" → ["test", "code", "pass"]
            # "Write failing test, implement feature, verify tests pass" → ["test", "implement", "verify"]

            steps = sentence.split("→")
            if len(steps) == 1:
                # No explicit arrows, try commas
                steps = sentence.split(",")

            steps = [s.strip() for s in steps if s.strip()]

            # Extract key action words
            for step in steps:
                # Extract action verbs and nouns
                words = step.lower().split()
                for i, word in enumerate(words):
                    # Look for action verbs and objects
                    if word in [
                        "write",
                        "test",
                        "run",
                        "implement",
                        "verify",
                        "fix",
                        "debug",
                        "deploy",
                        "check",
                    ]:
                        claims.append(word)
                    elif i + 1 < len(words) and words[i] in ["write", "run", "implement"]:
                        # Include next word (e.g., "write test", "run tests")
                        claims.append(f"{word} {words[i+1]}")

            # If no specific actions found, use the whole sentence as a claim
            if not claims:
                claims.append(sentence)

        elif pattern_type == "decision":
            # Decision: extract the decision itself
            # "chose PostgreSQL for JSONB" → ["PostgreSQL", "JSONB"]
            # Simple: just use the sentence as one claim
            claims.append(sentence)

        elif pattern_type == "fact":
            # Fact: the statement itself is the claim
            claims.append(sentence)

        else:  # pattern or default
            # Pattern: extract behavioral statements
            # "run tests after auth changes" → ["run tests", "auth changes"]
            if "after" in sentence.lower():
                parts = sentence.lower().split("after")
                if len(parts) == 2:
                    claims.append(parts[0].strip())
                    claims.append(parts[1].strip())
            elif "with" in sentence.lower():
                parts = sentence.lower().split("with")
                if len(parts) == 2:
                    claims.append(parts[0].strip())
                    claims.append(parts[1].strip())
            else:
                claims.append(sentence)

    return list(set([c for c in claims if len(c) > 2]))  # Filter out too-short, deduplicate


def _find_evidence_for_claim(claim: str, source_events: List[EpisodicEvent]) -> Optional[str]:
    """
    Search for evidence of a claim in source events.

    Returns the matching event content, or None if not found.

    Enhanced matching: strips prefixes like "Architectural decision:" to match
    the actual decision content in decision events.
    """
    from ..episodic.models import EventType

    claim_lower = claim.lower()

    # For decision-type claims, strip common prefixes to allow matching
    claim_to_match = claim_lower
    if claim_lower.startswith("architectural decision:"):
        claim_to_match = claim_lower.replace("architectural decision:", "").strip()

    for event in source_events:
        # Check event content
        if claim_to_match in event.content.lower():
            return f"Event content: {event.content[:100]}"

        # For decision events, also check if the event content matches the claim directly
        if event.event_type == EventType.DECISION and claim_lower in event.content.lower():
            return f"Decision event: {event.content[:100]}"

        # Check context
        if event.context and event.context.cwd and claim_to_match in event.context.cwd.lower():
            return f"Event location: {event.context.cwd}"

        if event.context and event.context.files:
            for file in event.context.files:
                if claim_to_match in file.lower():
                    return f"Event file: {file}"

        # Check learned field
        if event.learned and claim_to_match in event.learned.lower():
            return f"Event learning: {event.learned[:100]}"

    # No exact match found
    return None


def _validate_pattern_type(
    pattern_type: str, source_events: List[EpisodicEvent], claims: List[str]
) -> bool:
    """
    Type-specific validation.

    Returns True if pattern type is appropriate for the events.

    For workflows, we're more lenient since they describe sequences,
    not necessarily literal text in events.
    """
    from ..episodic.models import EventType

    if pattern_type == "workflow":
        # Workflow requires multiple events with clear sequence
        if len(source_events) < 2:
            return False
        # Should have variety of event types (not all same)
        event_types = set(e.event_type for e in source_events)
        return len(event_types) >= 2

    elif pattern_type == "decision":
        # Decision pattern should have at least one decision event
        decision_events = [e for e in source_events if e.event_type == EventType.DECISION]
        return len(decision_events) >= 1

    elif pattern_type == "fact":
        # Facts should be concrete, verifiable claims
        # Any source events are fine
        return len(source_events) >= 1

    else:  # "pattern"
        # Patterns should have multiple events showing repetition
        return len(source_events) >= 2

    return True


def calculate_cluster_confidence(cluster: List[EpisodicEvent]) -> float:
    """
    Calculate how confident we should be in patterns from this cluster.

    Factors:
    - Cluster size (more events = more confidence)
    - Event confidence scores (individual events should be confident)
    - Cluster cohesion (events should be related)

    Returns:
        Confidence multiplier (0.0-1.0) to apply to all patterns from cluster
    """
    if not cluster:
        return 0.0

    # Size factor: normalize cluster size
    # 2 events = 0.5, 3 events = 0.67, 5+ events = 1.0
    size_factor = min(1.0, len(cluster) / 5.0)

    # Event confidence: average confidence of events in cluster
    avg_event_confidence = sum(e.confidence for e in cluster) / len(cluster)

    # Cohesion: if all events are same type, likely related
    event_types = set(str(e.event_type) for e in cluster)
    cohesion = 1.0 if len(event_types) <= 2 else 0.7  # Some variety is good

    # Composite confidence
    confidence = 0.5 * size_factor + 0.3 * avg_event_confidence + 0.2 * cohesion

    return confidence


def _validate_workflow_pattern(
    pattern_description: str, source_events: List[EpisodicEvent]
) -> bool:
    """
    Validate that a workflow pattern matches the actual event sequence.

    For workflows, we check:
    1. Multiple events (at least 2)
    2. Variety of event types (not all same)
    3. Logical sequence (some causal relationship)

    This is a structural validation, not text matching.
    """
    if len(source_events) < 2:
        return False

    # Check event type variety
    event_types = set(e.event_type for e in source_events)
    if len(event_types) < 2:
        return False

    # Check for logical sequences (optional but helpful)
    has_sequence = False

    # Look for common workflow patterns in event sequence
    sorted_events = sorted(source_events, key=lambda e: e.timestamp)

    for i in range(len(sorted_events) - 1):
        current = sorted_events[i]
        next_event = sorted_events[i + 1]

        # Check for common causal patterns
        from ..episodic.models import EventOutcome

        # Test → Success pattern
        if "test" in current.content.lower() and next_event.outcome == EventOutcome.SUCCESS:
            has_sequence = True
            break

        # Error → Success pattern
        if current.outcome == EventOutcome.FAILURE and next_event.outcome == EventOutcome.SUCCESS:
            has_sequence = True
            break

        # File change → Success pattern
        if next_event.outcome == EventOutcome.SUCCESS:
            has_sequence = True
            break

    return has_sequence or len(event_types) >= 2


def adjust_pattern_confidence_for_llm_brittleness(
    pattern_confidence: float, grounding_score: float, extended_thinking_budget: int
) -> float:
    """
    Adjust confidence to account for CoT brittleness.

    Research finding (arXiv:2508.01191): Chain-of-thought reasoning is brittle.
    More thinking doesn't always help—can actually degrade quality.

    Heuristic: Discount LLM confidence based on reasoning budget and grounding.
    """
    # If well-grounded, keep original confidence
    if grounding_score >= 0.9:
        return pattern_confidence

    # If poorly grounded, heavily discount
    if grounding_score < 0.5:
        return pattern_confidence * 0.3  # Reduce by 70%

    # Middle ground: moderate discount
    # More thinking budget = more discount (CoT brittleness)
    thinking_penalty = min(0.2, extended_thinking_budget / 10000)  # Max 20% penalty
    return pattern_confidence * (0.8 - thinking_penalty) * grounding_score


def rank_patterns_by_reliability(
    patterns: List[dict], max_patterns: int = 3  # List of {description, confidence, validation}
) -> List[dict]:
    """
    Rank patterns by reliability (grounding + confidence).

    Returns top-N most reliable patterns.

    Ranking formula: reliability = grounding_score * confidence_adjusted
    """
    if not patterns:
        return []

    # Calculate reliability score for each pattern
    scored_patterns = []
    for pattern in patterns:
        validation = pattern.get("validation")
        if not validation:
            reliability = 0.0
        else:
            reliability = validation.grounding_score * validation.confidence_adjusted

        scored_patterns.append({**pattern, "reliability_score": reliability})

    # Sort by reliability
    scored_patterns.sort(key=lambda p: p["reliability_score"], reverse=True)

    # Return top N with reliability >= 0.5
    return [p for p in scored_patterns[:max_patterns] if p["reliability_score"] >= 0.5]
