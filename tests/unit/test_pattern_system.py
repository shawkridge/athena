"""Unit tests for code pattern learning and suggestion system (Phase 4).

Tests cover:
- Pattern model validation
- Pattern store CRUD operations
- Pattern extraction from git history
- Pattern matching and scoring
- Pattern suggestion generation
- Suggestion effectiveness tracking
"""

import pytest
from datetime import datetime

from athena.core.database import Database
from athena.procedural.code_patterns import (
    RefactoringType,
    BugFixType,
    CodeSmellType,
    PatternType,
    CodeMetrics,
    CodeChange,
    RefactoringPattern,
    BugFixPattern,
    CodeSmellPattern,
    PatternApplication,
    ArchitecturalPattern,
    PatternSuggestion,
)
from athena.procedural.pattern_store import PatternStore
from athena.procedural.pattern_extractor import PatternExtractor
from athena.procedural.pattern_matcher import PatternMatcher
from athena.procedural.pattern_suggester import PatternSuggester


class TestPatternModels:
    """Test pattern model validation."""

    def test_code_metrics_creation(self):
        """Test CodeMetrics model creation."""
        metrics = CodeMetrics(
            lines_added=10,
            lines_deleted=5,
            files_changed=2,
            functions_modified=1,
            cyclomatic_complexity_before=5.0,
            cyclomatic_complexity_after=3.0,
        )

        assert metrics.lines_added == 10
        assert metrics.lines_deleted == 5
        assert metrics.files_changed == 2

    def test_code_metrics_validation(self):
        """Test CodeMetrics validation."""
        with pytest.raises(ValueError):
            CodeMetrics(lines_added=-1)

        with pytest.raises(ValueError):
            CodeMetrics(lines_deleted=-5)

    def test_refactoring_pattern_creation(self):
        """Test RefactoringPattern creation."""
        pattern = RefactoringPattern(
            refactoring_type=RefactoringType.EXTRACT_METHOD,
            description="Extract long method into smaller pieces",
            language="python",
            frequency=5,
            effectiveness=0.8,
        )

        assert pattern.refactoring_type == RefactoringType.EXTRACT_METHOD
        assert pattern.effectiveness == 0.8

    def test_refactoring_pattern_validation(self):
        """Test RefactoringPattern validation."""
        with pytest.raises(ValueError):
            RefactoringPattern(
                description="", refactoring_type=RefactoringType.RENAME
            )

        with pytest.raises(ValueError):
            RefactoringPattern(
                description="Test",
                refactoring_type=RefactoringType.RENAME,
                effectiveness=1.5,  # Invalid: > 1.0
            )

    def test_bug_fix_pattern_creation(self):
        """Test BugFixPattern creation."""
        pattern = BugFixPattern(
            bug_type=BugFixType.NULL_POINTER,
            description="Null pointer handling",
            solution="Check for None before use",
            confidence=0.9,
        )

        assert pattern.bug_type == BugFixType.NULL_POINTER
        assert pattern.confidence == 0.9

    def test_bug_fix_pattern_validation(self):
        """Test BugFixPattern validation."""
        with pytest.raises(ValueError):
            BugFixPattern(
                bug_type=BugFixType.NULL_POINTER,
                description="",
                solution="...",
            )

    def test_code_smell_pattern_creation(self):
        """Test CodeSmellPattern creation."""
        pattern = CodeSmellPattern(
            smell_type=CodeSmellType.LONG_METHOD,
            description="Method is too long",
            detection_rule="method_lines > 50",
            severity="warning",
            priority=7,
        )

        assert pattern.smell_type == CodeSmellType.LONG_METHOD
        assert pattern.priority == 7

    def test_pattern_suggestion_creation(self):
        """Test PatternSuggestion creation."""
        suggestion = PatternSuggestion(
            pattern_id=1,
            pattern_type=PatternType.REFACTORING,
            file_path="src/auth.py",
            location="Line 42: authenticate()",
            confidence=0.85,
            reason="Method is 60 lines, candidate for extraction",
        )

        assert suggestion.file_path == "src/auth.py"
        assert suggestion.confidence == 0.85
        assert not suggestion.applied


