"""Memory Improvement Pipeline - integrates reconsolidation, evidence inference, and contradiction resolution.

This orchestrator runs during the nightly consolidation dream to:
1. Activate reconsolidation windows for retrieved memories
2. Infer evidence types for episodic events
3. Detect and resolve contradictory memories
4. Consolidate labile memories back to active state

Designed to be called from the main dreaming.py during consolidation.
"""

import logging
from typing import Dict, Optional

from ..core.database import Database
from .reconsolidation_activator import ReconsolidationActivator
from .evidence_inferencer import EvidenceInferencer
from .contradiction_detector import ContradictionDetector

logger = logging.getLogger(__name__)


class MemoryImprovementPipeline:
    """Orchestrates memory quality improvements during consolidation."""

    def __init__(self, db: Database):
        """Initialize pipeline with database.

        Args:
            db: Database instance
        """
        self.db = db
        self.reconsolidation = ReconsolidationActivator(db)
        self.evidence = EvidenceInferencer(db)
        self.contradictions = ContradictionDetector(db)

    async def run_full_pipeline(self, project_id: Optional[int] = None) -> Dict[str, int]:
        """Run complete memory improvement pipeline for a project.

        Called during nightly dream consolidation.

        Args:
            project_id: Optional project to focus on. If None, runs across all projects.

        Returns:
            Dictionary with metrics:
            {
                'labile_consolidated': int,  # Memories moved out of lability window
                'evidence_types_inferred': int,  # New evidence types assigned
                'contradictions_detected': int,  # Contradictions found
                'contradictions_resolved': int,  # Contradictions resolved
            }
        """
        metrics = {
            "labile_consolidated": 0,
            "evidence_types_inferred": 0,
            "contradictions_detected": 0,
            "contradictions_resolved": 0,
            "pipeline_duration_seconds": 0,
        }

        import time

        start_time = time.time()

        logger.info(f"Starting Memory Improvement Pipeline for project_id={project_id}")

        try:
            # Step 1: Consolidate labile memories (close out reconsolidation windows)
            logger.info("Step 1: Consolidating labile memories...")
            labile_count = await self.reconsolidation.consolidate_labile_memories()
            metrics["labile_consolidated"] = labile_count
            logger.info(f"  ✓ Consolidated {labile_count} labile memories")

            # Step 2: Infer evidence types for events without explicit type
            logger.info("Step 2: Inferring evidence types...")
            evidence_count = await self.evidence.infer_evidence_batch(limit=2000)
            metrics["evidence_types_inferred"] = evidence_count
            logger.info(f"  ✓ Inferred evidence types for {evidence_count} events")

            # Step 3: Detect contradictions
            logger.info("Step 3: Detecting contradictions...")
            if project_id:
                contradictions = await self.contradictions.detect_contradictions_in_project(
                    project_id
                )
            else:
                # Detect across all projects
                async with self.db.get_connection() as conn:
                    result = await conn.execute(
                        "SELECT DISTINCT project_id FROM episodic_events ORDER BY project_id"
                    )
                    project_ids = [row[0] for row in await result.fetchall()]

                contradictions = []
                for pid in project_ids:
                    project_contradictions = (
                        await self.contradictions.detect_contradictions_in_project(pid)
                    )
                    contradictions.extend(project_contradictions)

            metrics["contradictions_detected"] = len(contradictions)
            logger.info(f"  ✓ Detected {len(contradictions)} contradictions")

            # Step 4: Resolve contradictions (auto-resolve high-confidence ones)
            logger.info("Step 4: Resolving contradictions...")
            resolved_count = 0
            for contradiction in contradictions:
                # Only auto-resolve if severity > 0.6 (moderate-to-high confidence)
                if contradiction.get("severity", 0) > 0.6:
                    success = await self.contradictions.resolve_contradiction(
                        contradiction["event1_id"],
                        contradiction["event2_id"],
                        resolution_strategy=contradiction.get("recommended_resolution", "auto"),
                    )
                    if success:
                        resolved_count += 1

            metrics["contradictions_resolved"] = resolved_count
            logger.info(f"  ✓ Resolved {resolved_count}/{len(contradictions)} contradictions")

            # Step 5: Get labile memories for next cycle
            logger.info("Step 5: Summary of labile memories...")
            labile_memories = await self.reconsolidation.get_labile_memories(project_id)
            logger.info(
                f"  ✓ {len(labile_memories)} memories in reconsolidation window "
                f"(waiting for updates)"
            )

            duration = time.time() - start_time
            metrics["pipeline_duration_seconds"] = duration

            logger.info(
                f"Memory Improvement Pipeline complete in {duration:.1f}s:\n"
                f"  • Consolidated: {metrics['labile_consolidated']} labile memories\n"
                f"  • Evidence inferred: {metrics['evidence_types_inferred']} events\n"
                f"  • Contradictions detected: {metrics['contradictions_detected']}\n"
                f"  • Contradictions resolved: {metrics['contradictions_resolved']}\n"
                f"  • Pending reconsolidation: {len(labile_memories)} memories"
            )

            return metrics

        except Exception as e:
            logger.error(f"Error in Memory Improvement Pipeline: {e}", exc_info=True)
            return metrics

    async def analyze_memory_health(self, project_id: Optional[int] = None) -> Dict[str, any]:
        """Analyze overall health of episodic memory system.

        Returns:
            Metrics about memory health
        """
        try:
            async with self.db.get_connection() as conn:
                # Get event counts by lifecycle status
                if project_id:
                    status_result = await conn.execute(
                        """
                        SELECT lifecycle_status, COUNT(*) as count
                        FROM episodic_events
                        WHERE project_id = %s
                        GROUP BY lifecycle_status
                        """,
                        (project_id,),
                    )
                else:
                    status_result = await conn.execute(
                        """
                        SELECT lifecycle_status, COUNT(*) as count
                        FROM episodic_events
                        GROUP BY lifecycle_status
                        """
                    )

                status_rows = await status_result.fetchall()
                status_dist = {row[0]: row[1] for row in status_rows}

                # Get evidence type distribution
                if project_id:
                    evidence_result = await conn.execute(
                        """
                        SELECT evidence_type, COUNT(*) as count
                        FROM episodic_events
                        WHERE project_id = %s
                        GROUP BY evidence_type
                        """,
                        (project_id,),
                    )
                else:
                    evidence_result = await conn.execute(
                        """
                        SELECT evidence_type, COUNT(*) as count
                        FROM episodic_events
                        GROUP BY evidence_type
                        """
                    )

                evidence_rows = await evidence_result.fetchall()
                evidence_dist = {row[0]: row[1] for row in evidence_rows}

                # Get quality distribution (average evidence_quality)
                if project_id:
                    quality_result = await conn.execute(
                        """
                        SELECT
                            AVG(evidence_quality) as avg_quality,
                            MIN(evidence_quality) as min_quality,
                            MAX(evidence_quality) as max_quality,
                            STDDEV(evidence_quality) as stddev_quality
                        FROM episodic_events
                        WHERE project_id = %s
                        """,
                        (project_id,),
                    )
                else:
                    quality_result = await conn.execute(
                        """
                        SELECT
                            AVG(evidence_quality) as avg_quality,
                            MIN(evidence_quality) as min_quality,
                            MAX(evidence_quality) as max_quality,
                            STDDEV(evidence_quality) as stddev_quality
                        FROM episodic_events
                        """
                    )

                quality_row = await quality_result.fetchone()

                return {
                    "lifecycle_distribution": status_dist,
                    "evidence_type_distribution": evidence_dist,
                    "quality_metrics": {
                        "avg_quality": float(quality_row[0]) if quality_row[0] else 0.5,
                        "min_quality": float(quality_row[1]) if quality_row[1] else 0.0,
                        "max_quality": float(quality_row[2]) if quality_row[2] else 1.0,
                        "stddev_quality": float(quality_row[3]) if quality_row[3] else 0.0,
                    },
                    "project_id": project_id,
                }

        except Exception as e:
            logger.error(f"Error analyzing memory health: {e}")
            return {}
