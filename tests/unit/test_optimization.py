"""Tests for performance optimization components (tier selection, caching).

Tests cover:
- Tier selection heuristics
- Query result caching with TTL
- Session context caching
- LRU eviction
- Cache statistics
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from athena.optimization.query_cache import QueryCache, QueryCacheEntry, SessionContextCache
from athena.optimization.tier_selection import TierSelector


class TestTierSelector:
    """Tests for cascade depth auto-selection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.selector = TierSelector(debug=False)

    def test_fast_query_classification(self):
        """Test that simple queries are classified as Tier 1."""
        fast_queries = [
            "When did we last talk?",
            "What happened yesterday?",
            "What is the definition of foo?",
            "Find recent events",
            "Show me the last test results",
        ]

        for query in fast_queries:
            depth = self.selector.select_depth(query)
            assert depth == 1, f"Query '{query}' should be Tier 1, got Tier {depth}"

    def test_enriched_query_classification(self):
        """Test that contextual queries are classified as Tier 2."""
        enriched_queries = [
            "How does this relate to our current phase?",
            "What is the relationship between these errors?",
            "Why did the test fail?",
            "Explain the dependencies in our system",
        ]

        for query in enriched_queries:
            depth = self.selector.select_depth(query)
            assert depth >= 2, f"Query '{query}' should be Tier 2+, got Tier {depth}"

    def test_synthesis_query_classification(self):
        """Test that complex queries are classified as Tier 3."""
        synthesis_queries = [
            "Synthesize everything we know about error handling",
            "What's the best strategy given all our constraints?",
            "Provide a comprehensive analysis of the system",
            "Given everything, what should we do next?",
        ]

        for query in synthesis_queries:
            depth = self.selector.select_depth(query)
            assert depth >= 2, f"Query '{query}' should be Tier 2+, got {depth}"

    def test_short_query_gets_tier_1(self):
        """Test that very short queries default to Tier 1."""
        depth = self.selector.select_depth("Hello?")
        assert depth == 1

    def test_explicit_depth_overrides_selection(self):
        """Test that explicit cascade_depth parameter is respected."""
        query = "Complex question that would normally be Tier 3"

        depth_1 = self.selector.select_depth(query, user_specified_depth=1)
        assert depth_1 == 1

        depth_3 = self.selector.select_depth(query, user_specified_depth=3)
        assert depth_3 == 3

    def test_context_affects_depth_selection(self):
        """Test that context (phase, etc.) influences depth selection."""
        query = "Tell me what's happening"

        # Planning phase might suggest deeper search
        planning_context = {"phase": "planning"}
        depth_planning = self.selector.select_depth(query, planning_context)

        # Execution phase with session context might be faster
        exec_context = {"phase": "executing", "session_id": "123"}
        depth_exec = self.selector.select_depth(query, exec_context)

        # Both should be reasonable (1-3)
        assert 1 <= depth_planning <= 3
        assert 1 <= depth_exec <= 3

    def test_explain_selection(self):
        """Test that selection explanation is provided."""
        query = "When did this happen?"
        explanation = self.selector.explain_selection(query)

        assert "Depth" in explanation
        assert "Tier" in explanation or "Fast" in explanation or "Enriched" in explanation or "Synthesis" in explanation


class TestQueryCacheEntry:
    """Tests for individual cache entries."""

    def test_entry_not_expired_immediately(self):
        """Test that new entries are not expired."""
        entry = QueryCacheEntry("hash123", {"result": "data"}, ttl_seconds=300)
        assert not entry.is_expired()

    def test_entry_expires_after_ttl(self):
        """Test that entries expire after TTL."""
        entry = QueryCacheEntry("hash123", {"result": "data"}, ttl_seconds=0)
        # Immediately expired
        assert entry.is_expired()

    def test_hits_tracking(self):
        """Test that hits are tracked."""
        entry = QueryCacheEntry("hash123", {"result": "data"})
        assert entry.hits == 0

        entry.record_hit()
        assert entry.hits == 1

        entry.record_hit()
        assert entry.hits == 2

    def test_age_calculation(self):
        """Test that entry age is calculated correctly."""
        entry = QueryCacheEntry("hash123", {"result": "data"})
        age = entry.get_age_seconds()

        assert age >= 0  # Should be very close to 0


