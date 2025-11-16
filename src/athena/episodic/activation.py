"""Activation-based lifecycle management for episodic memory.

Implements ACT-R style activation decay to determine which events should stay
in working memory (active) vs. be consolidated or archived.

Based on neuroscience research:
- Baddeley's working memory model (capacity-limited, ~7±2 items)
- ACT-R activation equation: ln(sum(t_i^(-d))) where d ≈ 0.5
- Consolidation triggers: task completion, emotional salience, repetition
"""

import math
from datetime import datetime, timedelta
from typing import Optional

from .models import EpisodicEvent


def compute_activation(
    event: EpisodicEvent,
    current_time: Optional[datetime] = None,
    decay_rate: float = 0.5,
    pending_task_boost: float = 2.0,
    high_importance_boost: float = 1.5,
) -> float:
    """
    Compute activation level for an episodic event.

    Activation = base_level_decay + importance_boost + actionability_boost

    Args:
        event: The episodic event to score
        current_time: Reference time (default: now)
        decay_rate: ACT-R decay parameter (higher = faster decay), typically 0.5
        pending_task_boost: Activation boost for events related to pending tasks
        high_importance_boost: Activation boost for high-importance events

    Returns:
        Activation score (higher = more likely to stay in working memory)
    """
    if current_time is None:
        current_time = datetime.now()

    # Base level decay (ACT-R style)
    # Lower activation if consolidated or archived already
    if event.lifecycle_status in ("consolidated", "archived"):
        return 0.0

    # Time since last access (in seconds)
    time_since_access = (current_time - event.last_activation).total_seconds()
    time_since_access_hours = time_since_access / 3600.0

    # Prevent log of zero
    if time_since_access_hours < 0.1:
        time_since_access_hours = 0.1

    # Base-level activation: logarithm of accumulated practice
    # With one access at time t: base_level = ln(t^(-d)) = -d * ln(t)
    base_level = -decay_rate * math.log(time_since_access_hours) if time_since_access_hours > 0 else 0.0

    # Apply activation count (frequency bonus)
    # More frequent accesses increase base level
    frequency_bonus = math.log(max(event.activation_count, 1)) * 0.1

    # Consolidation score boost
    # Higher consolidation score = pattern was extracted = important
    consolidation_boost = event.consolidation_score * 1.0

    # Importance boost
    importance_boost = 0.0
    if event.importance_score > 0.7:
        importance_boost = high_importance_boost

    # Actionability boost
    # Events with clear next steps stay active
    actionability_boost = 0.0
    if event.has_next_step or event.actionability_score > 0.7:
        actionability_boost = 1.0

    # Success/positive outcomes stay longer
    success_boost = 0.0
    if event.outcome:
        # Handle both enum and string outcomes (model uses use_enum_values=True)
        outcome_str = event.outcome.value if hasattr(event.outcome, 'value') else str(event.outcome)
        if outcome_str == "success":
            success_boost = 0.5

    # Total activation
    total_activation = (
        base_level
        + frequency_bonus
        + consolidation_boost
        + importance_boost
        + actionability_boost
        + success_boost
    )

    return max(total_activation, 0.0)


def should_consolidate(
    event: EpisodicEvent,
    current_time: Optional[datetime] = None,
    consolidation_threshold_days: int = 7,
) -> bool:
    """
    Determine if an event should be consolidated (moved to long-term memory).

    Events are consolidated if:
    1. Related task is completed (handled by caller)
    2. Event is older than consolidation_threshold_days, AND
    3. Event has been accessed/used (frequency > 0)

    Args:
        event: The episodic event
        current_time: Reference time (default: now)
        consolidation_threshold_days: Days before consolidation eligible

    Returns:
        True if event should be consolidated
    """
    if current_time is None:
        current_time = datetime.now()

    # Already consolidated/archived
    if event.lifecycle_status != "active":
        return False

    # Age check
    age = (current_time - event.timestamp).days
    if age < consolidation_threshold_days:
        return False

    # Only consolidate if accessed (activation_count > 0)
    # Unused events are candidates for archival instead
    if event.activation_count == 0:
        return False

    return True


