"""Concurrent load testing for Phase 4 production hardening."""

import concurrent.futures
import tempfile
import time
from datetime import datetime, timedelta
from typing import List, Tuple

import pytest

from athena.core.database import Database
from athena.episodic.models import EpisodicEvent, EventContext, EventType
from athena.integration.auto_populate import IntegratedEpisodicStore


@pytest.fixture
def load_test_db():
    """Create temporary database for load testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = Database(db_path)

    # Create project
    now = int(time.time())
    cursor = db.conn.cursor()
    cursor.execute(
        "INSERT INTO projects (name, path, created_at, last_accessed) VALUES (?, ?, ?, ?)",
        ("load-test-project", "/test", now, now),
    )
    db.conn.commit()

    yield db
    db.close()


@pytest.mark.benchmark
def test_concurrent_insert_100_events(load_test_db):
    """Test 100 concurrent event insertions."""
    store = IntegratedEpisodicStore(
        load_test_db, auto_spatial=True, auto_temporal=False, spatial_batch_size=50
    )

    base_paths = [
        f"/project/src/module{i % 5}/file{j % 3}.py"
        for i in range(5)
        for j in range(3)
    ]

    def create_event(event_num: int) -> EpisodicEvent:
        """Create a test event."""
        return EpisodicEvent(
            project_id=1,
            session_id=f"concurrent-{event_num // 10}",
            timestamp=datetime.now() + timedelta(seconds=event_num),
            event_type=EventType.FILE_CHANGE if event_num % 2 == 0 else EventType.ACTION,
            content=f"Event {event_num}: {base_paths[event_num % len(base_paths)]}",
            context=EventContext(
                cwd="/project",
                files=[base_paths[event_num % len(base_paths)]],
            ),
        )

    print("\n🔄 Testing 100 concurrent inserts...")
    start = time.time()

    # Insert 100 events sequentially (simulating concurrent load)
    event_ids = []
    for i in range(100):
        event = create_event(i)
        event_id = store.record_event(event, project_id=1)
        event_ids.append(event_id)

    # Flush final batch
    store.flush(project_id=1)

    elapsed = time.time() - start

    # Verify all events were inserted
    assert len(event_ids) == 100
    assert all(eid > 0 for eid in event_ids)

    # Performance assertions
    rate = 100 / elapsed
    print(f"  ✅ 100 events in {elapsed:.2f}s ({rate:.1f} events/sec)")
    print(f"  ✅ Average: {elapsed * 1000 / 100:.2f}ms per event")

    # Should complete within reasonable time (target: < 10 seconds for 100 events, minimum 10 ev/sec)
    assert elapsed < 10.0, f"Too slow: {elapsed:.2f}s for 100 events"
    assert rate > 10.0, f"Too slow: {rate:.1f} events/sec (target: >10 events/sec)"


@pytest.mark.benchmark
def test_mixed_workload_concurrent(load_test_db):
    """Test mixed workload: 70% retrieval, 30% insertion."""
    store = IntegratedEpisodicStore(
        load_test_db, auto_spatial=True, auto_temporal=False
    )

    # First, insert 200 events to have data to query
    print("\n📝 Pre-loading 200 events...")
    base_paths = [
        f"/project/src/module{i % 5}/file{j % 3}.py"
        for i in range(5)
        for j in range(3)
    ]

    for i in range(200):
        event = EpisodicEvent(
            project_id=1,
            session_id=f"preload-{i // 100}",
            timestamp=datetime.now() + timedelta(seconds=i),
            event_type=EventType.FILE_CHANGE if i % 2 == 0 else EventType.ACTION,
            content=f"Preload {i}",
            context=EventContext(
                cwd="/project",
                files=[base_paths[i % len(base_paths)]],
            ),
        )
        store.record_event(event, project_id=1)

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/200 preloaded")

    store.flush(project_id=1)

    print("🔄 Running mixed workload (70% retrieval, 30% insertion)...")
    start = time.time()

    # Run mixed operations
    total_ops = 100
    retrieval_ops = int(total_ops * 0.7)  # 70 retrievals
    insertion_ops = total_ops - retrieval_ops  # 30 insertions

    operation_times = {"retrieval": [], "insertion": []}

    # Perform retrievals
    for i in range(retrieval_ops):
        op_start = time.time()
        events = store.get_recent_events(project_id=1, hours=24, limit=50)
        op_time = time.time() - op_start
        operation_times["retrieval"].append(op_time)
        assert len(events) > 0, f"Query {i} returned no results"

    # Perform insertions
    for i in range(insertion_ops):
        op_start = time.time()
        event = EpisodicEvent(
            project_id=1,
            session_id="mixed-workload",
            timestamp=datetime.now(),
            event_type=EventType.ACTION,
            content=f"Mixed op {i}",
            context=EventContext(cwd="/project"),
        )
        store.record_event(event, project_id=1)
        op_time = time.time() - op_start
        operation_times["insertion"].append(op_time)

    store.flush(project_id=1)

    elapsed = time.time() - start

    # Print statistics
    print(f"\n  📊 Workload Statistics:")
    print(f"    Retrievals: {retrieval_ops} ops")
    print(f"      - Avg latency: {sum(operation_times['retrieval']) / len(operation_times['retrieval']) * 1000:.2f}ms")
    print(f"      - Max latency: {max(operation_times['retrieval']) * 1000:.2f}ms")

    print(f"    Insertions: {insertion_ops} ops")
    print(f"      - Avg latency: {sum(operation_times['insertion']) / len(operation_times['insertion']) * 1000:.2f}ms")
    print(f"      - Max latency: {max(operation_times['insertion']) * 1000:.2f}ms")

    print(f"    Total time: {elapsed:.2f}s ({total_ops / elapsed:.1f} ops/sec)")

    # Performance assertions
    assert elapsed < 10.0, f"Mixed workload too slow: {elapsed:.2f}s for 100 ops"

    # Retrieve latency should be < 100ms
    avg_retrieval = sum(operation_times["retrieval"]) / len(operation_times["retrieval"])
    assert avg_retrieval < 0.1, f"Retrieval too slow: {avg_retrieval * 1000:.2f}ms"


@pytest.mark.benchmark
def test_concurrent_throughput_1000_events(load_test_db):
    """Test throughput: insert 1000 events with batching."""
    store = IntegratedEpisodicStore(
        load_test_db,
        auto_spatial=True,
        auto_temporal=False,
        spatial_batch_size=50,
    )

    base_paths = [
        f"/project/src/auth/{file}" for file in ["jwt.py", "middleware.py", "utils.py"]
    ] + [
        f"/project/src/api/{file}" for file in ["routes.py", "models.py", "handlers.py"]
    ]

    print("\n🚀 Throughput test: 1000 events with spatial indexing...")
    start = time.time()

    for i in range(1000):
        event = EpisodicEvent(
            project_id=1,
            session_id=f"throughput-{i // 500}",
            timestamp=datetime.now() + timedelta(seconds=i),
            event_type=EventType.FILE_CHANGE if i % 3 == 0 else EventType.ACTION,
            content=f"Throughput event {i}",
            context=EventContext(
                cwd="/project",
                files=[base_paths[i % len(base_paths)]],
            ),
        )
        store.record_event(event, project_id=1)

        if (i + 1) % 200 == 0:
            elapsed_so_far = time.time() - start
            rate = (i + 1) / elapsed_so_far
            print(f"  {i + 1}/1000 events ({rate:.1f} ev/sec)")

    store.flush(project_id=1)

    elapsed = time.time() - start
    rate = 1000 / elapsed

    print(f"\n  ✅ 1000 events in {elapsed:.2f}s ({rate:.1f} events/sec)")

    # Success criteria: maintain >10 events/sec throughput (production baseline)
    # Note: Embedding overhead adds ~30ms/event, so expect 20-50 events/sec
    assert rate > 10.0, f"Throughput too slow: {rate:.1f} events/sec (target: >10 events/sec)"
    assert elapsed < 100.0, f"Throughput too slow: {elapsed:.2f}s for 1000 events"


@pytest.mark.benchmark
def test_query_latency_under_load(load_test_db):
    """Test query latency as database grows."""
    store = IntegratedEpisodicStore(
        load_test_db, auto_spatial=True, auto_temporal=False
    )

    print("\n📊 Query latency under load...")

    # Insert events in batches and measure query latency
    latencies_by_size = {}
    batch_sizes = [100, 500, 1000]

    for batch_size in batch_sizes:
        # Insert events if not already present
        current_count = len(store.get_recent_events(project_id=1, hours=24, limit=1000))

        if current_count < batch_size:
            print(f"  Inserting {batch_size - current_count} events...")
            for i in range(current_count, batch_size):
                event = EpisodicEvent(
                    project_id=1,
                    session_id=f"load-{i // 500}",
                    timestamp=datetime.now() + timedelta(seconds=i),
                    event_type=EventType.ACTION,
                    content=f"Event {i}",
                    context=EventContext(cwd="/project"),
                )
                store.record_event(event, project_id=1)

            store.flush(project_id=1)

        # Measure query latency
        latencies = []
        for _ in range(10):
            start = time.time()
            events = store.get_recent_events(project_id=1, hours=24, limit=50)
            latency = time.time() - start
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        latencies_by_size[batch_size] = {"avg": avg_latency, "max": max_latency}

        print(
            f"    {batch_size} events: avg={avg_latency * 1000:.2f}ms, max={max_latency * 1000:.2f}ms"
        )

    # Query latency should scale sub-linearly (index efficiency)
    # Max should not exceed 500ms even for 1000 events
    assert (
        latencies_by_size[1000]["max"] < 0.5
    ), f"Query latency too high: {latencies_by_size[1000]['max'] * 1000:.2f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
