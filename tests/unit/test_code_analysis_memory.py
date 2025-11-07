"""Tests for code analysis memory integration."""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from athena.code_search.code_analysis_memory import CodeAnalysisMemory, CodeAnalysisMemoryManager
from athena.episodic.models import EpisodicEvent, EventType, CodeEventType, EventOutcome


class TestCodeAnalysisMemory:
    """Test CodeAnalysisMemory class."""

    @pytest.fixture
    def mock_stores(self):
        """Create mock memory stores."""
        return {
            "episodic_store": Mock(),
            "semantic_store": Mock(),
            "graph_store": Mock(),
            "consolidator": Mock(),
        }

    @pytest.fixture
    def memory(self, mock_stores):
        """Create CodeAnalysisMemory with mocks."""
        return CodeAnalysisMemory(
            episodic_store=mock_stores["episodic_store"],
            semantic_store=mock_stores["semantic_store"],
            graph_store=mock_stores["graph_store"],
            consolidator=mock_stores["consolidator"],
            project_id=1,
            session_id="test_session",
        )

    # ========================================================================
    # record_code_analysis Tests
    # ========================================================================

    def test_record_code_analysis_success(self, memory, mock_stores):
        """Test successful code analysis recording."""
        # Setup
        mock_stores["episodic_store"].store_event.return_value = 123

        analysis_results = {
            "quality_score": 0.85,
            "complexity_avg": 4.5,
            "test_coverage": "80%",
            "issues": [{"type": "high_complexity", "unit": "process"}],
        }

        # Execute
        event_id = memory.record_code_analysis(
            repo_path="/test/repo",
            analysis_results=analysis_results,
            duration_ms=2500,
            file_count=100,
            unit_count=1200,
        )

        # Assert
        assert event_id == 123
        mock_stores["episodic_store"].store_event.assert_called_once()

        # Verify event structure
        call_args = mock_stores["episodic_store"].store_event.call_args
        event = call_args[0][0]

        assert event.project_id == 1
        assert event.session_id == "test_session"
        assert event.event_type == EventType.ACTION
        assert event.code_event_type == CodeEventType.CODE_REVIEW
        assert event.outcome == EventOutcome.SUCCESS
        assert event.duration_ms == 2500
        assert event.files_changed == 100
        assert event.performance_metrics["units_analyzed"] == 1200

    def test_record_code_analysis_no_store(self):
        """Test recording without episodic store."""
        memory = CodeAnalysisMemory(
            episodic_store=None,
            semantic_store=None,
            graph_store=None,
            consolidator=None,
        )

        event_id = memory.record_code_analysis(
            repo_path="/test",
            analysis_results={},
            duration_ms=100,
        )

        assert event_id is None

    def test_record_code_analysis_with_issues(self, memory, mock_stores):
        """Test recording analysis with detected issues."""
        mock_stores["episodic_store"].store_event.return_value = 456

        analysis_results = {
            "quality_score": 0.5,
            "complexity_avg": 8.0,
            "issues": [
                {"type": "high_complexity", "unit": "func1"},
                {"type": "high_complexity", "unit": "func2"},
                {"type": "security", "unit": "auth"},
            ],
        }

        event_id = memory.record_code_analysis(
            repo_path="/test",
            analysis_results=analysis_results,
            duration_ms=3000,
            file_count=50,
            unit_count=500,
        )

        assert event_id == 456
        call_args = mock_stores["episodic_store"].store_event.call_args
        event = call_args[0][0]

        assert event.code_quality_score == 0.5

    # ========================================================================
    # store_code_insights Tests
    # ========================================================================

    def test_store_code_insights_success(self, memory, mock_stores):
        """Test successful insight storage."""
        analysis_results = {
            "quality_score": 0.75,
            "complexity_avg": 5.0,
            "test_coverage": "75%",
            "issues": [{"type": "warning"}],
        }

        result = memory.store_code_insights(
            analysis_results=analysis_results,
            repo_path="/test",
            tags=["test", "analysis"],
        )

        assert result is True
        # Verify multiple insights were stored
        assert mock_stores["semantic_store"].remember.call_count >= 3

    def test_store_code_insights_no_store(self):
        """Test insight storage without semantic store."""
        memory = CodeAnalysisMemory(
            episodic_store=None,
            semantic_store=None,
            graph_store=None,
            consolidator=None,
        )

        result = memory.store_code_insights(
            analysis_results={},
            repo_path="/test",
        )

        assert result is False

    def test_store_code_insights_with_custom_tags(self, memory, mock_stores):
        """Test insight storage with custom tags."""
        analysis_results = {
            "quality_score": 0.8,
            "complexity_avg": 4.0,
            "test_coverage": "80%",
            "issues": [],
        }

        memory.store_code_insights(
            analysis_results=analysis_results,
            repo_path="/test",
            tags=["custom", "tag"],
        )

        # Verify custom tags are used
        for call in mock_stores["semantic_store"].remember.call_args_list:
            kwargs = call[1]
            tags = kwargs.get("tags", [])
            assert "custom" in tags or "tag" in tags

    # ========================================================================
    # add_code_entities_to_graph Tests
    # ========================================================================

    def test_add_code_entities_to_graph_success(self, memory, mock_stores):
        """Test successful entity addition to graph."""
        code_units = [
            {
                "name": "validate_email",
                "type": "Function",  # Use capitalized entity type
                "file": "validators.py",
                "line": 42,
                "docstring": "Validates email format",
                "complexity": 3,
            },
            {
                "name": "UserValidator",
                "type": "Component",  # Use Component for class types
                "file": "validators.py",
                "line": 100,
                "docstring": "Validates users",
                "complexity": 5,
            },
        ]

        count = memory.add_code_entities_to_graph(
            code_units=code_units,
            repo_path="/test",
        )

        assert count == 2
        # Verify entity addition called
        assert mock_stores["graph_store"].add_entity.call_count >= 2

    def test_add_code_entities_to_graph_empty(self, memory, mock_stores):
        """Test entity addition with empty list."""
        count = memory.add_code_entities_to_graph(
            code_units=[],
            repo_path="/test",
        )

        assert count == 0
        mock_stores["graph_store"].add_entity.assert_not_called()

    def test_add_code_entities_to_graph_no_store(self):
        """Test entity addition without graph store."""
        memory = CodeAnalysisMemory(
            episodic_store=None,
            semantic_store=None,
            graph_store=None,
            consolidator=None,
        )

        code_units = [{"name": "test", "type": "function"}]
        count = memory.add_code_entities_to_graph(
            code_units=code_units,
            repo_path="/test",
        )

        assert count == 0

    def test_add_code_entities_handles_errors(self, memory, mock_stores):
        """Test graceful handling of entity addition errors."""
        mock_stores["graph_store"].add_entity.side_effect = Exception("Graph error")

        code_units = [
            {"name": "func1", "type": "function"},
            {"name": "func2", "type": "function"},
        ]

        # Should not raise, should log and continue
        count = memory.add_code_entities_to_graph(
            code_units=code_units,
            repo_path="/test",
        )

        # Count should be 0 due to errors
        assert count == 0

    # ========================================================================
    # record_code_metrics_trend Tests
    # ========================================================================

    def test_record_code_metrics_trend_success(self, memory, mock_stores):
        """Test successful metrics trend recording."""
        metrics = {
            "files_indexed": 150,
            "units_extracted": 2000,
            "avg_complexity": 4.5,
            "indexing_time_ms": 2500,
        }

        result = memory.record_code_metrics_trend(
            metrics=metrics,
            repo_path="/test",
        )

        assert result is True
        mock_stores["episodic_store"].store_event.assert_called_once()

    def test_record_code_metrics_trend_no_store(self):
        """Test metrics recording without episodic store."""
        memory = CodeAnalysisMemory(
            episodic_store=None,
            semantic_store=None,
            graph_store=None,
            consolidator=None,
        )

        result = memory.record_code_metrics_trend(
            metrics={"test": 1},
            repo_path="/test",
        )

        assert result is False

    # ========================================================================
    # extract_analysis_patterns Tests
    # ========================================================================

    def test_extract_analysis_patterns_success(self, memory, mock_stores):
        """Test successful pattern extraction."""
        mock_events = [Mock(), Mock(), Mock()]
        mock_stores["episodic_store"].get_events_by_type.return_value = mock_events
        mock_stores["consolidator"].consolidate.return_value = {"pattern": "data"}

        result = memory.extract_analysis_patterns(days_back=7)

        assert result == {"pattern": "data"}
        mock_stores["consolidator"].consolidate.assert_called_once()

    def test_extract_analysis_patterns_no_events(self, memory, mock_stores):
        """Test pattern extraction with no events."""
        mock_stores["episodic_store"].get_events_by_type.return_value = []

        result = memory.extract_analysis_patterns(days_back=7)

        assert result is None
        mock_stores["consolidator"].consolidate.assert_not_called()

    def test_extract_analysis_patterns_no_consolidator(self, mock_stores):
        """Test pattern extraction without consolidator."""
        memory = CodeAnalysisMemory(
            episodic_store=mock_stores["episodic_store"],
            semantic_store=None,
            graph_store=None,
            consolidator=None,
        )

        result = memory.extract_analysis_patterns(days_back=7)

        assert result is None

    # ========================================================================
    # Helper Method Tests
    # ========================================================================

    def test_summarize_analysis(self, memory):
        """Test analysis summarization."""
        analysis = {
            "quality_score": 0.85,
            "complexity_avg": 4.5,
            "issues": [1, 2, 3],
        }

        summary = memory._summarize_analysis(analysis)

        assert "0.85" in summary or "85" in summary
        assert "4.50" in summary or "4.5" in summary
        assert "3" in summary

    def test_extract_learnings(self, memory):
        """Test learning extraction from analysis."""
        analysis = {
            "quality_score": 0.3,  # Below 0.5 -> learning 1
            "complexity_avg": 6,   # Above 5 -> learning 3
            "test_coverage": 0.5,  # Below 0.7 -> learning 4
            "issues": list(range(15)),  # > 10 -> learning 2
        }

        learnings = memory._extract_learnings(analysis)

        assert "quality" in learnings.lower() or "refactor" in learnings.lower()
        assert "complexity" in learnings.lower() or "break" in learnings.lower()
        assert "test" in learnings.lower() or "coverage" in learnings.lower()


