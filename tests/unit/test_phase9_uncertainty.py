"""Unit tests for Phase 9.1: Uncertainty-Aware Generation."""

import pytest

from athena.core.database import Database
from athena.phase9.uncertainty import (
    ConfidenceLevel,
    ConfidenceScore,
    ConfidenceScorer,
    PlanAlternative,
    UncertaintyAnalyzer,
    UncertaintyBreakdown,
    UncertaintyStore,
    UncertaintyType,
)


@pytest.fixture
def uncertainty_store(tmp_path):
    """Create uncertainty store for testing."""
    db = Database(str(tmp_path / "test_uncertainty.db"))
    return UncertaintyStore(db)


@pytest.fixture
def analyzer(uncertainty_store):
    """Create analyzer for testing."""
    return UncertaintyAnalyzer(uncertainty_store)


class TestConfidenceScorer:
    """Test ConfidenceScorer functionality."""

    def test_calculate_confidence_level(self):
        """Test confidence level calculation from scores."""
        assert ConfidenceScorer.calculate_confidence_level(0.35) == ConfidenceLevel.VERY_LOW
        assert ConfidenceScorer.calculate_confidence_level(0.50) == ConfidenceLevel.LOW
        assert ConfidenceScorer.calculate_confidence_level(0.70) == ConfidenceLevel.MEDIUM
        assert ConfidenceScorer.calculate_confidence_level(0.82) == ConfidenceLevel.HIGH
        assert ConfidenceScorer.calculate_confidence_level(0.95) == ConfidenceLevel.VERY_HIGH

    def test_score_estimate(self):
        """Test estimate confidence scoring."""
        score = ConfidenceScorer.score_estimate(
            task_id=1,
            estimate=100.0,
            historical_variance=0.10,
            data_points=15,
            estimate_complexity=0.3,
            external_factors=[],
        )

        assert isinstance(score, ConfidenceScore)
        assert score.task_id == 1
        assert score.aspect == "estimate"
        assert 0.0 <= score.value <= 1.0
        assert score.confidence_level in ConfidenceLevel.__members__.values()
        assert score.lower_bound is not None
        assert score.upper_bound is not None
        assert score.lower_bound < score.upper_bound

    def test_score_estimate_with_high_variance(self):
        """Test scoring with high historical variance."""
        low_variance_score = ConfidenceScorer.score_estimate(
            task_id=1,
            estimate=100.0,
            historical_variance=0.05,
            data_points=20,
            estimate_complexity=0.2,
        )

        high_variance_score = ConfidenceScorer.score_estimate(
            task_id=2,
            estimate=100.0,
            historical_variance=0.30,
            data_points=20,
            estimate_complexity=0.2,
        )

        # Low variance should have higher confidence
        assert low_variance_score.value > high_variance_score.value

    def test_score_prediction(self):
        """Test prediction confidence scoring."""
        score = ConfidenceScorer.score_prediction(
            task_id=1,
            prediction="Task will complete on time",
            supporting_data=["history shows 80% on-time delivery", "team has experience"],
            conflicting_data=[],
            historical_accuracy=0.80,
            model_uncertainty=0.10,
        )

        assert score.task_id == 1
        assert score.aspect == "prediction"
        assert 0.0 <= score.value <= 1.0

    def test_score_resource_estimate(self):
        """Test resource requirement scoring."""
        score = ConfidenceScorer.score_resource_estimate(
            task_id=1,
            required_skills=["Python", "React", "PostgreSQL"],
            available_skills=["Python", "React"],
            tool_dependencies=["Docker", "Kubernetes"],
            tools_available=["Docker"],
        )

        assert score.task_id == 1
        assert score.aspect == "resource"
        assert 0.0 <= score.value <= 1.0
        assert "PostgreSQL" in str(score.contradicting_evidence)

    def test_score_timeline(self):
        """Test timeline confidence scoring."""
        score = ConfidenceScorer.score_timeline(
            task_id=1,
            estimated_duration=480,  # 8 hours in minutes
            deadline_days=1,
            dependency_count=0,
            historical_delays=0.0,
        )

        assert score.task_id == 1
        assert score.aspect == "timeline"
        assert 0.0 <= score.value <= 1.0

    def test_generate_confidence_interval(self):
        """Test confidence interval generation."""
        interval = ConfidenceScorer.generate_confidence_interval(
            estimate=100.0,
            variance=0.15,
            confidence_level=0.95,
        )

        assert interval.estimate == 100.0
        assert interval.lower_bound < interval.estimate
        assert interval.upper_bound > interval.estimate
        assert interval.confidence_level == 0.95


