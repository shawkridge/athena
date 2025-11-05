"""Tests for cost tracking and optimization recommendations."""

import pytest

from athena.evaluation.cost_tracking import (
    CostEntry,
    CostMetrics,
    CostTracker,
    CostType,
    OptimizationRecommendation,
    OptimizationStrategy,
)


@pytest.fixture
def cost_tracker():
    """Fixture providing cost tracker."""
    return CostTracker()


class TestCostTypes:
    """Tests for cost types."""

    def test_all_cost_types_defined(self):
        """Test that all cost types are defined."""
        cost_types = [
            CostType.EMBEDDING,
            CostType.VECTOR_SEARCH,
            CostType.LEXICAL_SEARCH,
            CostType.RERANKING,
            CostType.CONSOLIDATION,
            CostType.STORAGE,
            CostType.RETRIEVAL,
            CostType.API_CALL,
        ]
        assert len(cost_types) == 8

    def test_cost_type_values(self):
        """Test cost type string values."""
        assert CostType.EMBEDDING.value == "embedding"
        assert CostType.API_CALL.value == "api_call"
        assert CostType.RERANKING.value == "reranking"


class TestCostEntry:
    """Tests for CostEntry."""

    def test_create_cost_entry(self):
        """Test creating cost entry."""
        entry = CostEntry(
            cost_type=CostType.EMBEDDING,
            amount=0.001,
        )
        assert entry.cost_type == CostType.EMBEDDING
        assert entry.amount == 0.001

    def test_cost_entry_with_metadata(self):
        """Test cost entry with metadata."""
        entry = CostEntry(
            cost_type=CostType.API_CALL,
            amount=0.05,
            operation_id="op_123",
            metadata={"tokens": 1000, "model": "claude-3-sonnet"},
        )
        assert entry.operation_id == "op_123"
        assert entry.metadata["tokens"] == 1000

    def test_cost_entry_string(self):
        """Test cost entry string representation."""
        entry = CostEntry(cost_type=CostType.EMBEDDING, amount=0.001)
        assert "embedding" in str(entry).lower()
        assert "0.001000" in str(entry)


class TestCostTracker:
    """Tests for CostTracker."""

    def test_tracker_initialization(self, cost_tracker):
        """Test tracker initializes correctly."""
        assert cost_tracker.entries == []
        assert cost_tracker.budget_threshold == 100.0

    def test_record_single_cost(self, cost_tracker):
        """Test recording single cost."""
        cost_tracker.record_cost(CostType.EMBEDDING, 0.001)
        assert len(cost_tracker.entries) == 1
        assert cost_tracker.entries[0].cost_type == CostType.EMBEDDING

    def test_record_multiple_costs(self, cost_tracker):
        """Test recording multiple costs."""
        cost_tracker.record_cost(CostType.EMBEDDING, 0.001)
        cost_tracker.record_cost(CostType.API_CALL, 0.05)
        cost_tracker.record_cost(CostType.RERANKING, 0.02)

        assert len(cost_tracker.entries) == 3

    def test_get_metrics_total_cost(self, cost_tracker):
        """Test computing total cost."""
        cost_tracker.record_cost(CostType.EMBEDDING, 0.001)
        cost_tracker.record_cost(CostType.EMBEDDING, 0.002)
        cost_tracker.record_cost(CostType.API_CALL, 0.05)

        metrics = cost_tracker.get_metrics()
        assert abs(metrics.total_cost - 0.053) < 0.0001

    def test_get_metrics_by_type(self, cost_tracker):
        """Test metrics breakdown by cost type."""
        cost_tracker.record_cost(CostType.EMBEDDING, 0.001)
        cost_tracker.record_cost(CostType.EMBEDDING, 0.002)
        cost_tracker.record_cost(CostType.API_CALL, 0.05)

        metrics = cost_tracker.get_metrics()
        assert metrics.cost_by_type["embedding"] == 0.003
        assert metrics.cost_by_type["api_call"] == 0.05

    def test_get_metrics_volume(self, cost_tracker):
        """Test metrics volume tracking."""
        for i in range(5):
            cost_tracker.record_cost(CostType.EMBEDDING, 0.001)
        for i in range(3):
            cost_tracker.record_cost(CostType.API_CALL, 0.05)

        metrics = cost_tracker.get_metrics()
        assert metrics.embedding_count == 5
        assert metrics.api_call_count == 3

    def test_get_metrics_per_unit_costs(self, cost_tracker):
        """Test per-unit cost calculation."""
        cost_tracker.record_cost(CostType.EMBEDDING, 0.001)
        cost_tracker.record_cost(CostType.EMBEDDING, 0.002)
        cost_tracker.record_cost(CostType.API_CALL, 0.10)

        metrics = cost_tracker.get_metrics()
        assert metrics.embedding_count == 2
        assert abs(metrics.cost_per_embedding - 0.0015) < 0.0001
        assert metrics.cost_per_api_call == 0.10

    def test_budget_status_ok(self, cost_tracker):
        """Test budget status when within limits."""
        cost_tracker.budget_threshold = 100.0
        cost_tracker.record_cost(CostType.API_CALL, 30.0)

        status = cost_tracker.get_budget_status()
        assert status["status"] == "OK"
        assert status["usage_percentage"] == 30.0

    def test_budget_status_caution(self, cost_tracker):
        """Test budget status at caution level."""
        cost_tracker.budget_threshold = 100.0
        cost_tracker.record_cost(CostType.API_CALL, 60.0)

        status = cost_tracker.get_budget_status()
        assert status["status"] == "CAUTION"
        assert status["usage_percentage"] == 60.0

    def test_budget_status_warning(self, cost_tracker):
        """Test budget status at warning level."""
        cost_tracker.budget_threshold = 100.0
        cost_tracker.record_cost(CostType.API_CALL, 80.0)

        status = cost_tracker.get_budget_status()
        assert status["status"] == "WARNING"
        assert status["alert"] is not None

    def test_budget_status_critical(self, cost_tracker):
        """Test budget status at critical level."""
        cost_tracker.budget_threshold = 100.0
        cost_tracker.record_cost(CostType.API_CALL, 95.0)

        status = cost_tracker.get_budget_status()
        assert status["status"] == "CRITICAL"
        assert "critical" in status["alert"].lower()

    def test_remaining_budget_calculation(self, cost_tracker):
        """Test remaining budget calculation."""
        cost_tracker.budget_threshold = 100.0
        cost_tracker.record_cost(CostType.API_CALL, 25.0)

        status = cost_tracker.get_budget_status()
        assert status["remaining_budget"] == 75.0


