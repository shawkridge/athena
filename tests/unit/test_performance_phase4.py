"""Performance tests for Phase 4 optimization."""

import tempfile
import time
from pathlib import Path

import pytest

from athena.core.database import Database
from athena.performance import (
    BatchExecutor,
    BulkInsertBuilder,
    EntityCache,
    LRUCache,
    PerformanceMonitor,
    QueryCache,
    QueryOptimizer,
    get_monitor,
    timer,
)


@pytest.fixture
def tmp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db = Database(Path(tmp_dir) / "test.db")
        yield db


class TestLRUCache:
    """Test LRU cache performance."""

    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        cache = LRUCache(max_size=100)

        # Set value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_hit_rate(self):
        """Test cache hit rate tracking."""
        cache = LRUCache(max_size=10)

        # Populate cache
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")

        # Access same keys multiple times
        for _ in range(100):
            for i in range(10):
                assert cache.get(f"key{i}") is not None

        stats = cache.get_stats()
        assert stats["hit_rate"] > 0.9

    def test_cache_eviction(self):
        """Test LRU eviction when cache full."""
        cache = LRUCache(max_size=3)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Add one more (should evict key1)
        cache.set("key4", "value4")

        # key1 should be gone
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        cache = LRUCache(max_size=100, default_ttl_seconds=1)

        cache.set("key1", "value1", ttl_seconds=1)
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None


class TestQueryCache:
    """Test query result caching."""

    def test_query_cache_basic(self):
        """Test basic query caching."""
        qcache = QueryCache()

        query = "SELECT * FROM users WHERE id = ?"
        params = (42,)
        result = [{"id": 42, "name": "Alice"}]

        # First call - not cached
        cached = qcache.get(query, params)
        assert cached is None

        # Store result
        qcache.set(query, params, result)

        # Second call - should be cached
        cached = qcache.get(query, params)
        assert cached == result

    def test_query_cache_hit_rate(self):
        """Test query cache hit rate."""
        qcache = QueryCache()

        query = "SELECT * FROM users WHERE status = ?"
        params = ("active",)
        result = [{"id": 1, "status": "active"}]

        # Cache the result
        qcache.set(query, params, result)

        # Access multiple times
        for _ in range(100):
            assert qcache.get(query, params) == result

        stats = qcache.get_stats()
        assert stats["hit_rate"] > 0.99


class TestEntityCache:
    """Test entity caching."""

    def test_entity_cache_basic(self):
        """Test basic entity caching."""
        ecache = EntityCache(max_entities=100)

        entity = {"id": 42, "name": "function", "type": "FUNCTION"}
        ecache.set(42, entity, file_path="src/module.py", entity_type="FUNCTION")

        cached = ecache.get(42)
        assert cached == entity

    def test_entity_cache_by_file(self):
        """Test entity lookup by file."""
        ecache = EntityCache(max_entities=100)

        # Add entities to same file
        for i in range(5):
            entity = {"id": i, "name": f"entity{i}"}
            ecache.set(i, entity, file_path="src/module.py")

        # Retrieve by file
        entities = ecache.get_by_file("src/module.py")
        assert len(entities) == 5
        assert all(eid in entities for eid in range(5))

    def test_entity_cache_invalidation(self):
        """Test cache invalidation by file."""
        ecache = EntityCache(max_entities=100)

        for i in range(5):
            entity = {"id": i}
            ecache.set(i, entity, file_path="src/module.py")

        # Invalidate file
        ecache.invalidate_file("src/module.py")

        # Entities should be gone
        assert len(ecache.get_by_file("src/module.py")) == 0


class TestBatchExecutor:
    """Test batch operations."""

    def test_batch_insert_basic(self, tmp_db):
        """Test basic batch insert."""
        # Create table
        tmp_db.conn.execute(
            "CREATE TABLE test_data (id INTEGER PRIMARY KEY, value TEXT)"
        )
        tmp_db.conn.commit()

        # Batch insert
        executor = BatchExecutor(tmp_db, batch_size=100)
        for i in range(10):
            sql = "INSERT INTO test_data (value) VALUES (?)"
            executor.add_insert(sql, [f"value{i}"])

        result = executor.execute(silent=True)
        assert result["success"] is True

        # Verify data
        cursor = tmp_db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_data")
        count = cursor.fetchone()[0]
        assert count == 10

    @pytest.mark.skip(reason="Flaky timing test - depends on system load")
    def test_batch_throughput(self, tmp_db):
        """Test batch throughput improvement."""
        tmp_db.conn.execute(
            "CREATE TABLE perf_test (id INTEGER PRIMARY KEY, value TEXT)"
        )
        tmp_db.conn.commit()

        # Individual inserts
        start = time.time()
        cursor = tmp_db.conn.cursor()
        for i in range(100):
            cursor.execute("INSERT INTO perf_test (value) VALUES (?)", (f"val{i}",))
        tmp_db.conn.commit()
        individual_time = (time.time() - start) * 1000

        # Clear table
        tmp_db.conn.execute("DELETE FROM perf_test")
        tmp_db.conn.commit()

        # Batch insert
        start = time.time()
        executor = BatchExecutor(tmp_db, batch_size=100)
        for i in range(100):
            executor.add_insert(
                "INSERT INTO perf_test (value) VALUES (?)",
                [f"val{i}"],
            )
        executor.execute(silent=True)
        batch_time = (time.time() - start) * 1000

        # Batch should be faster
        assert batch_time < individual_time
        print(f"Individual: {individual_time:.2f}ms, Batch: {batch_time:.2f}ms")


