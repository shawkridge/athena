"""Performance benchmarks for consolidation pipeline.

Tests the episodic→semantic consolidation system at scale.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from athena.consolidation.pipeline import consolidate_episodic_to_semantic
from athena.consolidation.clustering import cluster_events_by_context
from athena.consolidation.pattern_extraction import extract_patterns
from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventType, EventContext, EventOutcome
from athena.episodic.store import EpisodicStore
from athena.memory.store import MemoryStore
from athena.projects.manager import ProjectManager


@pytest.fixture
def perf_db(tmp_path):
    """Create database for performance testing."""
    db_path = tmp_path / "consolidation_perf.db"
    db = Database(db_path)
    yield db
    db.close()


@pytest.fixture
def project_manager(perf_db):
    """Initialize project manager."""
    return ProjectManager(perf_db)


@pytest.fixture
def test_project(project_manager):
    """Create test project."""
    return project_manager.get_or_create_project(name="perf-test-project")


@pytest.fixture
def episodic_store(perf_db):
    """Initialize episodic store."""
    return EpisodicStore(perf_db)


@pytest.fixture
def semantic_store(tmp_path):
    """Initialize semantic store."""
    db_path = tmp_path / "semantic_perf.db"
    return MemoryStore(str(db_path))


def generate_consolidation_events(count: int, project_id: int, base_time: datetime = None):
    """Generate events suitable for consolidation testing.

    Creates events in clusters (sessions) to enable pattern extraction.
    """
    if base_time is None:
        base_time = datetime.now() - timedelta(days=7)

    events = []
    sessions_count = count // 20  # ~20 events per session

    # Define repeating workflow patterns
    workflows = [
        {
            "task": "Implement authentication",
            "phase": "auth-refactor",
            "files": ["/project/src/auth/middleware.py", "/project/src/auth/jwt.py"],
            "steps": [
                ("FILE_CHANGE", "Modified authentication middleware", "success"),
                ("ACTION", "Added JWT token validation", "success"),
                ("TEST_RUN", "Authentication tests passing", "success"),
                ("DECISION", "Chose JWT over sessions", "success"),
            ]
        },
        {
            "task": "Fix database performance",
            "phase": "optimization",
            "files": ["/project/src/database/queries.py", "/project/src/database/indexes.py"],
            "steps": [
                ("ERROR", "Slow query detected", "failure"),
                ("ACTION", "Added database index", "success"),
                ("TEST_RUN", "Performance improved 10x", "success"),
            ]
        },
        {
            "task": "Add API endpoint",
            "phase": "api-development",
            "files": ["/project/src/api/users.py", "/project/tests/test_api.py"],
            "steps": [
                ("FILE_CHANGE", "Created new API endpoint", "success"),
                ("ACTION", "Added input validation", "success"),
                ("TEST_RUN", "All API tests passing", "success"),
            ]
        },
    ]

    event_idx = 0
    for session_idx in range(sessions_count):
        session_id = f"session-{session_idx}"
        workflow = workflows[session_idx % len(workflows)]

        # Session start time
        session_start = base_time + timedelta(hours=session_idx * 2)

        # Generate events for this session's workflow
        for step_idx, (event_type_str, content, outcome_str) in enumerate(workflow["steps"]):
            if event_idx >= count:
                break

            event_time = session_start + timedelta(minutes=step_idx * 15)

            events.append(EpisodicEvent(
                project_id=project_id,
                session_id=session_id,
                event_type=EventType(event_type_str.lower()),
                content=content,
                context=EventContext(
                    cwd=workflow["files"][0].rsplit("/", 1)[0],
                    files=workflow["files"],
                    task=workflow["task"],
                    phase=workflow["phase"]
                ),
                timestamp=event_time,
                outcome=EventOutcome(outcome_str),
                files_changed=len(workflow["files"]),
                lines_added=50 if "added" in content.lower() else 0,
                lines_deleted=10 if "modified" in content.lower() else 0
            ))

            event_idx += 1

    return events[:count]


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_clustering_1000_events(episodic_store, test_project):
    """Benchmark event clustering with 1000 events."""
    # Insert 1000 events
    events = generate_consolidation_events(1000, test_project.id)
    for event in events:
        episodic_store.record_event(event)

    # Fetch events back
    all_events = episodic_store.get_recent_events(test_project.id, hours=24*7, limit=1000)

    # Benchmark: Cluster events
    start = time.perf_counter()
    clusters = cluster_events_by_context(all_events)
    duration = time.perf_counter() - start

    assert len(clusters) > 0
    assert duration < 1.0, f"Clustering took {duration:.3f}s (expected < 1s)"

    print(f"\n✓ Clustered {len(all_events)} events into {len(clusters)} clusters in {duration*1000:.1f}ms")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_pattern_extraction_from_clusters(episodic_store, test_project):
    """Benchmark pattern extraction from event clusters."""
    # Insert 1000 events
    events = generate_consolidation_events(1000, test_project.id)
    for event in events:
        episodic_store.record_event(event)

    # Fetch and cluster events
    all_events = episodic_store.get_recent_events(test_project.id, hours=24*7, limit=1000)
    clusters = cluster_events_by_context(all_events)

    # Benchmark: Extract patterns from clusters
    start = time.perf_counter()
    patterns = []
    for cluster in clusters:
        cluster_patterns = extract_patterns(cluster)
        patterns.extend(cluster_patterns)
    duration = time.perf_counter() - start

    assert len(patterns) > 0
    assert duration < 5.0, f"Pattern extraction took {duration:.3f}s (expected < 5s)"

    print(f"\n✓ Extracted {len(patterns)} patterns from {len(clusters)} clusters in {duration:.2f}s")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_full_consolidation_pipeline(episodic_store, semantic_store, test_project):
    """Benchmark complete consolidation pipeline with 1000 events."""
    # Insert 1000 events
    events = generate_consolidation_events(1000, test_project.id)
    for event in events:
        episodic_store.record_event(event)

    # Benchmark: Full consolidation pipeline
    start = time.perf_counter()
    report = consolidate_episodic_to_semantic(
        project_id=test_project.id,
        episodic_store=episodic_store,
        semantic_store=semantic_store,
        time_window_hours=24*7
    )
    duration = time.perf_counter() - start

    assert report is not None
    assert report.patterns_extracted > 0
    assert duration < 10.0, f"Full consolidation took {duration:.2f}s (expected < 10s)"

    print(f"\n✓ Full consolidation completed in {duration:.2f}s")
    print(f"  - Events processed: {report.events_processed}")
    print(f"  - Events consolidated: {report.events_consolidated}")
    print(f"  - Patterns extracted: {report.patterns_extracted}")
    print(f"  - Quality improvement: {report.quality_improvement:.1%}")


@pytest.mark.slow
@pytest.mark.benchmark
def test_benchmark_incremental_consolidation(episodic_store, semantic_store, test_project):
    """Benchmark incremental consolidation (realistic usage pattern)."""
    # Simulate daily consolidation: 100 new events per day for 10 days
    print("\n🔄 Incremental consolidation benchmark (10 days, 100 events/day):\n")

    total_duration = 0
    base_time = datetime.now() - timedelta(days=10)

    for day in range(10):
        # Generate events for this day
        day_start = base_time + timedelta(days=day)
        events = generate_consolidation_events(100, test_project.id, day_start)

        for event in events:
            episodic_store.record_event(event)

        # Run consolidation for last 24 hours
        start = time.perf_counter()
        report = consolidate_episodic_to_semantic(
            project_id=test_project.id,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            time_window_hours=24
        )
        duration = time.perf_counter() - start
        total_duration += duration

        print(f"  Day {day+1}: {duration*1000:.1f}ms ({report.events_processed} events, {report.patterns_extracted} patterns)")

        # Mark events as consolidated
        for event in events:
            episodic_store.mark_event_consolidated(event.id)

    avg_duration = total_duration / 10
    print(f"\n✓ Average daily consolidation: {avg_duration*1000:.1f}ms")
    assert avg_duration < 2.0, f"Avg consolidation took {avg_duration:.3f}s (expected < 2s)"


@pytest.mark.slow
@pytest.mark.benchmark
def test_stress_consolidation_5000_events(episodic_store, semantic_store, test_project):
    """Stress test: Consolidate 5000 events at once."""
    print("\n🔥 Stress test: Consolidating 5000 events...")

    # Insert 5000 events
    events = generate_consolidation_events(5000, test_project.id)

    insert_start = time.perf_counter()
    for event in events:
        episodic_store.record_event(event)
    insert_duration = time.perf_counter() - insert_start

    print(f"  ✓ Inserted 5000 events in {insert_duration:.2f}s")

    # Run consolidation
    consolidation_start = time.perf_counter()
    report = consolidate_episodic_to_semantic(
        project_id=test_project.id,
        episodic_store=episodic_store,
        semantic_store=semantic_store,
        time_window_hours=24*30
    )
    consolidation_duration = time.perf_counter() - consolidation_start

    print(f"  ✓ Consolidated in {consolidation_duration:.2f}s")
    print(f"    - Events: {report.events_processed}")
    print(f"    - Clusters: {report.clusters_formed}")
    print(f"    - Patterns: {report.patterns_extracted}")
    print(f"    - Memories: {report.memories_created}")

    assert consolidation_duration < 30.0, f"Consolidation took {consolidation_duration:.2f}s (expected < 30s)"

    # Check memory quality
    memories = semantic_store.list_memories(test_project.id, limit=1000)
    print(f"    - Semantic memories stored: {len(memories)}")


@pytest.mark.slow
@pytest.mark.benchmark
def test_profile_consolidation_bottlenecks(episodic_store, semantic_store, test_project):
    """Profile consolidation to identify bottlenecks."""
    print("\n📊 Consolidation bottleneck analysis:\n")

    # Insert 500 events
    events = generate_consolidation_events(500, test_project.id)
    for event in events:
        episodic_store.record_event(event)

    all_events = episodic_store.get_recent_events(test_project.id, hours=24*7, limit=500)

    # Profile: Event fetching
    fetch_start = time.perf_counter()
    all_events = episodic_store.get_recent_events(test_project.id, hours=24*7, limit=500)
    fetch_duration = time.perf_counter() - fetch_start
    print(f"  Event fetching: {fetch_duration*1000:.1f}ms")

    # Profile: Clustering
    cluster_start = time.perf_counter()
    clusters = cluster_events_by_context(all_events)
    cluster_duration = time.perf_counter() - cluster_start
    print(f"  Event clustering: {cluster_duration*1000:.1f}ms ({len(clusters)} clusters)")

    # Profile: Pattern extraction
    pattern_start = time.perf_counter()
    all_patterns = []
    for cluster in clusters:
        cluster_patterns = extract_patterns(cluster)
        all_patterns.extend(cluster_patterns)
    pattern_duration = time.perf_counter() - pattern_start
    print(f"  Pattern extraction: {pattern_duration*1000:.1f}ms ({len(all_patterns)} patterns)")

    # Profile: Memory storage
    storage_start = time.perf_counter()
    for pattern in all_patterns[:10]:  # Store first 10 patterns
        semantic_store.create_memory(
            project_id=test_project.id,
            content=str(pattern),
            memory_type="pattern"
        )
    storage_duration = time.perf_counter() - storage_start
    print(f"  Memory storage: {storage_duration*1000:.1f}ms (10 memories)")

    total = fetch_duration + cluster_duration + pattern_duration + storage_duration
    print(f"\n  Total time: {total*1000:.1f}ms")
    print(f"  Breakdown: Fetch {fetch_duration/total*100:.1f}%, Cluster {cluster_duration/total*100:.1f}%, "
          f"Extract {pattern_duration/total*100:.1f}%, Store {storage_duration/total*100:.1f}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
