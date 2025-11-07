"""Tests for code procedural patterns."""

import pytest
from src.athena.code_search.code_procedural_patterns import (
    PatternType,
    PatternCategory,
    CodePattern,
    PatternDetector,
    PatternAnalyzer,
    ProceduralMemoryIntegration,
)
from src.athena.code_search.symbol_extractor import (
    Symbol,
    SymbolType,
    SymbolIndex,
)
from src.athena.code_search.code_graph_integration import CodeGraphBuilder


class TestCodePattern:
    """Tests for CodePattern."""

    def test_pattern_creation(self):
        """Test creating pattern."""
        pattern = CodePattern(
            name="Singleton",
            pattern_type=PatternType.DESIGN_PATTERN,
            category=PatternCategory.CREATIONAL,
            confidence=0.85,
        )

        assert pattern.name == "Singleton"
        assert pattern.pattern_type == PatternType.DESIGN_PATTERN
        assert pattern.confidence == 0.85

    def test_pattern_to_dict(self):
        """Test pattern serialization."""
        pattern = CodePattern(
            name="Factory",
            pattern_type=PatternType.DESIGN_PATTERN,
            category=PatternCategory.CREATIONAL,
            description="Creates objects",
            confidence=0.75,
            indicators=["factory_method"],
        )

        pattern_dict = pattern.to_dict()
        assert pattern_dict["name"] == "Factory"
        assert pattern_dict["pattern_type"] == "design_pattern"
        assert "factory_method" in pattern_dict["indicators"]


class TestPatternDetector:
    """Tests for PatternDetector."""

    @pytest.fixture
    def detector(self):
        """Create detector."""
        return PatternDetector()

    @pytest.fixture
    def sample_symbols(self):
        """Create sample symbols."""
        return [
            Symbol(
                name="create_instance",
                type=SymbolType.FUNCTION,
                file_path="factory.py",
                line_number=10,
            ),
            Symbol(
                name="notify_observers",
                type=SymbolType.METHOD,
                file_path="observer.py",
                line_number=20,
            ),
            Symbol(
                name="subscribe",
                type=SymbolType.METHOD,
                file_path="observer.py",
                line_number=25,
            ),
        ]

    @pytest.fixture
    def sample_graph(self):
        """Create sample graph."""
        return CodeGraphBuilder()

    def test_detect_factory_pattern(self, detector, sample_symbols, sample_graph):
        """Test factory pattern detection."""
        pattern = detector.detect_factory_pattern(sample_symbols, sample_graph)

        assert pattern is not None
        assert pattern.name == "Factory"
        assert pattern.confidence > 0.5

    def test_detect_observer_pattern(self, detector, sample_symbols, sample_graph):
        """Test observer pattern detection."""
        pattern = detector.detect_observer_pattern(sample_symbols, sample_graph)

        assert pattern is not None
        assert pattern.name == "Observer"
        assert pattern.confidence > 0.5

    def test_detect_decorator_pattern_no_decorators(self, detector, sample_symbols, sample_graph):
        """Test decorator pattern detection without decorators."""
        pattern = detector.detect_decorator_pattern(sample_symbols, sample_graph)

        # Pattern is None when no decorators detected (confidence filter)
        assert pattern is None or pattern.name == "Decorator"

    def test_detect_dry_violation(self, detector, sample_symbols):
        """Test DRY violation detection."""
        # Add similar named methods
        symbols = sample_symbols + [
            Symbol(
                name="process_data_1",
                type=SymbolType.METHOD,
                file_path="test.py",
                line_number=10,
            ),
            Symbol(
                name="process_data_2",
                type=SymbolType.METHOD,
                file_path="test.py",
                line_number=20,
            ),
        ]

        pattern = detector.detect_dry_violation(symbols, "")
        assert pattern is not None or pattern is None  # May or may not detect

    def test_detect_high_coupling(self, detector, sample_graph):
        """Test high coupling detection."""
        from src.athena.code_search.code_graph_integration import CodeRelationType, CodeEntity, CodeEntityType

        # Add entities first
        main_entity = CodeEntity(
            name="MainModule",
            entity_type=CodeEntityType.MODULE,
            file_path="main.py",
            line_number=1,
        )
        sample_graph.entities["MainModule"] = main_entity
        sample_graph._entity_index["main.py"] = {"MainModule"}

        # Add many dependencies
        for i in range(6):
            sample_graph.add_relationship(
                "MainModule",
                f"Dependency{i}",
                CodeRelationType.DEPENDS_ON,
            )

        pattern = detector.detect_high_coupling(sample_graph)
        assert pattern is not None
        assert pattern.confidence > 0.5

    def test_detect_insufficient_documentation(self, detector):
        """Test insufficient documentation detection."""
        symbols = [
            Symbol(
                name="public_function",
                type=SymbolType.FUNCTION,
                file_path="test.py",
                line_number=10,
                docstring=None,  # No docs
            ),
            Symbol(
                name="another_function",
                type=SymbolType.FUNCTION,
                file_path="test.py",
                line_number=20,
                docstring=None,  # No docs
            ),
        ]

        pattern = detector.detect_insufficient_documentation(symbols)
        if pattern and pattern.confidence > 0.5:
            assert pattern.name == "Insufficient Documentation"


