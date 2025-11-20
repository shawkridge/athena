"""Integration hook for memory improvements into consolidation dream.

This module patches the consolidation pipeline to include:
1. Reconsolidation activation (mark retrieved memories as labile)
2. Evidence type inference (auto-detect knowledge type)
3. Contradiction detection and resolution (fix conflicting memories)

Import this module to activate memory improvements during consolidation.

Usage in dreaming.py or orchestrator.py:
    from .integration_memory_improvements import integrate_memory_improvements
    integrate_memory_improvements(consolidation_orchestrator, database)
"""

import logging
from typing import Optional

from ..core.database import Database
from .memory_improvement_pipeline import MemoryImprovementPipeline

logger = logging.getLogger(__name__)


def integrate_memory_improvements(orchestrator: object, db: Database) -> None:
    """Integrate memory improvements into consolidation orchestrator.

    This function patches the orchestrator's _consolidate_project method
    to include memory improvements as a post-consolidation step.

    Args:
        orchestrator: ConsolidationOrchestrator instance
        db: Database instance
    """
    # Store original method
    original_consolidate = orchestrator._consolidate_project

    # Create pipeline
    pipeline = MemoryImprovementPipeline(db)

    async def consolidate_with_improvements(project_id: int):
        """Enhanced consolidation that includes memory improvements."""
        # Run original consolidation
        await original_consolidate(project_id)

        # Run memory improvements (Phase 2A, 2B, 3)
        logger.info(f"Running memory improvements for project {project_id}")
        await pipeline.run_full_pipeline(project_id)

    # Patch the method
    orchestrator._consolidate_project = consolidate_with_improvements
    logger.info("Memory improvements integrated into consolidation orchestrator")


async def run_memory_improvements_standalone(
    db: Database, project_id: Optional[int] = None
) -> dict:
    """Run memory improvements standalone (for manual triggers).

    Args:
        db: Database instance
        project_id: Optional specific project, or None for all projects

    Returns:
        Metrics from the improvement pipeline
    """
    pipeline = MemoryImprovementPipeline(db)
    return await pipeline.run_full_pipeline(project_id)


def patch_semantic_search_for_reconsolidation(search_instance: object, db: Database) -> None:
    """Patch semantic search to activate reconsolidation on recall.

    This wraps the recall method to mark retrieved memories as labile.

    Args:
        search_instance: SemanticSearch instance
        db: Database instance
    """
    from .reconsolidation_activator import ReconsolidationActivator

    # Store original method
    original_recall = search_instance.recall_postgres_async

    reconsolidation = ReconsolidationActivator(db)

    async def recall_with_reconsolidation(
        query_embedding, project_id, query_text, k, memory_types, min_similarity
    ):
        """Enhanced recall that activates reconsolidation on retrieved memories."""
        # Call original recall
        results = await original_recall(
            query_embedding, project_id, query_text, k, memory_types, min_similarity
        )

        # Mark retrieved memories as labile (open for modification)
        for result in results:
            if hasattr(result, "id"):
                # This is a MemorySearchResult with ID
                await reconsolidation.mark_retrieved_memory_labile(result.id)
            elif isinstance(result, dict) and "id" in result:
                await reconsolidation.mark_retrieved_memory_labile(result["id"])

        return results

    # Patch the method
    search_instance._recall_postgres_async = recall_with_reconsolidation
    logger.info("Reconsolidation activation patched into semantic search")
