"""Unit tests for Phase 2 performance optimizations.

Tests for:
1. Connection pooling (connection_pool.py)
2. Query result caching (query_cache.py)
3. Performance profiling (performance_profiler.py)
"""

import pytest
import sys
import os
import time
import tempfile
from pathlib import Path

# Add hooks lib to path
hooks_lib_path = Path(__file__).parent.parent.parent / "claude" / "hooks" / "lib"
sys.path.insert(0, str(hooks_lib_path))


class TestConnectionPool:
    """Tests for connection pooling."""

    def test_singleton_pattern(self):
        """Test that ConnectionPool is a singleton."""
        from connection_pool import get_connection_pool

        pool1 = get_connection_pool()
        pool2 = get_connection_pool()

        assert pool1 is pool2, "ConnectionPool should be a singleton"

    def test_pool_initialization(self):
        """Test pool initializes with correct settings."""
        from connection_pool import ConnectionPool

        pool = ConnectionPool()

        assert pool.MIN_CONNECTIONS == 1
        assert pool.MAX_CONNECTIONS == 3
        assert pool.IDLE_TIMEOUT == 300

    def test_get_stats(self):
        """Test pool statistics collection."""
        from connection_pool import get_connection_pool

        pool = get_connection_pool()
        stats = pool.get_stats()

        assert "total_connections" in stats
        assert "available_connections" in stats
        assert "in_use_connections" in stats
        assert "max_connections" in stats

        assert stats["max_connections"] == 3


class TestQueryCache:
    """Tests for query result caching."""

    def test_cache_key_hash_deterministic(self):
        """Test that cache keys produce deterministic hashes."""
        from query_cache import QueryCacheKey

        query = "SELECT * FROM table WHERE id = ?"
        params = (1, 2, 3)

        key1 = QueryCacheKey(query, params)
        key2 = QueryCacheKey(query, params)

        assert key1.hash_key == key2.hash_key
        assert hash(key1) == hash(key2)

    def test_cache_key_different_params(self):
        """Test that different params produce different keys."""
        from query_cache import QueryCacheKey

        query = "SELECT * FROM table WHERE id = ?"

        key1 = QueryCacheKey(query, (1,))
        key2 = QueryCacheKey(query, (2,))

        assert key1.hash_key != key2.hash_key

    def test_l1_cache_get_set(self):
        """Test L1 cache get/set operations."""
        from query_cache import L1Cache, QueryCacheKey

        cache = L1Cache(ttl_seconds=10)
        query = "SELECT * FROM table"
        params = (1,)
        result = [(1, "data"), (2, "data")]

        key = QueryCacheKey(query, params)

        # Initially empty
        assert cache.get(key) is None

        # Set value
        cache.set(key, result)

        # Should retrieve
        cached = cache.get(key)
        assert cached == result

    def test_l1_cache_ttl_expiration(self):
        """Test L1 cache TTL expiration."""
        from query_cache import L1Cache, QueryCacheKey

        cache = L1Cache(ttl_seconds=1)
        key = QueryCacheKey("SELECT 1", ())
        result = [(1,)]

        cache.set(key, result)
        assert cache.get(key) is not None

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get(key) is None

    def test_l1_cache_stats(self):
        """Test L1 cache statistics."""
        from query_cache import L1Cache, QueryCacheKey

        cache = L1Cache(max_entries=100, ttl_seconds=300)
        stats = cache.get_stats()

        assert stats["entries"] == 0
        assert stats["max_entries"] == 100
        assert stats["ttl_seconds"] == 300

        # Add an entry
        key = QueryCacheKey("SELECT 1", ())
        cache.set(key, [(1,)])

        stats = cache.get_stats()
        assert stats["entries"] == 1

    def test_l2_cache_sqlite_persistence(self):
        """Test L2 cache persistence with SQLite."""
        from query_cache import L2Cache, QueryCacheKey

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = L2Cache(db_path=db_path)

            query = "SELECT * FROM table"
            params = (1,)
            result = [(1, "data")]

            key = QueryCacheKey(query, params)

            # Set value
            cache.set(key, result, ttl_seconds=3600)

            # Create new cache instance pointing to same DB
            cache2 = L2Cache(db_path=db_path)

            # Should retrieve from persistent storage
            cached = cache2.get(key)
            assert cached == result

    def test_l2_cache_cleanup(self):
        """Test L2 cache cleanup of old entries."""
        from query_cache import L2Cache, QueryCacheKey

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = L2Cache(db_path=db_path)

            key = QueryCacheKey("SELECT 1", ())
            cache.set(key, [(1,)], ttl_seconds=-1)  # Already expired

            stats_before = cache.get_stats()
            cache.cleanup(max_age_days=0)  # Remove everything
            stats_after = cache.get_stats()

            # Cleanup should remove expired entries
            assert stats_after["entries"] <= stats_before["entries"]

    def test_dual_level_cache_hierarchy(self):
        """Test dual-level cache with L1 -> L2 hierarchy."""
        from query_cache import DualLevelCache, QueryCacheKey

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = DualLevelCache(l1_ttl=300, l2_db_path=db_path)

            query = "SELECT * FROM table"
            params = (1,)
            result = [(1, "data")]

            # Initially empty
            assert cache.get(query, params) is None

            # Set value (goes to both L1 and L2)
            cache.set(query, params, result)

            # Should hit L1
            assert cache.get(query, params) == result

            # Create new cache instance (L1 empty, L2 has data)
            cache2 = DualLevelCache(l1_ttl=300, l2_db_path=db_path)

            # Should hit L2
            assert cache2.get(query, params) == result

            # L1 should now be populated
            assert cache2.get(query, params) == result


