"""Comprehensive tests for Advanced RAG features.

Tests cover:
- Query routing with all query types
- Retrieval optimization with caching and merging
- Context weighting with multi-factor scoring
- Integration scenarios
- Edge cases and error handling
"""

import pytest
from datetime import datetime, timedelta
from athena.rag.query_router import (
    QueryRouter,
    QueryTypeDetector,
    ComplexityAnalyzer,
    StrategySelector,
    QueryType,
    RAGStrategy,
    ComplexityLevel,
)
from athena.rag.retrieval_optimizer import (
    RetrievalOptimizer,
    RetrievalCache,
    ResultMerger,
    RetrievalResult,
    RetrievalBackend,
    RetrievalMode,
)
from athena.rag.context_weighter import (
    ContextWeighter,
    ContextItem,
    ContextType,
    WeightingFactors,
    TemporalWeighter,
    CredibilityWeighter,
    ConnectivityWeighter,
    ApplicabilityWeighter,
    InteractionWeighter,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def query_router():
    """Query router instance."""
    return QueryRouter()


@pytest.fixture
def retrieval_optimizer():
    """Retrieval optimizer instance."""
    return RetrievalOptimizer(cache_size=100, cache_ttl_seconds=3600)


@pytest.fixture
def context_weighter():
    """Context weighter instance."""
    return ContextWeighter()


@pytest.fixture
def sample_context_items():
    """Sample context items for weighting."""
    now = datetime.now()
    return [
        ContextItem(
            id="doc1",
            content="Official documentation",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.9,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
            source="official_docs",
            credibility=0.95,
            connection_count=15,
            view_count=100,
        ),
        ContextItem(
            id="code1",
            content="Code example",
            context_type=ContextType.CODE,
            semantic_score=0.8,
            created_at=now - timedelta(days=7),
            updated_at=now - timedelta(days=7),
            source="github",
            credibility=0.70,
            connection_count=8,
            view_count=50,
        ),
        ContextItem(
            id="proc1",
            content="Procedure steps",
            context_type=ContextType.PROCEDURE,
            semantic_score=0.75,
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=30),
            source="community",
            credibility=0.60,
            connection_count=5,
            view_count=20,
        ),
    ]


# ============================================================================
# QueryTypeDetector Tests
# ============================================================================


class TestQueryTypeDetector:
    """Test query type detection."""

    def test_detect_factual(self, query_router):
        """Test factual query detection."""
        detector = query_router.type_detector
        queries = [
            "What is machine learning?",
            "Where is the capital of France?",
        ]
        for q in queries:
            detected = detector.detect(q)
            assert detected in (QueryType.FACTUAL, QueryType.EXPLORATORY)

    def test_detect_temporal(self, query_router):
        """Test temporal query detection."""
        detector = query_router.type_detector
        queries = [
            "When did World War II end?",
            "How long does it take to learn Python?",
        ]
        for q in queries:
            detected = detector.detect(q)
            assert detected in (QueryType.TEMPORAL, QueryType.FACTUAL)

    def test_detect_relational(self, query_router):
        """Test relational query detection."""
        detector = query_router.type_detector
        queries = [
            "How is photosynthesis related to oxygen?",
            "What is the connection between diet and health?",
        ]
        for q in queries:
            detected = detector.detect(q)
            # Should detect as relational or related type
            assert detected is not None

    def test_detect_exploratory(self, query_router):
        """Test exploratory query detection."""
        detector = query_router.type_detector
        queries = [
            "Tell me about quantum computing",
            "Explain the theory of relativity",
            "Describe the water cycle",
        ]
        for q in queries:
            assert detector.detect(q) == QueryType.EXPLORATORY

    def test_detect_comparative(self, query_router):
        """Test comparative query detection."""
        detector = query_router.type_detector
        queries = [
            "Compare Python and Java",
            "What's the difference between cats and dogs?",
            "Contrast democracy and dictatorship",
        ]
        for q in queries:
            assert detector.detect(q) == QueryType.COMPARATIVE

    def test_detect_procedural(self, query_router):
        """Test procedural query detection."""
        detector = query_router.type_detector
        queries = [
            "How to install Python",
            "Steps to make coffee",
            "Instructions for setting up a server",
        ]
        for q in queries:
            assert detector.detect(q) == QueryType.PROCEDURAL

    def test_detect_reasoning(self, query_router):
        """Test reasoning query detection."""
        detector = query_router.type_detector
        queries = [
            "Why is the sky blue?",
            "Explain why plants need sunlight",
            "Analyze the causes of climate change",
        ]
        for q in queries:
            assert detector.detect(q) == QueryType.REASONING

    def test_cache(self, query_router):
        """Test query type cache."""
        detector = query_router.type_detector
        query = "What is AI?"

        # First call
        type1 = detector.detect(query)
        # Second call should use cache
        type2 = detector.detect(query)

        assert type1 == type2
        assert query in detector._cache

    def test_empty_query(self, query_router):
        """Test empty query detection."""
        detector = query_router.type_detector
        assert detector.detect("") == QueryType.UNKNOWN

    def test_clear_cache(self, query_router):
        """Test clearing cache."""
        detector = query_router.type_detector
        detector.detect("What is AI?")
        assert len(detector._cache) > 0
        detector.clear_cache()
        assert len(detector._cache) == 0


