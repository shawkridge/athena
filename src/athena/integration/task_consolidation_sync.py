"""Task → Consolidation Sync Integration.

Automatically triggers consolidation when tasks complete.

Implements the feedback loop:
Task Completed
  ↓ Hook: PostTaskCompletion
  ↓ Record as episodic event
  ↓ Check for repeated patterns (last 3 tasks)
  ↓ If pattern found (2+ matches):
      - Suggest workflow creation
      - Auto-tag for consolidation
      - Update procedural memory success rates
  ↓ Command: /task-status handles feedback loop
  ↓ Skill: workflow-suggestion autonomously proposes
  ↓ Agent: consolidation-trigger monitors & orchestrates
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ConsolidationTriggerType(str, Enum):
    """Trigger types for consolidation."""
    TASK_COMPLETION = "task_completion"  # Single task completed
    PATTERN_DETECTED = "pattern_detected"  # 2+ similar tasks completed
    BATCH_COMPLETION = "batch_completion"  # Multiple tasks completed in session
    WORKFLOW_PATTERN = "workflow_pattern"  # Reusable workflow identified


class TaskConsolidationSync:
    """Sync completed tasks into consolidation pipeline.

    Monitors task completion and:
    1. Records tasks as episodic events
    2. Detects patterns from recent task history
    3. Suggests workflows from repeated patterns
    4. Triggers consolidation when patterns found
    5. Updates procedural memory with success rates

    Attributes:
        pattern_detection_window: Number of recent tasks to analyze (default: 10)
        pattern_threshold: Minimum similarity to flag as pattern (0.0-1.0)
    """

    def __init__(
        self,
        pattern_detection_window: int = 10,
        pattern_threshold: float = 0.6
    ):
        """Initialize task-consolidation sync.

        Args:
            pattern_detection_window: How many recent tasks to consider
            pattern_threshold: Similarity threshold for pattern detection (0-1)
        """
        self.pattern_detection_window = pattern_detection_window
        self.pattern_threshold = pattern_threshold
        self.logger = logging.getLogger(__name__)
        self._task_history: List[Dict[str, Any]] = []

    def on_task_completed(
        self,
        task_id: str,
        task_content: str,
        outcome: str,  # "success", "failure", "partial"
        duration_seconds: float = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle task completion event.

        Args:
            task_id: Task identifier
            task_content: Task description
            outcome: Completion outcome
            duration_seconds: How long task took
            metadata: Additional context (project_id, tags, etc.)

        Returns:
            Dictionary with consolidation triggers and suggestions
        """
        # Record task in history
        task_record = {
            'task_id': task_id,
            'content': task_content,
            'outcome': outcome,
            'duration_seconds': duration_seconds,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self._task_history.append(task_record)

        # Keep only recent history
        if len(self._task_history) > self.pattern_detection_window:
            self._task_history = self._task_history[-self.pattern_detection_window:]

        self.logger.info(f"Recorded task completion: {task_id} ({outcome})")

        # Analyze for patterns
        patterns = self._detect_patterns()
        consolidation_triggers = []

        # Single task completion trigger
        consolidation_triggers.append({
            'type': ConsolidationTriggerType.TASK_COMPLETION.value,
            'task_id': task_id,
            'outcome': outcome,
            'confidence': 0.7
        })

        # Pattern-based triggers
        if patterns:
            for pattern in patterns:
                consolidation_triggers.append({
                    'type': ConsolidationTriggerType.PATTERN_DETECTED.value,
                    'pattern': pattern['pattern_text'],
                    'matched_tasks': pattern['matched_task_ids'],
                    'similarity_score': pattern['similarity'],
                    'confidence': min(1.0, pattern['similarity'] * 1.2),
                    'suggested_workflow': pattern['suggested_workflow']
                })

        # Batch completion trigger (if multiple successes recently)
        successful_count = sum(1 for t in self._task_history[-3:] if t['outcome'] == 'success')
        if successful_count >= 2:
            consolidation_triggers.append({
                'type': ConsolidationTriggerType.BATCH_COMPLETION.value,
                'successful_tasks': successful_count,
                'window': 'last_3_tasks',
                'confidence': 0.8
            })

        return {
            'task_id': task_id,
            'consolidation_needed': len(consolidation_triggers) > 1,
            'triggers': consolidation_triggers,
            'patterns_detected': len(patterns),
            'recommendations': self._generate_recommendations(patterns, outcome)
        }

    def _detect_patterns(self) -> List[Dict[str, Any]]:
        """Detect patterns in recent task history.

        Looks for:
        - Similar task types
        - Similar outcomes
        - Sequential patterns
        - Domain patterns

        Returns:
            List of detected patterns with metadata
        """
        if len(self._task_history) < 2:
            return []

        patterns = []
        recent_tasks = self._task_history[-self.pattern_detection_window:]

        # Pattern 1: Similar task content
        for i in range(len(recent_tasks)):
            for j in range(i + 1, len(recent_tasks)):
                similarity = self._calculate_similarity(
                    recent_tasks[i]['content'],
                    recent_tasks[j]['content']
                )

                if similarity >= self.pattern_threshold:
                    pattern = {
                        'pattern_text': f"Similar to '{recent_tasks[i]['content'][:50]}'",
                        'matched_task_ids': [recent_tasks[i]['task_id'], recent_tasks[j]['task_id']],
                        'similarity': similarity,
                        'pattern_type': 'content_similarity',
                        'suggested_workflow': self._suggest_workflow(
                            recent_tasks[i], recent_tasks[j]
                        )
                    }
                    patterns.append(pattern)

        # Pattern 2: Repeated successful outcomes
        successful_tasks = [t for t in recent_tasks if t['outcome'] == 'success']
        if len(successful_tasks) >= 2:
            avg_duration = sum(t.get('duration_seconds', 0) for t in successful_tasks) / len(successful_tasks)
            patterns.append({
                'pattern_text': f"Success pattern ({len(successful_tasks)} consecutive successes)",
                'matched_task_ids': [t['task_id'] for t in successful_tasks],
                'similarity': 0.9,
                'pattern_type': 'success_streak',
                'average_duration': avg_duration,
                'suggested_workflow': 'consolidate_successes'
            })

        return patterns

    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """Calculate similarity between two task descriptions.

        Simple implementation using word overlap.

        Args:
            text1: First task description
            text2: Second task description

        Returns:
            Similarity score 0.0-1.0
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def _suggest_workflow(task1: Dict[str, Any], task2: Dict[str, Any]) -> str:
        """Suggest workflow name based on similar tasks.

        Args:
            task1: First task
            task2: Second task

        Returns:
            Suggested workflow name
        """
        # Extract common domain from task descriptions
        content = f"{task1['content']} {task2['content']}"

        # Domain detection heuristics
        if any(word in content.lower() for word in ['test', 'verify', 'check', 'validate']):
            return 'validation_workflow'
        elif any(word in content.lower() for word in ['implement', 'create', 'build', 'develop']):
            return 'implementation_workflow'
        elif any(word in content.lower() for word in ['refactor', 'clean', 'improve', 'optimize']):
            return 'refactoring_workflow'
        elif any(word in content.lower() for word in ['debug', 'fix', 'error', 'issue']):
            return 'debugging_workflow'
        else:
            return 'generic_workflow'

    def _generate_recommendations(
        self,
        patterns: List[Dict[str, Any]],
        outcome: str
    ) -> List[str]:
        """Generate consolidation recommendations.

        Args:
            patterns: Detected patterns
            outcome: Result of current task

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        if not patterns:
            recommendations.append("No patterns detected. Continue collecting task data.")
            return recommendations

        if outcome == 'success':
            recommendations.append("Task successful - good candidate for consolidation")

        if len(patterns) >= 2:
            recommendations.append("Multiple patterns detected - trigger full consolidation")
            recommendations.append("Consider creating new procedural workflow from patterns")

        for pattern in patterns:
            if pattern.get('pattern_type') == 'success_streak':
                recommendations.append(
                    f"Success pattern found ({len(pattern['matched_task_ids'])} tasks) - "
                    "consolidate to procedural memory"
                )

        return recommendations

    def get_task_statistics(self) -> Dict[str, Any]:
        """Get statistics from task history.

        Returns:
            Dictionary with task metrics
        """
        if not self._task_history:
            return {'total_tasks': 0, 'message': 'No task history'}

        total = len(self._task_history)
        successful = sum(1 for t in self._task_history if t['outcome'] == 'success')
        failed = sum(1 for t in self._task_history if t['outcome'] == 'failure')
        avg_duration = (
            sum(t.get('duration_seconds', 0) for t in self._task_history) / total
            if total > 0 else 0
        )

        return {
            'total_tasks': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0.0,
            'average_duration_seconds': avg_duration,
            'window_size': self.pattern_detection_window
        }

    def clear_history(self) -> None:
        """Clear task history (typically at session end)."""
        self._task_history.clear()
        self.logger.info("Cleared task history")
