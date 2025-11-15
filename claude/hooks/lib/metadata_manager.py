"""Task metadata management for Phase 3a.

Enriches tasks with: effort estimates, actual effort, complexity scores, and tags.
Enables completion analytics: compare estimated vs actual effort.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from connection_pool import PooledConnection


class MetadataManager:
    """Manage task metadata including effort, complexity, and tags."""

    def __init__(self):
        """Initialize metadata manager."""
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure all metadata columns exist on prospective_tasks."""
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Add metadata columns if they don't exist
                # (Using ALTER TABLE IF NOT EXISTS pattern for safety)
                metadata_columns = [
                    ("effort_estimate", "INTEGER DEFAULT 0"),  # minutes
                    ("effort_actual", "INTEGER DEFAULT 0"),  # minutes
                    ("complexity_score", "INTEGER DEFAULT 5"),  # 1-10
                    ("priority_score", "INTEGER DEFAULT 5"),  # 1-10
                    ("tags", "TEXT DEFAULT '[]'"),  # JSON array
                    ("started_at", "TIMESTAMP"),
                    ("completed_at", "TIMESTAMP"),
                ]

                for col_name, col_def in metadata_columns:
                    try:
                        cursor.execute(
                            f"ALTER TABLE prospective_tasks ADD COLUMN {col_name} {col_def}"
                        )
                    except Exception:
                        # Column already exists, skip
                        pass

                conn.commit()

        except Exception as e:
            print(f"⚠ Error ensuring metadata schema: {e}", file=sys.stderr)

    def set_metadata(
        self,
        project_id: int,
        task_id: int,
        effort_estimate: Optional[int] = None,
        complexity_score: Optional[int] = None,
        priority_score: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Set task metadata.

        Args:
            project_id: Project ID
            task_id: Task ID
            effort_estimate: Estimated time in minutes
            complexity_score: 1-10 complexity rating
            priority_score: 1-10 priority rating
            tags: List of tags (e.g., ['feature', 'urgent', 'refactor'])

        Returns:
            Result dict with updated metadata
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Build dynamic UPDATE
                set_clauses = []
                values = []

                if effort_estimate is not None:
                    set_clauses.append("effort_estimate = %s")
                    values.append(effort_estimate)

                if complexity_score is not None:
                    if not (1 <= complexity_score <= 10):
                        return {"error": "Complexity score must be 1-10"}
                    set_clauses.append("complexity_score = %s")
                    values.append(complexity_score)

                if priority_score is not None:
                    if not (1 <= priority_score <= 10):
                        return {"error": "Priority score must be 1-10"}
                    set_clauses.append("priority_score = %s")
                    values.append(priority_score)

                if tags is not None:
                    tags_json = json.dumps(tags)
                    set_clauses.append("tags = %s")
                    values.append(tags_json)

                if not set_clauses:
                    return {"error": "No metadata fields to update"}

                # Execute update
                query = f"""
                UPDATE prospective_tasks
                SET {', '.join(set_clauses)}
                WHERE id = %s AND project_id = %s
                RETURNING id, effort_estimate, complexity_score, priority_score, tags
                """

                values.extend([task_id, project_id])
                cursor.execute(query, values)
                result = cursor.fetchone()
                conn.commit()

                if result:
                    tags_list = json.loads(result[4]) if result[4] else []
                    return {
                        "success": True,
                        "task_id": result[0],
                        "effort_estimate": result[1],
                        "complexity_score": result[2],
                        "priority_score": result[3],
                        "tags": tags_list,
                    }
                else:
                    return {"error": f"Task {task_id} not found"}

        except Exception as e:
            return {"error": f"Set metadata failed: {str(e)}"}

    def record_actual_effort(
        self, project_id: int, task_id: int, actual_minutes: int
    ) -> Dict[str, Any]:
        """Record actual effort spent on a task.

        Also sets started_at if not already set.

        Args:
            project_id: Project ID
            task_id: Task ID
            actual_minutes: Actual time spent in minutes

        Returns:
            Result dict with effort info
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # First check if started_at is set
                cursor.execute(
                    """
                    SELECT started_at, effort_actual FROM prospective_tasks
                    WHERE id = %s AND project_id = %s
                    """,
                    (task_id, project_id),
                )

                row = cursor.fetchone()
                if not row:
                    return {"error": f"Task {task_id} not found"}

                started_at = row[0]
                current_actual = row[1] or 0

                # Set started_at if not already set
                if started_at is None:
                    started_at = datetime.now()

                # Update actual effort
                cursor.execute(
                    """
                    UPDATE prospective_tasks
                    SET effort_actual = %s, started_at = %s
                    WHERE id = %s AND project_id = %s
                    RETURNING effort_estimate, effort_actual, effort_estimate > 0
                    """,
                    (actual_minutes, started_at, task_id, project_id),
                )

                result = cursor.fetchone()
                conn.commit()

                if result:
                    estimate = result[0]
                    actual = result[1]
                    has_estimate = result[2]

                    response = {
                        "success": True,
                        "task_id": task_id,
                        "effort_estimate": estimate,
                        "effort_actual": actual,
                    }

                    if has_estimate and estimate > 0:
                        accuracy = (
                            100 * min(estimate, actual) / max(estimate, actual)
                        )
                        variance = actual - estimate
                        response["accuracy_percent"] = round(accuracy, 1)
                        response["variance_minutes"] = variance

                    return response
                else:
                    return {"error": "Failed to record effort"}

        except Exception as e:
            return {"error": f"Record effort failed: {str(e)}"}

    def calculate_accuracy(
        self, project_id: int, task_id: int
    ) -> Optional[Dict[str, Any]]:
        """Calculate estimate accuracy for a task.

        Accuracy = min(estimate, actual) / max(estimate, actual) * 100
        Variance = actual - estimate (positive = took longer)

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            Accuracy dict with percent and variance, or None if no estimate/actual
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT effort_estimate, effort_actual
                    FROM prospective_tasks
                    WHERE id = %s AND project_id = %s
                    """,
                    (task_id, project_id),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                estimate = row[0] or 0
                actual = row[1] or 0

                if estimate == 0 or actual == 0:
                    return None  # Can't calculate without both

                accuracy = 100 * min(estimate, actual) / max(estimate, actual)
                variance = actual - estimate

                return {
                    "accuracy_percent": round(accuracy, 1),
                    "variance_minutes": variance,
                    "estimate": estimate,
                    "actual": actual,
                    "overestimated": variance < 0,
                    "underestimated": variance > 0,
                }

        except Exception as e:
            print(f"⚠ Error calculating accuracy: {e}", file=sys.stderr)
            return None

    def get_task_metadata(self, project_id: int, task_id: int) -> Optional[Dict[str, Any]]:
        """Get all metadata for a task.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            Metadata dict with all fields
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        id, title, status,
                        effort_estimate, effort_actual,
                        complexity_score, priority_score,
                        tags, started_at, completed_at
                    FROM prospective_tasks
                    WHERE id = %s AND project_id = %s
                    """,
                    (task_id, project_id),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                tags = json.loads(row[7]) if row[7] else []

                metadata = {
                    "id": row[0],
                    "content": row[1],
                    "status": row[2],
                    "effort_estimate": row[3],
                    "effort_actual": row[4],
                    "complexity_score": row[5],
                    "priority_score": row[6],
                    "tags": tags,
                    "started_at": row[8],
                    "completed_at": row[9],
                }

                # Include accuracy if both estimate and actual are set
                accuracy = self.calculate_accuracy(project_id, task_id)
                if accuracy:
                    metadata["accuracy"] = accuracy

                return metadata

        except Exception as e:
            print(f"⚠ Error getting metadata: {e}", file=sys.stderr)
            return None

    def get_project_analytics(self, project_id: int) -> Dict[str, Any]:
        """Get aggregate analytics for all tasks in project.

        Returns statistics on estimates vs actual, complexity distribution, etc.

        Args:
            project_id: Project ID

        Returns:
            Analytics dict with summary statistics
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get all tasks with effort data
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_tasks,
                        SUM(CASE WHEN effort_estimate > 0 THEN 1 ELSE 0 END) as estimated_tasks,
                        SUM(CASE WHEN effort_actual > 0 THEN 1 ELSE 0 END) as tracked_tasks,
                        AVG(effort_estimate) as avg_estimate,
                        AVG(effort_actual) as avg_actual,
                        AVG(complexity_score) as avg_complexity,
                        MAX(complexity_score) as max_complexity,
                        MIN(complexity_score) as min_complexity
                    FROM prospective_tasks
                    WHERE project_id = %s AND status IN ('completed', 'in_progress')
                    """,
                    (project_id,),
                )

                row = cursor.fetchone()
                if not row or row[0] == 0:
                    return {"error": "No tasks found"}

                total = row[0]
                estimated = row[1] or 0
                tracked = row[2] or 0

                analytics = {
                    "total_tasks": total,
                    "estimated_tasks": estimated,
                    "tracked_tasks": tracked,
                    "avg_estimate_minutes": round(row[3], 1) if row[3] else 0,
                    "avg_actual_minutes": round(row[4], 1) if row[4] else 0,
                    "avg_complexity": round(row[5], 1) if row[5] else 0,
                    "complexity_range": (int(row[7]) if row[7] else 1, int(row[6]) if row[6] else 10),
                }

                # Calculate overall accuracy
                if estimated > 0 and tracked > 0:
                    cursor.execute(
                        """
                        SELECT
                            AVG(
                                100 * LEAST(effort_estimate, effort_actual) /
                                GREATEST(effort_estimate, effort_actual)
                            ) as accuracy
                        FROM prospective_tasks
                        WHERE project_id = %s AND effort_estimate > 0 AND effort_actual > 0
                        """,
                        (project_id,),
                    )

                    accuracy_row = cursor.fetchone()
                    if accuracy_row and accuracy_row[0]:
                        analytics["overall_accuracy_percent"] = round(accuracy_row[0], 1)

                return analytics

        except Exception as e:
            print(f"⚠ Error getting project analytics: {e}", file=sys.stderr)
            return {"error": f"Analytics failed: {str(e)}"}

    def add_tags(self, project_id: int, task_id: int, tags: List[str]) -> Dict[str, Any]:
        """Add tags to a task (non-destructive).

        Args:
            project_id: Project ID
            task_id: Task ID
            tags: Tags to add

        Returns:
            Result dict with updated tags
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get current tags
                cursor.execute(
                    """
                    SELECT tags FROM prospective_tasks
                    WHERE id = %s AND project_id = %s
                    """,
                    (task_id, project_id),
                )

                row = cursor.fetchone()
                if not row:
                    return {"error": f"Task {task_id} not found"}

                current_tags = json.loads(row[0]) if row[0] else []

                # Add new tags (avoid duplicates)
                updated_tags = list(set(current_tags + tags))

                # Update
                cursor.execute(
                    """
                    UPDATE prospective_tasks
                    SET tags = %s
                    WHERE id = %s AND project_id = %s
                    RETURNING tags
                    """,
                    (json.dumps(updated_tags), task_id, project_id),
                )

                result = cursor.fetchone()
                conn.commit()

                if result:
                    return {
                        "success": True,
                        "task_id": task_id,
                        "tags": json.loads(result[0]),
                    }
                else:
                    return {"error": "Failed to add tags"}

        except Exception as e:
            return {"error": f"Add tags failed: {str(e)}"}

    def set_completed_timestamp(
        self, project_id: int, task_id: int
    ) -> Dict[str, Any]:
        """Set completed_at timestamp.

        Called when task status is changed to 'completed'.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            Result dict
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                now = datetime.now()

                cursor.execute(
                    """
                    UPDATE prospective_tasks
                    SET completed_at = %s
                    WHERE id = %s AND project_id = %s
                    RETURNING id, started_at, completed_at
                    """,
                    (now, task_id, project_id),
                )

                result = cursor.fetchone()
                conn.commit()

                if result:
                    return {
                        "success": True,
                        "task_id": result[0],
                        "started_at": result[1],
                        "completed_at": result[2],
                    }
                else:
                    return {"error": f"Task {task_id} not found"}

        except Exception as e:
            return {"error": f"Set completion timestamp failed: {str(e)}"}


def test_metadata_manager():
    """Test metadata manager functionality."""
    print("\n=== Metadata Manager Test ===\n")

    mgr = MetadataManager()

    # Test 1: Set metadata
    print("1. Setting metadata for a task...")
    result = mgr.set_metadata(
        project_id=1,
        task_id=1,
        effort_estimate=120,
        complexity_score=7,
        priority_score=8,
        tags=["feature", "urgent"],
    )
    if result.get("success"):
        print(f"  ✓ Metadata set")
        print(f"    Estimate: {result['effort_estimate']} minutes")
        print(f"    Complexity: {result['complexity_score']}/10")
        print(f"    Tags: {result['tags']}")
    else:
        print(f"  ✗ {result.get('error')}")

    # Test 2: Record actual effort
    print("\n2. Recording actual effort (150 minutes)...")
    result = mgr.record_actual_effort(project_id=1, task_id=1, actual_minutes=150)
    if result.get("success"):
        print(f"  ✓ Effort recorded")
        print(f"    Estimate: {result['effort_estimate']} min")
        print(f"    Actual: {result['effort_actual']} min")
        if "accuracy_percent" in result:
            print(f"    Accuracy: {result['accuracy_percent']}%")
    else:
        print(f"  ✗ {result.get('error')}")

    # Test 3: Calculate accuracy
    print("\n3. Calculating accuracy...")
    accuracy = mgr.calculate_accuracy(project_id=1, task_id=1)
    if accuracy:
        print(f"  ✓ Accuracy: {accuracy['accuracy_percent']}%")
        print(f"    Variance: {accuracy['variance_minutes']} minutes")
        print(f"    {'Overestimated' if accuracy['overestimated'] else 'Underestimated'}")
    else:
        print("  ℹ No accuracy data yet")

    # Test 4: Get task metadata
    print("\n4. Getting full metadata...")
    metadata = mgr.get_task_metadata(project_id=1, task_id=1)
    if metadata:
        print(f"  ✓ Task: {metadata['content']}")
        print(f"    Effort: {metadata['effort_estimate']}m estimate, {metadata['effort_actual']}m actual")
        print(f"    Complexity: {metadata['complexity_score']}/10")
        print(f"    Tags: {metadata['tags']}")
    else:
        print("  ℹ Task not found")

    # Test 5: Add tags
    print("\n5. Adding tags...")
    result = mgr.add_tags(project_id=1, task_id=1, tags=["refactor"])
    if result.get("success"):
        print(f"  ✓ Tags: {result['tags']}")
    else:
        print(f"  ✗ {result.get('error')}")

    # Test 6: Project analytics
    print("\n6. Getting project analytics...")
    analytics = mgr.get_project_analytics(project_id=1)
    if "error" not in analytics:
        print(f"  ✓ Total tasks: {analytics['total_tasks']}")
        print(f"    Estimated: {analytics['estimated_tasks']}")
        print(f"    Avg complexity: {analytics['avg_complexity']}/10")
        if "overall_accuracy_percent" in analytics:
            print(f"    Overall accuracy: {analytics['overall_accuracy_percent']}%")
    else:
        print(f"  ℹ {analytics.get('error')}")

    print("\n✓ Metadata Manager tests complete\n")


if __name__ == "__main__":
    test_metadata_manager()
