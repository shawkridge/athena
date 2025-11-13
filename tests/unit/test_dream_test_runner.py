"""Tests for dream test runner."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from athena.testing.dream_test_runner import DreamTestRunner
from athena.consolidation.dream_models import (
    DreamProcedure,
    DreamType,
    DreamTier,
    DreamStatus,
)
from athena.testing.dream_sandbox import DreamTestResult, TestOutcome


@pytest.fixture
def mock_database():
    """Create mock database."""
    return Mock()


@pytest.fixture
def test_runner(mock_database):
    """Create test runner instance."""
    with patch('athena.testing.dream_test_runner.Database', return_value=mock_database):
        runner = DreamTestRunner(
            db=mock_database,
            sandbox_timeout_seconds=5,
            tests_per_dream=3,
        )
    return runner


@pytest.fixture
def sample_dream():
    """Create sample dream procedure."""
    return DreamProcedure(
        id=1,
        base_procedure_id=100,
        base_procedure_name="base_proc",
        dream_type=DreamType.CONSTRAINT_RELAXATION,
        code='''
def process_data(items: list) -> dict:
    """Process items."""
    _result = {"count": len(items), "items": items}
    return _result
''',
        model_used="deepseek-v3.1",
        reasoning="Test dream",
        status=DreamStatus.PENDING_TEST,
        tier=DreamTier.VIABLE,
        viability_score=0.8,
    )


class TestDreamTestRunner:
    """Test DreamTestRunner."""

    def test_runner_creation(self, test_runner):
        """Test runner can be created."""
        assert test_runner is not None
        assert test_runner.tests_per_dream == 3
        assert test_runner.dreams_tested == 0
        assert test_runner.dreams_passed == 0

    @pytest.mark.asyncio
    async def test_test_dream_creates_inputs(self, test_runner, sample_dream):
        """Test that testing dream generates test inputs."""
        with patch.object(test_runner.sandbox, 'execute_dream', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = DreamTestResult(
                dream_id=1,
                test_outcome=TestOutcome.SUCCESS,
                success=True,
                execution_time_ms=100.0,
                stdout="{}",
                stderr="",
                exit_code=0,
                sandbox_id="test1",
            )

            with patch.object(test_runner.store, 'update_dream', new_callable=AsyncMock):
                result = await test_runner.test_dream(sample_dream)

            assert result["dream_id"] == 1
            assert len(result["test_results"]) > 0

    @pytest.mark.asyncio
    async def test_test_dream_with_no_inputs(self, test_runner, sample_dream):
        """Test handling of dreams with no generated inputs."""
        with patch.object(
            test_runner.test_generator,
            'generate_test_inputs',
            return_value=[]
        ):
            with patch.object(test_runner.sandbox, 'execute_dream', new_callable=AsyncMock) as mock_execute:
                mock_execute.return_value = DreamTestResult(
                    dream_id=1,
                    test_outcome=TestOutcome.SUCCESS,
                    success=True,
                    execution_time_ms=100.0,
                    stdout="{}",
                    stderr="",
                    exit_code=0,
                    sandbox_id="test1",
                )

                with patch.object(test_runner.store, 'update_dream', new_callable=AsyncMock):
                    result = await test_runner.test_dream(sample_dream)

                # Should still execute with empty input fallback
                assert result["dream_id"] == 1

    @pytest.mark.asyncio
    async def test_test_tier1_dreams(self, test_runner, sample_dream):
        """Test testing all Tier 1 dreams."""
        with patch.object(
            test_runner.store,
            'get_by_tier',
            new_callable=AsyncMock,
            return_value=[sample_dream]
        ):
            with patch.object(test_runner, 'test_dream', new_callable=AsyncMock) as mock_test:
                mock_test.return_value = {
                    "dream_id": 1,
                    "dream_type": "constraint_relaxation",
                    "total_tests": 3,
                    "passed": True,
                    "test_results": [],
                }

                result = await test_runner.test_tier1_dreams()

                assert result["success"] is True
                assert result["total_tier1_dreams"] == 1

    @pytest.mark.asyncio
    async def test_test_with_edge_cases(self, test_runner, sample_dream):
        """Test edge case testing."""
        with patch.object(test_runner.sandbox, 'execute_dream', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = DreamTestResult(
                dream_id=1,
                test_outcome=TestOutcome.SUCCESS,
                success=True,
                execution_time_ms=100.0,
                stdout="{}",
                stderr="",
                exit_code=0,
                sandbox_id="test1",
            )

            result = await test_runner.test_with_edge_cases(sample_dream)

            assert result["dream_id"] == 1
            assert "edge_case_count" in result
            assert "results" in result

    @pytest.mark.asyncio
    async def test_update_dream_status(self, test_runner, sample_dream):
        """Test updating dream status after testing."""
        with patch.object(test_runner.store, 'get_dream', new_callable=AsyncMock, return_value=sample_dream):
            with patch.object(test_runner.store, 'update_dream', new_callable=AsyncMock) as mock_update:
                await test_runner._update_dream_status(
                    1,
                    DreamStatus.TESTED,
                    "success",
                    None,
                )

                mock_update.assert_called_once()

    def test_calculate_statistics(self, test_runner):
        """Test statistics calculation."""
        # Add some test results
        for i in range(5):
            result = DreamTestResult(
                dream_id=i,
                test_outcome=TestOutcome.SUCCESS if i < 3 else TestOutcome.TIMEOUT,
                success=i < 3,
                execution_time_ms=100.0 * (i + 1),
                stdout="output",
                stderr="",
                exit_code=0 if i < 3 else 1,
                sandbox_id=f"test{i}",
            )
            test_runner.test_results.append(result)

        stats = test_runner._calculate_statistics()

        assert stats["total_tests"] == 5
        assert stats["passed"] == 3
        assert stats["failed"] == 2
        assert stats["success_rate"] == 0.6
        assert stats["average_execution_time_ms"] > 0

    def test_calculate_statistics_empty(self, test_runner):
        """Test statistics calculation with no results."""
        stats = test_runner._calculate_statistics()

        assert stats["total_tests"] == 0
        assert stats["passed"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_generate_learning_report(self, test_runner):
        """Test generating learning report."""
        # Add some failures to create patterns
        for i in range(3):
            result = DreamTestResult(
                dream_id=i,
                test_outcome=TestOutcome.SYNTAX_ERROR,
                success=False,
                execution_time_ms=100.0,
                stdout="",
                stderr="SyntaxError: invalid syntax",
                exit_code=1,
                sandbox_id=f"test{i}",
                error_category=None,
            )
            test_runner.test_results.append(result)

        report = await test_runner.generate_learning_report()

        assert "total_dreams_tested" in report
        assert "test_statistics" in report

    @pytest.mark.asyncio
    async def test_continuous_testing_stops_after_iterations(self, test_runner):
        """Test continuous testing stops after max iterations."""
        call_count = 0

        async def mock_test_tier1():
            nonlocal call_count
            call_count += 1
            return {"success": True}

        with patch.object(test_runner, 'test_tier1_dreams', side_effect=mock_test_tier1):
            await test_runner.run_continuous_testing(
                interval_seconds=0.001,  # Very short interval
                max_iterations=3
            )

        assert call_count == 3

    def test_parse_result_dict(self):
        """Test parsing result dictionary."""
        result_dict = {
            "success": True,
            "test_outcome": "success",
            "error_category": "syntax",
        }

        parsed = DreamTestRunner._parse_result_dict(result_dict)

        assert parsed["success"] is True
        assert parsed["outcome"] == "success"
        assert parsed["error_category"] == "syntax"

    def test_parse_result_dict_missing_fields(self):
        """Test parsing result dictionary with missing fields."""
        result_dict = {}

        parsed = DreamTestRunner._parse_result_dict(result_dict)

        assert parsed["success"] is False
        assert parsed["outcome"] == "unknown"