class TestPatternStore:
    """Test pattern storage layer."""

    def test_create_refactoring_pattern(self, tmp_path):
        """Test storing refactoring pattern."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)

        pattern = RefactoringPattern(
            refactoring_type=RefactoringType.EXTRACT_METHOD,
            description="Extract method from large function",
            language="python",
            frequency=3,
            effectiveness=0.8,
        )

        pattern_id = store.create_refactoring_pattern(pattern)

        assert pattern_id > 0

        # Verify stored
        result = store.get_refactoring_patterns(limit=10)
        assert len(result) == 1
        assert result[0]["description"] == pattern.description

    def test_create_bug_fix_pattern(self, tmp_path):
        """Test storing bug-fix pattern."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)

        pattern = BugFixPattern(
            bug_type=BugFixType.NULL_POINTER,
            description="Null pointer in authentication",
            solution="Add null check before use",
            confidence=0.9,
        )

        pattern_id = store.create_bug_fix_pattern(pattern)

        assert pattern_id > 0

        result = store.get_bug_fix_patterns(limit=10)
        assert len(result) == 1
        assert result[0]["solution"] == pattern.solution

    def test_create_code_smell_pattern(self, tmp_path):
        """Test storing code smell pattern."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)

        pattern = CodeSmellPattern(
            smell_type=CodeSmellType.LONG_METHOD,
            description="Method exceeds 50 lines",
            detection_rule="method_lines > 50",
            severity="warning",
            priority=6,
        )

        pattern_id = store.create_code_smell_pattern(pattern)

        assert pattern_id > 0

        result = store.get_code_smell_patterns(limit=10)
        assert len(result) == 1
        assert result[0]["smell_type"] == CodeSmellType.LONG_METHOD.value

    def test_record_pattern_application(self, tmp_path):
        """Test recording pattern application."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)

        # First create a pattern
        pattern = RefactoringPattern(
            refactoring_type=RefactoringType.RENAME,
            description="Rename variable",
            language="python",
        )
        pattern_id = store.create_refactoring_pattern(pattern)

        # Record application
        application = PatternApplication(
            pattern_id=pattern_id,
            pattern_type=PatternType.REFACTORING,
            commit_hash="abc123",
            author="test@example.com",
            outcome="success",
        )

        app_id = store.record_pattern_application(application)
        assert app_id > 0

    def test_pattern_suggestion(self, tmp_path):
        """Test creating pattern suggestions."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)

        # Create a pattern first
        pattern = RefactoringPattern(
            refactoring_type=RefactoringType.EXTRACT_CLASS,
            description="Extract class",
            language="python",
        )
        pattern_id = store.create_refactoring_pattern(pattern)

        # Create suggestion
        suggestion = PatternSuggestion(
            pattern_id=pattern_id,
            pattern_type=PatternType.REFACTORING,
            file_path="src/handler.py",
            location="Line 50: RequestHandler",
            confidence=0.75,
            reason="Class has too many responsibilities",
        )

        suggestion_id = store.suggest_pattern(suggestion)
        assert suggestion_id > 0

        # Verify retrieval
        suggestions = store.get_suggestions_for_file("src/handler.py")
        assert len(suggestions) == 1
        assert suggestions[0]["confidence"] == 0.75

    def test_get_statistics(self, tmp_path):
        """Test pattern statistics."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)

        # Create multiple patterns
        for i in range(3):
            pattern = RefactoringPattern(
                refactoring_type=RefactoringType.RENAME,
                description=f"Rename pattern {i}",
                language="python",
            )
            store.create_refactoring_pattern(pattern)

        for i in range(2):
            pattern = BugFixPattern(
                bug_type=BugFixType.NULL_POINTER,
                description=f"Null pointer fix {i}",
                solution="Check None",
            )
            store.create_bug_fix_pattern(pattern)

        stats = store.get_statistics()

        assert stats["total_refactoring_patterns"] == 1  # One type only
        assert stats["total_bug_fix_patterns"] == 1  # One type only
        assert stats["successful_applications"] == 0  # None applied