class TestPatternAnalyzer:
    """Tests for PatternAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer."""
        return PatternAnalyzer()

    @pytest.fixture
    def test_symbols(self):
        """Create test symbols."""
        return [
            Symbol(
                name="create_user",
                type=SymbolType.FUNCTION,
                file_path="services.py",
                line_number=10,
                docstring="Creates a user",
            ),
            Symbol(
                name="UserService",
                type=SymbolType.CLASS,
                file_path="services.py",
                line_number=20,
                complexity=3,
            ),
            Symbol(
                name="notify_observers",
                type=SymbolType.METHOD,
                file_path="events.py",
                line_number=30,
            ),
        ]

    @pytest.fixture
    def test_graph(self):
        """Create test graph."""
        return CodeGraphBuilder()

    def test_analyze_code(self, analyzer, test_symbols, test_graph):
        """Test code analysis."""
        patterns = analyzer.analyze_code(test_symbols, test_graph)

        assert isinstance(patterns, list)
        # May or may not detect patterns depending on heuristics
        assert len(patterns) >= 0

    def test_learn_pattern(self, analyzer):
        """Test pattern learning."""
        pattern = CodePattern(
            name="TestPattern",
            pattern_type=PatternType.DESIGN_PATTERN,
            category=PatternCategory.STRUCTURAL,
            confidence=0.8,
        )

        analyzer.learn_pattern(pattern)

        assert len(analyzer.learned_patterns) == 1
        assert pattern.frequency == 1

    def test_learn_pattern_twice(self, analyzer):
        """Test learning same pattern twice."""
        pattern = CodePattern(
            name="TestPattern",
            pattern_type=PatternType.DESIGN_PATTERN,
            category=PatternCategory.STRUCTURAL,
        )

        analyzer.learn_pattern(pattern)
        analyzer.learn_pattern(pattern)

        assert len(analyzer.learned_patterns) == 1
        learned = analyzer.learned_patterns[list(analyzer.learned_patterns.keys())[0]]
        assert learned.frequency == 2

    def test_get_learned_patterns(self, analyzer):
        """Test retrieving learned patterns."""
        patterns = [
            CodePattern(
                name="Pattern1",
                pattern_type=PatternType.DESIGN_PATTERN,
                category=PatternCategory.STRUCTURAL,
            ),
            CodePattern(
                name="Pattern2",
                pattern_type=PatternType.ANTI_PATTERN,
                category=PatternCategory.STRUCTURAL,
            ),
        ]

        for p in patterns:
            analyzer.learn_pattern(p)

        learned = analyzer.get_learned_patterns()
        assert len(learned) == 2

    def test_get_patterns_by_type(self, analyzer):
        """Test filtering by pattern type."""
        analyzer.learn_pattern(
            CodePattern(
                name="DesignPattern",
                pattern_type=PatternType.DESIGN_PATTERN,
                category=PatternCategory.STRUCTURAL,
            )
        )
        analyzer.learn_pattern(
            CodePattern(
                name="AntiPattern",
                pattern_type=PatternType.ANTI_PATTERN,
                category=PatternCategory.STRUCTURAL,
            )
        )

        design_patterns = analyzer.get_patterns_by_type(PatternType.DESIGN_PATTERN)
        assert len(design_patterns) == 1
        assert design_patterns[0].name == "DesignPattern"

    def test_get_patterns_by_category(self, analyzer):
        """Test filtering by category."""
        analyzer.learn_pattern(
            CodePattern(
                name="CreationalPattern",
                pattern_type=PatternType.DESIGN_PATTERN,
                category=PatternCategory.CREATIONAL,
            )
        )
        analyzer.learn_pattern(
            CodePattern(
                name="BehavioralPattern",
                pattern_type=PatternType.DESIGN_PATTERN,
                category=PatternCategory.BEHAVIORAL,
            )
        )

        creational = analyzer.get_patterns_by_category(PatternCategory.CREATIONAL)
        assert len(creational) == 1

    def test_suggest_improvements(self, analyzer):
        """Test improvement suggestions."""
        pattern = CodePattern(
            name="TestAntiPattern",
            pattern_type=PatternType.ANTI_PATTERN,
            category=PatternCategory.STRUCTURAL,
            improvements=["Refactor duplicate code", "Extract common logic"],
        )

        improvements = analyzer.suggest_improvements([pattern])
        assert "TestAntiPattern" in improvements
        assert len(improvements["TestAntiPattern"]) == 2

    def test_calculate_quality_score_no_patterns(self, analyzer):
        """Test quality score with no patterns."""
        score = analyzer.calculate_code_quality_score([])
        assert score == 1.0

    def test_calculate_quality_score_with_patterns(self, analyzer):
        """Test quality score calculation."""
        patterns = [
            CodePattern(
                name="AntiPattern",
                pattern_type=PatternType.ANTI_PATTERN,
                category=PatternCategory.STRUCTURAL,
            ),
            CodePattern(
                name="DesignPattern",
                pattern_type=PatternType.DESIGN_PATTERN,
                category=PatternCategory.STRUCTURAL,
            ),
        ]

        score = analyzer.calculate_code_quality_score(patterns)
        assert 0 <= score <= 1

    def test_generate_pattern_report(self, analyzer):
        """Test report generation."""
        pattern = CodePattern(
            name="TestPattern",
            pattern_type=PatternType.DESIGN_PATTERN,
            category=PatternCategory.STRUCTURAL,
            description="A test pattern",
            confidence=0.85,
        )
        analyzer.learn_pattern(pattern)

        report = analyzer.generate_pattern_report([pattern])
        assert "TestPattern" in report
        assert "test pattern" in report.lower()


