#!/usr/bin/env python3
"""
Standalone consolidation runner with dream generation.

Run nightly via cron without Claude Code context.
Generates dreams autonomously and stores them for Claude evaluation.

Usage:
    python3 run_consolidation_with_dreams.py --strategy balanced
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path
import argparse
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.core.database import Database
from athena.consolidation.system import ConsolidationSystem
from athena.consolidation.dreaming import DreamGenerator, DreamGenerationConfig
from athena.consolidation.dream_store import DreamStore, DreamGenerationRun
from athena.procedural.store import ProceduralStore
from athena.consolidation.cross_project_synthesizer import ProcedureReference
from athena.consolidation.memory_improvement_pipeline import MemoryImprovementPipeline


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/athena-dreams.log"),
    ]
)

logger = logging.getLogger(__name__)


async def run_consolidation_with_dreams(strategy: str = "balanced", projects: list = None):
    """
    Run consolidation with dream generation.

    Args:
        strategy: Dream generation strategy ("light", "balanced", "deep")
        projects: Optional list of project IDs to consolidate
    """
    logger.info("=" * 80)
    logger.info(f"Starting Athena consolidation with dreams (strategy={strategy})")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info("=" * 80)

    start_time = time.time()
    dream_count = 0
    consolidation_successful = True

    try:
        # Initialize database and stores
        db = Database()
        consolidation_system = ConsolidationSystem(db)
        procedural_store = ProceduralStore(db)
        dream_store = DreamStore(db)
        dream_generator = DreamGenerator()

        # Step 1: Run standard consolidation
        logger.info("Step 1: Running standard consolidation...")

        try:
            result = await consolidation_system.consolidate(
                strategy="balanced",
                enable_dreams=False  # Consolidation without dreams first
            )
            logger.info(f"Consolidation complete: {result}")
        except Exception as e:
            logger.error(f"Consolidation failed: {e}", exc_info=True)
            consolidation_successful = False

        # Step 1.5: Run memory improvements (evidence inference, contradiction detection, reconsolidation)
        logger.info("Step 1.5: Running memory improvements...")

        try:
            pipeline = MemoryImprovementPipeline(db)
            improvement_metrics = await pipeline.run_full_pipeline()
            logger.info(
                f"Memory improvements complete: "
                f"labile_consolidated={improvement_metrics.get('labile_consolidated', 0)}, "
                f"evidence_inferred={improvement_metrics.get('evidence_types_inferred', 0)}, "
                f"contradictions_resolved={improvement_metrics.get('contradictions_resolved', 0)}"
            )
        except Exception as e:
            logger.warning(f"Memory improvements had issues (non-critical): {e}", exc_info=True)
            # Don't fail consolidation if memory improvements have issues

        # Step 2: Generate dreams from validated patterns
        logger.info("Step 2: Generating dreams from procedures...")

        try:
            # Get all procedures
            procedures = await procedural_store.list_all()
            logger.info(f"Found {len(procedures)} procedures to generate dreams for")

            config = DreamGenerationConfig.from_strategy(strategy)

            for procedure in procedures:
                if not procedure.code:
                    logger.debug(f"Skipping {procedure.name} (no code)")
                    continue

                logger.info(f"Generating dreams for {procedure.name}...")

                # Find related procedures for cross-project synthesis
                related_procedures = []
                if config.cross_project_synthesis_enabled:
                    related_procedures = await _find_related_procedures(
                        procedural_store, procedure
                    )

                try:
                    dreams = await dream_generator.generate_dreams(
                        procedure_id=procedure.id,
                        procedure_name=procedure.name,
                        procedure_code=procedure.code,
                        related_procedures=related_procedures,
                        config=config
                    )

                    # Store dreams in database
                    for dream in dreams:
                        dream_id = await dream_store.store_dream(dream)
                        dream_count += 1
                        logger.debug(f"  Stored dream {dream_id}: {dream.name}")

                    logger.info(f"Generated {len(dreams)} dreams for {procedure.name}")

                except Exception as e:
                    logger.error(f"Error generating dreams for {procedure.name}: {e}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"Dream generation failed: {e}", exc_info=True)

        # Step 3: Record generation run
        logger.info("Step 3: Recording generation run...")

        try:
            stats = await dream_store.get_statistics()

            run = DreamGenerationRun(
                strategy=strategy,
                timestamp=datetime.now(),
                total_dreams_generated=dream_count,
                constraint_relaxation_count=len(
                    await dream_store.get_by_type("constraint_relaxation", limit=1000)
                ),
                cross_project_synthesis_count=len(
                    await dream_store.get_by_type("cross_project_synthesis", limit=1000)
                ),
                parameter_exploration_count=len(
                    await dream_store.get_by_type("parameter_exploration", limit=1000)
                ),
                conditional_variant_count=len(
                    await dream_store.get_by_type("conditional_variant", limit=1000)
                ),
                duration_seconds=time.time() - start_time,
                model_usage={
                    "deepseek_v3_1": 25,  # Estimated
                    "qwen_2_5_coder": 25,
                    "local_qwen3": 0,
                }
            )

            run_id = await dream_store.record_generation_run(run)
            logger.info(f"Recorded generation run {run_id}")

        except Exception as e:
            logger.error(f"Error recording generation run: {e}", exc_info=True)

        # Summary
        elapsed = time.time() - start_time
        logger.info("=" * 80)
        logger.info(f"CONSOLIDATION COMPLETE")
        logger.info(f"  Status: {'SUCCESS' if consolidation_successful else 'PARTIAL'}")
        logger.info(f"  Dreams generated: {dream_count}")
        logger.info(f"  Time elapsed: {elapsed:.1f}s")
        logger.info(f"  Pending evaluation: {len(await dream_store.get_pending_evaluation())}")
        logger.info("=" * 80)

        return dream_count, consolidation_successful

    except Exception as e:
        logger.error(f"Fatal error in consolidation: {e}", exc_info=True)
        return 0, False

    finally:
        await dream_generator.close()


async def _find_related_procedures(
    store: ProceduralStore, procedure
) -> list:
    """Find related procedures for synthesis."""
    related = []

    try:
        all_procedures = await store.list_all()

        # Simple heuristic: same category or shared tags
        for other in all_procedures:
            if other.id == procedure.id:
                continue

            if other.category == procedure.category:
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run Athena consolidation with dream generation"
    )
    parser.add_argument(
        "--strategy",
        choices=["light", "balanced", "deep"],
        default="balanced",
        help="Dream generation strategy"
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        help="Optional specific project IDs to consolidate"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )

    args = parser.parse_args()

    # Run consolidation
    try:
        dream_count, success = asyncio.run(
            run_consolidation_with_dreams(
                strategy=args.strategy,
                projects=args.projects
            )
        )

        # Exit with appropriate code
        if success:
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Consolidation interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