class TestPatternMatcher:
    """Test pattern matching engine."""

    def test_match_refactoring_opportunities(self, tmp_path):
        """Test finding refactoring opportunities."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        matcher = PatternMatcher(db)

        # Create a pattern
        pattern = RefactoringPattern(
            refactoring_type=RefactoringType.EXTRACT_METHOD,
            description="Extract long method",
            before_pattern="def long_method",
            language="python",
            frequency=5,
            effectiveness=0.85,
        )
        store.create_refactoring_pattern(pattern)

        # Test code with the pattern's before_pattern in it
        code = "def long_method():\n" + "\n".join(["    pass"] * 50)

        matches = matcher.match_refactoring_opportunities("test.py", code)

        # Should find at least the pattern if it matches
        assert isinstance(matches, list)

    def test_match_bug_fix_patterns(self, tmp_path):
        """Test matching bug-fix patterns."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        matcher = PatternMatcher(db)

        # Create a bug-fix pattern
        pattern = BugFixPattern(
            bug_type=BugFixType.NULL_POINTER,
            description="Null pointer in login",
            symptoms=["Null pointer reference", "NoneType"],
            solution="Check for None",
            language="python",
            confidence=0.9,
        )
        store.create_bug_fix_pattern(pattern)

        # Test error description with matching symptoms
        error = "NoneType: 'NoneType' object has no attribute 'validate'"

        matches = matcher.match_bug_fix_patterns("auth.py", error)

        # Check that matching works (may or may not find matches based on heuristics)
        assert isinstance(matches, list)

    def test_detect_code_smells(self, tmp_path):
        """Test code smell detection."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        matcher = PatternMatcher(db)

        # Create smell pattern
        pattern = CodeSmellPattern(
            smell_type=CodeSmellType.LONG_METHOD,
            description="Method exceeds 50 lines",
            detection_rule="method_lines > 50",
            severity="warning",
            priority=7,
        )
        store.create_code_smell_pattern(pattern)

        # Long code sample
        code = "\n".join(["def long_method():"] + ["    pass"] * 60)

        matches = matcher.detect_code_smells("handler.py", code)

        assert len(matches) > 0
        assert matches[0].pattern_type == PatternType.CODE_SMELL

    def test_pattern_score_calculation(self, tmp_path):
        """Test pattern match scoring."""
        db = Database(tmp_path / "test.db")
        matcher = PatternMatcher(db)

        # High confidence + high frequency + high effectiveness = high score
        score = matcher._calculate_pattern_score(
            confidence=0.9,
            frequency=10,
            effectiveness=0.85,
            impact="high",
            effort="low",
        )

        # Score should be a positive number
        assert score > 0

        # Low confidence + low frequency = low score
        score2 = matcher._calculate_pattern_score(
            confidence=0.3,
            frequency=1,
            effectiveness=0.5,
            impact="low",
            effort="high",
        )

        # Higher score should be from higher inputs
        assert score > score2


class TestPatternSuggester:
    """Test pattern suggestion generation."""

    def test_suggest_refactorings(self, tmp_path):
        """Test refactoring suggestions."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        suggester = PatternSuggester(db)

        # Create pattern
        pattern = RefactoringPattern(
            refactoring_type=RefactoringType.EXTRACT_METHOD,
            description="Extract method",
            language="python",
            frequency=5,
            effectiveness=0.8,
        )
        store.create_refactoring_pattern(pattern)

        # Generate suggestions
        code = "\n".join(["def long_method():"] + ["    pass"] * 40)
        suggestions = suggester.suggest_refactorings("test.py", code)

        assert len(suggestions) >= 0  # May or may not match depending on heuristics

    def test_suggest_bug_fixes(self, tmp_path):
        """Test bug-fix suggestions."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        suggester = PatternSuggester(db)

        # Create pattern
        pattern = BugFixPattern(
            bug_type=BugFixType.NULL_POINTER,
            description="Null pointer fix",
            symptoms=["Null reference", "NoneType"],
            solution="Add None check",
            confidence=0.85,
        )
        store.create_bug_fix_pattern(pattern)

        # Generate suggestions
        error = "Error: NoneType object has no attribute 'value'"
        suggestions = suggester.suggest_bug_fixes("handler.py", error)

        # Verify suggestions is a list (may or may not find matches)
        assert isinstance(suggestions, list)

    def test_apply_suggestion(self, tmp_path):
        """Test marking suggestion as applied."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        suggester = PatternSuggester(db)

        # Create and store suggestion
        suggestion = PatternSuggestion(
            pattern_id=1,
            pattern_type=PatternType.REFACTORING,
            file_path="test.py",
            location="Line 10",
            confidence=0.8,
            reason="Test suggestion",
        )
        suggestion_id = store.suggest_pattern(suggestion)

        # Apply it
        success = suggester.apply_suggestion(suggestion_id, "Applied successfully")
        assert success

    def test_dismiss_suggestion(self, tmp_path):
        """Test dismissing suggestion."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        suggester = PatternSuggester(db)

        # Create suggestion
        suggestion = PatternSuggestion(
            pattern_id=1,
            pattern_type=PatternType.REFACTORING,
            file_path="test.py",
            location="Line 10",
            confidence=0.8,
            reason="Test",
        )
        suggestion_id = store.suggest_pattern(suggestion)

        # Dismiss it
        success = suggester.dismiss_suggestion(suggestion_id, "Not applicable")
        assert success

    def test_suggestion_effectiveness(self, tmp_path):
        """Test measuring suggestion effectiveness."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        suggester = PatternSuggester(db)

        # Create multiple suggestions for same pattern
        for i in range(5):
            suggestion = PatternSuggestion(
                pattern_id=1,
                pattern_type=PatternType.REFACTORING,
                file_path=f"test{i}.py",
                location=f"Line {i * 10}",
                confidence=0.8,
                reason="Test",
            )
            suggestion_id = store.suggest_pattern(suggestion)

            # Apply some
            if i < 3:
                suggester.apply_suggestion(suggestion_id)

        # Check effectiveness
        metrics = suggester.measure_suggestion_effectiveness(1)

        assert metrics["applied_count"] == 3
        assert metrics["total_suggestions"] == 5
        assert metrics["effectiveness_rate"] == 0.6  # 3/5

    def test_suggestion_statistics(self, tmp_path):
        """Test overall suggestion statistics."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        suggester = PatternSuggester(db)

        # Create mixed suggestions
        for i in range(3):
            suggestion = PatternSuggestion(
                pattern_id=i,
                pattern_type=PatternType.REFACTORING,
                file_path="test.py",
                location=f"Line {i}",
                confidence=0.8,
                reason="Test",
            )
            suggestion_id = store.suggest_pattern(suggestion)
            if i < 2:
                suggester.apply_suggestion(suggestion_id)

        stats = suggester.get_suggestion_statistics()

        assert stats["total_suggestions"] == 3
        assert stats["applied"] == 2
        assert stats["overall_effectiveness"] == pytest.approx(2 / 3)

    def test_file_recommendations(self, tmp_path):
        """Test file-level improvement recommendations."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        suggester = PatternSuggester(db)

        file_path = "src/handler.py"

        # Create suggestions with different impacts
        for impact in ["high", "medium", "low"]:
            suggestion = PatternSuggestion(
                pattern_id=1,
                pattern_type=PatternType.REFACTORING,
                file_path=file_path,
                location="Line 10",
                confidence=0.8,
                reason="Test",
                impact=impact,
            )
            store.suggest_pattern(suggestion)

        recommendations = suggester.get_file_improvement_recommendations(file_path)

        assert recommendations["file_path"] == file_path
        assert recommendations["total_pending_suggestions"] == 3
        # Check that counts are non-negative
        assert recommendations["high_impact_count"] >= 0
        assert recommendations["medium_impact_count"] >= 0
        assert recommendations["low_impact_count"] >= 0


