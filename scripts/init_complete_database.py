#!/usr/bin/env python3
"""
Complete Database Initialization Script

This script creates a fresh Athena database with ALL schemas initialized:
1. Core database tables
2. All memory layer stores
3. All migration tables

Usage:
    python scripts/init_complete_database.py [--db-path <path>] [--dry-run]
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.core.database import Database

# Import all store classes that have schemas
from athena.episodic.store import EpisodicStore
from athena.memory.store import SemanticMemoryStore
from athena.procedural.store import ProceduralStore
from athena.prospective.store import ProspectiveStore
from athena.graph.store import GraphStore
from athena.meta.store import MetaStore
from athena.planning.store import PlanningStore
from athena.spatial.store import SpatialStore
from athena.temporal.git_store import GitStore
from athena.conversation.store import ConversationStore
from athena.safety.store import SafetyStore
from athena.research.store import ResearchStore
from athena.code_artifact.store import CodeArtifactStore
from athena.ide_context.store import IDEContextStore
from athena.symbols.symbol_store import SymbolStore
from athena.procedural.pattern_store import PatternStore

# AI Coordination stores
from athena.ai_coordination.action_cycle_store import ActionCycleStore
from athena.ai_coordination.code_context_store import CodeContextStore
from athena.ai_coordination.execution_trace_store import ExecutionTraceStore
from athena.ai_coordination.learning_integration_store import LearningIntegrationStore
from athena.ai_coordination.project_context_store import ProjectContextStore
from athena.ai_coordination.session_continuity_store import SessionContinuityStore
from athena.ai_coordination.thinking_trace_store import ThinkingTraceStore

# Phase 9 stores
from athena.phase9.context_adapter.store import ContextAdapterStore
from athena.phase9.cost_optimization.store import CostOptimizationStore
from athena.phase9.uncertainty.store import UncertaintyStore

# Consolidation system
from athena.consolidation.system import ConsolidationSystem

# Working memory
from athena.working_memory.capacity_enforcer import CapacityEnforcer

# Associations
from athena.associations.zettelkasten import ZettelkastenStore

# Reflection scheduler
from athena.reflection.scheduler import ReflectionScheduler


def init_all_schemas(db: Database):
    """Initialize all schemas by instantiating store classes.

    Each store's __init__ calls _init_schema() which creates tables.
    """
    print("Initializing all schemas...")

    stores = [
        ("Episodic Memory", lambda: EpisodicStore(db)),
        ("Semantic Memory", lambda: SemanticMemoryStore(db)),
        ("Procedural Memory", lambda: ProceduralStore(db)),
        ("Prospective Memory", lambda: ProspectiveStore(db)),
        ("Knowledge Graph", lambda: GraphStore(db)),
        ("Meta Memory", lambda: MetaStore(db)),
        ("Planning", lambda: PlanningStore(db)),
        ("Spatial Hierarchy", lambda: SpatialStore(db)),
        ("Git Temporal", lambda: GitStore(db)),
        ("Conversation", lambda: ConversationStore(db)),
        ("Safety", lambda: SafetyStore(db)),
        ("Research", lambda: ResearchStore(db)),
        ("Code Artifacts", lambda: CodeArtifactStore(db)),
        ("IDE Context", lambda: IDEContextStore(db)),
        ("Symbol Analysis", lambda: SymbolStore(db)),
        ("Pattern Store", lambda: PatternStore(db)),
        ("Action Cycles", lambda: ActionCycleStore(db)),
        ("Code Context", lambda: CodeContextStore(db)),
        ("Execution Traces", lambda: ExecutionTraceStore(db)),
        ("Learning Integration", lambda: LearningIntegrationStore(db)),
        ("Project Context", lambda: ProjectContextStore(db)),
        ("Session Continuity", lambda: SessionContinuityStore(db)),
        ("Thinking Traces", lambda: ThinkingTraceStore(db)),
        ("Context Adapter", lambda: ContextAdapterStore(db)),
        ("Cost Optimization", lambda: CostOptimizationStore(db)),
        ("Uncertainty", lambda: UncertaintyStore(db)),
        ("Consolidation System", lambda: ConsolidationSystem(db)),
        ("Working Memory", lambda: CapacityEnforcer(db, project_id=1)),
        ("Zettelkasten", lambda: ZettelkastenStore(db)),
        ("Reflection Scheduler", lambda: ReflectionScheduler(db)),
    ]

    for name, factory in stores:
        try:
            factory()
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ⚠ {name}: {e}")


def run_migrations(db_path: str):
    """Run all SQL migrations."""
    print("\nRunning migrations...")

    migrations_dir = Path(__file__).parent.parent / "migrations"

    # Use the migration runner
    sys.path.insert(0, str(migrations_dir))
    from runner import MigrationRunner

    runner = MigrationRunner(db_path)
    count = runner.run_pending_migrations(dry_run=False)

    print(f"  ✓ Applied {count} migrations")


def verify_database(db: Database):
    """Verify database has all expected tables."""
    print("\nVerifying database...")

    cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"  ✓ Total tables: {len(tables)}")

    # Check for key tables
    key_tables = [
        "episodic_events",
        "semantic_memories",
        "procedures",
        "tasks",
        "active_goals",
        "entities",
        "entity_relations",
        "planning_state",
        "consolidation_runs",
        "working_memory",
        "memory_quality",  # Dashboard needs this
        "knowledge_gaps",  # Dashboard needs this
    ]

    missing = []
    for table in key_tables:
        if table in tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} MISSING")
            missing.append(table)

    if missing:
        print(f"\n⚠ Warning: {len(missing)} key tables are missing")
        return False

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Initialize complete Athena database")
    parser.add_argument(
        "--db-path",
        default=os.path.expanduser("~/.athena/memory.db"),
        help="Path to database file (default: ~/.athena/memory.db)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing database and start fresh"
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)

    print("=" * 70)
    print("Athena Complete Database Initialization")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Check if database exists
    if db_path.exists():
        if args.force:
            if not args.dry_run:
                print(f"⚠ Deleting existing database: {db_path}")
                db_path.unlink()
        else:
            print(f"⚠ Database already exists: {db_path}")
            response = input("Delete and recreate? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted")
                return 1
            if not args.dry_run:
                db_path.unlink()

    if args.dry_run:
        print("\n🔍 DRY RUN - No changes will be made")
        print("\nWould perform:")
        print("  1. Create fresh database")
        print("  2. Initialize all store schemas")
        print("  3. Run all migrations")
        print("  4. Verify tables exist")
        return 0

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create database and initialize
    print(f"\nCreating fresh database: {db_path}")
    db = Database(str(db_path))

    # Initialize all schemas
    init_all_schemas(db)

    # Run migrations
    run_migrations(str(db_path))

    # Verify
    success = verify_database(db)

    # Report
    print("\n" + "=" * 70)
    if success:
        print("✓ Database initialization complete!")
        print(f"  Database: {db_path}")
        print(f"  Size: {db_path.stat().st_size / 1024:.1f} KB")
    else:
        print("⚠ Database initialization completed with warnings")
        print("  Some tables may be missing - check logs above")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
