"""Tests for episodic memory tools (record_event, recall_events, get_timeline)."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta
from athena.mcp.tools.episodic_tools import (
    RecordEventTool,
    RecallEventsTool,
    GetTimelineTool,
)
from athena.mcp.tools.base import ToolStatus


@pytest.fixture
def mock_episodic_store():
    """Create mock episodic store."""
    store = Mock()
    store.record_event = Mock(return_value=1)
    store.get_recent_events = Mock(return_value=[])
    store.search_events = Mock(return_value=[])
    store.get_events_by_type = Mock(return_value=[])
    store.get_events_by_date = Mock(return_value=[])
    return store


@pytest.fixture
def mock_project_manager():
    """Create mock project manager."""
    manager = Mock()
    mock_project = Mock()
    mock_project.id = 1
    mock_project.name = "test_project"
    manager.get_or_create_project = Mock(return_value=mock_project)
    manager.require_project = Mock(return_value=mock_project)
    return manager


@pytest.fixture
def record_event_tool(mock_episodic_store, mock_project_manager):
    """Create record event tool instance."""
    return RecordEventTool(mock_episodic_store, mock_project_manager)


@pytest.fixture
def recall_events_tool(mock_episodic_store, mock_project_manager):
    """Create recall events tool instance."""
    return RecallEventsTool(mock_episodic_store, mock_project_manager)


@pytest.fixture
def timeline_tool(mock_episodic_store, mock_project_manager):
    """Create timeline tool instance."""
    return GetTimelineTool(mock_episodic_store, mock_project_manager)


class TestRecordEventTool:
    """Test RecordEventTool functionality."""

    @pytest.mark.asyncio
    async def test_record_event_missing_content(self, record_event_tool):
        """Test record event with missing content parameter."""
        result = await record_event_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Missing required parameter" in result.error

    @pytest.mark.asyncio
    async def test_record_event_basic(self, record_event_tool, mock_episodic_store):
        """Test basic event recording."""
        mock_episodic_store.record_event.return_value = 42

        result = await record_event_tool.execute(
            content="Test event content"
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.data["event_id"] == 42
        assert "session_" in result.data["session_id"]

    @pytest.mark.asyncio
    async def test_record_event_with_type(self, record_event_tool, mock_episodic_store):
        """Test recording event with specific type."""
        mock_episodic_store.record_event.return_value = 42

        result = await record_event_tool.execute(
            content="Test",
            event_type="decision"
        )
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_record_event_with_outcome(self, record_event_tool, mock_episodic_store):
        """Test recording event with outcome."""
        mock_episodic_store.record_event.return_value = 42

        result = await record_event_tool.execute(
            content="Test",
            outcome="success"
        )
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_record_event_with_context(self, record_event_tool, mock_episodic_store):
        """Test recording event with context."""
        mock_episodic_store.record_event.return_value = 42

        result = await record_event_tool.execute(
            content="Test",
            context={
                "cwd": "/home/user",
                "files": ["file1.py", "file2.py"],
                "task": "implementation",
                "phase": "coding"
            }
        )
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_record_event_project_error(self, record_event_tool, mock_project_manager):
        """Test record event when project lookup fails."""
        mock_project_manager.get_or_create_project.side_effect = Exception("No project")

        result = await record_event_tool.execute(content="Test")
        assert result.status == ToolStatus.ERROR
        assert "Project error" in result.error

    @pytest.mark.asyncio
    async def test_record_event_storage_error(self, record_event_tool, mock_episodic_store):
        """Test record event when storage fails."""
        mock_episodic_store.record_event.side_effect = Exception("Storage error")

        result = await record_event_tool.execute(content="Test")
        assert result.status == ToolStatus.ERROR
        assert "Recording failed" in result.error


class TestRecallEventsTool:
    """Test RecallEventsTool functionality."""

    @pytest.mark.asyncio
    async def test_recall_events_no_results(self, recall_events_tool, mock_episodic_store):
        """Test recall when no events found."""
        mock_episodic_store.get_recent_events.return_value = []

        result = await recall_events_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 0

    @pytest.mark.asyncio
    async def test_recall_events_with_results(self, recall_events_tool, mock_episodic_store):
        """Test recall with successful results."""
        # Mock event
        mock_event = Mock()
        mock_event.id = 1
        mock_event.timestamp = datetime.now()
        mock_event.event_type = Mock(value="action")
        mock_event.content = "Test event content"
        mock_event.outcome = None

        mock_episodic_store.get_recent_events.return_value = [mock_event]

        result = await recall_events_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 1
        assert len(result.data["events"]) == 1

    @pytest.mark.asyncio
    async def test_recall_events_with_timeframe(self, recall_events_tool, mock_episodic_store):
        """Test recall with timeframe filter."""
        mock_episodic_store.get_recent_events.return_value = []

        result = await recall_events_tool.execute(timeframe="this_week")
        assert result.status == ToolStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_recall_events_with_query(self, recall_events_tool, mock_episodic_store):
        """Test recall with search query."""
        mock_episodic_store.search_events.return_value = []

        result = await recall_events_tool.execute(query="test search")
        assert result.status == ToolStatus.SUCCESS

        # Verify search was called
        mock_episodic_store.search_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall_events_with_type_filter(self, recall_events_tool, mock_episodic_store):
        """Test recall with event type filter."""
        mock_episodic_store.get_events_by_type.return_value = []

        result = await recall_events_tool.execute(event_type="decision")
        assert result.status == ToolStatus.SUCCESS

        # Verify get_events_by_type was called
        mock_episodic_store.get_events_by_type.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall_events_with_limit(self, recall_events_tool, mock_episodic_store):
        """Test recall respects limit parameter."""
        mock_episodic_store.get_recent_events.return_value = []

        result = await recall_events_tool.execute(limit=25)
        assert result.status == ToolStatus.SUCCESS

        # Verify limit was passed
        call_args = mock_episodic_store.get_recent_events.call_args
        assert call_args[1]["limit"] == 25

    @pytest.mark.asyncio
    async def test_recall_events_project_error(self, recall_events_tool, mock_project_manager):
        """Test recall when project lookup fails."""
        mock_project_manager.require_project.side_effect = Exception("No project")

        result = await recall_events_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Project error" in result.error


class TestGetTimelineTool:
    """Test GetTimelineTool functionality."""

    @pytest.mark.asyncio
    async def test_timeline_no_events(self, timeline_tool, mock_episodic_store):
        """Test timeline with no events."""
        mock_episodic_store.get_recent_events.return_value = []

        result = await timeline_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 0

    @pytest.mark.asyncio
    async def test_timeline_with_events(self, timeline_tool, mock_episodic_store):
        """Test timeline with events."""
        # Mock event
        mock_event = Mock()
        mock_event.timestamp = datetime.now()
        mock_event.event_type = Mock(value="action")
        mock_event.content = "Test event content"

        mock_episodic_store.get_recent_events.return_value = [mock_event]

        result = await timeline_tool.execute()
        assert result.status == ToolStatus.SUCCESS
        assert result.data["count"] == 1
        assert result.data["period_days"] == 7

    @pytest.mark.asyncio
    async def test_timeline_custom_days(self, timeline_tool, mock_episodic_store):
        """Test timeline with custom day count."""
        mock_episodic_store.get_recent_events.return_value = []

        result = await timeline_tool.execute(days=30)
        assert result.status == ToolStatus.SUCCESS
        assert result.data["period_days"] == 30

    @pytest.mark.asyncio
    async def test_timeline_custom_limit(self, timeline_tool, mock_episodic_store):
        """Test timeline with custom limit."""
        mock_episodic_store.get_recent_events.return_value = []

        result = await timeline_tool.execute(limit=50)
        assert result.status == ToolStatus.SUCCESS

        # Verify limit was passed
        call_args = mock_episodic_store.get_recent_events.call_args
        assert call_args[1]["limit"] == 50

    @pytest.mark.asyncio
    async def test_timeline_project_error(self, timeline_tool, mock_project_manager):
        """Test timeline when project lookup fails."""
        mock_project_manager.require_project.side_effect = Exception("No project")

        result = await timeline_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Project error" in result.error

    @pytest.mark.asyncio
    async def test_timeline_retrieval_error(self, timeline_tool, mock_episodic_store):
        """Test timeline when retrieval fails."""
        mock_episodic_store.get_recent_events.side_effect = Exception("Retrieval error")

        result = await timeline_tool.execute()
        assert result.status == ToolStatus.ERROR
        assert "Retrieval failed" in result.error


class TestEpisodicToolsMetadata:
    """Test metadata for episodic tools."""

    def test_record_event_metadata(self, record_event_tool):
        """Test record event tool metadata."""
        assert record_event_tool.metadata.name == "record_event"
        assert "record" in record_event_tool.metadata.tags
        assert record_event_tool.metadata.category == "episodic"

    def test_recall_events_metadata(self, recall_events_tool):
        """Test recall events tool metadata."""
        assert recall_events_tool.metadata.name == "recall_events"
        assert "query" in recall_events_tool.metadata.tags
        assert recall_events_tool.metadata.category == "episodic"

    def test_timeline_metadata(self, timeline_tool):
        """Test timeline tool metadata."""
        assert timeline_tool.metadata.name == "get_timeline"
        assert "timeline" in timeline_tool.metadata.tags
        assert timeline_tool.metadata.category == "episodic"

    def test_record_event_parameters(self, record_event_tool):
        """Test record event parameters."""
        params = record_event_tool.metadata.parameters
        assert "content" in params
        assert "event_type" in params
        assert "outcome" in params
        assert "context" in params

    def test_recall_events_parameters(self, recall_events_tool):
        """Test recall events parameters."""
        params = recall_events_tool.metadata.parameters
        assert "timeframe" in params
        assert "query" in params
        assert "event_type" in params
        assert "limit" in params

    def test_timeline_parameters(self, timeline_tool):
        """Test timeline parameters."""
        params = timeline_tool.metadata.parameters
        assert "days" in params
        assert "limit" in params
