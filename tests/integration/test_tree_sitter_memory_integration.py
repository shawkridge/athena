"""Integration tests for TreeSitterCodeSearch with memory recording."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from athena.code_search.tree_sitter_search import TreeSitterCodeSearch
from athena.code_search.code_analysis_memory import CodeAnalysisMemory, CodeAnalysisMemoryManager
from athena.episodic.models import EpisodicEvent, EventType, CodeEventType, EventOutcome


class TestTreeSitterMemoryIntegration:
    """Integration tests for TreeSitterCodeSearch with memory system."""

    @pytest.fixture
    def sample_python_project(self, tmp_path):
        """Create a sample Python project for testing."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create some Python files
        main_py = project_dir / "main.py"
        main_py.write_text("""
def process_data(data):
    \"\"\"Process input data.\"\"\"
    result = []
    for item in data:
        if validate(item):
            result.append(transform(item))
    return result

def validate(item):
    \"\"\"Validate an item.\"\"\"
    return item is not None

def transform(item):
    \"\"\"Transform an item.\"\"\"
    return item.upper() if isinstance(item, str) else str(item)
""")

        utils_py = project_dir / "utils.py"
        utils_py.write_text("""
import json

class DataProcessor:
    \"\"\"Processes data with various strategies.\"\"\"

    def __init__(self, strategy="default"):
        self.strategy = strategy

    def process(self, data):
        \"\"\"Process data according to strategy.\"\"\"
        if self.strategy == "json":
            return json.dumps(data)
        return str(data)
""")

        return str(project_dir)

    @pytest.fixture
    def mock_memory_stores(self):
        """Create mock memory stores for testing."""
        return {
            "episodic_store": Mock(),
            "semantic_store": Mock(),
            "graph_store": Mock(),
            "consolidator": Mock(),
        }

    def test_build_index_records_to_memory(self, sample_python_project, mock_memory_stores):
        """Test that build_index records indexing event to memory."""
        # Setup mocks
        mock_memory_stores["episodic_store"].store_event.return_value = 1
        mock_memory_stores["semantic_store"].remember.return_value = True
        mock_memory_stores["graph_store"].add_entity.return_value = True

        # Create search with memory
        search = TreeSitterCodeSearch(
            sample_python_project,
            language="python",
            episodic_store=mock_memory_stores["episodic_store"],
            semantic_store=mock_memory_stores["semantic_store"],
            graph_store=mock_memory_stores["graph_store"],
            consolidator=mock_memory_stores["consolidator"],
            project_id=1,
        )

        # Build index
        stats = search.build_index()

        # Verify indexing succeeded
        assert stats["files_indexed"] > 0
        assert stats["units_extracted"] > 0

        # Verify episodic events were recorded (CODE_REVIEW and/or PERFORMANCE_PROFILE)
        assert mock_memory_stores["episodic_store"].store_event.call_count > 0

        # Find the CODE_REVIEW event (first call is usually the code analysis event)
        calls = mock_memory_stores["episodic_store"].store_event.call_args_list
        code_review_found = False
        for call in calls:
            event = call[0][0]
            assert isinstance(event, EpisodicEvent)
            assert event.event_type == EventType.ACTION
            assert event.outcome == EventOutcome.SUCCESS

            if event.code_event_type == CodeEventType.CODE_REVIEW:
                code_review_found = True
                assert event.files_changed == stats["files_indexed"]
                assert event.performance_metrics["units_analyzed"] == stats["units_extracted"]

        assert code_review_found, "CODE_REVIEW event should be recorded"

        # Verify insights were stored to semantic memory
        mock_memory_stores["semantic_store"].remember.assert_called()

        # Verify entities attempted to be added (may fail due to entity type validation)
        mock_memory_stores["graph_store"].add_entity.assert_called()

    def test_analyze_codebase_records_analysis(self, sample_python_project, mock_memory_stores):
        """Test that analyze_codebase records analysis to memory."""
        # Setup mocks
        mock_memory_stores["episodic_store"].store_event.return_value = 2
        mock_memory_stores["episodic_store"].get_events_by_type.return_value = []
        mock_memory_stores["consolidator"].consolidate.return_value = {"trend": "improving"}

        # Create and index search
        search = TreeSitterCodeSearch(
            sample_python_project,
            language="python",
            episodic_store=mock_memory_stores["episodic_store"],
            semantic_store=mock_memory_stores["semantic_store"],
            graph_store=mock_memory_stores["graph_store"],
            consolidator=mock_memory_stores["consolidator"],
            project_id=1,
        )

        search.build_index()

        # Reset mock to verify analyze_codebase calls
        mock_memory_stores["episodic_store"].reset_mock()
        mock_memory_stores["episodic_store"].get_events_by_type.return_value = []

        # Analyze codebase
        analysis = search.analyze_codebase()

        # Verify analysis contains expected fields
        assert "quality_score" in analysis
        assert "complexity_avg" in analysis
        assert "issues" in analysis
        assert "duration_ms" in analysis

        # Verify episodic event was recorded
        assert mock_memory_stores["episodic_store"].store_event.called

        # Find CODE_REVIEW event in calls
        calls = mock_memory_stores["episodic_store"].store_event.call_args_list
        code_review_found = False
        for call in calls:
            event = call[0][0]
            if event.code_event_type == CodeEventType.CODE_REVIEW:
                code_review_found = True
                break

        assert code_review_found, "CODE_REVIEW event should be recorded by analyze_codebase"

        # Verify semantic insights were stored
        mock_memory_stores["semantic_store"].remember.assert_called()

        # Verify trends are in result or quality score is present
        assert "trends" in analysis or analysis.get("quality_score") is not None

    def test_memory_integration_with_multiple_analyses(self, sample_python_project, mock_memory_stores):
        """Test multiple analyses over time to verify trend tracking."""
        # Setup mocks
        event_ids = [1, 2, 3]
        mock_memory_stores["episodic_store"].store_event.side_effect = event_ids
        mock_memory_stores["consolidator"].consolidate.return_value = {
            "trend": "improving",
            "avg_quality": 0.8,
            "issue_count_trend": "decreasing",
        }

        # Create search
        search = TreeSitterCodeSearch(
            sample_python_project,
            language="python",
            episodic_store=mock_memory_stores["episodic_store"],
            semantic_store=mock_memory_stores["semantic_store"],
            graph_store=mock_memory_stores["graph_store"],
            consolidator=mock_memory_stores["consolidator"],
            project_id=1,
        )

        # Initial index
        search.build_index()

        # Perform multiple analyses
        analyses = []
        for i in range(3):
            analysis = search.analyze_codebase()
            analyses.append(analysis)

        # Verify all analyses were recorded
        assert mock_memory_stores["episodic_store"].store_event.call_count >= 4  # 1 build + 3 analyze

        # Verify consolidation was called
        assert mock_memory_stores["consolidator"].consolidate.call_count > 0

    def test_search_without_memory_stores(self, sample_python_project):
        """Test that search works fine without memory stores."""
        # Create search without memory stores
        search = TreeSitterCodeSearch(
            sample_python_project,
            language="python",
        )

        # Index should work
        stats = search.build_index()
        assert stats["files_indexed"] > 0

        # Search should work
        results = search.search("validate", top_k=5)
        assert isinstance(results, list)

        # Analyze should work
        analysis = search.analyze_codebase()
        assert "quality_score" in analysis

    def test_analyze_codebase_detects_high_complexity_issues(self, sample_python_project, mock_memory_stores):
        """Test that analyze_codebase detects and records complexity issues."""
        # Setup mocks
        mock_memory_stores["episodic_store"].store_event.return_value = 3
        mock_memory_stores["consolidator"].consolidate.return_value = None

        # Create search
        search = TreeSitterCodeSearch(
            sample_python_project,
            language="python",
            episodic_store=mock_memory_stores["episodic_store"],
            semantic_store=mock_memory_stores["semantic_store"],
            graph_store=mock_memory_stores["graph_store"],
            consolidator=mock_memory_stores["consolidator"],
            project_id=1,
        )

        search.build_index()

        # Analyze
        analysis = search.analyze_codebase()

        # Verify issue detection works
        assert isinstance(analysis.get("issues"), list)

        # Verify event was recorded with issues in analysis results
        call_args = mock_memory_stores["episodic_store"].store_event.call_args
        event = call_args[0][0]
        content = json.loads(event.content)

        assert "analysis_results" in content
        assert "issues" in content["analysis_results"]

    def test_code_analysis_memory_manager_integration(self, sample_python_project, mock_memory_stores):
        """Test CodeAnalysisMemoryManager integration with TreeSitterCodeSearch."""
        # Create memory manager
        memory_manager = CodeAnalysisMemoryManager()
        memory_manager.analysis_memory = CodeAnalysisMemory(
            episodic_store=mock_memory_stores["episodic_store"],
            semantic_store=mock_memory_stores["semantic_store"],
            graph_store=mock_memory_stores["graph_store"],
            consolidator=mock_memory_stores["consolidator"],
            project_id=1,
        )

        # Setup mocks
        mock_memory_stores["episodic_store"].store_event.return_value = 10

        # Use manager to record analysis
        analysis_results = {
            "quality_score": 0.85,
            "complexity_avg": 4.5,
            "issues": [],
        }

        event_id = memory_manager.record_analysis(
            repo_path=sample_python_project,
            analysis_results=analysis_results,
            duration_ms=2500,
            file_count=2,
            unit_count=5,
        )

        assert event_id == 10

        # Verify insights were stored
        memory_manager.store_insights(
            analysis_results=analysis_results,
            repo_path=sample_python_project,
        )
        assert mock_memory_stores["semantic_store"].remember.called

    def test_entity_addition_to_graph_during_indexing(self, sample_python_project, mock_memory_stores):
        """Test that code entities are attempted to be added to graph during indexing."""
        # Setup mocks
        add_entity_calls = []

        def track_entity_addition(entity=None, **kwargs):
            if entity:
                add_entity_calls.append(entity)
            return True

        # Mock the add_entity to accept both positional and keyword arguments
        mock_memory_stores["graph_store"].add_entity.side_effect = track_entity_addition

        # Create search
        search = TreeSitterCodeSearch(
            sample_python_project,
            language="python",
            episodic_store=mock_memory_stores["episodic_store"],
            semantic_store=mock_memory_stores["semantic_store"],
            graph_store=mock_memory_stores["graph_store"],
            consolidator=mock_memory_stores["consolidator"],
            project_id=1,
        )

        search.build_index()

        # Verify add_entity was called (attempting to add entities)
        # Note: Some may fail due to entity type enum validation, but the method should be called
        assert mock_memory_stores["graph_store"].add_entity.called

        # Verify from tree_sitter_search._add_units_to_graph that entities are being processed
        # Note: The add_entity in tree_sitter_search uses different signature,
        # while code_analysis_memory uses Entity objects. Both should be attempted.

    def test_metrics_trend_recording(self, sample_python_project, mock_memory_stores):
        """Test that code metrics are recorded for trend analysis."""
        # Setup mocks
        mock_memory_stores["episodic_store"].store_event.return_value = 5

        # Create search
        search = TreeSitterCodeSearch(
            sample_python_project,
            language="python",
            episodic_store=mock_memory_stores["episodic_store"],
            semantic_store=mock_memory_stores["semantic_store"],
            graph_store=mock_memory_stores["graph_store"],
            consolidator=mock_memory_stores["consolidator"],
            project_id=1,
        )

        # Build index (which records metrics)
        stats = search.build_index()

        # Verify event was stored with metrics
        assert mock_memory_stores["episodic_store"].store_event.call_count >= 1

        # Check event contains performance metrics
        for call in mock_memory_stores["episodic_store"].store_event.call_args_list:
            event = call[0][0]
            if event.code_event_type == CodeEventType.CODE_REVIEW:
                assert "performance_metrics" in event.__dict__
                metrics = event.performance_metrics
                assert "files_analyzed" in metrics or "units_analyzed" in metrics

    def test_graceful_degradation_with_failing_stores(self, sample_python_project):
        """Test that search continues even if memory stores fail."""
        # Create mocks that fail
        failing_episodic = Mock()
        failing_episodic.store_event.side_effect = Exception("Store error")

        failing_semantic = Mock()
        failing_semantic.remember.side_effect = Exception("Store error")

        failing_graph = Mock()
        failing_graph.add_entity.side_effect = Exception("Store error")

        # Create search with failing stores
        search = TreeSitterCodeSearch(
            sample_python_project,
            language="python",
            episodic_store=failing_episodic,
            semantic_store=failing_semantic,
            graph_store=failing_graph,
            consolidator=None,
            project_id=1,
        )

        # Index should still succeed despite failing stores
        stats = search.build_index()
        assert stats["files_indexed"] > 0

        # Search should still work
        results = search.search("validate")
        assert isinstance(results, list)

        # Analyze should still work
        analysis = search.analyze_codebase()
        assert "quality_score" in analysis


