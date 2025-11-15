#!/usr/bin/env python3
"""
Execute knowledge graph consolidation task.

This script:
1. Initializes the Athena memory manager
2. Runs consolidation on all projects with recent episodic events
3. Populates knowledge graph with extracted entities and relationships
4. Reports statistics
"""

import sys
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Execute knowledge graph consolidation."""
    try:
        logger.info("=" * 60)
        logger.info("Knowledge Graph Consolidation Task")
        logger.info("=" * 60)

        # Import after path setup
        sys.path.insert(0, 'src')

        from athena.core.database import Database
        from athena.mcp.handlers_consolidation_tools import ConsolidationTools
        from athena.manager import UnifiedMemoryManager
        from athena.memory import MemoryStore
        from athena.episodic.store import EpisodicStore
        from athena.integration import IntegratedEpisodicStore
        from athena.procedural.store import ProceduralStore
        from athena.prospective.store import ProspectiveStore
        from athena.graph.store import GraphStore
        from athena.meta.store import MetaMemoryStore
        from athena.consolidation.system import ConsolidationSystem
        from athena.projects import ProjectManager
        from athena.spatial.store import SpatialStore

        logger.info("Initializing memory system...")

        # Initialize database
        db = Database()

        # Initialize all stores
        memory_store = MemoryStore(db_path="/tmp", backend='postgres')
        spatial_store = SpatialStore(db)
        episodic_store = IntegratedEpisodicStore(
            db,
            spatial_store=spatial_store,
            auto_spatial=True,
            auto_temporal=True
        )
        procedural_store = ProceduralStore(db)
        prospective_store = ProspectiveStore(db)
        graph_store = GraphStore(db)
        meta_store = MetaMemoryStore(db)
        consolidation_system = ConsolidationSystem(
            db,
            memory_store,
            episodic_store.episodic_store,
            procedural_store,
            meta_store
        )
        project_manager = ProjectManager(memory_store)

        # Initialize unified manager
        logger.info("Creating unified memory manager...")
        unified_manager = UnifiedMemoryManager(
            semantic=memory_store,
            episodic=episodic_store,
            procedural=procedural_store,
            prospective=prospective_store,
            graph=graph_store,
            meta=meta_store,
            consolidation=consolidation_system,
            project_manager=project_manager,
            enable_advanced_rag=False
        )

        # Create consolidation tools
        logger.info("Creating consolidation tools...")
        consolidation_tools = ConsolidationTools(unified_manager)

        # Get projects that need consolidation
        logger.info("Checking for projects with recent episodic events...")
        projects = db.query("SELECT id, name FROM projects ORDER BY id")

        total_entities = 0
        total_relationships = 0

        for project in projects:
            project_id = project[0] if isinstance(project, tuple) else project['id']
            project_name = project[1] if isinstance(project, tuple) else project['name']

            # Check if project has recent events
            cutoff_time = int((datetime.now() - timedelta(hours=24)).timestamp())
            recent_events = db.query(
                "SELECT COUNT(*) as count FROM episodic_events WHERE project_id = %s AND timestamp > %s",
                (project_id, cutoff_time)
            )

            event_count = recent_events[0][0] if recent_events else 0

            if event_count >= 3:
                logger.info(f"\n  Project {project_id} ({project_name}): {event_count} recent events")
                logger.info(f"  Running consolidation...")

                try:
                    result = consolidation_tools.perform_full_consolidation(
                        project_id=project_id,
                        include_code_analysis=False
                    )

                    if result.get("success"):
                        entities = result.get("total_entities_created", 0)
                        relationships = result.get("total_relationships_created", 0)
                        duration = result.get("duration_seconds", 0)

                        logger.info(f"  ✅ Consolidation complete:")
                        logger.info(f"     - Entities created: {entities}")
                        logger.info(f"     - Relationships: {relationships}")
                        logger.info(f"     - Duration: {duration:.2f}s")

                        total_entities += entities
                        total_relationships += relationships
                    else:
                        logger.warning(f"  ❌ Consolidation failed: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    logger.error(f"  ❌ Error during consolidation: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.debug(f"  Project {project_id} ({project_name}): Only {event_count} recent events (need 3+)")

        # Final report
        logger.info("\n" + "=" * 60)
        logger.info("CONSOLIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total entities created: {total_entities}")
        logger.info(f"Total relationships created: {total_relationships}")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)

        # Verify data in database
        logger.info("\nVerifying knowledge graph tables...")
        entity_count = db.query("SELECT COUNT(*) FROM entities")[0][0]
        relation_count = db.query("SELECT COUNT(*) FROM entity_relations")[0][0]

        logger.info(f"Knowledge graph tables:")
        logger.info(f"  - Entities: {entity_count}")
        logger.info(f"  - Relationships: {relation_count}")

        if entity_count > 0:
            logger.info(f"\n✅ SUCCESS: Knowledge graph populated with {entity_count} entities!")
            logger.info("   Graph visualization is ready to display real data.")
        else:
            logger.warning("\n⚠️  No entities created. Check episodic events and extraction logic.")

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
