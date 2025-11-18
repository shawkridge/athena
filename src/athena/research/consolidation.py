"""Research consolidation store for Phase 3.3.

Provides sync access to research consolidation tables (patterns, expertise,
credibility, thresholds, strategies, graph entities/relations).

Uses BaseStore pattern for consistency with Athena architecture.
"""

import json
import logging
from typing import Optional, List, Dict, Any

from ..core.base_store import BaseStore
from ..core.database import Database
from .models import (
    ResearchPattern,
    ResearchPatternType,
    AgentDomainExpertise,
    SourceDomainCredibility,
    QualityThreshold,
    SearchStrategy,
    ResearchGraphEntity,
    ResearchGraphRelation,
    ResearchConsolidationRun,
)

logger = logging.getLogger(__name__)


class ResearchConsolidationStore(BaseStore):
    """Manages research consolidation data (patterns, expertise, strategies)."""

    def __init__(self, db: Optional[Database] = None):
        """Initialize store with database."""
        super().__init__(db)

    # =========================================================================
    # PATTERNS
    # =========================================================================

    def create_pattern(self, pattern: ResearchPattern) -> Optional[int]:
        """Create a new research pattern.

        Args:
            pattern: ResearchPattern instance

        Returns:
            Pattern ID or None if failed
        """
        try:
            cursor = self.execute(
                """
                INSERT INTO research_patterns (
                    task_id, pattern_type, pattern_content,
                    confidence, metrics, source_findings, finding_count, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    pattern.task_id,
                    (
                        pattern.pattern_type.value
                        if isinstance(pattern.pattern_type, ResearchPatternType)
                        else pattern.pattern_type
                    ),
                    pattern.pattern_content,
                    pattern.confidence,
                    json.dumps(pattern.metrics),
                    pattern.source_findings,
                    pattern.finding_count,
                    pattern.created_at,
                ),
                fetch_one=True,
            )
            self.commit()
            return cursor[0] if cursor else None
        except Exception as e:
            logger.error(f"Failed to create pattern: {e}")
            return None

    def get_patterns_by_task(self, task_id: int) -> List[ResearchPattern]:
        """Get all patterns for a research task.

        Args:
            task_id: Research task ID

        Returns:
            List of ResearchPattern instances
        """
        try:
            rows = self.execute(
                "SELECT * FROM research_patterns WHERE task_id = %s ORDER BY created_at DESC",
                (task_id,),
                fetch_all=True,
            )
            return [self._row_to_pattern(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get patterns: {e}")
            return []

    def _row_to_pattern(self, row: Dict[str, Any]) -> ResearchPattern:
        """Convert database row to ResearchPattern model."""
        if not isinstance(row, dict):
            row = dict(row) if hasattr(row, "items") else {}

        metrics = {}
        if row.get("metrics"):
            metrics = self.deserialize_json(row.get("metrics"), {})

        return ResearchPattern(
            id=row.get("id"),
            task_id=row.get("task_id"),
            pattern_type=row.get("pattern_type"),
            pattern_content=row.get("pattern_content"),
            confidence=row.get("confidence", 0.0),
            metrics=metrics,
            source_findings=row.get("source_findings") or [],
            finding_count=row.get("finding_count", 0),
            created_at=int(row.get("created_at", 0)),
        )

    # =========================================================================
    # AGENT EXPERTISE
    # =========================================================================

    def upsert_agent_expertise(self, expertise: AgentDomainExpertise) -> Optional[int]:
        """Create or update agent domain expertise.

        Args:
            expertise: AgentDomainExpertise instance

        Returns:
            Expertise ID or None if failed
        """
        try:
            cursor = self.execute(
                """
                INSERT INTO agent_domain_expertise (
                    agent_name, domain, total_findings,
                    avg_credibility, successful_tasks, confidence, last_updated
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(agent_name, domain) DO UPDATE SET
                    total_findings = EXCLUDED.total_findings,
                    avg_credibility = EXCLUDED.avg_credibility,
                    successful_tasks = EXCLUDED.successful_tasks,
                    confidence = EXCLUDED.confidence,
                    last_updated = EXCLUDED.last_updated
                RETURNING id
            """,
                (
                    expertise.agent_name,
                    expertise.domain,
                    expertise.total_findings,
                    expertise.avg_credibility,
                    expertise.successful_tasks,
                    expertise.confidence,
                    expertise.last_updated,
                ),
                fetch_one=True,
            )
            self.commit()
            return cursor[0] if cursor else None
        except Exception as e:
            logger.error(f"Failed to upsert agent expertise: {e}")
            return None

    def get_agent_expertise(self, agent_name: str, domain: str) -> Optional[AgentDomainExpertise]:
        """Get expertise for a specific agent/domain combination.

        Args:
            agent_name: Agent name
            domain: Domain name

        Returns:
            AgentDomainExpertise or None
        """
        try:
            row = self.execute(
                "SELECT * FROM agent_domain_expertise WHERE agent_name = %s AND domain = %s",
                (agent_name, domain),
                fetch_one=True,
            )
            if not row:
                return None
            return self._row_to_agent_expertise(row)
        except Exception as e:
            logger.error(f"Failed to get agent expertise: {e}")
            return None

    def get_agent_domains(self, agent_name: str) -> List[AgentDomainExpertise]:
        """Get all domains where an agent has expertise.

        Args:
            agent_name: Agent name

        Returns:
            List of AgentDomainExpertise instances
        """
        try:
            rows = self.execute(
                "SELECT * FROM agent_domain_expertise WHERE agent_name = %s ORDER BY avg_credibility DESC",
                (agent_name,),
                fetch_all=True,
            )
            return [self._row_to_agent_expertise(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get agent domains: {e}")
            return []

    def _row_to_agent_expertise(self, row: Dict[str, Any]) -> AgentDomainExpertise:
        """Convert database row to AgentDomainExpertise model."""
        if not isinstance(row, dict):
            row = dict(row) if hasattr(row, "items") else {}

        return AgentDomainExpertise(
            id=row.get("id"),
            agent_name=row.get("agent_name"),
            domain=row.get("domain"),
            total_findings=row.get("total_findings", 0),
            avg_credibility=row.get("avg_credibility", 0.0),
            successful_tasks=row.get("successful_tasks", 0),
            confidence=row.get("confidence", 0.5),
            last_updated=int(row.get("last_updated", 0)),
        )

    # =========================================================================
    # SOURCE CREDIBILITY
    # =========================================================================

    def upsert_source_credibility(self, credibility: SourceDomainCredibility) -> Optional[int]:
        """Create or update source domain credibility.

        Args:
            credibility: SourceDomainCredibility instance

        Returns:
            Credibility ID or None if failed
        """
        try:
            cursor = self.execute(
                """
                INSERT INTO source_domain_credibility (
                    source, domain, avg_credibility, finding_count,
                    cross_validation_rate, temporal_trend, confidence, last_updated
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(source, domain) DO UPDATE SET
                    avg_credibility = EXCLUDED.avg_credibility,
                    finding_count = EXCLUDED.finding_count,
                    cross_validation_rate = EXCLUDED.cross_validation_rate,
                    temporal_trend = EXCLUDED.temporal_trend,
                    confidence = EXCLUDED.confidence,
                    last_updated = EXCLUDED.last_updated
                RETURNING id
            """,
                (
                    credibility.source,
                    credibility.domain,
                    credibility.avg_credibility,
                    credibility.finding_count,
                    credibility.cross_validation_rate,
                    credibility.temporal_trend,
                    credibility.confidence,
                    credibility.last_updated,
                ),
                fetch_one=True,
            )
            self.commit()
            return cursor[0] if cursor else None
        except Exception as e:
            logger.error(f"Failed to upsert source credibility: {e}")
            return None

    def get_sources_for_domain(self, domain: str) -> List[SourceDomainCredibility]:
        """Get all sources ranked by credibility for a domain.

        Args:
            domain: Domain name

        Returns:
            List of SourceDomainCredibility instances sorted by credibility DESC
        """
        try:
            rows = self.execute(
                "SELECT * FROM source_domain_credibility WHERE domain = %s ORDER BY avg_credibility DESC",
                (domain,),
                fetch_all=True,
            )
            return [self._row_to_source_credibility(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get sources for domain: {e}")
            return []

    def _row_to_source_credibility(self, row: Dict[str, Any]) -> SourceDomainCredibility:
        """Convert database row to SourceDomainCredibility model."""
        if not isinstance(row, dict):
            row = dict(row) if hasattr(row, "items") else {}

        return SourceDomainCredibility(
            id=row.get("id"),
            source=row.get("source"),
            domain=row.get("domain"),
            avg_credibility=row.get("avg_credibility", 0.5),
            finding_count=row.get("finding_count", 0),
            cross_validation_rate=row.get("cross_validation_rate"),
            temporal_trend=row.get("temporal_trend"),
            confidence=row.get("confidence", 0.5),
            last_updated=int(row.get("last_updated", 0)),
        )

    # =========================================================================
    # QUALITY THRESHOLDS
    # =========================================================================

    def upsert_quality_threshold(self, threshold: QualityThreshold) -> Optional[int]:
        """Create or update quality threshold for a domain.

        Args:
            threshold: QualityThreshold instance

        Returns:
            Threshold ID or None if failed
        """
        try:
            cursor = self.execute(
                """
                INSERT INTO quality_thresholds (
                    domain, threshold_optimal, threshold_strict, threshold_lenient,
                    findings_tested, retention_rate_optimal, last_updated
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(domain) DO UPDATE SET
                    threshold_optimal = EXCLUDED.threshold_optimal,
                    threshold_strict = EXCLUDED.threshold_strict,
                    threshold_lenient = EXCLUDED.threshold_lenient,
                    findings_tested = EXCLUDED.findings_tested,
                    retention_rate_optimal = EXCLUDED.retention_rate_optimal,
                    last_updated = EXCLUDED.last_updated
                RETURNING id
            """,
                (
                    threshold.domain,
                    threshold.threshold_optimal,
                    threshold.threshold_strict,
                    threshold.threshold_lenient,
                    threshold.findings_tested,
                    threshold.retention_rate_optimal,
                    threshold.last_updated,
                ),
                fetch_one=True,
            )
            self.commit()
            return cursor[0] if cursor else None
        except Exception as e:
            logger.error(f"Failed to upsert quality threshold: {e}")
            return None

    def get_quality_threshold(self, domain: str) -> Optional[QualityThreshold]:
        """Get quality threshold for a domain.

        Args:
            domain: Domain name

        Returns:
            QualityThreshold or None
        """
        try:
            row = self.execute(
                "SELECT * FROM quality_thresholds WHERE domain = %s",
                (domain,),
                fetch_one=True,
            )
            if not row:
                return None
            return self._row_to_quality_threshold(row)
        except Exception as e:
            logger.error(f"Failed to get quality threshold: {e}")
            return None

    def _row_to_quality_threshold(self, row: Dict[str, Any]) -> QualityThreshold:
        """Convert database row to QualityThreshold model."""
        if not isinstance(row, dict):
            row = dict(row) if hasattr(row, "items") else {}

        return QualityThreshold(
            id=row.get("id"),
            domain=row.get("domain"),
            threshold_optimal=row.get("threshold_optimal", 0.75),
            threshold_strict=row.get("threshold_strict", 0.85),
            threshold_lenient=row.get("threshold_lenient", 0.60),
            findings_tested=row.get("findings_tested", 0),
            retention_rate_optimal=row.get("retention_rate_optimal"),
            last_updated=int(row.get("last_updated", 0)),
        )

    # =========================================================================
    # SEARCH STRATEGIES
    # =========================================================================

    def upsert_search_strategy(self, strategy: SearchStrategy) -> Optional[int]:
        """Create or update search strategy.

        Args:
            strategy: SearchStrategy instance

        Returns:
            Strategy ID or None if failed
        """
        try:
            cursor = self.execute(
                """
                INSERT INTO search_strategies (
                    name, domain, description, recommended_sources, excluded_sources,
                    expected_quality, expected_findings_per_query, success_count,
                    failure_count, created_from_patterns, procedure_id, confidence, last_updated
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(domain, name) DO UPDATE SET
                    description = EXCLUDED.description,
                    recommended_sources = EXCLUDED.recommended_sources,
                    excluded_sources = EXCLUDED.excluded_sources,
                    expected_quality = EXCLUDED.expected_quality,
                    success_count = EXCLUDED.success_count,
                    failure_count = EXCLUDED.failure_count,
                    confidence = EXCLUDED.confidence,
                    last_updated = EXCLUDED.last_updated
                RETURNING id
            """,
                (
                    strategy.name,
                    strategy.domain,
                    strategy.description,
                    strategy.recommended_sources,
                    strategy.excluded_sources,
                    strategy.expected_quality,
                    strategy.expected_findings_per_query,
                    strategy.success_count,
                    strategy.failure_count,
                    strategy.created_from_patterns,
                    strategy.procedure_id,
                    strategy.confidence,
                    strategy.last_updated,
                ),
                fetch_one=True,
            )
            self.commit()
            return cursor[0] if cursor else None
        except Exception as e:
            logger.error(f"Failed to upsert search strategy: {e}")
            return None

    def get_strategies_for_domain(self, domain: str) -> List[SearchStrategy]:
        """Get all strategies for a domain.

        Args:
            domain: Domain name

        Returns:
            List of SearchStrategy instances sorted by confidence DESC
        """
        try:
            rows = self.execute(
                "SELECT * FROM search_strategies WHERE domain = %s ORDER BY confidence DESC",
                (domain,),
                fetch_all=True,
            )
            return [self._row_to_search_strategy(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get strategies for domain: {e}")
            return []

    def _row_to_search_strategy(self, row: Dict[str, Any]) -> SearchStrategy:
        """Convert database row to SearchStrategy model."""
        if not isinstance(row, dict):
            row = dict(row) if hasattr(row, "items") else {}

        return SearchStrategy(
            id=row.get("id"),
            name=row.get("name"),
            domain=row.get("domain"),
            description=row.get("description"),
            recommended_sources=row.get("recommended_sources") or [],
            excluded_sources=row.get("excluded_sources") or [],
            expected_quality=row.get("expected_quality", 0.8),
            expected_findings_per_query=row.get("expected_findings_per_query", 50),
            success_count=row.get("success_count", 0),
            failure_count=row.get("failure_count", 0),
            created_from_patterns=row.get("created_from_patterns") or [],
            procedure_id=row.get("procedure_id"),
            confidence=row.get("confidence", 0.5),
            last_updated=int(row.get("last_updated", 0)),
        )

    # =========================================================================
    # GRAPH ENTITIES
    # =========================================================================

    def create_graph_entity(self, entity: ResearchGraphEntity) -> Optional[int]:
        """Create a new graph entity.

        Args:
            entity: ResearchGraphEntity instance

        Returns:
            Entity ID or None if failed
        """
        try:
            cursor = self.execute(
                """
                INSERT INTO research_graph_entities (
                    task_id, entity_name, entity_type,
                    mentioned_in_findings, frequency, confidence, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    entity.task_id,
                    entity.entity_name,
                    entity.entity_type,
                    entity.mentioned_in_findings,
                    entity.frequency,
                    entity.confidence,
                    entity.created_at,
                ),
                fetch_one=True,
            )
            self.commit()
            return cursor[0] if cursor else None
        except Exception as e:
            logger.error(f"Failed to create graph entity: {e}")
            return None

    def get_entities_for_task(self, task_id: int) -> List[ResearchGraphEntity]:
        """Get all entities for a research task.

        Args:
            task_id: Research task ID

        Returns:
            List of ResearchGraphEntity instances
        """
        try:
            rows = self.execute(
                "SELECT * FROM research_graph_entities WHERE task_id = %s ORDER BY frequency DESC",
                (task_id,),
                fetch_all=True,
            )
            return [self._row_to_graph_entity(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get entities: {e}")
            return []

    def _row_to_graph_entity(self, row: Dict[str, Any]) -> ResearchGraphEntity:
        """Convert database row to ResearchGraphEntity model."""
        if not isinstance(row, dict):
            row = dict(row) if hasattr(row, "items") else {}

        return ResearchGraphEntity(
            id=row.get("id"),
            task_id=row.get("task_id"),
            entity_name=row.get("entity_name"),
            entity_type=row.get("entity_type"),
            mentioned_in_findings=row.get("mentioned_in_findings") or [],
            frequency=row.get("frequency", 1),
            confidence=row.get("confidence", 0.8),
            created_at=int(row.get("created_at", 0)),
        )

    # =========================================================================
    # GRAPH RELATIONS
    # =========================================================================

    def create_graph_relation(self, relation: ResearchGraphRelation) -> Optional[int]:
        """Create a new graph relation.

        Args:
            relation: ResearchGraphRelation instance

        Returns:
            Relation ID or None if failed
        """
        try:
            cursor = self.execute(
                """
                INSERT INTO research_graph_relations (
                    task_id, source_entity, relation_type, target_entity,
                    strength, source_findings, confidence, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    relation.task_id,
                    relation.source_entity,
                    relation.relation_type,
                    relation.target_entity,
                    relation.strength,
                    relation.source_findings,
                    relation.confidence,
                    relation.created_at,
                ),
                fetch_one=True,
            )
            self.commit()
            return cursor[0] if cursor else None
        except Exception as e:
            logger.error(f"Failed to create graph relation: {e}")
            return None

    def get_relations_for_task(self, task_id: int) -> List[ResearchGraphRelation]:
        """Get all relations for a research task.

        Args:
            task_id: Research task ID

        Returns:
            List of ResearchGraphRelation instances
        """
        try:
            rows = self.execute(
                "SELECT * FROM research_graph_relations WHERE task_id = %s ORDER BY strength DESC",
                (task_id,),
                fetch_all=True,
            )
            return [self._row_to_graph_relation(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get relations: {e}")
            return []

    def _row_to_graph_relation(self, row: Dict[str, Any]) -> ResearchGraphRelation:
        """Convert database row to ResearchGraphRelation model."""
        if not isinstance(row, dict):
            row = dict(row) if hasattr(row, "items") else {}

        return ResearchGraphRelation(
            id=row.get("id"),
            task_id=row.get("task_id"),
            source_entity=row.get("source_entity"),
            relation_type=row.get("relation_type"),
            target_entity=row.get("target_entity"),
            strength=row.get("strength", 0.8),
            source_findings=row.get("source_findings") or [],
            confidence=row.get("confidence", 0.8),
            created_at=int(row.get("created_at", 0)),
        )

    # =========================================================================
    # CONSOLIDATION RUNS
    # =========================================================================

    def create_consolidation_run(self, run: ResearchConsolidationRun) -> Optional[int]:
        """Create a new consolidation run.

        Args:
            run: ResearchConsolidationRun instance

        Returns:
            Run ID or None if failed
        """
        try:
            cursor = self.execute(
                """
                INSERT INTO research_consolidation_runs (
                    task_id, started_at, completed_at, status,
                    patterns_extracted, procedures_created, entities_created,
                    relations_created, expertise_updates, strategy_improvements, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    run.task_id,
                    run.started_at,
                    run.completed_at,
                    run.status,
                    run.patterns_extracted,
                    run.procedures_created,
                    run.entities_created,
                    run.relations_created,
                    run.expertise_updates,
                    run.strategy_improvements,
                    run.error_message,
                ),
                fetch_one=True,
            )
            self.commit()
            return cursor[0] if cursor else None
        except Exception as e:
            logger.error(f"Failed to create consolidation run: {e}")
            return None

    def update_consolidation_run(self, run: ResearchConsolidationRun) -> bool:
        """Update consolidation run status.

        Args:
            run: Updated ResearchConsolidationRun instance

        Returns:
            True if successful, False otherwise
        """
        try:
            self.execute(
                """
                UPDATE research_consolidation_runs SET
                    completed_at = %s, status = %s,
                    patterns_extracted = %s, procedures_created = %s,
                    entities_created = %s, relations_created = %s,
                    expertise_updates = %s, strategy_improvements = %s,
                    error_message = %s
                WHERE task_id = %s
            """,
                (
                    run.completed_at,
                    run.status,
                    run.patterns_extracted,
                    run.procedures_created,
                    run.entities_created,
                    run.relations_created,
                    run.expertise_updates,
                    run.strategy_improvements,
                    run.error_message,
                    run.task_id,
                ),
            )
            self.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update consolidation run: {e}")
            return False

    def get_consolidation_run(self, task_id: int) -> Optional[ResearchConsolidationRun]:
        """Get consolidation run for a task.

        Args:
            task_id: Research task ID

        Returns:
            ResearchConsolidationRun or None
        """
        try:
            row = self.execute(
                "SELECT * FROM research_consolidation_runs WHERE task_id = %s",
                (task_id,),
                fetch_one=True,
            )
            if not row:
                return None
            return self._row_to_consolidation_run(row)
        except Exception as e:
            logger.error(f"Failed to get consolidation run: {e}")
            return None

    def _row_to_consolidation_run(self, row: Dict[str, Any]) -> ResearchConsolidationRun:
        """Convert database row to ResearchConsolidationRun model."""
        if not isinstance(row, dict):
            row = dict(row) if hasattr(row, "items") else {}

        return ResearchConsolidationRun(
            id=row.get("id"),
            task_id=row.get("task_id"),
            started_at=int(row.get("started_at", 0)),
            completed_at=int(row.get("completed_at", 0)) if row.get("completed_at") else None,
            status=row.get("status", "running"),
            patterns_extracted=row.get("patterns_extracted", 0),
            procedures_created=row.get("procedures_created", 0),
            entities_created=row.get("entities_created", 0),
            relations_created=row.get("relations_created", 0),
            expertise_updates=row.get("expertise_updates", 0),
            strategy_improvements=row.get("strategy_improvements", 0),
            error_message=row.get("error_message"),
        )
