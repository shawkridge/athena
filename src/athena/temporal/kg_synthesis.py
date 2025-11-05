"""Temporal Knowledge Graph Synthesis - Zep Pattern Implementation.

Transforms episodic events into temporal knowledge graph with recency,
frequency, causality, and dependency metadata.

Based on: Zep arXiv:2501.13956 "Temporal Knowledge Graphs for Infinite Context LLMs"
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..episodic.models import EpisodicEvent, EventType, EventOutcome
from ..episodic.store import EpisodicStore
from ..graph.store import GraphStore
from ..graph.models import Observation
from .models import EntityMetadata, TemporalKGRelation, KGSynthesisResult


class TemporalKGSynthesis:
    """
    Transform episodic events into temporal knowledge graph.

    3-Stage Pipeline:
    1. Extract entities & relations from events (LLM-based)
    2. Infer temporal relationships (causality, recency, frequency, dependency)
    3. Update knowledge graph with temporal metadata
    """

    def __init__(
        self,
        episodic_store: EpisodicStore,
        graph_store: GraphStore,
        causality_threshold: float = 0.5,
        recency_decay_hours: float = 1.0,
        frequency_threshold: int = 10,
    ):
        """
        Initialize Temporal KG Synthesis.

        Args:
            episodic_store: Store for retrieving episodic events
            graph_store: Store for updating knowledge graph
            causality_threshold: Min causality score to create relation (default 0.5)
            recency_decay_hours: Exponential decay rate for recency weighting
            frequency_threshold: Access count threshold for frequency normalization
        """
        self.episodic_store = episodic_store
        self.graph_store = graph_store
        self.causality_threshold = causality_threshold
        self.recency_decay_seconds = recency_decay_hours * 3600
        self.frequency_threshold = frequency_threshold

    def synthesize(
        self,
        session_id: str,
        since_timestamp: Optional[float] = None,
    ) -> KGSynthesisResult:
        """
        Transform events into temporal KG updates.

        3-stage pipeline:
        1. Extract entities & relations from episodic events
        2. Infer temporal relationships between entities
        3. Update knowledge graph with temporal metadata

        Args:
            session_id: Session to synthesize
            since_timestamp: Only process events after this timestamp (optional)

        Returns:
            KGSynthesisResult with counts and latency
        """
        start_time = time.time()

        # Stage 1: Extract entities and relations
        events = self.episodic_store.get_events_by_session(session_id)
        if not events:
            return KGSynthesisResult(
                entities_count=0,
                relations_count=0,
                temporal_relations_count=0,
                latency_ms=0.0,
                quality_score=0.0,
            )

        # Stage 2: Infer temporal relationships
        temporal_relations = self._infer_temporal_relations(events)

        # Stage 3: Update knowledge graph
        self._update_kg_with_temporal_metadata(events, temporal_relations)

        latency_ms = (time.time() - start_time) * 1000
        quality_score = self._calculate_quality_score(events, temporal_relations)

        return KGSynthesisResult(
            entities_count=len(set(r.from_entity for r in temporal_relations)) + 1,
            relations_count=len(temporal_relations),
            temporal_relations_count=len([r for r in temporal_relations if r.causality > self.causality_threshold]),
            latency_ms=latency_ms,
            quality_score=quality_score,
        )

    def _infer_temporal_relations(self, events: List[EpisodicEvent]) -> List[TemporalKGRelation]:
        """
        Stage 2: Infer temporal relationships between events.

        Infers:
        - Causality: Does event A cause event B?
        - Recency: How recent is the relationship?
        - Frequency: How often does this pattern occur?
        - Dependency: Does event B require event A?

        Args:
            events: List of episodic events

        Returns:
            List of temporal KG relations
        """
        if len(events) < 2:
            return []

        temporal_relations = []
        now = datetime.now().timestamp()

        # Compare all pairs of events
        for i, event_a in enumerate(events):
            for event_b in events[i + 1 :]:
                # Calculate causality
                causality = self._calculate_causality(event_a, event_b)

                # Calculate recency weight (exponential decay, clamped to [0, 1])
                time_diff_seconds = (event_b.timestamp.timestamp() - event_a.timestamp.timestamp())
                recency_weight = np.clip(np.exp(-time_diff_seconds / self.recency_decay_seconds), 0.0, 1.0)

                # Detect dependency (heuristic)
                dependency = self._detect_dependency(event_a, event_b)

                # Calculate frequency (simplified: number of shared attributes)
                frequency = self._calculate_frequency(event_a, event_b)

                # Combined temporal score
                temporal_score = 0.5 * causality + 0.3 * recency_weight + 0.2 * (1.0 if dependency else 0.0)

                # Create relation
                relation = TemporalKGRelation(
                    from_entity=f"event_{event_a.id}",
                    to_entity=f"event_{event_b.id}",
                    relation_type="causes" if causality > 0.7 else "precedes",
                    causality=causality,
                    recency_weight=recency_weight,
                    frequency=frequency,
                    dependency=dependency,
                    temporal_score=temporal_score,
                    inferred_at=datetime.now(),
                )

                temporal_relations.append(relation)

        return temporal_relations

    def _calculate_causality(self, event_a: EpisodicEvent, event_b: EpisodicEvent) -> float:
        """
        Calculate causality score between two events (0-1).

        Heuristics:
        - error → success: high causality (1.0)
        - decision → action: medium causality (0.8)
        - test_fail → file_change → test_success: chain (0.6)
        - shared_files: mild causality (0.4)
        """
        # Error → Success pattern
        if (
            event_a.event_type == EventType.ERROR
            and event_b.outcome == EventOutcome.SUCCESS
        ):
            return 1.0

        # Decision → Action pattern
        if (
            event_a.event_type == EventType.DECISION
            and event_b.event_type == EventType.ACTION
        ):
            return 0.8

        # Test failure → Test success
        if (
            event_a.event_type == EventType.TEST_RUN
            and event_a.outcome == EventOutcome.FAILURE
            and event_b.event_type == EventType.TEST_RUN
            and event_b.outcome == EventOutcome.SUCCESS
        ):
            return 0.7

        # Shared context (files)
        if event_a.context.files and event_b.context.files:
            shared = len(set(event_a.context.files) & set(event_b.context.files))
            if shared > 0:
                return min(0.4 + (shared * 0.1), 0.6)

        return 0.0

    def _detect_dependency(self, event_a: EpisodicEvent, event_b: EpisodicEvent) -> bool:
        """
        Detect if event B depends on event A (heuristic).

        Patterns:
        - compile → test (requires object file)
        - build → deploy (requires artifact)
        - test → success → merge (requires passing tests)
        """
        # Test depends on compile/build
        if event_a.event_type == EventType.ACTION and event_b.event_type == EventType.TEST_RUN:
            if "compile" in event_a.content.lower() or "build" in event_a.content.lower():
                return True

        # Deploy depends on successful build
        if (
            event_a.outcome == EventOutcome.SUCCESS
            and "build" in event_a.content.lower()
            and "deploy" in event_b.content.lower()
        ):
            return True

        # Merge depends on passing tests
        if (
            event_a.event_type == EventType.TEST_RUN
            and event_a.outcome == EventOutcome.SUCCESS
            and "merge" in event_b.content.lower()
        ):
            return True

        return False

    def _calculate_frequency(self, event_a: EpisodicEvent, event_b: EpisodicEvent) -> float:
        """
        Calculate frequency score (0-1).

        Based on shared attributes (context, type, outcome).
        """
        score = 0.0

        # Same event type
        if event_a.event_type == event_b.event_type:
            score += 0.3

        # Same outcome
        if event_a.outcome == event_b.outcome:
            score += 0.2

        # Same task
        if event_a.context.task == event_b.context.task:
            score += 0.3

        # Shared files
        if event_a.context.files and event_b.context.files:
            shared = len(set(event_a.context.files) & set(event_b.context.files))
            score += min(shared * 0.1, 0.2)

        return min(score, 1.0)

    def _update_kg_with_temporal_metadata(
        self,
        events: List[EpisodicEvent],
        temporal_relations: List[TemporalKGRelation],
    ) -> None:
        """
        Stage 3: Update knowledge graph with temporal metadata.

        For each event/entity:
        1. Add temporal metadata observation to graph
        2. Create or update temporal relations
        """
        now = datetime.now()

        # Update entity metadata
        for event in events:
            entity_name = f"event_{event.id}"

            # Calculate metadata (clamped to [0, 1])
            recency_weight = np.clip(
                np.exp(
                    -(now.timestamp() - event.timestamp.timestamp()) / self.recency_decay_seconds
                ),
                0.0,
                1.0
            )

            # Find related temporal relations
            related_entities = []
            avg_causality = 0.0
            relation_count = 0

            for rel in temporal_relations:
                if rel.from_entity == entity_name:
                    related_entities.append(rel.to_entity)
                    avg_causality += rel.causality
                    relation_count += 1
                elif rel.to_entity == entity_name:
                    related_entities.append(rel.from_entity)
                    avg_causality += rel.causality
                    relation_count += 1

            if relation_count > 0:
                avg_causality /= relation_count

            # Create metadata object
            metadata = EntityMetadata(
                entity_name=entity_name,
                last_access=now,
                access_count=1,  # Would be updated from history
                recency_weight=recency_weight,
                temporal_span_seconds=0.0,  # Would be calculated from history
                is_critical=avg_causality > 0.7,
                related_entities=related_entities,
                causality_score=avg_causality,
            )

            # Add observation to graph
            # First find the entity
            entities = self.graph_store.search_entities(entity_name)
            if entities:
                entity = entities[0]
                obs = Observation(
                    entity_id=entity.id,
                    content=f"temporal_metadata: {json.dumps({
                        'last_access': metadata.last_access.isoformat(),
                        'recency_weight': float(metadata.recency_weight),
                        'is_critical': metadata.is_critical,
                        'causality_score': float(metadata.causality_score),
                        'related_entities': metadata.related_entities,
                    })}",
                    created_at=datetime.now()
                )
                self.graph_store.add_observation(obs)

        # Create temporal relations in graph
        for rel in temporal_relations:
            if rel.causality > self.causality_threshold:
                self.graph_store.create_relation(
                    from_entity=rel.from_entity,
                    to_entity=rel.to_entity,
                    relation_type="causes" if rel.causality > 0.7 else "precedes",
                )

    def _calculate_quality_score(
        self,
        events: List[EpisodicEvent],
        temporal_relations: List[TemporalKGRelation],
    ) -> float:
        """
        Calculate quality score (0-1) for synthesis.

        Based on:
        - Coverage: # relations / max possible relations
        - Confidence: Avg temporal score
        - Validity: % relations with valid causality
        """
        if not events or not temporal_relations:
            return 0.0

        # Coverage
        max_relations = len(events) * (len(events) - 1) / 2
        coverage = len(temporal_relations) / max_relations if max_relations > 0 else 0.0

        # Confidence
        avg_score = np.mean([r.temporal_score for r in temporal_relations])

        # Validity
        valid_relations = sum(1 for r in temporal_relations if r.causality > 0.0)
        validity = valid_relations / len(temporal_relations) if temporal_relations else 0.0

        # Combined quality
        quality = 0.3 * coverage + 0.5 * avg_score + 0.2 * validity
        return min(quality, 1.0)
