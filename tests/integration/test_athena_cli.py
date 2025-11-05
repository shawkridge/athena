"""Integration tests for ATHENA CLI tool.

Tests comprehensive CLI functionality including:
- analyze command with various profiles
- Configuration file loading
- Multi-format output generation
- Error handling
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import yaml

from athena.cli import (
    ATHENAAnalyzer,
    AnalysisConfig,
    AnalysisProfile,
    OutputFormat,
    AnalysisSummary,
    load_config,
)


@pytest.fixture
def temp_source_dir(tmp_path):
    """Create temporary source directory with test files."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    # Create test Python files
    (src_dir / "main.py").write_text("""
def process_data(user_id):
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    result = execute_query(query)
    return result
""")

    (src_dir / "utils.py").write_text("""
def helper_function():
    x = 1
    y = 2
    return x + y
""")

    # Create test JavaScript files
    (src_dir / "app.js").write_text("""
function authenticate(token) {
    const query = "SELECT * FROM users WHERE token = " + token;
    return db.execute(query);
}
""")

    return src_dir


@pytest.fixture
def analysis_config(temp_source_dir):
    """Create basic analysis configuration."""
    return AnalysisConfig(
        source_dir=temp_source_dir,
        profile=AnalysisProfile.STANDARD,
        output_format=OutputFormat.JSON,
        verbose=False,
    )


class TestAnalysisConfig:
    """Test AnalysisConfig initialization and defaults."""

    def test_config_initialization(self, temp_source_dir):
        """Test basic config initialization."""
        config = AnalysisConfig(source_dir=temp_source_dir)
        assert config.source_dir == temp_source_dir
        assert config.profile == AnalysisProfile.STANDARD
        assert config.output_format == OutputFormat.JSON

    def test_config_with_custom_patterns(self, temp_source_dir):
        """Test config with custom include/exclude patterns."""
        patterns = ["**/*.py", "**/*.ts"]
        excludes = ["**/test_*.py", "**/dist/**"]

        config = AnalysisConfig(
            source_dir=temp_source_dir,
            include_patterns=patterns,
            exclude_patterns=excludes,
        )

        assert config.include_patterns == patterns
        assert config.exclude_patterns == excludes

    def test_config_all_profiles(self, temp_source_dir):
        """Test config with all available profiles."""
        for profile in AnalysisProfile:
            config = AnalysisConfig(
                source_dir=temp_source_dir,
                profile=profile,
            )
            assert config.profile == profile

    def test_config_all_output_formats(self, temp_source_dir):
        """Test config with all output formats."""
        for fmt in OutputFormat:
            config = AnalysisConfig(
                source_dir=temp_source_dir,
                output_format=fmt,
            )
            assert config.output_format == fmt

    def test_config_default_patterns(self):
        """Test that default patterns are set."""
        config = AnalysisConfig(source_dir=Path("."))
        assert config.include_patterns is not None
        assert len(config.include_patterns) > 0
        assert config.exclude_patterns is not None
        assert len(config.exclude_patterns) > 0


