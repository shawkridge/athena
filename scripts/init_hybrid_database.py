#!/usr/bin/env python3
"""
Initialize Hybrid Database System (SQLite + Qdrant)

This script creates fresh databases for the Athena hybrid architecture:
- SQLite: Structured data (tasks, events, entities, relations)
- Qdrant: Vector embeddings (semantic memories)

Usage:
    python scripts/init_hybrid_database.py [--sqlite-path PATH] [--qdrant-url URL] [--force]
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.core.database import Database
from athena.rag.qdrant_adapter import QdrantAdapter


def init_sqlite(db_path: str) -> Database:
    """Initialize SQLite with all schemas.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Database instance
    """
    print(f"\n{'='*70}")
    print("SQLite Initialization")
    print(f"{'='*70}")
    print(f"Database: {db_path}\n")

    db = Database(db_path)

    # Import and initialize all stores (creates schemas)
    stores = []

    # Core layers
    try:
        from athena.episodic.store import EpisodicStore
        EpisodicStore(db)
        stores.append("Episodic Memory")
    except Exception as e:
        print(f"  ⚠ Episodic Memory: {e}")

    try:
        from athena.memory.store import MemoryStore
        MemoryStore(db)
        stores.append("Semantic Memory (metadata only)")
    except Exception as e:
        print(f"  ⚠ Semantic Memory: {e}")

    try:
        from athena.procedural.store import ProceduralStore
        ProceduralStore(db)
        stores.append("Procedural Memory")
    except Exception as e:
        print(f"  ⚠ Procedural Memory: {e}")

    try:
        from athena.prospective.store import ProspectiveStore
        ProspectiveStore(db)
        stores.append("Prospective Memory (Tasks/Goals)")
    except Exception as e:
        print(f"  ⚠ Prospective Memory: {e}")

    try:
        from athena.graph.store import GraphStore
        GraphStore(db)
        stores.append("Knowledge Graph")
    except Exception as e:
        print(f"  ⚠ Knowledge Graph: {e}")

    try:
        from athena.meta.store import MetaMemoryStore
        MetaMemoryStore(db)
        stores.append("Meta-Memory")
    except Exception as e:
        print(f"  ⚠ Meta-Memory: {e}")

    try:
        from athena.planning.store import PlanningStore
        PlanningStore(db)
        stores.append("Planning")
    except Exception as e:
        print(f"  ⚠ Planning: {e}")

    try:
        from athena.spatial.store import SpatialStore
        SpatialStore(db)
        stores.append("Spatial Hierarchy")
    except Exception as e:
        print(f"  ⚠ Spatial: {e}")

    # Additional systems
    try:
        from athena.conversation.store import ConversationStore
        ConversationStore(db)
        stores.append("Conversation")
    except Exception as e:
        print(f"  ⚠ Conversation: {e}")

    try:
        from athena.safety.store import SafetyStore
        SafetyStore(db)
        stores.append("Safety")
    except Exception as e:
        print(f"  ⚠ Safety: {e}")

    try:
        from athena.consolidation.system import ConsolidationSystem
        ConsolidationSystem(db)
        stores.append("Consolidation System")
    except Exception as e:
        print(f"  ⚠ Consolidation: {e}")

    print("Initialized stores:")
    for store in stores:
        print(f"  ✓ {store}")

    # Verify tables
    cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"\nTotal tables created: {len(tables)}")

    # Check for critical tables
    critical_tables = [
        "episodic_events",
        "semantic_memories",
        "procedures",
        "tasks",
        "active_goals",
        "entities",
        "entity_relations",
        "memory_quality",
    ]

    print("\nCritical tables:")
    missing = []
    for table in critical_tables:
        if table in tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} MISSING")
            missing.append(table)

    # Run migrations to create additional tables
    print(f"\nRunning migrations...")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    sys.path.insert(0, str(migrations_dir))

    try:
        from runner import MigrationRunner
        runner = MigrationRunner(db_path)
        count = runner.run_pending_migrations(dry_run=False)
        print(f"  ✓ Applied {count} migrations")

        # Refresh table list after migrations
        cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"  ✓ Total tables after migrations: {len(tables)}")
    except Exception as e:
        print(f"  ⚠ Migration error: {e}")

    # Create dashboard-compatible views/aliases
    print(f"\nCreating dashboard views...")
    try:
        # Alias prospective_tasks → tasks for dashboard
        db.conn.execute("CREATE VIEW IF NOT EXISTS tasks AS SELECT * FROM prospective_tasks")
        print(f"  ✓ Created view: tasks → prospective_tasks")

        # Create semantic_memories table for metadata (embeddings in Qdrant)
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                tags TEXT,
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(f"  ✓ Created table: semantic_memories (metadata only)")

        # Create knowledge_gaps table for dashboard
        db.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gap_type TEXT NOT NULL,
                domain TEXT,
                severity TEXT DEFAULT 'medium',
                description TEXT NOT NULL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolution_notes TEXT
            )
        """)
        print(f"  ✓ Created table: knowledge_gaps")

        db.conn.commit()
    except Exception as e:
        print(f"  ⚠ View creation error: {e}")

    if missing:
        # Recheck after migrations and views
        cursor = db.conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name")
        all_objects = [row[0] for row in cursor.fetchall()]
        still_missing = [t for t in critical_tables if t not in all_objects]

        if still_missing:
            print(f"\n⚠ Warning: {len(still_missing)} critical tables still missing: {', '.join(still_missing)}")
        else:
            print(f"\n✅ All critical tables present after migrations!")
    else:
        print(f"\n✅ SQLite initialization complete!")

    return db


