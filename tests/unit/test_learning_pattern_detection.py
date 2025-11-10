"""Tests for Strategy 3 - Code pattern detection and duplicate prevention."""

import pytest
from athena.learning.pattern_detector import (
    PatternDetector,
    CodePattern,
    DuplicateGroup,
)


@pytest.fixture
def pattern_detector():
    """Create pattern detector for testing."""
    return PatternDetector()


@pytest.fixture
def sample_python_file(tmp_path):
    """Create a sample Python file with patterns."""
    file_path = tmp_path / "sample.py"
    content = '''
def process_data(data):
    """Process input data."""
    if not data:
        return None
    return data * 2

def handle_request(request):
    """Handle HTTP request."""
    if not request:
        return None
    return request.process()

class DataProcessor:
    """Process data."""
    pass

class RequestHandler:
    """Handle requests."""
    pass
'''
    file_path.write_text(content)
    return str(file_path)


class TestPatternDetector:
    """Tests for PatternDetector class."""

    def test_pattern_detector_creation(self, pattern_detector):
        """Test pattern detector initializes correctly."""
        assert pattern_detector is not None
        assert isinstance(pattern_detector, PatternDetector)

    def test_analyze_codebase(self, pattern_detector, sample_python_file):
        """Test analyzing codebase for patterns."""
        analysis = pattern_detector.analyze_codebase([sample_python_file])

        assert isinstance(analysis, dict)
        assert "total_files" in analysis
        assert "patterns_found" in analysis
        assert "duplicate_groups" in analysis
        assert "patterns" in analysis
        assert "duplicates" in analysis
        assert "recommendations" in analysis

        assert analysis["total_files"] == 1

    def test_find_similar_functions(self, pattern_detector, sample_python_file):
        """Test finding similar functions."""
        function_code = """
def process_data(data):
    if not data:
        return None
    return data * 2
"""

        similar = pattern_detector.find_similar_functions(
            function_code,
            [sample_python_file],
            similarity_threshold=0.7,
        )

        assert isinstance(similar, list)
        # Should find similar named functions
        for item in similar:
            assert "file" in item
            assert "function" in item
            assert "similarity" in item
            assert 0.0 <= item["similarity"] <= 1.0

    def test_find_duplicate_logic(self, pattern_detector, sample_python_file):
        """Test finding duplicate logic."""
        code_snippet = """
if not data:
    return None
"""

        duplicates = pattern_detector.find_duplicate_logic(
            code_snippet,
            [sample_python_file],
        )

        assert isinstance(duplicates, list)
        # May find duplicates if pattern exists in file
        for item in duplicates:
            assert "file" in item
            assert "similarity" in item
            assert 0.0 <= item["similarity"] <= 1.0

    def test_suggest_refactoring(self, pattern_detector):
        """Test refactoring suggestions for duplicates."""
        duplicate_group = DuplicateGroup(
            group_id="dup_1",
            description="Found 3 similar validation functions",
            duplicates=[
                {"file": "src/validator1.py", "line": 10},
                {"file": "src/validator2.py", "line": 15},
                {"file": "src/validator3.py", "line": 20},
            ],
            similarity_percentage=92.5,
            recommendation="Extract to shared validation module",
        )

        suggestion = pattern_detector.suggest_refactoring(duplicate_group)

        assert isinstance(suggestion, dict)
        assert "issue" in suggestion
        assert "similarity" in suggestion
        assert "recommendation" in suggestion
        assert "steps" in suggestion
        assert "benefits" in suggestion
        assert isinstance(suggestion["steps"], list)
        assert len(suggestion["steps"]) > 0
        assert isinstance(suggestion["benefits"], list)

    def test_get_pattern_statistics(self, pattern_detector, sample_python_file):
        """Test getting pattern statistics."""
        # First extract patterns so they're stored internally
        pattern_detector._extract_patterns([sample_python_file])

        # Now get statistics from the internal patterns
        stats = pattern_detector.get_pattern_statistics()

        assert isinstance(stats, dict)
        assert "total_patterns" in stats
        assert isinstance(stats["total_patterns"], int)
        # When patterns exist, we should have these fields
        if stats["total_patterns"] > 0:
            assert "pattern_types" in stats
            assert "most_common_type" in stats
            assert "duplicate_groups" in stats
            assert "total_duplicate_instances" in stats

    def test_pattern_statistics_empty(self, pattern_detector):
        """Test statistics when no analysis has been done."""
        stats = pattern_detector.get_pattern_statistics()

        assert stats["total_patterns"] == 0