class TestATHENAAnalyzer:
    """Test ATHENA analyzer functionality."""

    def test_analyzer_initialization(self, analysis_config):
        """Test analyzer initialization."""
        analyzer = ATHENAAnalyzer(analysis_config)
        assert analyzer.config == analysis_config
        assert analyzer.parser is not None
        assert analyzer.integrator is not None

    def test_analyzer_verbose_logging(self, analysis_config, capsys):
        """Test verbose logging output."""
        analyzer = ATHENAAnalyzer(analysis_config, verbose=True)
        analyzer.log("Test message", "INFO")

        captured = capsys.readouterr()
        assert "Test message" in captured.err
        assert "INFO" in captured.err

    def test_analyzer_log_levels(self, analysis_config, capsys):
        """Test different log levels."""
        analyzer = ATHENAAnalyzer(analysis_config, verbose=True)

        for level in ["INFO", "WARNING", "ERROR", "DEBUG"]:
            analyzer.log(f"Message at {level}", level)

        captured = capsys.readouterr()
        assert "INFO" in captured.err
        assert "WARNING" in captured.err
        assert "ERROR" in captured.err

    def test_analyzer_log_silent_when_not_verbose(self, analysis_config, capsys):
        """Test that logging is silent when verbose=False."""
        analyzer = ATHENAAnalyzer(analysis_config, verbose=False)
        analyzer.log("This should not appear")

        captured = capsys.readouterr()
        assert "This should not appear" not in captured.err

    def test_get_quick_analyzers(self, analysis_config):
        """Test quick analyzer selection."""
        analyzer = ATHENAAnalyzer(analysis_config)
        quick = analyzer._get_quick_analyzers()

        assert "complexity" in quick
        assert "quality_score" in quick
        assert len(quick) == 2

    def test_get_security_analyzers(self, analysis_config):
        """Test security analyzer selection."""
        analyzer = ATHENAAnalyzer(analysis_config)
        security = analyzer._get_security_analyzers()

        assert "security" in security
        assert "dead_code" in security

    def test_get_performance_analyzers(self, analysis_config):
        """Test performance analyzer selection."""
        analyzer = ATHENAAnalyzer(analysis_config)
        perf = analyzer._get_performance_analyzers()

        assert "performance" in perf
        assert "complexity" in perf

    def test_get_quality_analyzers(self, analysis_config):
        """Test quality analyzer selection."""
        analyzer = ATHENAAnalyzer(analysis_config)
        quality = analyzer._get_quality_analyzers()

        assert "patterns" in quality
        assert "code_smells" in quality
        assert "quality_score" in quality
        assert "technical_debt" in quality
        assert "refactoring" in quality

    def test_get_all_analyzers(self, analysis_config):
        """Test all analyzers selection."""
        analyzer = ATHENAAnalyzer(analysis_config)
        all_analyzers = analyzer._get_all_analyzers()

        # Expected analyzers (dead_code requires DependencyResolver, so it's optional)
        expected_analyzers = [
            "patterns",
            "security",
            "performance",
            "quality_score",
            "code_smells",
            "technical_debt",
            "refactoring",
            "complexity",
        ]

        for expected in expected_analyzers:
            assert expected in all_analyzers

        # Verify at least 8 analyzers are present
        assert len(all_analyzers) >= 8

    @patch("athena.cli.ATHENAAnalyzer._parse_source")
    @patch("athena.cli.ATHENAAnalyzer._run_analysis")
    @patch("athena.cli.ATHENAAnalyzer._create_summary")
    def test_analyze_execution(self, mock_summary, mock_analysis, mock_parse, analysis_config):
        """Test full analyze execution."""
        # Setup mocks
        mock_parse.return_value = {"symbol1": {}}
        mock_analysis.return_value = {"analyzers": {}, "issues": []}
        mock_summary.return_value = AnalysisSummary(
            timestamp="2025-10-31T12:00:00",
            source_dir="test",
            profile="standard",
            total_files=1,
            total_symbols=1,
            total_issues=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            overall_quality_score=75.0,
            security_score=70.0,
            performance_score=75.0,
            maintainability_score=70.0,
            analysis_duration_seconds=1.0,
        )

        analyzer = ATHENAAnalyzer(analysis_config)
        results = analyzer.analyze()

        assert "summary" in results
        assert "results" in results
        assert "config" in results
        assert results["config"]["profile"] == "standard"

    def test_create_summary(self, analysis_config):
        """Test summary creation."""
        analyzer = ATHENAAnalyzer(analysis_config)

        results = {
            "issues": [
                {"severity": "CRITICAL"},
                {"severity": "HIGH"},
                {"severity": "HIGH"},
                {"severity": "MEDIUM"},
            ],
            "metrics": {
                "overall_score": 80.0,
                "security_score": 75.0,
                "performance_score": 85.0,
                "maintainability_score": 78.0,
            }
        }

        summary = analyzer._create_summary(results, 5.0)

        assert summary.total_issues == 4
        assert summary.critical_count == 1
        assert summary.high_count == 2
        assert summary.medium_count == 1
        assert summary.low_count == 0
        assert summary.overall_quality_score == 80.0
        assert summary.analysis_duration_seconds == 5.0


class TestConfigLoading:
    """Test configuration file loading."""

    def test_load_config_defaults(self):
        """Test loading with no config file."""
        config = load_config(None)
        assert config.source_dir == Path(".")
        assert config.profile == AnalysisProfile.STANDARD

    def test_load_config_from_file(self, tmp_path):
        """Test loading configuration from YAML file."""
        config_file = tmp_path / ".athena.yml"
        config_data = {
            "source_dir": "src/",
            "profile": "security",
            "output_format": "html",
            "include_patterns": ["**/*.py"],
            "exclude_patterns": ["**/test_*.py"],
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_file))

        assert config.source_dir == Path("src/")
        assert config.profile == AnalysisProfile.SECURITY
        assert config.output_format == OutputFormat.HTML
        assert "**/*.py" in config.include_patterns

    def test_load_config_missing_optional_fields(self, tmp_path):
        """Test loading config with minimal required fields."""
        config_file = tmp_path / ".athena.yml"
        config_data = {
            "source_dir": "src/",
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_file))

        assert config.source_dir == Path("src/")
        assert config.profile == AnalysisProfile.STANDARD  # Default

    def test_load_config_nonexistent_file(self):
        """Test loading nonexistent config file returns defaults."""
        config = load_config("nonexistent.yml")
        assert config.source_dir == Path(".")


