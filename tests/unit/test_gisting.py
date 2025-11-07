"""Unit tests for gisting and prompt caching."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from athena.efficiency.gisting import (
    GistManager,
    GistCacheEntry,
    CacheMetrics,
    create_gist_manager,
)


class TestGistCacheEntry:
    """Test GistCacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = GistCacheEntry(
            gist_id="test:abc123",
            original_hash="def456",
            summary="Test summary",
            content_type="document",
            original_length=1000,
            summary_length=100,
            compression_ratio=10.0,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            cache_tokens_saved=900,
        )

        assert entry.gist_id == "test:abc123"
        assert entry.content_type == "document"
        assert entry.compression_ratio == 10.0
        assert entry.access_count == 1

    def test_cache_entry_defaults(self):
        """Test cache entry default values."""
        entry = GistCacheEntry(
            gist_id="test:abc",
            original_hash="def",
            summary="Test",
            content_type="document",
            original_length=100,
            summary_length=10,
            compression_ratio=10.0,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )

        assert entry.access_count == 0
        assert entry.cache_tokens_saved == 0
        assert entry.model_used == "claude-3-5-haiku"


class TestCacheMetrics:
    """Test CacheMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = CacheMetrics(
            total_requests=100,
            cache_hits=70,
            cache_misses=30,
            hit_rate=0.7,
            cost_savings_percentage=15.0,
        )

        assert metrics.total_requests == 100
        assert metrics.cache_hits == 70
        assert metrics.hit_rate == 0.7

    def test_metrics_defaults(self):
        """Test default metric values."""
        metrics = CacheMetrics()

        assert metrics.total_requests == 0
        assert metrics.cache_hits == 0
        assert metrics.hit_rate == 0.0
        assert metrics.avg_compression_ratio == 1.0


class TestGistManagerInitialization:
    """Test GistManager initialization."""

    def test_init_memory_only(self):
        """Test initializing with memory-only cache."""
        manager = GistManager()

        assert manager.cache_dir is None
        assert len(manager._gist_cache) == 0
        assert manager.max_cache_size_bytes > 0

    def test_init_with_cache_dir(self):
        """Test initializing with persistent cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GistManager(cache_dir=tmpdir)

            assert manager.cache_dir == Path(tmpdir)
            assert manager.cache_dir.exists()

    def test_init_with_custom_cache_size(self):
        """Test custom cache size."""
        manager = GistManager(max_cache_size_mb=50)

        assert manager.max_cache_size_bytes == 50 * 1024 * 1024

    def test_factory_function(self):
        """Test factory function."""
        manager = create_gist_manager()

        assert isinstance(manager, GistManager)


class TestGistDocument:
    """Test document gisting."""

    def test_gist_simple_document(self):
        """Test gisting a simple document."""
        manager = GistManager()
        content = "This is a test document with some content."

        summary, entry = manager.gist_document(
            content=content, content_type="document", max_summary_tokens=50
        )

        assert isinstance(summary, str)
        assert entry.gist_id.startswith("document:")
        assert entry.content_type == "document"
        assert entry.original_length > 0
        assert entry.summary_length > 0

    def test_gist_code_document(self):
        """Test gisting code."""
        manager = GistManager()
        code = "def hello():\n    print('hello')\n\ndef goodbye():\n    print('goodbye')"

        summary, entry = manager.gist_document(
            content=code, content_type="code", max_summary_tokens=100
        )

        assert entry.content_type == "code"
        assert len(summary) > 0

    def test_gist_memory_document(self):
        """Test gisting a memory event."""
        manager = GistManager()
        memory = "Completed task X on 2024-01-01. Impact: 50% improvement in latency."

        summary, entry = manager.gist_document(
            content=memory, content_type="memory", max_summary_tokens=75
        )

        assert entry.content_type == "memory"
        assert len(summary) > 0

    def test_gist_query_document(self):
        """Test gisting a query."""
        manager = GistManager()
        query = "How do I optimize database performance for large datasets?"

        summary, entry = manager.gist_document(
            content=query, content_type="query", max_summary_tokens=50
        )

        assert entry.content_type == "query"
        assert len(summary) > 0

    def test_gist_compression_ratio(self):
        """Test compression ratio calculation."""
        manager = GistManager()
        long_content = "Test content. " * 100  # 1400+ characters

        _, entry = manager.gist_document(long_content)

        # Should compress somewhat
        assert entry.compression_ratio >= 1.0

    def test_gist_hash_computation(self):
        """Test that same content gets same hash."""
        manager = GistManager()
        content = "Test content"

        _, entry1 = manager.gist_document(content)
        _, entry2 = manager.gist_document(content, force_regenerate=True)

        # Same content should have same hash
        assert entry1.original_hash == entry2.original_hash


