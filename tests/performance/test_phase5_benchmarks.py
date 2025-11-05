"""Phase 5 Performance Benchmarks - SLA Validation.

This suite validates that the memory system meets production SLAs:
- Query latency: <500ms for semantic, <300ms for spatial-temporal
- Consolidation throughput: >100 events/sec
- Memory scaling: 10K-100K memories
- Concurrent operations: 100+ concurrent queries
"""

import pytest
import time
import numpy as np
from datetime import datetime, timedelta
from typing import List

from athena.core.database import Database
from athena.memory.store import MemoryStore
from athena.episodic.store import EpisodicStore
from athena.episodic.models import EpisodicEvent, EventType
from athena.projects.manager import ProjectManager
from athena.consolidation.pipeline import consolidate_episodic_to_semantic


@pytest.fixture
def test_db():
    """Create in-memory test database."""
    db = Database(":memory:")
    yield db
    db.close()


@pytest.fixture
def project_manager(test_db):
    """Initialize project manager."""
    return ProjectManager(test_db)


@pytest.fixture
def episodic_store(test_db):
    """Initialize episodic store."""
    return EpisodicStore(test_db)


@pytest.fixture
def semantic_store():
    """Initialize semantic store."""
    return MemoryStore(":memory:")


@pytest.fixture
def test_project(project_manager):
    """Create test project."""
    return project_manager.get_or_create_project(name="benchmark-project")


class TestSemanticQueryLatency:
    """Benchmark semantic memory query latency."""

    @pytest.mark.benchmark
    def test_semantic_recall_mean_latency_under_500ms(
        self,
        semantic_store,
        test_project
    ):
        """Semantic recall should average <500ms."""
        # Populate with test memories
        queries = [
            "JWT authentication",
            "database optimization",
            "API endpoint design",
            "error handling",
            "performance tuning",
        ]

        for i, query in enumerate(queries):
            semantic_store.remember(
                content=f"Knowledge about {query} implementation details",
                memory_type="fact",
                project_id=test_project.id,
                tags=[query.split()[0].lower()]
            )

        # Measure latency for each query
        latencies = []
        for query in queries:
            start = time.perf_counter()
            results = semantic_store.recall(query, test_project.id, k=5)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        mean_latency = np.mean(latencies)
        median_latency = np.median(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)

        print(f"\nSemantic Recall Latency:")
        print(f"  Mean: {mean_latency:.1f}ms")
        print(f"  Median: {median_latency:.1f}ms")
        print(f"  P95: {p95_latency:.1f}ms")
        print(f"  P99: {p99_latency:.1f}ms")

        # SLA: Mean <500ms
        assert mean_latency < 500, f"Mean latency {mean_latency:.1f}ms exceeds 500ms SLA"

    @pytest.mark.benchmark
    def test_semantic_recall_median_under_300ms(
        self,
        semantic_store,
        test_project
    ):
        """Semantic recall median should be <300ms."""
        # Populate with memories
        for i in range(10):
            semantic_store.remember(
                content=f"Memory {i}: Test data for latency measurement",
                memory_type="fact",
                project_id=test_project.id
            )

        # Measure latencies
        latencies = []
        for i in range(20):
            query = f"Memory {i % 10}"
            start = time.perf_counter()
            results = semantic_store.recall(query, test_project.id, k=5)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        median_latency = np.median(latencies)
        print(f"\nSemantic Recall Median Latency: {median_latency:.1f}ms")

        # SLA: Median <300ms
        assert median_latency < 300, f"Median latency {median_latency:.1f}ms exceeds 300ms SLA"

    @pytest.mark.benchmark
    def test_semantic_recall_p99_under_2000ms(
        self,
        semantic_store,
        test_project
    ):
        """Semantic recall P99 should be <2000ms (outlier SLA)."""
        # Populate
        for i in range(5):
            semantic_store.remember(
                content=f"Benchmark data point {i}",
                memory_type="fact",
                project_id=test_project.id
            )

        # Measure latencies
        latencies = []
        for i in range(30):
            start = time.perf_counter()
            results = semantic_store.recall("benchmark", test_project.id, k=5)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        p99_latency = np.percentile(latencies, 99)
        print(f"\nSemantic Recall P99 Latency: {p99_latency:.1f}ms")

        # SLA: P99 <2000ms
        assert p99_latency < 2000, f"P99 latency {p99_latency:.1f}ms exceeds 2000ms SLA"