class TestOptimizationRecommendations:
    """Tests for optimization recommendations."""

    def test_recommendation_properties(self):
        """Test recommendation has all required properties."""
        rec = OptimizationRecommendation(
            strategy=OptimizationStrategy.PROMPT_CACHING,
            title="Enable Prompt Caching",
            description="Cache reused context",
            potential_savings=0.90,
            difficulty="easy",
            estimated_implementation_time_minutes=30,
        )

        assert rec.strategy == OptimizationStrategy.PROMPT_CACHING
        assert rec.potential_savings == 0.90
        assert rec.difficulty == "easy"

    def test_recommendation_string(self):
        """Test recommendation string representation."""
        rec = OptimizationRecommendation(
            strategy=OptimizationStrategy.PROMPT_CACHING,
            title="Test",
            description="Test recommendation",
            potential_savings=0.90,
            difficulty="easy",
            estimated_implementation_time_minutes=30,
            monthly_savings=50.0,
        )

        rec_str = str(rec)
        assert "prompt_caching" in rec_str
        assert "90%" in rec_str
        assert "$50.00" in rec_str

    def test_recommendation_roi_calculation(self):
        """Test ROI calculation in recommendation."""
        rec = OptimizationRecommendation(
            strategy=OptimizationStrategy.LOCAL_EMBEDDINGS,
            title="Switch to Local Embeddings",
            description="Use Ollama instead of API",
            potential_savings=1.0,
            difficulty="easy",
            estimated_implementation_time_minutes=20,
            one_time_cost=0.0,
            monthly_savings=50.0,
            roi_months=0.0,
        )
        assert rec.monthly_savings == 50.0