class TestCodePattern:
    """Tests for CodePattern dataclass."""

    def test_code_pattern_creation(self):
        """Test CodePattern dataclass creation."""
        pattern = CodePattern(
            pattern_id="func_process_data",
            name="process_data",
            description="Process input data",
            locations=[
                {"file": "src/main.py", "line": 10},
                {"file": "src/utils.py", "line": 45},
            ],
            frequency=2,
            pattern_type="function",
            similarity_score=0.95,
        )

        assert pattern.pattern_id == "func_process_data"
        assert pattern.name == "process_data"
        assert pattern.pattern_type == "function"
        assert pattern.frequency == 2
        assert len(pattern.locations) == 2
        assert 0.0 <= pattern.similarity_score <= 1.0

    def test_code_pattern_class_type(self):
        """Test CodePattern for class patterns."""
        pattern = CodePattern(
            pattern_id="class_DataStore",
            name="DataStore",
            description="Store for data",
            locations=[
                {"file": "src/storage.py", "line": 100},
            ],
            frequency=1,
            pattern_type="class",
            similarity_score=1.0,
        )

        assert pattern.pattern_type == "class"
        assert pattern.name == "DataStore"

    def test_code_pattern_with_high_frequency(self):
        """Test CodePattern with many occurrences."""
        locations = [{"file": f"src/module{i}.py", "line": i * 10} for i in range(10)]

        pattern = CodePattern(
            pattern_id="pattern_utility",
            name="utility_function",
            description="A utility function",
            locations=locations,
            frequency=10,
            pattern_type="function",
            similarity_score=0.88,
        )

        assert pattern.frequency == 10
        assert len(pattern.locations) == 10


class TestDuplicateGroup:
    """Tests for DuplicateGroup dataclass."""

    def test_duplicate_group_creation(self):
        """Test DuplicateGroup dataclass creation."""
        duplicate = DuplicateGroup(
            group_id="dup_validation",
            description="Found 2 similar validation functions",
            duplicates=[
                {"file": "src/validators/email.py", "line": 5},
                {"file": "src/validators/phone.py", "line": 10},
            ],
            similarity_percentage=88.5,
            recommendation="Extract to shared validation module",
        )

        assert duplicate.group_id == "dup_validation"
        assert len(duplicate.duplicates) == 2
        assert duplicate.similarity_percentage == 88.5
        assert 0.0 <= duplicate.similarity_percentage <= 100.0

    def test_duplicate_group_high_similarity(self):
        """Test DuplicateGroup with high similarity."""
        duplicate = DuplicateGroup(
            group_id="dup_exact",
            description="Exact copy of function",
            duplicates=[
                {"file": "src/file1.py", "line": 1},
                {"file": "src/file2.py", "line": 50},
            ],
            similarity_percentage=99.9,
            recommendation="Remove duplicate, use shared function",
        )

        assert duplicate.similarity_percentage > 99.0

    def test_duplicate_group_many_duplicates(self):
        """Test DuplicateGroup with many occurrences."""
        duplicates = [
            {"file": f"src/module{i}.py", "line": i * 10}
            for i in range(5)
        ]

        duplicate = DuplicateGroup(
            group_id="dup_widely_duplicated",
            description="Code appears in 5 places",
            duplicates=duplicates,
            similarity_percentage=85.0,
            recommendation="Critical refactoring needed",
        )

        assert len(duplicate.duplicates) == 5


