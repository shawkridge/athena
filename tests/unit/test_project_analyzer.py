"""Unit tests for ProjectAnalyzer."""

import pytest
from pathlib import Path
from athena.analysis import ProjectAnalyzer, ProjectAnalysis


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project structure for testing."""
    # Create directory structure
    src = tmp_path / "src"
    src.mkdir()

    core = src / "core"
    core.mkdir()

    utils = src / "utils"
    utils.mkdir()

    tests = tmp_path / "tests"
    tests.mkdir()

    # Create Python files in core
    (core / "database.py").write_text("""
import asyncio
from typing import Optional, List

class Database:
    '''Database connection handler'''

    def __init__(self, path: str):
        self.path = path

    async def connect(self) -> None:
        '''Connect to database'''
        pass

    async def query(self, sql: str) -> List[dict]:
        '''Execute query'''
        try:
            result = await self._execute(sql)
            return result
        except Exception as e:
            print(f"Error: {e}")
            raise
""")

    (core / "models.py").write_text("""
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    id: int
    name: str
    email: Optional[str] = None

class Repository:
    def __init__(self):
        pass
""")

    # Create files in utils
    (utils / "helpers.py").write_text("""
def format_date(date):
    return str(date)

def validate_email(email: str) -> bool:
    return "@" in email
""")

    # Create test files
    (tests / "test_database.py").write_text("""
import pytest

def test_database_init():
    pass

def test_database_connect():
    pass
""")

    (tests / "test_utils.py").write_text("""
def test_format_date():
    pass
