"""Memory optimization: pruning and scoring."""

import time

from ..core.database import Database


class MemoryOptimizer:
    """Optimize memory storage through scoring and pruning."""

    def __init__(self, db: Database):
        """Initialize optimizer.

        Args:
            db: Database instance
        """
        self.db = db

    def update_usefulness_scores(self, project_id: int):
        """Recalculate usefulness scores for all memories.

        Score formula:
        - 40% access frequency (accesses per day since creation)
        - 30% recency (decay over time since last access)
        - 30% memory type priority (decisions > patterns > facts > context)

        Args:
            project_id: Project ID to update
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            UPDATE memories
            SET usefulness_score = (
                -- Access frequency (normalized by age)
                0.4 * (
                    access_count /
                    CAST((julianday('now') - julianday(created_at, 'unixepoch')) AS REAL)
                ) +
                -- Recency (1.0 if accessed today, decays to 0 over 90 days)
                0.3 * CASE
                    WHEN last_accessed IS NULL THEN 0.5
                    ELSE MAX(0, 1.0 - (
                        (julianday('now') - julianday(last_accessed, 'unixepoch')) / 90.0
                    ))
                END +
                -- Memory type priority
                0.3 * CASE memory_type
                    WHEN 'decision' THEN 1.0
                    WHEN 'pattern' THEN 0.9
                    WHEN 'fact' THEN 0.7
                    WHEN 'context' THEN 0.5
                    ELSE 0.5
                END
            )
            WHERE project_id = ?
        """,
            (project_id,),
        )

        # commit handled by cursor context

    def prune_low_value_memories(
        self,
        project_id: int,
        score_threshold: float = 0.2,
        age_threshold_days: int = 90,
        dry_run: bool = False,
    ) -> int:
        """Delete memories with low usefulness scores.

        Args:
            project_id: Project ID
            score_threshold: Minimum usefulness score (0-1)
            age_threshold_days: Minimum age in days since last access
            dry_run: If True, return count without deleting

        Returns:
            Number of memories that would be/were pruned
        """
        cursor = self.db.get_cursor()

        age_cutoff = int(time.time()) - (age_threshold_days * 86400)

        if dry_run:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM memories
                WHERE project_id = ?
                AND usefulness_score < ?
                AND (last_accessed IS NULL OR last_accessed < ?)
            """,
                (project_id, score_threshold, age_cutoff),
            )
            return cursor.fetchone()[0]

        # Get IDs to delete
        cursor.execute(
            """
            SELECT id
            FROM memories
            WHERE project_id = ?
            AND usefulness_score < ?
            AND (last_accessed IS NULL OR last_accessed < ?)
        """,
            (project_id, score_threshold, age_cutoff),
        )
        ids_to_delete = [row[0] for row in cursor.fetchall()]

        # Delete memories and vectors
        for memory_id in ids_to_delete:
            self.db.delete_memory(memory_id)

        return len(ids_to_delete)

    def optimize(self, project_id: int, dry_run: bool = False) -> dict:
        """Run full optimization: update scores and prune.

        Args:
            project_id: Project ID
            dry_run: If True, don't actually delete

        Returns:
            Optimization statistics
        """
        # Update scores first
        self.update_usefulness_scores(project_id)

        # Get stats before pruning
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT COUNT(*), AVG(usefulness_score) FROM memories WHERE project_id = ?",
            (project_id,),
        )
        before_count, avg_score = cursor.fetchone()

        # Prune low-value memories
        pruned = self.prune_low_value_memories(project_id, dry_run=dry_run)

        # Get stats after pruning
        cursor.execute(
            "SELECT COUNT(*), AVG(usefulness_score) FROM memories WHERE project_id = ?",
            (project_id,),
        )
        after_count, avg_score_after = cursor.fetchone()

        # Update optimization stats
        if not dry_run:
            cursor.execute(
                """
                INSERT INTO optimization_stats (project_id, last_optimized, memories_pruned, avg_usefulness)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    last_optimized = excluded.last_optimized,
                    memories_pruned = optimization_stats.memories_pruned + excluded.memories_pruned,
                    avg_usefulness = excluded.avg_usefulness
            """,
                (project_id, int(time.time()), pruned, avg_score_after or 0.0),
            )
            # commit handled by cursor context

        return {
            "before_count": before_count,
            "after_count": after_count,
            "pruned": pruned,
            "avg_score_before": round(avg_score or 0.0, 3),
            "avg_score_after": round(avg_score_after or 0.0, 3),
            "dry_run": dry_run,
        }

    def get_optimization_stats(self, project_id: int) -> dict:
        """Get optimization statistics for a project.

        Args:
            project_id: Project ID

        Returns:
            Optimization stats
        """
        cursor = self.db.get_cursor()
        cursor.execute("SELECT * FROM optimization_stats WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()

        if not row:
            return {
                "last_optimized": None,
                "total_pruned": 0,
                "avg_usefulness": 0.0,
            }

        return {
            "last_optimized": row["last_optimized"],
            "total_pruned": row["memories_pruned"],
            "avg_usefulness": round(row["avg_usefulness"], 3),
        }