class TestPerformanceProfiler:
    """Tests for performance profiling."""

    def test_profiler_initialization(self):
        """Test profiler initialization."""
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler()
        assert profiler.enable_memory_tracking is True
        assert len(profiler.operations) == 0

    def test_profiler_track_operation(self):
        """Test tracking a single operation."""
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler(enable_memory_tracking=False)

        with profiler.track("test_op"):
            time.sleep(0.01)  # 10ms

        assert len(profiler.operations) == 1
        assert profiler.operations[0].operation_name == "test_op"
        assert profiler.operations[0].wall_time_ms >= 10

    def test_profiler_multiple_operations(self):
        """Test tracking multiple operations."""
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler(enable_memory_tracking=False)

        for i in range(3):
            with profiler.track(f"op_{i}"):
                time.sleep(0.001)

        assert len(profiler.operations) == 3
        assert profiler.operation_counts["op_0"] == 1
        assert profiler.operation_counts["op_1"] == 1
        assert profiler.operation_counts["op_2"] == 1

    def test_profiler_summary(self):
        """Test profiler summary generation."""
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler(enable_memory_tracking=False)

        with profiler.track("test_op"):
            time.sleep(0.001)

        summary = profiler.get_summary()

        assert summary["total_operations"] == 1
        assert "avg_time_ms" in summary
        assert "operations_by_type" in summary
        assert "test_op" in summary["operations_by_type"]

    def test_profiler_report(self):
        """Test profiler report generation."""
        from performance_profiler import PerformanceProfiler

        profiler = PerformanceProfiler(enable_memory_tracking=False)

        with profiler.track("test_op"):
            time.sleep(0.001)

        report = profiler.report()

        assert "PERFORMANCE PROFILING REPORT" in report
        assert "test_op" in report
        assert "Total Operations: 1" in report

    def test_profiler_json_export(self):
        """Test JSON export."""
        from performance_profiler import PerformanceProfiler
        import json

        profiler = PerformanceProfiler(enable_memory_tracking=False)

        with profiler.track("test_op"):
            time.sleep(0.001)

        json_str = profiler.export_json()
        data = json.loads(json_str)

        assert data["total_operations"] == 1
        assert "operations_by_type" in data

    def test_query_profiler(self):
        """Test query profiler."""
        from performance_profiler import QueryProfiler

        profiler = QueryProfiler()

        profiler.track_query("SELECT * FROM table", 5.0, rows_affected=10, success=True)
        profiler.track_query("SELECT * FROM table", 3.0, rows_affected=5, success=True)

        stats = profiler.get_stats()

        assert stats["total_queries"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
        assert stats["avg_time_ms"] == 4.0

    def test_query_profiler_failures(self):
        """Test query profiler with failures."""
        from performance_profiler import QueryProfiler

        profiler = QueryProfiler()

        profiler.track_query("SELECT 1", 1.0, success=True)
        profiler.track_query("SELECT 2", 1.0, success=False)

        stats = profiler.get_stats()

        assert stats["total_queries"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1


class TestPerformanceIntegration:
    """Integration tests for performance optimizations."""

    def test_profiler_context_manager(self):
        """Test profiler as context manager."""
        from performance_profiler import PerformanceProfiler

        with PerformanceProfiler(enable_memory_tracking=False) as profiler:
            with profiler.track("op1"):
                time.sleep(0.001)
            with profiler.track("op2"):
                time.sleep(0.001)

        summary = profiler.get_summary()
        assert summary["total_operations"] == 2

    def test_cache_invalidation(self):
        """Test cache invalidation after updates."""
        from query_cache import DualLevelCache

        cache = DualLevelCache()

        # Set value
        cache.set("SELECT 1", (), [(1,)])
        assert cache.get("SELECT 1", ()) == [(1,)]

        # Invalidate
        cache.invalidate()

        # Should be cleared
        assert cache.get("SELECT 1", ()) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