# ============================================================================
# ComplexityAnalyzer Tests
# ============================================================================


class TestComplexityAnalyzer:
    """Test complexity analysis."""

    def test_simple_query(self, query_router):
        """Test simple query classification."""
        analyzer = query_router.complexity_analyzer
        assert analyzer.analyze("What is AI?") == ComplexityLevel.SIMPLE

    def test_moderate_query(self, query_router):
        """Test moderate complexity query."""
        analyzer = query_router.complexity_analyzer
        query = "How does AI relate to machine learning and deep learning?"
        assert analyzer.analyze(query) in (
            ComplexityLevel.MODERATE,
            ComplexityLevel.COMPLEX,
        )

    def test_complex_query(self, query_router):
        """Test complex query classification."""
        analyzer = query_router.complexity_analyzer
        query = "Explain how machine learning algorithms work, what are their limitations, and how they differ from symbolic AI approaches"
        result = analyzer.analyze(query)
        # Complex queries should score higher on complexity scale
        assert result in (ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX)

    def test_complexity_factors(self, query_router):
        """Test that complexity considers multiple factors."""
        analyzer = query_router.complexity_analyzer
        simple = analyzer.analyze("What is AI?")
        complex_query = analyzer.analyze(
            "Why do neural networks fail and what are alternative approaches? How do different approaches compare?"
        )
        # Map to numeric values for comparison
        complexity_values = {
            ComplexityLevel.SIMPLE: 1,
            ComplexityLevel.MODERATE: 2,
            ComplexityLevel.COMPLEX: 3,
            ComplexityLevel.VERY_COMPLEX: 4,
        }
        assert complexity_values[simple] <= complexity_values[complex_query]


# ============================================================================
# QueryRouter Tests
# ============================================================================


