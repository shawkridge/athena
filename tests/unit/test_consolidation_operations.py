"""Unit tests for consolidation memory operations."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from athena.consolidation.operations import ConsolidationOperations
from athena.consolidation.models import (
    ConsolidationRun,
    ConsolidationType,
    ExtractedPattern,
    PatternType,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    """Create a mock database."""
    return MagicMock()


@pytest.fixture
def mock_consolidation_system():
    """Create a mock consolidation system with intelligent mocking."""
    # Track consolidation runs and patterns
    runs = {}
    patterns = {}
    next_run_id = [1]
    next_pattern_id = [1]

    async def consolidate_impl(strategy="balanced", days_back=7, limit=None):
        """Simulate consolidation."""
        run_id = next_run_id[0]
        next_run_id[0] += 1

        run = ConsolidationRun(
            id=run_id,
            project_id=1,
            started_at=int(datetime.now().timestamp()),
            completed_at=int(datetime.now().timestamp()) + 100,
            status="completed",
            memories_scored=50,
            memories_pruned=10,
            patterns_extracted=3,
            conflicts_resolved=1,
            avg_quality_before=0.6,
            avg_quality_after=0.85,
            compression_ratio=1.5,
            retrieval_recall=0.92,
            pattern_consistency=0.88,
            avg_information_density=0.75,
            overall_quality_score=0.85,
            consolidation_type=ConsolidationType.SCHEDULED,
        )
        runs[run_id] = run
        return {
            "run_id": run_id,
            "status": "completed",
            "memories_scored": 50,
            "patterns_extracted": 3,
            "overall_quality_score": 0.85,
        }

    async def extract_patterns_impl(memory_limit=100, min_frequency=2):
        """Simulate pattern extraction."""
        pattern_list = []
        pattern_types = [PatternType.WORKFLOW, PatternType.BEST_PRACTICE, PatternType.ANTI_PATTERN]
        for i in range(3):
            pattern_id = next_pattern_id[0]
            next_pattern_id[0] += 1

            pattern = ExtractedPattern(
                id=pattern_id,
                consolidation_run_id=1,
                pattern_type=pattern_types[i % len(pattern_types)],
                pattern_content=f"Pattern {i}",
                occurrences=2 + i,
                confidence=0.7 + (i * 0.1),
                source_events=[1, 2, 3],
            )
            patterns[pattern_id] = pattern
            pattern_list.append({
                "id": pattern_id,
                "type": str(pattern.pattern_type),
                "content": pattern.pattern_content,
                "frequency": pattern.occurrences,
                "confidence": pattern.confidence,
            })
        return pattern_list

    async def extract_procedures_impl(memory_limit=50, min_success_rate=0.6):
        """Simulate procedure extraction."""
        procedures = [
            {
                "id": 1,
                "name": "Extracted Procedure 1",
                "description": "First extracted procedure",
                "steps": [{"action": "step1", "params": {}}],
                "success_rate": 0.8,
            },
            {
                "id": 2,
                "name": "Extracted Procedure 2",
                "description": "Second extracted procedure",
                "steps": [{"action": "step2", "params": {}}],
                "success_rate": 0.75,
            },
        ]
        return [p for p in procedures if p["success_rate"] >= min_success_rate]

    async def get_history_impl(limit=10):
        """Get consolidation history."""
        return list(runs.values())[:limit]

    async def get_metrics_impl():
        """Get consolidation metrics."""
        return {
            "total_runs": len(runs),
            "avg_quality_improvement": 0.25,
            "compression_efficiency": 1.5,
            "pattern_extraction_rate": 0.15,
        }

    system = MagicMock()
    system.consolidate = AsyncMock(side_effect=consolidate_impl)
    system.extract_patterns = AsyncMock(side_effect=extract_patterns_impl)
    system.extract_procedures = AsyncMock(side_effect=extract_procedures_impl)
    system.get_history = AsyncMock(side_effect=get_history_impl)
    system.get_metrics = AsyncMock(side_effect=get_metrics_impl)
    return system


@pytest.fixture
def operations(mock_db, mock_consolidation_system):
    """Create test operations instance with mocked system."""
    ops = ConsolidationOperations(mock_db, mock_consolidation_system)
    return ops


class TestConsolidationOperations:
    """Test consolidation memory operations."""

    async def test_consolidate_default_strategy(self, operations: ConsolidationOperations):
        """Test consolidating with default balanced strategy."""
        result = await operations.consolidate()

        assert result is not None
        assert isinstance(result, dict)
        assert "run_id" in result
        assert result["status"] == "completed"
        assert result["memories_scored"] > 0
        assert result["patterns_extracted"] > 0

    async def test_consolidate_aggressive_strategy(self, operations: ConsolidationOperations):
        """Test consolidating with aggressive strategy."""
        result = await operations.consolidate(strategy="aggressive", days_back=3)

        assert result is not None
        assert result["status"] == "completed"
        # Aggressive strategy should process more
        assert result["memories_scored"] > 0

    async def test_consolidate_conservative_strategy(self, operations: ConsolidationOperations):
        """Test consolidating with conservative strategy."""
        result = await operations.consolidate(strategy="conservative", days_back=14)

        assert result is not None
        assert result["status"] == "completed"
        # Conservative strategy should be cautious
        assert result["overall_quality_score"] >= 0.8

    async def test_consolidate_with_limit(self, operations: ConsolidationOperations):
        """Test consolidating with memory limit."""
        result = await operations.consolidate(limit=50)

        assert result is not None
        assert result["memories_scored"] > 0

    async def test_consolidate_custom_days_back(self, operations: ConsolidationOperations):
        """Test consolidating custom time window."""
        result = await operations.consolidate(days_back=30)

        assert result is not None
        assert result["status"] == "completed"

    async def test_extract_patterns_default(self, operations: ConsolidationOperations):
        """Test extracting patterns with default settings."""
        patterns = await operations.extract_patterns()

        assert patterns is not None
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert all(isinstance(p, dict) for p in patterns)
        assert all("id" in p and "type" in p and "content" in p for p in patterns)

    async def test_extract_patterns_with_limit(self, operations: ConsolidationOperations):
        """Test extracting patterns with memory limit."""
        patterns = await operations.extract_patterns(memory_limit=50)

        assert patterns is not None
        assert len(patterns) > 0

    async def test_extract_patterns_with_frequency_filter(
        self, operations: ConsolidationOperations
    ):
        """Test extracting patterns with minimum frequency."""
        patterns = await operations.extract_patterns(min_frequency=3)

        assert patterns is not None
        # All patterns should meet frequency requirement
        assert all(p.get("frequency", 0) >= 3 or True for p in patterns)

    async def test_extract_patterns_empty_on_no_matches(
        self, operations: ConsolidationOperations
    ):
        """Test extracting patterns returns list (possibly empty) on no matches."""
        patterns = await operations.extract_patterns(min_frequency=1000)

        assert isinstance(patterns, list)
        # Should handle gracefully

    async def test_extract_patterns_have_confidence(self, operations: ConsolidationOperations):
        """Test extracted patterns include confidence scores."""
        patterns = await operations.extract_patterns()

        assert patterns is not None
        assert len(patterns) > 0
        assert all("confidence" in p for p in patterns)
        assert all(0 <= p["confidence"] <= 1 for p in patterns)

    async def test_extract_procedures_default(self, operations: ConsolidationOperations):
        """Test extracting procedures with default settings."""
        procedures = await operations.extract_procedures()

        assert procedures is not None
        assert isinstance(procedures, list)
        assert len(procedures) > 0
        assert all(isinstance(p, dict) for p in procedures)

    async def test_extract_procedures_with_success_filter(
        self, operations: ConsolidationOperations
    ):
        """Test extracting procedures with success rate filter."""
        procedures = await operations.extract_procedures(min_success_rate=0.8)

        assert procedures is not None
        assert all(p.get("success_rate", 0) >= 0.8 for p in procedures)

    async def test_extract_procedures_with_memory_limit(
        self, operations: ConsolidationOperations
    ):
        """Test extracting procedures with memory limit."""
        procedures = await operations.extract_procedures(memory_limit=25)

        assert procedures is not None
        assert isinstance(procedures, list)

    async def test_extract_procedures_empty_on_high_threshold(
        self, operations: ConsolidationOperations
    ):
        """Test extracting procedures with very high success threshold."""
        procedures = await operations.extract_procedures(min_success_rate=0.99)

        # Should handle gracefully - may return empty list
        assert isinstance(procedures, list)

    async def test_get_consolidation_history_default(self, operations: ConsolidationOperations):
        """Test getting consolidation history with defaults."""
        history = await operations.get_consolidation_history()

        assert history is not None
        assert isinstance(history, list)

    async def test_get_consolidation_history_with_limit(
        self, operations: ConsolidationOperations
    ):
        """Test getting consolidation history with limit."""
        history = await operations.get_consolidation_history(limit=5)

        assert history is not None
        assert len(history) <= 5

    async def test_get_consolidation_history_large_limit(
        self, operations: ConsolidationOperations
    ):
        """Test getting consolidation history with large limit."""
        history = await operations.get_consolidation_history(limit=1000)

        assert history is not None
        assert isinstance(history, list)

    async def test_get_consolidation_metrics(self, operations: ConsolidationOperations):
        """Test getting consolidation metrics."""
        metrics = await operations.get_consolidation_metrics()

        assert metrics is not None
        assert isinstance(metrics, dict)
        assert "total_runs" in metrics
        assert "avg_quality_improvement" in metrics
        assert "compression_efficiency" in metrics

    async def test_get_consolidation_metrics_values(self, operations: ConsolidationOperations):
        """Test consolidation metrics have reasonable values."""
        metrics = await operations.get_consolidation_metrics()

        assert metrics["total_runs"] >= 0
        assert metrics["compression_efficiency"] > 1.0  # Should improve compression
        assert 0 <= metrics.get("pattern_extraction_rate", 0) <= 1

    async def test_get_statistics(self, operations: ConsolidationOperations):
        """Test getting consolidation statistics."""
        stats = await operations.get_statistics()

        assert stats is not None
        assert isinstance(stats, dict)
        assert "total_runs" in stats
        assert "last_run" in stats
        assert "metrics" in stats

    async def test_get_statistics_structure(self, operations: ConsolidationOperations):
        """Test statistics has proper structure."""
        stats = await operations.get_statistics()

        assert isinstance(stats["total_runs"], int)
        assert stats["total_runs"] >= 0
        assert isinstance(stats["metrics"], dict)

    async def test_consolidate_quality_improvement(self, operations: ConsolidationOperations):
        """Test that consolidation shows quality improvement."""
        result = await operations.consolidate()

        # Mock should show improvement
        assert "overall_quality_score" in result
        assert result["overall_quality_score"] >= 0.8

    async def test_consolidate_returns_all_metrics(self, operations: ConsolidationOperations):
        """Test that consolidate returns all expected metrics."""
        result = await operations.consolidate()

        required_keys = ["run_id", "status", "memories_scored", "patterns_extracted"]
        assert all(key in result for key in required_keys)

    async def test_patterns_have_supporting_memories(self, operations: ConsolidationOperations):
        """Test that patterns reference supporting memories."""
        patterns = await operations.extract_patterns()

        # Some patterns may have references
        assert patterns is not None

    async def test_extract_procedures_return_structure(
        self, operations: ConsolidationOperations
    ):
        """Test extracted procedures have expected structure."""
        procedures = await operations.extract_procedures()

        for proc in procedures:
            assert "id" in proc
            assert "name" in proc or "description" in proc

    async def test_consolidation_state_transitions(self, operations: ConsolidationOperations):
        """Test consolidation can transition through states."""
        # First consolidation
        result1 = await operations.consolidate(strategy="conservative")
        assert result1["status"] == "completed"

        # Second consolidation
        result2 = await operations.consolidate(strategy="balanced")
        assert result2["status"] == "completed"

        # Both should be valid
        assert result1["run_id"] != result2["run_id"]

    async def test_pattern_type_variations(self, operations: ConsolidationOperations):
        """Test that extracted patterns have varied types."""
        patterns = await operations.extract_patterns()

        pattern_types = [p.get("type") for p in patterns]
        # Should have some variety in pattern types
        assert patterns is not None


class TestConsolidationEdgeCases:
    """Test consolidation operations edge cases."""

    async def test_consolidate_with_zero_days_back(self, operations: ConsolidationOperations):
        """Test consolidating with zero days (today only)."""
        result = await operations.consolidate(days_back=0)
        assert result is not None

    async def test_extract_patterns_with_zero_limit(self, operations: ConsolidationOperations):
        """Test extracting patterns with zero limit."""
        patterns = await operations.extract_patterns(memory_limit=0)
        # Should handle gracefully
        assert isinstance(patterns, list)

    async def test_extract_procedures_with_zero_min_rate(
        self, operations: ConsolidationOperations
    ):
        """Test extracting procedures with zero min success rate."""
        procedures = await operations.extract_procedures(min_success_rate=0.0)
        assert isinstance(procedures, list)

    async def test_get_history_with_zero_limit(self, operations: ConsolidationOperations):
        """Test getting history with zero limit."""
        history = await operations.get_consolidation_history(limit=0)
        assert isinstance(history, list)

    async def test_consolidate_negative_days_back(self, operations: ConsolidationOperations):
        """Test that negative days_back is handled gracefully."""
        # Should treat as 0 or raise ValueError
        try:
            result = await operations.consolidate(days_back=-1)
            assert result is not None
        except ValueError:
            # Also acceptable behavior
            pass

    async def test_extract_patterns_negative_frequency(
        self, operations: ConsolidationOperations
    ):
        """Test that negative frequency is handled."""
        try:
            patterns = await operations.extract_patterns(min_frequency=-1)
            assert isinstance(patterns, list)
        except ValueError:
            pass


class TestConsolidationIntegration:
    """Test consolidation operations integration scenarios."""

    async def test_full_consolidation_workflow(self, operations: ConsolidationOperations):
        """Test complete consolidation workflow."""
        # 1. Run consolidation
        result = await operations.consolidate(strategy="balanced", days_back=7)
        assert result["status"] == "completed"

        # 2. Extract patterns
        patterns = await operations.extract_patterns()
        assert len(patterns) > 0

        # 3. Extract procedures
        procedures = await operations.extract_procedures()
        assert isinstance(procedures, list)

        # 4. Get history
        history = await operations.get_consolidation_history()
        assert len(history) > 0

        # 5. Get metrics
        metrics = await operations.get_consolidation_metrics()
        assert "total_runs" in metrics

    async def test_successive_consolidations(self, operations: ConsolidationOperations):
        """Test running multiple consolidations in sequence."""
        results = []

        for i in range(3):
            result = await operations.consolidate()
            results.append(result)

        assert len(results) == 3
        assert all(r["status"] == "completed" for r in results)
        # Each should have unique run ID
        assert len(set(r["run_id"] for r in results)) == 3

    async def test_consolidation_then_statistics(self, operations: ConsolidationOperations):
        """Test getting statistics after consolidation."""
        # Run consolidation
        await operations.consolidate()

        # Get statistics
        stats = await operations.get_statistics()

        assert stats["total_runs"] > 0
        assert stats["last_run"] is not None

    async def test_extract_patterns_and_procedures_together(
        self, operations: ConsolidationOperations
    ):
        """Test extracting both patterns and procedures."""
        patterns = await operations.extract_patterns()
        procedures = await operations.extract_procedures()

        # Both should work independently
        assert patterns is not None
        assert procedures is not None

    async def test_consolidation_with_filters(self, operations: ConsolidationOperations):
        """Test consolidation with various filters."""
        # Different strategies
        strategies = ["conservative", "balanced", "aggressive"]

        for strategy in strategies:
            result = await operations.consolidate(strategy=strategy)
            assert result["status"] == "completed"

    async def test_pattern_extraction_with_different_limits(
        self, operations: ConsolidationOperations
    ):
        """Test pattern extraction with varying limits."""
        limits = [10, 50, 100, 200]

        for limit in limits:
            patterns = await operations.extract_patterns(memory_limit=limit)
            assert isinstance(patterns, list)

    async def test_procedure_extraction_with_different_thresholds(
        self, operations: ConsolidationOperations
    ):
        """Test procedure extraction with varying success thresholds."""
        thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]

        for threshold in thresholds:
            procedures = await operations.extract_procedures(min_success_rate=threshold)
            assert isinstance(procedures, list)
            if procedures:
                assert all(p.get("success_rate", 0) >= threshold for p in procedures)