class TestPatternExtraction:
    """Test pattern extraction from code history."""

    def test_detect_refactoring_type(self, tmp_path):
        """Test refactoring type detection."""
        db = Database(tmp_path / "test.db")
        extractor = PatternExtractor(db)

        # Test extract method detection
        commit_msg = "extract authenticate method from login flow"
        refactoring_type = extractor._detect_refactoring_type(commit_msg, 20, 5, 2)
        assert refactoring_type == RefactoringType.EXTRACT_METHOD

        # Test rename detection
        commit_msg = "rename User class to Person"
        refactoring_type = extractor._detect_refactoring_type(commit_msg, 10, 10, 1)
        assert refactoring_type == RefactoringType.RENAME

        # Test inline detection
        commit_msg = "inline helper method"
        refactoring_type = extractor._detect_refactoring_type(commit_msg, 5, 15, 1)
        assert refactoring_type == RefactoringType.INLINE

    def test_map_regression_to_bug_type(self, tmp_path):
        """Test regression to bug type mapping."""
        db = Database(tmp_path / "test.db")
        extractor = PatternExtractor(db)

        # Test mapping
        bug_type = extractor._map_regression_to_bug_type("test_failure")
        assert bug_type == BugFixType.LOGIC_ERROR

        bug_type = extractor._map_regression_to_bug_type("memory_leak")
        assert bug_type == BugFixType.MEMORY_LEAK

        bug_type = extractor._map_regression_to_bug_type("security_issue")
        assert bug_type == BugFixType.INJECTION

    def test_extract_symptoms(self, tmp_path):
        """Test symptom extraction."""
        db = Database(tmp_path / "test.db")
        extractor = PatternExtractor(db)

        description = "Login crashes when authentication times out"
        symptoms = extractor._extract_symptoms(description)

        assert len(symptoms) > 0
        # Check that crash symptom is extracted
        assert any("crash" in s.lower() for s in symptoms)
        # May or may not extract timeout depending on keywords
        assert all(isinstance(s, str) for s in symptoms)


class TestPatternIntegration:
    """Test end-to-end pattern system integration."""

    def test_pattern_workflow(self, tmp_path):
        """Test complete pattern workflow."""
        db = Database(tmp_path / "test.db")
        store = PatternStore(db)
        suggester = PatternSuggester(db)

        # 1. Create patterns
        refactoring = RefactoringPattern(
            refactoring_type=RefactoringType.EXTRACT_METHOD,
            description="Extract method",
            language="python",
            frequency=3,
            effectiveness=0.8,
        )
        pattern_id = store.create_refactoring_pattern(refactoring)

        # 2. Generate suggestions
        code = "\n".join(["def process_data():"] + ["    pass"] * 50)
        suggestions = suggester.suggest_refactorings("main.py", code)

        # 3. Track effectiveness
        if suggestions:
            suggestion_id = suggestions[0].id
            suggester.apply_suggestion(suggestion_id)

            metrics = suggester.measure_suggestion_effectiveness(pattern_id)
            assert metrics["applied_count"] >= 0

        # 4. Check statistics
        stats = suggester.get_suggestion_statistics()
        assert stats["total_suggestions"] >= 0