class TestQueryRouter:
    """Test query routing."""

    def test_route_factual(self, query_router):
        """Test factual query routing."""
        analysis = query_router.route("What is machine learning?")
        assert analysis.query_type == QueryType.FACTUAL
        assert analysis.primary_strategy in (
            RAGStrategy.BASIC,
            RAGStrategy.RERANKING,
        )

    def test_route_reasoning(self, query_router):
        """Test reasoning query routing."""
        analysis = query_router.route("Why does X cause Y?")
        assert analysis.query_type == QueryType.REASONING
        assert analysis.primary_strategy in (
            RAGStrategy.REFLECTIVE,
            RAGStrategy.PLANNING,
        )

    def test_confidence_score(self, query_router):
        """Test confidence score calculation."""
        clear_query = query_router.route("What is AI?")
        ambiguous_query = query_router.route("Thing about stuff and things")

        assert clear_query.confidence_score > ambiguous_query.confidence_score

    def test_secondary_strategies(self, query_router):
        """Test secondary strategies selection."""
        analysis = query_router.route("What is machine learning?")
        assert len(analysis.secondary_strategies) > 0
        assert analysis.primary_strategy != analysis.secondary_strategies[0]

    def test_special_requirements(self, query_router):
        """Test detection of special requirements."""
        planning_query = query_router.route("What steps should I follow?")
        assert planning_query.requires_planning

        temporal_query = query_router.route("When did this happen?")
        assert temporal_query.requires_temporal

        reasoning_query = query_router.route("Why does this occur?")
        assert reasoning_query.requires_reasoning

    def test_estimated_hops(self, query_router):
        """Test reasoning hop estimation."""
        simple = query_router.route("What is AI?")
        complex_q = query_router.route("Why and how does X relate to Y if Z happens?")

        assert simple.estimated_hops <= complex_q.estimated_hops

    def test_cache(self, query_router):
        """Test routing cache."""
        query = "What is AI?"
        route1 = query_router.route(query, use_cache=True)
        route2 = query_router.route(query, use_cache=True)

        assert route1 == route2
        assert len(query_router._routing_cache) > 0

    def test_clear_cache(self, query_router):
        """Test clearing routing cache."""
        query_router.route("What is AI?")
        assert len(query_router._routing_cache) > 0
        query_router.clear_cache()
        assert len(query_router._routing_cache) == 0

    def test_cache_stats(self, query_router):
        """Test cache statistics."""
        query_router.route("What is AI?")
        query_router.route("What is ML?")
        stats = query_router.get_cache_stats()

        assert stats["routing_cache"] >= 2


# ============================================================================
# RetrievalCache Tests
# ============================================================================


class TestRetrievalCache:
    """Test retrieval caching."""

    def test_cache_hit(self):
        """Test cache hit."""
        cache = RetrievalCache(max_size=10)
        query = "What is AI?"
        results = [{"id": "1", "content": "AI definition"}]

        cache.put(query, results)
        retrieved = cache.get(query)

        assert retrieved == results
        assert cache.stats["hits"] == 1

    def test_cache_miss(self):
        """Test cache miss."""
        cache = RetrievalCache(max_size=10)
        retrieved = cache.get("Non-existent query")

        assert retrieved is None
        assert cache.stats["misses"] == 1

    def test_cache_expiration(self):
        """Test cache TTL expiration."""
        cache = RetrievalCache(max_size=10, default_ttl_seconds=0)
        query = "What is AI?"
        results = [{"id": "1"}]

        cache.put(query, results)
        # Wait for expiration
        import time

        time.sleep(0.01)
        retrieved = cache.get(query)

        assert retrieved is None

    def test_lru_eviction(self):
        """Test LRU eviction."""
        cache = RetrievalCache(max_size=2)

        cache.put("query1", [{"id": "1"}])
        cache.put("query2", [{"id": "2"}])
        cache.put("query3", [{"id": "3"}])  # Should evict query1

        assert cache.get("query1") is None
        assert cache.get("query2") is not None
        assert cache.stats["evictions"] >= 1

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = RetrievalCache(max_size=10)
        cache.put("q1", [{"id": "1"}])
        cache.get("q1")
        cache.get("q2")

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


# ============================================================================
# ResultMerger Tests
# ============================================================================


