#!/usr/bin/env python3
"""
Create fresh Athena database with complete schema initialization.

This script:
1. Creates a fresh database file
2. Initializes the UnifiedMemoryManager (which initializes all layers)
3. Runs migrations
4. Verifies tables exist

Usage:
    python scripts/init_fresh_database.py [--db-path PATH] [--dry-run]
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Initialize fresh Athena database")
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
    print("Athena Database Initialization")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Check if database exists
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"⚠ Database already exists: {db_path} ({size_mb:.1f} MB)")

        if not args.force and not args.dry_run:
            response = input("Delete and recreate? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted")
                return 1

        if not args.dry_run:
            backup_path = db_path.parent / f"{db_path.name}.backup.pre-init"
            print(f"Creating backup: {backup_path}")
            import shutil
            shutil.copy2(db_path, backup_path)
            db_path.unlink()
            print(f"Deleted: {db_path}")

    if args.dry_run:
        print("\n🔍 DRY RUN - No changes will be made")
        print("\nWould perform:")
        print("  1. Create fresh database")
        print("  2. Initialize UnifiedMemoryManager (all layers)")
        print("  3. Run all migrations")
        print("  4. Verify tables exist")
        return 0

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nCreating fresh database...")

    # Import and initialize manager (this creates all tables)
    from athena.manager import UnifiedMemoryManager
    from athena.core.database import Database

    print("Initializing UnifiedMemoryManager...")
    db = Database(str(db_path))
    manager = UnifiedMemoryManager(db=db)
    print("  ✓ All layer schemas initialized")

    # Run migrations
    print("\nRunning migrations...")
    migrations_dir = Path(__file__).parent.parent / "migrations"
    sys.path.insert(0, str(migrations_dir))

    try:
        from runner import MigrationRunner
        runner = MigrationRunner(str(db_path))
        count = runner.run_pending_migrations(dry_run=False)
        print(f"  ✓ Applied {count} migrations")
    except Exception as e:
        print(f"  ⚠ Migration error (may be normal if tables already exist): {e}")

    # Verify
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
        "memory_quality",
    ]

    print("\nKey tables:")
    missing = []
    for table in key_tables:
        if table in tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} MISSING")
            missing.append(table)

    # Report
    print("\n" + "=" * 70)
    if missing:
        print(f"⚠ Database initialized with {len(missing)} missing tables")
        print("Missing tables:", ", ".join(missing))
    else:
        print("✓ Database initialization complete!")

    print(f"  Database: {db_path}")
    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        print(f"  Size: {size_kb:.1f} KB")
    print(f"  Tables: {len(tables)}")
    print("=" * 70)

    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
