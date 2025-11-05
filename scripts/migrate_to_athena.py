#!/usr/bin/env python3
"""Migrate memories from memory-mcp to new athena project.

Usage:
    python scripts/migrate_to_athena.py --target ~/.work/athena/memory.db
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from athena.core.database import Database
from athena.projects.memory_migration import MemoryMigrationManager


def main():
    parser = argparse.ArgumentParser(
        description="Migrate memories from memory-mcp to athena project"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=str(Path.home() / ".athena" / "memory.db"),
        help="Source database path (default: ~/.athena/memory.db)"
    )
    parser.add_argument(
        "--target",
        type=str,
        required=True,
        help="Target database path (e.g., ~/.work/athena/memory.db)"
    )
    parser.add_argument(
        "--source-project-id",
        type=int,
        default=1,
        help="Source project ID to migrate from (default: 1)"
    )
    parser.add_argument(
        "--target-project-id",
        type=int,
        default=1,
        help="Target project ID to migrate to (default: 1)"
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="+",
        choices=["episodic", "semantic", "procedural", "prospective", "graph", "associations"],
        default=[],
        help="Memory layers to exclude from migration"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Validate paths
    source_path = Path(args.source).expanduser()
    target_path = Path(args.target).expanduser()

    if not source_path.exists():
        print(f"❌ Source database not found: {source_path}")
        sys.exit(1)

    if not target_path.parent.exists():
        print(f"❌ Target directory does not exist: {target_path.parent}")
        sys.exit(1)

    print(f"🔄 Memory Migration Tool")
    print(f"Source: {source_path}")
    print(f"Target: {target_path}")
    print(f"Source Project ID: {args.source_project_id}")
    print(f"Target Project ID: {args.target_project_id}")
    print()

    # Connect to databases
    try:
        source_db = Database(str(source_path))
        target_db = Database(str(target_path))
    except Exception as e:
        print(f"❌ Failed to connect to databases: {e}")
        sys.exit(1)

    # Create migration manager
    migration = MemoryMigrationManager(source_db, target_db)

    # Get statistics
    print("📊 Migration Statistics")
    stats = migration.get_migration_stats(args.source_project_id)
    print(f"  Semantic memories: {stats['semantic']}")
    print(f"  Episodic events: {stats['episodic']}")
    print(f"  Procedures: {stats['procedural']}")
    print(f"  Tasks: {stats['prospective']}")
    print(f"  Entities: {stats['entities']}")
    print(f"  Relations: {stats['relations']}")
    print()

    if args.dry_run:
        print("✅ Dry-run complete. No changes made.")
        sys.exit(0)

    # Build migration parameters
    migration_params = {
        "source_project_id": args.source_project_id,
        "target_project_id": args.target_project_id,
    }

    # Exclude specified layers
    exclude_map = {
        "episodic": "include_episodic",
        "semantic": "include_semantic",
        "procedural": "include_procedural",
        "prospective": "include_prospective",
        "graph": "include_graph",
        "associations": "include_associations",
    }

    for layer in args.exclude:
        if layer in exclude_map:
            migration_params[exclude_map[layer]] = False

    print("⏳ Starting migration...")
    print()

    # Perform migration
    try:
        start_time = datetime.now()
        results = migration.migrate_project_memories(**migration_params)
        elapsed = (datetime.now() - start_time).total_seconds()

        print("✅ Migration Complete!")
        print()
        print("📦 Migrated:")
        print(f"  ✓ Semantic memories: {results['semantic']}")
        print(f"  ✓ Episodic events: {results['episodic']}")
        print(f"  ✓ Procedures: {results['procedural']}")
        print(f"  ✓ Tasks: {results['prospective']}")
        print(f"  ✓ Entities: {results['entities']}")
        print(f"  ✓ Relations: {results['relations']}")
        print(f"  ✓ Associations: {results['associations']}")
        print()
        print(f"⏱️  Time elapsed: {elapsed:.2f}s")
        print()
        print(f"🎉 All memories migrated to {target_path}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