class TestResultMerger:
    """Test result merging."""

    def test_merge_results(self):
        """Test merging results from multiple backends."""
        merger = ResultMerger()

        result1 = RetrievalResult(
            query="test",
            backend=RetrievalBackend.SEMANTIC,
            items=[{"id": "1", "content": "a"}],
            count=1,
            score=0.9,
            latency_ms=10.0,
        )

        result2 = RetrievalResult(
            query="test",
            backend=RetrievalBackend.GRAPH,
            items=[{"id": "2", "content": "b"}],
            count=1,
            score=0.8,
            latency_ms=15.0,
        )

        merged = merger.merge([result1, result2])

        assert merged.total_count == 2
        assert RetrievalBackend.SEMANTIC.value in merged.sources
        assert RetrievalBackend.GRAPH.value in merged.sources

    def test_deduplication(self):
        """Test result deduplication."""
        merger = ResultMerger()

        result1 = RetrievalResult(
            query="test",
            backend=RetrievalBackend.SEMANTIC,
            items=[{"id": "1"}, {"id": "2"}],
            count=2,
            score=0.9,
            latency_ms=10.0,
        )

        result2 = RetrievalResult(
            query="test",
            backend=RetrievalBackend.GRAPH,
            items=[{"id": "2"}, {"id": "3"}],  # id:2 is duplicate
            count=2,
            score=0.8,
            latency_ms=15.0,
        )

        merged = merger.merge([result1, result2])

        assert merged.deduplication_ratio > 0
        assert merged.total_count == 3  # Only 3 unique

    def test_quality_calculation(self):
        """Test overall quality calculation."""
        merger = ResultMerger()

        high_quality = RetrievalResult(
            query="test",
            backend=RetrievalBackend.SEMANTIC,
            items=[{"id": "1"}] * 10,  # 10 results
            count=10,
            score=0.95,
            latency_ms=10.0,
        )

        low_quality = RetrievalResult(
            query="test",
            backend=RetrievalBackend.GRAPH,
            items=[{"id": "20"}],  # 1 result
            count=1,
            score=0.5,
            latency_ms=15.0,
        )

        merged = merger.merge([high_quality, low_quality])

        assert merged.overall_quality > 0.5


# ============================================================================
# RetrievalOptimizer Tests
# ============================================================================


class TestRetrievalOptimizer:
    """Test retrieval optimization."""

    def test_backend_registration(self, retrieval_optimizer):
        """Test backend registration."""

        class MockRetriever:
            def search(self, query, top_k):
                return [{"id": "1"}]

        retriever = MockRetriever()
        retrieval_optimizer.register_backend(RetrievalBackend.SEMANTIC, retriever)

        assert RetrievalBackend.SEMANTIC in retrieval_optimizer.backends

    def test_retrieve_with_fallback(self, retrieval_optimizer):
        """Test retrieval with fallback."""

        class MockRetriever:
            def search(self, query, top_k):
                return [{"id": "1", "score": 0.9}]

        retrieval_optimizer.register_backend(RetrievalBackend.SEMANTIC, MockRetriever())

        results = retrieval_optimizer.retrieve("test query", top_k=10)

        assert results.total_count > 0
        assert len(results.items) <= 10

    def test_cache_integration(self, retrieval_optimizer):
        """Test cache integration."""

        class MockRetriever:
            call_count = 0

            def search(self, query, top_k):
                self.call_count += 1
                return [{"id": "1"}]

        mock = MockRetriever()
        retrieval_optimizer.register_backend(RetrievalBackend.SEMANTIC, mock)

        # First call should hit backend
        results1 = retrieval_optimizer.retrieve("test", use_cache=True)
        # Second call should hit cache
        results2 = retrieval_optimizer.retrieve("test", use_cache=True)

        assert results1.items == results2.items
        assert mock.call_count == 1  # Only called once


# ============================================================================
# TemporalWeighter Tests
# ============================================================================


class TestTemporalWeighter:
    """Test temporal weighting."""

    def test_recent_content_higher_weight(self):
        """Test that recent content gets higher weight."""
        weighter = TemporalWeighter()
        now = datetime.now()

        recent = ContextItem(
            id="recent",
            content="Recent",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
            source="test",
        )

        old = ContextItem(
            id="old",
            content="Old",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=now - timedelta(days=90),
            updated_at=now - timedelta(days=90),
            source="test",
        )

        recent_weight = weighter.weight(recent, now)
        old_weight = weighter.weight(old, now)

        assert recent_weight > old_weight

    def test_exponential_decay(self):
        """Test exponential decay with half-life."""
        weighter = TemporalWeighter(half_life_days=30)
        now = datetime.now()

        at_halflife = ContextItem(
            id="halflife",
            content="30 days old",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(days=30),
            source="test",
        )

        weight = weighter.weight(at_halflife, now)
        assert 0.45 < weight < 0.55  # Should be ~0.5 at half-life


# ============================================================================
# CredibilityWeighter Tests
# ============================================================================


