"""
Extract entities from episodic events and populate knowledge graph.

Consolidates episodic memory into knowledge graph entities through:
1. NLP extraction of named entities and concepts
2. Temporal clustering of related events
3. Entity deduplication and merging
4. Relationship inference
"""

import json
import logging
from typing import Dict, Any, List, Set
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class EpisodicGraphExtractor:
    """Extract knowledge graph entities from episodic events."""

    def __init__(self, db):
        """Initialize extractor.

        Args:
            db: Database instance
        """
        self.db = db

    def extract_and_populate(
        self,
        project_id: int,
        hours_back: int = 24,
        min_events: int = 3
    ) -> Dict[str, Any]:
        """Extract entities from episodic events and populate graph.

        Args:
            project_id: Project ID
            hours_back: Hours of events to process
            min_events: Minimum events to trigger consolidation

        Returns:
            Consolidation statistics
        """
        try:
            from ..graph.store import GraphStore
            from ..graph.models import Entity, EntityType, Relation, RelationType, Observation

            # Get recent episodic events
            cutoff_time = int((datetime.now() - timedelta(hours=hours_back)).timestamp())

            events = self.db.query(
                """
                SELECT id, content, event_type, timestamp
                FROM episodic_events
                WHERE project_id = %s AND timestamp > %s
                ORDER BY timestamp DESC
                LIMIT 100
                """,
                (project_id, cutoff_time)
            )

            if len(events) < min_events:
                logger.info(f"Not enough events ({len(events)} < {min_events}) for consolidation")
                return {
                    "success": True,
                    "entities_created": 0,
                    "entities_updated": 0,
                    "observations_added": 0,
                    "events_processed": len(events),
                    "reason": "Not enough events"
                }

            # Extract concepts from event content
            concepts = self._extract_concepts(events)

            # Create entities for unique concepts
            graph_store = GraphStore(self.db)
            entities_created = 0
            observations_added = 0

            for concept_type, concept_names in concepts.items():
                for concept_name in concept_names:
                    try:
                        # Try to find existing entity
                        existing = graph_store.find_entity(name=concept_name, entity_type=concept_type)

                        if existing:
                            # Entity exists, add observations from new events
                            entity_id = existing[0].id if existing else None
                        else:
                            # Create new entity
                            entity = Entity(
                                name=concept_name,
                                entity_type=EntityType(concept_type),
                                project_id=project_id,
                                metadata={
                                    "consolidated_from_events": True,
                                    "created_at": datetime.now().isoformat(),
                                    "event_count": len(events)
                                }
                            )
                            entity_id = graph_store.create_entity(entity)
                            entities_created += 1

                        # Add observations from events
                        if entity_id:
                            for event in events:
                                obs_added = self._add_observation(
                                    graph_store,
                                    entity_id,
                                    event
                                )
                                observations_added += obs_added

                    except Exception as e:
                        logger.warning(f"Error processing concept {concept_name}: {e}")

            # Create relationships between entities
            self._create_entity_relationships(
                graph_store,
                project_id,
                events
            )

            return {
                "success": True,
                "entities_created": entities_created,
                "entities_updated": 0,
                "observations_added": observations_added,
                "events_processed": len(events),
            }

        except Exception as e:
            logger.error(f"Error extracting episodic entities: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "entities_created": 0,
                "entities_updated": 0,
                "observations_added": 0,
                "events_processed": 0,
            }

    def _extract_concepts(self, events: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """Extract concepts from event content using pattern matching.

        Args:
            events: List of episodic events

        Returns:
            Dict mapping concept types to sets of concept names
        """
        concepts = {
            "Concept": set(),
            "Pattern": set(),
            "Component": set(),
            "Decision": set(),
        }

        # Keywords for concept extraction
        concept_patterns = {
            "Concept": [
                r"\b(memory|learning|pattern|consolidation|knowledge|graph|embedding)\b",
                r"\b(api|database|cache|storage|layer|system|architecture)\b",
                r"\b(search|query|retrieval|reasoning|inference)\b",
            ],
            "Pattern": [
                r"\b(pattern|strategy|approach|technique|method|workflow)\b",
                r"\b(optimization|improvement|refactor|redesign)\b",
            ],
            "Component": [
                r"\b(service|handler|manager|store|processor|builder)\b",
                r"\b(module|layer|interface|adapter|controller)\b",
            ],
            "Decision": [
                r"\b(decided|choose|implement|use|adopt|migrate)\b",
                r"\b(fixed|resolved|improved|optimized|refactored)\b",
            ],
        }

        for event in events:
            content = event.get("content", "").lower()
            event_type = event.get("event_type", "").lower()

            # Extract from content and event type
            text_to_analyze = f"{content} {event_type}"

            for concept_type, patterns in concept_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, text_to_analyze, re.IGNORECASE)
                    for match in matches:
                        concepts[concept_type].add(match.capitalize())

        # Remove duplicates and empty sets
        return {k: v for k, v in concepts.items() if v}

    def _add_observation(
        self,
        graph_store,
        entity_id: int,
        event: Dict[str, Any]
    ) -> int:
        """Add observation from event to entity.

        Args:
            graph_store: GraphStore instance
            entity_id: Entity ID
            event: Episodic event

        Returns:
            Number of observations added
        """
        try:
            from ..graph.models import Observation

            if event.get("content"):
                obs = Observation(
                    entity_id=entity_id,
                    content=event["content"][:500],  # Truncate long content
                    observation_type="extracted_from_episodic_event",
                    source="episodic_consolidation",
                    timestamp=event.get("timestamp", int(datetime.now().timestamp()))
                )
                graph_store.add_observation(obs)
                return 1
        except Exception as e:
            logger.debug(f"Could not add observation: {e}")

        return 0

    def _create_entity_relationships(
        self,
        graph_store,
        project_id: int,
        events: List[Dict[str, Any]]
    ):
        """Infer and create relationships between extracted entities.

        Args:
            graph_store: GraphStore instance
            project_id: Project ID
            events: Source episodic events
        """
        try:
            from ..graph.models import Relation, RelationType

            # Get all entities for this project
            all_entities = graph_store.read_graph(project_id)
            entities = all_entities.get("nodes", []) if isinstance(all_entities, dict) else []

            if not entities:
                return

            # Create simple co-occurrence based relationships
            # Entities that appear in same events are related
            for i, entity1 in enumerate(entities):
                entity1_name = entity1.get("name", "") if isinstance(entity1, dict) else entity1.name
                entity1_id = entity1.get("id", None) if isinstance(entity1, dict) else entity1.id

                for entity2 in entities[i+1:]:
                    entity2_name = entity2.get("name", "") if isinstance(entity2, dict) else entity2.name
                    entity2_id = entity2.get("id", None) if isinstance(entity2, dict) else entity2.id

                    # Check if both appear in same event
                    for event in events:
                        content = event.get("content", "").lower()
                        if (entity1_name.lower() in content and
                            entity2_name.lower() in content):
                            try:
                                rel = Relation(
                                    from_entity_id=entity1_id,
                                    to_entity_id=entity2_id,
                                    relation_type=RelationType("relates_to"),
                                    strength=1.0,
                                    confidence=0.7,
                                    metadata={
                                        "co_occurrence": True,
                                        "source": "episodic_consolidation"
                                    }
                                )
                                graph_store.create_relation(rel)
                                break
                            except Exception as e:
                                logger.debug(f"Relationship creation: {e}")

        except Exception as e:
            logger.warning(f"Error creating relationships: {e}")