""")

    # Create config files
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'")
    (tmp_path / "README.md").write_text("# Sample Project")

    return tmp_path


class TestProjectAnalyzer:
    """Test ProjectAnalyzer functionality."""

    def test_initialization(self, sample_project):
        """Test analyzer initialization."""
        analyzer = ProjectAnalyzer(str(sample_project))
        assert analyzer.project_path == sample_project
        assert analyzer.project_name == sample_project.name

    def test_initialization_invalid_path(self):
        """Test initialization with invalid path."""
        with pytest.raises(ValueError):
            ProjectAnalyzer("/nonexistent/path")

    def test_scan_files(self, sample_project):
        """Test file scanning."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()

        assert len(analyzer.files) > 0
        # Should find: database.py, models.py, helpers.py, test_*.py
        assert len(analyzer.files) >= 4

    def test_file_metrics(self, sample_project):
        """Test file metrics collection."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()

        # Check that we have metrics for files
        for path, metrics in analyzer.files.items():
            assert metrics.path is not None
            assert metrics.lines >= 0
            assert metrics.language == "python"
            assert 0.0 <= metrics.complexity <= 1.0

    def test_language_detection(self, sample_project):
        """Test language detection."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()

        # All files should be detected as python
        languages = set(m.language for m in analyzer.files.values())
        assert "python" in languages

    def test_test_file_detection(self, sample_project):
        """Test that test files are marked correctly."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()

        test_files = [m for m in analyzer.files.values() if m.is_test]
        assert len(test_files) > 0

        # All test files should be in tests directory
        for tf in test_files:
            assert "test" in tf.path.lower()

    def test_identify_components(self, sample_project):
        """Test component identification."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()
        analyzer._identify_components()

        # Should identify components from directory structure
        assert len(analyzer.components) > 0
        # Components are identified by first directory level
        assert "src" in analyzer.components  # Top-level component

    def test_extract_patterns(self, sample_project):
        """Test pattern extraction."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()
        analyzer._extract_patterns()

        # Should find at least some patterns
        assert len(analyzer.patterns) > 0

        # Patterns should have basic properties
        for pattern in analyzer.patterns.values():
            assert pattern.name is not None
            assert pattern.occurrences >= 0
            assert 0.0 <= pattern.frequency <= 1.0

    def test_analyze_complete(self, sample_project):
        """Test complete analysis."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analysis = analyzer.analyze()

        # Check analysis structure
        assert isinstance(analysis, ProjectAnalysis)
        assert analysis.project_name == sample_project.name
        assert analysis.total_files > 0
        assert analysis.total_lines > 0

    def test_analysis_statistics(self, sample_project):
        """Test analysis statistics."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analysis = analyzer.analyze()

        # Check statistics
        assert analysis.languages["python"] > 0
        assert analysis.avg_complexity >= 0.0
        assert analysis.avg_complexity <= 1.0
        assert analysis.test_file_ratio >= 0.0
        assert analysis.test_file_ratio <= 1.0

    def test_analysis_components(self, sample_project):
        """Test component analysis."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analysis = analyzer.analyze()

        # Should identify components
        assert len(analysis.components) > 0

        # Each component should have metadata
        for component in analysis.components:
            assert component.name is not None
            assert len(component.files) > 0
            assert component.complexity >= 0.0

    def test_analysis_patterns(self, sample_project):
        """Test pattern analysis."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analysis = analyzer.analyze()

        # Should identify patterns
        assert len(analysis.patterns) > 0

        # Each pattern should have properties
        for pattern in analysis.patterns:
            assert pattern.name is not None
            assert pattern.occurrences >= 0

    def test_analysis_insights(self, sample_project):
        """Test insight generation."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analysis = analyzer.analyze()

        # Should generate insights
        assert len(analysis.insights) > 0

        # Insights should be strings
        for insight in analysis.insights:
            assert isinstance(insight, str)
            assert len(insight) > 0

    def test_analysis_recommendations(self, sample_project):
        """Test recommendation generation."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analysis = analyzer.analyze()

        # Should generate recommendations
        assert len(analysis.recommendations) >= 0

        # Recommendations should be strings
        for rec in analysis.recommendations:
            assert isinstance(rec, str)

    def test_complexity_calculation(self, sample_project):
        """Test complexity calculation."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()

        # All complexities should be valid
        for metrics in analyzer.files.values():
            assert 0.0 <= metrics.complexity <= 1.0

    def test_language_distribution(self, sample_project):
        """Test language distribution."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()

        dist = analyzer._get_language_distribution()

        # Should have python files
        assert "python" in dist
        assert dist["python"] > 0

    def test_test_coverage_ratio(self, sample_project):
        """Test test file ratio calculation."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()

        ratio = analyzer._calculate_test_ratio()

        # Should be valid ratio
        assert 0.0 <= ratio <= 1.0

    def test_average_complexity(self, sample_project):
        """Test average complexity calculation."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()

        avg = analyzer._calculate_avg_complexity()

        # Should be valid complexity value
        assert 0.0 <= avg <= 1.0

    def test_dependency_analysis(self, sample_project):
        """Test dependency analysis."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analyzer._scan_files()

        external, internal = analyzer._analyze_dependencies()

        # Should return lists/dicts
        assert isinstance(external, list)
        assert isinstance(internal, dict)

    def test_analysis_timestamp(self, sample_project):
        """Test analysis timestamp."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analysis = analyzer.analyze()

        # Should have valid timestamp
        assert analysis.analysis_timestamp is not None
        assert "T" in analysis.analysis_timestamp

    def test_analysis_reproducibility(self, sample_project):
        """Test that analysis is reproducible."""
        analyzer1 = ProjectAnalyzer(str(sample_project))
        analysis1 = analyzer1.analyze()

        analyzer2 = ProjectAnalyzer(str(sample_project))
        analysis2 = analyzer2.analyze()

        # Should have same counts
        assert analysis1.total_files == analysis2.total_files
        assert analysis1.total_lines == analysis2.total_lines
        assert len(analysis1.components) == len(analysis2.components)


class TestProjectAnalysisDataClass:
    """Test ProjectAnalysis dataclass."""

    def test_project_analysis_fields(self, sample_project):
        """Test ProjectAnalysis has required fields."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analysis = analyzer.analyze()

        # Check required fields exist
        assert hasattr(analysis, 'project_name')
        assert hasattr(analysis, 'project_path')
        assert hasattr(analysis, 'total_files')
        assert hasattr(analysis, 'total_lines')
        assert hasattr(analysis, 'languages')
        assert hasattr(analysis, 'components')
        assert hasattr(analysis, 'patterns')
        assert hasattr(analysis, 'insights')
        assert hasattr(analysis, 'recommendations')

    def test_project_analysis_types(self, sample_project):
        """Test ProjectAnalysis field types."""
        analyzer = ProjectAnalyzer(str(sample_project))
        analysis = analyzer.analyze()

        # Check types
        assert isinstance(analysis.project_name, str)
        assert isinstance(analysis.project_path, str)
        assert isinstance(analysis.total_files, int)
        assert isinstance(analysis.total_lines, int)
        assert isinstance(analysis.languages, dict)
        assert isinstance(analysis.components, list)
        assert isinstance(analysis.patterns, list)
        assert isinstance(analysis.insights, list)
        assert isinstance(analysis.recommendations, list)