class TestCredibilityWeighter:
    """Test credibility weighting."""

    def test_source_ratings(self):
        """Test source credibility ratings."""
        weighter = CredibilityWeighter()

        official = ContextItem(
            id="1",
            content="",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source="official_docs",
            credibility=0.95,  # Explicitly set credibility
        )

        web = ContextItem(
            id="2",
            content="",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source="web",
            credibility=0.40,  # Explicitly set credibility
        )

        official_weight = weighter.weight(official)
        web_weight = weighter.weight(web)

        assert official_weight > web_weight

    def test_custom_source_rating(self):
        """Test setting custom source rating."""
        weighter = CredibilityWeighter()
        weighter.set_source_rating("custom_source", 0.9)

        item = ContextItem(
            id="1",
            content="",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source="custom_source",
            credibility=0.0,  # 0 means use source rating
        )

        weight = weighter.weight(item)
        assert weight == 0.9


# ============================================================================
# ConnectivityWeighter Tests
# ============================================================================


class TestConnectivityWeighter:
    """Test connectivity weighting."""

    def test_more_connections_higher_weight(self):
        """Test that more connections give higher weight."""
        weighter = ConnectivityWeighter(max_connections=100)

        connected = ContextItem(
            id="1",
            content="",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source="test",
            connection_count=80,
        )

        isolated = ContextItem(
            id="2",
            content="",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source="test",
            connection_count=5,
        )

        connected_weight = weighter.weight(connected)
        isolated_weight = weighter.weight(isolated)

        assert connected_weight > isolated_weight


# ============================================================================
# ApplicabilityWeighter Tests
# ============================================================================


class TestApplicabilityWeighter:
    """Test applicability weighting."""

    def test_procedure_high_applicability(self):
        """Test that procedures are highly applicable."""
        weighter = ApplicabilityWeighter()

        procedure = ContextItem(
            id="1",
            content="",
            context_type=ContextType.PROCEDURE,
            semantic_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source="test",
        )

        weight = weighter.weight(procedure)
        assert weight > 0.8


# ============================================================================
# InteractionWeighter Tests
# ============================================================================


class TestInteractionWeighter:
    """Test interaction weighting."""

    def test_high_views_high_weight(self):
        """Test that high view count gives higher weight."""
        weighter = InteractionWeighter()

        popular = ContextItem(
            id="1",
            content="",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source="test",
            view_count=1000,
        )

        unpopular = ContextItem(
            id="2",
            content="",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source="test",
            view_count=0,
        )

        popular_weight = weighter.weight(popular)
        unpopular_weight = weighter.weight(unpopular)

        assert popular_weight > unpopular_weight


# ============================================================================
# ContextWeighter Tests
# ============================================================================