class TestUncertaintyStore:
    """Test UncertaintyStore functionality."""

    def test_create_plan_alternative(self, uncertainty_store):
        """Test creating plan alternative."""
        plan = PlanAlternative(
            task_id=1,
            plan_type="sequential",
            steps=["Step 1", "Step 2", "Step 3"],
            estimated_duration_minutes=120,
            confidence_score=0.85,
            risk_factors=["risk1"],
            rank=1,
        )

        saved = uncertainty_store.create_plan_alternative(plan)
        assert saved.id is not None
        assert saved.task_id == 1
        assert saved.plan_type == "sequential"

    def test_list_plan_alternatives(self, uncertainty_store):
        """Test listing plan alternatives."""
        for i in range(3):
            plan = PlanAlternative(
                task_id=1,
                plan_type=f"type_{i}",
                estimated_duration_minutes=100 + i * 10,
                confidence_score=0.70 + i * 0.05,
                rank=i + 1,
            )
            uncertainty_store.create_plan_alternative(plan)

        plans = uncertainty_store.list_plan_alternatives(task_id=1)
        assert len(plans) == 3
        # Should be sorted by confidence score descending
        assert plans[0].confidence_score >= plans[1].confidence_score

    def test_create_confidence_score(self, uncertainty_store):
        """Test creating confidence score."""
        score = ConfidenceScore(
            task_id=1,
            aspect="estimate",
            value=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            uncertainty_sources=[UncertaintyType.EPISTEMIC],
            contributing_factors={"variance": 0.8, "data": 0.9},
        )

        saved = uncertainty_store.create_confidence_score(score)
        assert saved.id is not None
        assert saved.value == 0.85

    def test_get_confidence_scores(self, uncertainty_store):
        """Test retrieving confidence scores."""
        score1 = ConfidenceScore(
            task_id=1,
            aspect="estimate",
            value=0.85,
            confidence_level=ConfidenceLevel.HIGH,
        )
        score2 = ConfidenceScore(
            task_id=1,
            aspect="timeline",
            value=0.75,
            confidence_level=ConfidenceLevel.MEDIUM,
        )

        uncertainty_store.create_confidence_score(score1)
        uncertainty_store.create_confidence_score(score2)

        scores = uncertainty_store.get_confidence_scores(task_id=1)
        assert len(scores) == 2

        estimate_scores = uncertainty_store.get_confidence_scores(task_id=1, aspect="estimate")
        assert len(estimate_scores) == 1
        assert estimate_scores[0].aspect == "estimate"

    def test_create_uncertainty_breakdown(self, uncertainty_store):
        """Test creating uncertainty breakdown."""
        breakdown = UncertaintyBreakdown(
            task_id=1,
            total_uncertainty=0.25,
            uncertainty_sources={
                "variance": {"type": "epistemic", "value": 0.15},
                "external": {"type": "aleatoric", "value": 0.10},
            },
            reducible_uncertainty=0.15,
            irreducible_uncertainty=0.10,
            mitigations=["Collect more data", "Prepare for external factors"],
        )

        saved = uncertainty_store.create_uncertainty_breakdown(breakdown)
        assert saved.task_id == 1
        assert saved.total_uncertainty == 0.25


class TestUncertaintyAnalyzer:
    """Test UncertaintyAnalyzer functionality."""

    def test_analyze_uncertainty(self, analyzer):
        """Test uncertainty analysis."""
        breakdown = analyzer.analyze_uncertainty(
            task_id=1,
            estimate=100.0,
            external_factors=["weather", "vendor delays"],
            data_points=8,
            historical_variance=0.15,
        )

        assert breakdown.task_id == 1
        assert 0.0 <= breakdown.total_uncertainty <= 1.0
        assert breakdown.reducible_uncertainty + breakdown.irreducible_uncertainty > 0
        assert len(breakdown.mitigations) > 0

    def test_generate_alternative_plans(self, analyzer):
        """Test generating alternative plans."""
        plans = analyzer.generate_alternative_plans(
            task_id=1,
            base_estimate=100.0,
        )

        assert len(plans) >= 3  # At least sequential, parallel, iterative
        assert all(p.task_id == 1 for p in plans)
        assert all(0.0 <= p.confidence_score <= 1.0 for p in plans)
        # Should be sorted by confidence score
        assert plans[0].confidence_score >= plans[-1].confidence_score

    def test_compare_plan_alternatives(self, analyzer):
        """Test comparing plan alternatives."""
        plans = analyzer.generate_alternative_plans(task_id=1, base_estimate=100.0)
        comparison = analyzer.compare_plan_alternatives(plans)

        assert "total_alternatives" in comparison
        assert "best_confidence" in comparison
        assert "fastest_plan" in comparison
        assert "risk_assessment" in comparison
        assert comparison["total_alternatives"] == len(plans)

    def test_record_confidence_outcome(self, analyzer):
        """Test recording confidence prediction outcome."""
        calib = analyzer.record_confidence_outcome(
            project_id=1,
            aspect="estimate",
            predicted_confidence=0.85,
            actual_outcome=True,
        )

        assert calib.project_id == 1
        assert calib.predicted_confidence == 0.85
        assert calib.actual_outcome is True
        assert calib.calibration_error is not None

    def test_analyze_calibration(self, analyzer):
        """Test calibration analysis."""
        # Record several predictions
        for i in range(15):
            analyzer.record_confidence_outcome(
                project_id=1,
                aspect="estimate",
                predicted_confidence=0.80,
                actual_outcome=i % 2 == 0,  # 50% outcome rate
            )

        trend = analyzer.analyze_calibration(project_id=1, aspect="estimate")

        assert trend.project_id == 1
        assert trend.aspect == "estimate"
        assert 0.0 <= trend.average_confidence <= 1.0
        assert trend.sample_size > 0

    def test_empty_calibration_analysis(self, analyzer):
        """Test calibration analysis with no data."""
        trend = analyzer.analyze_calibration(project_id=999, aspect="estimate")

        assert trend.project_id == 999
        assert trend.sample_size == 0
        assert len(trend.recommendations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
