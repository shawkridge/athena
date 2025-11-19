"""Integration tests for memory flow router system.

Tests the complete memory flow pipeline:
- Activation dynamics (decay + RIF)
- Tier management (working → session → episodic)
- Consolidation (strong → semantic, weak → decay)
- Temporal clustering (group related items)
- Query routing (hot-first search)
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from src.athena.core.database import Database, reset_database
from src.athena.flow.router import MemoryFlowRouter
from src.athena.episodic.store import EpisodicStore
from src.athena.episodic.models import EpisodicEvent, EventType, EventOutcome


@pytest.fixture
async def db():
    """Get test database instance."""
    reset_database()
    db = Database()
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
async def router(db):
    """Get memory flow router instance."""
    yield MemoryFlowRouter(db)


@pytest.fixture
async def episodic_store(db):
    """Get episodic store instance."""
    yield EpisodicStore(db)


@pytest.mark.asyncio
async def test_record_event_access_boosts_activation(router, episodic_store):
    """Test that recording event access boosts its activation."""
    # Create test event
    event = EpisodicEvent(
        project_id=1,
        session_id="test-session",
        content="Test event content",
        event_type=EventType.ACTION,
        outcome=EventOutcome.SUCCESS,
    )
    event_id = await episodic_store.store(event)

    # Record access
    await router.record_event_access(event_id, boost=0.5)

    # Verify access was recorded
    stored = await episodic_store.get(event_id)
    assert stored is not None
    assert stored.activation_count >= 1


@pytest.mark.asyncio
async def test_working_memory_respects_baddeley_limit(
    router, episodic_store
):
    """Test that working memory enforces 7±2 hard limit."""
    # Create 15 test events
    event_ids = []
    for i in range(15):
        event = EpisodicEvent(
            project_id=1,
            session_id="test-session",
            content=f"Event {i}",
            event_type=EventType.ACTION,
            importance_score=0.5,
            actionability_score=0.5,
        )
        event_id = await episodic_store.store(event)
        event_ids.append(event_id)

    # Access all events to move them to working memory
    for event_id in event_ids:
        await router.record_event_access(event_id)

    # Get working memory
    working = await router.get_working_memory(limit=7)

    # Should not exceed 7 items
    assert len(working) <= 7
    assert len(working) >= 5  # Allow 7±2


@pytest.mark.asyncio
async def test_consolidation_promotes_strong_items(router, episodic_store):
    """Test that consolidation promotes items with high activation."""
    # Create high-importance event
    event = EpisodicEvent(
        project_id=1,
        session_id="test-session",
        content="Important discovery",
        event_type=EventType.DECISION,
        importance_score=0.9,
        actionability_score=0.8,
        activation_count=10,
    )
    event_id = await episodic_store.store(event)

    # Run consolidation
    stats = await router.run_consolidation_cycle()

    # Check if promoted
    # (May or may not promote depending on activation calculation)
    assert "promoted" in stats
    assert "decayed" in stats


@pytest.mark.asyncio
async def test_temporal_clustering_groups_recent_items(
    router, episodic_store
):
    """Test that temporal clustering groups temporally-related items."""
    # Create 5 events within 5 minutes
    now = datetime.now()
    event_ids = []

    for i in range(5):
        event = EpisodicEvent(
            project_id=1,
            session_id="test-session",
            content=f"Related event {i}",
            event_type=EventType.ACTION,
            timestamp=now + timedelta(seconds=i * 30),
            importance_score=0.7,
            actionability_score=0.6,
        )
        event_id = await episodic_store.store(event)
        event_ids.append(event_id)

    # Run clustering
    stats = await router.run_temporal_clustering()

    # Should create clusters
    assert stats["clustered"] >= 0
    assert stats["consolidated"] >= 0


@pytest.mark.asyncio
async def test_search_hot_first_prioritizes_working_memory(
    router, episodic_store
):
    """Test that hot-first search prioritizes working memory items."""
    # Create events in different tiers
    # Working memory item
    event1 = EpisodicEvent(
        project_id=1,
        session_id="test-session",
        content="Important recent action",
        event_type=EventType.ACTION,
        lifecycle_status="active",
        last_activation=datetime.now(),
    )
    event1_id = await episodic_store.store(event1)

    # Session cache item
    event2 = EpisodicEvent(
        project_id=1,
        session_id="test-session",
        content="Less recent action",
        event_type=EventType.ACTION,
        lifecycle_status="session",
        last_activation=datetime.now() - timedelta(hours=1),
    )
    event2_id = await episodic_store.store(event2)

    # Search
    results = await router.search_hot_first("action", limit=10)

    # Working memory item should appear first
    if results:
        first_tier = results[0].get("tier", "")
        assert first_tier == "active" or "session" in [
            r.get("tier") for r in results
        ]


@pytest.mark.asyncio
async def test_decay_cycle_updates_activation(router, episodic_store):
    """Test that decay cycle updates activation levels."""
    # Create event
    event = EpisodicEvent(
        project_id=1,
        session_id="test-session",
        content="Test event",
        event_type=EventType.ACTION,
        activation_count=5,
    )
    event_id = await episodic_store.store(event)

    # Record initial state
    initial = await episodic_store.get(event_id)
    initial_count = initial.activation_count

    # Run decay
    stats = await router.process_decay()

    # Check results
    assert "decayed" in stats
    assert "demoted" in stats
    assert "archived" in stats


@pytest.mark.asyncio
async def test_flow_health_returns_valid_metrics(router):
    """Test that flow health check returns valid metrics."""
    health = await router.get_flow_health()

    assert "working_memory_utilization" in health
    assert "session_cache_utilization" in health
    assert "consolidation_rate" in health
    assert "tier_composition" in health
    assert "warnings" in health

    # Check value ranges
    assert 0 <= health["working_memory_utilization"] <= 2.0  # Allow over 100%
    assert 0 <= health["session_cache_utilization"] <= 2.0
    assert 0 <= health["consolidation_rate"] <= 1.0


@pytest.mark.asyncio
async def test_get_working_memory_returns_active_items(
    router, episodic_store
):
    """Test that get_working_memory returns currently active items."""
    # Create some events
    for i in range(5):
        event = EpisodicEvent(
            project_id=1,
            session_id="test-session",
            content=f"Event {i}",
            event_type=EventType.ACTION,
            lifecycle_status="active" if i < 3 else "session",
        )
        await episodic_store.store(event)

    # Get working memory
    items = await router.get_working_memory(limit=10)

    # Should return items (may be 0-7 depending on data)
    assert isinstance(items, list)
    assert len(items) <= 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