class TestBulkInsertBuilder:
    """Test bulk insert builder."""

    def test_bulk_insert_builder(self, tmp_db):
        """Test bulk insert builder."""
        tmp_db.conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
        )
        tmp_db.conn.commit()

        builder = BulkInsertBuilder("users", ["name", "email"])
        builder.add_row("Alice", "alice@example.com")
        builder.add_row("Bob", "bob@example.com")
        builder.add_row("Charlie", "charlie@example.com")

        result = builder.execute(tmp_db)
        assert result["success"] is True
        assert result["rows"] == 3

        # Verify data
        cursor = tmp_db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        assert cursor.fetchone()[0] == 3


class TestPerformanceMonitor:
    """Test performance monitoring."""

    def test_monitor_basic(self):
        """Test basic monitoring."""
        monitor = PerformanceMonitor()

        monitor.record_operation("query1", 10.5)
        monitor.record_operation("query1", 15.2)

        stats = monitor.get_metric("query1")
        assert stats["count"] == 2
        assert 10.5 < stats["average"] < 15.2

    def test_monitor_with_timer(self):
        """Test monitoring with timer context manager."""
        monitor = PerformanceMonitor()

        with monitor.timer("operation1"):
            time.sleep(0.01)  # 10ms

        stats = monitor.get_metric("operation1")
        assert stats["count"] == 1
        assert stats["average"] >= 10  # At least 10ms

    def test_monitor_summary(self):
        """Test monitoring summary."""
        monitor = PerformanceMonitor()

        for i in range(10):
            monitor.record_operation("op1", 5.0)

        summary = monitor.get_summary()
        assert summary["total_operations"] == 10
        assert summary["operations_per_second"] > 0

    def test_global_monitor(self):
        """Test global monitor instance."""
        monitor = get_monitor()

        with timer("test_operation"):
            time.sleep(0.005)

        stats = monitor.get_metric("test_operation")
        assert stats is not None


class TestQueryOptimizer:
    """Test query optimization."""

    def test_index_creation(self, tmp_db):
        """Test index creation."""
        # Create test table
        tmp_db.conn.execute(
            "CREATE TABLE test_table (id INTEGER, name TEXT, email TEXT)"
        )
        tmp_db.conn.commit()

        optimizer = QueryOptimizer(tmp_db)

        # Create some indexes
        result = optimizer.create_indexes()

        assert result["created"] > 0 or result["skipped"] > 0

    def test_performance_analysis(self, tmp_db):
        """Test performance analysis."""
        tmp_db.conn.execute(
            "CREATE TABLE analysis_test (id INTEGER, value TEXT)"
        )
        tmp_db.conn.commit()

        optimizer = QueryOptimizer(tmp_db)
        stats = optimizer.analyze_performance()

        assert "tables" in stats
        assert "indexes" in stats


class TestCacheIntegration:
    """Test caching integration scenarios."""

    def test_multi_level_cache(self):
        """Test multi-level caching strategy."""
        # L1: Query cache
        qcache = QueryCache(max_queries=100)

        # L2: Entity cache
        ecache = EntityCache(max_entities=1000)

        # Populate caches
        query = "SELECT * FROM entities"
        params = ()
        result = [{"id": 1}, {"id": 2}]

        qcache.set(query, params, result)
        for entity in result:
            ecache.set(entity["id"], entity)

        # Access from cache
        cached_result = qcache.get(query, params)
        assert cached_result == result

        cached_entity = ecache.get(1)
        assert cached_entity == {"id": 1}

    def test_cache_warming(self):
        """Test cache warming."""
        cache = LRUCache(max_size=100)

        # Warm up cache
        data = {f"key{i}": f"value{i}" for i in range(50)}
        cache.warmup(data)

        stats = cache.get_stats()
        assert stats["size"] == 50