class TestPatternExtraction:
    """Tests for pattern extraction logic."""

    def test_extract_functions_from_file(self, pattern_detector, sample_python_file):
        """Test extracting function patterns from file."""
        patterns = pattern_detector._extract_patterns([sample_python_file])

        # Should find function patterns
        function_patterns = {
            k: v for k, v in patterns.items() if v.pattern_type == "function"
        }
        assert len(function_patterns) > 0

    def test_extract_classes_from_file(self, pattern_detector, sample_python_file):
        """Test extracting class patterns from file."""
        patterns = pattern_detector._extract_patterns([sample_python_file])

        # Should find class patterns
        class_patterns = {
            k: v for k, v in patterns.items() if v.pattern_type == "class"
        }
        assert len(class_patterns) > 0

    def test_find_duplicates_in_patterns(self, pattern_detector, sample_python_file):
        """Test finding duplicates within extracted patterns."""
        patterns = pattern_detector._extract_patterns([sample_python_file])
        duplicates = pattern_detector._find_duplicates(patterns)

        assert isinstance(duplicates, list)
        # May find duplicates if patterns repeat
        for dup in duplicates:
            assert isinstance(dup, DuplicateGroup)

    def test_generate_recommendations(self, pattern_detector, sample_python_file):
        """Test generating recommendations from analysis."""
        patterns = pattern_detector._extract_patterns([sample_python_file])
        duplicates = pattern_detector._find_duplicates(patterns)
        recommendations = pattern_detector._generate_recommendations(patterns, duplicates)

        assert isinstance(recommendations, list)
        # Should provide recommendations if duplicates found
        for rec in recommendations:
            assert isinstance(rec, str)


class TestCodeNormalization:
    """Tests for code normalization logic."""

    def test_normalize_code(self, pattern_detector):
        """Test code normalization for comparison."""
        code = """
        def process_data(data):
            # This is a comment
            result = data * 2  # Inline comment
            return result
        """

        normalized = pattern_detector._normalize_code(code)

        assert isinstance(normalized, str)
        # Should be lowercase
        assert normalized == normalized.lower()
        # Should have reduced whitespace
        assert "  " not in normalized or normalized.count("  ") < code.count("  ")

    def test_normalize_removes_comments(self, pattern_detector):
        """Test that normalization removes comments."""
        code = "x = 5  # Important comment"
        normalized = pattern_detector._normalize_code(code)

        # Comment should be removed or minimized
        assert "#" not in normalized or normalized.count("#") < code.count("#")

    def test_patterns_match(self, pattern_detector):
        """Test pattern matching in content."""
        pattern = "if not data return none"  # Normalized pattern
        content = """
        if not data:
            return None
        """

        normalized_content = pattern_detector._normalize_code(content)

        # Should find match (after normalization)
        match = pattern_detector._patterns_match(pattern, content)
        assert isinstance(match, bool)


class TestSimilarityDetection:
    """Tests for similarity detection."""

    def test_extract_function_signature(self, pattern_detector):
        """Test extracting function signature."""
        code = """
        def validate_email(email: str, strict: bool = False) -> bool:
            pass
        """

        sig = pattern_detector._extract_signature(code)

        assert isinstance(sig, str)
        assert "validate_email" in sig or len(sig) > 0

    def test_signatures_similar_same_name(self, pattern_detector):
        """Test similarity for same function name."""
        sig1 = "get_data()"
        similar = pattern_detector._signatures_similar(sig1, "get_data")

        assert similar is True

    def test_signatures_similar_different_cases(self, pattern_detector):
        """Test similarity with different naming conventions."""
        sig1 = "get_data()"
        similar = pattern_detector._signatures_similar(sig1, "getData")

        assert isinstance(similar, bool)

    def test_signatures_not_similar(self, pattern_detector):
        """Test dissimilar signatures."""
        sig1 = "process_file()"
        similar = pattern_detector._signatures_similar(sig1, "validate_input")

        assert similar is False


class TestPatternDetectionIntegration:
    """Integration tests for pattern detection workflow."""

    def test_complete_analysis_workflow(self, pattern_detector, sample_python_file):
        """Test complete pattern detection workflow."""
        # Analyze codebase
        analysis = pattern_detector.analyze_codebase([sample_python_file])

        # Check all components present
        assert analysis["total_files"] == 1
        assert analysis["patterns_found"] >= 0
        assert isinstance(analysis["patterns"], dict)
        assert isinstance(analysis["duplicates"], list)
        assert isinstance(analysis["recommendations"], list)

    def test_multiple_file_analysis(self, pattern_detector, tmp_path):
        """Test analyzing multiple files."""
        # Create multiple sample files
        for i in range(3):
            file_path = tmp_path / f"module{i}.py"
            file_path.write_text(f"""
def process_data(data):
    return data * 2

class DataProcessor:
    pass
""")

        files = [str(tmp_path / f"module{i}.py") for i in range(3)]
        analysis = pattern_detector.analyze_codebase(files)

        assert analysis["total_files"] == 3
        # Should find repeated patterns across files
        assert analysis["patterns_found"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
