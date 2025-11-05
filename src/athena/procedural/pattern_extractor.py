"""Pattern extraction engine for learning from code changes.

Automatically extracts patterns from:
- Git commit history
- Code changes
- Regression fixes
- Refactoring events
"""

from datetime import datetime
from typing import Optional

from ..core.database import Database
from ..temporal.git_store import GitStore
from .code_patterns import (
    RefactoringPattern,
    RefactoringType,
    BugFixPattern,
    BugFixType,
    CodeMetrics,
)
from .pattern_store import PatternStore


class PatternExtractor:
    """Extract patterns from code history."""

    def __init__(self, db: Database):
        """Initialize pattern extractor."""
        self.db = db
        self.git_store = GitStore(db)
        self.pattern_store = PatternStore(db)

    def extract_refactoring_patterns(
        self, lookback_days: int = 90, language: Optional[str] = None
    ) -> list[RefactoringPattern]:
        """Extract refactoring patterns from git history.

        Analyzes commits to identify common refactoring patterns.
        """
        patterns = []

        # Get recent commits
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT id, commit_hash, commit_message, insertions, deletions,
                   files_changed, author
            FROM git_commits
            WHERE committed_timestamp > ?
            ORDER BY committed_timestamp DESC
            """,
            (
                int((datetime.now().timestamp() - (lookback_days * 86400))),
            ),
        )

        commits = cursor.fetchall()

        # Analyze commits for refactoring indicators
        for commit in commits:
            commit_id = commit[0]
            commit_hash = commit[1]
            message = commit[2]
            insertions = commit[3]
            deletions = commit[4]
            files_changed = commit[5]

            # Detect refactoring type from commit message and metrics
            refactoring_type = self._detect_refactoring_type(
                message, insertions, deletions, files_changed
            )

            if refactoring_type:
                # Get file changes for this commit
                file_changes = self.git_store.get_commit_file_changes(
                    commit_id
                )

                metrics = CodeMetrics(
                    lines_added=insertions,
                    lines_deleted=deletions,
                    files_changed=files_changed,
                )

                pattern = RefactoringPattern(
                    refactoring_type=refactoring_type,
                    description=message,
                    language=language or "python",
                    metrics=metrics,
                    learned_from_commits=[commit_hash],
                )

                patterns.append(pattern)

        return patterns

    def extract_bug_fix_patterns(
        self, lookback_days: int = 90, language: Optional[str] = None
    ) -> list[BugFixPattern]:
        """Extract bug-fix patterns from regression history.

        Analyzes regressions and their fixes to identify patterns.
        """
        patterns = []

        # Get regressions and their fixes
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT id, regression_type, regression_description,
                   introducing_commit, discovered_commit, fix_commit,
                   affected_files, impact_estimate, confidence
            FROM git_regressions
            WHERE fix_commit IS NOT NULL
            AND created_at > ?
            """,
            (
                int((datetime.now().timestamp() - (lookback_days * 86400))),
            ),
        )

        regressions = cursor.fetchall()

        for regression in regressions:
            regression_id = regression[0]
            regression_type = regression[1]
            description = regression[2]
            fix_commit = regression[5]
            impact = regression[7]
            confidence = regression[8]

            # Map regression type to bug fix type
            bug_type = self._map_regression_to_bug_type(regression_type)

            if bug_type:
                # Extract symptoms from description
                symptoms = self._extract_symptoms(description)
                solution = self._extract_solution(fix_commit)

                pattern = BugFixPattern(
                    bug_type=bug_type,
                    description=description,
                    symptoms=symptoms,
                    solution=solution,
                    language=language or "python",
                    confidence=confidence,
                    learned_from_regressions=[regression_id],
                )

                patterns.append(pattern)

        return patterns

    def _detect_refactoring_type(
        self,
        commit_message: str,
        insertions: int,
        deletions: int,
        files_changed: int,
    ) -> Optional[RefactoringType]:
        """Detect refactoring type from commit characteristics."""
        message_lower = commit_message.lower()

        # Extract method: increases file count, adds lines
        if (
            "extract" in message_lower
            and "method" in message_lower
            or "consolidate" in message_lower
        ):
            return RefactoringType.EXTRACT_METHOD

        # Rename: similar insertions/deletions, few files
        if (
            "rename" in message_lower
            or "refactor" in message_lower
            and insertions < 50
            and files_changed <= 3
        ):
            return RefactoringType.RENAME

        # Inline: deletions > insertions, removes code
        if "inline" in message_lower or (
            deletions > insertions and files_changed <= 2
        ):
            return RefactoringType.INLINE

        # Remove duplication: similar insertions/deletions, multiple files
        if (
            "dedup" in message_lower
            or "consolidate" in message_lower
            or "dry" in message_lower
        ):
            return RefactoringType.REMOVE_DUPLICATION

        # Simplify
        if "simplif" in message_lower or "cleanup" in message_lower:
            return RefactoringType.CONSOLIDATE_CONDITIONAL

        return None

    def _map_regression_to_bug_type(
        self, regression_type: str
    ) -> Optional[BugFixType]:
        """Map regression type to bug fix type."""
        mapping = {
            "test_failure": BugFixType.LOGIC_ERROR,
            "feature_breakage": BugFixType.API_MISUSE,
            "perf_degradation": BugFixType.TIMEOUT,
            "bug_introduction": BugFixType.LOGIC_ERROR,
            "memory_leak": BugFixType.MEMORY_LEAK,
            "security_issue": BugFixType.INJECTION,
        }
        return mapping.get(regression_type)

    def _extract_symptoms(self, description: str) -> list[str]:
        """Extract symptoms from regression description."""
        symptoms = []

        keywords = {
            "crash": "Application crashes",
            "hang": "Application hangs",
            "timeout": "Operation times out",
            "null": "Null pointer reference",
            "memory": "Memory error",
            "slow": "Performance degradation",
            "incorrect": "Incorrect behavior",
            "fail": "Function fails",
            "error": "Error is thrown",
        }

        for keyword, symptom in keywords.items():
            if keyword in description.lower():
                symptoms.append(symptom)

        return symptoms if symptoms else ["Unexpected behavior"]

    def _extract_solution(self, fix_commit: str) -> str:
        """Extract solution from fix commit."""
        commit = self.git_store.get_commit(fix_commit)
        if commit:
            return commit["commit_message"]
        return "See fix commit"

    def learn_from_file_history(
        self, file_path: str
    ) -> tuple[list[RefactoringPattern], list[BugFixPattern]]:
        """Learn patterns specific to a file from its history."""
        refactoring_patterns = []
        bug_fix_patterns = []

        # Get all commits touching this file
        commits = self.git_store.get_commits_by_file(file_path)

        # Get all regressions affecting this file
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT regression_type, regression_description, fix_commit
            FROM git_regressions
            WHERE affected_files LIKE ?
            AND fix_commit IS NOT NULL
            """,
            (f"%{file_path}%",),
        )

        regressions = cursor.fetchall()

        for regression in regressions:
            reg_type = regression[0]
            description = regression[1]

            bug_type = self._map_regression_to_bug_type(reg_type)
            if bug_type:
                pattern = BugFixPattern(
                    bug_type=bug_type,
                    description=description,
                    solution="See regression fix commits",
                )
                bug_fix_patterns.append(pattern)

        return refactoring_patterns, bug_fix_patterns

    def get_author_patterns(
        self, author: str
    ) -> tuple[list[RefactoringPattern], list[BugFixPattern]]:
        """Get patterns specific to an author."""
        refactoring_patterns = []
        bug_fix_patterns = []

        # Get author's commits
        commits = self.git_store.get_commits_by_author(author, limit=1000)

        # Analyze for patterns
        for commit in commits:
            message = commit["commit_message"]
            insertions = commit.get("insertions", 0)
            deletions = commit.get("deletions", 0)

            refactoring_type = self._detect_refactoring_type(
                message, insertions, deletions, 1
            )

            if refactoring_type:
                pattern = RefactoringPattern(
                    refactoring_type=refactoring_type,
                    description=message,
                    learned_from_commits=[commit["commit_hash"]],
                )
                refactoring_patterns.append(pattern)

        return refactoring_patterns, bug_fix_patterns

    def get_language_patterns(
        self, language: str
    ) -> tuple[list[RefactoringPattern], list[BugFixPattern]]:
        """Get patterns specific to a programming language."""
        patterns = self.pattern_store.get_refactoring_patterns(
            language=language
        )

        refactoring_patterns = [
            RefactoringPattern(
                refactoring_type=RefactoringType(p["refactoring_type"]),
                description=p["description"],
                language=language,
            )
            for p in patterns
        ]

        bug_fix_patterns = self.pattern_store.get_bug_fix_patterns(
            language=language
        )

        return refactoring_patterns, bug_fix_patterns
