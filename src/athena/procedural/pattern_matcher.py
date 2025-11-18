"""Pattern matching engine for detecting applicable code patterns.

Matches current code against learned patterns and generates suggestions:
- Refactoring opportunities detection
- Bug-fix pattern matching when issues arise
- Code smell detection with severity scoring
- Architectural improvement suggestions
"""

from dataclasses import dataclass

from ..core.database import Database
from .code_patterns import (
    RefactoringPattern,
    BugFixPattern,
    CodeSmellPattern,
    PatternType,
)
from .pattern_store import PatternStore


@dataclass
class MatchResult:
    """Result of pattern matching against code."""

    pattern_id: int
    pattern_type: PatternType
    confidence: float  # 0-1, how likely pattern applies
    score: float  # Composite score for ranking
    reason: str  # Why pattern was matched
    impact: str  # "low", "medium", "high"
    effort: str  # "low", "medium", "high"


class PatternMatcher:
    """Match code against learned patterns."""

    def __init__(self, db: Database):
        """Initialize pattern matcher."""
        self.db = db
        self.pattern_store = PatternStore(db)

    def match_refactoring_opportunities(
        self, file_path: str, code_content: str, language: str = "python", limit: int = 10
    ) -> list[MatchResult]:
        """Find refactoring opportunities in code.

        Analyzes code structure and content to suggest applicable refactoring patterns.
        """
        matches = []

        # Get all refactoring patterns for this language
        patterns = self.pattern_store.get_refactoring_patterns(language=language, limit=100)

        for pattern_dict in patterns:
            pattern = RefactoringPattern(
                id=pattern_dict["id"],
                refactoring_type=pattern_dict["refactoring_type"],
                description=pattern_dict["description"],
                before_pattern=pattern_dict.get("before_pattern"),
                after_pattern=pattern_dict.get("after_pattern"),
                language=language,
                frequency=pattern_dict.get("frequency", 0),
                effectiveness=pattern_dict.get("effectiveness", 0.5),
            )

            # Match code against pattern
            confidence = self._match_refactoring_pattern(code_content, pattern)

            if confidence > 0.4:  # Threshold for inclusion
                # Estimate impact and effort based on pattern type and code size
                impact = self._estimate_refactoring_impact(pattern, code_content)
                effort = self._estimate_refactoring_effort(pattern, code_content)

                # Calculate composite score
                score = self._calculate_pattern_score(
                    confidence,
                    pattern.frequency,
                    pattern.effectiveness,
                    impact,
                    effort,
                )

                matches.append(
                    MatchResult(
                        pattern_id=pattern.id,
                        pattern_type=PatternType.REFACTORING,
                        confidence=confidence,
                        score=score,
                        reason=self._explain_refactoring_match(pattern, code_content),
                        impact=impact,
                        effort=effort,
                    )
                )

        # Sort by score (highest first)
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    def match_bug_fix_patterns(
        self, file_path: str, error_description: str, language: str = "python", limit: int = 10
    ) -> list[MatchResult]:
        """Find applicable bug-fix patterns for an error.

        Matches error symptoms against known bug-fix patterns.
        """
        matches = []

        # Get all bug-fix patterns for this language
        patterns = self.pattern_store.get_bug_fix_patterns(language=language, limit=100)

        for pattern_dict in patterns:
            pattern = BugFixPattern(
                id=pattern_dict["id"],
                bug_type=pattern_dict["bug_type"],
                description=pattern_dict["description"],
                solution=pattern_dict["solution"],
                language=language,
                frequency=pattern_dict.get("frequency", 0),
                confidence=pattern_dict.get("confidence", 0.5),
            )

            # Match error symptoms against pattern
            confidence = self._match_bug_fix_pattern(error_description, pattern)

            if confidence > 0.4:  # Threshold for inclusion
                impact = "high"  # Bug fixes have high impact
                effort = self._estimate_bug_fix_effort(pattern)

                # Calculate composite score
                score = self._calculate_pattern_score(
                    confidence,
                    pattern.frequency,
                    pattern.confidence,
                    "high",
                    effort,
                )

                matches.append(
                    MatchResult(
                        pattern_id=pattern.id,
                        pattern_type=PatternType.BUG_FIX,
                        confidence=confidence,
                        score=score,
                        reason=self._explain_bug_fix_match(pattern, error_description),
                        impact=impact,
                        effort=effort,
                    )
                )

        # Sort by score (highest first)
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    def detect_code_smells(
        self,
        file_path: str,
        code_content: str,
        language: str = "python",
        limit: int = 10,
    ) -> list[MatchResult]:
        """Detect code smells in provided code.

        Analyzes code for anti-patterns and quality issues.
        """
        matches = []

        # Get all code smell patterns
        patterns = self.pattern_store.get_code_smell_patterns(limit=100)

        for pattern_dict in patterns:
            pattern = CodeSmellPattern(
                id=pattern_dict["id"],
                smell_type=pattern_dict["smell_type"],
                description=pattern_dict["description"],
                severity=pattern_dict.get("severity", "warning"),
                priority=pattern_dict.get("priority", 5),
            )

            # Check if code contains this smell
            confidence = self._detect_code_smell(code_content, pattern)

            if confidence > 0.3:  # Lower threshold for smells (common)
                impact = self._map_smell_severity_to_impact(pattern.severity)
                effort = "low"  # Code smell fixes are usually low effort

                score = self._calculate_pattern_score(
                    confidence,
                    1,  # Smells have consistent frequency
                    0.7,  # Fixing smells improves code quality
                    impact,
                    effort,
                )

                matches.append(
                    MatchResult(
                        pattern_id=pattern.id,
                        pattern_type=PatternType.CODE_SMELL,
                        confidence=confidence,
                        score=score,
                        reason=pattern.description,
                        impact=impact,
                        effort=effort,
                    )
                )

        # Sort by priority and score
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    def _match_refactoring_pattern(self, code_content: str, pattern: RefactoringPattern) -> float:
        """Calculate confidence that refactoring pattern applies to code.

        Returns 0-1 confidence score.
        """
        confidence = 0.0

        # Check for pattern indicators in code
        if pattern.before_pattern:
            # Simple substring matching (in production, use AST analysis)
            if pattern.before_pattern.lower() in code_content.lower():
                confidence += 0.4

        # Check method size (refactoring often applies to long methods)
        lines = code_content.split("\n")
        if len(lines) > 30:
            confidence += 0.3  # Long code → refactoring opportunity

        # Check code structure complexity (multiple nested blocks)
        indent_levels = [len(line) - len(line.lstrip()) for line in lines]
        if indent_levels and max(indent_levels) >= 16:  # 4+ levels of nesting
            confidence += 0.2

        return min(confidence, 1.0)

    def _match_bug_fix_pattern(self, error_description: str, pattern: BugFixPattern) -> float:
        """Calculate confidence that bug-fix pattern applies to error.

        Returns 0-1 confidence score.
        """
        confidence = 0.0
        error_lower = error_description.lower()

        # Check symptoms match
        for symptom in pattern.symptoms:
            if symptom.lower() in error_lower:
                confidence += 0.3  # Each matching symptom increases confidence

        # Check if pattern description matches
        if pattern.description.lower() in error_lower:
            confidence += 0.2

        return min(confidence, 1.0)

    def _detect_code_smell(self, code_content: str, pattern: CodeSmellPattern) -> float:
        """Detect if code contains specific code smell.

        Returns 0-1 confidence score.
        """
        confidence = 0.0
        code_lower = code_content.lower()

        # Check for smell keywords in detection rule
        if pattern.detection_rule:
            if pattern.detection_rule.lower() in code_lower:
                confidence += 0.5

        # Simple heuristics for common smells
        if "long_method" in pattern.smell_type:
            lines = len(code_content.split("\n"))
            if lines > 50:
                confidence += 0.5

        if "duplicate_code" in pattern.smell_type:
            # Count repeated patterns (simple heuristic)
            words = code_lower.split()
            if len(words) != len(set(words)):
                confidence += 0.3

        if "dead_code" in pattern.smell_type:
            # Check for unused variable patterns
            if "unused" in code_lower or "#" in code_content:
                confidence += 0.2

        if "magic_number" in pattern.smell_type:
            # Look for hardcoded numbers
            import re

            numbers = re.findall(r"\b\d+\b", code_content)
            if len(numbers) > 5:
                confidence += 0.3

        return min(confidence, 1.0)

    def _estimate_refactoring_impact(self, pattern: RefactoringPattern, code_content: str) -> str:
        """Estimate impact of applying refactoring pattern.

        Returns 'low', 'medium', or 'high'.
        """
        # Use pattern effectiveness as proxy for impact
        if pattern.effectiveness > 0.75:
            return "high"
        elif pattern.effectiveness > 0.5:
            return "medium"
        return "low"

    def _estimate_refactoring_effort(self, pattern: RefactoringPattern, code_content: str) -> str:
        """Estimate effort needed for refactoring.

        Returns 'low', 'medium', or 'high'.
        """
        lines = len(code_content.split("\n"))

        # Estimate based on code size and pattern type
        # Handle both enum and string values
        pattern_type = (
            pattern.refactoring_type.value
            if hasattr(pattern.refactoring_type, "value")
            else pattern.refactoring_type
        )

        if pattern_type in ("rename", "inline"):
            return "low"  # Simple patterns
        elif pattern_type in ("extract_method", "extract_class"):
            if lines < 30:
                return "low"
            elif lines < 100:
                return "medium"
            else:
                return "high"
        else:
            return "medium"

    def _estimate_bug_fix_effort(self, pattern: BugFixPattern) -> str:
        """Estimate effort needed to apply bug-fix pattern.

        Returns 'low', 'medium', or 'high'.
        """
        if pattern.time_to_fix_minutes:
            if pattern.time_to_fix_minutes < 15:
                return "low"
            elif pattern.time_to_fix_minutes < 60:
                return "medium"
            else:
                return "high"

        # Heuristic based on criticality
        if pattern.is_critical:
            return "high"

        return "medium"

    def _calculate_pattern_score(
        self,
        confidence: float,
        frequency: int,
        effectiveness: float,
        impact: str,
        effort: str,
    ) -> float:
        """Calculate composite pattern match score.

        Factors in:
        - Confidence in match (0-1)
        - Pattern frequency (how often seen)
        - Pattern effectiveness (how well it works)
        - Impact (how much improvement)
        - Effort (how much work required)

        Returns 0-100 score.
        """
        # Normalize frequency (cap at 100)
        freq_score = min(frequency, 100) / 100.0

        # Normalize impact
        impact_score = {"low": 0.3, "medium": 0.6, "high": 1.0}.get(impact, 0.5)

        # Effort penalty (lower effort = higher score)
        effort_score = {"low": 1.0, "medium": 0.7, "high": 0.4}.get(effort, 0.5)

        # Composite score: confidence × frequency × effectiveness × impact / effort
        score = confidence * freq_score * effectiveness * impact_score * effort_score * 100

        return score

    def _explain_refactoring_match(self, pattern: RefactoringPattern, code_content: str) -> str:
        """Generate explanation for refactoring pattern match."""
        lines = len(code_content.split("\n"))
        indent_levels = [len(line) - len(line.lstrip()) for line in code_content.split("\n")]
        max_indent = max(indent_levels) if indent_levels else 0

        reasons = []

        if pattern.before_pattern and pattern.before_pattern.lower() in code_content.lower():
            reasons.append(f"Code contains pattern: {pattern.before_pattern[:30]}")

        if lines > 30:
            reasons.append(f"Code is {lines} lines (threshold: 30)")

        if max_indent >= 16:
            nesting_levels = max_indent // 4
            reasons.append(f"Nested {nesting_levels} levels deep")

        return " • ".join(reasons) if reasons else pattern.description

    def _explain_bug_fix_match(self, pattern: BugFixPattern, error_description: str) -> str:
        """Generate explanation for bug-fix pattern match."""
        matched_symptoms = [s for s in pattern.symptoms if s.lower() in error_description.lower()]

        if matched_symptoms:
            return f"Symptoms match: {', '.join(matched_symptoms[:2])}"

        return pattern.description

    def _map_smell_severity_to_impact(self, severity: str) -> str:
        """Map code smell severity to impact level."""
        severity_map = {
            "info": "low",
            "warning": "medium",
            "critical": "high",
        }
        return severity_map.get(severity, "medium")
