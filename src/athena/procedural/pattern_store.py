"""Pattern store for learning and retrieving code patterns.

Database layer for:
- Refactoring patterns
- Bug-fix patterns
- Code smells
- Architectural patterns
- Pattern applications and suggestions
"""

from datetime import datetime
from typing import Optional

from ..core.database import Database
from .code_patterns import (
    RefactoringPattern,
    RefactoringType,
    BugFixPattern,
    BugFixType,
    CodeSmellPattern,
    CodeSmellType,
    PatternApplication,
    PatternSuggestion,
)


class PatternStore:
    """Store for code patterns."""

    def __init__(self, db: Database):
        """Initialize pattern store."""
        self.db = db

    def create_refactoring_pattern(self, pattern: RefactoringPattern) -> int:
        """Create a refactoring pattern."""
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            INSERT INTO refactoring_patterns (
                refactoring_type, description, before_pattern,
                after_pattern, language, frequency, effectiveness,
                learned_from_commits, is_template, template_name,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pattern.refactoring_type.value,
                pattern.description,
                pattern.before_pattern,
                pattern.after_pattern,
                pattern.language,
                pattern.frequency,
                pattern.effectiveness,
                "|".join(pattern.learned_from_commits),
                int(pattern.is_template),
                pattern.template_name,
                now,
                now,
            ),
        )
        # commit handled by cursor context
        return cursor.lastrowid

    def create_bug_fix_pattern(self, pattern: BugFixPattern) -> int:
        """Create a bug-fix pattern."""
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            INSERT INTO bug_fix_patterns (
                bug_type, description, symptoms, root_causes,
                solution, prevention_steps, language, frequency,
                confidence, learned_from_regressions, time_to_fix_minutes,
                is_critical, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pattern.bug_type.value,
                pattern.description,
                "|".join(pattern.symptoms),
                "|".join(pattern.root_causes),
                pattern.solution,
                "|".join(pattern.prevention_steps),
                pattern.language,
                pattern.frequency,
                pattern.confidence,
                "|".join(str(r) for r in pattern.learned_from_regressions),
                pattern.time_to_fix_minutes,
                int(pattern.is_critical),
                now,
                now,
            ),
        )
        # commit handled by cursor context
        return cursor.lastrowid

    def create_code_smell_pattern(self, pattern: CodeSmellPattern) -> int:
        """Create a code smell pattern."""
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            INSERT INTO code_smell_patterns (
                smell_type, description, detection_rule, severity,
                affected_file, affected_symbol, suggested_fixes,
                frequency_in_codebase, priority, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pattern.smell_type.value,
                pattern.description,
                pattern.detection_rule,
                pattern.severity,
                pattern.affected_file,
                pattern.affected_symbol,
                "|".join(pattern.suggested_fixes),
                pattern.frequency_in_codebase,
                pattern.priority,
                now,
            ),
        )
        # commit handled by cursor context
        return cursor.lastrowid

    def get_refactoring_patterns(
        self,
        refactoring_type: Optional[RefactoringType] = None,
        language: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get refactoring patterns with optional filtering."""
        cursor = self.db.get_cursor()

        query = "SELECT * FROM refactoring_patterns WHERE 1=1"
        params = []

        if refactoring_type:
            query += " AND refactoring_type = ?"
            params.append(refactoring_type.value)

        if language:
            query += " AND language = ?"
            params.append(language)

        query += " ORDER BY frequency DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        return [
            {
                "id": row[0],
                "refactoring_type": row[1],
                "description": row[2],
                "before_pattern": row[3],
                "after_pattern": row[4],
                "language": row[5],
                "frequency": row[6],
                "effectiveness": row[7],
            }
            for row in cursor.fetchall()
        ]

    def get_bug_fix_patterns(
        self,
        bug_type: Optional[BugFixType] = None,
        language: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get bug-fix patterns with optional filtering."""
        cursor = self.db.get_cursor()

        query = "SELECT * FROM bug_fix_patterns WHERE 1=1"
        params = []

        if bug_type:
            query += " AND bug_type = ?"
            params.append(bug_type.value)

        if language:
            query += " AND language = ?"
            params.append(language)

        query += " ORDER BY confidence DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        return [
            {
                "id": row[0],
                "bug_type": row[1],
                "description": row[2],
                "solution": row[5],
                "language": row[7],
                "frequency": row[8],
                "confidence": row[9],
            }
            for row in cursor.fetchall()
        ]

    def get_code_smell_patterns(
        self,
        smell_type: Optional[CodeSmellType] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get code smell patterns."""
        cursor = self.db.get_cursor()

        query = "SELECT * FROM code_smell_patterns WHERE 1=1"
        params = []

        if smell_type:
            query += " AND smell_type = ?"
            params.append(smell_type.value)

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY priority DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        return [
            {
                "id": row[0],
                "smell_type": row[1],
                "description": row[2],
                "severity": row[4],
                "priority": row[9],
            }
            for row in cursor.fetchall()
        ]

    def record_pattern_application(self, application: PatternApplication) -> int:
        """Record application of a pattern."""
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp())

        cursor.execute(
            """
            INSERT INTO pattern_applications (
                pattern_id, pattern_type, commit_hash, author,
                timestamp, success, outcome, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application.pattern_id,
                application.pattern_type.value,
                application.commit_hash,
                application.author,
                int(application.timestamp.timestamp()),
                int(application.success),
                application.outcome,
                now,
            ),
        )
        # commit handled by cursor context
        return cursor.lastrowid

    def suggest_pattern(self, suggestion: PatternSuggestion) -> int:
        """Create a pattern suggestion."""
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            INSERT INTO pattern_suggestions (
                pattern_id, pattern_type, file_path, location,
                confidence, reason, impact, effort, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                suggestion.pattern_id,
                suggestion.pattern_type.value,
                suggestion.file_path,
                suggestion.location,
                suggestion.confidence,
                suggestion.reason,
                suggestion.impact,
                suggestion.effort,
                int(suggestion.created_at.timestamp()),
            ),
        )
        # commit handled by cursor context
        return cursor.lastrowid

    def get_suggestions_for_file(self, file_path: str) -> list[dict]:
        """Get pattern suggestions for a specific file."""
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT id, pattern_type, location, confidence, reason
            FROM pattern_suggestions
            WHERE file_path = ? AND dismissed = 0 AND applied = 0
            ORDER BY confidence DESC
            """,
            (file_path,),
        )

        return [
            {
                "id": row[0],
                "pattern_type": row[1],
                "location": row[2],
                "confidence": row[3],
                "reason": row[4],
            }
            for row in cursor.fetchall()
        ]

    def get_statistics(self) -> dict:
        """Get pattern statistics."""
        cursor = self.db.get_cursor()

        # Count patterns by type
        cursor.execute(
            """
            SELECT refactoring_type, COUNT(*) FROM refactoring_patterns
            GROUP BY refactoring_type
            """
        )
        refactoring_stats = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT bug_type, COUNT(*) FROM bug_fix_patterns
            GROUP BY bug_type
            """
        )
        bug_fix_stats = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT smell_type, COUNT(*) FROM code_smell_patterns
            GROUP BY smell_type
            """
        )
        smell_stats = {row[0]: row[1] for row in cursor.fetchall()}

        # Count applications
        cursor.execute("SELECT COUNT(*) FROM pattern_applications WHERE success = 1")
        successful_applications = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM pattern_applications")
        total_applications = cursor.fetchone()[0]

        return {
            "refactoring_patterns": refactoring_stats,
            "bug_fix_patterns": bug_fix_stats,
            "code_smell_patterns": smell_stats,
            "total_refactoring_patterns": len(refactoring_stats),
            "total_bug_fix_patterns": len(bug_fix_stats),
            "total_smell_patterns": len(smell_stats),
            "successful_applications": successful_applications,
            "total_applications": total_applications,
            "application_success_rate": (
                successful_applications / total_applications if total_applications > 0 else 0
            ),
        }

    def get_most_effective_patterns(
        self, pattern_type: str = "refactoring", limit: int = 10
    ) -> list[dict]:
        """Get most effective patterns."""
        cursor = self.db.get_cursor()

        if pattern_type == "refactoring":
            cursor.execute(
                """
                SELECT id, description, effectiveness, frequency
                FROM refactoring_patterns
                ORDER BY effectiveness DESC, frequency DESC
                LIMIT ?
                """,
                (limit,),
            )
        elif pattern_type == "bug_fix":
            cursor.execute(
                """
                SELECT id, description, confidence, frequency
                FROM bug_fix_patterns
                ORDER BY confidence DESC, frequency DESC
                LIMIT ?
                """,
                (limit,),
            )
        else:
            return []

        return [
            {
                "id": row[0],
                "description": row[1],
                "score": row[2],
                "frequency": row[3],
            }
            for row in cursor.fetchall()
        ]
