"""
One-time migration: Consolidate old and new consolidation systems.

This migration handles the transition from the old consolidation tracking system
(consolidation_status, consolidated_at) to the new lifecycle system
(lifecycle_status, consolidation_score, last_activation, activation_count).

Migration Strategy:
1. Backfill new fields based on old field values
2. Update consolidation pipeline to use new fields
3. Remove old fields from schema and model
4. Verify all code uses new system

Timeline: One-time execution at next database upgrade
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


async def migrate_consolidation_system(db) -> dict:
    """
    Execute one-time migration from old to new consolidation system.

    Args:
        db: Database instance (PostgreSQL)

    Returns:
        Migration report with counts
    """
    report = {
        "total_events": 0,
        "migrated_events": 0,
        "errors": [],
    }

    try:
        async with db.get_connection() as conn:
            # Step 1: Get counts
            cursor = conn.cursor()
            await cursor.execute("SELECT COUNT(*) as count FROM episodic_events")
            result = await cursor.fetchone()
            report["total_events"] = result["count"]

            # Step 2: Backfill new fields from old fields
            # For events with consolidation_status='consolidated', set:
            #   - lifecycle_status='consolidated'
            #   - consolidation_score=1.0 (high confidence)
            #   - last_activation=consolidated_at (if available, else now)
            #   - activation_count=1 (assume accessed once at consolidation)
            await cursor.execute(
                """
                UPDATE episodic_events
                SET
                    lifecycle_status = CASE
                        WHEN consolidation_status = 'consolidated' THEN 'consolidated'
                        ELSE 'active'
                    END,
                    consolidation_score = CASE
                        WHEN consolidation_status = 'consolidated' THEN 1.0
                        ELSE 0.0
                    END,
                    last_activation = CASE
                        WHEN consolidated_at IS NOT NULL THEN to_timestamp(consolidated_at)
                        ELSE NOW()
                    END,
                    activation_count = CASE
                        WHEN consolidation_status = 'consolidated' THEN 1
                        ELSE 0
                    END
                WHERE lifecycle_status = 'active' AND consolidation_status IS NOT NULL
            """
            )

            # Get count of migrated events
            report["migrated_events"] = await cursor.rowcount

            # Step 3: Verify migration
            await cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN lifecycle_status = 'consolidated' THEN 1 ELSE 0 END) as consolidated,
                    SUM(CASE WHEN lifecycle_status = 'active' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN lifecycle_status = 'archived' THEN 1 ELSE 0 END) as archived
                FROM episodic_events
            """
            )
            verification = await cursor.fetchone()
            report["verification"] = {
                "total": verification["total"],
                "consolidated": verification["consolidated"],
                "active": verification["active"],
                "archived": verification["archived"],
            }

            await conn.commit()
            logger.info(f"Consolidation system migration completed: {report}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        report["errors"].append(str(e))

    return report


async def rollback_migration(db) -> dict:
    """
    Rollback migration (restore old fields).

    Only use if migration causes issues.

    Args:
        db: Database instance

    Returns:
        Rollback report
    """
    report = {
        "rolled_back": False,
        "error": None,
    }

    try:
        async with db.get_connection() as conn:
            cursor = conn.cursor()

            # Restore old field values from new fields
            await cursor.execute(
                """
                UPDATE episodic_events
                SET
                    consolidation_status = CASE
                        WHEN lifecycle_status = 'consolidated' THEN 'consolidated'
                        ELSE 'unconsolidated'
                    END,
                    consolidated_at = CASE
                        WHEN lifecycle_status = 'consolidated' THEN EXTRACT(EPOCH FROM last_activation)::INTEGER
                        ELSE NULL
                    END
                WHERE consolidation_status IS NULL
            """
            )

            await conn.commit()
            report["rolled_back"] = True
            logger.info("Consolidation system migration rolled back successfully")

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        report["error"] = str(e)

    return report
