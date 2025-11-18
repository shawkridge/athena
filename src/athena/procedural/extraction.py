"""Procedure extraction from temporal patterns."""

from collections import defaultdict
from typing import Optional

from ..episodic.models import EpisodicEvent
from ..episodic.store import EpisodicStore
from .models import Procedure, ProcedureCategory
from .store import ProceduralStore


def extract_procedures_from_patterns(
    project_id: int,
    episodic_store: EpisodicStore,
    procedural_store: ProceduralStore,
    min_occurrences: int = 3,
    lookback_days: int = 30,
) -> list[Procedure]:
    """Extract procedures from repeated temporal patterns.

    Args:
        project_id: Project ID to analyze
        episodic_store: Episodic event store
        procedural_store: Procedural memory store
        min_occurrences: Minimum pattern occurrences to extract procedure
        lookback_days: Days of history to analyze

    Returns:
        List of extracted procedures
    """
    from ..temporal.chains import create_temporal_chains

    # Get recent events
    events = episodic_store.get_recent_events(project_id, hours=lookback_days * 24)

    if len(events) < 5:
        return []

    # Create temporal chains
    chains = create_temporal_chains(events, same_session_only=False)

    if not chains:
        return []

    # Group chains by pattern signature
    pattern_groups = _group_chains_by_signature(chains)

    # Extract procedures from frequent patterns
    procedures = []
    for pattern_signature, pattern_instances in pattern_groups.items():
        if len(pattern_instances) >= min_occurrences:
            # Convert chains to event sequences
            event_sequences = [chain.events for chain in pattern_instances]

            procedure = _create_procedure_from_pattern(
                pattern_signature=pattern_signature,
                instances=event_sequences,
                project_id=project_id,
            )

            if procedure:
                # Check if procedure already exists
                existing = procedural_store.find_procedure(procedure.name)
                if not existing:
                    procedure_id = procedural_store.create_procedure(procedure)
                    procedure.id = procedure_id
                    procedures.append(procedure)

    return procedures


def _group_chains_by_signature(chains) -> dict[str, list]:
    """Group event chains by their pattern signatures.

    Args:
        chains: List of EventChain objects

    Returns:
        Dictionary mapping pattern signatures to lists of chains
    """
    pattern_groups = defaultdict(list)

    for chain in chains:
        if len(chain.events) >= 3:  # Only consider meaningful sequences
            signature = _create_pattern_signature(chain.events)
            pattern_groups[signature].append(chain)

    return pattern_groups


def _create_pattern_signature(events: list[EpisodicEvent]) -> str:
    """Create a signature string for a pattern.

    Args:
        events: Sequence of events forming a pattern

    Returns:
        Pattern signature string
    """
    # Create signature based on event types and outcomes
    signature_parts = []

    for event in events:
        event_type = (
            event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
        )
        outcome = event.outcome or "unknown"
        signature_parts.append(f"{event_type}:{outcome}")

    return " -> ".join(signature_parts)


def _create_procedure_from_pattern(
    pattern_signature: str, instances: list[list[EpisodicEvent]], project_id: int
) -> Optional[Procedure]:
    """Create a procedure from a repeated pattern.

    Args:
        pattern_signature: Pattern signature string
        instances: List of pattern instances
        project_id: Project ID

    Returns:
        Procedure if extraction succeeded, None otherwise
    """
    if not instances:
        return None

    # Determine procedure category from pattern
    category = _infer_category(instances[0])

    # Extract common steps
    steps = []
    for i in range(len(instances[0])):
        event = instances[0][i]
        step = {
            "order": i + 1,
            "action": event.content,
            "event_type": (
                event.event_type.value
                if hasattr(event.event_type, "value")
                else str(event.event_type)
            ),
            "expected_outcome": event.outcome,
        }
        steps.append(step)

    # Create procedure name
    procedure_name = _generate_procedure_name(pattern_signature, instances)

    # Create template
    template = _generate_template(steps)

    # Calculate success rate
    success_count = sum(1 for inst in instances if all(e.outcome == "success" for e in inst))
    success_rate = success_count / len(instances)

    # Extract applicable contexts (common file paths, tags)
    applicable_contexts = _extract_contexts(instances)

    procedure = Procedure(
        name=procedure_name,
        category=category,
        description=f"Procedure extracted from {len(instances)} occurrences of pattern: {pattern_signature}",
        trigger_pattern=pattern_signature,
        applicable_contexts=applicable_contexts,
        template=template,
        steps=steps,
        examples=[_create_example(inst) for inst in instances[:3]],  # First 3 examples
        success_rate=success_rate,
        usage_count=len(instances),
        created_by="learned",
    )

    return procedure


