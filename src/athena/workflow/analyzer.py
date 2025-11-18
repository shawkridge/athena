"""Task Sequence Analysis - Phase 3b.

Mines completed task sequences to discover workflow patterns.
Analyzes task types and calculates pattern strength.
"""

import logging
import json
from typing import Optional, Dict, Any, List
from collections import defaultdict, Counter

from ..core.database import Database
from .patterns import WorkflowPatternStore

logger = logging.getLogger(__name__)


class TaskTypeClassifier:
    """Classifies tasks into types based on content and tags."""

    KEYWORDS = {
        "feature": ["implement", "develop", "build", "add", "create", "feature"],
        "test": ["test", "testing", "unit test", "integration", "qa"],
        "review": ["review", "code review", "approve", "feedback"],
        "bugfix": ["bug", "fix", "bug fix", "patch", "hotfix"],
        "design": ["design", "architect", "plan", "spec", "requirement"],
        "deploy": ["deploy", "release", "push", "production", "go live"],
        "documentation": ["doc", "document", "write docs", "readme"],
        "refactor": ["refactor", "cleanup", "clean up", "tech debt", "optimize"],
    }

    @classmethod
    def classify(cls, content: str, tags: Optional[List[str]] = None) -> str:
        """Classify task type from content and tags.

        Args:
            content: Task content/title
            tags: Optional list of tags

        Returns:
            Task type (e.g., 'feature', 'test', 'review')
        """
        content_lower = content.lower()

        # Check tags first (highest priority)
        if tags:
            for tag_type, keywords in cls.KEYWORDS.items():
                if any(tag.lower() in [k.lower() for k in keywords] for tag in tags):
                    return tag_type

        # Check content keywords
        for task_type, keywords in cls.KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return task_type

        # Default to generic task type
        return "task"


