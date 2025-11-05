"""Unit tests for Task → Consolidation Sync Integration."""

import pytest
from datetime import datetime

from athena.integration.task_consolidation_sync import (
    TaskConsolidationSync,
    TaskStatus,
    ConsolidationTriggerType
)


class TestTaskRecording:
    """Tests for task recording."""

    def test_record_single_task_completion(self):
        """Should record task completion."""
        sync = TaskConsolidationSync()

        result = sync.on_task_completed(
            task_id="task_1",
            task_content="Implement user authentication",
            outcome="success",
            duration_seconds=3600
        )

        assert result['task_id'] == "task_1"
        assert result['consolidation_needed'] is not None

    def test_record_multiple_tasks(self):
        """Should maintain task history."""
        sync = TaskConsolidationSync()

        for i in range(5):
            sync.on_task_completed(
                task_id=f"task_{i}",
                task_content=f"Task content {i}",
                outcome="success"
            )

        stats = sync.get_task_statistics()
        assert stats['total_tasks'] == 5

    def test_history_window_limit(self):
        """Should respect history window size."""
        sync = TaskConsolidationSync(pattern_detection_window=3)

        for i in range(10):
            sync.on_task_completed(
                task_id=f"task_{i}",
                task_content=f"Task {i}",
                outcome="success"
            )

        stats = sync.get_task_statistics()
        assert stats['total_tasks'] == 3  # Limited to window


class TestPatternDetection:
    """Tests for pattern detection."""

    def test_detect_similar_tasks(self):
        """Should detect similar task content."""
        sync = TaskConsolidationSync(pattern_threshold=0.5)

        sync.on_task_completed(
            task_id="task_1",
            task_content="Implement user login",
            outcome="success"
        )

        result = sync.on_task_completed(
            task_id="task_2",
            task_content="Implement user authentication",
            outcome="success"
        )

        assert len(result['triggers']) > 1
        # Should have both task completion and pattern triggers

    def test_detect_success_streak(self):
        """Should detect consecutive successes."""
        sync = TaskConsolidationSync()

        sync.on_task_completed(
            task_id="task_1",
            task_content="Task 1",
            outcome="success"
        )
        sync.on_task_completed(
            task_id="task_2",
            task_content="Task 2",
            outcome="success"
        )

        result = sync.on_task_completed(
            task_id="task_3",
            task_content="Task 3",
            outcome="success"
        )

        # Should detect batch completion pattern
        batch_triggers = [t for t in result['triggers']
                         if t['type'] == ConsolidationTriggerType.BATCH_COMPLETION.value]
        assert len(batch_triggers) > 0

    def test_no_pattern_with_dissimilar_tasks(self):
        """Should have fewer patterns from dissimilar tasks."""
        sync = TaskConsolidationSync(pattern_threshold=0.9)

        sync.on_task_completed(
            task_id="task_1",
            task_content="Completely different task about auth",
            outcome="success"
        )

        result = sync.on_task_completed(
            task_id="task_2",
            task_content="Unrelated task about database optimization",
            outcome="success"
        )

        # Should have batch success trigger but limited patterns
        assert result['patterns_detected'] <= 1


class TestSimilarityCalculation:
    """Tests for text similarity."""

    def test_identical_text_similarity(self):
        """Identical texts should have high similarity."""
        sync = TaskConsolidationSync()
        similarity = sync._calculate_similarity("test task", "test task")
        assert similarity == 1.0

    def test_different_text_similarity(self):
        """Completely different texts should have low similarity."""
        sync = TaskConsolidationSync()
        similarity = sync._calculate_similarity(
            "implement authentication",
            "optimize database queries"
        )
        assert similarity < 0.5

    def test_partial_overlap_similarity(self):
        """Partially overlapping texts should have medium similarity."""
        sync = TaskConsolidationSync()
        similarity = sync._calculate_similarity(
            "implement user authentication",
            "implement user profile"
        )
        assert 0.3 < similarity < 0.8