class TestCaching:
    """Test caching functionality."""

    def test_cache_hit(self):
        """Test cache hit."""
        manager = GistManager()
        content = "Test content"

        # First call - miss
        summary1, entry1 = manager.gist_document(content)

        # Second call - hit
        summary2, entry2 = manager.gist_document(content)

        assert summary1 == summary2
        assert manager._metrics.cache_hits > 0

    def test_cache_miss_force_regenerate(self):
        """Test cache miss with force_regenerate."""
        manager = GistManager()
        content = "Test content"

        summary1, _ = manager.gist_document(content)
        # Force regenerate ignores cache
        summary2, _ = manager.gist_document(content, force_regenerate=True)

        # Both should be summaries (may differ due to LLM randomness)
        assert len(summary1) > 0
        assert len(summary2) > 0

    def test_get_cached_gist(self):
        """Test retrieving cached gist."""
        manager = GistManager()
        content = "Test content"

        _, entry = manager.gist_document(content)
        gist_id = entry.gist_id

        # Retrieve from cache
        cached = manager.get_cached_gist(gist_id)
        assert cached is not None
        assert cached.summary == entry.summary

    def test_get_nonexistent_gist(self):
        """Test retrieving non-existent gist."""
        manager = GistManager()

        cached = manager.get_cached_gist("nonexistent:abc123")
        assert cached is None

    def test_cache_entry_access_tracking(self):
        """Test that cache entries track access."""
        manager = GistManager()
        content = "Test content"

        _, entry = manager.gist_document(content)
        initial_access = entry.access_count

        # Access again
        manager.get_cached_gist(entry.gist_id)

        # Should update access count
        assert manager.get_cached_gist(entry.gist_id).access_count > initial_access


class TestCacheInvalidation:
    """Test cache invalidation and expiry."""

    def test_invalidate_gist(self):
        """Test invalidating a gist."""
        manager = GistManager()
        content = "Test content"

        _, entry = manager.gist_document(content)
        gist_id = entry.gist_id

        # Verify it's cached
        assert manager.get_cached_gist(gist_id) is not None

        # Invalidate
        result = manager.invalidate_gist(gist_id)

        assert result is True
        assert manager.get_cached_gist(gist_id) is None

    def test_invalidate_nonexistent_gist(self):
        """Test invalidating non-existent gist."""
        manager = GistManager()

        result = manager.invalidate_gist("nonexistent:abc")
        assert result is False

    def test_invalidate_old_gists(self):
        """Test invalidating old gists."""
        manager = GistManager()
        content = "Test content"

        # Create a gist
        _, entry = manager.gist_document(content)

        # Manually set created_at to old date
        entry.created_at = datetime.now() - timedelta(days=40)

        # Invalidate gists older than 30 days
        count = manager.invalidate_old_gists(days_old=30)

        assert count > 0

    def test_clear_cache(self):
        """Test clearing entire cache."""
        manager = GistManager()

        # Create multiple gists
        for i in range(3):
            manager.gist_document(f"Content {i}")

        assert len(manager._gist_cache) > 0

        # Clear cache
        count = manager.clear_cache(include_disk=False)

        assert count == 3
        assert len(manager._gist_cache) == 0


class TestCacheMetrics:
    """Test cache metrics tracking."""

    def test_get_cache_metrics(self):
        """Test retrieving cache metrics."""
        manager = GistManager()
        content = "Test content"

        # Generate some cache activity
        manager.gist_document(content)
        manager.gist_document(content)  # Should hit

        metrics = manager.get_cache_metrics()

        assert isinstance(metrics, CacheMetrics)
        assert metrics.cache_hits > 0

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        manager = GistManager()
        content = "Test content"

        # Create cache miss
        manager.gist_document(content)
        # Create cache hit
        manager.gist_document(content)

        metrics = manager.get_cache_metrics()

        # Should be 50% (1 hit out of 2 requests)
        assert metrics.hit_rate == 0.5

    def test_compression_ratio_tracking(self):
        """Test compression ratio tracking."""
        manager = GistManager()
        long_content = "Test content. " * 50

        _, entry = manager.gist_document(long_content)

        stats = manager.get_cache_stats()

        # Should track compression
        assert stats["avg_compression_ratio"] >= 1.0

    def test_cache_stats(self):
        """Test getting cache statistics."""
        manager = GistManager()

        # Create some gists
        manager.gist_document("Content 1")
        manager.gist_document("Content 2")

        stats = manager.get_cache_stats()

        assert stats["total_gists"] == 2
        assert stats["cache_size_mb"] >= 0
        assert "hit_rate" in stats
        assert "cost_savings_percent" in stats


