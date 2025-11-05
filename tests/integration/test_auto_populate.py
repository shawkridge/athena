"""Integration tests for automatic layer population."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from athena.integration import IntegratedEpisodicStore, auto_populate_spatial, auto_populate_temporal
from athena.spatial.store import SpatialStore


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = Database(db_path)
    yield db
    db.close()

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def project_id():
    """Return test project ID."""
    return 1


def test_auto_populate_spatial_from_event(temp_db, project_id):
    """Test automatic spatial hierarchy building from event context."""
    spatial_store = SpatialStore(temp_db)

    # Create event with file context
    event = EpisodicEvent(
        project_id=project_id,
        session_id="test-session",
        timestamp=datetime.now(),
        event_type=EventType.FILE_CHANGE,
        content="Modified authentication middleware",
        context=EventContext(
            cwd="/project/src",
            files=[
                "/project/src/auth/middleware.py",
                "/project/src/auth/utils.py",
            ],
        ),
    )

    # Auto-populate spatial hierarchy
    nodes_created = auto_populate_spatial(event, spatial_store, project_id)

    # Should create nodes for all path components
    assert nodes_created > 0

    # Verify nodes were created
    node = spatial_store.get_node(project_id, "/project")
    assert node is not None
    assert node.name == "project"
    assert node.depth == 0

    auth_node = spatial_store.get_node(project_id, "/project/src/auth")
    assert auth_node is not None
    assert auth_node.name == "auth"
    assert auth_node.parent_path == "/project/src"


def test_auto_populate_spatial_with_cwd_only(temp_db, project_id):
    """Test spatial population when only cwd is present."""
    spatial_store = SpatialStore(temp_db)

    event = EpisodicEvent(
        project_id=project_id,
        session_id="test-session",
        timestamp=datetime.now(),
        event_type=EventType.CONVERSATION,
        content="Discussed refactoring",
        context=EventContext(cwd="/project/docs"),
    )

    nodes_created = auto_populate_spatial(event, spatial_store, project_id)

    assert nodes_created > 0

    docs_node = spatial_store.get_node(project_id, "/project/docs")
    assert docs_node is not None


def test_auto_populate_temporal_creates_relations(temp_db, project_id):
    """Test automatic temporal relation creation."""
    integrated_store = IntegratedEpisodicStore(temp_db, auto_spatial=False, auto_temporal=False)

    # Create sequence of events
    base_time = datetime.now()
    events = [
        EpisodicEvent(
            project_id=project_id,
            session_id="session-1",
            timestamp=base_time,
            event_type=EventType.FILE_CHANGE,
            content="Write test",
            context=EventContext(cwd="/project"),
        ),
        EpisodicEvent(
            project_id=project_id,
            session_id="session-1",
            timestamp=base_time + timedelta(seconds=30),
            event_type=EventType.TEST_RUN,
            content="Run tests",
            context=EventContext(cwd="/project"),
        ),
        EpisodicEvent(
            project_id=project_id,
            session_id="session-1",
            timestamp=base_time + timedelta(seconds=60),
            event_type=EventType.FILE_CHANGE,
            content="Fix implementation",
            context=EventContext(cwd="/project"),
        ),
    ]

    # Record events
    for event in events:
        integrated_store.record_event(event)

    # Manually trigger temporal population
    relations_created = auto_populate_temporal(
        episodic_store=integrated_store.episodic_store,
        project_id=project_id,
        hours_lookback=24,
    )

    # Should create relations between consecutive events
    assert relations_created > 0

    # Verify relations exist
    event_1 = integrated_store.get_recent_events(project_id, hours=24)[2]  # First event (oldest)
    relations = integrated_store.get_event_relations(event_1.id)

    assert len(relations) > 0
    assert any(r["relation_type"] == "immediately_after" for r in relations)


def test_integrated_store_auto_spatial(temp_db, project_id):
    """Test IntegratedEpisodicStore auto-spatial population."""
    # Use batch_size=1 to test immediate spatial population
    integrated_store = IntegratedEpisodicStore(temp_db, auto_spatial=True, auto_temporal=False, spatial_batch_size=1)

    event = EpisodicEvent(
        project_id=project_id,
        session_id="test-session",
        timestamp=datetime.now(),
        event_type=EventType.FILE_CHANGE,
        content="Update config",
        context=EventContext(
            cwd="/project/config",
            files=["/project/config/settings.json"],
        ),
    )

    event_id = integrated_store.record_event(event)

    assert event_id > 0

    # Verify spatial nodes were auto-created
    config_node = integrated_store.spatial_store.get_node(project_id, "/project/config")
    assert config_node is not None
    assert config_node.name == "config"


def test_integrated_store_auto_temporal_batching(temp_db, project_id):
    """Test IntegratedEpisodicStore auto-temporal with batching."""
    integrated_store = IntegratedEpisodicStore(
        temp_db,
        auto_spatial=False,
        auto_temporal=True,
        temporal_batch_size=3  # Trigger after 3 events
    )

    base_time = datetime.now()

    # Record 3 events to trigger temporal update
    for i in range(3):
        event = EpisodicEvent(
            project_id=project_id,
            session_id="batch-session",
            timestamp=base_time + timedelta(seconds=i * 10),
            event_type=EventType.FILE_CHANGE,
            content=f"Change {i}",
            context=EventContext(cwd="/project"),
        )
        integrated_store.record_event(event)

    # Temporal relations should have been created automatically
    events = integrated_store.get_recent_events(project_id, hours=24)

    if len(events) >= 2:
        first_event = events[-1]  # Oldest event
        relations = integrated_store.get_event_relations(first_event.id)
        # Should have at least one temporal relation
        assert len(relations) > 0


def test_integrated_store_delegates_methods(temp_db, project_id):
    """Test that IntegratedEpisodicStore delegates methods to underlying store."""
    integrated_store = IntegratedEpisodicStore(temp_db)

    event = EpisodicEvent(
        project_id=project_id,
        session_id="delegation-test",
        timestamp=datetime.now(),
        event_type=EventType.ACTION,
        content="Test delegation",
        context=EventContext(cwd="/project"),
    )

    event_id = integrated_store.record_event(event)

    # Test delegation of get_event
    retrieved = integrated_store.get_event(event_id)
    assert retrieved is not None
    assert retrieved.id == event_id
    assert retrieved.content == "Test delegation"

    # Test delegation of get_recent_events
    recent = integrated_store.get_recent_events(project_id, hours=1)
    assert len(recent) > 0
    assert any(e.id == event_id for e in recent)


def test_auto_populate_no_context(temp_db, project_id):
    """Test auto-population with event that has no context."""
    spatial_store = SpatialStore(temp_db)

    event = EpisodicEvent(
        project_id=project_id,
        session_id="no-context",
        timestamp=datetime.now(),
        event_type=EventType.CONVERSATION,
        content="General discussion",
        # No context
    )

    # Should not crash, just return 0
    nodes_created = auto_populate_spatial(event, spatial_store, project_id)
    assert nodes_created == 0
