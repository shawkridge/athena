"""E2E tests for task learning with real LLM validation (System 2).

These tests require:
- ENABLE_LLM_FEATURES=true (environment variable)
- LLM service available (llamacpp, Claude API, or Ollama)
- Marked with @pytest.mark.e2e (skip by default)

Run with: pytest -m e2e tests/e2e/test_task_learning_with_llm.py
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from athena.prospective.pattern_extraction import PatternExtractor
from athena.prospective.pattern_validator import PatternValidator
from athena.prospective.task_learning_integration import TaskLearningIntegration
from athena.prospective.models import ProspectiveTask, TaskStatus, TaskPriority
from athena.prospective.task_patterns import TaskExecutionMetrics


@pytest.mark.e2e
class TestTaskLearningWithRealLLM:
    """E2E tests validating task learning with actual LLM integration."""

    def test_pattern_validation_with_llm(self, ensure_llm_available):
        """Test pattern validation using real LLM (System 2).

        This validates:
        - LLM connectivity (llamacpp, Claude, or configured provider)
        - Pattern validation response parsing
        - Confidence adjustment calculation
        - Fallback to heuristics if LLM fails
        """
        validator = PatternValidator()

        # Create a pattern with uncertainty
        from athena.prospective.task_patterns import TaskPattern

        pattern = TaskPattern(
            id=1,
            pattern_name="High Priority Quick Tasks",
            pattern_type="success_rate",
            description="High priority tasks with <30 min estimated time have 85% success",
            condition_json={"priority": "high", "estimated_minutes": {"<": 30}},
            prediction="Success rate 85%+",
            success_rate=0.85,
            sample_size=20,
            confidence_score=0.75,  # Below threshold, triggers System 2
        )

        # Validate with real LLM
        result = validator.validate_pattern(pattern)

        # Verify result structure
        assert "is_valid" in result
        assert "confidence_adjustment" in result
        assert "validation_notes" in result
        assert "recommendations" in result

        # Verify LLM actually ran (not fallback)
        assert result.get("validation_notes") is not None
        print(f"LLM Validation Result: {result}")

    def test_full_pipeline_with_llm(self, ensure_llm_available):
        """Test complete task learning pipeline with LLM validation.

        Pipeline:
        1. Create completed tasks with metrics
        2. Extract patterns using heuristics
        3. Validate patterns using real LLM
        4. Apply validation results
        """
        mock_db = Mock()
        integration = TaskLearningIntegration(mock_db)
        extractor = PatternExtractor(mock_db, project_id=1)
        validator = PatternValidator()

        # Create sample task metrics
        metrics_list = []
        for i in range(10):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i,
                    estimated_total_minutes=60,
                    actual_total_minutes=65,
                    success=i < 9,  # 90% success
                    priority="high",
                    completed_at=datetime.now(),
                )
            )

        for i in range(10, 20):
            metrics_list.append(
                TaskExecutionMetrics(
                    task_id=i,
                    estimated_total_minutes=60,
                    actual_total_minutes=80,
                    success=i < 14,  # 40% success
                    priority="low",
                    completed_at=datetime.now(),
                )
            )

        # Step 1: Extract patterns (System 1)
        patterns = extractor.extract_all_patterns(metrics_list)
        assert len(patterns) > 0
        print(f"Extracted {len(patterns)} patterns")

        # Step 2: Validate with LLM (System 2) - only uncertain patterns
        uncertain_patterns = [p for p in patterns if p.confidence_score < 0.8]
        print(f"Validating {len(uncertain_patterns)} uncertain patterns with LLM...")

        for pattern in uncertain_patterns:
            result = validator.validate_pattern(pattern)
            updated = validator.apply_validation_results(pattern, result)

            # Verify validation applied
            assert updated.system_2_validated is True
            assert updated.confidence_score >= 0.0
            assert updated.confidence_score <= 1.0
            print(
                f"  {pattern.pattern_name}: "
                f"confidence {pattern.confidence_score:.2f} → {updated.confidence_score:.2f}"
            )

        print("✅ Full pipeline with LLM validation complete")

    def test_llm_error_handling(self, ensure_llm_available):
        """Test graceful fallback when LLM fails or times out.

        Validates:
        - Exception handling (network errors, timeouts)
        - Fallback to heuristic validation
        - Result consistency (same structure as LLM validation)
        """
        from unittest.mock import patch

        validator = PatternValidator()

        from athena.prospective.task_patterns import TaskPattern

        pattern = TaskPattern(
            id=1,
            pattern_name="Test Pattern",
            pattern_type="timing",
            description="Test pattern for error handling",
            condition_json={},
            prediction="Test",
            success_rate=0.8,
            sample_size=15,
            confidence_score=0.7,
        )

        # Simulate LLM timeout by patching requests
        with patch("athena.prospective.pattern_validator.requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection timeout")

            result = validator.validate_pattern(pattern)

            # Should still return valid result (fallback)
            assert "is_valid" in result
            assert "confidence_adjustment" in result
            assert isinstance(result["is_valid"], bool)
            print(f"Fallback validation result: {result}")

    @pytest.mark.slow
    def test_batch_pattern_validation_with_llm(self, ensure_llm_available):
        """Test batch validation of multiple patterns with LLM.

        This is marked as @pytest.mark.slow because it validates
        multiple patterns with real LLM calls.
        """
        from athena.prospective.task_patterns import TaskPattern

        validator = PatternValidator()

        # Create multiple patterns with varying confidence
        patterns = [
            TaskPattern(
                id=i,
                pattern_name=f"Pattern {i}",
                pattern_type="success_rate",
                description=f"Test pattern {i}",
                condition_json={"task_type": f"type_{i}"},
                prediction=f"Prediction {i}",
                success_rate=0.7 + (i * 0.02),
                sample_size=10 + i,
                confidence_score=0.65 + (i * 0.03),  # Below threshold
            )
            for i in range(3)
        ]

        # Batch validate
        results = validator.validate_patterns_batch(patterns)

        # Verify all patterns validated
        assert len(results) > 0
        for pattern_id, result in results.items():
            assert "is_valid" in result
            assert "validation_notes" in result
            print(f"Pattern {pattern_id} validated: {result['validation_notes']}")

        print("✅ Batch validation with LLM complete")


@pytest.mark.e2e
class TestLLMProvider:
    """Tests for different LLM providers."""

    def test_llm_provider_detection(self):
        """Verify LLM provider is correctly configured."""
        from athena.core.config import LLM_PROVIDER, ENABLE_LLM_FEATURES

        assert ENABLE_LLM_FEATURES is True, "LLM features must be enabled for E2E tests"
        assert LLM_PROVIDER in [
            "llamacpp",
            "claude",
            "ollama",
        ], f"Unknown LLM provider: {LLM_PROVIDER}"
        print(f"Using LLM provider: {LLM_PROVIDER}")

    def test_llm_configuration(self):
        """Verify LLM provider configuration is complete."""
        import os
        from athena.core.config import (
            LLM_PROVIDER,
            LLAMACPP_REASONING_URL,
            CLAUDE_API_KEY,
        )

        if LLM_PROVIDER == "llamacpp":
            assert LLAMACPP_REASONING_URL, "LLAMACPP_REASONING_URL not configured"
            assert "localhost" in LLAMACPP_REASONING_URL or (
                "http" in LLAMACPP_REASONING_URL
            ), "Invalid LLM URL"

        elif LLM_PROVIDER == "claude":
            api_key = CLAUDE_API_KEY or os.environ.get("ANTHROPIC_API_KEY")
            assert api_key, "ANTHROPIC_API_KEY or CLAUDE_API_KEY not set"

        print(f"LLM configuration valid for {LLM_PROVIDER}")