def _infer_category(events: list[EpisodicEvent]) -> ProcedureCategory:
    """Infer procedure category from events.

    Args:
        events: List of events in pattern

    Returns:
        Inferred procedure category
    """
    # Simple heuristic: look at event content keywords
    content_combined = " ".join(e.content.lower() for e in events)

    if "test" in content_combined or "pytest" in content_combined:
        return ProcedureCategory.TESTING
    elif "git" in content_combined or "commit" in content_combined:
        return ProcedureCategory.GIT
    elif "refactor" in content_combined:
        return ProcedureCategory.REFACTORING
    elif "debug" in content_combined or "error" in content_combined:
        return ProcedureCategory.DEBUGGING
    elif "deploy" in content_combined:
        return ProcedureCategory.DEPLOYMENT
    elif "review" in content_combined:
        return ProcedureCategory.CODE_REVIEW
    else:
        return ProcedureCategory.ARCHITECTURE


def _generate_procedure_name(pattern_signature: str, instances: list[list[EpisodicEvent]]) -> str:
    """Generate a descriptive procedure name.

    Args:
        pattern_signature: Pattern signature
        instances: Pattern instances

    Returns:
        Generated procedure name
    """
    # Use first event content as base
    first_event = instances[0][0]
    base_name = first_event.content[:50].strip()

    # Sanitize for procedure name
    name = base_name.replace(" ", "_").replace("/", "_").replace(":", "_")
    name = "".join(c for c in name if c.isalnum() or c == "_")

    return name.lower()


def _generate_template(steps: list[dict]) -> str:
    """Generate a template string from steps.

    Args:
        steps: List of step dictionaries

    Returns:
        Template string
    """
    template_lines = []
    for step in steps:
        template_lines.append(f"{step['order']}. {step['action']}")

    return "\n".join(template_lines)


def _extract_contexts(instances: list[list[EpisodicEvent]]) -> list[str]:
    """Extract common context tags from pattern instances.

    Args:
        instances: Pattern instances

    Returns:
        List of applicable contexts
    """
    contexts = set()

    for instance in instances:
        for event in instance:
            if event.context and hasattr(event.context, "cwd") and event.context.cwd:
                # Extract file paths
                cwd = event.context.cwd
                if "/" in cwd:
                    parts = cwd.split("/")
                    # Add relevant path components
                    for part in parts[-3:]:  # Last 3 path parts
                        if part and not part.startswith("."):
                            contexts.add(part)

            # Extract from content
            content_lower = event.content.lower()
            if "test" in content_lower:
                contexts.add("testing")
            if "git" in content_lower:
                contexts.add("git")
            if "refactor" in content_lower:
                contexts.add("refactoring")

    return sorted(list(contexts))[:5]  # Max 5 contexts


def _create_example(events: list[EpisodicEvent]) -> dict:
    """Create an example from event sequence.

    Args:
        events: Event sequence

    Returns:
        Example dictionary
    """
    return {
        "timestamp": events[0].timestamp.isoformat(),
        "steps": [
            {"action": e.content, "outcome": e.outcome, "timestamp": e.timestamp.isoformat()}
            for e in events
        ],
    }


def suggest_procedure_for_context(
    context: str,
    applicable_contexts: Optional[list[str]],
    procedural_store: ProceduralStore,
    top_k: int = 5,
) -> list[Procedure]:
    """Suggest procedures relevant to current context.

    Args:
        context: Current context description
        applicable_contexts: Context tags
        procedural_store: Procedural store
        top_k: Number of suggestions

    Returns:
        List of suggested procedures
    """
    # Search by context
    if applicable_contexts:
        procedures = procedural_store.search_procedures(context, applicable_contexts)
    else:
        procedures = procedural_store.search_procedures(context)

    # Sort by success rate and usage
    procedures.sort(key=lambda p: (p.success_rate, p.usage_count), reverse=True)

    return procedures[:top_k]
