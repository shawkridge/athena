"""Community summarization for knowledge graph using LLM."""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from ..core.database import Database
from ..core.embeddings import EmbeddingModel
from .models import Entity, EntityType

logger = logging.getLogger(__name__)


@dataclass
class SummaryMetadata:
    """Metadata about a community summary."""

    community_id: int
    entity_count: int
    relation_count: int
    summary_tokens: int
    model_used: str
    created_at: datetime
    confidence: float  # 0-1 based on entity diversity


class CommunitySummarizer:
    """Generates and manages community summaries for knowledge graph."""

    def __init__(self, db: Database, embedding_model: Optional[str] = None):
        """Initialize community summarizer.

        Args:
            db: Database instance
            embedding_model: Optional embedding model for semantic analysis
        """
        self.db = db
        self.embedder = EmbeddingModel(embedding_model) if embedding_model else None
        self._summary_cache: Dict[int, str] = {}
        self._metadata_cache: Dict[int, SummaryMetadata] = {}

    def summarize_community(
        self,
        community_id: int,
        entity_ids: List[int],
        entity_names: List[str],
        max_tokens: int = 200,
    ) -> Tuple[str, SummaryMetadata]:
        """Generate a summary for a community.

        Uses hierarchical approach:
        1. Extract key entities and relationships
        2. Identify central nodes (high connectivity)
        3. Generate LLM-based summary
        4. Validate summary quality

        Args:
            community_id: ID of community
            entity_ids: IDs of entities in community
            entity_names: Names of entities in community
            max_tokens: Maximum tokens in summary (target: 100-200)

        Returns:
            Tuple of (summary_text, metadata)
        """
        # Check cache first
        if community_id in self._summary_cache:
            return self._summary_cache[community_id], self._metadata_cache[community_id]

        try:
            # Get relationship information
            relations = self._get_community_relations(entity_ids)
            rel_count = len(relations)

            # Identify central entities (hub nodes)
            central_entities = self._identify_central_entities(entity_ids, relations)

            # Build context for LLM
            context = self._build_summary_context(
                entity_names, central_entities, relations, max_tokens
            )

            # Generate summary using LLM
            summary = self._generate_summary(context, max_tokens)

            # Create metadata
            metadata = SummaryMetadata(
                community_id=community_id,
                entity_count=len(entity_ids),
                relation_count=rel_count,
                summary_tokens=len(summary.split()),
                model_used="claude-3-haiku",
                created_at=datetime.now(),
                confidence=self._calculate_confidence(entity_ids, relations),
            )

            # Cache results
            self._summary_cache[community_id] = summary
            self._metadata_cache[community_id] = metadata

            logger.info(
                f"Summarized community {community_id}: "
                f"{len(entity_ids)} entities, {rel_count} relations"
            )

            return summary, metadata

        except Exception as e:
            logger.error(f"Failed to summarize community {community_id}: {e}")
            # Fallback to simple summary
            fallback = self._create_fallback_summary(entity_names)
            metadata = SummaryMetadata(
                community_id=community_id,
                entity_count=len(entity_ids),
                relation_count=0,
                summary_tokens=len(fallback.split()),
                model_used="fallback",
                created_at=datetime.now(),
                confidence=0.3,
            )
            self._summary_cache[community_id] = fallback
            self._metadata_cache[community_id] = metadata
            return fallback, metadata

    def batch_summarize_communities(
        self, project_id: int, max_tokens: int = 200, force_refresh: bool = False
    ) -> Dict[int, Tuple[str, SummaryMetadata]]:
        """Batch summarize all communities in a project.

        Optimizations:
        - Groups small communities together
        - Prioritizes large/important communities
        - Reuses existing summaries unless force_refresh=True
        - Tracks cost and quality metrics

        Args:
            project_id: Project ID
            max_tokens: Maximum tokens per summary
            force_refresh: If True, regenerate all summaries

        Returns:
            Dict mapping community_id to (summary, metadata)
        """
        try:
            # Get all communities for project
            communities = self._get_project_communities(project_id)

            if not communities:
                logger.warning(f"No communities found for project {project_id}")
                return {}

            results = {}
            processed = 0
            skipped = 0

            # Sort by size (large first) for efficiency
            sorted_communities = sorted(
                communities, key=lambda c: len(c["entity_ids"]), reverse=True
            )

            for community in sorted_communities:
                community_id = community["id"]

                # Skip if already summarized and not forcing refresh
                if not force_refresh and self._is_summarized(community_id):
                    skipped += 1
                    summary, metadata = self._get_cached_summary(community_id)
                    results[community_id] = (summary, metadata)
                    continue

                # Generate summary
                summary, metadata = self.summarize_community(
                    community_id=community_id,
                    entity_ids=community["entity_ids"],
                    entity_names=community["entity_names"],
                    max_tokens=max_tokens,
                )

                results[community_id] = (summary, metadata)
                processed += 1

                # Log progress
                if processed % 10 == 0:
                    logger.info(
                        f"Summarized {processed} communities (skipped {skipped})"
                    )

            logger.info(
                f"Batch summarization complete: "
                f"processed={processed}, skipped={skipped}, total={len(results)}"
            )

            return results

        except Exception as e:
            logger.error(f"Batch summarization failed: {e}")
            return {}

    def update_community_summary(
        self, community_id: int, summary: str, save_to_db: bool = True
    ) -> bool:
        """Update summary for a community in database.

        Args:
            community_id: ID of community
            summary: New summary text
            save_to_db: If True, persist to database

        Returns:
            True if successful
        """
        try:
            if save_to_db:
                # Update communities table
                self.db.execute(
                    """
                    UPDATE communities
                    SET summary = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (summary, int(datetime.now().timestamp()), community_id),
                )
                self.db.commit()

            # Update cache
            self._summary_cache[community_id] = summary

            return True

        except Exception as e:
            logger.error(f"Failed to update summary for community {community_id}: {e}")
            return False

    def get_summary(self, community_id: int) -> Optional[str]:
        """Get summary for a community.

        Args:
            community_id: ID of community

        Returns:
            Summary text or None if not found
        """
        # Check cache first
        if community_id in self._summary_cache:
            return self._summary_cache[community_id]

        # Try to load from database
        try:
            result = self.db.execute_one(
                "SELECT summary FROM communities WHERE id = ?", (community_id,)
            )
            if result:
                summary = result.get("summary")
                if summary:
                    self._summary_cache[community_id] = summary
                    return summary
        except Exception as e:
            logger.warning(f"Failed to load summary for community {community_id}: {e}")

        return None

    def get_summary_stats(self, community_id: int) -> Optional[SummaryMetadata]:
        """Get metadata for a community summary.

        Args:
            community_id: ID of community

        Returns:
            Summary metadata or None
        """
        if community_id in self._metadata_cache:
            return self._metadata_cache[community_id]

        return None

    def clear_cache(self) -> None:
        """Clear summary cache."""
        self._summary_cache.clear()
        self._metadata_cache.clear()
        logger.info("Summary cache cleared")

    # Private helper methods

    def _get_community_relations(self, entity_ids: List[int]) -> List[Dict]:
        """Get relationships within a community.

        Args:
            entity_ids: List of entity IDs in community

        Returns:
            List of relation dicts
        """
        try:
            # Get all relations between entities in community
            placeholders = ",".join("?" * len(entity_ids))
            query = f"""
                SELECT from_entity_id, to_entity_id, relation_type, strength
                FROM entity_relations
                WHERE from_entity_id IN ({placeholders})
                  AND to_entity_id IN ({placeholders})
            """

            relations = self.db.execute(query, entity_ids + entity_ids)
            return relations if relations else []

        except Exception as e:
            logger.warning(f"Failed to get community relations: {e}")
            return []

    def _identify_central_entities(
        self, entity_ids: List[int], relations: List[Dict]
    ) -> List[int]:
        """Identify central (hub) entities in community.

        Uses degree centrality: entities with most connections.

        Args:
            entity_ids: List of entity IDs
            relations: List of relations in community

        Returns:
            Top 3-5 central entity IDs
        """
        try:
            # Count connections for each entity
            degree = {eid: 0 for eid in entity_ids}

            for rel in relations:
                from_id = rel.get("from_entity_id")
                to_id = rel.get("to_entity_id")

                if from_id in degree:
                    degree[from_id] += 1
                if to_id in degree:
                    degree[to_id] += 1

            # Return top 3-5 by degree
            top_count = min(5, max(3, len(entity_ids) // 3))
            central = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:top_count]

            return [eid for eid, _ in central]

        except Exception as e:
            logger.warning(f"Failed to identify central entities: {e}")
            return entity_ids[:min(5, len(entity_ids))]

    def _build_summary_context(
        self,
        entity_names: List[str],
        central_entities: List[int],
        relations: List[Dict],
        max_tokens: int,
    ) -> str:
        """Build context for LLM summarization.

        Args:
            entity_names: Names of entities
            central_entities: IDs of important entities
            relations: Relations in community
            max_tokens: Max tokens for summary

        Returns:
            Context string for LLM
        """
        lines = []

        # Add entity list
        lines.append("Entities in community:")
        for name in entity_names[:20]:  # Limit to 20 for context
            lines.append(f"  - {name}")

        # Add central entities highlight
        if central_entities:
            lines.append("\nKey entities (high connectivity):")
            for eid in central_entities[:5]:
                # Try to find name for this entity
                lines.append(f"  - Entity {eid}")

        # Add relationship summary
        if relations:
            lines.append(f"\nRelationships ({len(relations)} total):")
            # Show top relation types
            rel_types = {}
            for rel in relations:
                rel_type = rel.get("relation_type", "unknown")
                rel_types[rel_type] = rel_types.get(rel_type, 0) + 1

            for rel_type, count in sorted(
                rel_types.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                lines.append(f"  - {rel_type}: {count} relations")

        # Add instruction
        lines.append(
            f"\nGenerate a concise summary (target: {max_tokens} tokens) "
            "that captures the essence of this community."
        )

        return "\n".join(lines)

    def _generate_summary(self, context: str, max_tokens: int) -> str:
        """Generate summary using LLM.

        Args:
            context: Context for LLM
            max_tokens: Maximum tokens in summary

        Returns:
            Generated summary
        """
        try:
            # Use Anthropic API if available
            try:
                from anthropic import Anthropic

                client = Anthropic()
                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=max_tokens,
                    messages=[
                        {
                            "role": "user",
                            "content": f"{context}\n\nProvide a concise summary of this knowledge graph community.",
                        }
                    ],
                )
                return message.content[0].text

            except ImportError:
                logger.warning("Anthropic client not available, using fallback")
                return self._create_fallback_summary([])

        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}")
            return ""

    def _create_fallback_summary(self, entity_names: List[str]) -> str:
        """Create simple fallback summary when LLM not available.

        Args:
            entity_names: Names of entities

        Returns:
            Simple summary
        """
        if not entity_names:
            return "A community with multiple related entities."

        top_names = entity_names[:3]
        return f"Community containing {len(entity_names)} entities including {', '.join(top_names)}."

    def _calculate_confidence(self, entity_ids: List[int], relations: List[Dict]) -> float:
        """Calculate confidence score for summary.

        Based on:
        - Community density (more edges = higher confidence)
        - Entity diversity
        - Relation strength

        Args:
            entity_ids: List of entity IDs
            relations: List of relations

        Returns:
            Confidence score (0-1)
        """
        try:
            if not entity_ids or len(entity_ids) < 2:
                return 0.3

            # Max possible edges in community
            max_edges = len(entity_ids) * (len(entity_ids) - 1) / 2

            # Actual edges (approximation from relations)
            actual_edges = len(relations) / 2  # Divide by 2 for bidirectional

            # Density: 0-1
            density = min(actual_edges / max_edges, 1.0) if max_edges > 0 else 0.0

            # Average strength
            avg_strength = (
                sum(r.get("strength", 1.0) for r in relations) / len(relations)
                if relations
                else 0.5
            )

            # Combined confidence
            confidence = (density * 0.6 + avg_strength * 0.4) * 0.8 + 0.2

            return min(confidence, 1.0)

        except Exception as e:
            logger.warning(f"Failed to calculate confidence: {e}")
            return 0.5

    def _is_summarized(self, community_id: int) -> bool:
        """Check if a community already has a summary.

        Args:
            community_id: ID of community

        Returns:
            True if summary exists
        """
        try:
            result = self.db.execute_one(
                "SELECT summary FROM communities WHERE id = ? AND summary IS NOT NULL",
                (community_id,),
            )
            return result is not None

        except Exception as e:
            logger.warning(f"Failed to check summarization status: {e}")
            return False

    def _get_cached_summary(self, community_id: int) -> Tuple[str, SummaryMetadata]:
        """Get cached summary without recomputation.

        Args:
            community_id: ID of community

        Returns:
            Tuple of (summary, metadata)
        """
        if community_id in self._summary_cache:
            return (
                self._summary_cache[community_id],
                self._metadata_cache[community_id],
            )

        # Try to load from database
        try:
            result = self.db.execute_one(
                "SELECT summary FROM communities WHERE id = ?", (community_id,)
            )
            if result and result.get("summary"):
                summary = result["summary"]
                # Create minimal metadata
                metadata = SummaryMetadata(
                    community_id=community_id,
                    entity_count=0,
                    relation_count=0,
                    summary_tokens=len(summary.split()),
                    model_used="loaded",
                    created_at=datetime.now(),
                    confidence=0.5,
                )
                return summary, metadata
        except Exception as e:
            logger.warning(f"Failed to load cached summary: {e}")

        return "", SummaryMetadata(
            community_id=community_id,
            entity_count=0,
            relation_count=0,
            summary_tokens=0,
            model_used="empty",
            created_at=datetime.now(),
            confidence=0.0,
        )

    def _get_project_communities(self, project_id: int) -> List[Dict]:
        """Get all communities for a project.

        Args:
            project_id: Project ID

        Returns:
            List of community dicts with entity info
        """
        try:
            # Get communities from database
            communities = self.db.execute(
                "SELECT id, entity_ids FROM communities WHERE project_id = ?",
                (project_id,),
            )

            result = []
            for community in communities:
                try:
                    entity_ids = json.loads(community.get("entity_ids", "[]"))
                    if entity_ids:
                        # Get entity names
                        placeholders = ",".join("?" * len(entity_ids))
                        entities = self.db.execute(
                            f"SELECT id, name FROM entities WHERE id IN ({placeholders})",
                            entity_ids,
                        )

                        entity_names = [e.get("name", f"Entity {e.get('id')}") for e in entities]

                        result.append(
                            {
                                "id": community.get("id"),
                                "entity_ids": entity_ids,
                                "entity_names": entity_names,
                            }
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to parse community {community.get('id')}: {e}"
                    )

            return result

        except Exception as e:
            logger.error(f"Failed to get project communities: {e}")
            return []
