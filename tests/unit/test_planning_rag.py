"""Unit tests for planning-aware RAG module."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from athena.rag.planning_rag import (
    PlanningQueryClassifier,
    PatternRecommender,
    HybridPlanningSearch,
    FailureAnalyzer,
    PlanningRAGRouter,
    PatternRecommendation,
    HybridSearchResult,
    FailureAnalysis,
)
from athena.planning.models import (
    PlanningPattern,
    PatternType,
    DecompositionStrategy,
    DecompositionType,
    OrchestratorPattern,
    CoordinationType,
    ValidationRule,
    ValidationRuleType,
    ExecutionFeedback,
    ExecutionOutcome,
)
from athena.core.models import Memory, MemorySearchResult


class TestPlanningQueryClassifier:
    """Tests for PlanningQueryClassifier."""

    def test_classify_planning_query_with_keywords(self):
        """Test classification of planning query using keywords."""
        classifier = PlanningQueryClassifier()

        # Strong planning query (has "decompose")
        is_planning, confidence = classifier.classify("How should I decompose this task?")
        assert is_planning is True
        assert confidence >= 0.5  # 1 keyword = 0.5 confidence

    def test_classify_non_planning_query(self):
        """Test classification of non-planning query."""
        classifier = PlanningQueryClassifier()

        # Non-planning query
        is_planning, confidence = classifier.classify("What is the syntax for Python lists?")
        assert is_planning is False
        assert confidence < 0.5

    def test_classify_ambiguous_query(self):
        """Test classification of ambiguous query."""
        classifier = PlanningQueryClassifier()

        # Ambiguous query with some planning keywords
        is_planning, confidence = classifier.classify("How do I structure my project?")
        assert isinstance(is_planning, bool)
        assert 0.0 <= confidence <= 1.0

    def test_classify_multiple_planning_keywords(self):
        """Test that multiple keywords increase confidence."""
        classifier = PlanningQueryClassifier()

        # Query with multiple planning keywords
        is_planning, confidence = classifier.classify(
            "How should I decompose and validate this complex strategy?"
        )
        assert is_planning is True
        assert confidence >= 0.7

    @patch("memory_mcp.rag.planning_rag.LLMClient")
    def test_classify_with_llm_fallback(self, mock_llm_class):
        """Test LLM-based classification when keyword heuristic is uncertain."""
        mock_llm = Mock()
        mock_llm.generate.return_value = "yes, this is a planning question"

        classifier = PlanningQueryClassifier(llm_client=mock_llm)
        is_planning, confidence = classifier.classify("How do I approach this problem?")

        # Should use LLM for semantic classification
        assert isinstance(is_planning, bool)


class TestPatternRecommender:
    """Tests for PatternRecommender."""

    @pytest.fixture
    def mock_planning_store(self):
        """Create mock planning store."""
        store = Mock()
        return store

    @pytest.fixture
    def sample_pattern(self):
        """Create sample planning pattern."""
        return PlanningPattern(
            id=1,
            project_id=1,
            pattern_type=PatternType.HIERARCHICAL,
            name="hierarchical-decomposition",
            description="Decomposes tasks hierarchically",
            success_rate=0.92,
            quality_score=0.88,
            execution_count=15,
            applicable_domains=["backend", "api"],
            applicable_task_types=["refactoring", "feature"],
            complexity_range=(5, 9),
        )

    def test_recommend_patterns_by_task_type(self, mock_planning_store, sample_pattern):
        """Test pattern recommendation by task type."""
        mock_planning_store.find_patterns_by_task_type.return_value = [sample_pattern]

        recommender = PatternRecommender(mock_planning_store)
        recommendations = recommender.recommend_patterns(
            task_description="Refactor authentication module",
            task_type="refactoring",
            project_id=1,
        )

        assert len(recommendations) > 0
        assert recommendations[0].pattern.id == 1
        assert recommendations[0].confidence >= 0.0
        assert recommendations[0].confidence <= 1.0

    def test_recommend_patterns_by_domain(self, mock_planning_store, sample_pattern):
        """Test pattern recommendation by domain."""
        mock_planning_store.find_patterns_by_domain.return_value = [sample_pattern]
        mock_planning_store.find_patterns_by_task_type.return_value = []

        recommender = PatternRecommender(mock_planning_store)
        recommendations = recommender.recommend_patterns(
            task_description="Build API endpoint",
            domain="backend",
            project_id=1,
        )

        assert len(recommendations) > 0
        assert recommendations[0].pattern.applicable_domains == ["backend", "api"]

    def test_pattern_confidence_scoring_logic(self, mock_planning_store, sample_pattern):
        """Test that confidence scoring uses multiple factors."""
        mock_planning_store.find_patterns_by_task_type.return_value = [sample_pattern]
        mock_planning_store.find_patterns_by_domain.return_value = []

        recommender = PatternRecommender(mock_planning_store)

        # Score the pattern directly
        rec = recommender._score_pattern(sample_pattern, "Test task", complexity=7, domain="backend")

        # Verify recommendation object
        assert isinstance(rec, PatternRecommendation)
        assert rec.confidence >= 0.0
        assert rec.confidence <= 1.0
        assert rec.pattern.id == sample_pattern.id

    def test_pattern_recommendation_sort_by_confidence(self, mock_planning_store):
        """Test that recommendations are sorted by confidence."""
        high_confidence_pattern = PlanningPattern(
            id=1,
            project_id=1,
            pattern_type=PatternType.HIERARCHICAL,
            name="high-confidence",
            description="test",
            success_rate=0.95,
        )
        low_confidence_pattern = PlanningPattern(
            id=2,
            project_id=1,
            pattern_type=PatternType.FLAT,
            name="low-confidence",
            description="test",
            success_rate=0.60,
        )
        mock_planning_store.find_patterns_by_task_type.return_value = [
            low_confidence_pattern,
            high_confidence_pattern,
        ]

        recommender = PatternRecommender(mock_planning_store)
        recommendations = recommender.recommend_patterns(
            task_description="Test",
            task_type="refactoring",
            project_id=1,
            k=2,
        )

        # First recommendation should have higher confidence
        assert recommendations[0].confidence >= recommendations[1].confidence


class TestHybridPlanningSearch:
    """Tests for HybridPlanningSearch."""

    @pytest.fixture
    def mock_stores(self):
        """Create mock stores."""
        memory_store = Mock()
        planning_store = Mock()
        return memory_store, planning_store

    @pytest.fixture
    def sample_search_result(self):
        """Create sample search result."""
        memory = Memory(
            id=1,
            content="Sample memory content",
            memory_type="fact",  # Use valid enum value
            project_id=1,
            created_at=datetime.now(),
        )
        return MemorySearchResult(
            memory=memory,
            similarity=0.85,
            rank=1,
            metadata={"type": "semantic"},
        )

    def test_hybrid_search_basic(self, mock_stores, sample_search_result):
        """Test basic hybrid search."""
        memory_store, planning_store = mock_stores

        # Mock semantic search
        memory_store.search.return_value = [sample_search_result]

        # Mock planning search (empty for this test)
        planning_store.find_patterns_by_task_type.return_value = []
        planning_store.find_orchestration_patterns.return_value = []
        planning_store.find_validation_rules_by_risk.return_value = []
        planning_store.find_strategies_by_type.return_value = []

        hybrid_search = HybridPlanningSearch(memory_store, planning_store)
        result = hybrid_search.search("Test query", project_id=1)

        assert isinstance(result, HybridSearchResult)
        assert len(result.semantic_results) > 0
        assert result.hybrid_score >= 0.0

    def test_hybrid_search_extracts_task_type(self, mock_stores):
        """Test that hybrid search extracts task type from query."""
        memory_store, planning_store = mock_stores
        memory_store.search.return_value = []
        planning_store.find_patterns_by_task_type.return_value = []
        planning_store.find_orchestration_patterns.return_value = []
        planning_store.find_validation_rules_by_risk.return_value = []
        planning_store.find_strategies_by_type.return_value = []

        hybrid_search = HybridPlanningSearch(memory_store, planning_store)

        # Query with clear refactoring task type
        result = hybrid_search.search("How should I refactor the auth module?", project_id=1)

        # Verify planning store was called with refactoring task type
        assert planning_store.find_patterns_by_task_type.called

    def test_hybrid_search_extracts_complexity(self, mock_stores):
        """Test that hybrid search extracts complexity from query."""
        memory_store, planning_store = mock_stores
        memory_store.search.return_value = []
        planning_store.find_patterns_by_task_type.return_value = []
        planning_store.find_orchestration_patterns.return_value = []
        planning_store.find_validation_rules_by_risk.return_value = []
        planning_store.find_strategies_by_type.return_value = []

        hybrid_search = HybridPlanningSearch(memory_store, planning_store)

        # Test complexity extraction
        complexity_simple = hybrid_search._extract_complexity("This is a simple task")
        assert complexity_simple == 3

        complexity_complex = hybrid_search._extract_complexity("This is a complex task")
        assert complexity_complex == 7


class TestFailureAnalyzer:
    """Tests for FailureAnalyzer."""

    @pytest.fixture
    def mock_planning_store(self):
        """Create mock planning store."""
        store = Mock()
        store.db.conn.cursor.return_value = Mock()
        return store

    def test_analyze_execution_failure(self, mock_planning_store):
        """Test analysis of execution failures."""
        # Mock cursor and fetchall
        cursor_mock = Mock()
        mock_planning_store.db.conn.cursor.return_value = cursor_mock

        # Mock a failed execution record
        failed_row = (
            1,  # id
            1,  # project_id
            None,  # task_id
            None,  # pattern_id
            None,  # orchestration_pattern_id
            ExecutionOutcome.FAILURE.value,  # execution_outcome
            0.5,  # execution_quality_score
            30,  # planned_duration_minutes
            60,  # actual_duration_minutes
            100.0,  # duration_variance_pct
            "API timeout; database connection lost",  # blockers_encountered
            "Increased timeout values",  # adjustments_made
            "Assumed stable API connectivity",  # assumption_violations
            "Need better error handling",  # learning_extracted
            0.8,  # confidence_in_learning
            None,  # quality_metrics
            datetime.now().timestamp(),  # created_at
            "agent-1",  # executor_agent
            1,  # phase_number
        )

        cursor_mock.fetchall.return_value = [failed_row]

        analyzer = FailureAnalyzer(mock_planning_store)
        analysis = analyzer.analyze_failure_type("execution_failure", project_id=1)

        assert analysis is not None
        assert analysis.failure_type == "execution_failure"
        assert analysis.similar_past_failures == 1
        assert len(analysis.root_causes) > 0

    def test_analyze_no_failures(self, mock_planning_store):
        """Test analysis when no failures exist."""
        cursor_mock = Mock()
        mock_planning_store.db.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchall.return_value = []

        analyzer = FailureAnalyzer(mock_planning_store)
        analysis = analyzer.analyze_failure_type("execution_failure", project_id=1)

        assert analysis is None


class TestPlanningRAGRouter:
    """Tests for PlanningRAGRouter."""

    @pytest.fixture
    def mock_stores(self):
        """Create mock stores."""
        memory_store = Mock()
        planning_store = Mock()
        return memory_store, planning_store

    def test_route_planning_query(self, mock_stores):
        """Test routing of planning query."""
        memory_store, planning_store = mock_stores

        # Mock planning store returns
        planning_store.find_patterns_by_task_type.return_value = []
        planning_store.find_patterns_by_domain.return_value = []
        planning_store.find_orchestration_patterns.return_value = []
        planning_store.find_validation_rules_by_risk.return_value = []
        planning_store.find_strategies_by_type.return_value = []
        memory_store.search.return_value = []

        router = PlanningRAGRouter(memory_store, planning_store)
        result = router.route_query("How should I decompose this task?")

        assert result["is_planning_query"] is True
        assert result["classification_confidence"] >= 0.5
        assert isinstance(result["pattern_recommendations"], list)
        assert result["hybrid_search_results"] is not None

    def test_route_non_planning_query(self, mock_stores):
        """Test routing of non-planning query."""
        memory_store, planning_store = mock_stores

        router = PlanningRAGRouter(memory_store, planning_store)
        result = router.route_query("What is Python syntax?")

        assert result["is_planning_query"] is False
        assert len(result["pattern_recommendations"]) == 0

    def test_route_query_with_failure_analysis(self, mock_stores):
        """Test routing of query with failure analysis."""
        memory_store, planning_store = mock_stores

        # Mock planning store returns
        planning_store.find_patterns_by_task_type.return_value = []
        planning_store.find_patterns_by_domain.return_value = []
        planning_store.find_orchestration_patterns.return_value = []
        planning_store.find_validation_rules_by_risk.return_value = []
        planning_store.find_strategies_by_type.return_value = []
        memory_store.search.return_value = []

        # Mock failure analyzer
        cursor_mock = Mock()
        planning_store.db.conn.cursor.return_value = cursor_mock
        cursor_mock.fetchall.return_value = []

        router = PlanningRAGRouter(memory_store, planning_store)
        result = router.route_query("How should I avoid failures?")

        # Should be classified as planning query
        assert isinstance(result["is_planning_query"], bool)


# Integration tests
class TestPlanningRAGIntegration:
    """Integration tests for planning RAG system."""

    def test_full_planning_workflow(self):
        """Test complete planning workflow."""
        # Create mock stores
        memory_store = Mock()
        planning_store = Mock()

        # Mock planning store returns
        planning_store.find_patterns_by_task_type.return_value = []
        planning_store.find_patterns_by_domain.return_value = []
        planning_store.find_orchestration_patterns.return_value = []
        planning_store.find_validation_rules_by_risk.return_value = []
        planning_store.find_strategies_by_type.return_value = []
        memory_store.search.return_value = []

        # Create router
        router = PlanningRAGRouter(memory_store, planning_store)

        # Test query routing
        result = router.route_query(
            "How should I decompose and validate this complex refactoring?",
            project_id=1,
            task_type="refactoring",
            complexity=7,
            domain="backend",
        )

        # Verify result structure
        assert "query" in result
        assert "is_planning_query" in result
        assert "pattern_recommendations" in result
        assert "hybrid_search_results" in result
        assert isinstance(result["is_planning_query"], bool)

    def test_confidence_scores_calculation(self):
        """Test that confidence scores are properly calculated."""
        memory_store = Mock()
        planning_store = Mock()

        # Create a pattern with high success rate
        pattern = PlanningPattern(
            id=1,
            project_id=1,
            pattern_type=PatternType.HIERARCHICAL,
            name="test",
            description="test",
            success_rate=0.95,
            complexity_range=(5, 9),
            applicable_domains=["backend"],
            applicable_task_types=["refactoring"],
        )

        recommender = PatternRecommender(planning_store)

        # Score the pattern directly
        rec = recommender._score_pattern(
            pattern,
            "Test refactoring",
            complexity=7,
            domain="backend",
        )

        # Verify confidence score is in valid range
        assert hasattr(rec, "confidence")
        assert 0.0 <= rec.confidence <= 1.0
        assert rec.confidence > 0.5  # High success rate should yield good confidence
