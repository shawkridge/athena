"""Tests for code search caching system."""

import pytest
from pathlib import Path
import time

from athena.code_search.tree_sitter_search import TreeSitterCodeSearch
from athena.code_search.cache import (
    SearchResultCache,
    EmbeddingCache,
    TypeFilterCache,
    CombinedSearchCache,
)
from athena.code_search.models import CodeUnit, SearchResult


@pytest.fixture
def test_repo(tmp_path):
    """Create a test repository."""
    (tmp_path / "src").mkdir()

    main_file = tmp_path / "src" / "main.py"
    main_file.write_text("""
def authenticate(user: str) -> bool:
    '''Authenticate a user.'''
    return validate_user(user)

def validate_user(user: str) -> bool:
    '''Validate user credentials.'''
    return len(user) > 0

class AuthHandler:
    '''Handles authentication.'''
    def __init__(self):
        pass

    def login(self, user: str) -> bool:
        '''Log in a user.'''
        return authenticate(user)
""")

    return tmp_path


@pytest.fixture
def search_engine(test_repo):
    """Create a search engine with cache enabled."""
    engine = TreeSitterCodeSearch(str(test_repo), enable_cache=True)
    engine.build_index()
    return engine


class TestSearchResultCache:
    """Test SearchResultCache."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = SearchResultCache(max_size=100)
        assert cache.max_size == 100
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_cache_set_and_get(self):
        """Test setting and getting cached results."""
        cache = SearchResultCache()

        # Create dummy results
        results = []
        cache.set("test query", 10, 0.3, results)

        # Retrieve cached results
        cached = cache.get("test query", 10, 0.3)
        assert cached is not None
        assert cached == results

    def test_cache_miss(self):
        """Test cache miss."""
        cache = SearchResultCache()

        result = cache.get("nonexistent", 10, 0.3)
        assert result is None
        assert cache.misses == 1

    def test_cache_hit(self):
        """Test cache hit."""
        cache = SearchResultCache()

        results = []
        cache.set("test", 10, 0.3, results)
        cache.get("test", 10, 0.3)

        assert cache.hits == 1

    def test_cache_key_uniqueness(self):
        """Test that different parameters create different keys."""
        cache = SearchResultCache()

        results1 = []
        results2 = []

        cache.set("query", 10, 0.3, results1)
        cache.set("query", 20, 0.3, results2)

        cached1 = cache.get("query", 10, 0.3)
        cached2 = cache.get("query", 20, 0.3)

        assert cached1 == results1
        assert cached2 == results2

    def test_cache_eviction(self):
        """Test LRU eviction."""
        cache = SearchResultCache(max_size=3)

        # Fill cache
        cache.set("q1", 10, 0.3, [])
        cache.set("q2", 10, 0.3, [])
        cache.set("q3", 10, 0.3, [])

        assert len(cache.cache) == 3

        # Add one more (should evict oldest)
        cache.set("q4", 10, 0.3, [])
        assert len(cache.cache) == 3

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = SearchResultCache()
        cache.set("test", 10, 0.3, [])
        assert len(cache.cache) == 1

        cache.clear()
        assert len(cache.cache) == 0

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = SearchResultCache()

        cache.set("test", 10, 0.3, [])
        cache.get("test", 10, 0.3)
        cache.get("other", 10, 0.3)

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total"] == 2
        assert stats["cached_queries"] == 1


class TestEmbeddingCache:
    """Test EmbeddingCache."""

    def test_embedding_cache_initialization(self):
        """Test embedding cache initialization."""
        cache = EmbeddingCache(max_size=1000)
        assert cache.max_size == 1000

    def test_embedding_cache_set_and_get(self):
        """Test setting and getting embeddings."""
        cache = EmbeddingCache()

        embedding = [0.1, 0.2, 0.3, 0.4]
        cache.set("test text", embedding)

        cached = cache.get("test text")
        assert cached == embedding

    def test_embedding_cache_stats(self):
        """Test embedding cache statistics."""
        cache = EmbeddingCache()

        cache.set("text1", [0.1, 0.2])
        cache.get("text1")
        cache.get("text2")

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1


class TestTypeFilterCache:
    """Test TypeFilterCache."""

    def test_type_filter_cache(self):
        """Test type filter cache."""
        cache = TypeFilterCache()

        unit_ids = ["id1", "id2", "id3"]
        cache.set("function", unit_ids)

        cached = cache.get("function")
        assert cached == unit_ids


class TestCombinedCache:
    """Test CombinedSearchCache."""

    def test_combined_cache_initialization(self):
        """Test combined cache initialization."""
        cache = CombinedSearchCache()

        assert cache.search_cache is not None
        assert cache.embedding_cache is not None
        assert cache.type_cache is not None

    def test_combined_cache_clear_all(self):
        """Test clearing all caches."""
        cache = CombinedSearchCache()

        cache.search_cache.set("test", 10, 0.3, [])
        cache.embedding_cache.set("text", [0.1, 0.2])
        cache.type_cache.set("function", ["id1"])

        cache.clear_all()

        assert len(cache.search_cache.cache) == 0
        assert len(cache.embedding_cache.cache) == 0
        assert len(cache.type_cache.cache) == 0

    def test_combined_cache_stats(self):
        """Test combined cache statistics."""
        cache = CombinedSearchCache()

        stats = cache.get_stats()

        assert "search" in stats
        assert "embedding" in stats
        assert "type_filter" in stats


class TestCacheIntegration:
    """Test cache integration with TreeSitterCodeSearch."""

    def test_cache_enabled_by_default(self, test_repo):
        """Test that cache is enabled by default."""
        engine = TreeSitterCodeSearch(str(test_repo))
        assert engine.cache is not None

    def test_cache_can_be_disabled(self, test_repo):
        """Test disabling cache."""
        engine = TreeSitterCodeSearch(str(test_repo), enable_cache=False)
        engine.build_index()
        assert engine.cache is None

    def test_search_uses_cache(self, search_engine):
        """Test that search uses cache."""
        # First search
        results1 = search_engine.search("authenticate", top_k=10, min_score=0.0)

        # Check cache stats
        stats = search_engine.get_cache_stats()
        assert stats["cache_enabled"]
        assert stats["search"]["hits"] == 0
        assert stats["search"]["misses"] == 1

        # Second search (should hit cache)
        results2 = search_engine.search("authenticate", top_k=10, min_score=0.0)

        # Check cache stats again
        stats = search_engine.get_cache_stats()
        assert stats["search"]["hits"] == 1
        assert stats["search"]["misses"] == 1

        # Results should be identical
        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.unit.id == r2.unit.id

    def test_cache_performance_improvement(self, search_engine):
        """Test that cache improves performance."""
        query = "authenticate"

        # First search (uncached)
        start = time.time()
        search_engine.search(query, top_k=10, min_score=0.0)
        time_uncached = time.time() - start

        # Second search (cached)
        start = time.time()
        search_engine.search(query, top_k=10, min_score=0.0)
        time_cached = time.time() - start

        # Cached search should be faster
        assert time_cached < time_uncached

    def test_different_parameters_dont_share_cache(self, search_engine):
        """Test that different parameters don't share cache."""
        # Search with limit 5
        results1 = search_engine.search("authenticate", top_k=5, min_score=0.0)

        # Search with limit 10
        results2 = search_engine.search("authenticate", top_k=10, min_score=0.0)

        # Results should be different (different limits)
        assert len(results1) <= 5
        assert len(results2) <= 10

        # Should be separate cache entries
        stats = search_engine.get_cache_stats()
        assert stats["search"]["cached_queries"] == 2

    def test_clear_cache(self, search_engine):
        """Test clearing cache."""
        # Populate cache
        search_engine.search("authenticate", top_k=10, min_score=0.0)

        stats = search_engine.get_cache_stats()
        assert stats["search"]["cached_queries"] == 1

        # Clear cache
        search_engine.clear_cache()

        stats = search_engine.get_cache_stats()
        assert stats["search"]["cached_queries"] == 0

    def test_cache_stats_available(self, search_engine):
        """Test that cache stats are available."""
        stats = search_engine.get_cache_stats()

        assert "cache_enabled" in stats
        assert "search" in stats
        assert "embedding" in stats
        assert "type_filter" in stats

        # Check search stats
        search_stats = stats["search"]
        assert "hits" in search_stats
        assert "misses" in search_stats
        assert "hit_rate" in search_stats
        assert "cached_queries" in search_stats


class TestCachePerformance:
    """Test cache performance benefits."""

    def test_cache_hit_rate(self, search_engine):
        """Test cache hit rate accumulation."""
        queries = [
            "authenticate",
            "validate",
            "authenticate",
            "handler",
            "validate",
            "authenticate",
        ]

        for query in queries:
            search_engine.search(query, top_k=10, min_score=0.0)

        stats = search_engine.get_cache_stats()
        search_stats = stats["search"]

        # Should have 3 hits and 3 misses
        assert search_stats["hits"] == 3
        assert search_stats["misses"] == 3
        assert search_stats["hit_rate"] == 50.0

    def test_cache_throughput_improvement(self, search_engine):
        """Test cache throughput improvement."""
        import time

        # Warm up cache with one search
        search_engine.search("authenticate", top_k=10, min_score=0.0)

        # Time 100 searches on same query (all cache hits)
        start = time.time()
        for _ in range(100):
            search_engine.search("authenticate", top_k=10, min_score=0.0)
        cached_time = time.time() - start

        # Without cache, this would be much slower
        # We can't measure directly, but cached_time should be very small
        assert cached_time < 1.0  # 100 cached searches in <1 second
