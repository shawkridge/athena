"""Tests for strategy 7 - synthesis and option comparison."""

import pytest
from athena.synthesis.engine import (
    get_synthesis_engine,
    SynthesisEngine,
    SolutionDimension,
)
from athena.synthesis.option_generator import OptionGenerator
from athena.synthesis.comparison import ComparisonFramework


@pytest.fixture
def synthesis_engine():
    """Create synthesis engine for testing."""
    return get_synthesis_engine()


@pytest.fixture
def option_generator():
    """Create option generator for testing."""
    return OptionGenerator()


@pytest.fixture
def comparison_framework():
    """Create comparison framework for testing."""
    return ComparisonFramework()


def test_synthesis_engine_creation(synthesis_engine):
    """Test synthesis engine initializes correctly."""
    assert synthesis_engine is not None
    assert isinstance(synthesis_engine, SynthesisEngine)


def test_synthesize_problem(synthesis_engine):
    """Test synthesizing solutions for a problem."""
    synthesis = synthesis_engine.synthesize(
        "How do we handle traffic spikes?",
        num_approaches=3,
    )

    assert synthesis.synthesis_id.startswith("synth_")
    assert synthesis.problem_statement == "How do we handle traffic spikes?"
    assert len(synthesis.approaches) == 3
    assert synthesis.summary is not None


def test_synthesis_approaches_have_required_fields(synthesis_engine):
    """Test that approaches have all required fields."""
    synthesis = synthesis_engine.synthesize(
        "How do we improve database performance?",
        num_approaches=2,
    )

    for approach in synthesis.approaches:
        assert approach.approach_id is not None
        assert approach.name is not None
        assert approach.description is not None
        assert approach.pros is not None
        assert approach.cons is not None
        assert approach.risk_level in ["low", "medium", "high"]
        assert approach.effort_days >= 0


def test_option_generator_creates_options(option_generator):
    """Test option generator creates detailed options."""
    options = option_generator.generate_options(
        "How to optimize slow queries?",
        num_options=2,
    )

    assert len(options) == 2

    for option in options:
        assert "name" in option
        assert "description" in option
        assert "scores" in option
        assert "details" in option
        assert option["scores"]["overall"] is not None


def test_option_scores_are_valid(option_generator):
    """Test that option scores are valid (0.0-1.0)."""
    options = option_generator.generate_options("test", num_options=2)

    for option in options:
        scores = option["scores"]
        for score in scores.values():
            assert 0.0 <= score <= 1.0


def test_comparison_framework_compares_approaches(comparison_framework):
    """Test comparison framework can compare approaches."""
    approach_a = {
        "name": "Simple Approach",
        "scores": {
            "simplicity": 0.9,
            "performance": 0.3,
            "scalability": 0.2,
            "maintainability": 0.8,
            "reliability": 0.7,
            "cost": 0.2,
        },
    }

    approach_b = {
        "name": "Complex Approach",
        "scores": {
            "simplicity": 0.3,
            "performance": 0.9,
            "scalability": 0.9,
            "maintainability": 0.4,
            "reliability": 0.9,
            "cost": 0.7,
        },
    }

    result = comparison_framework.compare_approaches(approach_a, approach_b)

    assert result.approach_a == "Simple Approach"
    assert result.approach_b == "Complex Approach"
    assert result.winner is not None
    assert len(result.dimensions) > 0
    assert result.recommendation is not None


def test_comparison_identifies_trade_offs(comparison_framework):
    """Test that comparison identifies trade-offs."""
    approach_a = {
        "name": "Fast But Complex",
        "scores": {
            "simplicity": 0.2,
            "performance": 0.95,
            "scalability": 0.9,
            "maintainability": 0.2,
            "reliability": 0.8,
            "cost": 0.5,
        },
    }

    approach_b = {
        "name": "Simple But Slow",
        "scores": {
            "simplicity": 0.95,
            "performance": 0.2,
            "scalability": 0.2,
            "maintainability": 0.95,
            "reliability": 0.6,
            "cost": 0.3,
        },
    }

    result = comparison_framework.compare_approaches(approach_a, approach_b)

    # Should identify trade-offs
    assert len(result.trade_offs) > 0


