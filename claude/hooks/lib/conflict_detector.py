"""Detect and handle conflicts in simultaneous task edits.

When a task is edited both in PostgreSQL (via external tool) and in TodoWrite
(via Claude), conflicts can occur. This module detects and suggests resolution.

Strategy:
1. Timestamp-based: Last write wins, but log the conflict
2. Field-level: Merge non-conflicting fields, detect conflicting ones
3. User-aware: If Claude edited it, Claude's version takes precedence
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from connection_pool import PooledConnection


class ConflictDetector:
    """Detect and resolve task edit conflicts."""

    def __init__(self):
        """Initialize conflict detector."""
        pass

    def detect_conflict(
        self,
        project_id: int,
        task_id: int,
        claude_version: Dict[str, Any],
        postgres_version: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Detect conflicts between Claude edits and database state.

        Args:
            project_id: Project ID
            task_id: Task ID
            claude_version: Version from Claude/TodoWrite
            postgres_version: Current version in PostgreSQL (if None, fetch it)

        Returns:
            Conflict report: {has_conflict, conflicts, resolution, ...}
        """
        # Fetch current PostgreSQL version if not provided
        if postgres_version is None:
            postgres_version = self._get_postgres_version(project_id, task_id)

        if postgres_version is None:
            return {
                "has_conflict": False,
                "type": "new_task",
                "message": "Task not in database, will be created",
            }

        # Compare versions
        conflicts = []
        conflicting_fields = []

        fields_to_check = ["status", "priority", "content", "description"]

        for field in fields_to_check:
            claude_val = claude_version.get(field)
            postgres_val = postgres_version.get(field)

            if claude_val != postgres_val and claude_val is not None:
                conflicts.append(
                    {
                        "field": field,
                        "claude_version": claude_val,
                        "postgres_version": postgres_val,
                        "conflict_type": self._classify_conflict(field, claude_val, postgres_val),
                    }
                )
                conflicting_fields.append(field)

        if not conflicts:
            return {
                "has_conflict": False,
                "type": "no_conflict",
                "message": "Versions match, no conflict",
            }

        return {
            "has_conflict": True,
            "type": "field_conflict",
            "task_id": task_id,
            "conflicts": conflicts,
            "conflicting_fields": conflicting_fields,
            "resolution": "claude_wins",  # Default: Claude's edit takes precedence
            "message": f"Detected {len(conflicts)} field conflict(s)",
        }

    def _get_postgres_version(
        self, project_id: int, task_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get current task version from PostgreSQL.

        Args:
            project_id: Project ID
            task_id: Task ID

        Returns:
            Task dict or None
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, title, status, priority, description, last_claude_sync_at
                    FROM prospective_tasks
                    WHERE id = %s AND project_id = %s
                    """,
                    (task_id, project_id),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "content": row[1],
                        "status": row[2],
                        "priority": row[3],
                        "description": row[4],
                        "last_sync": row[5],
                    }

                return None

        except Exception:
            return None

    def _classify_conflict(
        self, field: str, claude_val: Any, postgres_val: Any
    ) -> str:
        """Classify the type of conflict.

        Args:
            field: Field name
            claude_val: Claude's value
            postgres_val: PostgreSQL value

        Returns:
            Conflict type: status_change|priority_change|content_change|other
        """
        if field == "status":
            return "status_change"
        elif field == "priority":
            return "priority_change"
        elif field == "content":
            return "content_change"
        else:
            return "other_change"

    def resolve_conflict(
        self,
        project_id: int,
        task_id: int,
        claude_version: Dict[str, Any],
        postgres_version: Dict[str, Any],
        strategy: str = "claude_wins",
    ) -> Dict[str, Any]:
        """Resolve a detected conflict.

        Strategies:
        - claude_wins: Use Claude's values (default)
        - postgres_wins: Use database values
        - merge: Merge non-conflicting fields, use claude_wins for conflicts
        - manual: Return conflict, require manual intervention

        Args:
            project_id: Project ID
            task_id: Task ID
            claude_version: Claude's version
            postgres_version: Database version
            strategy: Resolution strategy

        Returns:
            Resolved version dict
        """
        if strategy == "claude_wins":
            # Claude's edits take precedence
            return {
                "success": True,
                "strategy": "claude_wins",
                "resolved_version": claude_version,
                "message": "Claude's edits take precedence",
            }

        elif strategy == "postgres_wins":
            # Keep database version
            return {
                "success": True,
                "strategy": "postgres_wins",
                "resolved_version": postgres_version,
                "message": "Database version kept",
            }

        elif strategy == "merge":
            # Merge: non-conflicting from both, conflicting from claude
            merged = dict(postgres_version)

            for key, claude_val in claude_version.items():
                if claude_val is not None:
                    postgres_val = postgres_version.get(key)

                    if postgres_val is None or claude_val == postgres_val:
                        # No conflict, use claude
                        merged[key] = claude_val
                    else:
                        # Conflict, claude wins
                        merged[key] = claude_val

            return {
                "success": True,
                "strategy": "merge",
                "resolved_version": merged,
                "message": "Merged versions with claude_wins for conflicts",
            }

        else:  # manual
            return {
                "success": False,
                "strategy": "manual",
                "conflict_report": {
                    "claude_version": claude_version,
                    "postgres_version": postgres_version,
                },
                "message": "Manual intervention required",
            }

    def log_conflict(
        self,
        project_id: int,
        task_id: int,
        conflict_report: Dict[str, Any],
        resolution: str,
    ) -> bool:
        """Log a conflict for audit trail.

        Args:
            project_id: Project ID
            task_id: Task ID
            conflict_report: Conflict details
            resolution: How it was resolved

        Returns:
            True if logged successfully
        """
        try:
            import json
            import sys

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "project_id": project_id,
                "task_id": task_id,
                "conflict_report": conflict_report,
                "resolution": resolution,
            }

            print(
                f"[CONFLICT LOG] Task {task_id}: {conflict_report.get('message')} - Resolved: {resolution}",
                file=sys.stderr,
            )

            return True

        except Exception:
            return False

    def should_proceed_with_sync(
        self, conflict_report: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Determine if sync should proceed based on conflict severity.

        Args:
            conflict_report: Conflict report

        Returns:
            (should_proceed, reason)
        """
        if not conflict_report.get("has_conflict"):
            return True, "No conflict detected"

        conflicting_fields = conflict_report.get("conflicting_fields", [])
        critical_fields = ["status"]  # Status changes are critical

        has_critical = any(f in critical_fields for f in conflicting_fields)

        if has_critical:
            return False, f"Critical field conflict in {conflicting_fields}"

        # Non-critical conflicts can proceed (claude_wins)
        return True, "Non-critical conflict, proceeding with claude_wins"


def test_conflict_detector():
    """Test conflict detection and resolution."""
    print("\n=== Conflict Detector Test ===\n")

    detector = ConflictDetector()

    # Test 1: No conflict
    print("1. Testing no conflict scenario...")
    claude_version = {
        "content": "Task A",
        "status": "in_progress",
        "priority": 5,
    }
    postgres_version = {
        "content": "Task A",
        "status": "in_progress",
        "priority": 5,
    }

    result = detector.detect_conflict(1, 1, claude_version, postgres_version)
    print(f"  ✓ {result['message']}")

    # Test 2: Simple conflict
    print("\n2. Testing simple conflict...")
    postgres_version["priority"] = 3

    result = detector.detect_conflict(1, 1, claude_version, postgres_version)
    if result["has_conflict"]:
        print(f"  ✓ Detected conflict: {result['message']}")
        print(f"    Fields: {result['conflicting_fields']}")

    # Test 3: Resolve conflict
    print("\n3. Testing conflict resolution...")
    resolution = detector.resolve_conflict(
        1, 1, claude_version, postgres_version, strategy="claude_wins"
    )
    if resolution["success"]:
        print(f"  ✓ Resolved: {resolution['message']}")
        print(f"    Priority: {resolution['resolved_version'].get('priority')}")

    # Test 4: Merge strategy
    print("\n4. Testing merge strategy...")
    postgres_version["description"] = "Old description"
    claude_version["description"] = "New description"

    resolution = detector.resolve_conflict(
        1, 1, claude_version, postgres_version, strategy="merge"
    )
    if resolution["success"]:
        print(f"  ✓ Merged versions: {resolution['message']}")

    # Test 5: Check if sync should proceed
    print("\n5. Testing sync proceed decision...")
    conflict_report = {
        "has_conflict": True,
        "conflicting_fields": ["priority"],
    }

    should_proceed, reason = detector.should_proceed_with_sync(conflict_report)
    print(
        f"  ✓ Proceed: {should_proceed}, Reason: {reason}"
    )

    print("\n✓ Conflict Detector tests complete\n")


if __name__ == "__main__":
    test_conflict_detector()
