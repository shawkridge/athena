"""Performance benchmarking suite for memory-mcp system.

Tests with 1000+ events to identify bottlenecks and validate indexing strategy.
"""

import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pytest

from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from athena.episodic.store import EpisodicStore
from athena.spatial.store import SpatialStore
from athena.spatial.hierarchy import build_spatial_hierarchy
from athena.temporal.chains import create_temporal_relations


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def perf_db(tmp_path):
    """Create a database for performance testing."""
    db_path = tmp_path / "perf_test.db"
    db = Database(db_path)

    # Create test project
    project = db.create_project("perf-test", str(tmp_path))

    yield db, project.id

    db.close()


@pytest.fixture
def episodic_store(perf_db):
    """Create episodic store."""
    db, project_id = perf_db
    return EpisodicStore(db), project_id


@pytest.fixture
def spatial_store(perf_db):
    """Create spatial store."""
    db, project_id = perf_db
    return SpatialStore(db), project_id


# =============================================================================
# DATA GENERATION
# =============================================================================


def generate_realistic_events(
    count: int,
    project_id: int,
    base_time: datetime = None
) -> List[EpisodicEvent]:
    """Generate realistic episodic events for testing.

    Args:
        count: Number of events to generate
        project_id: Project ID
        base_time: Starting timestamp (default: now - 30 days)

    Returns:
        List of generated events
    """
    if base_time is None:
        base_time = datetime.now() - timedelta(days=30)

    events = []

    # Realistic file paths
    file_paths = [
        "/project/src/auth/login.py",
        "/project/src/auth/jwt.py",
        "/project/src/auth/middleware.py",
        "/project/src/api/users.py",
        "/project/src/api/posts.py",
        "/project/src/database/models.py",
        "/project/src/database/migrations.py",
        "/project/tests/test_auth.py",
        "/project/tests/test_api.py",
        "/project/docs/README.md",
    ]

    # Realistic event types and content
    event_templates = [
        (EventType.ACTION, "Implemented JWT token generation", EventOutcome.SUCCESS),
        (EventType.ACTION, "Added user authentication middleware", EventOutcome.SUCCESS),
        (EventType.ACTION, "Refactored database models", EventOutcome.SUCCESS),
        (EventType.ERROR, "Test failure: authentication endpoint", EventOutcome.FAILURE),
        (EventType.ACTION, "Fixed authentication bug", EventOutcome.SUCCESS),
        (EventType.DECISION, "Chose JWT over session cookies", EventOutcome.SUCCESS),
        (EventType.FILE_CHANGE, "Updated user model schema", EventOutcome.SUCCESS),
        (EventType.FILE_CHANGE, "Added password hashing", EventOutcome.SUCCESS),
        (EventType.SUCCESS, "All tests passing", EventOutcome.SUCCESS),
        (EventType.ERROR, "Database migration failed", EventOutcome.FAILURE),
    ]

    sessions = [f"session-{i}" for i in range(count // 20)]  # ~20 events per session

    for i in range(count):
        # Distribute events over time (more recent = more events)
        # Exponential distribution for realistic workload
        time_offset_hours = int(30 * 24 * (1 - (1 - i / count) ** 2))
        timestamp = base_time + timedelta(hours=time_offset_hours)

        # Pick random template
        event_type, content, outcome = random.choice(event_templates)

        # Pick random files (1-3 files per event)
        num_files = random.randint(1, 3)
        files = random.sample(file_paths, num_files)

        # Pick session (consecutive events more likely in same session)
        session_id = sessions[i // 20] if i // 20 < len(sessions) else sessions[-1]

        context = EventContext(
            cwd=files[0].rsplit("/", 1)[0],  # Directory of first file
            files=files,
            task=f"Task {i // 10}" if i % 10 < 8 else None,
            phase=f"Phase {i // 100}" if i % 100 < 80 else None,
        )

        event = EpisodicEvent(
            project_id=project_id,
            session_id=session_id,
            timestamp=timestamp,
            event_type=event_type,
            content=f"{content} (event {i})",
            outcome=outcome,
            context=context,
            duration_ms=random.randint(100, 5000),
            files_changed=len(files),
            lines_added=random.randint(0, 100),
            lines_deleted=random.randint(0, 50),
            learned=f"Learning from event {i}" if i % 5 == 0 else None,
            confidence=random.uniform(0.7, 1.0),
        )

        events.append(event)

    return events


# =============================================================================
# BENCHMARK TESTS
# =============================================================================


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_insert_1000_events(episodic_store):
    """Benchmark inserting 1000 events."""
    store, project_id = episodic_store
    events = generate_realistic_events(1000, project_id)

    start = time.perf_counter()
    for event in events:
        store.record_event(event)
    duration = time.perf_counter() - start

    # Expectations: Should complete in < 5 seconds
    assert duration < 5.0, f"Insert took {duration:.2f}s (expected < 5s)"

    print(f"\n✓ Inserted 1000 events in {duration:.3f}s ({1000/duration:.1f} events/sec)")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_query_by_timestamp(episodic_store):
    """Benchmark timestamp-based queries."""
    store, project_id = episodic_store

    # Insert 1000 events
    events = generate_realistic_events(1000, project_id)
    for event in events:
        store.record_event(event)

    # Benchmark: Get recent events (last 7 days)
    start = time.perf_counter()
    recent = store.get_recent_events(project_id, hours=24*7, limit=100)
    duration = time.perf_counter() - start

    assert len(recent) > 0
    assert duration < 0.1, f"Query took {duration:.3f}s (expected < 0.1s)"

    print(f"\n✓ Queried recent events in {duration*1000:.1f}ms")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_query_by_session(episodic_store):
    """Benchmark session-based queries."""
    store, project_id = episodic_store

    # Insert 1000 events
    events = generate_realistic_events(1000, project_id)
    for event in events:
        store.record_event(event)

    # Benchmark: Get all events in a session
    session_id = events[100].session_id

    start = time.perf_counter()
    session_events = store.get_events_by_session(session_id)
    duration = time.perf_counter() - start

    assert len(session_events) > 0
    assert duration < 0.05, f"Query took {duration:.3f}s (expected < 0.05s)"

    print(f"\n✓ Queried session events in {duration*1000:.1f}ms ({len(session_events)} events)")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_query_by_type(episodic_store):
    """Benchmark event type queries."""
    store, project_id = episodic_store

    # Insert 1000 events
    events = generate_realistic_events(1000, project_id)
    for event in events:
        store.record_event(event)

    # Benchmark: Get all errors
    start = time.perf_counter()
    errors = store.get_events_by_type(project_id, EventType.ERROR, limit=50)
    duration = time.perf_counter() - start

    assert len(errors) > 0
    assert duration < 0.05, f"Query took {duration:.3f}s (expected < 0.05s)"

    print(f"\n✓ Queried error events in {duration*1000:.1f}ms ({len(errors)} events)")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_text_search(episodic_store):
    """Benchmark text search on content."""
    store, project_id = episodic_store

    # Insert 1000 events
    events = generate_realistic_events(1000, project_id)
    for event in events:
        store.record_event(event)

    # Benchmark: Search for "authentication"
    start = time.perf_counter()
    results = store.search_events(project_id, "authentication", limit=20)
    duration = time.perf_counter() - start

    assert len(results) > 0
    assert duration < 0.1, f"Search took {duration:.3f}s (expected < 0.1s)"

    print(f"\n✓ Text search in {duration*1000:.1f}ms ({len(results)} results)")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_spatial_hierarchy_build(episodic_store, spatial_store):
    """Benchmark building spatial hierarchy from events."""
    ep_store, project_id = episodic_store
    sp_store, _ = spatial_store

    # Insert 1000 events
    events = generate_realistic_events(1000, project_id)
    for event in events:
        ep_store.record_event(event)

    # Benchmark: Extract spatial contexts and build hierarchy
    start = time.perf_counter()

    file_paths = set()
    cursor = ep_store.db.conn.cursor()
    cursor.execute(
        "SELECT DISTINCT context_cwd, context_files FROM episodic_events WHERE project_id = ?",
        (project_id,)
    )

    for row in cursor.fetchall():
        if row["context_cwd"]:
            file_paths.add(row["context_cwd"])
        if row["context_files"]:
            files = json.loads(row["context_files"])
            file_paths.update(files)

    # Build and store spatial hierarchy for each path
    for path in file_paths:
        nodes = build_spatial_hierarchy(path)
        for node in nodes:
            sp_store.store_node(project_id, node)

    duration = time.perf_counter() - start

    assert len(file_paths) > 0
    assert duration < 2.0, f"Spatial build took {duration:.3f}s (expected < 2s)"

    print(f"\n✓ Built spatial hierarchy in {duration:.3f}s ({len(file_paths)} paths)")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_temporal_chain_creation(episodic_store):
    """Benchmark creating temporal chains."""
    store, project_id = episodic_store

    # Insert 1000 events
    events = generate_realistic_events(1000, project_id)
    event_ids = []
    for event in events:
        event_id = store.record_event(event)
        event_ids.append(event_id)

    # Fetch events back for temporal chain creation
    all_events = store.get_recent_events(project_id, hours=24*30, limit=1000)

    # Benchmark: Create temporal relations
    start = time.perf_counter()
    relations = create_temporal_relations(all_events)
    duration = time.perf_counter() - start

    # Store relations in database
    for relation in relations:
        store.create_event_relation(
            relation.from_event_id,
            relation.to_event_id,
            relation.relation_type,
            relation.strength
        )

    assert len(relations) > 0
    assert duration < 5.0, f"Relation creation took {duration:.3f}s (expected < 5s)"

    print(f"\n✓ Created {len(relations)} temporal relations in {duration:.3f}s")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_temporal_chain_traversal(episodic_store):
    """Benchmark traversing temporal chains."""
    store, project_id = episodic_store

    # Insert 1000 events and create relations
    events = generate_realistic_events(1000, project_id)
    event_ids = []
    for event in events:
        event_id = store.record_event(event)
        event_ids.append(event_id)

    all_events = store.get_recent_events(project_id, hours=24*30, limit=1000)
    relations = create_temporal_relations(all_events)

    for relation in relations:
        store.create_event_relation(
            relation.from_event_id,
            relation.to_event_id,
            relation.relation_type,
            relation.strength
        )

    # Benchmark: Traverse forward from a mid-point event
    mid_event_id = event_ids[len(event_ids) // 2]

    start = time.perf_counter()
    related = store.get_related_events(mid_event_id, direction='forward')
    duration = time.perf_counter() - start

    # Without indexes on event_relations, this will be SLOW
    print(f"\n⚠ Chain traversal took {duration*1000:.1f}ms ({len(related)} related events)")

    if duration > 0.5:
        print(f"  WARNING: Slow traversal detected! Add indexes to event_relations table")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_consolidation_candidate_selection(episodic_store):
    """Benchmark finding events for consolidation."""
    store, project_id = episodic_store

    # Insert 1000 events
    events = generate_realistic_events(1000, project_id)
    for event in events:
        store.record_event(event)

    # Benchmark: Find unconsolidated events in last 24 hours
    start = time.perf_counter()
    cutoff = datetime.now() - timedelta(hours=24)
    candidates = store.get_events_by_timeframe(
        project_id,
        cutoff,
        datetime.now(),
        consolidation_status='unconsolidated',
        limit=100
    )
    duration = time.perf_counter() - start

    assert duration < 0.1, f"Query took {duration:.3f}s (expected < 0.1s)"

    print(f"\n✓ Found consolidation candidates in {duration*1000:.1f}ms ({len(candidates)} events)")


# =============================================================================
# STRESS TESTS
# =============================================================================


@pytest.mark.slow
@pytest.mark.benchmark
def test_stress_5000_events(episodic_store):
    """Stress test with 5000 events."""
    store, project_id = episodic_store

    print("\n🔥 Stress test: Inserting 5000 events...")

    events = generate_realistic_events(5000, project_id)

    start = time.perf_counter()
    for event in events:
        store.record_event(event)
    insert_duration = time.perf_counter() - start

    print(f"  ✓ Insert: {insert_duration:.2f}s ({5000/insert_duration:.1f} events/sec)")

    # Query performance with large dataset
    start = time.perf_counter()
    recent = store.get_recent_events(project_id, hours=24*7, limit=100)
    query_duration = time.perf_counter() - start

    print(f"  ✓ Query recent: {query_duration*1000:.1f}ms")

    # Text search with large dataset
    start = time.perf_counter()
    results = store.search_events(project_id, "authentication", limit=20)
    search_duration = time.perf_counter() - start

    print(f"  ✓ Text search: {search_duration*1000:.1f}ms")

    assert insert_duration < 25.0, f"Insert too slow: {insert_duration:.2f}s"
    assert query_duration < 0.2, f"Query too slow: {query_duration:.3f}s"
    assert search_duration < 0.2, f"Search too slow: {search_duration:.3f}s"


# =============================================================================
# PROFILING HELPERS
# =============================================================================


@pytest.mark.slow
@pytest.mark.benchmark
def test_profile_query_plans(episodic_store):
    """Analyze SQLite query plans for common queries."""
    store, project_id = episodic_store

    # Insert sample events
    events = generate_realistic_events(100, project_id)
    for event in events:
        store.record_event(event)

    cursor = store.db.conn.cursor()

    print("\n📊 Query Plans Analysis:\n")

    # Query 1: Recent events
    query1 = """
        EXPLAIN QUERY PLAN
        SELECT * FROM episodic_events
        WHERE project_id = ? AND timestamp > ?
        ORDER BY timestamp DESC
        LIMIT 50
    """
    cutoff = int((datetime.now() - timedelta(hours=24)).timestamp())
    cursor.execute(query1, (project_id, cutoff))
    print("Query 1 - Recent events:")
    for row in cursor.fetchall():
        print(f"  {row}")

    # Query 2: Session events
    query2 = """
        EXPLAIN QUERY PLAN
        SELECT * FROM episodic_events
        WHERE session_id = ?
        ORDER BY timestamp ASC
    """
    cursor.execute(query2, ("session-1",))
    print("\nQuery 2 - Session events:")
    for row in cursor.fetchall():
        print(f"  {row}")

    # Query 3: Consolidation candidates
    query3 = """
        EXPLAIN QUERY PLAN
        SELECT * FROM episodic_events
        WHERE project_id = ? AND consolidation_status = 'unconsolidated'
        ORDER BY timestamp DESC
        LIMIT 100
    """
    cursor.execute(query3, (project_id,))
    print("\nQuery 3 - Consolidation candidates:")
    for row in cursor.fetchall():
        print(f"  {row}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
