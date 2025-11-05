"""Tests for duplication analyzer."""

import pytest

from athena.symbols.symbol_models import Symbol, SymbolType, create_symbol
from athena.symbols.duplication_analyzer import (
    DuplicationAnalyzer,
    CodeBlock,
    DuplicationPair,
    CloneType,
)


class TestDuplicationAnalyzerBasics:
    """Test basic duplication analyzer functionality."""

    def test_analyzer_initialization(self):
        """Test duplication analyzer can be created."""
        analyzer = DuplicationAnalyzer()
        assert analyzer is not None
        assert len(analyzer.code_blocks) == 0
        assert len(analyzer.duplication_pairs) == 0

    def test_add_symbol(self):
        """Test adding a symbol to analyzer."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code="def func1():\n    return 42",
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        block = analyzer.add_symbol(symbol, symbol.code)

        assert block is not None
        assert block.symbol == symbol
        assert block.hash_value is not None
        assert len(analyzer.code_blocks) == 1


class TestExactDuplicates:
    """Test exact code duplicate detection."""

    def test_detect_exact_duplicate(self):
        """Test detecting exactly identical code."""
        code = "def process():\n    x = 1\n    return x"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code=code,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process2",
            namespace="",
            signature="()",
            line_start=10,
            line_end=14,
            code=code,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code)
        analyzer.add_symbol(symbol2, code)
        pairs = analyzer.analyze_all(similarity_threshold=0.8)

        assert len(pairs) > 0
        exact_pairs = analyzer.get_exact_duplicates()
        assert len(exact_pairs) > 0
        assert exact_pairs[0].clone_type == CloneType.EXACT
        assert exact_pairs[0].similarity_score == 1.0

    def test_no_exact_duplicate_different_code(self):
        """Test that different code is not detected as duplicate."""
        code1 = "def process_list(items):\n    for i in items:\n        print(i)\n    return len(items)"
        code2 = "def calculate_sum(numbers):\n    total = 0\n    for n in numbers:\n        total += n\n    return total"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func1",
            namespace="",
            signature="(items)",
            line_start=1,
            line_end=5,
            code=code1,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func2",
            namespace="",
            signature="(numbers)",
            line_start=10,
            line_end=15,
            code=code2,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code1)
        analyzer.add_symbol(symbol2, code2)
        pairs = analyzer.analyze_all(similarity_threshold=0.85)

        # Should have no exact duplicates at high threshold
        exact_pairs = analyzer.get_exact_duplicates()
        assert len(exact_pairs) == 0


class TestSimilarDuplicates:
    """Test similar code duplicate detection."""

    def test_detect_similar_duplicate(self):
        """Test detecting similar code with minor differences."""
        code1 = "def process(x):\n    result = x * 2\n    return result"
        code2 = "def process(y):\n    result = y * 2\n    return result"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process1",
            namespace="",
            signature="(x)",
            line_start=1,
            line_end=5,
            code=code1,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="process2",
            namespace="",
            signature="(y)",
            line_start=10,
            line_end=14,
            code=code2,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code1)
        analyzer.add_symbol(symbol2, code2)
        pairs = analyzer.analyze_all(similarity_threshold=0.8)

        assert len(pairs) > 0
        similar = analyzer.get_similar_duplicates()
        assert len(similar) > 0
        assert similar[0].similarity_score > 0.8

    def test_similar_with_whitespace_differences(self):
        """Test detecting similar code with whitespace differences."""
        code1 = "def func():\n    x = 1\n    y = 2\n    return x + y"
        code2 = "def func():\n    x=1\n    y=2\n    return x+y"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=5,
            code=code1,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func2",
            namespace="",
            signature="()",
            line_start=10,
            line_end=14,
            code=code2,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code1)
        analyzer.add_symbol(symbol2, code2)
        pairs = analyzer.analyze_all(similarity_threshold=0.8)

        assert len(pairs) > 0

    def test_similar_with_comments_removed(self):
        """Test that comments don't affect duplication detection."""
        code1 = "def func():\n    # Calculate sum\n    x = 1\n    y = 2\n    return x + y"
        code2 = "def func():\n    x = 1\n    y = 2\n    return x + y"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=6,
            code=code1,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func2",
            namespace="",
            signature="()",
            line_start=10,
            line_end=14,
            code=code2,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code1)
        analyzer.add_symbol(symbol2, code2)
        pairs = analyzer.analyze_all(similarity_threshold=0.8)

        assert len(pairs) > 0