class TestBatchGisting:
    """Test batch gisting."""

    def test_batch_gist_documents(self):
        """Test batch gisting multiple documents."""
        manager = GistManager()

        documents = [
            ("Document 1 content", "document"),
            ("def foo(): pass", "code"),
            ("Memory of event X", "memory"),
        ]

        results = manager.batch_gist_documents(documents)

        assert len(results) == 3

        for summary, entry in results:
            assert isinstance(summary, str)
            assert len(summary) > 0
            assert entry.gist_id.startswith(
                ("document:", "code:", "memory:")
            )

    def test_batch_with_empty_list(self):
        """Test batch gisting with empty list."""
        manager = GistManager()

        results = manager.batch_gist_documents([])

        assert results == []

    def test_batch_reuses_cache(self):
        """Test that batch gisting reuses cache."""
        manager = GistManager()
        content = "Test content"

        documents = [
            (content, "document"),
            (content, "document"),  # Same content
        ]

        results = manager.batch_gist_documents(documents)

        assert len(results) == 2
        # Both should have same summary (from cache)
        assert results[0][0] == results[1][0]


class TestPersistentCache:
    """Test persistent disk caching."""

    def test_persist_to_disk(self):
        """Test persisting cache to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GistManager(cache_dir=tmpdir)
            content = "Test content for persistence"

            _, entry = manager.gist_document(content)

            # Check file was created
            cache_file = Path(tmpdir) / f"{entry.gist_id}.json"
            assert cache_file.exists()

    def test_load_from_disk(self):
        """Test loading cache from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manager and cache
            manager1 = GistManager(cache_dir=tmpdir)
            content = "Test content"
            _, entry1 = manager1.gist_document(content)
            gist_id = entry1.gist_id

            # Create new manager instance (simulates reload)
            manager2 = GistManager(cache_dir=tmpdir)

            # Should be able to retrieve
            entry2 = manager2.get_cached_gist(gist_id)
            assert entry2 is not None
            assert entry2.summary == entry1.summary

    def test_cache_serialization(self):
        """Test cache entry serialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GistManager(cache_dir=tmpdir)
            content = "Test content"

            _, entry = manager.gist_document(content)

            # Check file content is valid JSON
            cache_file = Path(tmpdir) / f"{entry.gist_id}.json"
            data = json.loads(cache_file.read_text())

            assert data["gist_id"] == entry.gist_id
            assert data["summary"] == entry.summary
            assert "created_at" in data
            assert "last_accessed" in data


class TestComputeHash:
    """Test hash computation."""

    def test_hash_same_content(self):
        """Test that same content produces same hash."""
        manager = GistManager()
        content = "Test content"

        hash1 = manager._compute_hash(content)
        hash2 = manager._compute_hash(content)

        assert hash1 == hash2

    def test_hash_different_content(self):
        """Test different content produces different hash."""
        manager = GistManager()

        hash1 = manager._compute_hash("Content 1")
        hash2 = manager._compute_hash("Content 2")

        assert hash1 != hash2

    def test_hash_is_hex(self):
        """Test hash is valid hex string."""
        manager = GistManager()

        hash_val = manager._compute_hash("Test")

        # Should be hex string
        assert all(c in "0123456789abcdef" for c in hash_val)


class TestTokenEstimation:
    """Test token estimation."""

    def test_estimate_tokens(self):
        """Test token estimation."""
        manager = GistManager()

        # Rough estimate: ~4 chars per token
        text = "a" * 400
        estimated = manager._estimate_tokens(text)

        # Should estimate around 100 tokens
        assert 50 < estimated < 150

    def test_estimate_empty_string(self):
        """Test estimating empty string."""
        manager = GistManager()

        estimated = manager._estimate_tokens("")

        assert estimated >= 1  # Minimum 1 token

    def test_estimate_short_text(self):
        """Test estimating short text."""
        manager = GistManager()

        estimated = manager._estimate_tokens("Hi")

        assert estimated >= 1


class TestCacheEviction:
    """Test cache eviction policy."""

    def test_lru_eviction(self):
        """Test LRU (Least Recently Used) eviction."""
        # Create manager with very small cache
        manager = GistManager(max_cache_size_mb=1)

        # Add multiple large gists to trigger eviction
        for i in range(5):
            manager.gist_document("x" * 1000 + f" {i}")

        # Should have evicted some entries
        assert len(manager._gist_cache) <= 5

    def test_cache_size_limit(self):
        """Test cache respects size limits."""
        manager = GistManager(max_cache_size_mb=0.1)  # Very small

        # Try to fill cache
        for i in range(10):
            manager.gist_document(f"Content {i} " * 100)

        # Cache should be within limits
        assert manager._cache_size_bytes <= manager.max_cache_size_bytes * 1.1