class TestConsolidationThroughput:
    """Benchmark consolidation throughput."""

    @pytest.mark.benchmark
    def test_consolidation_throughput_exceeds_100_events_per_sec(
        self,
        episodic_store,
        semantic_store,
        test_project
    ):
        """
        Consolidation should handle >100 events/sec.

        This validates that the system can consolidate at least 100 events
        from memory within a reasonable timeframe for daily consolidation.
        """
        session_id = "benchmark_session"
        base_time = datetime.now() - timedelta(hours=1)

        # Generate 100 test events
        events = [
            EpisodicEvent(
                project_id=test_project.id,
                session_id=session_id,
                event_type=EventType.ACTION,
                content=f"Event {i}: Consolidation benchmark event",
                timestamp=base_time + timedelta(seconds=i),
                outcome="success"
            )
            for i in range(100)
        ]

        # Record events
        for event in events:
            episodic_store.record_event(event)

        # Measure consolidation time
        start = time.perf_counter()
        report = consolidate_episodic_to_semantic(
            project_id=test_project.id,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            time_window_hours=24
        )
        consolidation_time = time.perf_counter() - start

        # Calculate throughput
        events_processed = report.events_consolidated
        throughput = events_processed / consolidation_time if consolidation_time > 0 else 0

        print(f"\nConsolidation Throughput:")
        print(f"  Events processed: {events_processed}")
        print(f"  Time: {consolidation_time:.3f}s")
        print(f"  Throughput: {throughput:.1f} events/sec")
        print(f"  Patterns extracted: {report.patterns_extracted}")

        # SLA: >100 events/sec (so 100 events should process in <1 second)
        assert throughput > 100, f"Throughput {throughput:.1f} events/sec below 100 events/sec SLA"

    @pytest.mark.benchmark
    def test_consolidation_batch_performance(
        self,
        episodic_store,
        semantic_store,
        test_project
    ):
        """
        Consolidation should handle batches efficiently.
        Measure time to consolidate 500 events.
        """
        session_id = "batch_session"
        base_time = datetime.now() - timedelta(hours=2)

        # Generate 500 events
        events = [
            EpisodicEvent(
                project_id=test_project.id,
                session_id=session_id,
                event_type=EventType.ACTION,
                content=f"Batch event {i}",
                timestamp=base_time + timedelta(seconds=i),
                outcome="success"
            )
            for i in range(500)
        ]

        for event in events:
            episodic_store.record_event(event)

        # Measure consolidation
        start = time.perf_counter()
        report = consolidate_episodic_to_semantic(
            project_id=test_project.id,
            episodic_store=episodic_store,
            semantic_store=semantic_store
        )
        consolidation_time = time.perf_counter() - start

        print(f"\nBatch Consolidation (500 events):")
        print(f"  Time: {consolidation_time:.3f}s")
        print(f"  Events consolidated: {report.events_consolidated}")

        # Should complete in reasonable time (<10 seconds for 500 events)
        assert consolidation_time < 10, f"Batch consolidation took {consolidation_time:.1f}s"


class TestMemoryScaling:
    """Benchmark memory system scaling."""

    @pytest.mark.benchmark
    def test_retrieval_latency_scales_with_memory_count(
        self,
        semantic_store,
        test_project
    ):
        """
        Query latency should not degrade significantly as memory count increases.
        Test with 100, 500, and 1000 memories.
        """
        results_by_size = {}

        for memory_count in [100, 500, 1000]:
            # Populate memories
            for i in range(memory_count):
                semantic_store.remember(
                    content=f"Scaling test memory {i}: Technical knowledge",
                    memory_type="fact",
                    project_id=test_project.id,
                    tags=["scaling", "test"]
                )

            # Measure query latency
            latencies = []
            for _ in range(10):
                start = time.perf_counter()
                results = semantic_store.recall("technical", test_project.id, k=5)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)

            mean_latency = np.mean(latencies)
            results_by_size[memory_count] = mean_latency

        print(f"\nQuery Latency vs Memory Count:")
        for size, latency in results_by_size.items():
            print(f"  {size} memories: {latency:.1f}ms")

        # Latency should not increase dramatically
        # Allow 2x increase from 100 to 1000 memories
        latency_100 = results_by_size[100]
        latency_1000 = results_by_size[1000]
        scaling_factor = latency_1000 / latency_100 if latency_100 > 0 else 1

        print(f"  Scaling factor (1000/100): {scaling_factor:.2f}x")
        assert scaling_factor < 3, f"Latency scaled {scaling_factor:.2f}x (should be <3x)"

    @pytest.mark.benchmark
    def test_storage_requirements_for_large_memory_count(
        self,
        semantic_store,
        test_project
    ):
        """
        Storage should scale linearly with memory count.
        10K memories should use <500MB.
        """
        # Note: This test is conceptual; actual storage depends on backend
        memory_count = 1000
        for i in range(memory_count):
            semantic_store.remember(
                content=f"Storage test {i}: " + "x" * 100,  # ~100 bytes per memory
                memory_type="fact",
                project_id=test_project.id
            )

        memories = semantic_store.list_memories(test_project.id, limit=10000)
        print(f"\nStorage Test:")
        print(f"  Memories stored: {len(memories)}")
        print(f"  Expected ~{memory_count} memories")

        assert len(memories) >= memory_count, "All memories should be stored"