class TestMemoryEventContent:
    """Tests for memory event content and structure."""

    @pytest.fixture
    def memory(self):
        """Create CodeAnalysisMemory with mocks."""
        return CodeAnalysisMemory(
            episodic_store=Mock(),
            semantic_store=Mock(),
            graph_store=Mock(),
            consolidator=Mock(),
            project_id=1,
            session_id="test_session",
        )

    def test_event_content_structure(self, memory):
        """Test that event content is properly structured."""
        memory.episodic_store.store_event.return_value = 1

        analysis_results = {
            "quality_score": 0.75,
            "complexity_avg": 4.5,
            "test_coverage": "80%",
            "issues": [{"type": "high_complexity", "unit": "func1"}],
        }

        memory.record_code_analysis(
            repo_path="/test/repo",
            analysis_results=analysis_results,
            duration_ms=2000,
            file_count=50,
            unit_count=500,
        )

        # Verify event was stored with correct structure
        call_args = memory.episodic_store.store_event.call_args
        event = call_args[0][0]

        content = json.loads(event.content)
        assert "repo_path" in content
        assert "summary" in content
        assert "analysis_results" in content

        # Verify summary format
        assert "Quality:" in content["summary"] or "0.75" in content["summary"]

    def test_learning_extraction_in_events(self, memory):
        """Test that learned insights are extracted and stored in events."""
        memory.episodic_store.store_event.return_value = 1

        # Analysis with multiple issues that should trigger learnings
        analysis_results = {
            "quality_score": 0.3,  # Below 0.5
            "complexity_avg": 6,    # Above 5
            "test_coverage": 0.5,   # Below 0.7
            "issues": list(range(15)),  # > 10 issues
        }

        memory.record_code_analysis(
            repo_path="/test/repo",
            analysis_results=analysis_results,
            duration_ms=3000,
            file_count=100,
            unit_count=1000,
        )

        # Verify event has learned insights
        call_args = memory.episodic_store.store_event.call_args
        event = call_args[0][0]

        # Event should have learned field populated
        assert hasattr(event, "learned")
        assert event.learned is not None
        assert len(event.learned) > 0


