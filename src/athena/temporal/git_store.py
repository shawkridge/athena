"""Git-aware temporal store for version control metadata.

Manages storage and retrieval of git commits, file changes, regressions,
and author metrics with automatic temporal chain linking.
"""

from datetime import datetime
from typing import Optional

from ..core.database import Database
from .git_models import (
    AuthorMetrics,
    BranchMetrics,
    GitChangeType,
    GitCommitEvent,
    GitFileChange,
    GitMetadata,
    GitTemporalRelation,
    RegressionAnalysis,
    RegressionType,
)


class GitStore:
    """Store for git-aware temporal data."""

    def __init__(self, db: Database):
        """Initialize git store with database connection."""
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self):
        """Create git-aware tables if they don't exist."""
        cursor = self.db.conn.cursor()

        # Git commits table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS git_commits (
                id INTEGER PRIMARY KEY,
                event_id INTEGER,
                commit_hash TEXT UNIQUE NOT NULL,
                commit_message TEXT NOT NULL,
                author TEXT NOT NULL,
                author_email TEXT,
                committer TEXT,
                committer_email TEXT,
                committed_timestamp INTEGER NOT NULL,
                branch TEXT NOT NULL,
                files_changed INTEGER DEFAULT 0,
                insertions INTEGER DEFAULT 0,
                deletions INTEGER DEFAULT 0,
                is_merge INTEGER DEFAULT 0,
                is_release INTEGER DEFAULT 0,
                parents TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(event_id) REFERENCES episodic_events(id)
            )
            """
        )

        # Git file changes table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS git_file_changes (
                id INTEGER PRIMARY KEY,
                commit_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                change_type TEXT NOT NULL,
                old_path TEXT,
                insertions INTEGER DEFAULT 0,
                deletions INTEGER DEFAULT 0,
                hunks INTEGER DEFAULT 0,
                patch TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(commit_id) REFERENCES git_commits(id)
            )
            """
        )

        # Regression analysis table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS git_regressions (
                id INTEGER PRIMARY KEY,
                regression_type TEXT NOT NULL,
                regression_description TEXT NOT NULL,
                introducing_commit TEXT NOT NULL,
                discovered_commit TEXT NOT NULL,
                discovered_event_id INTEGER,
                fix_commit TEXT,
                affected_files TEXT,
                affected_symbols TEXT,
                root_cause TEXT,
                impact_estimate REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.5,
                bisect_verified INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(discovered_event_id) REFERENCES episodic_events(id),
                FOREIGN KEY(introducing_commit) REFERENCES git_commits(commit_hash),
                FOREIGN KEY(discovered_commit) REFERENCES git_commits(commit_hash)
            )
            """
        )

        # Author metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS git_author_metrics (
                id INTEGER PRIMARY KEY,
                author TEXT UNIQUE NOT NULL,
                email TEXT,
                commits_count INTEGER DEFAULT 0,
                files_changed_total INTEGER DEFAULT 0,
                insertions_total INTEGER DEFAULT 0,
                deletions_total INTEGER DEFAULT 0,
                merge_commits INTEGER DEFAULT 0,
                regressions_introduced INTEGER DEFAULT 0,
                regressions_fixed INTEGER DEFAULT 0,
                avg_commit_size REAL DEFAULT 0.0,
                specialization TEXT,
                last_commit_timestamp INTEGER,
                most_frequent_file_patterns TEXT,
                updated_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )

        # Git temporal relations table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS git_temporal_relations (
                id INTEGER PRIMARY KEY,
                from_commit TEXT NOT NULL,
                to_commit TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL NOT NULL,
                distance_commits INTEGER DEFAULT 0,
                time_delta_seconds INTEGER DEFAULT 0,
                file_overlap REAL DEFAULT 0.0,
                inferred_at INTEGER NOT NULL,
                FOREIGN KEY(from_commit) REFERENCES git_commits(commit_hash),
                FOREIGN KEY(to_commit) REFERENCES git_commits(commit_hash)
            )
            """
        )

        # Branch metrics table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS git_branch_metrics (
                id INTEGER PRIMARY KEY,
                branch_name TEXT UNIQUE NOT NULL,
                is_main INTEGER DEFAULT 0,
                is_protected INTEGER DEFAULT 0,
                created_timestamp INTEGER NOT NULL,
                last_commit_timestamp INTEGER,
                commits_ahead_of_main INTEGER DEFAULT 0,
                commits_behind_main INTEGER DEFAULT 0,
                merge_commits_on_branch INTEGER DEFAULT 0,
                open_regressions INTEGER DEFAULT 0,
                updated_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )

        # Create indexes for fast lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_git_commits_hash
            ON git_commits(commit_hash)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_git_commits_author
            ON git_commits(author)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_git_commits_timestamp
            ON git_commits(committed_timestamp)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_git_file_changes_commit
            ON git_file_changes(commit_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_git_file_changes_path
            ON git_file_changes(file_path)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_git_regressions_introducing
            ON git_regressions(introducing_commit)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_git_regressions_type
            ON git_regressions(regression_type)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_git_temporal_from
            ON git_temporal_relations(from_commit)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_git_temporal_to
            ON git_temporal_relations(to_commit)
            """
        )

        self.db.conn.commit()

    def create_commit(
        self, git_metadata: GitMetadata, event_id: Optional[int] = None
    ) -> int:
        """Insert a git commit and return its ID."""
        cursor = self.db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            INSERT INTO git_commits (
                event_id, commit_hash, commit_message, author, author_email,
                committer, committer_email, committed_timestamp, branch,
                files_changed, insertions, deletions, parents, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                git_metadata.commit_hash,
                git_metadata.commit_message,
                git_metadata.author,
                git_metadata.author_email,
                git_metadata.committer,
                git_metadata.committer_email,
                int(git_metadata.committed_timestamp.timestamp()),
                git_metadata.branch,
                git_metadata.files_changed,
                git_metadata.insertions,
                git_metadata.deletions,
                "|".join(git_metadata.parents),
                now,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def add_file_change(
        self, commit_id: int, file_change: GitFileChange
    ) -> int:
        """Add a file change to a commit."""
        cursor = self.db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            INSERT INTO git_file_changes (
                commit_id, file_path, change_type, old_path,
                insertions, deletions, hunks, patch, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                commit_id,
                file_change.file_path,
                file_change.change_type.value,
                file_change.old_path,
                file_change.insertions,
                file_change.deletions,
                file_change.hunks,
                file_change.patch,
                now,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def create_commit_event(
        self, commit_event: GitCommitEvent
    ) -> tuple[int, list[int]]:
        """Create a full commit event with file changes. Returns (commit_id, file_change_ids)."""
        commit_id = self.create_commit(
            commit_event.git_metadata, commit_event.event_id
        )

        file_change_ids = []
        for file_change in commit_event.file_changes:
            file_id = self.add_file_change(commit_id, file_change)
            file_change_ids.append(file_id)

        return commit_id, file_change_ids

    def get_commit(self, commit_hash: str) -> Optional[dict]:
        """Retrieve a commit by hash."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT id, event_id, commit_hash, commit_message, author,
                   author_email, committer, committer_email,
                   committed_timestamp, branch, files_changed,
                   insertions, deletions, is_merge, is_release
            FROM git_commits WHERE commit_hash = ?
            """,
            (commit_hash,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "event_id": row[1],
            "commit_hash": row[2],
            "commit_message": row[3],
            "author": row[4],
            "author_email": row[5],
            "committer": row[6],
            "committer_email": row[7],
            "committed_timestamp": datetime.fromtimestamp(row[8]),
            "branch": row[9],
            "files_changed": row[10],
            "insertions": row[11],
            "deletions": row[12],
            "is_merge": bool(row[13]),
            "is_release": bool(row[14]),
        }

    def get_commit_file_changes(self, commit_id: int) -> list[dict]:
        """Get all file changes for a commit."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT id, file_path, change_type, old_path,
                   insertions, deletions, hunks
            FROM git_file_changes
            WHERE commit_id = ?
            """,
            (commit_id,),
        )

        return [
            {
                "id": row[0],
                "file_path": row[1],
                "change_type": row[2],
                "old_path": row[3],
                "insertions": row[4],
                "deletions": row[5],
                "hunks": row[6],
            }
            for row in cursor.fetchall()
        ]

    def get_commits_by_author(self, author: str, limit: int = 100) -> list[dict]:
        """Get commits by a specific author."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT id, commit_hash, commit_message, committed_timestamp,
                   branch, files_changed, insertions, deletions
            FROM git_commits
            WHERE author = ?
            ORDER BY committed_timestamp DESC
            LIMIT ?
            """,
            (author, limit),
        )

        return [
            {
                "id": row[0],
                "commit_hash": row[1],
                "commit_message": row[2],
                "committed_timestamp": datetime.fromtimestamp(row[3]),
                "branch": row[4],
                "files_changed": row[5],
                "insertions": row[6],
                "deletions": row[7],
            }
            for row in cursor.fetchall()
        ]

    def get_commits_by_file(self, file_path: str, limit: int = 50) -> list[dict]:
        """Get all commits that touched a specific file."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT gc.id, gc.commit_hash, gc.commit_message,
                   gc.author, gc.committed_timestamp, gfc.change_type
            FROM git_commits gc
            JOIN git_file_changes gfc ON gc.id = gfc.commit_id
            WHERE gfc.file_path = ?
            ORDER BY gc.committed_timestamp DESC
            LIMIT ?
            """,
            (file_path, limit),
        )

        return [
            {
                "id": row[0],
                "commit_hash": row[1],
                "commit_message": row[2],
                "author": row[3],
                "committed_timestamp": datetime.fromtimestamp(row[4]),
                "change_type": row[5],
            }
            for row in cursor.fetchall()
        ]

    def record_regression(
        self, regression: RegressionAnalysis
    ) -> int:
        """Record a regression analysis."""
        cursor = self.db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            INSERT INTO git_regressions (
                regression_type, regression_description,
                introducing_commit, discovered_commit,
                discovered_event_id, fix_commit,
                affected_files, affected_symbols,
                root_cause, impact_estimate, confidence,
                bisect_verified, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                regression.regression_type.value,
                regression.regression_description,
                regression.introducing_commit,
                regression.discovered_commit,
                regression.discovered_event_id,
                regression.fix_commit,
                "|".join(regression.affected_files),
                "|".join(regression.affected_symbols),
                regression.root_cause_analysis,
                regression.impact_estimate,
                regression.confidence,
                int(regression.bisect_verified),
                now,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def get_regressions_by_type(
        self, regression_type: RegressionType, limit: int = 50
    ) -> list[dict]:
        """Get all regressions of a specific type."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT id, regression_description, introducing_commit,
                   discovered_commit, fix_commit, impact_estimate,
                   confidence, bisect_verified, created_at
            FROM git_regressions
            WHERE regression_type = ?
            ORDER BY impact_estimate DESC, created_at DESC
            LIMIT ?
            """,
            (regression_type.value, limit),
        )

        return [
            {
                "id": row[0],
                "description": row[1],
                "introducing_commit": row[2],
                "discovered_commit": row[3],
                "fix_commit": row[4],
                "impact_estimate": row[5],
                "confidence": row[6],
                "bisect_verified": bool(row[7]),
                "created_at": datetime.fromtimestamp(row[8]),
            }
            for row in cursor.fetchall()
        ]

    def get_regressions_by_commit(
        self, commit_hash: str
    ) -> list[dict]:
        """Get all regressions introduced by a commit."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT id, regression_type, regression_description,
                   discovered_commit, fix_commit, impact_estimate,
                   confidence, created_at
            FROM git_regressions
            WHERE introducing_commit = ?
            ORDER BY impact_estimate DESC
            """,
            (commit_hash,),
        )

        return [
            {
                "id": row[0],
                "type": row[1],
                "description": row[2],
                "discovered_commit": row[3],
                "fix_commit": row[4],
                "impact_estimate": row[5],
                "confidence": row[6],
                "created_at": datetime.fromtimestamp(row[7]),
            }
            for row in cursor.fetchall()
        ]

    def update_author_metrics(
        self, metrics: AuthorMetrics
    ) -> int:
        """Update or create author metrics."""
        cursor = self.db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            INSERT OR REPLACE INTO git_author_metrics (
                author, email, commits_count, files_changed_total,
                insertions_total, deletions_total, merge_commits,
                regressions_introduced, regressions_fixed,
                avg_commit_size, specialization,
                last_commit_timestamp,
                most_frequent_file_patterns,
                updated_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metrics.author,
                metrics.email,
                metrics.commits_count,
                metrics.files_changed_total,
                metrics.insertions_total,
                metrics.deletions_total,
                metrics.merge_commits,
                metrics.regressions_introduced,
                metrics.regressions_fixed,
                metrics.avg_commit_size,
                metrics.specialization,
                int(metrics.last_commit_timestamp.timestamp())
                if metrics.last_commit_timestamp
                else None,
                "|".join(metrics.most_frequent_file_patterns),
                now,
                now,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def get_author_metrics(self, author: str) -> Optional[dict]:
        """Get metrics for a specific author."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT id, author, email, commits_count,
                   files_changed_total, insertions_total, deletions_total,
                   merge_commits, regressions_introduced, regressions_fixed,
                   avg_commit_size, specialization,
                   last_commit_timestamp, most_frequent_file_patterns
            FROM git_author_metrics
            WHERE author = ?
            """,
            (author,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "author": row[1],
            "email": row[2],
            "commits_count": row[3],
            "files_changed_total": row[4],
            "insertions_total": row[5],
            "deletions_total": row[6],
            "merge_commits": row[7],
            "regressions_introduced": row[8],
            "regressions_fixed": row[9],
            "avg_commit_size": row[10],
            "specialization": row[11],
            "last_commit_timestamp": (
                datetime.fromtimestamp(row[12]) if row[12] else None
            ),
            "most_frequent_file_patterns": (
                row[13].split("|") if row[13] else []
            ),
        }

    def create_temporal_relation(
        self, relation: GitTemporalRelation
    ) -> int:
        """Create a git temporal relation between commits."""
        cursor = self.db.conn.cursor()

        cursor.execute(
            """
            INSERT INTO git_temporal_relations (
                from_commit, to_commit, relation_type, strength,
                distance_commits, time_delta_seconds, file_overlap,
                inferred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                relation.from_commit,
                relation.to_commit,
                relation.relation_type,
                relation.strength,
                relation.distance_commits,
                relation.time_delta_seconds,
                relation.file_overlap,
                int(relation.inferred_at.timestamp()),
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def get_temporal_relations_from(
        self, commit_hash: str
    ) -> list[dict]:
        """Get all temporal relations from a commit."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT to_commit, relation_type, strength,
                   distance_commits, file_overlap
            FROM git_temporal_relations
            WHERE from_commit = ?
            ORDER BY strength DESC
            """,
            (commit_hash,),
        )

        return [
            {
                "to_commit": row[0],
                "relation_type": row[1],
                "strength": row[2],
                "distance_commits": row[3],
                "file_overlap": row[4],
            }
            for row in cursor.fetchall()
        ]

    def update_branch_metrics(
        self, metrics: BranchMetrics
    ) -> int:
        """Update or create branch metrics."""
        cursor = self.db.conn.cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            INSERT OR REPLACE INTO git_branch_metrics (
                branch_name, is_main, is_protected,
                created_timestamp, last_commit_timestamp,
                commits_ahead_of_main, commits_behind_main,
                merge_commits_on_branch, open_regressions,
                updated_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metrics.branch_name,
                int(metrics.is_main),
                int(metrics.is_protected),
                int(metrics.created_timestamp.timestamp()),
                int(metrics.last_commit_timestamp.timestamp())
                if metrics.last_commit_timestamp
                else None,
                metrics.commits_ahead_of_main,
                metrics.commits_behind_main,
                metrics.merge_commits_on_branch,
                metrics.open_regressions,
                now,
                now,
            ),
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def get_branch_metrics(self, branch_name: str) -> Optional[dict]:
        """Get metrics for a specific branch."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT id, branch_name, is_main, is_protected,
                   created_timestamp, last_commit_timestamp,
                   commits_ahead_of_main, commits_behind_main,
                   merge_commits_on_branch, open_regressions
            FROM git_branch_metrics
            WHERE branch_name = ?
            """,
            (branch_name,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "branch_name": row[1],
            "is_main": bool(row[2]),
            "is_protected": bool(row[3]),
            "created_timestamp": datetime.fromtimestamp(row[4]),
            "last_commit_timestamp": (
                datetime.fromtimestamp(row[5]) if row[5] else None
            ),
            "commits_ahead_of_main": row[6],
            "commits_behind_main": row[7],
            "merge_commits_on_branch": row[8],
            "open_regressions": row[9],
        }