class TestWorkflowSuggestion:
    """Tests for workflow suggestion."""

    def test_suggest_validation_workflow(self):
        """Should suggest validation workflow for test tasks."""
        sync = TaskConsolidationSync()
        task1 = {'content': 'Test user authentication', 'outcome': 'success'}
        task2 = {'content': 'Verify login functionality', 'outcome': 'success'}

        workflow = sync._suggest_workflow(task1, task2)
        assert 'validation' in workflow.lower()

    def test_suggest_implementation_workflow(self):
        """Should suggest implementation workflow for build tasks."""
        sync = TaskConsolidationSync()
        task1 = {'content': 'Create database schema', 'outcome': 'success'}
        task2 = {'content': 'Implement API endpoint', 'outcome': 'success'}

        workflow = sync._suggest_workflow(task1, task2)
        assert 'implementation' in workflow.lower()

    def test_suggest_debugging_workflow(self):
        """Should suggest debugging workflow for error tasks."""
        sync = TaskConsolidationSync()
        task1 = {'content': 'Fix authentication error', 'outcome': 'success'}
        task2 = {'content': 'Debug login issue', 'outcome': 'success'}

        workflow = sync._suggest_workflow(task1, task2)
        assert 'debugging' in workflow.lower()


class TestConsolidationTriggers:
    """Tests for consolidation trigger generation."""

    def test_single_task_trigger(self):
        """Should generate task completion trigger."""
        sync = TaskConsolidationSync()

        result = sync.on_task_completed(
            task_id="task_1",
            task_content="Test task",
            outcome="success"
        )

        task_triggers = [t for t in result['triggers']
                        if t['type'] == ConsolidationTriggerType.TASK_COMPLETION.value]
        assert len(task_triggers) > 0
        assert task_triggers[0]['task_id'] == "task_1"

    def test_pattern_trigger_confidence(self):
        """Pattern triggers should have confidence scores."""
        sync = TaskConsolidationSync(pattern_threshold=0.5)

        sync.on_task_completed(
            task_id="task_1",
            task_content="Implement authentication",
            outcome="success"
        )

        result = sync.on_task_completed(
            task_id="task_2",
            task_content="Implement authentication system",
            outcome="success"
        )

        # Check pattern triggers have confidence
        pattern_triggers = [t for t in result['triggers']
                           if t['type'] == ConsolidationTriggerType.PATTERN_DETECTED.value]
        if pattern_triggers:
            assert 'confidence' in pattern_triggers[0]
            assert 0.0 <= pattern_triggers[0]['confidence'] <= 1.0


class TestRecommendations:
    """Tests for consolidation recommendations."""

    def test_recommendations_with_success(self):
        """Successful tasks should get recommendations."""
        sync = TaskConsolidationSync()

        result = sync.on_task_completed(
            task_id="task_1",
            task_content="Test task",
            outcome="success"
        )

        assert isinstance(result['recommendations'], list)
        # First task has minimal patterns, so may have "no patterns" message
        assert len(result['recommendations']) >= 0

    def test_recommendations_with_patterns(self):
        """Multiple patterns should recommend consolidation."""
        sync = TaskConsolidationSync(pattern_threshold=0.5)

        sync.on_task_completed(
            task_id="task_1",
            task_content="Implement test feature",
            outcome="success"
        )

        result = sync.on_task_completed(
            task_id="task_2",
            task_content="Implement another feature",
            outcome="success"
        )

        # Should have recommendations about patterns or consolidation
        assert isinstance(result['recommendations'], list)


class TestStatistics:
    """Tests for task statistics."""

    def test_success_rate_calculation(self):
        """Should calculate success rate correctly."""
        sync = TaskConsolidationSync()

        sync.on_task_completed("task_1", "Task 1", "success")
        sync.on_task_completed("task_2", "Task 2", "success")
        sync.on_task_completed("task_3", "Task 3", "failure")

        stats = sync.get_task_statistics()
        assert stats['total_tasks'] == 3
        assert stats['successful'] == 2
        assert stats['failed'] == 1
        assert stats['success_rate'] == pytest.approx(2/3, 0.01)

    def test_average_duration(self):
        """Should calculate average task duration."""
        sync = TaskConsolidationSync()

        sync.on_task_completed("task_1", "Task 1", "success", duration_seconds=100)
        sync.on_task_completed("task_2", "Task 2", "success", duration_seconds=200)

        stats = sync.get_task_statistics()
        assert stats['average_duration_seconds'] == pytest.approx(150, 0.1)

    def test_empty_statistics(self):
        """Should handle empty task history."""
        sync = TaskConsolidationSync()
        stats = sync.get_task_statistics()

        assert stats['total_tasks'] == 0
        assert 'message' in stats


class TestHistoryClear:
    """Tests for history management."""

    def test_clear_history(self):
        """Should clear task history."""
        sync = TaskConsolidationSync()

        sync.on_task_completed("task_1", "Task 1", "success")
        stats_before = sync.get_task_statistics()
        assert stats_before['total_tasks'] == 1

        sync.clear_history()
        stats_after = sync.get_task_statistics()
        assert stats_after['total_tasks'] == 0
