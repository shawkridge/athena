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
            from ..graph.models import Entity, EntityType, Relation, RelationType

            # Get recent episodic events
            cutoff_time = int((datetime.now() - timedelta(hours=hours_back)).timestamp())

            events = self.db.query(
                """
                SELECT id, content, event_type, metadata, created_at
                FROM episodic_events
                WHERE project_id = %s AND created_at > %s
                ORDER BY created_at DESC
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
            entities_updated = 0
            observations_added = 0

            for concept_type, concept_names in concepts.items():
                for concept_name in concept_names:
                    try:
                        # Check if entity exists
                        existing = graph_store.find_entity_by_name(
                            concept_name,
                            concept_type,
                            project_id
                        )

                        if existing:
                            # Update existing entity
                            graph_store.update_entity(
                                existing.id,
                                name=concept_name,
                                metadata={
                                    "consolidated_from_events": True,
                                    "last_updated": datetime.now().isoformat(),
                                    "event_count": existing.metadata.get("event_count", 0) + len(events)
                                }
                            )
                            entities_updated += 1
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
                            graph_store.create_entity(entity)
                            entities_created += 1

                        # Add observations from events
                        for event in events:
                            obs_added = self._add_observation(
                                graph_store,
                                concept_name,
                                concept_type,
                                event,
                                project_id
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
                "entities_updated": entities_updated,
                "observations_added": observations_added,
                "events_processed": len(events),
            }

        except Exception as e:
            logger.error(f"Error extracting episodic entities: {e}")
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
        entity_name: str,
        entity_type: str,
        event: Dict[str, Any],
        project_id: int
    ) -> int:
        """Add observation from event to entity.

        Args:
            graph_store: GraphStore instance
            entity_name: Entity name
            entity_type: Entity type
            event: Episodic event
            project_id: Project ID

        Returns:
            Number of observations added
        """
        try:
            entity = graph_store.find_entity_by_name(
                entity_name,
                entity_type,
                project_id
            )

            if entity and event.get("content"):
                graph_store.add_observation(
                    entity_id=entity.id,
                    content=event["content"][:500],  # Truncate long content
                    observation_type="extracted_from_episodic_event",
                    source="episodic_consolidation",
                    timestamp=event.get("created_at", int(datetime.now().timestamp()))
                )
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
            entities = graph_store.get_all_for_project(project_id)

            # Create simple co-occurrence based relationships
            # Entities that appear in same events are related
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    # Check if both appear in same event
                    for event in events:
                        content = event.get("content", "").lower()
                        if (entity1.name.lower() in content and
                            entity2.name.lower() in content):
                            try:
                                graph_store.create_relation(
                                    from_entity_id=entity1.id,
                                    to_entity_id=entity2.id,
                                    relation_type="relates_to",
                                    strength=1.0,
                                    confidence=0.7,
                                    metadata={
                                        "co_occurrence": True,
                                        "source": "episodic_consolidation"
                                    }
                                )
                                break
                            except Exception as e:
                                logger.debug(f"Relationship creation: {e}")

        except Exception as e:
            logger.warning(f"Error creating relationships: {e}")
