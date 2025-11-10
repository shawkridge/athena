"""Pattern extraction from planning execution feedback.

Converts execution feedback data into generalizable planning patterns.
This is the core learning mechanism for the planning layer.

Process:
1. Cluster execution feedback by decomposition approach
2. Calculate aggregate metrics (success_rate, quality_score, token_efficiency)
3. Create PlanningPattern objects
4. Store patterns with provenance tracking
5. Update pattern metrics incrementally as feedback accumulates

Based on memory-mcp's episodic→semantic consolidation, adapted for planning domain.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import statistics

from ..planning.models import (
    PlanningPattern,
    DecompositionStrategy,
    ExecutionFeedback,
    PatternType,
)
from ..planning.store import PlanningStore
from ..core.database import Database

logger = logging.getLogger(__name__)


@dataclass
class ExecutionCluster:
    """A group of related execution feedback items."""

    cluster_id: str
    pattern_type: PatternType
    feedback_items: List[ExecutionFeedback]
    created_at: datetime


@dataclass
class ExtractedPlanningPattern:
    """Pattern extracted from execution cluster."""

    pattern_type: PatternType
    name: str
    description: str
    success_rate: float
    quality_score: float
    execution_count: int
    applicable_domains: List[str]
    applicable_task_types: List[str]
    source_feedback_ids: List[int]
    confidence: float  # How confident are we in this pattern?
    evidence: str  # Why this pattern was extracted


class ExecutionClusterer:
    """Group similar executions together for pattern extraction."""

    def __init__(self):
        """Initialize clusterer."""
        self.clusters: Dict[str, ExecutionCluster] = {}

    def cluster_by_decomposition(
        self,
        feedback_items: List[ExecutionFeedback],
    ) -> Dict[str, ExecutionCluster]:
        """
        Cluster execution feedback by decomposition approach.

        Groups executions that used similar decomposition strategies
        (e.g., all "hierarchical" decompositions go together).

        Args:
            feedback_items: List of ExecutionFeedback objects

        Returns:
            Dictionary mapping cluster_id to ExecutionCluster
        """
        clusters: Dict[str, ExecutionCluster] = defaultdict(list)

        # Group by pattern type if available
        for feedback in feedback_items:
            if feedback.pattern_id:
                # Link to existing pattern
                cluster_key = f"pattern_{feedback.pattern_id}"
                clusters[cluster_key].append(feedback)
            else:
                # Infer pattern type from task characteristics
                # For now, group all together (will be refined in Phase 2)
                cluster_key = "unclassified"
                clusters[cluster_key].append(feedback)

        # Convert to ExecutionCluster objects
        result = {}
        for cluster_key, feedback_list in clusters.items():
            if not feedback_list:
                continue

            # Infer pattern type from majority of feedbacks
            pattern_type = self._infer_pattern_type(feedback_list)

            cluster = ExecutionCluster(
                cluster_id=cluster_key,
                pattern_type=pattern_type,
                feedback_items=feedback_list,
                created_at=datetime.now(),
            )
            result[cluster_key] = cluster

        return result

    @staticmethod
    def _infer_pattern_type(feedback_items: List[ExecutionFeedback]) -> PatternType:
        """
        Infer pattern type from feedback items.

        For Phase 1, use simple heuristics:
        - If many blockers: hierarchical (better error detection)
        - If short duration: flat (simple tasks)
        - Default: hybrid (flexible)
        """
        if not feedback_items:
            return PatternType.HYBRID

        total_blockers = sum(len(f.blockers_encountered) for f in feedback_items)
        avg_blockers = total_blockers / len(feedback_items)

        if avg_blockers > 1.5:
            return PatternType.HIERARCHICAL
        elif avg_blockers < 0.5:
            return PatternType.FLAT
        else:
            return PatternType.HYBRID


class PlanningPatternExtractor:
    """Extract planning patterns from execution feedback."""

    def __init__(self, planning_store: PlanningStore, db: Database):
        """
        Initialize pattern extractor.

        Args:
            planning_store: PlanningStore for database operations
            db: Database instance for direct access
        """
        self.store = planning_store
        self.db = db
        self.clusterer = ExecutionClusterer()

    def extract_patterns(
        self,
        project_id: int,
        feedback_items: List[ExecutionFeedback],
        min_confidence: float = 0.65,
    ) -> List[ExtractedPlanningPattern]:
        """
        Extract planning patterns from execution feedback.

        Algorithm:
        1. Cluster feedback by decomposition approach
        2. Calculate metrics for each cluster
        3. Create PlanningPattern objects
        4. Validate patterns against source data
        5. Return patterns meeting confidence threshold

        Args:
            project_id: Project ID
            feedback_items: List of ExecutionFeedback objects
            min_confidence: Minimum confidence threshold for pattern creation

        Returns:
            List of ExtractedPlanningPattern objects
        """
        if not feedback_items or len(feedback_items) < 2:
            logger.debug(f"Insufficient feedback for pattern extraction (got {len(feedback_items)})")
            return []

        logger.info(f"Extracting patterns from {len(feedback_items)} feedback items (project {project_id})")

        # Step 1: Cluster feedback
        clusters = self.clusterer.cluster_by_decomposition(feedback_items)
        logger.debug(f"Created {len(clusters)} clusters")

        # Step 2: Extract patterns from clusters
        patterns = []
        for cluster in clusters.values():
            extracted = self._extract_pattern_from_cluster(project_id, cluster)
            if extracted and extracted.confidence >= min_confidence:
                patterns.append(extracted)
                logger.debug(
                    f"Extracted pattern: {extracted.name} (confidence: {extracted.confidence:.2f})"
                )

        logger.info(f"Extracted {len(patterns)} patterns with confidence ≥ {min_confidence}")
        return patterns

    def _extract_pattern_from_cluster(
        self,
        project_id: int,
        cluster: ExecutionCluster,
    ) -> Optional[ExtractedPlanningPattern]:
        """
        Extract a single pattern from an execution cluster.

        Args:
            project_id: Project ID
            cluster: ExecutionCluster to analyze

        Returns:
            ExtractedPlanningPattern or None if extraction failed
        """
        feedback_items = cluster.feedback_items

        if not feedback_items:
            return None

        # Calculate metrics
        def is_success(outcome) -> bool:
            """Check if outcome is success."""
            if hasattr(outcome, 'value'):
                return outcome.value == "success"
            return str(outcome) == "success"

        success_count = sum(1 for f in feedback_items if is_success(f.execution_outcome))
        success_rate = success_count / len(feedback_items)

        quality_scores = [
            f.execution_quality_score
            for f in feedback_items
            if f.execution_quality_score is not None
        ]
        quality_score = statistics.mean(quality_scores) if quality_scores else 0.5

        # Extract domains and task types from feedback
        domains = self._extract_domains(feedback_items)
        task_types = self._extract_task_types(feedback_items)

        # Calculate confidence
        confidence = self._calculate_confidence(
            len(feedback_items),
            success_rate,
            quality_score,
        )

        # Generate pattern name and description
        pattern_name = self._generate_pattern_name(cluster.pattern_type, domains, task_types)
        description = self._generate_description(
            cluster.pattern_type,
            success_rate,
            len(feedback_items),
            domains,
        )

        # Generate evidence
        evidence = (
            f"Extracted from {len(feedback_items)} executions. "
            f"Success rate: {success_rate:.1%}. "
            f"Quality: {quality_score:.2f}. "
            f"Domains: {', '.join(domains)}."
        )

        source_feedback_ids = [f.id for f in feedback_items if f.id]

        return ExtractedPlanningPattern(
            pattern_type=cluster.pattern_type,
            name=pattern_name,
            description=description,
            success_rate=success_rate,
            quality_score=quality_score,
            execution_count=len(feedback_items),
            applicable_domains=domains,
            applicable_task_types=task_types,
            source_feedback_ids=source_feedback_ids,
            confidence=confidence,
            evidence=evidence,
        )

    @staticmethod
    def _extract_domains(feedback_items: List[ExecutionFeedback]) -> List[str]:
        """Extract domains from feedback (Phase 1: placeholder)."""
        # In Phase 1, we don't have explicit domain tracking
        # Phase 2 will add this via task metadata
        return ["general"]

    @staticmethod
    def _extract_task_types(feedback_items: List[ExecutionFeedback]) -> List[str]:
        """Extract task types from feedback (Phase 1: infer from phase)."""
        task_types = set()

        for f in feedback_items:
            if f.phase_number:
                task_types.add(f"phase_{f.phase_number}")

        return list(task_types) if task_types else ["general"]

    @staticmethod
    def _calculate_confidence(
        execution_count: int,
        success_rate: float,
        quality_score: float,
    ) -> float:
        """
        Calculate confidence in extracted pattern.

        Factors:
        - Execution count: More data = higher confidence
        - Success rate: Consistent results = higher confidence
        - Quality: Higher quality = higher confidence

        Args:
            execution_count: Number of executions in cluster
            success_rate: Success rate (0-1)
            quality_score: Quality score (0-1)

        Returns:
            Confidence score (0-1)
        """
        # Execution count confidence: saturates at 10+ executions
        count_confidence = min(execution_count / 10.0, 1.0)

        # Consistency confidence: peaked at 0.8-0.9 success rate
        consistency_confidence = 1.0 - abs(success_rate - 0.85)

        # Quality confidence: high quality = more reliable
        quality_confidence = quality_score

        # Weighted average
        confidence = (
            0.5 * count_confidence +
            0.3 * consistency_confidence +
            0.2 * quality_confidence
        )

        return min(max(confidence, 0.0), 1.0)

    @staticmethod
    def _generate_pattern_name(
        pattern_type: PatternType,
        domains: List[str],
        task_types: List[str],
    ) -> str:
        """Generate descriptive pattern name."""
        domain = domains[0] if domains else "general"
        task_type = task_types[0] if task_types else "task"
        pattern_str = pattern_type.value if hasattr(pattern_type, 'value') else str(pattern_type)

        return f"{pattern_str}-{domain}-{task_type}".replace("_", "-")

    @staticmethod
    def _generate_description(
        pattern_type: PatternType,
        success_rate: float,
        execution_count: int,
        domains: List[str],
    ) -> str:
        """Generate pattern description."""
        pattern_str = pattern_type.value if hasattr(pattern_type, 'value') else str(pattern_type)
        domain_str = ", ".join(domains) if domains else "general"

        return (
            f"{pattern_str.title()} decomposition approach with {success_rate:.1%} success rate. "
            f"Based on {execution_count} executions in {domain_str} domain."
        )


class ConsolidationRouter:
    """Route execution feedback to pattern learning."""

    def __init__(self, planning_store: PlanningStore, db: Database):
        """
        Initialize consolidation router.

        Args:
            planning_store: PlanningStore instance
            db: Database instance
        """
        self.store = planning_store
        self.db = db
        self.extractor = PlanningPatternExtractor(planning_store, db)

    def process_execution_feedback(
        self,
        project_id: int,
        feedback: ExecutionFeedback,
        consolidation_threshold: int = 5,
    ) -> Optional[PlanningPattern]:
        """
        Process new execution feedback and optionally trigger consolidation.

        Args:
            project_id: Project ID
            feedback: ExecutionFeedback to process
            consolidation_threshold: Trigger consolidation after N feedback items

        Returns:
            Learned pattern if consolidation triggered, else None
        """
        # Store the feedback
        feedback_id = self.store.record_execution_feedback(feedback)
        logger.debug(f"Recorded execution feedback (ID: {feedback_id})")

        # Check if we should trigger consolidation
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM execution_feedback WHERE project_id = ?",
            (project_id,),
        )
        total_feedback = cursor.fetchone()[0]

        if total_feedback % consolidation_threshold == 0:
            logger.info(
                f"Consolidation threshold reached ({total_feedback} feedback items). "
                "Triggering pattern extraction..."
            )
            return self.consolidate_patterns(project_id)

        return None

    def consolidate_patterns(
        self,
        project_id: int,
        min_confidence: float = 0.65,
    ) -> Optional[PlanningPattern]:
        """
        Trigger pattern consolidation for a project.

        Args:
            project_id: Project ID
            min_confidence: Minimum confidence threshold

        Returns:
            Most important learned pattern (for notification), or None
        """
        # Retrieve all feedback for project
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT * FROM execution_feedback WHERE project_id = ? ORDER BY created_at DESC LIMIT 50",
            (project_id,),
        )

        feedback_rows = cursor.fetchall()
        feedback_items = [
            self.store._row_to_execution_feedback(row)
            for row in feedback_rows
        ]
        feedback_items = [f for f in feedback_items if f]

        if not feedback_items:
            logger.debug(f"No feedback found for project {project_id}")
            return None

        # Extract patterns
        extracted_patterns = self.extractor.extract_patterns(
            project_id,
            feedback_items,
            min_confidence=min_confidence,
        )

        if not extracted_patterns:
            logger.debug("No patterns extracted")
            return None

        # Store patterns
        stored_patterns = []
        for extracted in extracted_patterns:
            # Check if pattern already exists
            existing = self.store.find_patterns_by_task_type(
                project_id,
                extracted.applicable_task_types[0] if extracted.applicable_task_types else "general",
                limit=1,
            )

            if existing and existing[0].name == extracted.name:
                # Update existing pattern
                self.store.update_planning_pattern_metrics(
                    existing[0].id,
                    extracted.success_rate,
                    extracted.quality_score,
                    existing[0].execution_count + extracted.execution_count,
                )
                logger.debug(f"Updated existing pattern: {extracted.name}")
            else:
                # Create new pattern
                pattern = PlanningPattern(
                    project_id=project_id,
                    pattern_type=extracted.pattern_type,
                    name=extracted.name,
                    description=extracted.description,
                    success_rate=extracted.success_rate,
                    quality_score=extracted.quality_score,
                    execution_count=extracted.execution_count,
                    applicable_domains=extracted.applicable_domains,
                    applicable_task_types=extracted.applicable_task_types,
                    source="learned",
                    created_at=datetime.now(),
                )
                pattern_id = self.store.create_planning_pattern(pattern)
                logger.info(f"Created new pattern: {extracted.name} (ID: {pattern_id})")

                # Convert back to PlanningPattern object for return
                stored_pattern = self.store.get_planning_pattern(pattern_id)
                if stored_pattern:
                    stored_patterns.append(stored_pattern)

        # Return most important pattern (highest success rate)
        if stored_patterns:
            return max(stored_patterns, key=lambda p: p.success_rate)

        return None


# Convenience functions

def consolidate_project_patterns(
    planning_store: PlanningStore,
    db: Database,
    project_id: int,
) -> Optional[PlanningPattern]:
    """
    Consolidate patterns for a project.

    Args:
        planning_store: PlanningStore instance
        db: Database instance
        project_id: Project ID to consolidate

    Returns:
        Most important learned pattern, or None
    """
    router = ConsolidationRouter(planning_store, db)
    return router.consolidate_patterns(project_id)


def process_feedback_and_consolidate(
    planning_store: PlanningStore,
    db: Database,
    project_id: int,
    feedback: ExecutionFeedback,
    consolidation_threshold: int = 5,
) -> Optional[PlanningPattern]:
    """
    Process feedback and optionally consolidate.

    Args:
        planning_store: PlanningStore instance
        db: Database instance
        project_id: Project ID
        feedback: ExecutionFeedback to process
        consolidation_threshold: Consolidation trigger threshold

    Returns:
        Learned pattern if triggered, else None
    """
    router = ConsolidationRouter(planning_store, db)
    return router.process_execution_feedback(project_id, feedback, consolidation_threshold)