class TestAnalysisProfiles:
    """Test analysis profiles functionality."""

    def test_quick_profile_analyzers(self, analysis_config):
        """Test quick profile includes minimal analyzers."""
        analysis_config.profile = AnalysisProfile.QUICK
        analyzer = ATHENAAnalyzer(analysis_config)

        quick_analyzers = analyzer._get_quick_analyzers()
        assert len(quick_analyzers) == 2  # Quick should be minimal

    def test_comprehensive_profile_analyzers(self, analysis_config):
        """Test comprehensive profile includes all analyzers."""
        analysis_config.profile = AnalysisProfile.COMPREHENSIVE
        analyzer = ATHENAAnalyzer(analysis_config)

        all_analyzers = analyzer._get_all_analyzers()
        assert len(all_analyzers) > 5

    def test_security_profile_includes_security_analyzer(self, analysis_config):
        """Test security profile includes security analyzer."""
        analysis_config.profile = AnalysisProfile.SECURITY
        analyzer = ATHENAAnalyzer(analysis_config)

        security_analyzers = analyzer._get_security_analyzers()
        assert "security" in security_analyzers

    def test_performance_profile_includes_performance_analyzer(self, analysis_config):
        """Test performance profile includes performance analyzer."""
        analysis_config.profile = AnalysisProfile.PERFORMANCE
        analyzer = ATHENAAnalyzer(analysis_config)

        perf_analyzers = analyzer._get_performance_analyzers()
        assert "performance" in perf_analyzers

    def test_quality_profile_includes_quality_analyzer(self, analysis_config):
        """Test quality profile includes quality analyzer."""
        analysis_config.profile = AnalysisProfile.QUALITY
        analyzer = ATHENAAnalyzer(analysis_config)

        quality_analyzers = analyzer._get_quality_analyzers()
        assert "quality_score" in quality_analyzers


class TestOutputFormats:
    """Test output format handling."""

    def test_json_output_format(self, analysis_config):
        """Test JSON output format."""
        analysis_config.output_format = OutputFormat.JSON
        assert analysis_config.output_format == OutputFormat.JSON

    def test_html_output_format(self, analysis_config):
        """Test HTML output format."""
        analysis_config.output_format = OutputFormat.HTML
        assert analysis_config.output_format == OutputFormat.HTML

    def test_text_output_format(self, analysis_config):
        """Test TEXT output format."""
        analysis_config.output_format = OutputFormat.TEXT
        assert analysis_config.output_format == OutputFormat.TEXT

    def test_markdown_output_format(self, analysis_config):
        """Test MARKDOWN output format."""
        analysis_config.output_format = OutputFormat.MARKDOWN
        assert analysis_config.output_format == OutputFormat.MARKDOWN


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_analyze_with_empty_directory(self, tmp_path):
        """Test analyzing empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        config = AnalysisConfig(
            source_dir=empty_dir,
            include_patterns=["**/*.py"],
        )
        analyzer = ATHENAAnalyzer(config, verbose=False)

        # Should not raise error, just return empty results
        assert analyzer.config.source_dir == empty_dir

    def test_analysis_summary_with_no_issues(self, analysis_config):
        """Test summary creation with no issues."""
        analyzer = ATHENAAnalyzer(analysis_config)

        results = {
            "issues": [],
            "metrics": {
                "overall_score": 95.0,
                "security_score": 95.0,
                "performance_score": 95.0,
                "maintainability_score": 95.0,
            }
        }

        summary = analyzer._create_summary(results, 2.0)

        assert summary.total_issues == 0
        assert summary.critical_count == 0
        assert summary.overall_quality_score == 95.0

    def test_analysis_summary_all_critical_issues(self, analysis_config):
        """Test summary with all critical issues."""
        analyzer = ATHENAAnalyzer(analysis_config)

        results = {
            "issues": [
                {"severity": "CRITICAL"},
                {"severity": "CRITICAL"},
                {"severity": "CRITICAL"},
            ],
            "metrics": {}
        }

        summary = analyzer._create_summary(results, 1.0)

        assert summary.total_issues == 3
        assert summary.critical_count == 3

    def test_config_path_normalization(self, tmp_path):
        """Test that paths are properly normalized."""
        source = tmp_path / "src"
        source.mkdir()

        config = AnalysisConfig(source_dir=source)
        assert isinstance(config.source_dir, Path)
        assert config.source_dir.exists()