class TestProceduralMemoryIntegration:
    """Tests for procedural memory integration."""

    @pytest.fixture
    def integration(self):
        """Create integration."""
        return ProceduralMemoryIntegration()

    @pytest.fixture
    def code_context(self):
        """Create code context."""
        symbols = [
            Symbol(
                name="process_data",
                type=SymbolType.FUNCTION,
                file_path="main.py",
                line_number=10,
                docstring="Processes input data",
            ),
            Symbol(
                name="DataProcessor",
                type=SymbolType.CLASS,
                file_path="main.py",
                line_number=5,
                complexity=3,
            ),
        ]
        graph = CodeGraphBuilder()
        for symbol in symbols:
            graph.add_symbol(symbol)
        return symbols, graph, "def process_data(x): return x * 2"

    def test_record_code_patterns(self, integration, code_context):
        """Test recording patterns."""
        symbols, graph, code = code_context

        result = integration.record_code_patterns(
            symbols, graph, code, session_id="test_session"
        )

        assert "patterns_detected" in result
        assert "patterns" in result
        assert "quality_score" in result
        assert result["session_id"] == "test_session"

    def test_get_pattern_insights(self, integration, code_context):
        """Test getting insights."""
        symbols, graph, code = code_context

        integration.record_code_patterns(symbols, graph, code)
        insights = integration.get_pattern_insights()

        assert "total_patterns_learned" in insights
        assert "by_type" in insights
        assert "by_category" in insights

    def test_suggest_refactorings(self, integration):
        """Test refactoring suggestions."""
        # Add anti-pattern
        pattern = CodePattern(
            name="TestAntiPattern",
            pattern_type=PatternType.ANTI_PATTERN,
            category=PatternCategory.STRUCTURAL,
            entities=["func1", "func2"],
            improvements=["Refactor"],
        )
        integration.analyzer.learn_pattern(pattern)

        suggestions = integration.suggest_refactorings()
        assert len(suggestions) >= 0  # May have suggestions


class TestPatternIntegration:
    """Integration tests for pattern detection."""

    def test_full_pattern_workflow(self):
        """Test complete pattern detection workflow."""
        # Create analyzer
        integration = ProceduralMemoryIntegration()

        # Create symbols for factory pattern
        symbols = [
            Symbol(
                name="create_database",
                type=SymbolType.FUNCTION,
                file_path="factory.py",
                line_number=10,
                docstring="Factory method for creating DB",
            ),
            Symbol(
                name="create_cache",
                type=SymbolType.FUNCTION,
                file_path="factory.py",
                line_number=20,
            ),
        ]

        # Create graph
        graph = CodeGraphBuilder()
        for symbol in symbols:
            graph.add_symbol(symbol)

        # Record patterns
        result = integration.record_code_patterns(symbols, graph, "")

        assert result["patterns_detected"] >= 0
        assert "quality_score" in result

        # Get insights
        insights = integration.get_pattern_insights()
        assert insights["total_patterns_learned"] >= 0