def init_qdrant(url: str) -> QdrantAdapter:
    """Initialize Qdrant collections.

    Args:
        url: Qdrant server URL

    Returns:
        QdrantAdapter instance
    """
    print(f"\n{'='*70}")
    print("Qdrant Initialization")
    print(f"{'='*70}")
    print(f"URL: {url}\n")

    # Create adapter (automatically creates collection)
    adapter = QdrantAdapter(url=url)

    # Verify
    if adapter.health_check():
        print(f"✓ Connected to Qdrant")
        print(f"✓ Collection: {adapter.collection_name}")
        print(f"✓ Embedding dimension: {adapter.embedding_dim}")
        print(f"✓ Memory count: {adapter.count()}")
        print(f"\n✅ Qdrant initialization complete!")
    else:
        print(f"✗ Failed to connect to Qdrant at {url}")
        print(f"  Make sure Qdrant is running: docker-compose up -d qdrant")
        sys.exit(1)

    return adapter


def verify_hybrid_system(db: Database, adapter: QdrantAdapter):
    """Verify both databases are working correctly.

    Args:
        db: SQLite database
        adapter: Qdrant adapter
    """
    print(f"\n{'='*70}")
    print("Hybrid System Verification")
    print(f"{'='*70}\n")

    # Test SQLite
    try:
        cursor = db.conn.execute("SELECT COUNT(*) FROM episodic_events")
        event_count = cursor.fetchone()[0]
        print(f"✓ SQLite: {event_count} episodic events")
    except Exception as e:
        print(f"✗ SQLite query failed: {e}")

    # Test Qdrant
    try:
        count = adapter.count()
        print(f"✓ Qdrant: {count} semantic memories")
    except Exception as e:
        print(f"✗ Qdrant query failed: {e}")

    print(f"\n✅ Hybrid system verified and ready!")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Initialize hybrid database system")
    parser.add_argument(
        "--sqlite-path",
        default="/root/.athena/memory.db",
        help="Path to SQLite database (default: /root/.athena/memory.db for Docker)"
    )
    parser.add_argument(
        "--qdrant-url",
        default="http://qdrant:6333",
        help="Qdrant server URL (default: http://qdrant:6333 for Docker)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing databases and start fresh"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local paths (not Docker paths)"
    )

    args = parser.parse_args()

    # Adjust paths for local development
    if args.local:
        args.sqlite_path = os.path.expanduser("~/.athena/memory.db")
        args.qdrant_url = "http://localhost:6333"

    print("="*70)
    print("Athena Hybrid Database Initialization")
    print("="*70)
    print(f"SQLite:  {args.sqlite_path}")
    print(f"Qdrant:  {args.qdrant_url}")
    print(f"Force:   {args.force}")
    print()

    # Check if SQLite exists
    sqlite_path = Path(args.sqlite_path)
    if sqlite_path.exists():
        size_mb = sqlite_path.stat().st_size / (1024 * 1024)
        print(f"⚠ SQLite database exists: {sqlite_path} ({size_mb:.1f} MB)")

        if not args.force:
            response = input("Delete and recreate? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted")
                return 1

        # Backup before deleting
        backup_path = sqlite_path.parent / f"{sqlite_path.name}.backup.pre-hybrid"
        print(f"Creating backup: {backup_path}")
        import shutil
        shutil.copy2(sqlite_path, backup_path)

        sqlite_path.unlink()
        print(f"Deleted: {sqlite_path}")

    # Ensure directory exists
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize both databases
    try:
        db = init_sqlite(str(sqlite_path))
        adapter = init_qdrant(args.qdrant_url)
        verify_hybrid_system(db, adapter)
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Final report
    print(f"\n{'='*70}")
    print("Initialization Complete!")
    print(f"{'='*70}")
    print(f"SQLite:  {sqlite_path} ({sqlite_path.stat().st_size / 1024:.1f} KB)")
    print(f"Qdrant:  {args.qdrant_url}")
    print(f"\nNext steps:")
    print(f"  1. Start MCP server: docker-compose up -d athena")
    print(f"  2. Start dashboard: docker-compose up -d backend")
    print(f"  3. Access dashboard: http://localhost:3000")
    print(f"{'='*70}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