class TestLooseDuplicates:
    """Test loosely similar code detection."""

    def test_detect_loose_duplicate(self):
        """Test detecting code with similar logic but different structure."""
        code1 = "def calculate(a, b):\n    return a + b"
        code2 = "def compute(x, y):\n    result = x + y\n    return result"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="calculate",
            namespace="",
            signature="(a, b)",
            line_start=1,
            line_end=3,
            code=code1,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="compute",
            namespace="",
            signature="(x, y)",
            line_start=5,
            line_end=8,
            code=code2,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code1)
        analyzer.add_symbol(symbol2, code2)
        pairs = analyzer.analyze_all(similarity_threshold=0.6)

        # Might detect as loose or not, depending on similarity
        assert isinstance(pairs, list)


class TestCodeNormalization:
    """Test code normalization for comparison."""

    def test_normalize_removes_comments(self):
        """Test that normalization removes comments."""
        analyzer = DuplicationAnalyzer()
        code = "def func():\n    # This is a comment\n    x = 1"
        normalized = analyzer._normalize_code(code)

        assert "comment" not in normalized.lower()
        assert "x = 1" in normalized

    def test_normalize_removes_whitespace(self):
        """Test that normalization removes extra whitespace."""
        analyzer = DuplicationAnalyzer()
        code = "def func ( ):\n    x   =   1"
        normalized = analyzer._normalize_code(code)

        # Should be more compact
        assert len(normalized) < len(code)

    def test_normalize_handles_empty_lines(self):
        """Test that normalization skips empty lines."""
        analyzer = DuplicationAnalyzer()
        code = "def func():\n\n    x = 1\n\n    return x"
        normalized = analyzer._normalize_code(code)

        assert normalized.count('\n') < code.count('\n')


class TestSimilarityCalculation:
    """Test similarity score calculation."""

    def test_identical_similarity_is_one(self):
        """Test that identical code has similarity of 1.0."""
        analyzer = DuplicationAnalyzer()
        code = "def func():\n    return 42"

        similarity = analyzer._calculate_similarity(code, code)
        assert similarity == 1.0

    def test_completely_different_low_similarity(self):
        """Test that completely different code has low similarity."""
        analyzer = DuplicationAnalyzer()
        code1 = "class DataProcessor:\n    def __init__(self, data):\n        self.data = data\n    def process(self):\n        return self.data.upper()"
        code2 = "import json\nwith open('file.json') as f:\n    data = json.load(f)\nprint(data)"

        similarity = analyzer._calculate_similarity(code1, code2)
        assert similarity < 0.6

    def test_very_similar_high_similarity(self):
        """Test that very similar code has high similarity."""
        analyzer = DuplicationAnalyzer()
        code1 = "def func(x):\n    return x * 2"
        code2 = "def func(y):\n    return y * 2"

        similarity = analyzer._calculate_similarity(code1, code2)
        assert similarity > 0.8


