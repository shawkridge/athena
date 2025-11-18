"""Git-aware temporal retrieval and analysis functions.

Provides high-level queries for:
- When was a bug introduced?
- Who introduced it?
- What changed since then?
- Impact analysis
- Regression tracking
"""

from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database
from .git_models import RegressionType
from .git_store import GitStore


class GitTemporalRetrieval:
    """High-level retrieval and analysis for git temporal data."""

    def __init__(self, db: Database):
        """Initialize git temporal retrieval."""
        self.db = db
        self.store = GitStore(db)

    def when_was_introduced(self, regression_commit: str) -> Optional[dict]:
        """Find when a specific regression was introduced.

        Returns commit metadata including timestamp, author, message, and files changed.
        """
        commit = self.store.get_commit(regression_commit)
        if not commit:
            return None

        return {
            "commit_hash": commit["commit_hash"],
            "when": commit["committed_timestamp"],
            "author": commit["author"],
            "author_email": commit["author_email"],
            "branch": commit["branch"],
            "message": commit["commit_message"],
            "files_changed": commit["files_changed"],
            "insertions": commit["insertions"],
            "deletions": commit["deletions"],
        }

    def who_introduced_regression(self, regression_commit: str) -> Optional[dict]:
        """Find who introduced a regression.

        Returns author information and their metrics.
        """
        commit = self.store.get_commit(regression_commit)
        if not commit:
            return None

        author = commit["author"]
        metrics = self.store.get_author_metrics(author)

        return {
            "author": author,
            "email": commit["author_email"],
            "commit_hash": regression_commit,
            "commit_message": commit["commit_message"],
            "when": commit["committed_timestamp"],
            "metrics": metrics,
        }

    def what_changed_since(
        self,
        regression_commit: str,
        fix_commit: Optional[str] = None,
        lookback_hours: int = 24,
    ) -> dict:
        """Analyze what changed between regression and fix.

        If fix_commit not provided, shows changes in the lookback period after regression.
        """
        intro_commit = self.store.get_commit(regression_commit)
        if not intro_commit:
            return {"error": "Regression commit not found"}

        intro_time = intro_commit["committed_timestamp"]

        if fix_commit:
            fix_data = self.store.get_commit(fix_commit)
            if not fix_data:
                return {"error": "Fix commit not found"}
            end_time = fix_data["committed_timestamp"]
        else:
            end_time = intro_time + timedelta(hours=lookback_hours)

        # Query all commits between intro and fix
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT gc.id, gc.commit_hash, gc.commit_message, gc.author,
                   gc.committed_timestamp, gc.files_changed,
                   gc.insertions, gc.deletions
            FROM git_commits gc
            WHERE gc.committed_timestamp > ? AND gc.committed_timestamp <= ?
            ORDER BY gc.committed_timestamp ASC
            """,
            (
                int(intro_time.timestamp()),
                int(end_time.timestamp()),
            ),
        )

        commits_between = []
        total_changes = 0
        affected_files = set()

        for row in cursor.fetchall():
            commit_id = row[0]
            commit_hash = row[1]

            # Get file changes for this commit
            file_changes = self.store.get_commit_file_changes(commit_id)
            affected_files.update(fc["file_path"] for fc in file_changes)
            total_changes += row[6] + row[7]  # insertions + deletions

            commits_between.append(
                {
                    "hash": commit_hash,
                    "message": row[2],
                    "author": row[3],
                    "timestamp": datetime.fromtimestamp(row[4]),
                    "files_changed": row[5],
                    "insertions": row[6],
                    "deletions": row[7],
                }
            )

        return {
            "regression_commit": regression_commit,
            "intro_timestamp": intro_time,
            "fix_commit": fix_commit,
            "fix_timestamp": end_time,
            "commits_between": commits_between,
            "total_commits": len(commits_between),
            "affected_files": list(affected_files),
            "total_changes": total_changes,
        }

    def trace_regression_timeline(self, regression_commit: str) -> dict:
        """Create a complete timeline of a regression from introduction to fix.

        Shows: when introduced, discovered, fixed, and related commits.
        """
        regressions = self.store.get_regressions_by_commit(regression_commit)

        if not regressions:
            return {
                "introducing_commit": regression_commit,
                "regressions_found": 0,
                "timeline": [],
            }

        timeline = []
        for reg in regressions:
            intro = self.store.get_commit(regression_commit)
            discovered = self.store.get_commit(reg["discovered_commit"])
            fix = self.store.get_commit(reg["fix_commit"]) if reg["fix_commit"] else None

            timeline.append(
                {
                    "type": reg["type"],
                    "description": reg["description"],
                    "introduced": intro["committed_timestamp"] if intro else None,
                    "discovered": discovered["committed_timestamp"] if discovered else None,
                    "fixed": fix["committed_timestamp"] if fix else None,
                    "time_to_discovery_hours": (
                        (
                            discovered["committed_timestamp"] - intro["committed_timestamp"]
                        ).total_seconds()
                        / 3600
                        if discovered and intro
                        else None
                    ),
                    "time_to_fix_hours": (
                        (fix["committed_timestamp"] - intro["committed_timestamp"]).total_seconds()
                        / 3600
                        if fix and intro
                        else None
                    ),
                    "impact": reg["impact_estimate"],
                    "confidence": reg["confidence"],
                }
            )

        return {
            "introducing_commit": regression_commit,
            "regressions_found": len(timeline),
            "timeline": timeline,
        }

    def find_high_risk_commits(self, limit: int = 20) -> list[dict]:
        """Find commits that introduced the most/highest-impact regressions.

        Ranked by impact estimate and number of regressions.
        """
        cursor = self.db.get_cursor()
        cursor.execute(
            """
            SELECT gr.introducing_commit, COUNT(*) as regression_count,
                   AVG(gr.impact_estimate) as avg_impact,
                   MAX(gr.impact_estimate) as max_impact
            FROM git_regressions gr
            GROUP BY gr.introducing_commit
            ORDER BY max_impact DESC, regression_count DESC, avg_impact DESC
            LIMIT ?
            """,
            (limit,),
        )

        high_risk = []
        for row in cursor.fetchall():
            commit_hash = row[0]
            regression_count = row[1]
            avg_impact = row[2]
            max_impact = row[3]

            commit = self.store.get_commit(commit_hash)
            if commit:
                high_risk.append(
                    {
                        "commit_hash": commit_hash,
                        "author": commit["author"],
                        "timestamp": commit["committed_timestamp"],
                        "message": commit["commit_message"],
                        "regression_count": regression_count,
                        "avg_impact": avg_impact,
                        "max_impact": max_impact,
                    }
                )

        return high_risk

    def analyze_author_risk(self, author: str) -> dict:
        """Analyze regression patterns for a specific author.

        Shows their commit history, regression introduction rate, fix rate.
        """
        commits = self.store.get_commits_by_author(author, limit=1000)
        regressions = self.store.get_regressions_by_type(
            RegressionType.BUG_INTRODUCTION, limit=1000
        )

        # Filter regressions introduced by this author
        author_regressions = [
            r for r in regressions if self._commit_author(r["introducing_commit"]) == author
        ]

        metrics = self.store.get_author_metrics(author)

        return {
            "author": author,
            "total_commits": len(commits),
            "regressions_introduced": len(author_regressions),
            "regression_rate": (len(author_regressions) / len(commits) if commits else 0.0),
            "avg_impact": (
                sum(r["impact_estimate"] for r in author_regressions) / len(author_regressions)
                if author_regressions
                else 0.0
            ),
            "metrics": metrics,
            "regressions": author_regressions[:10],
        }

    def find_related_commits(
        self, commit_hash: str, relation_type: Optional[str] = None
    ) -> list[dict]:
        """Find commits related to a specific commit.

        Can filter by relation type (introduces_regression, fixes_regression, etc).
        """
        relations = self.store.get_temporal_relations_from(commit_hash)

        if relation_type:
            relations = [r for r in relations if r["relation_type"] == relation_type]

        results = []
        for rel in relations:
            related_commit = self.store.get_commit(rel["to_commit"])
            if related_commit:
                results.append(
                    {
                        "commit": related_commit,
                        "relation_type": rel["relation_type"],
                        "strength": rel["strength"],
                        "distance_commits": rel["distance_commits"],
                        "file_overlap": rel["file_overlap"],
                    }
                )

        return results

    def get_regression_statistics(self) -> dict:
        """Get overall regression statistics.

        Shows distribution by type, severity, fix rates, etc.
        """
        cursor = self.db.get_cursor()

        # Total regressions by type
        cursor.execute(
            """
            SELECT regression_type, COUNT(*) as count,
                   AVG(impact_estimate) as avg_impact,
                   COUNT(CASE WHEN fix_commit IS NOT NULL THEN 1 END) as fixed_count
            FROM git_regressions
            GROUP BY regression_type
            """
        )

        stats_by_type = {}
        for row in cursor.fetchall():
            reg_type = row[0]
            count = row[1]
            avg_impact = row[2]
            fixed_count = row[3]

            stats_by_type[reg_type] = {
                "count": count,
                "avg_impact": avg_impact,
                "fixed_count": fixed_count,
                "unfixed_count": count - fixed_count,
                "fix_rate": fixed_count / count if count > 0 else 0.0,
            }

        # Overall stats
        cursor.execute(
            """
            SELECT COUNT(*) as total, AVG(impact_estimate) as avg_impact,
                   COUNT(CASE WHEN fix_commit IS NOT NULL THEN 1 END) as fixed
            FROM git_regressions
            """
        )
        overall = cursor.fetchone()

        return {
            "total_regressions": overall[0],
            "avg_impact": overall[1],
            "total_fixed": overall[2],
            "total_unfixed": overall[0] - (overall[2] or 0),
            "overall_fix_rate": (overall[2] / overall[0] if overall[0] > 0 else 0.0),
            "by_type": stats_by_type,
        }

    def get_file_history(self, file_path: str, include_regressions: bool = True) -> dict:
        """Get complete history of a file including regressions.

        Shows all commits that touched it and any related regressions.
        """
        commits = self.store.get_commits_by_file(file_path, limit=100)

        related_regressions = []
        if include_regressions:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT DISTINCT gr.id, gr.regression_type,
                       gr.regression_description, gr.introducing_commit,
                       gr.discovered_commit, gr.impact_estimate
                FROM git_regressions gr
                WHERE gr.affected_files LIKE ?
                ORDER BY gr.created_at DESC
                """,
                (f"%{file_path}%",),
            )
            related_regressions = [
                {
                    "id": row[0],
                    "type": row[1],
                    "description": row[2],
                    "introducing_commit": row[3],
                    "discovered_commit": row[4],
                    "impact": row[5],
                }
                for row in cursor.fetchall()
            ]

        return {
            "file_path": file_path,
            "total_commits": len(commits),
            "commits": commits,
            "related_regressions": related_regressions,
        }

    def _commit_author(self, commit_hash: str) -> Optional[str]:
        """Helper to get commit author."""
        commit = self.store.get_commit(commit_hash)
        return commit["author"] if commit else None