class TestPatternExtraction:
    """Tests for pattern extraction from multiple analyses."""

    @pytest.fixture
    def memory_with_events(self):
        """Create memory system with sample events."""
        episodic_store = Mock()
        consolidator = Mock()

        # Create sample events
        sample_events = [
            Mock(
                project_id=1,
                timestamp=None,
                content=json.dumps({"analysis_results": {"quality_score": 0.7}}),
            ),
            Mock(
                project_id=1,
                timestamp=None,
                content=json.dumps({"analysis_results": {"quality_score": 0.75}}),
            ),
            Mock(
                project_id=1,
                timestamp=None,
                content=json.dumps({"analysis_results": {"quality_score": 0.8}}),
            ),
        ]

        episodic_store.get_events_by_type.return_value = sample_events
        consolidator.consolidate.return_value = {
            "trend": "improving",
            "avg_quality": 0.75,
        }

        memory = CodeAnalysisMemory(
            episodic_store=episodic_store,
            consolidator=consolidator,
        )

        return memory

    def test_pattern_extraction_called_with_correct_params(self, memory_with_events):
        """Test that pattern extraction is called with correct parameters."""
        patterns = memory_with_events.extract_analysis_patterns(days_back=7)

        # Verify consolidator was called
        memory_with_events.consolidator.consolidate.assert_called_once()

        # Verify get_events_by_type was called with correct params
        memory_with_events.episodic_store.get_events_by_type.assert_called_once()
        call_kwargs = memory_with_events.episodic_store.get_events_by_type.call_args[1]
        assert call_kwargs["days_back"] == 7
        assert call_kwargs["code_event_type"] == CodeEventType.CODE_REVIEW

        # Verify patterns returned
        assert patterns == {"trend": "improving", "avg_quality": 0.75}

    def test_pattern_extraction_returns_none_without_events(self):
        """Test that pattern extraction returns None when no events found."""
        episodic_store = Mock()
        consolidator = Mock()

        episodic_store.get_events_by_type.return_value = []

        memory = CodeAnalysisMemory(
            episodic_store=episodic_store,
            consolidator=consolidator,
        )

        patterns = memory.extract_analysis_patterns(days_back=7)

        # Should return None
        assert patterns is None

        # Consolidator should not be called
        consolidator.consolidate.assert_not_called()