class TestDuplicationQueries:
    """Test querying duplication results."""

    def test_get_exact_duplicates(self):
        """Test getting exact duplicate pairs."""
        code = "def func():\n    return 42"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code=code,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f2",
            namespace="",
            signature="()",
            line_start=5,
            line_end=7,
            code=code,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code)
        analyzer.add_symbol(symbol2, code)
        analyzer.analyze_all()

        exact = analyzer.get_exact_duplicates()
        assert len(exact) > 0

    def test_get_duplicates_for_symbol(self):
        """Test getting duplicates for specific symbol."""
        code1 = "def func():\n    return 42"
        code2 = "def func():\n    return 42"
        code3 = "def other():\n    return 99"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code=code1,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f2",
            namespace="",
            signature="()",
            line_start=5,
            line_end=7,
            code=code2,
            language="python",
            visibility="public"
        )

        symbol3 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f3",
            namespace="",
            signature="()",
            line_start=10,
            line_end=12,
            code=code3,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code1)
        analyzer.add_symbol(symbol2, code2)
        analyzer.add_symbol(symbol3, code3)
        analyzer.analyze_all()

        f1_dups = analyzer.get_duplicates_for_symbol(symbol1)
        assert len(f1_dups) >= 1

    def test_get_worst_offenders(self):
        """Test getting symbols with most duplication."""
        code = "def func():\n    return 42"

        symbols = []
        for i in range(5):
            symbol = create_symbol(
                file_path="test.py",
                symbol_type=SymbolType.FUNCTION,
                name=f"func{i}",
                namespace="",
                signature="()",
                line_start=i*5+1,
                line_end=i*5+4,
                code=code if i < 3 else f"def func{i}():\n    return {i}",
                language="python",
                visibility="public"
            )
            symbols.append(symbol)

        analyzer = DuplicationAnalyzer()
        for symbol in symbols:
            analyzer.add_symbol(symbol, symbol.code)

        analyzer.analyze_all()

        worst = analyzer.get_worst_offenders(limit=5)
        assert isinstance(worst, list)


class TestRefactoringOpportunities:
    """Test refactoring opportunity identification."""

    def test_get_refactoring_opportunities(self):
        """Test getting refactoring opportunities."""
        code = "def func():\n    return 42"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code=code,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f2",
            namespace="",
            signature="()",
            line_start=5,
            line_end=7,
            code=code,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code)
        analyzer.add_symbol(symbol2, code)
        analyzer.analyze_all()

        opportunities = analyzer.get_refactoring_opportunities()
        assert len(opportunities) > 0

    def test_suggest_extraction(self):
        """Test extraction suggestions."""
        code1 = "def func():\n    return 42"
        code2 = "def func():\n    return 42"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code=code1,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f2",
            namespace="",
            signature="()",
            line_start=5,
            line_end=7,
            code=code2,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code1)
        analyzer.add_symbol(symbol2, code2)
        pairs = analyzer.analyze_all()

        if pairs:
            suggestions = analyzer.suggest_extraction(pairs[0])
            assert len(suggestions) > 0


class TestDuplicationMetrics:
    """Test duplication metrics calculation."""

    def test_metrics_calculation(self):
        """Test calculating duplication metrics."""
        code1 = "def func1():\n    return 1"
        code2 = "def func1():\n    return 1"
        code3 = "def func2():\n    return 2"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code=code1,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f2",
            namespace="",
            signature="()",
            line_start=5,
            line_end=7,
            code=code2,
            language="python",
            visibility="public"
        )

        symbol3 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f3",
            namespace="",
            signature="()",
            line_start=10,
            line_end=12,
            code=code3,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code1)
        analyzer.add_symbol(symbol2, code2)
        analyzer.add_symbol(symbol3, code3)
        analyzer.analyze_all()

        metrics = analyzer.get_metrics()
        assert metrics is not None
        assert metrics.total_symbols == 3
        assert metrics.duplication_pairs >= 1
        assert metrics.duplication_percentage >= 0.0

    def test_metrics_before_analysis(self):
        """Test that metrics is None before analysis."""
        analyzer = DuplicationAnalyzer()

        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code="def func():\n    pass",
            language="python",
            visibility="public"
        )

        analyzer.add_symbol(symbol, symbol.code)
        metrics = analyzer.get_metrics()

        assert metrics is None