class TaskSequenceAnalyzer:
    """Analyzes completed task sequences to discover patterns."""

    def __init__(self, db: Database):
        """Initialize analyzer.

        Args:
            db: Database instance
        """
        self.db = db
        self.pattern_store = WorkflowPatternStore(db)

    def analyze_completed_sequences(self, project_id: int) -> Dict[str, Any]:
        """Analyze completed task sequences for a project.

        Mines all completed tasks in chronological order to discover patterns.

        Args:
            project_id: Project ID

        Returns:
            Analysis results dict with patterns found
        """
        try:
            cursor = self.db.get_cursor()

            # Get all completed tasks in order
            cursor.execute(
                """
                SELECT id, content, tags, completed_at
                FROM prospective_tasks
                WHERE project_id = %s AND status = 'completed'
                ORDER BY completed_at ASC
                """,
                (project_id,),
            )

            completed_tasks = cursor.fetchall()
            if len(completed_tasks) < 2:
                return {"message": "Not enough completed tasks to analyze"}

            # Extract task types
            task_sequence = []
            for task in completed_tasks:
                task_id, content, tags_json, completed_at = task
                tags = json.loads(tags_json) if tags_json else []
                task_type = TaskTypeClassifier.classify(content, tags)

                task_sequence.append(
                    {
                        "id": task_id,
                        "type": task_type,
                        "completed_at": completed_at,
                    }
                )

            # Mine transitions
            patterns_found = 0
            durations = defaultdict(list)

            for i in range(len(task_sequence) - 1):
                current = task_sequence[i]
                next_task = task_sequence[i + 1]

                from_type = current["type"]
                to_type = next_task["type"]

                # Calculate duration in hours
                duration_hours = (
                    next_task["completed_at"] - current["completed_at"]
                ).total_seconds() / 3600

                # Store pattern
                self.pattern_store.store_pattern(
                    project_id,
                    from_type,
                    to_type,
                    duration_hours,
                )

                durations[(from_type, to_type)].append(duration_hours)
                patterns_found += 1

            # Calculate confidence scores
            self.pattern_store.calculate_confidence(project_id)

            # Build typical sequences for each task type
            self._build_typical_sequences(project_id, task_sequence)

            return {
                "success": True,
                "patterns_found": patterns_found,
                "completed_tasks": len(completed_tasks),
                "task_types": len(set(t["type"] for t in task_sequence)),
                "message": f"Analyzed {len(completed_tasks)} completed tasks, found {patterns_found} patterns",
            }

        except Exception as e:
            logger.error(f"Failed to analyze sequences: {e}")
            return {"error": str(e)}

    def _build_typical_sequences(
        self, project_id: int, task_sequence: List[Dict[str, Any]]
    ) -> None:
        """Build typical workflow sequences for each task type.

        Args:
            project_id: Project ID
            task_sequence: Sequence of completed tasks with types
        """
        try:
            # Group sequences by task type
            sequences_by_type = defaultdict(list)

            for i, task in enumerate(task_sequence):
                task_type = task["type"]
                # Look ahead to see what comes next
                if i < len(task_sequence) - 1:
                    next_type = task_sequence[i + 1]["type"]
                    sequences_by_type[task_type].append(next_type)

            # For each task type, find the most common successor
            for task_type, successors in sequences_by_type.items():
                if not successors:
                    continue

                # Get top 3 successors by frequency
                counter = Counter(successors)
                top_successors = [s[0] for s in counter.most_common(3)]

                # Calculate average confidence
                cursor = self.db.get_cursor()
                cursor.execute(
                    """
                    SELECT AVG(confidence) FROM workflow_patterns
                    WHERE project_id = %s AND from_task_type = %s
                    """,
                    (project_id, task_type),
                )

                row = cursor.fetchone()
                avg_confidence = row[0] if row and row[0] else 0.0

                # Store typical sequence
                self.pattern_store.store_workflow_sequence(
                    project_id,
                    task_type,
                    top_successors,
                    confidence_avg=avg_confidence,
                    task_count=len(successors),
                )

        except Exception as e:
            logger.error(f"Failed to build typical sequences: {e}")

    def get_task_type_distribution(self, project_id: int) -> Optional[Dict[str, int]]:
        """Get distribution of task types in completed tasks.

        Args:
            project_id: Project ID

        Returns:
            Dict mapping task types to counts
        """
        try:
            cursor = self.db.get_cursor()

            cursor.execute(
                """
                SELECT content, tags
                FROM prospective_tasks
                WHERE project_id = %s AND status = 'completed'
                """,
                (project_id,),
            )

            rows = cursor.fetchall()
            if not rows:
                return None

            type_counts = defaultdict(int)

            for content, tags_json in rows:
                tags = json.loads(tags_json) if tags_json else []
                task_type = TaskTypeClassifier.classify(content, tags)
                type_counts[task_type] += 1

            return dict(type_counts)

        except Exception as e:
            logger.error(f"Failed to get task type distribution: {e}")
            return None

    def get_pattern_statistics(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get statistics about discovered patterns.

        Args:
            project_id: Project ID

        Returns:
            Statistics dict
        """
        try:
            cursor = self.db.get_cursor()

            # Total patterns
            cursor.execute(
                """
                SELECT COUNT(*), AVG(confidence), AVG(frequency)
                FROM workflow_patterns
                WHERE project_id = %s
                """,
                (project_id,),
            )

            row = cursor.fetchone()
            if not row or row[0] == 0:
                return None

            total_patterns = row[0]
            avg_confidence = row[1] or 0.0
            avg_frequency = row[2] or 0.0

            # High confidence patterns (>70%)
            cursor.execute(
                """
                SELECT COUNT(*) FROM workflow_patterns
                WHERE project_id = %s AND confidence > 0.7
                """,
                (project_id,),
            )

            high_confidence = cursor.fetchone()[0] or 0

            # Low confidence patterns (<10%)
            cursor.execute(
                """
                SELECT COUNT(*) FROM workflow_patterns
                WHERE project_id = %s AND confidence < 0.1 AND frequency > 0
                """,
                (project_id,),
            )

            anomalies = cursor.fetchone()[0] or 0

            return {
                "total_patterns": total_patterns,
                "avg_confidence": round(avg_confidence, 3),
                "avg_frequency": round(avg_frequency, 1),
                "high_confidence": high_confidence,
                "anomalies": anomalies,
                "process_maturity": (
                    "high" if avg_confidence > 0.75 else "medium" if avg_confidence > 0.5 else "low"
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return None