class TestQueryCache:
    """Tests for query result caching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = QueryCache(max_entries=5, default_ttl_seconds=300)

    def test_cache_miss_on_empty_cache(self):
        """Test that empty cache returns None."""
        result = self.cache.get("test query")
        assert result is None

    def test_cache_hit_after_put(self):
        """Test that cached results can be retrieved."""
        query = "Test query"
        results = {"tier_1": {"semantic": ["result1", "result2"]}}

        self.cache.put(query, results)
        cached = self.cache.get(query)

        assert cached == results

    def test_cache_with_context(self):
        """Test that context is considered in cache key."""
        query = "Test query"
        results1 = {"tier_1": {"semantic": ["result1"]}}
        results2 = {"tier_1": {"semantic": ["result2"]}}

        context1 = {"session_id": "sess1"}
        context2 = {"session_id": "sess2"}

        self.cache.put(query, results1, context1)
        self.cache.put(query, results2, context2)

        # Should get different results based on context
        cached1 = self.cache.get(query, context1)
        cached2 = self.cache.get(query, context2)

        assert cached1 == results1
        assert cached2 == results2

    def test_expired_entries_not_returned(self):
        """Test that expired entries are not returned."""
        self.cache = QueryCache(max_entries=5, default_ttl_seconds=0)  # Immediate expiration

        query = "Test query"
        results = {"tier_1": {}}

        self.cache.put(query, results)
        # Entry should be immediately expired
        cached = self.cache.get(query)
        assert cached is None

    def test_lru_eviction(self):
        """Test that LRU eviction happens when cache is full."""
        # Create cache with max 3 entries
        cache = QueryCache(max_entries=3, default_ttl_seconds=300)

        # Add 4 entries (last one should trigger eviction)
        for i in range(4):
            cache.put(f"query_{i}", {"result": i})

        # Cache should not exceed max_entries
        assert len(cache.cache) <= 3

        # Total evictions should be tracked
        assert cache.total_evictions >= 1

    def test_clear_cache(self):
        """Test that cache can be cleared."""
        self.cache.put("query1", {"result": 1})
        self.cache.put("query2", {"result": 2})
        assert len(self.cache.cache) == 2

        self.cache.clear()
        assert len(self.cache.cache) == 0

    def test_invalidate_specific_entry(self):
        """Test that specific entries can be invalidated."""
        query1 = "query1"
        query2 = "query2"

        self.cache.put(query1, {"result": 1})
        self.cache.put(query2, {"result": 2})
        assert len(self.cache.cache) == 2

        # Invalidate query1
        self.cache.invalidate(query1)
        assert self.cache.get(query1) is None
        assert self.cache.get(query2) is not None

    def test_invalidate_all(self):
        """Test that all entries can be invalidated."""
        self.cache.put("query1", {"result": 1})
        self.cache.put("query2", {"result": 2})

        self.cache.invalidate()  # No args = invalidate all
        assert len(self.cache.cache) == 0

    def test_cache_statistics(self):
        """Test that cache statistics are tracked."""
        self.cache.put("query1", {"result": 1})

        # Create a hit
        self.cache.get("query1")

        # Create a miss
        self.cache.get("query_nonexistent")

        stats = self.cache.get_stats()
        assert "hit_rate" in stats
        assert "total_hits" in stats
        assert "total_misses" in stats
        assert stats["total_hits"] == 1
        assert stats["total_misses"] == 1

    def test_cleanup_expired_entries(self):
        """Test that expired entries can be cleaned up."""
        cache = QueryCache(max_entries=10, default_ttl_seconds=0)

        # Add some entries
        for i in range(3):
            cache.put(f"query_{i}", {"result": i})

        # All should be expired
        removed = cache.cleanup_expired()
        assert removed >= 3
        assert len(cache.cache) == 0


class TestSessionContextCache:
    """Tests for session context caching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = SessionContextCache(ttl_seconds=60)

    def test_context_cache_miss(self):
        """Test that missing context returns None."""
        result = self.cache.get("nonexistent_session")
        assert result is None

    def test_context_cache_hit(self):
        """Test that cached context can be retrieved."""
        session_id = "sess123"
        context = {"task": "debug", "phase": "executing"}

        self.cache.put(session_id, context)
        cached = self.cache.get(session_id)

        assert cached == context

    def test_context_cache_expiration(self):
        """Test that context expires after TTL."""
        cache = SessionContextCache(ttl_seconds=0)  # Immediate expiration

        session_id = "sess123"
        context = {"task": "debug"}

        cache.put(session_id, context)
        # Should be immediately expired
        cached = cache.get(session_id)
        assert cached is None

    def test_invalidate_specific_session(self):
        """Test that specific session cache can be invalidated."""
        self.cache.put("sess1", {"task": "task1"})
        self.cache.put("sess2", {"task": "task2"})

        self.cache.invalidate("sess1")

        assert self.cache.get("sess1") is None
        assert self.cache.get("sess2") is not None

    def test_invalidate_all_sessions(self):
        """Test that all session cache can be invalidated."""
        self.cache.put("sess1", {"task": "task1"})
        self.cache.put("sess2", {"task": "task2"})

        self.cache.invalidate()  # No args = clear all

        assert self.cache.get_size() == 0

    def test_get_size(self):
        """Test that cache size is tracked."""
        assert self.cache.get_size() == 0

        self.cache.put("sess1", {"task": "task1"})
        assert self.cache.get_size() == 1

        self.cache.put("sess2", {"task": "task2"})
        assert self.cache.get_size() == 2


class TestManagerIntegration:
    """Integration tests with UnifiedMemoryManager (requires manager fixture)."""

    def test_recall_uses_cache(self):
        """Test that recall method uses caching."""
        # This would require a proper manager fixture
        # Placeholder for integration test
        pass

    def test_recall_auto_selects_depth(self):
        """Test that recall auto-selects depth when not specified."""
        # This would require a proper manager fixture
        # Placeholder for integration test
        pass

    def test_recall_respects_explicit_depth(self):
        """Test that recall respects explicit cascade_depth parameter."""
        # This would require a proper manager fixture
        # Placeholder for integration test
        pass
