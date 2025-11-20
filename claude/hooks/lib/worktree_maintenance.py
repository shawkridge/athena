"""Worktree Maintenance Utilities

Handles cleanup and management of orphaned worktrees, deleted branches,
and inconsistent states.
"""

import os
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

from connection_pool import PooledConnection
from git_worktree_helper import GitWorktreeHelper

logger = logging.getLogger(__name__)


class WorktreeMaintenance:
    """Manage worktree lifecycle and cleanup."""

    @staticmethod
    def find_orphaned_todos(
        project_id: int,
        check_filesystem: bool = True,
    ) -> Dict[str, Any]:
        """Find todos that belong to deleted or missing worktrees.

        Args:
            project_id: Project ID to check
            check_filesystem: If True, verify worktree paths exist

        Returns:
            Dict with orphaned todo information
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Get todos with worktree paths
                cursor.execute(
                    """
                    SELECT
                        id,
                        todo_id,
                        goal,
                        status,
                        worktree_path,
                        worktree_branch,
                        created_at,
                        updated_at
                    FROM todowrite_plans
                    WHERE project_id = %s
                      AND status IN ('pending', 'in_progress')
                      AND worktree_path IS NOT NULL
                    """,
                    (project_id,),
                )

                rows = cursor.fetchall()

                orphaned = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "project_id": project_id,
                    "total_todos_with_worktree": len(rows),
                    "orphaned_todos": [],
                    "orphaned_count": 0,
                }

                for row in rows:
                    row_id, todo_id, goal, status, worktree_path, worktree_branch, created_at, updated_at = row

                    is_orphaned = False

                    if check_filesystem:
                        # Check if worktree path still exists
                        if not os.path.exists(worktree_path):
                            is_orphaned = True
                            reason = "worktree_path_missing"
                        else:
                            # Check if it's still a valid git worktree
                            worktree_helper = GitWorktreeHelper()
                            info = worktree_helper.get_worktree_info(worktree_path)
                            if not info.get("worktree_path"):
                                is_orphaned = True
                                reason = "not_a_valid_worktree"
                            else:
                                reason = None
                    else:
                        # Just check if path is present (don't verify filesystem)
                        reason = None

                    if is_orphaned:
                        orphaned["orphaned_todos"].append({
                            "id": row_id,
                            "todo_id": todo_id,
                            "goal": goal,
                            "status": status,
                            "worktree_path": worktree_path,
                            "worktree_branch": worktree_branch,
                            "created_at": created_at,
                            "updated_at": updated_at,
                            "reason": reason,
                            "age_days": (
                                (datetime.now(timezone.utc).timestamp() - updated_at / 1000)
                                / (24 * 3600)
                                if updated_at
                                else None
                            ),
                        })
                        orphaned["orphaned_count"] += 1

                logger.info(
                    f"Found {orphaned['orphaned_count']} orphaned todos "
                    f"out of {orphaned['total_todos_with_worktree']} worktree-scoped todos"
                )

                return orphaned

        except Exception as e:
            logger.error(f"Error finding orphaned todos: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @staticmethod
    def cleanup_orphaned_todos(
        project_id: int,
        age_days: int = 7,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Mark orphaned todos as completed.

        Args:
            project_id: Project ID
            age_days: Only cleanup if todo hasn't been updated in N days
            dry_run: If True, don't actually modify anything (show what would happen)

        Returns:
            Dict with cleanup results
        """
        try:
            # First find orphaned todos
            orphaned_info = WorktreeMaintenance.find_orphaned_todos(project_id, check_filesystem=True)

            if "error" in orphaned_info:
                return orphaned_info

            # Filter by age
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=age_days)
            cutoff_timestamp = int(cutoff_time.timestamp() * 1000)

            todos_to_cleanup = [
                todo
                for todo in orphaned_info["orphaned_todos"]
                if todo.get("updated_at", 0) < cutoff_timestamp
            ]

            cleanup_result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
                "dry_run": dry_run,
                "age_threshold_days": age_days,
                "eligible_for_cleanup": len(todos_to_cleanup),
                "cleaned_up": 0,
                "details": [],
            }

            if not dry_run and todos_to_cleanup:
                with PooledConnection() as conn:
                    cursor = conn.cursor()

                    for todo in todos_to_cleanup:
                        cursor.execute(
                            """
                            UPDATE todowrite_plans
                            SET status = 'completed',
                                sync_status = 'orphaned_cleanup',
                                updated_at = %s
                            WHERE id = %s
                            RETURNING id
                            """,
                            (int(time.time()), todo["id"]),
                        )

                        if cursor.fetchone():
                            cleanup_result["cleaned_up"] += 1
                            cleanup_result["details"].append({
                                "id": todo["id"],
                                "todo_id": todo["todo_id"],
                                "goal": todo["goal"],
                                "status": "marked_completed",
                            })

                    conn.commit()

            logger.info(
                f"Cleanup: {cleanup_result['cleaned_up']} todos marked as completed "
                f"({cleanup_result['eligible_for_cleanup']} eligible)"
            )

            return cleanup_result

        except Exception as e:
            logger.error(f"Error cleaning up orphaned todos: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @staticmethod
    def migrate_worktree_path(
        old_path: str,
        new_path: str,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Update todos when a worktree is moved to a new path.

        Args:
            old_path: Old worktree path
            new_path: New worktree path
            dry_run: If True, show what would be updated without making changes

        Returns:
            Dict with migration results
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                # Find todos with old path
                cursor.execute(
                    """
                    SELECT COUNT(*), COUNT(DISTINCT project_id)
                    FROM todowrite_plans
                    WHERE worktree_path = %s
                    """,
                    (old_path,),
                )

                row = cursor.fetchone()
                todo_count, project_count = row if row else (0, 0)

                migration_result = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "dry_run": dry_run,
                    "old_path": old_path,
                    "new_path": new_path,
                    "todos_affected": todo_count,
                    "projects_affected": project_count,
                    "migrated": 0,
                }

                if todo_count > 0 and not dry_run:
                    cursor.execute(
                        """
                        UPDATE todowrite_plans
                        SET worktree_path = %s,
                            updated_at = %s
                        WHERE worktree_path = %s
                        RETURNING id
                        """,
                        (new_path, int(time.time()), old_path),
                    )

                    migrated = cursor.rowcount
                    conn.commit()
                    migration_result["migrated"] = migrated

                    logger.info(
                        f"Migrated {migrated} todos from {old_path} to {new_path}"
                    )
                else:
                    logger.info(
                        f"[DRY RUN] Would migrate {todo_count} todos from {old_path} to {new_path}"
                    )

                return migration_result

        except Exception as e:
            logger.error(f"Error migrating worktree path: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    @staticmethod
    def verify_worktree_health(project_id: int) -> Dict[str, Any]:
        """Verify consistency and health of worktree-scoped data.

        Args:
            project_id: Project ID to verify

        Returns:
            Dict with health check results
        """
        try:
            with PooledConnection() as conn:
                cursor = conn.cursor()

                health_report = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "project_id": project_id,
                    "checks": {},
                    "status": "healthy",
                }

                # Check 1: Todos with NULL worktree_path
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM todowrite_plans
                    WHERE project_id = %s AND worktree_path IS NULL
                    """,
                    (project_id,),
                )
                null_worktree_count = cursor.fetchone()[0]
                health_report["checks"]["non_worktree_todos"] = {
                    "count": null_worktree_count,
                    "status": "ok",
                }

                # Check 2: Todos with valid worktree_path entries
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT worktree_path) FROM todowrite_plans
                    WHERE project_id = %s AND worktree_path IS NOT NULL
                    """,
                    (project_id,),
                )
                distinct_worktrees = cursor.fetchone()[0]
                health_report["checks"]["distinct_worktrees"] = {
                    "count": distinct_worktrees,
                    "status": "ok",
                }

                # Check 3: Memory events with worktree tagging
                cursor.execute(
                    """
                    SELECT
                        COUNT(CASE WHEN worktree_path IS NULL THEN 1 END) as untagged,
                        COUNT(CASE WHEN worktree_path IS NOT NULL THEN 1 END) as tagged
                    FROM episodic_events
                    WHERE project_id = %s AND lifecycle_status = 'active'
                    """,
                    (project_id,),
                )
                row = cursor.fetchone()
                untagged, tagged = row if row else (0, 0)
                health_report["checks"]["memory_worktree_tagging"] = {
                    "untagged_memories": untagged,
                    "tagged_memories": tagged,
                    "status": "ok" if tagged > 0 or untagged == 0 else "warning",
                }

                # Check 4: Consistency - does status match lifecycle?
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM todowrite_plans
                    WHERE project_id = %s
                      AND status = 'completed'
                      AND sync_status != 'orphaned_cleanup'
                    """,
                    (project_id,),
                )
                completed_todos = cursor.fetchone()[0]
                health_report["checks"]["completed_todos"] = {
                    "count": completed_todos,
                    "status": "ok",
                }

                # Overall status
                if any(c.get("status") == "error" for c in health_report["checks"].values()):
                    health_report["status"] = "error"
                elif any(c.get("status") == "warning" for c in health_report["checks"].values()):
                    health_report["status"] = "warning"

                logger.info(f"Worktree health check completed: {health_report['status']}")
                return health_report

        except Exception as e:
            logger.error(f"Error verifying worktree health: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
            }

    @staticmethod
    def get_maintenance_report(project_id: int, check_filesystem: bool = True) -> Dict[str, Any]:
        """Generate a comprehensive maintenance report.

        Args:
            project_id: Project ID
            check_filesystem: If True, verify worktree paths on disk

        Returns:
            Dict with full maintenance analysis
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "sections": {},
        }

        # Section 1: Orphaned todos
        report["sections"]["orphaned_todos"] = WorktreeMaintenance.find_orphaned_todos(
            project_id, check_filesystem=check_filesystem
        )

        # Section 2: Health check
        report["sections"]["health_check"] = WorktreeMaintenance.verify_worktree_health(project_id)

        # Section 3: Recommendations
        recommendations = []

        orphaned_count = report["sections"]["orphaned_todos"].get("orphaned_count", 0)
        if orphaned_count > 0:
            recommendations.append(
                f"Found {orphaned_count} orphaned todos. Run `cleanup_orphaned_todos()` to mark as completed."
            )

        if report["sections"]["health_check"].get("status") == "warning":
            recommendations.append("Worktree health check shows warnings. Review memory tagging.")

        report["recommendations"] = recommendations if recommendations else ["System is healthy"]
        report["overall_status"] = (
            "healthy"
            if orphaned_count == 0 and report["sections"]["health_check"].get("status") == "healthy"
            else "needs_attention"
        )

        logger.info(f"Maintenance report generated: {report['overall_status']}")
        return report
