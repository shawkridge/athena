"""Pattern suggestion engine for recommending improvements.

Combines pattern matching with contextual analysis to:
- Suggest refactoring opportunities
- Recommend bug-fix patterns for errors
- Detect code smells with severity scoring
- Track suggestion history and effectiveness
"""

from datetime import datetime
from typing import Optional

from ..core.database import Database
from .code_patterns import (
    PatternSuggestion,
    PatternType,
)
from .pattern_store import PatternStore
from .pattern_matcher import PatternMatcher


class PatternSuggester:
    """Generate pattern suggestions for code improvements."""

    def __init__(self, db: Database):
        """Initialize pattern suggester."""
        self.db = db
        self.pattern_store = PatternStore(db)
        self.pattern_matcher = PatternMatcher(db)

    def suggest_refactorings(
        self, file_path: str, code_content: str, language: str = "python", limit: int = 5
    ) -> list[PatternSuggestion]:
        """Generate refactoring suggestions for a file.

        Analyzes code and recommends applicable refactoring patterns.
        """
        suggestions = []

        # Match patterns
        matches = self.pattern_matcher.match_refactoring_opportunities(
            file_path, code_content, language, limit=20
        )

        # Convert matches to suggestions
        for match in matches[:limit]:
            suggestion = PatternSuggestion(
                pattern_id=match.pattern_id,
                pattern_type=PatternType.REFACTORING,
                file_path=file_path,
                location=self._extract_location(code_content),
                confidence=match.confidence,
                reason=match.reason,
                impact=match.impact,
                effort=match.effort,
                created_at=datetime.now(),
            )

            # Store suggestion
            suggestion_id = self.pattern_store.suggest_pattern(suggestion)
            suggestion.id = suggestion_id
            suggestions.append(suggestion)

        return suggestions

    def suggest_bug_fixes(
        self, file_path: str, error_description: str, language: str = "python", limit: int = 5
    ) -> list[PatternSuggestion]:
        """Generate bug-fix suggestions for an error.

        Analyzes error and recommends applicable fix patterns.
        """
        suggestions = []

        # Match patterns
        matches = self.pattern_matcher.match_bug_fix_patterns(
            file_path, error_description, language, limit=20
        )

        # Convert matches to suggestions
        for match in matches[:limit]:
            suggestion = PatternSuggestion(
                pattern_id=match.pattern_id,
                pattern_type=PatternType.BUG_FIX,
                file_path=file_path,
                location=self._extract_location(error_description),
                confidence=match.confidence,
                reason=f"Error symptoms match: {match.reason}",
                impact=match.impact,
                effort=match.effort,
                created_at=datetime.now(),
            )

            # Store suggestion
            suggestion_id = self.pattern_store.suggest_pattern(suggestion)
            suggestion.id = suggestion_id
            suggestions.append(suggestion)

        return suggestions

    def suggest_code_smell_fixes(
        self, file_path: str, code_content: str, language: str = "python", limit: int = 5
    ) -> list[PatternSuggestion]:
        """Generate code smell fix suggestions.

        Detects anti-patterns and suggests improvements.
        """
        suggestions = []

        # Detect code smells
        matches = self.pattern_matcher.detect_code_smells(
            file_path, code_content, language, limit=20
        )

        # Convert matches to suggestions
        for match in matches[:limit]:
            suggestion = PatternSuggestion(
                pattern_id=match.pattern_id,
                pattern_type=PatternType.CODE_SMELL,
                file_path=file_path,
                location=self._extract_location(code_content),
                confidence=match.confidence,
                reason=match.reason,
                impact=match.impact,
                effort=match.effort,
                created_at=datetime.now(),
            )

            # Store suggestion
            suggestion_id = self.pattern_store.suggest_pattern(suggestion)
            suggestion.id = suggestion_id
            suggestions.append(suggestion)

        return suggestions

    def suggest_comprehensive(
        self,
        file_path: str,
        code_content: str,
        language: str = "python",
        limit_per_type: int = 3,
    ) -> dict[str, list[PatternSuggestion]]:
        """Generate comprehensive suggestions (refactoring + smells + patterns).

        Returns suggestions organized by type.
        """
        return {
            "refactorings": self.suggest_refactorings(
                file_path, code_content, language, limit_per_type
            ),
            "code_smells": self.suggest_code_smell_fixes(
                file_path, code_content, language, limit_per_type
            ),
        }

    def get_active_suggestions(self, file_path: str) -> list[dict]:
        """Get active (non-dismissed, non-applied) suggestions for a file.

        Returned by pattern_store.get_suggestions_for_file().
        """
        return self.pattern_store.get_suggestions_for_file(file_path)

    def apply_suggestion(self, suggestion_id: int, feedback: Optional[str] = None) -> bool:
        """Mark suggestion as applied.

        Args:
            suggestion_id: ID of suggestion to apply
            feedback: Optional feedback from user

        Returns:
            True if successfully marked applied
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            UPDATE pattern_suggestions
            SET applied = 1, feedback = ?
            WHERE id = ?
            """,
            (feedback, suggestion_id),
        )

        # commit handled by cursor context
        return cursor.rowcount > 0

    def dismiss_suggestion(self, suggestion_id: int, reason: Optional[str] = None) -> bool:
        """Mark suggestion as dismissed (not applicable).

        Args:
            suggestion_id: ID of suggestion to dismiss
            reason: Optional reason for dismissal

        Returns:
            True if successfully marked dismissed
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            UPDATE pattern_suggestions
            SET dismissed = 1, feedback = ?
            WHERE id = ?
            """,
            (reason, suggestion_id),
        )

        # commit handled by cursor context
        return cursor.rowcount > 0

    def measure_suggestion_effectiveness(
        self, pattern_id: int
    ) -> dict[str, float | int]:
        """Measure effectiveness of pattern suggestions.

        Returns stats on how often suggestions were applied vs dismissed.
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN applied = 1 THEN 1 ELSE 0 END) as applied_count,
                SUM(CASE WHEN dismissed = 1 THEN 1 ELSE 0 END) as dismissed_count,
                COUNT(*) as total_suggestions,
                AVG(confidence) as avg_confidence
            FROM pattern_suggestions
            WHERE pattern_id = ?
            """,
            (pattern_id,),
        )

        row = cursor.fetchone()
        applied_count = row[0] or 0
        dismissed_count = row[1] or 0
        total_suggestions = row[2] or 0
        avg_confidence = row[3] or 0.0

        effectiveness_rate = (
            applied_count / total_suggestions if total_suggestions > 0 else 0.0
        )
        dismissal_rate = (
            dismissed_count / total_suggestions if total_suggestions > 0 else 0.0
        )

        return {
            "applied_count": applied_count,
            "dismissed_count": dismissed_count,
            "total_suggestions": total_suggestions,
            "effectiveness_rate": effectiveness_rate,
            "dismissal_rate": dismissal_rate,
            "avg_confidence": float(avg_confidence),
        }

    def get_suggestion_statistics(self) -> dict:
        """Get overall statistics on pattern suggestions.

        Returns aggregated stats on suggestion effectiveness.
        """
        cursor = self.db.get_cursor()

        # Total suggestions
        cursor.execute("SELECT COUNT(*) FROM pattern_suggestions")
        total = cursor.fetchone()[0]

        # Applied suggestions
        cursor.execute("SELECT COUNT(*) FROM pattern_suggestions WHERE applied = 1")
        applied = cursor.fetchone()[0]

        # Dismissed suggestions
        cursor.execute("SELECT COUNT(*) FROM pattern_suggestions WHERE dismissed = 1")
        dismissed = cursor.fetchone()[0]

        # By type
        cursor.execute(
            """
            SELECT pattern_type, COUNT(*) as count,
                   SUM(CASE WHEN applied = 1 THEN 1 ELSE 0 END) as applied
            FROM pattern_suggestions
            GROUP BY pattern_type
            """
        )

        by_type = {}
        for row in cursor.fetchall():
            pattern_type = row[0]
            count = row[1]
            applied_count = row[2] or 0
            by_type[pattern_type] = {
                "count": count,
                "applied": applied_count,
                "effectiveness": applied_count / count if count > 0 else 0.0,
            }

        return {
            "total_suggestions": total,
            "applied": applied,
            "dismissed": dismissed,
            "pending": total - applied - dismissed,
            "overall_effectiveness": applied / total if total > 0 else 0.0,
            "by_type": by_type,
        }

    def get_file_improvement_recommendations(self, file_path: str) -> dict:
        """Get comprehensive improvement recommendations for a file.

        Analyzes all active suggestions and prioritizes improvements.
        """
        suggestions = self.get_active_suggestions(file_path)

        # Group by impact
        by_impact = {"high": [], "medium": [], "low": []}
        for suggestion in suggestions:
            impact = suggestion.get("impact", "medium")
            if impact in by_impact:
                by_impact[impact].append(suggestion)

        # Calculate improvement metrics
        total_suggestions = len(suggestions)
        high_impact = len(by_impact["high"])
        medium_impact = len(by_impact["medium"])
        low_impact = len(by_impact["low"])

        return {
            "file_path": file_path,
            "total_pending_suggestions": total_suggestions,
            "high_impact_count": high_impact,
            "medium_impact_count": medium_impact,
            "low_impact_count": low_impact,
            "recommendations_by_impact": by_impact,
            "priority_score": (high_impact * 1.0 + medium_impact * 0.5 + low_impact * 0.1),
        }

    def _extract_location(self, content: str) -> str:
        """Extract location (line number or symbol name) from content.

        Simple heuristic: use first function/class definition line.
        """
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Look for function/class definitions
            if line.strip().startswith(("def ", "class ")):
                # Extract name
                parts = line.split("(")[0].replace("def ", "").replace("class ", "").strip()
                return f"Line {i}: {parts}"

        # Default to first few lines
        return f"Lines 1-{min(5, len(lines))}"
