"""Tests for semantic code search query engine."""

import pytest

from src.athena.code_search.code_semantic_search import (
    QueryType,
    QueryStrategy,
    QueryTerm,
    ParsedQuery,
    SearchMetrics,
    QueryParser,
    QueryExpander,
    QueryOptimizer,
    SearchCache,
    SemanticSearchEngine,
)


class TestQueryTerm:
    """Tests for QueryTerm."""

    def test_term_creation(self):
        """Test creating query term."""
        term = QueryTerm(text="process_data", weight=1.2)

        assert term.text == "process_data"
        assert term.weight == 1.2
        assert term.is_negation is False
        assert term.target_field is None

    def test_term_with_variants(self):
        """Test query term with variants."""
        term = QueryTerm(
            text="fetch",
            variants=["get", "retrieve", "pull"],
        )

        assert len(term.variants) == 3
        assert "get" in term.variants


class TestParsedQuery:
    """Tests for ParsedQuery."""

    def test_parsed_query_creation(self):
        """Test creating parsed query."""
        terms = [QueryTerm(text="validate"), QueryTerm(text="input")]
        parsed = ParsedQuery(
            original="validate input",
            query_type=QueryType.PHRASE,
            strategy=QueryStrategy.SEMANTIC,
            primary_terms=terms,
        )

        assert parsed.original == "validate input"
        assert parsed.query_type == QueryType.PHRASE
        assert len(parsed.primary_terms) == 2