def test_comparison_all_approaches(comparison_framework):
    """Test comparing all approaches against each other."""
    approaches = [
        {
            "name": "Approach A",
            "scores": {
                "simplicity": 0.8,
                "performance": 0.5,
                "scalability": 0.3,
                "maintainability": 0.8,
                "reliability": 0.7,
                "cost": 0.2,
            },
        },
        {
            "name": "Approach B",
            "scores": {
                "simplicity": 0.5,
                "performance": 0.9,
                "scalability": 0.8,
                "maintainability": 0.5,
                "reliability": 0.9,
                "cost": 0.6,
            },
        },
        {
            "name": "Approach C",
            "scores": {
                "simplicity": 0.6,
                "performance": 0.7,
                "scalability": 0.6,
                "maintainability": 0.6,
                "reliability": 0.8,
                "cost": 0.4,
            },
        },
    ]

    result = comparison_framework.compare_all(approaches)

    assert result["total_approaches"] == 3
    assert result["best_overall"] is not None
    assert len(result["rankings"]) > 0


def test_find_dominant_approaches(comparison_framework):
    """Test finding Pareto-dominant approaches."""
    approaches = [
        {
            "name": "Dominated",
            "scores": {
                "simplicity": 0.5,
                "performance": 0.5,
                "scalability": 0.5,
                "maintainability": 0.5,
                "reliability": 0.5,
                "cost": 0.5,
            },
        },
        {
            "name": "Dominant",
            "scores": {
                "simplicity": 0.8,
                "performance": 0.8,
                "scalability": 0.8,
                "maintainability": 0.8,
                "reliability": 0.8,
                "cost": 0.2,
            },
        },
    ]

    dominant = comparison_framework.find_dominant(approaches)

    assert "Dominant" in dominant
    assert len(dominant) >= 1


def test_rank_by_criteria(comparison_framework):
    """Test ranking approaches by specific criteria."""
    approaches = [
        {
            "name": "Fast",
            "scores": {
                "performance": 0.95,
                "simplicity": 0.2,
            },
        },
        {
            "name": "Simple",
            "scores": {
                "performance": 0.3,
                "simplicity": 0.95,
            },
        },
    ]

    rankings = comparison_framework.rank_by_criteria(
        approaches,
        ["performance", "simplicity"],
    )

    assert "performance" in rankings
    assert "simplicity" in rankings
    assert rankings["performance"][0]["name"] == "Fast"
    assert rankings["simplicity"][0]["name"] == "Simple"


def test_synthesis_multiple_problems(synthesis_engine):
    """Test synthesizing for different problem types."""
    problems = [
        "How do we improve performance?",
        "How do we scale to 1 million users?",
        "How do we ensure reliability?",
    ]

    for problem in problems:
        synthesis = synthesis_engine.synthesize(problem, num_approaches=2)
        assert synthesis.problem_statement == problem
        assert len(synthesis.approaches) >= 1


def test_synthesis_with_context(synthesis_engine):
    """Test synthesis with additional context."""
    synthesis = synthesis_engine.synthesize(
        "How do we handle payment processing?",
        context={
            "budget": "limited",
            "team_size": "2 engineers",
            "timeline": "2 weeks",
        },
        num_approaches=2,
    )

    assert synthesis.context is not None
    assert len(synthesis.approaches) >= 1


def test_solution_dimension_enum():
    """Test SolutionDimension enum has expected values."""
    assert hasattr(SolutionDimension, "COMPLEXITY")
    assert hasattr(SolutionDimension, "PERFORMANCE")
    assert hasattr(SolutionDimension, "SCALABILITY")
    assert hasattr(SolutionDimension, "COST")
    assert hasattr(SolutionDimension, "RISK")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
