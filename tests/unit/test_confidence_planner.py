"""Unit tests for confidence-aware planning."""

import pytest
from pathlib import Path
from athena.core.database import Database
from athena.integration.confidence_planner import (
    ConfidencePlanner,
    ConfidentStep,
    ConfidentPlan,
)
from athena.prospective.models import Plan


@pytest.fixture
def db(tmp_path: Path):
    """Create test database."""
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def planner(db):
    """Create confidence planner."""
    return ConfidencePlanner(db)


class TestConfidentStep:
    """Test ConfidentStep model."""

    def test_confident_step_creation(self):
        """Test creating a confident step."""
        step = ConfidentStep(
            content="Implement authentication",
            estimated_duration=120,
            confidence_score=0.75,
            confidence_interval=(90, 150),
            risk_level="low",
        )
        assert step.content == "Implement authentication"
        assert step.estimated_duration == 120
        assert step.confidence_score == 0.75

    def test_confident_step_to_dict(self):
        """Test serializing confident step."""
        step = ConfidentStep(
            content="Test feature",
            estimated_duration=60,
            confidence_score=0.8,
            confidence_interval=(45, 75),
            risk_level="low",
        )
        data = step.to_dict()
        assert data["content"] == "Test feature"
        assert data["estimated_duration"] == 60
        assert data["confidence_score"] == 0.8


class TestConfidencePlanner:
    """Test ConfidencePlanner."""

    def test_planner_initialization(self, planner):
        """Test initializing planner."""
        assert planner.db is not None
        assert planner.uncertainty_analyzer is not None

    def test_extract_uncertainty_factors_epistemic(self, planner):
        """Test extracting epistemic uncertainty factors."""
        step = "Implement a complex novel authentication system"
        factors = planner._extract_uncertainty_factors(step)

        assert len(factors) > 0
        assert any("Complex" in f for f in factors)
        assert any("Novel" in f for f in factors)

    def test_extract_uncertainty_factors_aleatoric(self, planner):
        """Test extracting aleatoric uncertainty factors."""
        step = "Integrate with third-party API that depends on network"
        factors = planner._extract_uncertainty_factors(step)

        assert len(factors) > 0
        assert any("third-party" in f.lower() for f in factors)
        assert any("network" in f.lower() for f in factors)

    def test_compute_step_confidence_high(self, planner):
        """Test confidence computation for low-uncertainty step."""
        step = "Run unit tests"
        factors = []  # No uncertainty factors
        confidence = planner._compute_step_confidence(step, factors)

        assert confidence > 0.6
        assert confidence <= 0.95

    def test_compute_step_confidence_low(self, planner):
        """Test confidence computation for high-uncertainty step."""
        step = "Implement novel complex research prototype"
        factors = [
            "Complex task - knowledge uncertainty",
            "Novel approach - untested",
            "Prototype - unvalidated design",
        ]
        confidence = planner._compute_step_confidence(step, factors)

        assert confidence < 0.6
        assert confidence >= 0.1

    def test_compute_confidence_interval(self, planner):
        """Test confidence interval calculation."""
        estimate = 60  # 60 minutes
        confidence = 0.8
        num_factors = 1

        lower, upper = planner._compute_confidence_interval(estimate, confidence, num_factors)

        # Should be reasonable bounds
        assert lower < estimate
        assert upper > estimate
        assert lower >= estimate * 0.5  # At least 50% of estimate
        assert upper >= estimate  # Upper should be > estimate

    def test_confidence_interval_grows_with_uncertainty(self, planner):
        """Test that intervals grow with more uncertainty."""
        estimate = 100

        # Low uncertainty
        _, upper_low = planner._compute_confidence_interval(estimate, 0.8, 0)

        # High uncertainty
        _, upper_high = planner._compute_confidence_interval(estimate, 0.3, 3)

        # High uncertainty should have wider interval
        assert upper_high > upper_low

    def test_compute_risk_level_high_confidence(self, planner):
        """Test risk level for high confidence."""
        assert planner._compute_risk_level(0.85) == "low"
        assert planner._compute_risk_level(0.75) == "medium"

    def test_compute_risk_level_low_confidence(self, planner):
        """Test risk level for low confidence."""
        assert planner._compute_risk_level(0.45) == "high"
        assert planner._compute_risk_level(0.2) == "critical"

    def test_compute_overall_confidence(self, planner):
        """Test computing overall plan confidence."""
        steps = [
            ConfidentStep(content="Step 1", confidence_score=0.9),
            ConfidentStep(content="Step 2", confidence_score=0.7),
            ConfidentStep(content="Step 3", confidence_score=0.5),
        ]

        overall = planner._compute_overall_confidence(steps)

        assert overall > 0
        assert overall <= 1.0
        # Should be below average due to weight toward low values
        assert overall < 0.7

    def test_generate_recommendation_high_confidence(self, planner):
        """Test recommendation for high confidence."""
        rec = planner._generate_recommendation(0.85)
        assert "✅" in rec or "Proceed with confidence" in rec

    def test_generate_recommendation_low_confidence(self, planner):
        """Test recommendation for low confidence."""
        rec = planner._generate_recommendation(0.2)
        assert "🚫" in rec or "Too uncertain" in rec

    def test_build_confident_step(self, planner):
        """Test building a confident step from base step."""
        class MockPlan:
            id = 1
            task_id = 1
            steps = ["step"]

        mock_plan = MockPlan()
        step = "Implement complex authentication with external API"

        confident_step = planner._build_confident_step(step, mock_plan)

        assert confident_step.content == step
        assert confident_step.confidence_score > 0
        assert confident_step.confidence_score < 1
        assert confident_step.risk_level in ["low", "medium", "high", "critical"]
        assert len(confident_step.confidence_interval) == 2


class TestConfidentPlan:
    """Test ConfidentPlan model."""

    def test_confident_plan_creation(self):
        """Test creating a confident plan."""
        step = ConfidentStep(
            content="Test step",
            confidence_score=0.7,
            confidence_interval=(45, 75),
        )
        plan = ConfidentPlan(
            plan_id=1,
            task_id=1,
            steps=[step],
            overall_confidence=0.7,
            overall_risk="medium",
            recommendation="Proceed with caution",
        )

        assert plan.plan_id == 1
        assert len(plan.steps) == 1
        assert plan.overall_confidence == 0.7

    def test_confident_plan_to_dict(self):
        """Test serializing confident plan."""
        step = ConfidentStep(
            content="Test step",
            confidence_score=0.75,
            confidence_interval=(45, 75),
        )
        plan = ConfidentPlan(
            plan_id=1,
            task_id=1,
            steps=[step],
            overall_confidence=0.75,
            overall_risk="medium",
            recommendation="Test",
        )

        data = plan.to_dict()
        assert data["plan_id"] == 1
        assert len(data["steps"]) == 1
        assert data["overall_confidence"] == 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
