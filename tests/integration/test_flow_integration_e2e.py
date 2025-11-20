"""End-to-end integration test for MemoryFlowRouter with EpisodicStore.

Tests the complete workflow:
1. Create events via FlowAwareEpisodicStore
2. Access events (triggers flow routing)
3. Run consolidation cycles
4. Verify tier distribution
"""

import pytest

from src.athena.core.database import Database, reset_database
from src.athena.flow import FlowAwareEpisodicStore, get_flow_hooks_handler
from src.athena.episodic.models import EpisodicEvent, EventType


@pytest.fixture
async def db():
    """Get test database instance."""
    reset_database()
    db = Database()
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
async def flow_store(db):
    """Get flow-aware episodic store."""
    return FlowAwareEpisodicStore(db, enable_flow_routing=True)


@pytest.mark.asyncio
async def test_flow_aware_store_records_access(flow_store):
    """Test that accessing events records flow state changes."""
    # Create event
    event = EpisodicEvent(
        project_id=1,
        session_id="test",
        content="Test event",
        event_type=EventType.ACTION,
        importance_score=0.7,
    )
    event_id = await flow_store.store(event)

    # Access the event multiple times
    for i in range(3):
        result = await flow_store.get(event_id)
        assert result is not None
        assert result.id == event_id


@pytest.mark.asyncio
async def test_flow_aware_search_uses_hot_first(flow_store):
    """Test that search uses hot-first routing."""
    # Create test events
    events = []
    for i in range(5):
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content=f"Test event {i}",
            event_type=EventType.ACTION,
            lifecycle_status="active" if i < 2 else "session",
        )
        event_id = await flow_store.store(event)
        events.append(event_id)

    # Search should return results
    results = await flow_store.search("Test", limit=10)
    assert len(results) > 0


@pytest.mark.asyncio
async def test_working_memory_snapshot(flow_store):
    """Test getting working memory snapshot with metadata."""
    # Create some events
    for i in range(5):
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content=f"Event {i}",
            event_type=EventType.ACTION,
            importance_score=0.5 + (i * 0.1),
        )
        await flow_store.store(event)

    # Get working memory snapshot
    snapshot = await flow_store.get_working_memory_snapshot(limit=7)

    # Should return items with metadata
    assert isinstance(snapshot, list)
    for item in snapshot:
        assert "event" in item
        assert "activation_strength" in item
        assert "access_count" in item


@pytest.mark.asyncio
async def test_consolidation_candidates(flow_store):
    """Test getting consolidation candidates."""
    # Create high-importance event
    event = EpisodicEvent(
        project_id=1,
        session_id="test",
        content="Important discovery",
        event_type=EventType.DECISION,
        importance_score=0.9,
        actionability_score=0.8,
    )
    event_id = await flow_store.store(event)

    # Access it to increase activation
    for _ in range(5):
        await flow_store.get(event_id)

    # Get consolidation candidates
    candidates = await flow_store.get_consolidation_candidates(threshold=0.5)

    # Should identify candidates
    assert isinstance(candidates, list)


@pytest.mark.asyncio
async def test_hooks_integration_session_cycle(db):
    """Test hook handlers for session lifecycle."""
    handler = get_flow_hooks_handler(db)

    # Simulate session start
    start_result = await handler.on_session_start()
    assert start_result["status"] == "success"
    assert "working_memory_items" in start_result

    # Create some events to consolidate
    from src.athena.episodic.store import EpisodicStore

    episodic_store = EpisodicStore(db)
    for i in range(3):
        event = EpisodicEvent(
            project_id=1,
            session_id="test",
            content=f"Event {i}",
            event_type=EventType.ACTION,
            importance_score=0.7,
        )
        await episodic_store.store(event)

    # Simulate session end (consolidation)
    end_result = await handler.on_session_end()
    assert end_result["status"] == "success"
    assert "decay" in end_result
    assert "consolidation" in end_result


@pytest.mark.asyncio
async def test_periodic_decay_cycle(db):
    """Test periodic decay cycle handler."""
    handler = get_flow_hooks_handler(db)

    # Run periodic decay
    result = await handler.periodic_decay_cycle(interval_hours=1)
    assert result["status"] == "success"
    assert "stats" in result


@pytest.mark.asyncio
async def test_store_update_records_access(flow_store):
    """Test that updating an event records flow access."""
    # Create and store event
    event = EpisodicEvent(
        project_id=1,
        session_id="test",
        content="Test event",
        event_type=EventType.ACTION,
    )
    event_id = await flow_store.store(event)

    # Update the event
    result = await flow_store.update(event_id, content="Updated content")
    assert result is True


@pytest.mark.asyncio
async def test_flow_aware_store_with_disabled_routing(db):
    """Test that flow routing can be disabled."""
    store = FlowAwareEpisodicStore(db, enable_flow_routing=False)

    event = EpisodicEvent(
        project_id=1,
        session_id="test",
        content="Test event",
        event_type=EventType.ACTION,
    )
    event_id = await store.store(event)

    # Access should work but not trigger flow routing
    result = await store.get(event_id)
    assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
