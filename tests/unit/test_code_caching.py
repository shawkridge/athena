"""Tests for code search caching strategies."""

import pytest
import time

from src.athena.code_search.code_caching import (
    CacheStrategy,
    CacheEntry,
    LRUCache,
    TTLCache,
    EmbeddingCache,
    QueryCache,
    GraphCache,
    PatternCache,
    CacheManager,
)


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_entry_creation(self):
        """Test creating cache entry."""
        entry = CacheEntry(key="test", value="data", timestamp=time.time())

        assert entry.key == "test"
        assert entry.value == "data"
        assert entry.access_count == 0

    def test_entry_expiration(self):
        """Test TTL expiration check."""
        old_time = time.time() - 7200  # 2 hours ago
        entry = CacheEntry(key="test", value="data", timestamp=old_time)

        assert entry.is_expired(ttl_seconds=3600)  # 1 hour TTL

    def test_entry_not_expired(self):
        """Test non-expired entry."""
        entry = CacheEntry(key="test", value="data", timestamp=time.time())

        assert not entry.is_expired(ttl_seconds=3600)


class TestLRUCache:
    """Tests for LRU cache."""

    @pytest.fixture
    def cache(self):
        """Create LRU cache."""
        return LRUCache(max_size=3)

    def test_set_get(self, cache):
        """Test basic set/get."""
        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_cache_miss(self, cache):
        """Test cache miss."""
        result = cache.get("nonexistent")

        assert result is None
        assert cache.misses == 1

    def test_cache_hit(self, cache):
        """Test cache hit."""
        cache.set("key1", "value1")
        cache.get("key1")

        assert cache.hits == 1

    def test_lru_eviction(self, cache):
        """Test LRU eviction."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_lru_access_order(self, cache):
        """Test that access updates LRU order."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key4 (should evict key2, not key1)
        cache.set("key4", "value4")

        assert cache.get("key2") is None
        assert cache.get("key1") == "value1"

    def test_delete(self, cache):
        """Test deleting entry."""
        cache.set("key1", "value1")
        result = cache.delete("key1")

        assert result is True
        assert cache.get("key1") is None

    def test_clear(self, cache):
        """Test clearing cache."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert len(cache.entries) == 0
        assert cache.hits == 0

    def test_stats(self, cache):
        """Test cache statistics."""
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["strategy"] == "lru"


class TestTTLCache:
    """Tests for TTL cache."""

    @pytest.fixture
    def cache(self):
        """Create TTL cache."""
        return TTLCache(max_size=10, ttl_seconds=1)

    def test_set_get(self, cache):
        """Test basic set/get."""
        cache.set("key1", "value1")
        result = cache.get("key1")

        assert result == "value1"

    def test_ttl_expiration(self, cache):
        """Test TTL expiration."""
        cache.set("key1", "value1")
        time.sleep(1.1)  # Wait for expiration

        result = cache.get("key1")
        assert result is None

    def test_no_expiration_within_ttl(self, cache):
        """Test no expiration within TTL."""
        cache.set("key1", "value1")
        time.sleep(0.5)

        result = cache.get("key1")
        assert result == "value1"

    def test_ttl_unlimited(self):
        """Test unlimited TTL."""
        cache = TTLCache(max_size=10, ttl_seconds=0)
        cache.set("key1", "value1")
        time.sleep(0.1)

        result = cache.get("key1")
        assert result == "value1"


class TestEmbeddingCache:
    """Tests for embedding cache."""

    @pytest.fixture
    def cache(self):
        """Create embedding cache."""
        return EmbeddingCache(max_size=10)

    def test_set_get_embedding(self, cache):
        """Test embedding caching."""
        code = "def foo(): pass"
        embedding = [0.1, 0.2, 0.3]

        cache.set_embedding(code, embedding)
        result = cache.get_embedding(code)

        assert result == embedding

    def test_embedding_with_model(self, cache):
        """Test embedding with model specification."""
        code = "def foo(): pass"
        emb1 = [0.1, 0.2, 0.3]
        emb2 = [0.4, 0.5, 0.6]

        cache.set_embedding(code, emb1, model="model1")
        cache.set_embedding(code, emb2, model="model2")

        assert cache.get_embedding(code, model="model1") == emb1
        assert cache.get_embedding(code, model="model2") == emb2

    def test_embedding_cache_hit_rate(self, cache):
        """Test embedding cache hit rate."""
        codes = ["def foo(): pass", "def bar(): pass"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]

        for code, emb in zip(codes, embeddings):
            cache.set_embedding(code, emb)

        # Access twice each
        for code in codes:
            cache.get_embedding(code)
            cache.get_embedding(code)

        stats = cache.get_stats()
        assert stats["hit_rate"] == 1.0  # All hits


class TestQueryCache:
    """Tests for query cache."""

    @pytest.fixture
    def cache(self):
        """Create query cache."""
        return QueryCache(max_size=10)

    def test_set_get_results(self, cache):
        """Test query result caching."""
        query = "validate input"
        results = [
            {"name": "validate_input", "score": 0.95},
            {"name": "is_valid", "score": 0.82},
        ]

        cache.set_results(query, results)
        cached = cache.get_results(query)

        assert cached == results

    def test_query_with_parameters(self, cache):
        """Test query caching with parameters."""
        query = "process data"
        results1 = [{"name": "process", "score": 0.9}]
        results2 = [
            {"name": "process", "score": 0.9},
            {"name": "handle", "score": 0.7},
        ]

        cache.set_results(query, results1, strategy="semantic", top_k=5)
        cache.set_results(query, results2, strategy="hybrid", top_k=10)

        assert cache.get_results(query, strategy="semantic", top_k=5) == results1
        assert cache.get_results(query, strategy="hybrid", top_k=10) == results2


class TestGraphCache:
    """Tests for graph cache."""

    @pytest.fixture
    def cache(self):
        """Create graph cache."""
        return GraphCache(max_size=10)

    def test_cache_related_entities(self, cache):
        """Test caching related entities."""
        entities = ["func_a", "func_b", "func_c"]

        cache.set_related_entities("main", entities, max_depth=2)
        result = cache.get_related_entities("main", max_depth=2)

        assert result == entities

    def test_cache_dependencies(self, cache):
        """Test caching dependencies."""
        deps = ["import_a", "import_b"]

        cache.set_dependencies("module_a", deps)
        result = cache.get_dependencies("module_a")

        assert result == deps

    def test_cache_path(self, cache):
        """Test caching path between entities."""
        path = ["source", "intermediate", "target"]

        cache.set_path("source", "target", path)
        result = cache.get_path("source", "target")

        assert result == path


class TestPatternCache:
    """Tests for pattern cache."""

    @pytest.fixture
    def cache(self):
        """Create pattern cache."""
        return PatternCache(max_size=10)

    def test_cache_patterns(self, cache):
        """Test caching detected patterns."""
        patterns = [
            {"name": "singleton", "confidence": 0.95},
            {"name": "factory", "confidence": 0.72},
        ]

        cache.set_patterns("MyClass", patterns, pattern_type="design")
        result = cache.get_patterns("MyClass", pattern_type="design")

        assert result == patterns


class TestCacheManager:
    """Tests for cache manager."""

    @pytest.fixture
    def manager(self):
        """Create cache manager."""
        return CacheManager(max_size=50)

    def test_manager_creation(self, manager):
        """Test creating cache manager."""
        assert manager.embedding_cache is not None
        assert manager.query_cache is not None
        assert manager.graph_cache is not None
        assert manager.pattern_cache is not None

    def test_cache_layer_count(self, manager):
        """Test number of cache layers."""
        assert len(manager.cache_layers) == 5

    def test_clear_all(self, manager):
        """Test clearing all caches."""
        manager.embedding_cache.set("key", "value")
        manager.query_cache.set("key", "value")

        manager.clear_all()

        assert len(manager.embedding_cache.entries) == 0
        assert len(manager.query_cache.entries) == 0

    def test_clear_layer(self, manager):
        """Test clearing specific layer."""
        manager.embedding_cache.set("key1", "value1")
        manager.query_cache.set("key2", "value2")

        manager.clear_layer("embeddings")

        assert len(manager.embedding_cache.entries) == 0
        assert len(manager.query_cache.entries) == 1

    def test_get_stats(self, manager):
        """Test getting cache statistics."""
        manager.embedding_cache.set("key1", "value1")
        manager.embedding_cache.get("key1")
        manager.embedding_cache.get("missing")

        stats = manager.get_stats()

        assert "layers" in stats
        assert "overall_hit_rate" in stats
        assert stats["total_hits"] == 1
        assert stats["total_misses"] == 1

    def test_generate_report(self, manager):
        """Test cache report generation."""
        manager.embedding_cache.set("key", "value")
        manager.embedding_cache.get("key")

        report = manager.generate_cache_report()

        assert "CACHE PERFORMANCE REPORT" in report
        assert "Hit Rate" in report
        assert "EMBEDDINGS" in report


class TestCachingIntegration:
    """Integration tests for caching."""

    def test_multi_layer_caching(self):
        """Test using multiple cache layers together."""
        manager = CacheManager(max_size=100)

        # Embedding cache
        code = "def process(): pass"
        emb = [0.1, 0.2, 0.3]
        manager.embedding_cache.set_embedding(code, emb)

        # Query cache
        query = "process function"
        results = [{"name": "process"}]
        manager.query_cache.set_results(query, results)

        # Graph cache
        manager.graph_cache.set_related_entities("process", ["handle", "manage"])

        # Pattern cache
        manager.pattern_cache.set_patterns("ProcessClass", [{"name": "factory"}])

        # Verify all are cached
        assert manager.embedding_cache.get_embedding(code) == emb
        assert manager.query_cache.get_results(query) == results
        assert manager.graph_cache.get_related_entities("process") == ["handle", "manage"]
        assert manager.pattern_cache.get_patterns("ProcessClass") == [{"name": "factory"}]

    def test_cache_eviction_strategy(self):
        """Test cache eviction strategy."""
        cache = LRUCache(max_size=3)

        # Fill cache
        for i in range(3):
            cache.set(f"key{i}", f"value{i}")

        # Access key0 (make it recently used)
        cache.get("key0")

        # Add new item (should evict key1, not key0)
        cache.set("key3", "value3")

        assert cache.get("key0") is not None
        assert cache.get("key1") is None
        assert cache.get("key3") is not None