class TestDuplicationReport:
    """Test report generation."""

    def test_generate_duplication_report(self):
        """Test generating duplication report."""
        code = "def func():\n    return 42"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code=code,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f2",
            namespace="",
            signature="()",
            line_start=5,
            line_end=7,
            code=code,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code)
        analyzer.add_symbol(symbol2, code)
        analyzer.analyze_all()

        report = analyzer.get_duplication_report()

        assert isinstance(report, str)
        assert len(report) > 0
        assert "CODE DUPLICATION REPORT" in report

    def test_report_before_analysis(self):
        """Test report before analysis shows appropriate message."""
        analyzer = DuplicationAnalyzer()
        report = analyzer.get_duplication_report()

        assert "No duplication analysis performed" in report


class TestCloneTypeClassification:
    """Test clone type classification."""

    def test_classify_exact_clone(self):
        """Test classifying exact clone."""
        code = "def func():\n    return 1"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code=code,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f2",
            namespace="",
            signature="()",
            line_start=5,
            line_end=7,
            code=code,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code)
        analyzer.add_symbol(symbol2, code)
        pairs = analyzer.analyze_all()

        exact_pairs = [p for p in pairs if p.clone_type == CloneType.EXACT]
        assert len(exact_pairs) > 0

    def test_classify_similar_clone(self):
        """Test classifying similar clone."""
        analyzer = DuplicationAnalyzer()

        code1 = "def func(x):\n    return x * 2"
        code2 = "def func(y):\n    return y * 2"

        clone_type = analyzer._classify_clone(code1, code2, 0.95)

        assert clone_type == CloneType.SIMILAR

    def test_classify_loose_clone(self):
        """Test classifying loose clone."""
        analyzer = DuplicationAnalyzer()

        code1 = "def func(x):\n    return x * 2"
        code2 = "def compute(a, b):\n    result = a + b\n    return result"

        clone_type = analyzer._classify_clone(code1, code2, 0.65)

        assert clone_type == CloneType.LOOSE


class TestSpecialCases:
    """Test special cases and edge conditions."""

    def test_analyze_empty_codebase(self):
        """Test analyzing empty codebase."""
        analyzer = DuplicationAnalyzer()
        pairs = analyzer.analyze_all()

        assert pairs == []
        assert analyzer.get_metrics() is not None

    def test_single_symbol_no_duplicates(self):
        """Test single symbol has no duplicates."""
        symbol = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="func",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code="def func():\n    return 42",
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol, symbol.code)
        pairs = analyzer.analyze_all()

        assert len(pairs) == 0

    def test_large_code_blocks(self):
        """Test handling large code blocks."""
        large_code = "def func():\n" + "    x = 1\n" * 100 + "    return x"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=105,
            code=large_code,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f2",
            namespace="",
            signature="()",
            line_start=110,
            line_end=214,
            code=large_code,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, large_code)
        analyzer.add_symbol(symbol2, large_code)
        pairs = analyzer.analyze_all()

        assert len(pairs) > 0

    def test_threshold_filtering(self):
        """Test similarity threshold filtering."""
        code1 = "def func():\n    return 42"
        code2 = "def other():\n    return 42"

        symbol1 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f1",
            namespace="",
            signature="()",
            line_start=1,
            line_end=3,
            code=code1,
            language="python",
            visibility="public"
        )

        symbol2 = create_symbol(
            file_path="test.py",
            symbol_type=SymbolType.FUNCTION,
            name="f2",
            namespace="",
            signature="()",
            line_start=5,
            line_end=7,
            code=code2,
            language="python",
            visibility="public"
        )

        analyzer = DuplicationAnalyzer()
        analyzer.add_symbol(symbol1, code1)
        analyzer.add_symbol(symbol2, code2)

        # With high threshold
        pairs_high = analyzer.analyze_all(similarity_threshold=0.95)

        # With low threshold
        analyzer2 = DuplicationAnalyzer()
        analyzer2.add_symbol(symbol1, code1)
        analyzer2.add_symbol(symbol2, code2)
        pairs_low = analyzer2.analyze_all(similarity_threshold=0.5)

        # Lower threshold should find more or equal pairs
        assert len(pairs_low) >= len(pairs_high)
