"""
Integration of dream generation into the consolidation pipeline.

This module adds dream generation as a new step in consolidation,
occurring after pattern extraction and validation.
"""

import logging
import time
from typing import List, Optional
from datetime import datetime

from ..core.database import Database
from ..procedural.models import Procedure
from ..procedural.store import ProceduralStore
from .dreaming import DreamGenerator, DreamGenerationConfig
from .dream_store import DreamStore, DreamGenerationRun
from .cross_project_synthesizer import ProcedureReference

logger = logging.getLogger(__name__)


class DreamIntegration:
    """
    Integrates dream generation into consolidation pipeline.

    Handles:
    - Dream generation from validated procedures
    - Cross-project procedure discovery
    - Storing dreams with generation metadata
    - Recording generation statistics
    """

    def __init__(self, db: Database):
        """Initialize dream integration.

        Args:
            db: Database instance
        """
        self.db = db
        self.procedural_store = ProceduralStore(db)
        self.dream_store = DreamStore(db)
        self.dream_generator = None  # Initialized on first use

    async def generate_dreams_from_consolidation(
        self,
        strategy: str = "balanced",
        project_id: Optional[int] = None,
        consolidation_run_id: Optional[int] = None
    ) -> dict:
        """
        Generate dreams as part of consolidation.

        This is called after pattern extraction and validation.

        Args:
            strategy: Dream generation strategy ("light", "balanced", "deep")
            project_id: Optional project ID for filtering procedures
            consolidation_run_id: Optional consolidation run ID for linking

        Returns:
            Dictionary with generation results:
            {
                "total_dreams": int,
                "by_type": {str: int},
                "generation_time": float,
                "procedures_processed": int,
                "run_id": int
            }
        """
        logger.info(f"Starting dream generation (strategy={strategy})")

        start_time = time.time()
        total_dreams = 0
        dreams_by_type = {
            "constraint_relaxation": 0,
            "cross_project_synthesis": 0,
            "parameter_exploration": 0,
            "conditional_variant": 0
        }
        procedures_processed = 0

        try:
            # Initialize dream generator
            if not self.dream_generator:
                self.dream_generator = DreamGenerator()

            # Get dream config
            config = DreamGenerationConfig.from_strategy(strategy)

            # Get procedures to generate dreams for
            logger.info("Retrieving procedures for dream generation...")
            procedures = await self.procedural_store.list_all()

            if project_id:
                # Filter to project (if project-specific consolidation)
                # Note: ProceduralStore may not have project filtering
                # This would need to be added if using project-specific procedures
                logger.debug(f"Filtering procedures for project {project_id}")

            logger.info(f"Found {len(procedures)} procedures for dream generation")

            # Process each procedure
            for procedure in procedures:
                if not procedure.code:
                    logger.debug(f"Skipping {procedure.name} (no code)")
                    continue

                try:
                    logger.info(f"Generating dreams for {procedure.name}...")

                    # Find related procedures for cross-project synthesis
                    related_procedures = []
                    if config.cross_project_synthesis_enabled:
                        related_procedures = await self._find_related_procedures(procedure)

                    # Generate dreams
                    dreams = await self.dream_generator.generate_dreams(
                        procedure_id=procedure.id,
                        procedure_name=procedure.name,
                        procedure_code=procedure.code,
                        related_procedures=related_procedures,
                        config=config
                    )

                    # Store dreams
                    for dream in dreams:
                        dream_id = await self.dream_store.store_dream(dream)
                        total_dreams += 1

                        # Track by type
                        dream_type = dream.dream_type
                        if dream_type in dreams_by_type:
                            dreams_by_type[dream_type] += 1

                        logger.debug(f"  Stored dream {dream_id}: {dream.name}")

                    logger.info(f"Generated {len(dreams)} dreams for {procedure.name}")
                    procedures_processed += 1

                except Exception as e:
                    logger.error(
                        f"Error generating dreams for {procedure.name}: {e}",
                        exc_info=True
                    )
                    continue

            # Record generation run
            run_id = await self._record_generation_run(
                strategy=strategy,
                total_dreams=total_dreams,
                dreams_by_type=dreams_by_type,
                duration=time.time() - start_time,
                procedures_processed=procedures_processed
            )

            # Log summary
            elapsed = time.time() - start_time
            logger.info("=" * 70)
            logger.info(f"DREAM GENERATION COMPLETE")
            logger.info(f"  Total dreams: {total_dreams}")
            logger.info(f"  By type: {dreams_by_type}")
            logger.info(f"  Procedures processed: {procedures_processed}")
            logger.info(f"  Time elapsed: {elapsed:.1f}s")
            logger.info(f"  Generation run ID: {run_id}")
            logger.info("=" * 70)

            return {
                "total_dreams": total_dreams,
                "by_type": dreams_by_type,
                "generation_time": elapsed,
                "procedures_processed": procedures_processed,
                "run_id": run_id,
                "consolidation_run_id": consolidation_run_id
            }

        except Exception as e:
            logger.error(f"Fatal error in dream generation: {e}", exc_info=True)
            return {
                "total_dreams": 0,
                "by_type": dreams_by_type,
                "generation_time": time.time() - start_time,
                "procedures_processed": procedures_processed,
                "run_id": None,
                "error": str(e)
            }

    async def _find_related_procedures(
        self, procedure: Procedure
    ) -> List[ProcedureReference]:
        """
        Find procedures related to the given procedure.

        For cross-project synthesis, find procedures that could be
        meaningfully combined with this one.

        Args:
            procedure: Base procedure

        Returns:
            List of related ProcedureReference objects
        """
        related = []

        try:
            all_procedures = await self.procedural_store.list_all()

            for other in all_procedures:
                if other.id == procedure.id:
                    continue

                # Simple heuristic: same category or overlapping contexts
                score = 0

                if other.category == procedure.category:
                    score += 1

                if other.applicable_contexts and procedure.applicable_contexts:
                    overlap = set(other.applicable_contexts) & set(procedure.applicable_contexts)
                    if overlap:
                        score += len(overlap) * 0.5

                if score > 0:
                    related.append(
                        ProcedureReference(
                            id=other.id,
                            name=other.name,
                            category=other.category,
                            description=other.description or "",
                            code_snippet=other.code[:500] if other.code else "",
                            applicable_contexts=other.applicable_contexts or [],
                            semantic_tags=other.applicable_contexts or []
                        )
                    )

                if len(related) >= 5:
                    break

        except Exception as e:
            logger.warning(f"Error finding related procedures: {e}")

        return related

    async def _record_generation_run(
        self,
        strategy: str,
        total_dreams: int,
        dreams_by_type: dict,
        duration: float,
        procedures_processed: int
    ) -> int:
        """Record a dream generation run."""
        try:
            run = DreamGenerationRun(
                strategy=strategy,
                timestamp=datetime.now(),
                total_dreams_generated=total_dreams,
                constraint_relaxation_count=dreams_by_type.get("constraint_relaxation", 0),
                cross_project_synthesis_count=dreams_by_type.get("cross_project_synthesis", 0),
                parameter_exploration_count=dreams_by_type.get("parameter_exploration", 0),
                conditional_variant_count=dreams_by_type.get("conditional_variant", 0),
                duration_seconds=duration,
                model_usage={
                    "deepseek_v3_1": 25,  # Estimated
                    "qwen_2_5_coder": 25,
                    "local_qwen3": 0,
                }
            )

            run_id = await self.dream_store.record_generation_run(run)
            logger.info(f"Recorded generation run {run_id}")
            return run_id

        except Exception as e:
            logger.error(f"Error recording generation run: {e}", exc_info=True)
            return None

    async def get_dream_statistics(self) -> dict:
        """Get current dream system statistics."""
        try:
            return await self.dream_store.get_statistics()
        except Exception as e:
            logger.error(f"Error getting dream statistics: {e}")
            return {}

    async def close(self):
        """Clean up resources."""
        if self.dream_generator:
            await self.dream_generator.close()


# Convenience function for integration into consolidation
async def integrate_dreams_into_consolidation(
    db: Database,
    strategy: str = "balanced",
    project_id: Optional[int] = None,
    consolidation_run_id: Optional[int] = None
) -> dict:
    """
    Generate dreams and integrate results into consolidation.

    Can be called from ConsolidationSystem.run_consolidation() after
    pattern extraction.

    Usage:
        result = await integrate_dreams_into_consolidation(db, "balanced")
        logger.info(f"Generated {result['total_dreams']} dreams")

    Args:
        db: Database instance
        strategy: Dream generation strategy
        project_id: Optional project filter
        consolidation_run_id: Optional consolidation run ID

    Returns:
        Generation result dictionary
    """
    integration = DreamIntegration(db)

    try:
        return await integration.generate_dreams_from_consolidation(
            strategy=strategy,
            project_id=project_id,
            consolidation_run_id=consolidation_run_id
        )

    finally:
        await integration.close()