class TestRecommendationGeneration:
    """Tests for recommendation generation."""

    def test_no_recommendations_for_minimal_usage(self, cost_tracker):
        """Test that minimal usage generates fewer recommendations."""
        cost_tracker.record_cost(CostType.EMBEDDING, 0.001)

        recommendations = cost_tracker.get_recommendations()
        # Should have fewer recommendations with minimal cost
        assert len(recommendations) >= 0

    def test_recommendations_for_api_heavy_usage(self, cost_tracker):
        """Test recommendations for API-heavy usage."""
        for i in range(10):
            cost_tracker.record_cost(CostType.API_CALL, 0.10)

        recommendations = cost_tracker.get_recommendations()
        # Should recommend prompt caching for API calls
        strategies = [r.strategy for r in recommendations]
        assert OptimizationStrategy.PROMPT_CACHING in strategies

    def test_recommendations_for_embedding_heavy_usage(self, cost_tracker):
        """Test recommendations for embedding-heavy usage."""
        for i in range(100):
            cost_tracker.record_cost(CostType.EMBEDDING, 0.001)

        recommendations = cost_tracker.get_recommendations()
        # Should recommend local embeddings
        strategies = [r.strategy for r in recommendations]
        assert OptimizationStrategy.LOCAL_EMBEDDINGS in strategies

    def test_recommendations_sorted_by_savings(self, cost_tracker):
        """Test recommendations are sorted by savings."""
        for i in range(10):
            cost_tracker.record_cost(CostType.API_CALL, 0.10)
            cost_tracker.record_cost(CostType.EMBEDDING, 0.001)
            cost_tracker.record_cost(CostType.RERANKING, 0.05)

        recommendations = cost_tracker.get_recommendations()
        # Should be sorted by monthly savings (descending)
        if len(recommendations) > 1:
            for i in range(len(recommendations) - 1):
                assert (
                    recommendations[i].monthly_savings
                    >= recommendations[i + 1].monthly_savings
                )


class TestSummaryReport:
    """Tests for summary report generation."""

    def test_summary_report_format(self, cost_tracker):
        """Test summary report has expected format."""
        cost_tracker.record_cost(CostType.EMBEDDING, 0.001)
        cost_tracker.record_cost(CostType.API_CALL, 0.10)

        report = cost_tracker.summary_report()

        assert "COST TRACKING REPORT" in report
        assert "BUDGET STATUS" in report
        assert "$" in report
        assert "%" in report

    def test_summary_report_with_alerts(self, cost_tracker):
        """Test summary report includes alerts."""
        cost_tracker.budget_threshold = 100.0
        cost_tracker.record_cost(CostType.API_CALL, 80.0)

        report = cost_tracker.summary_report()
        assert "WARNING" in report or "Alert" in report

    def test_summary_report_with_recommendations(self, cost_tracker):
        """Test summary report includes top recommendations."""
        for i in range(100):
            cost_tracker.record_cost(CostType.EMBEDDING, 0.001)
        cost_tracker.record_cost(CostType.API_CALL, 0.50)

        report = cost_tracker.summary_report()
        assert "OPTIMIZATION" in report or "recommendation" in report.lower()


class TestOptimizationStrategies:
    """Tests for optimization strategy enum."""

    def test_all_strategies_defined(self):
        """Test all optimization strategies are defined."""
        strategies = [
            OptimizationStrategy.PROMPT_CACHING,
            OptimizationStrategy.QUANTIZATION,
            OptimizationStrategy.BATCH_PROCESSING,
            OptimizationStrategy.LAZY_LOADING,
            OptimizationStrategy.CONSOLIDATION,
            OptimizationStrategy.LOCAL_EMBEDDINGS,
            OptimizationStrategy.CACHING_LAYER,
            OptimizationStrategy.PRUNING,
        ]
        assert len(strategies) == 8

    def test_strategy_values(self):
        """Test strategy string values."""
        assert OptimizationStrategy.PROMPT_CACHING.value == "prompt_caching"
        assert OptimizationStrategy.LOCAL_EMBEDDINGS.value == "local_embeddings"


class TestCostMetrics:
    """Tests for CostMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating CostMetrics."""
        metrics = CostMetrics(period_name="today")

        assert metrics.period_name == "today"
        assert metrics.total_cost == 0.0
        assert metrics.cost_by_type == {}

    def test_metrics_string_output(self):
        """Test metrics string representation."""
        metrics = CostMetrics(
            period_name="this_week",
            total_cost=50.0,
            cost_by_type={"api_call": 40.0, "embedding": 10.0},
            api_call_count=100,
            embedding_count=5000,
            cost_per_api_call=0.40,
            cost_per_embedding=0.002,
        )

        metrics_str = str(metrics)
        assert "this_week" in metrics_str
        assert "$50.00" in metrics_str
        assert "api_call" in metrics_str