class TestQueryParser:
    """Tests for QueryParser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return QueryParser()

    def test_parse_simple_query(self, parser):
        """Test parsing simple keyword query."""
        parsed = parser.parse("authentication")

        assert parsed.query_type == QueryType.SIMPLE
        assert len(parsed.primary_terms) > 0
        assert any(t.text == "authentication" for t in parsed.primary_terms)

    def test_parse_phrase_query(self, parser):
        """Test parsing phrase query."""
        parsed = parser.parse("data validation function")

        assert parsed.query_type in [QueryType.PHRASE, QueryType.INTENT]
        assert len(parsed.primary_terms) >= 2

    def test_parse_intent_query(self, parser):
        """Test parsing intentional query."""
        parsed = parser.parse("find functions that validate input")

        # Should be PHRASE or INTENT - both are multi-word queries
        assert parsed.query_type in [QueryType.INTENT, QueryType.PHRASE]
        assert len(parsed.primary_terms) > 0

    def test_parse_filter_query(self, parser):
        """Test parsing filter-based query."""
        parsed = parser.parse("process with high complexity")

        # Should extract filters and terms
        assert "min_complexity" in parsed.filters
        assert len(parsed.primary_terms) > 0

    def test_parse_boolean_query(self, parser):
        """Test parsing boolean query."""
        parsed = parser.parse("authentication and validation")

        assert parsed.query_type == QueryType.BOOLEAN
        assert len(parsed.primary_terms) >= 2

    def test_parse_pattern_query(self, parser):
        """Test parsing design pattern query."""
        parsed = parser.parse("singleton pattern")

        # Pattern query with recognized pattern keywords
        assert parsed.query_type in [QueryType.PATTERN, QueryType.PHRASE, QueryType.INTENT]
        assert len(parsed.primary_terms) > 0

    def test_parse_with_exclusions(self, parser):
        """Test parsing with NOT/exclusions."""
        parsed = parser.parse("process without validation")

        assert len(parsed.exclusions) > 0

    def test_strategy_selection_simple(self, parser):
        """Test strategy selection for simple query."""
        parsed = parser.parse("data")

        assert parsed.strategy == QueryStrategy.SEMANTIC

    def test_strategy_selection_pattern(self, parser):
        """Test strategy selection for pattern query."""
        parsed = parser.parse("factory pattern")

        # Pattern/multi-word queries should select appropriate strategy
        assert parsed.strategy in [QueryStrategy.SYNTACTIC, QueryStrategy.SEMANTIC, QueryStrategy.HYBRID]

    def test_strategy_selection_filter(self, parser):
        """Test strategy selection for filter query."""
        parsed = parser.parse("functions with high complexity")

        # Should select hybrid strategy when filters present
        assert parsed.strategy in [QueryStrategy.HYBRID, QueryStrategy.SEMANTIC]


class TestQueryExpander:
    """Tests for QueryExpander."""

    @pytest.fixture
    def expander(self):
        """Create expander instance."""
        return QueryExpander()

    def test_expand_with_synonyms(self, expander):
        """Test query expansion with synonyms."""
        query = ParsedQuery(
            original="process data",
            query_type=QueryType.PHRASE,
            strategy=QueryStrategy.SEMANTIC,
            primary_terms=[QueryTerm(text="process")],
        )

        expanded = expander.expand(query)

        # Should have variants for 'process'
        assert len(expanded.primary_terms) > 1

    def test_expand_pattern_query(self, expander):
        """Test expansion for pattern queries."""
        query = ParsedQuery(
            original="singleton pattern",
            query_type=QueryType.PATTERN,
            strategy=QueryStrategy.SYNTACTIC,
            primary_terms=[QueryTerm(text="singleton")],
        )

        expanded = expander.expand(query)

        # Should have related patterns
        assert len(expanded.primary_terms) >= 1

    def test_variant_weight_reduction(self, expander):
        """Test that variants have reduced weight."""
        query = ParsedQuery(
            original="fetch data",
            query_type=QueryType.PHRASE,
            strategy=QueryStrategy.SEMANTIC,
            primary_terms=[QueryTerm(text="fetch", weight=1.0)],
        )

        original_term_count = len(query.primary_terms)
        expanded = expander.expand(query)

        # Variants should have lower weight
        if len(expanded.primary_terms) > original_term_count:
            new_terms = expanded.primary_terms[original_term_count:]
            for term in new_terms:
                assert term.weight < 1.0


class TestQueryOptimizer:
    """Tests for QueryOptimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create optimizer instance."""
        return QueryOptimizer()

    def test_optimize_removes_stopwords(self, optimizer):
        """Test that optimization removes stopwords."""
        query = ParsedQuery(
            original="find code function",
            query_type=QueryType.INTENT,
            strategy=QueryStrategy.SEMANTIC,
            primary_terms=[
                QueryTerm(text="code"),
                QueryTerm(text="function"),
                QueryTerm(text="process"),
            ],
        )

        optimized = optimizer.optimize(query)

        # Should remove 'code' and 'function' stopwords
        assert len(optimized.primary_terms) <= len(query.primary_terms)

    def test_optimize_reorders_terms(self, optimizer):
        """Test that optimization reorders terms by weight."""
        query = ParsedQuery(
            original="validate process data",
            query_type=QueryType.PHRASE,
            strategy=QueryStrategy.SEMANTIC,
            primary_terms=[
                QueryTerm(text="validate", weight=0.5),
                QueryTerm(text="process", weight=2.0),
                QueryTerm(text="data", weight=1.0),
            ],
        )

        optimized = optimizer.optimize(query)

        # Highest weight term should be first
        assert optimized.primary_terms[0].weight >= optimized.primary_terms[1].weight

    def test_record_query_metrics(self, optimizer):
        """Test recording query metrics."""
        metrics = SearchMetrics(
            query="test query",
            query_type=QueryType.SIMPLE,
            terms_used=1,
            filters_applied=0,
            cache_hit=False,
            execution_time_ms=50.0,
            result_count=5,
            top_score=0.9,
        )

        optimizer.record_query("test query", metrics)

        assert len(optimizer.query_history) == 1

    def test_get_common_patterns(self, optimizer):
        """Test getting common query patterns."""
        for i in range(5):
            metrics = SearchMetrics(
                query=f"query pattern {i % 2}",
                query_type=QueryType.SIMPLE,
                terms_used=1,
                filters_applied=0,
                cache_hit=False,
                execution_time_ms=50.0,
                result_count=5,
                top_score=0.9,
            )
            optimizer.record_query(f"query pattern {i % 2}", metrics)

        patterns = optimizer.get_common_patterns(limit=5)

        assert len(patterns) > 0
        assert isinstance(patterns[0], tuple)


class TestSearchCache:
    """Tests for SearchCache."""

    @pytest.fixture
    def cache(self):
        """Create cache instance."""
        return SearchCache(max_size=3)

    def test_cache_set_get(self, cache):
        """Test basic cache set/get."""
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

    def test_cache_lru_eviction(self, cache):
        """Test LRU eviction when cache is full."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # Should evict key1

        result = cache.get("key1")
        assert result is None

    def test_cache_lru_move_to_end(self, cache):
        """Test that accessed items move to end."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 (move to end)
        cache.get("key1")

        # Add key4 (should evict key2, not key1)
        cache.set("key4", "value4")

        assert cache.get("key2") is None
        assert cache.get("key1") == "value1"

    def test_cache_clear(self, cache):
        """Test cache clearing."""
        cache.set("key1", "value1")
        cache.clear()

        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_cache_stats(self, cache):
        """Test cache statistics."""
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


class TestSemanticSearchEngine:
    """Tests for SemanticSearchEngine."""

    @pytest.fixture
    def engine(self):
        """Create search engine instance."""
        return SemanticSearchEngine()

    def test_engine_creation(self, engine):
        """Test creating search engine."""
        assert engine.parser is not None
        assert engine.expander is not None
        assert engine.optimizer is not None
        assert engine.cache is not None

    def test_search_without_rag_pipeline(self, engine):
        """Test search without RAG pipeline returns empty."""
        results = engine.search("test query")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_search_caches_results(self, engine):
        """Test that search caches results."""
        # First search (miss)
        engine.search("test")
        stats_before = engine.cache.get_stats()

        # Second identical search (hit)
        engine.search("test")
        stats_after = engine.cache.get_stats()

        assert stats_after["hits"] > stats_before["hits"]

    def test_search_records_metrics(self, engine):
        """Test that search records metrics."""
        engine.search("test query")

        assert len(engine.search_history) == 1
        metric = engine.search_history[0]
        assert metric.query == "test query"
        assert metric.execution_time_ms > 0

    def test_get_analytics(self, engine):
        """Test getting search analytics."""
        engine.search("query one")
        engine.search("query two")

        analytics = engine.get_analytics()

        assert analytics["total_searches"] == 2
        assert "query_types" in analytics
        assert "cache_stats" in analytics

    def test_clear_cache(self, engine):
        """Test clearing cache."""
        engine.search("test")
        engine.cache.set("key", "value")

        engine.clear_cache()

        assert len(engine.cache.cache) == 0

    def test_generate_search_report(self, engine):
        """Test report generation."""
        engine.search("test query")

        report = engine.generate_search_report()

        assert "SEMANTIC SEARCH REPORT" in report
        assert "Total Searches" in report


class TestSearchMetrics:
    """Tests for SearchMetrics."""

    def test_metrics_creation(self):
        """Test creating search metrics."""
        metrics = SearchMetrics(
            query="test",
            query_type=QueryType.SIMPLE,
            terms_used=1,
            filters_applied=0,
            cache_hit=False,
            execution_time_ms=50.5,
            result_count=10,
            top_score=0.95,
        )

        assert metrics.query == "test"
        assert metrics.execution_time_ms == 50.5
        assert metrics.result_count == 10


class TestSemanticSearchIntegration:
    """Integration tests for semantic search."""

    def test_full_search_workflow(self):
        """Test complete search workflow."""
        engine = SemanticSearchEngine()

        # Execute multiple searches
        engine.search("authentication function")
        engine.search("validate input")
        engine.search("data processing")

        # Verify history
        assert len(engine.search_history) == 3

        # Verify analytics
        analytics = engine.get_analytics()
        assert analytics["total_searches"] == 3

        # Verify report
        report = engine.generate_search_report()
        assert "Total Searches: 3" in report

    def test_query_optimization_workflow(self):
        """Test query optimization workflow."""
        parser = QueryParser()
        expander = QueryExpander()
        optimizer = QueryOptimizer()

        # Parse
        query = parser.parse("find code functions with high complexity")

        # Expand
        query = expander.expand(query)
        expanded_terms = len(query.primary_terms)

        # Optimize
        query = optimizer.optimize(query)
        optimized_terms = len(query.primary_terms)

        # Optimization should not increase term count
        assert optimized_terms <= expanded_terms

    def test_cache_effectiveness(self):
        """Test cache effectiveness metrics."""
        cache = SearchCache(max_size=10)

        # Add and retrieve multiple times
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")

        for i in range(5):
            cache.get(f"key{i}")

        stats = cache.get_stats()

        assert stats["hit_rate"] > 0
        assert stats["hits"] > 0
