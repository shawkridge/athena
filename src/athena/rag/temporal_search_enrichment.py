"""Temporal Knowledge Graph Search Enrichment - P2 Integration.

Enriches search results with temporal KG causal relationships,
enabling discovery of causally-related memories through search.

Implements the missing integration point from P2:
- Temporal KG synthesis (IMPLEMENTED) → synthesis, storage, causality scoring ✅
- Temporal KG in search (THIS MODULE) → integration into search results ✅
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass, field

from ..core.models import MemorySearchResult
from ..core.database import Database
from ..temporal.kg_synthesis import TemporalKGSynthesis
from ..graph.store import GraphStore

logger = logging.getLogger(__name__)


@dataclass
class CausalRelation:
    """Causal relationship between search results."""

    source_memory_id: int
    target_memory_id: int
    relation_type: str  # 'causes', 'depends_on', 'precedes', 'concurrent'
    causality_score: float  # 0.0-1.0
    recency_weight: float  # 0.0-1.0
    temporal_score: float  # Combined score
    is_critical: bool = False  # High causality indicates critical link


@dataclass
class EnrichedSearchResult:
    """Search result enriched with temporal KG relationships."""

    base_result: MemorySearchResult
    causal_relations: List[CausalRelation] = field(default_factory=list)
    related_memories: List[int] = field(default_factory=list)  # IDs of causally-related memories
    impact_score: float = 0.0  # How critical this result is to understanding context

    @property
    def total_relations(self) -> int:
        """Total number of causal relationships."""
        return len(self.causal_relations)

    @property
    def critical_relations(self) -> List[CausalRelation]:
        """Relations with high causality (> 0.7)."""
        return [r for r in self.causal_relations if r.causality_score > 0.7]


class TemporalSearchEnricher:
    """Enriches search results with temporal KG relationships.

    Pipeline:
    1. Execute base search (returns MemorySearchResult list)
    2. Query temporal KG for causal relationships
    3. Retrieve related memories and their metadata
    4. Score impact/criticality of each result
    5. Return EnrichedSearchResult with full context
    """

    def __init__(
        self,
        db: Database,
        graph_store: GraphStore,
        temporal_kg: TemporalKGSynthesis,
    ):
        """Initialize temporal search enricher.

        Args:
            db: Database connection
            graph_store: Knowledge graph store
            temporal_kg: Temporal KG synthesis engine
        """
        self.db = db
        self.graph_store = graph_store
        self.temporal_kg = temporal_kg

    def enrich_results(
        self,
        base_results: List[MemorySearchResult],
        project_id: int,
        include_related: bool = True,
        max_relations_per_result: int = 5,
    ) -> List[EnrichedSearchResult]:
        """Enrich search results with temporal KG relationships.

        Args:
            base_results: Base search results from semantic search
            project_id: Project ID for context
            include_related: Whether to fetch full related memories
            max_relations_per_result: Max causal relations per result

        Returns:
            List of enriched search results with causal relationships
        """
        enriched = []

        for result in base_results:
            # Get causal relations for this memory
            relations = self._find_causal_relations(
                result.memory.id,
                project_id,
                max_relations=max_relations_per_result,
            )

            # Compute impact score
            impact_score = self._compute_impact_score(result, relations)

            # Get related memory IDs
            related_ids = [r.target_memory_id for r in relations]

            enriched_result = EnrichedSearchResult(
                base_result=result,
                causal_relations=relations,
                related_memories=related_ids,
                impact_score=impact_score,
            )

            enriched.append(enriched_result)

        # Optionally re-sort by impact score
        enriched.sort(
            key=lambda x: (x.impact_score, x.base_result.similarity),
            reverse=True,
        )

        return enriched

    def _find_causal_relations(
        self,
        memory_id: int,
        project_id: int,
        max_relations: int = 5,
    ) -> List[CausalRelation]:
        """Find causal relations for a memory in temporal KG.

        Args:
            memory_id: Memory to find relations for
            project_id: Project context
            max_relations: Max relations to return

        Returns:
            List of causal relations
        """
        try:
            cursor = self.db.get_cursor()

            # Query temporal relations from graph store
            # This joins episodic events with their causal relationships
            query = """
                SELECT DISTINCT
                    r.to_entity as target_entity,
                    r.relation_type,
                    COALESCE(
                        CAST(json_extract(r.metadata, '$.causality') AS REAL),
                        0.5
                    ) as causality,
                    COALESCE(
                        CAST(json_extract(r.metadata, '$.recency_weight') AS REAL),
                        0.5
                    ) as recency_weight,
                    COALESCE(
                        CAST(json_extract(r.metadata, '$.temporal_score') AS REAL),
                        0.5
                    ) as temporal_score
                FROM graph_relations r
                WHERE r.from_entity = ?
                    AND r.metadata IS NOT NULL
                    AND json_extract(r.metadata, '$.temporal') = 1
                ORDER BY
                    CAST(json_extract(r.metadata, '$.causality') AS REAL) DESC,
                    CAST(json_extract(r.metadata, '$.temporal_score') AS REAL) DESC
                LIMIT ?
            """

            cursor.execute(query, (f"event_{memory_id}", max_relations))
            rows = cursor.fetchall()

            relations = []
            for row in rows:
                target_entity, relation_type, causality, recency, temporal_score = row

                # Extract memory ID from entity reference (e.g., "event_123" → 123)
                try:
                    target_id = int(target_entity.split("_")[-1])
                except (ValueError, IndexError):
                    continue

                relation = CausalRelation(
                    source_memory_id=memory_id,
                    target_memory_id=target_id,
                    relation_type=relation_type,
                    causality_score=max(0.0, min(1.0, float(causality))),
                    recency_weight=max(0.0, min(1.0, float(recency))),
                    temporal_score=max(0.0, min(1.0, float(temporal_score))),
                    is_critical=float(causality) > 0.7,
                )
                relations.append(relation)

            return relations

        except Exception as e:
            logger.warning(f"Error finding causal relations for memory {memory_id}: {e}")
            return []

    def _compute_impact_score(
        self,
        result: MemorySearchResult,
        relations: List[CausalRelation],
    ) -> float:
        """Compute impact score for a search result.

        Impact = combination of:
        1. Base relevance (similarity score)
        2. Number of causal relations
        3. Strength of critical relations
        4. Recency of relations

        Args:
            result: Search result
            relations: Causal relations for this result

        Returns:
            Impact score 0.0-1.0
        """
        if not relations:
            return result.similarity

        # Base relevance (70%)
        base_score = result.similarity * 0.7

        # Relation strength (20%)
        # Critical relations boost score significantly
        critical_count = sum(1 for r in relations if r.is_critical)
        relation_boost = min(critical_count / 3, 1.0) * 0.2

        # Recency bonus (10%)
        # Recent relations indicate active context
        avg_recency = sum(r.recency_weight for r in relations) / len(relations)
        recency_bonus = avg_recency * 0.1

        total = base_score + relation_boost + recency_bonus
        return max(0.0, min(1.0, total))

    def find_causal_chain(
        self,
        start_memory_id: int,
        project_id: int,
        direction: str = "forward",
        max_depth: int = 5,
    ) -> List[CausalRelation]:
        """Find causal chain starting from a memory.

        Args:
            start_memory_id: Starting memory ID
            project_id: Project context
            direction: 'forward' (effects) or 'backward' (causes)
            max_depth: Max chain depth

        Returns:
            List of relations forming causal chain
        """
        try:
            chain = []
            visited = {start_memory_id}
            current_ids = [start_memory_id]

            for _ in range(max_depth):
                if not current_ids:
                    break

                next_ids = []
                for memory_id in current_ids:
                    relations = self._find_causal_relations(
                        memory_id,
                        project_id,
                        max_relations=3,
                    )

                    for relation in relations:
                        # Follow direction
                        if direction == "forward":
                            target_id = relation.target_memory_id
                        else:  # backward - reverse the relation
                            target_id = relation.source_memory_id
                            # Create reversed relation for consistency
                            relation = CausalRelation(
                                source_memory_id=relation.target_memory_id,
                                target_memory_id=relation.source_memory_id,
                                relation_type=relation.relation_type,
                                causality_score=relation.causality_score,
                                recency_weight=relation.recency_weight,
                                temporal_score=relation.temporal_score,
                                is_critical=relation.is_critical,
                            )

                        if target_id not in visited:
                            chain.append(relation)
                            visited.add(target_id)
                            next_ids.append(target_id)

                current_ids = next_ids

            return chain

        except Exception as e:
            logger.error(f"Error finding causal chain from {start_memory_id}: {e}")
            return []

    def get_causal_context(
        self,
        memory_id: int,
        project_id: int,
        context_depth: int = 2,
    ) -> Dict[str, Any]:
        """Get full causal context for a memory.

        Returns causes, effects, and indirect relationships.

        Args:
            memory_id: Memory to get context for
            project_id: Project context
            context_depth: How many hops to traverse

        Returns:
            Dict with 'causes', 'effects', 'concurrent' keys
        """
        try:
            causes = self.find_causal_chain(
                memory_id,
                project_id,
                direction="backward",
                max_depth=context_depth,
            )

            effects = self.find_causal_chain(
                memory_id,
                project_id,
                direction="forward",
                max_depth=context_depth,
            )

            return {
                "memory_id": memory_id,
                "causes": causes,
                "effects": effects,
                "total_relations": len(causes) + len(effects),
                "critical_relations": sum(1 for r in causes + effects if r.is_critical),
            }

        except Exception as e:
            logger.error(f"Error getting causal context for {memory_id}: {e}")
            return {
                "memory_id": memory_id,
                "causes": [],
                "effects": [],
                "total_relations": 0,
                "critical_relations": 0,
            }
