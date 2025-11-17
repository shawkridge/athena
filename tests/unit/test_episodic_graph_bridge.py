"""Unit tests for Episodic→Graph integration bridge."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from athena.episodic.models import EpisodicEvent, EventContext, EventType, EventOutcome
from athena.graph.models import EntityType, RelationType
from athena.integration.episodic_graph_bridge import EpisodicGraphBridge
from athena.integration.causality_detector import EventSignature, CausalLink, CausalityType


def create_test_event(**kwargs):
    """Helper to create valid test events."""
    defaults = {
        "project_id": 1,
        "session_id": "test_session",
        "timestamp": datetime.now(),
        "event_type": EventType.ACTION,
        "content": "Test event",
        "outcome": EventOutcome.SUCCESS,
    }
    defaults.update(kwargs)
    return EpisodicEvent(**defaults)


class TestEpisodicGraphBridge:
    """Test Episodic→Graph bridge integration."""

    def test_initialization(self):
        """Test bridge initialization."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        assert bridge.db is mock_db
        assert bridge.episodic_store is not None
        assert bridge.graph_store is not None
        assert bridge.causality_detector is not None

    def test_event_type_to_entity_type_mapping(self):
        """Test event type to entity type mapping."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Test mappings
        assert bridge._event_type_to_entity_type("action") == EntityType.TASK
        assert bridge._event_type_to_entity_type("error") == EntityType.CONCEPT
        assert bridge._event_type_to_entity_type("file_change") == EntityType.FILE
        assert bridge._event_type_to_entity_type("decision") == EntityType.DECISION
        assert bridge._event_type_to_entity_type("test_run") == EntityType.TASK
        assert bridge._event_type_to_entity_type("unknown") == EntityType.CONCEPT

    def test_event_to_signature_conversion(self):
        """Test converting episodic event to causality signature."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Create test event
        now = datetime.now()
        context = EventContext(
            task="task_1",
            phase="executing",
        )
        event = create_test_event(
            id=1,
            timestamp=now,
            event_type=EventType.TEST_RUN,
            outcome=EventOutcome.SUCCESS,
            context=context,
            content="Test passed",
        )

        signature = bridge._event_to_signature(event)

        assert signature.event_id == 1
        assert signature.event_type == EventType.TEST_RUN
        assert signature.outcome == EventOutcome.SUCCESS
        assert signature.task == "task_1"
        assert signature.phase == "executing"
        assert signature.has_test_result is True
        assert signature.test_passed is True

    def test_causality_to_relation_type_mapping(self):
        """Test causality type to relation type mapping."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Test mappings
        assert (
            bridge._causality_to_relation_type(CausalityType.DIRECT_CAUSE)
            == RelationType.CAUSED_BY
        )
        assert (
            bridge._causality_to_relation_type(CausalityType.CONTRIBUTING_FACTOR)
            == RelationType.DEPENDS_ON
        )
        assert (
            bridge._causality_to_relation_type(CausalityType.TEMPORAL_CORRELATION)
            == RelationType.RELATES_TO
        )
        assert (
            bridge._causality_to_relation_type(CausalityType.CODE_CHANGE_EFFECT)
            == RelationType.RESULTED_IN
        )

    def test_event_entity_caching(self):
        """Test event-to-entity ID caching."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Populate cache
        bridge._event_entity_cache[1] = 100
        bridge._event_entity_cache[2] = 101

        # Verify cache works
        assert bridge._event_entity_cache.get(1) == 100
        assert bridge._event_entity_cache.get(2) == 101
        assert bridge._event_entity_cache.get(999) is None

    @patch("athena.integration.episodic_graph_bridge.logger")
    def test_integrate_events_to_graph_empty(self, mock_logger):
        """Test integration with no events."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Mock empty event list
        bridge._get_recent_unintegrated_events = Mock(return_value=[])

        result = bridge.integrate_events_to_graph()

        assert result["status"] == "success"
        assert result["events_processed"] == 0
        assert result["entities_created"] == 0
        assert result["causal_relations_created"] == 0

    @patch("athena.integration.episodic_graph_bridge.logger")
    def test_integrate_events_to_graph_with_events(self, mock_logger):
        """Test integration with multiple events."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Create test events
        now = datetime.now()
        events = [
            create_test_event(
                id=1,
                timestamp=now - timedelta(minutes=5),
                event_type=EventType.FILE_CHANGE,
                outcome=EventOutcome.SUCCESS,
                content="Changed auth module",
            ),
            create_test_event(
                id=2,
                timestamp=now,
                event_type=EventType.TEST_RUN,
                outcome=EventOutcome.SUCCESS,
                content="Tests passed",
            ),
        ]

        # Mock the methods
        bridge._get_recent_unintegrated_events = Mock(return_value=events)
        bridge._create_entity_from_event = Mock(side_effect=[1, 2])
        bridge._event_to_signature = Mock(side_effect=[
            EventSignature(
                event_id=1,
                timestamp=int((now - timedelta(minutes=5)).timestamp() * 1000),
                event_type=EventType.FILE_CHANGE,
                outcome=EventOutcome.SUCCESS,
            ),
            EventSignature(
                event_id=2,
                timestamp=int(now.timestamp() * 1000),
                event_type=EventType.TEST_RUN,
                outcome=EventOutcome.SUCCESS,
            ),
        ])

        # Mock causality detection
        causal_link = CausalLink(
            source_event_id=1,
            target_event_id=2,
            causality_type=CausalityType.DIRECT_CAUSE,
            confidence=0.85,
            reasoning="Code change caused test",
            temporal_proximity_ms=5 * 60 * 1000,
            shared_context_score=0.7,
            code_signal_strength=0.9,
        )
        bridge.causality_detector.detect_causality_chains = Mock(return_value=[causal_link])
        bridge._create_causal_relation = Mock(return_value=True)

        result = bridge.integrate_events_to_graph()

        assert result["status"] == "success"
        assert result["events_processed"] == 2
        assert result["entities_created"] == 2
        assert result["causal_relations_created"] == 1
        assert result["causal_link_confidence_avg"] == 0.85

    def test_create_entity_from_event(self):
        """Test creating a graph entity from an episodic event."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Mock graph store
        bridge.graph_store.create_entity = Mock(return_value=42)
        bridge._mark_event_integrated = Mock()

        # Create test event
        event = create_test_event(
            id=10,
            timestamp=datetime.now(),
            event_type=EventType.FILE_CHANGE,
            outcome=EventOutcome.SUCCESS,
            content="Updated authentication module",
        )

        entity_id = bridge._create_entity_from_event(event)

        assert entity_id == 42
        bridge.graph_store.create_entity.assert_called_once()
        bridge._mark_event_integrated.assert_called_once_with(10)

    def test_create_causal_relation(self):
        """Test creating a causal relation in the graph."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Populate cache
        bridge._event_entity_cache[1] = 100
        bridge._event_entity_cache[2] = 101

        # Mock graph store
        bridge.graph_store.create_relation = Mock()

        # Create test causal link
        link = CausalLink(
            source_event_id=1,
            target_event_id=2,
            causality_type=CausalityType.DIRECT_CAUSE,
            confidence=0.85,
            reasoning="Code change caused test failure",
            temporal_proximity_ms=300000,  # 5 minutes
            shared_context_score=0.7,
            code_signal_strength=0.9,
        )

        result = bridge._create_causal_relation(link)

        assert result is True
        bridge.graph_store.create_relation.assert_called_once()

        # Verify the relation was created with correct data
        call_args = bridge.graph_store.create_relation.call_args[0]
        relation = call_args[0]
        assert relation.from_entity_id == 100
        assert relation.to_entity_id == 101
        assert relation.strength == 0.85
        assert relation.confidence == 0.85

    def test_create_causal_relation_missing_entities(self):
        """Test handling missing entities when creating causal relation."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Create link for non-existent entities
        link = CausalLink(
            source_event_id=999,
            target_event_id=998,
            causality_type=CausalityType.DIRECT_CAUSE,
            confidence=0.85,
            reasoning="Test",
            temporal_proximity_ms=100,
            shared_context_score=0.5,
            code_signal_strength=0.5,
        )

        result = bridge._create_causal_relation(link)

        assert result is False

    def test_query_event_causality_chain(self):
        """Test querying causality chain for an event."""
        mock_db = Mock()
        bridge = EpisodicGraphBridge(mock_db)

        # Populate cache
        bridge._event_entity_cache[1] = 100

        # Mock traverse method
        chain_data = {
            "causes": [
                {
                    "source": "Code change",
                    "type": "causes",
                    "description": "Code change led to test",
                    "confidence": 0.85,
                }
            ],
            "effects": [
                {
                    "target": "Success message",
                    "type": "causes",
                    "description": "Test success",
                    "confidence": 0.9,
                }
            ],
        }
        bridge._traverse_causal_chain = Mock(return_value=chain_data)

        result = bridge.query_event_causality_chain(1, depth=3)

        assert result["status"] == "success"
        assert result["event_id"] == 1
        assert result["causality_chain"] == chain_data
        bridge._traverse_causal_chain.assert_called_once_with(100, 3)

    def test_query_event_causality_chain_not_found(self):
        """Test querying causality chain when event not found."""
        mock_db = Mock()
        mock_db.get_cursor = Mock()
        cursor = Mock()
        cursor.fetchone = Mock(return_value=None)
        mock_db.get_cursor.return_value = cursor
        mock_db.conn = Mock()

        bridge = EpisodicGraphBridge(mock_db)

        result = bridge.query_event_causality_chain(999, depth=3)

        assert result["status"] == "error"
        assert "Entity not found" in result["error"]