class TestCodeAnalysisMemoryManager:
    """Test CodeAnalysisMemoryManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        mock_memory_manager = Mock()
        mock_memory_manager.episodic_store = Mock()
        mock_memory_manager.semantic_store = Mock()
        mock_memory_manager.graph_store = Mock()
        mock_memory_manager.consolidator = Mock()
        mock_memory_manager.project_id = 1
        mock_memory_manager.session_id = "session"

        manager = CodeAnalysisMemoryManager(memory_manager=mock_memory_manager)

        assert manager.analysis_memory is not None
        assert manager.analysis_memory.project_id == 1

    def test_manager_without_memory_manager(self):
        """Test manager without underlying memory manager."""
        manager = CodeAnalysisMemoryManager(memory_manager=None)

        assert manager.memory_manager is None
        assert manager.analysis_memory is None

    def test_manager_record_analysis(self):
        """Test manager record_analysis delegation."""
        mock_analysis_memory = Mock()
        mock_analysis_memory.record_code_analysis.return_value = 123

        manager = CodeAnalysisMemoryManager()
        manager.analysis_memory = mock_analysis_memory

        result = manager.record_analysis(
            repo_path="/test",
            analysis_results={},
            duration_ms=100,
        )

        assert result == 123
        mock_analysis_memory.record_code_analysis.assert_called_once()

    def test_manager_store_insights(self):
        """Test manager store_insights delegation."""
        mock_analysis_memory = Mock()
        mock_analysis_memory.store_code_insights.return_value = True

        manager = CodeAnalysisMemoryManager()
        manager.analysis_memory = mock_analysis_memory

        result = manager.store_insights(
            analysis_results={},
            repo_path="/test",
        )

        assert result is True
        mock_analysis_memory.store_code_insights.assert_called_once()

    def test_manager_add_entities(self):
        """Test manager add_entities delegation."""
        mock_analysis_memory = Mock()
        mock_analysis_memory.add_code_entities_to_graph.return_value = 5

        manager = CodeAnalysisMemoryManager()
        manager.analysis_memory = mock_analysis_memory

        result = manager.add_entities(code_units=[], repo_path="/test")

        assert result == 5
        mock_analysis_memory.add_code_entities_to_graph.assert_called_once()

    def test_manager_extract_patterns(self):
        """Test manager extract_patterns delegation."""
        mock_analysis_memory = Mock()
        mock_analysis_memory.extract_analysis_patterns.return_value = {"trend": "up"}

        manager = CodeAnalysisMemoryManager()
        manager.analysis_memory = mock_analysis_memory

        result = manager.extract_patterns(days_back=7)

        assert result == {"trend": "up"}
        mock_analysis_memory.extract_analysis_patterns.assert_called_once()

    def test_manager_handles_missing_analysis_memory(self):
        """Test manager gracefully handles missing analysis_memory."""
        manager = CodeAnalysisMemoryManager()
        manager.analysis_memory = None

        assert manager.record_analysis(repo_path="/test", analysis_results={}, duration_ms=100) is None
        assert manager.store_insights(analysis_results={}, repo_path="/test") is False
        assert manager.add_entities(code_units=[], repo_path="/test") == 0
        assert manager.extract_patterns() is None


class TestCodeAnalysisMemoryIntegration:
    """Integration tests for CodeAnalysisMemory."""

    def test_full_analysis_flow(self):
        """Test complete analysis flow with mocked stores."""
        # Setup mocks
        episodic_mock = Mock()
        semantic_mock = Mock()
        graph_mock = Mock()
        consolidator_mock = Mock()

        episodic_mock.store_event.return_value = 1
        episodic_mock.get_events_by_type.return_value = [Mock(), Mock()]
        consolidator_mock.consolidate.return_value = {"trend": "improving"}

        memory = CodeAnalysisMemory(
            episodic_store=episodic_mock,
            semantic_store=semantic_mock,
            graph_store=graph_mock,
            consolidator=consolidator_mock,
            project_id=1,
        )

        # Execute flow
        analysis_results = {
            "quality_score": 0.8,
            "complexity_avg": 4.5,
            "issues": [],
        }

        # 1. Record event
        event_id = memory.record_code_analysis(
            repo_path="/project",
            analysis_results=analysis_results,
            duration_ms=2500,
            file_count=100,
            unit_count=1200,
        )

        assert event_id == 1

        # 2. Store insights
        result = memory.store_code_insights(
            analysis_results=analysis_results,
            repo_path="/project",
        )

        assert result is True

        # 3. Add entities
        count = memory.add_code_entities_to_graph(
            code_units=[
                {"name": "func1", "type": "Function"},
                {"name": "class1", "type": "Component"},
            ],
            repo_path="/project",
        )

        assert count == 2

        # 4. Extract patterns
        patterns = memory.extract_analysis_patterns(days_back=7)

        assert patterns == {"trend": "improving"}

    def test_multiple_analyses_over_time(self):
        """Test recording multiple analyses (simulating trend tracking)."""
        episodic_mock = Mock()
        episodic_mock.store_event.return_value = 1

        memory = CodeAnalysisMemory(episodic_store=episodic_mock)

        # Simulate multiple analyses
        for i in range(3):
            quality = 0.7 + (i * 0.05)  # Improving quality
            memory.record_code_analysis(
                repo_path="/project",
                analysis_results={"quality_score": quality},
                duration_ms=2000 + (i * 100),
                file_count=100,
                unit_count=1000,
            )

        # Verify all were recorded
        assert episodic_mock.store_event.call_count == 3