def should_archive(
    event: EpisodicEvent,
    current_time: Optional[datetime] = None,
    archive_threshold_days: int = 30,
    importance_threshold: float = 0.3,
) -> bool:
    """
    Determine if an event should be archived (forgotten).

    Events are archived if:
    1. Event is older than archive_threshold_days, AND
    2. Event importance is below importance_threshold, AND
    3. Event has not been accessed recently

    Args:
        event: The episodic event
        current_time: Reference time (default: now)
        archive_threshold_days: Days before archival eligible
        importance_threshold: Minimum importance to keep

    Returns:
        True if event should be archived
    """
    if current_time is None:
        current_time = datetime.now()

    # Already archived
    if event.lifecycle_status == "archived":
        return False

    # Age check
    age = (current_time - event.timestamp).days
    if age < archive_threshold_days:
        return False

    # Importance check
    if event.importance_score >= importance_threshold:
        return False

    # Not accessed recently
    days_since_access = (current_time - event.last_activation).days
    if days_since_access < 7:  # Accessed within last week
        return False

    return True


def decay_activation_batch(
    events: list[EpisodicEvent],
    current_time: Optional[datetime] = None,
) -> dict[int, float]:
    """
    Compute activation for multiple events efficiently.

    Args:
        events: List of episodic events
        current_time: Reference time (default: now)

    Returns:
        Dictionary mapping event.id to activation score
    """
    if current_time is None:
        current_time = datetime.now()

    return {
        event.id: compute_activation(event, current_time)
        for event in events
        if event.id is not None
    }


def rank_by_activation(
    events: list[EpisodicEvent],
    current_time: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> list[tuple[EpisodicEvent, float]]:
    """
    Rank events by activation score, return top N.

    Args:
        events: List of episodic events
        current_time: Reference time (default: now)
        limit: Max items to return (default: None = all)

    Returns:
        List of (event, activation_score) tuples, sorted descending by activation
    """
    if current_time is None:
        current_time = datetime.now()

    scored = [
        (event, compute_activation(event, current_time))
        for event in events
    ]
    ranked = sorted(scored, key=lambda x: x[1], reverse=True)

    if limit is not None:
        return ranked[:limit]
    return ranked


def consolidate_and_archive_batch(
    events: list[EpisodicEvent],
    current_time: Optional[datetime] = None,
    consolidation_threshold_days: int = 7,
    archive_threshold_days: int = 30,
) -> dict:
    """
    Sleep-like consolidation: identify which events should be consolidated or archived.

    This is typically called nightly or at session end to:
    1. Identify events ready for consolidation (old, accessed)
    2. Identify events to archive (old, low importance, not accessed)
    3. Update lifecycle status accordingly

    Args:
        events: List of episodic events
        current_time: Reference time (default: now)
        consolidation_threshold_days: Days before consolidation eligible (default: 7)
        archive_threshold_days: Days before archival eligible (default: 30)

    Returns:
        Dict with consolidation/archival stats:
            - to_consolidate: List of events ready for consolidation
            - to_archive: List of events to archive
            - keep_active: List of events to keep active
            - stats: Counts and transitions
    """
    if current_time is None:
        current_time = datetime.now()

    to_consolidate = []
    to_archive = []
    keep_active = []

    for event in events:
        # Skip already consolidated/archived
        if event.lifecycle_status in ("consolidated", "archived"):
            continue

        # Check consolidation eligibility
        if should_consolidate(event, current_time, consolidation_threshold_days):
            to_consolidate.append(event)
        # Check archival eligibility
        elif should_archive(event, current_time, archive_threshold_days):
            to_archive.append(event)
        # Keep active
        else:
            keep_active.append(event)

    return {
        "to_consolidate": to_consolidate,
        "to_archive": to_archive,
        "keep_active": keep_active,
        "stats": {
            "total_processed": len(events),
            "consolidation_candidates": len(to_consolidate),
            "archival_candidates": len(to_archive),
            "remaining_active": len(keep_active),
        },
    }