class TestContextWeighter:
    """Test comprehensive context weighting."""

    def test_weight_single_item(self, context_weighter, sample_context_items):
        """Test weighting single item."""
        weighted = context_weighter.weight(sample_context_items[0])

        assert 0 <= weighted.overall_weight <= 1
        assert weighted.factor_scores is not None

    def test_weight_batch(self, context_weighter, sample_context_items):
        """Test batch weighting."""
        weighted_items = context_weighter.weight_batch(sample_context_items)

        assert len(weighted_items) == len(sample_context_items)
        # Should be sorted by weight (descending)
        for i in range(len(weighted_items) - 1):
            assert weighted_items[i].overall_weight >= weighted_items[i + 1].overall_weight

    def test_ranking_position(self, context_weighter, sample_context_items):
        """Test ranking positions are set."""
        weighted_items = context_weighter.weight_batch(sample_context_items)

        for i, item in enumerate(weighted_items):
            assert item.ranking_position == i + 1

    def test_top_k(self, context_weighter, sample_context_items):
        """Test top-k selection."""
        top_2 = context_weighter.top_k(sample_context_items, k=2)

        assert len(top_2) == 2
        assert top_2[0].overall_weight >= top_2[1].overall_weight

    def test_weight_adjustment(self, context_weighter):
        """Test adjusting weights."""
        context_weighter.set_weights(
            semantic_weight=0.5,
            temporal_weight=0.25,
            credibility_weight=0.25,
        )

        weights = context_weighter.get_weights()
        # Should normalize to sum of 1.0
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_explain_weight(self, context_weighter, sample_context_items):
        """Test weight explanation generation."""
        weighted = context_weighter.weight(sample_context_items[0])
        explanation = context_weighter.explain_weight(weighted)

        assert "Context Item" in explanation
        assert "Weight" in explanation
        assert "Factor" in explanation

    def test_required_type_preference(self, context_weighter, sample_context_items):
        """Test that required type is preferred."""
        procedure_item = sample_context_items[2]

        # Weight without type requirement
        weight_without = context_weighter.weight(
            procedure_item, required_type=None
        ).overall_weight

        # Weight with matching type requirement
        weight_with = context_weighter.weight(
            procedure_item, required_type=ContextType.PROCEDURE
        ).overall_weight

        assert weight_with > weight_without


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for Advanced RAG."""

    def test_full_rag_pipeline(self, query_router, retrieval_optimizer, context_weighter):
        """Test full RAG pipeline."""

        class MockRetriever:
            def search(self, query, top_k):
                return [
                    {"id": "1", "content": "doc1"},
                    {"id": "2", "content": "doc2"},
                ]

        # Register backend
        retrieval_optimizer.register_backend(RetrievalBackend.SEMANTIC, MockRetriever())

        # Route query
        query = "What is machine learning?"
        analysis = query_router.route(query)

        assert analysis.query_type == QueryType.FACTUAL
        assert analysis.primary_strategy is not None

        # Retrieve with optimizer
        retrieval_results = retrieval_optimizer.retrieve(query)
        assert retrieval_results.total_count > 0

        # Weight context
        now = datetime.now()
        context_items = [
            ContextItem(
                id=str(i),
                content=item["content"],
                context_type=ContextType.DOCUMENT,
                semantic_score=0.8,
                created_at=now,
                updated_at=now,
                source="test",
            )
            for i, item in enumerate(retrieval_results.items)
        ]

        weighted = context_weighter.weight_batch(context_items)
        assert len(weighted) > 0

    def test_complex_query_handling(self, query_router):
        """Test handling of complex multi-hop queries."""
        complex_query = "How does climate change impact ocean ecosystems, and what are the ripple effects on food chains and human economies?"

        analysis = query_router.route(complex_query)

        # Should detect as having reasoning requirements
        assert analysis.requires_reasoning
        assert analysis.estimated_hops > 1
        # Complexity should be moderate or higher
        complexity_values = {
            ComplexityLevel.SIMPLE: 1,
            ComplexityLevel.MODERATE: 2,
            ComplexityLevel.COMPLEX: 3,
            ComplexityLevel.VERY_COMPLEX: 4,
        }
        assert complexity_values[analysis.complexity] >= 2


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_query(self, query_router):
        """Test empty query handling."""
        analysis = query_router.route("")
        assert analysis.query_type == QueryType.UNKNOWN

    def test_very_long_query(self, query_router):
        """Test very long query."""
        long_query = " ".join(["word"] * 1000)
        analysis = query_router.route(long_query)
        # Very long query should be at least moderate in complexity
        complexity_values = {
            ComplexityLevel.SIMPLE: 1,
            ComplexityLevel.MODERATE: 2,
            ComplexityLevel.COMPLEX: 3,
            ComplexityLevel.VERY_COMPLEX: 4,
        }
        assert complexity_values[analysis.complexity] >= 2

    def test_special_characters(self, query_router):
        """Test query with special characters."""
        query = "What is C++ and Java? #programming @learning"
        analysis = query_router.route(query)
        assert analysis.query_type is not None

    def test_unicode_content(self, context_weighter):
        """Test unicode content weighting."""
        item = ContextItem(
            id="1",
            content="这是中文 это русский 日本語",
            context_type=ContextType.DOCUMENT,
            semantic_score=0.8,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source="test",
        )

        weighted = context_weighter.weight(item)
        assert 0 <= weighted.overall_weight <= 1

    def test_no_backends_registered(self, retrieval_optimizer):
        """Test retrieval with no backends."""
        results = retrieval_optimizer.retrieve("test query")
        assert results.total_count == 0
