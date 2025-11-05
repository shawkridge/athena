"""Integration of research findings with semantic memory and knowledge graph."""

import logging
from typing import Optional, List
from datetime import datetime

from athena.core.database import Database
from athena.memory import MemoryStore
from athena.graph.store import GraphStore
from athena.episodic.store import EpisodicStore
from athena.episodic.models import EpisodicEvent, EventType, EventOutcome
from .aggregation import AggregatedFinding

logger = logging.getLogger(__name__)


class ResearchMemoryIntegrator:
    """Integrate research findings into memory system."""

    def __init__(
        self,
        memory_store: MemoryStore,
        graph_store: GraphStore,
        episodic_store: EpisodicStore,
    ):
        """Initialize integrator.

        Args:
            memory_store: Semantic memory store
            graph_store: Knowledge graph store
            episodic_store: Episodic memory store
        """
        self.memory_store = memory_store
        self.graph_store = graph_store
        self.episodic_store = episodic_store

    def index_finding(
        self,
        finding: AggregatedFinding,
        task_id: int,
        project_id: int,
        tags: Optional[List[str]] = None,
    ) -> Optional[int]:
        """Index a research finding in semantic memory.

        Args:
            finding: The aggregated finding to index
            task_id: Research task ID
            project_id: Project ID
            tags: Optional tags for the finding

        Returns:
            Memory ID if successful, None otherwise
        """
        try:
            # Create content combining title, summary, and source info
            content = f"{finding.title}\n\n{finding.summary}"
            if finding.url:
                content += f"\n\nSource: {finding.url}"

            # Add source credibility info
            source_info = f"\nPrimary Source: {finding.primary_source} (credibility: {finding.final_credibility:.2f})"
            if finding.secondary_sources:
                source_info += f"\nValidated by: {', '.join(finding.secondary_sources)}"
            content += source_info

            # Create tags
            all_tags = tags or []
            all_tags.extend([
                f"research-{task_id}",
                f"source:{finding.primary_source}",
                "research-finding",
            ])

            # Add source tags
            if finding.secondary_sources:
                all_tags.append("cross-validated")

            # Store to semantic memory
            memory_id = self.memory_store.remember(
                content=content,
                memory_type="fact",
                tags=all_tags,
            )

            logger.info(f"Indexed finding {memory_id}: {finding.title[:50]}...")
            return memory_id

        except Exception as e:
            logger.error(f"Error indexing finding: {e}")
            return None

    def create_source_entity(
        self, source: str, credibility: float, project_id: Optional[int] = None
    ) -> Optional[int]:
        """Create or link a source entity in knowledge graph.

        Args:
            source: Source name (e.g., "arXiv", "GitHub")
            credibility: Source credibility score
            project_id: Optional project ID

        Returns:
            Entity ID if successful
        """
        try:
            from athena.graph.models import Entity, EntityType

            entity = Entity(
                name=source,
                entity_type=EntityType.CONCEPT,
                description=f"Research source with credibility score {credibility:.2f}",
            )

            entity_id = self.graph_store.create_entity(entity, project_id)
            logger.info(f"Created source entity: {source}")
            return entity_id

        except Exception as e:
            logger.error(f"Error creating source entity: {e}")
            return None

    def extract_entities(
        self, finding: AggregatedFinding
    ) -> List[tuple[str, str]]:
        """Extract potential entities from a finding.

        Args:
            finding: The finding to extract entities from

        Returns:
            List of (entity_name, entity_type) tuples
        """
        entities = []

        # Extract source entities
        entities.append((finding.primary_source, "source"))
        for secondary_source in finding.secondary_sources:
            entities.append((secondary_source, "source"))

        # Extract potential concepts from title
        # Simple approach: capitalize first word, add as concept
        words = finding.title.split()
        if words:
            potential_concept = words[0]
            if len(potential_concept) > 3:  # Only meaningful words
                entities.append((potential_concept, "concept"))

        return entities

    def record_research_session(
        self,
        task_id: int,
        topic: str,
        findings_count: int,
        high_confidence_count: int,
        sources_used: set,
        project_id: int,
    ) -> Optional[int]:
        """Record research session as episodic event.

        Args:
            task_id: Research task ID
            topic: Research topic
            findings_count: Total findings discovered
            high_confidence_count: Number of high-confidence findings
            sources_used: Set of sources searched
            project_id: Project ID

        Returns:
            Event ID if successful
        """
        try:
            content = (
                f"Completed research task on '{topic}'\n"
                f"Total findings: {findings_count}\n"
                f"High-confidence: {high_confidence_count}\n"
                f"Sources: {', '.join(sorted(sources_used))}"
            )

            event = EpisodicEvent(
                project_id=project_id,
                session_id=f"research-{task_id}",
                content=content,
                event_type=EventType.SUCCESS,
                outcome=EventOutcome.SUCCESS,
            )

            event_id = self.episodic_store.record_event(event, project_id)
            logger.info(f"Recorded research session event: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"Error recording research session: {e}")
            return None

    def build_finding_graph(
        self,
        finding: AggregatedFinding,
        task_id: int,
        project_id: Optional[int] = None,
    ) -> bool:
        """Build knowledge graph relationships for a finding.

        Args:
            finding: The finding to graph
            task_id: Research task ID
            project_id: Optional project ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create source entities if they don't exist
            source_entities = {}

            # Primary source
            if finding.primary_source not in source_entities:
                source_id = self.create_source_entity(
                    finding.primary_source, finding.base_credibility, project_id
                )
                if source_id:
                    source_entities[finding.primary_source] = source_id

            # Secondary sources
            for secondary_source in finding.secondary_sources:
                if secondary_source not in source_entities:
                    source_id = self.create_source_entity(
                        secondary_source, 0.8, project_id
                    )
                    if source_id:
                        source_entities[secondary_source] = source_id

            logger.info(
                f"Built knowledge graph for finding: {finding.title[:50]}..."
            )
            return True

        except Exception as e:
            logger.error(f"Error building finding graph: {e}")
            return False

    def query_research_findings(
        self, query: str, limit: int = 10
    ) -> List[dict]:
        """Query research findings from semantic memory.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching findings
        """
        try:
            # Search semantic memory for research-related findings
            results = self.memory_store.search(
                query=query,
                limit=limit,
                filters={"tags": ["research-finding"]},
            )

            return [
                {
                    "id": r.id,
                    "title": r.content[:100],  # Use first 100 chars as title
                    "content": r.content,
                    "credibility": r.metadata.get("credibility", 0.5)
                    if r.metadata
                    else 0.5,
                    "sources": r.metadata.get("sources", [])
                    if r.metadata
                    else [],
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Error querying research findings: {e}")
            return []

    def get_research_summary(self, task_id: int) -> dict:
        """Get summary of research task's memory integration.

        Args:
            task_id: Research task ID

        Returns:
            Summary dict with indexed findings, entities, etc.
        """
        try:
            # Search for findings from this task
            tag = f"research-{task_id}"
            findings = self.memory_store.search(
                query="",  # Empty query to get all
                limit=100,
                filters={"tags": [tag]},
            )

            if not findings:
                return {
                    "task_id": task_id,
                    "indexed_findings": 0,
                    "entities_created": 0,
                    "episodic_events": 0,
                }

            return {
                "task_id": task_id,
                "indexed_findings": len(findings),
                "average_relevance": sum(
                    f.metadata.get("relevance", 0.5) if f.metadata else 0.5
                    for f in findings
                ) / len(findings),
                "sources_represented": set(
                    f.metadata.get("sources", []) if f.metadata else [] for f in findings
                ),
            }

        except Exception as e:
            logger.error(f"Error getting research summary: {e}")
            return {"error": str(e)}
