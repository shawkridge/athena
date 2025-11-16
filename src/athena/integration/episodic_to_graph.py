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
    """Extract knowledge graph entities from episodic events.

    Implements dual-process extraction:
    - System 1 (fast): Heuristic-based pattern matching
    - System 2 (slow): LLM validation for uncertain extractions
    """

    def __init__(self, db, llm_client=None):
        """Initialize extractor.

        Args:
            db: Database instance
            llm_client: Optional LLM client for validation (dual-process)
        """
        self.db = db
        self.llm_client = llm_client
        self.uncertainty_threshold = 0.6  # If uncertainty > this, use LLM validation

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

            # System 1: Extract concepts from event content using heuristics
            concepts = self._extract_concepts(events)

            # Calculate extraction uncertainty
            uncertainty = self._calculate_extraction_uncertainty(concepts, events)

            # System 2: If uncertainty is high, validate with LLM
            if uncertainty > self.uncertainty_threshold:
                logger.debug(f"Extraction uncertainty {uncertainty:.2f} > threshold, using LLM validation")
                concepts = self._validate_concepts_with_llm(concepts, events)
            else:
                logger.debug(f"Extraction uncertainty {uncertainty:.2f} is low, using System 1 results")

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

        Uses System 1 (fast heuristics) to extract concepts. High-uncertainty
        extractions can be validated using System 2 (LLM).

        Extracts both abstract concepts and code-aware entities:
        - Abstract: Concepts, Patterns, Components, Decisions
        - Code: Functions, Classes, Files, Modules

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
            "Function": set(),
            "Class": set(),
            "File": set(),
        }

        # Keywords for abstract concept extraction
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

            # Extract abstract concepts from content and event type
            text_to_analyze = f"{content} {event_type}"

            for concept_type, patterns in concept_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, text_to_analyze, re.IGNORECASE)
                    for match in matches:
                        concepts[concept_type].add(match.capitalize())

            # Extract code-aware entities (System 1 + code metadata)
            # Functions: from symbol_name when event involves function calls
            if event.get("symbol_type") == "function" and event.get("symbol_name"):
                func_name = event["symbol_name"].strip()
                if func_name and len(func_name) > 1:  # Avoid single char names
                    concepts["Function"].add(func_name)

            # Classes: from symbol_type and symbol_name
            if event.get("symbol_type") == "class" and event.get("symbol_name"):
                class_name = event["symbol_name"].strip()
                if class_name:
                    concepts["Class"].add(class_name)

            # Files: extract from file_path (last component)
            if event.get("file_path"):
                file_path = event["file_path"]
                # Extract filename without full path
                filename = file_path.split("/")[-1]
                if filename and not filename.startswith("."):
                    concepts["File"].add(filename)

        # Remove duplicates and empty sets
        return {k: v for k, v in concepts.items() if v}

    def _calculate_extraction_uncertainty(self, concepts: Dict[str, Set[str]], events: List[Dict[str, Any]]) -> float:
        """Calculate uncertainty in concept extraction (System 1 confidence).

        Uses frequency and dispersion metrics:
        - Low uncertainty: Concepts appear frequently across multiple events
        - High uncertainty: Rare concepts or low pattern match confidence

        Args:
            concepts: Extracted concepts by type
            events: Original episodic events

        Returns:
            Uncertainty score (0.0-1.0, higher = more uncertain)
        """
        if not concepts or not events:
            return 1.0  # Maximum uncertainty

        total_concepts = sum(len(v) for v in concepts.values())
        if total_concepts == 0:
            return 1.0

        # Metrics: higher = more confident (lower uncertainty)
        concept_frequency_score = min(total_concepts / 10.0, 1.0)  # Expect ~10 concepts
        event_coverage_score = len(events) / 5.0  # Expected ~5 events
        concept_diversity_score = len(concepts) / 4.0  # All 4 types

        # Combine into confidence (0-1), then invert to uncertainty
        confidence = (concept_frequency_score * 0.5 + event_coverage_score * 0.3 + concept_diversity_score * 0.2)
        confidence = min(confidence, 1.0)
        uncertainty = 1.0 - confidence

        return uncertainty

    def _validate_concepts_with_llm(self, concepts: Dict[str, Set[str]], events: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
        """Validate extracted concepts using LLM (System 2 validation).

        Called when uncertainty is high. Uses LLM to:
        1. Confirm extracted concepts are appropriate
        2. Suggest missing concepts
        3. Remove spurious concepts

        Args:
            concepts: Concepts extracted by System 1
            events: Original episodic events

        Returns:
            Validated/refined concept dictionary
        """
        if not self.llm_client:
            logger.debug("No LLM client available, using System 1 results")
            return concepts

        try:
            # Build prompt for LLM validation
            event_summaries = "\n".join([
                f"[{e.get('event_type', 'unknown')}] {e.get('content', '')[:200]}"
                for e in events[:5]  # Use first 5 events
            ])

            extracted_str = "\n".join([
                f"- {ctype}: {', '.join(sorted(names))}"
                for ctype, names in concepts.items() if names
            ])

            prompt = f"""You are analyzing episodic events from a knowledge consolidation system.

EVENTS:
{event_summaries}

SYSTEM-1 EXTRACTED CONCEPTS:
{extracted_str}

Task: Validate these extracted concepts. For each concept type, identify which should be kept, removed, or added.

Respond with ONLY valid JSON (no markdown, no extra text):
{{
  "confirmed": ["concept1", "concept2"],
  "remove": ["spurious_concept"],
  "add": {{"ConceptType": ["new_concept1"], "Pattern": ["new_pattern"]}}
}}"""

            logger.info("Validating extracted concepts with LLM (System 2)")
            response = self.llm_client.generate(prompt)

            if not response:
                logger.warning("LLM returned empty response, using System 1 results")
                return concepts

            # Parse JSON from LLM response
            import json
            try:
                # Try to extract JSON from response (handle markdown formatting)
                json_str = response
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0]

                validation = json.loads(json_str.strip())
            except (json.JSONDecodeError, IndexError) as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}, using System 1 results")
                return concepts

            # Apply validation results
            validated_concepts = {k: v.copy() for k, v in concepts.items()}

            # Remove spurious concepts
            to_remove = set(validation.get("remove", []))
            for concept_type in validated_concepts:
                validated_concepts[concept_type] -= to_remove

            # Add new concepts suggested by LLM
            for concept_type, new_concepts in validation.get("add", {}).items():
                if concept_type not in validated_concepts:
                    validated_concepts[concept_type] = set()
                validated_concepts[concept_type].update(new_concepts)

            # Clean up empty sets
            validated_concepts = {k: v for k, v in validated_concepts.items() if v}

            logger.info(f"LLM validation complete: removed {len(to_remove)}, added {sum(len(v) for v in validation.get('add', {}).values())}")
            return validated_concepts

        except Exception as e:
            logger.warning(f"LLM validation failed: {e}, using System 1 results")
            return concepts

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