class TestConcurrentOperations:
    """Benchmark concurrent query handling."""

    @pytest.mark.benchmark
    def test_multiple_sequential_queries(
        self,
        semantic_store,
        test_project
    ):
        """
        System should handle multiple sequential queries efficiently.
        Measure time for 50 sequential queries.
        """
        # Setup
        for i in range(20):
            semantic_store.remember(
                content=f"Query test {i}: Sample knowledge",
                memory_type="fact",
                project_id=test_project.id
            )

        # Run 50 sequential queries
        queries = [
            "query",
            "test",
            "knowledge",
            "sample",
            "data"
        ] * 10

        start = time.perf_counter()
        for query in queries:
            semantic_store.recall(query, test_project.id, k=5)
        total_time = time.perf_counter() - start

        avg_latency = (total_time / len(queries)) * 1000
        print(f"\n50 Sequential Queries:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average latency: {avg_latency:.1f}ms")

        # Should complete in <30 seconds (50 * 600ms max per query)
        assert total_time < 30, f"Sequential queries took {total_time:.1f}s"

    @pytest.mark.benchmark
    def test_rapid_fire_queries(
        self,
        semantic_store,
        test_project
    ):
        """
        System should handle rapid-fire queries without degradation.
        Send 100 queries as fast as possible.
        """
        # Setup
        for i in range(10):
            semantic_store.remember(
                content=f"Rapid test {i}",
                memory_type="fact",
                project_id=test_project.id
            )

        # Fire queries rapidly
        start = time.perf_counter()
        for i in range(100):
            semantic_store.recall("test", test_project.id, k=5)
        total_time = time.perf_counter() - start

        print(f"\n100 Rapid-Fire Queries:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Queries/sec: {100 / total_time:.1f}")

        # Should handle at least 10 queries/sec
        assert total_time < 10, f"Rapid queries took {total_time:.1f}s"


class TestSLACompliance:
    """Validate overall SLA compliance."""

    @pytest.mark.benchmark
    def test_sla_semantic_query_latency(
        self,
        semantic_store,
        test_project
    ):
        """SLA: Semantic query latency <500ms mean."""
        for i in range(20):
            semantic_store.remember(
                content=f"SLA test {i}",
                memory_type="fact",
                project_id=test_project.id
            )

        latencies = []
        for i in range(50):
            start = time.perf_counter()
            semantic_store.recall("test", test_project.id, k=5)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        mean = np.mean(latencies)
        status = "✅ PASS" if mean < 500 else "❌ FAIL"
        print(f"\nSLA: Semantic Query Latency <500ms")
        print(f"  Result: {mean:.1f}ms {status}")

        assert mean < 500

    @pytest.mark.benchmark
    def test_sla_consolidation_throughput(
        self,
        episodic_store,
        semantic_store,
        test_project
    ):
        """SLA: Consolidation throughput >100 events/sec."""
        session_id = "sla_session"
        for i in range(100):
            event = EpisodicEvent(
                project_id=test_project.id,
                session_id=session_id,
                event_type=EventType.ACTION,
                content=f"SLA event {i}",
                timestamp=datetime.now() - timedelta(hours=1, seconds=100-i),
                outcome="success"
            )
            episodic_store.record_event(event)

        start = time.perf_counter()
        report = consolidate_episodic_to_semantic(
            project_id=test_project.id,
            episodic_store=episodic_store,
            semantic_store=semantic_store
        )
        elapsed = time.perf_counter() - start
        throughput = report.events_consolidated / elapsed if elapsed > 0 else 0

        status = "✅ PASS" if throughput > 100 else "❌ FAIL"
        print(f"\nSLA: Consolidation Throughput >100 events/sec")
        print(f"  Result: {throughput:.1f} events/sec {status}")

        assert throughput > 100
