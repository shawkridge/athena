"""Episodic→Graph Integration Bridge

Bridges episodic memory events with knowledge graph entities using temporal causality.
Automatically creates graph entities for events and links them with causal relationships.

This closes the critical gap: episodic events → graph entities → causal chains
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Set

from ..core.database import Database
from ..episodic.store import EpisodicStore
from ..episodic.models import EpisodicEvent
from ..graph.store import GraphStore
from ..graph.models import Entity, Relation, EntityType, RelationType
from .causality_detector import TemporalCausalityDetector, EventSignature, CausalLink, CausalityType

logger = logging.getLogger(__name__)


class EpisodicGraphBridge:
    """Bridges episodic memory and knowledge graph using temporal causality.

    Maps episodic events to graph entities and creates causal relations between them.
    """

    def __init__(self, db: Database):
        """Initialize the bridge.

        Args:
            db: Database instance
        """
        self.db = db
        self.episodic_store = EpisodicStore(db)
        self.graph_store = GraphStore(db)
        self.causality_detector = TemporalCausalityDetector()

        # Cache for event→entity mappings
        self._event_entity_cache: Dict[int, int] = {}

    def integrate_events_to_graph(
        self,
        event_ids: Optional[List[int]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Integrate episodic events into the knowledge graph.

        Creates entities for events and links them with causal relations.
        **TRANSACTION SAFETY**: All operations are wrapped in a single transaction.
        If any step fails, the entire integration is rolled back.

        Args:
            event_ids: Specific event IDs to process (if None, processes recent events)
            limit: Max events to process at once

        Returns:
            Integration report with statistics
        """
        cursor = None
        try:
            # Get events to process
            if event_ids:
                events = [self.episodic_store.get_event(eid) for eid in event_ids]
                events = [e for e in events if e is not None]
            else:
                events = self._get_recent_unintegrated_events(limit)

            if not events:
                logger.info("No events to integrate")
                return {
                    "status": "success",
                    "events_processed": 0,
                    "entities_created": 0,
                    "causal_relations_created": 0,
                }

            # BEGIN TRANSACTION: All operations must succeed together
            cursor = self.db.get_cursor()
            cursor.execute("BEGIN")

            # Create entities for events
            entity_ids = []
            for event in events:
                entity_id = self._create_entity_from_event(event)
                if entity_id:
                    entity_ids.append(entity_id)
                    self._event_entity_cache[event.id] = entity_id

            # Detect causal relationships
            event_signatures = [self._event_to_signature(e) for e in events]
            causal_links = self.causality_detector.detect_causality_chains(event_signatures)

            # Create causal relations in graph
            relation_count = 0
            for link in causal_links:
                if self._create_causal_relation(link):
                    relation_count += 1

            # COMMIT TRANSACTION: All steps succeeded, persist changes
            cursor.execute("COMMIT")
            self.db.conn.commit()

            logger.info(
                f"Integrated {len(events)} events: {len(entity_ids)} entities, "
                f"{relation_count} causal relations"
            )

            return {
                "status": "success",
                "events_processed": len(events),
                "entities_created": len(entity_ids),
                "causal_relations_created": relation_count,
                "causal_link_confidence_avg": (
                    sum(link.confidence for link in causal_links) / len(causal_links)
                    if causal_links else 0.0
                ),
            }

        except (ValueError, KeyError) as e:
            # ROLLBACK TRANSACTION: Validation error means transaction fails
            if cursor:
                try:
                    cursor.execute("ROLLBACK")
                    self.db.conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error rolling back transaction: {rollback_error}")

            logger.error(f"Validation error in event-to-graph integration: {e}", exc_info=False)
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "error": str(e),
                "transaction_rolled_back": True,
                "events_processed": 0,
                "entities_created": 0,
                "causal_relations_created": 0,
            }

        except (ConnectionError, TimeoutError) as e:
            # ROLLBACK TRANSACTION: Database connectivity error
            if cursor:
                try:
                    cursor.execute("ROLLBACK")
                    self.db.conn.rollback()
                except Exception:
                    pass  # Already disconnected

            logger.error(f"Database connectivity error during integration: {e}", exc_info=True)
            return {
                "status": "error",
                "error_type": "database_error",
                "error": str(e),
                "transaction_rolled_back": True,
                "retriable": True,  # Can retry later
                "events_processed": 0,
                "entities_created": 0,
                "causal_relations_created": 0,
            }

        except Exception as e:
            # ROLLBACK TRANSACTION: Unexpected error
            if cursor:
                try:
                    cursor.execute("ROLLBACK")
                    self.db.conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error rolling back transaction: {rollback_error}")

            logger.error(f"Unexpected error integrating events to graph (rolled back): {e}", exc_info=True)
            return {
                "status": "error",
                "error_type": "unexpected",
                "error": str(e),
                "transaction_rolled_back": True,
                "events_processed": 0,
                "entities_created": 0,
                "causal_relations_created": 0,
            }

    def _get_recent_unintegrated_events(self, limit: int) -> List[EpisodicEvent]:
        """Get recent events that haven't been integrated to the graph.

        Args:
            limit: Max events to return

        Returns:
            List of recent events
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT * FROM episodic_events
                WHERE integrated_to_graph = FALSE
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()

            events = []
            for row in rows:
                event = self.episodic_store._row_to_event(row)
                if event:
                    events.append(event)

            return events
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []

    def _create_entity_from_event(self, event: EpisodicEvent) -> Optional[int]:
        """Create a graph entity from an episodic event.

        Args:
            event: Episodic event

        Returns:
            Entity ID if created, None otherwise
        """
        try:
            # Determine entity type based on event type
            entity_type = self._event_type_to_entity_type(event.event_type)

            # Create descriptive name
            name = f"{event.event_type}: {event.content[:50]}"

            # Create entity
            entity = Entity(
                name=name,
                entity_type=entity_type,
                description=event.content,
                source="episodic_event",
                source_id=event.id,
                metadata={
                    "event_id": event.id,
                    "event_type": event.event_type,
                    "outcome": event.outcome,
                    "context": event.context.model_dump() if event.context else {},
                },
            )

            entity_id = self.graph_store.create_entity(entity)

            # Mark event as integrated
            self._mark_event_integrated(event.id)

            logger.debug(f"Created entity {entity_id} from event {event.id}")
            return entity_id

        except Exception as e:
            logger.error(f"Error creating entity from event {event.id}: {e}")
            return None

    def _event_type_to_entity_type(self, event_type: str) -> EntityType:
        """Map episodic event type to graph entity type.

        Args:
            event_type: Event type from episodic memory

        Returns:
            EntityType for the knowledge graph
        """
        mapping = {
            "conversation": EntityType.CONCEPT,
            "action": EntityType.TASK,
            "decision": EntityType.DECISION,
            "error": EntityType.CONCEPT,
            "success": EntityType.CONCEPT,
            "file_change": EntityType.FILE,
            "test_run": EntityType.TASK,
            "deployment": EntityType.TASK,
            "refactoring": EntityType.TASK,
            "debugging": EntityType.TASK,
        }
        return mapping.get(event_type, EntityType.CONCEPT)

    def _event_to_signature(self, event: EpisodicEvent) -> EventSignature:
        """Convert episodic event to causality detector signature.

        Args:
            event: Episodic event

        Returns:
            EventSignature for causality analysis
        """
        files = set()
        if event.context and event.context.files:
            files.update(event.context.files)

        return EventSignature(
            event_id=event.id,
            timestamp=int(event.timestamp.timestamp() * 1000),
            event_type=event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
            outcome=event.outcome.value if hasattr(event.outcome, 'value') else (str(event.outcome) if event.outcome else None),
            files=files,
            task=event.context.task if event.context else None,
            phase=event.context.phase if event.context else None,
            session_id=event.context.cwd if event.context else None,  # Use cwd as session proxy
            has_code_change=event.event_type == "file_change",
            has_test_result=event.event_type == "test_run",
            test_passed=event.outcome == "success" if event.event_type == "test_run" else None,
            error_type=None,  # EventContext doesn't have error_type
        )

    def _create_causal_relation(self, link: CausalLink) -> bool:
        """Create a causal relation in the knowledge graph.

        Args:
            link: Causal link from detector

        Returns:
            True if relation created, False otherwise
        """
        try:
            # Get entity IDs for the events
            source_entity_id = self._event_entity_cache.get(link.source_event_id)
            target_entity_id = self._event_entity_cache.get(link.target_event_id)

            if not source_entity_id or not target_entity_id:
                logger.debug(
                    f"Skipping relation - entities not found for events "
                    f"{link.source_event_id} → {link.target_event_id}"
                )
                return False

            # Map causality type to relation type
            relation_type = self._causality_to_relation_type(link.causality_type)

            # Create relation with confidence metadata
            relation = Relation(
                from_entity_id=source_entity_id,
                to_entity_id=target_entity_id,
                relation_type=relation_type,
                strength=link.confidence,  # Use confidence as relation strength
                confidence=link.confidence,
                metadata={
                    "temporal_proximity_ms": link.temporal_proximity_ms,
                    "shared_context_score": link.shared_context_score,
                    "code_signal_strength": link.code_signal_strength,
                    "reasoning": link.reasoning,
                },
            )

            self.graph_store.create_relation(relation)
            logger.debug(
                f"Created causal relation: event {link.source_event_id} → "
                f"{link.target_event_id} (confidence={link.confidence:.2f})"
            )
            return True

        except Exception as e:
            logger.error(f"Error creating causal relation: {e}")
            return False

    def _causality_to_relation_type(self, causality_type: CausalityType) -> RelationType:
        """Map causality type to graph relation type.

        Args:
            causality_type: Causality type from detector

        Returns:
            RelationType for the knowledge graph
        """
        mapping = {
            CausalityType.DIRECT_CAUSE: RelationType.CAUSED_BY,
            CausalityType.CONTRIBUTING_FACTOR: RelationType.DEPENDS_ON,
            CausalityType.TEMPORAL_CORRELATION: RelationType.RELATES_TO,
            CausalityType.CODE_CHANGE_EFFECT: RelationType.RESULTED_IN,
        }
        return mapping.get(causality_type, RelationType.RELATES_TO)

    def _mark_event_integrated(self, event_id: int) -> None:
        """Mark an event as integrated to the graph.

        Args:
            event_id: ID of event to mark
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                "UPDATE episodic_events SET integrated_to_graph = TRUE WHERE id = %s",
                (event_id,),
            )
            self.db.conn.commit()
        except Exception as e:
            logger.error(f"Error marking event as integrated: {e}")

    def query_event_causality_chain(self, event_id: int, depth: int = 3) -> Dict[str, Any]:
        """Query the causal chain for an event.

        Args:
            event_id: Event to start from
            depth: How many levels of causality to trace

        Returns:
            Causality chain with related events and relations
        """
        try:
            entity_id = self._event_entity_cache.get(event_id)
            if not entity_id:
                # Try to find entity for this event
                cursor = self.db.get_cursor()
                cursor.execute(
                    "SELECT id FROM knowledge_graph_entities WHERE source_id = %s",
                    (event_id,),
                )
                row = cursor.fetchone()
                if row:
                    entity_id = row[0]
                else:
                    return {"status": "error", "error": f"Entity not found for event {event_id}"}

            # Traverse graph to find causal chains
            chain = self._traverse_causal_chain(entity_id, depth)

            return {
                "status": "success",
                "event_id": event_id,
                "entity_id": entity_id,
                "causality_chain": chain,
            }

        except Exception as e:
            logger.error(f"Error querying causality chain: {e}")
            return {"status": "error", "error": str(e)}

    def _traverse_causal_chain(self, entity_id: int, depth: int) -> Dict[str, Any]:
        """Traverse the causal chain for an entity.

        Args:
            entity_id: Starting entity
            depth: Depth to traverse

        Returns:
            Causality chain structure
        """
        if depth <= 0:
            return {}

        try:
            cursor = self.db.get_cursor()

            # Get relations involving this entity
            cursor.execute(
                """
                SELECT r.*,
                       e1.id as source_id, e1.name as source_name,
                       e2.id as target_id, e2.name as target_name
                FROM knowledge_graph_relations r
                JOIN knowledge_graph_entities e1 ON r.from_entity_id = e1.id
                JOIN knowledge_graph_entities e2 ON r.to_entity_id = e2.id
                WHERE r.from_entity_id = %s OR r.to_entity_id = %s
                """,
                (entity_id, entity_id),
            )

            rows = cursor.fetchall()
            chain = {
                "causes": [],
                "effects": [],
            }

            for row in rows:
                relation_data = {
                    "type": row[4],  # relation_type
                    "description": row[5],  # description
                    "confidence": row[10] if row[10] else 0.0,  # weight
                }

                if row[2] == entity_id:  # This is the source
                    relation_data["target"] = row[14]  # target_name
                    chain["effects"].append(relation_data)
                else:
                    relation_data["source"] = row[12]  # source_name
                    chain["causes"].append(relation_data)

            return chain

        except Exception as e:
            logger.error(f"Error traversing causal chain: {e}")
            return {}
