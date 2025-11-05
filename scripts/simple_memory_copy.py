#!/usr/bin/env python3
"""Simple memory copy from memory-mcp database to athena project.

This script copies all memories from the source database directly to the target.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime


def copy_memories(source_db: str, target_db: str, dry_run: bool = False):
    """Copy all memories from source to target database."""

    # Connect to databases
    try:
        source_conn = sqlite3.connect(source_db)
        source_conn.row_factory = sqlite3.Row

        target_conn = sqlite3.connect(target_db)
        target_conn.row_factory = sqlite3.Row
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False

    counts = {}

    try:
        # Copy memories table
        print("📋 Copying memories...")
        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        memories = source_cursor.execute("SELECT * FROM memories").fetchall()
        count = 0

        for mem in memories:
            if dry_run:
                count += 1
            else:
                # Create columns list dynamically
                cols = [desc[0] for desc in source_cursor.description]
                values = tuple(mem[col] for col in cols)
                placeholders = ','.join(['?' for _ in cols])
                col_names = ','.join(cols)

                try:
                    target_cursor.execute(
                        f"INSERT INTO memories ({col_names}) VALUES ({placeholders})",
                        values
                    )
                    count += 1
                except sqlite3.IntegrityError:
                    # Record already exists, skip
                    pass

        target_conn.commit()
        counts['memories'] = count
        print(f"  ✓ Copied {count} memories")

        # Copy episodic events
        print("📋 Copying episodic events...")
        events = source_cursor.execute("SELECT * FROM episodic_events LIMIT 1000").fetchall()
        count = 0

        for event in events:
            if not dry_run:
                cols = [desc[0] for desc in source_cursor.description]
                values = tuple(event[col] for col in cols)
                placeholders = ','.join(['?' for _ in cols])
                col_names = ','.join(cols)

                try:
                    target_cursor.execute(
                        f"INSERT INTO episodic_events ({col_names}) VALUES ({placeholders})",
                        values
                    )
                    count += 1
                except sqlite3.IntegrityError:
                    pass
            else:
                count += 1

        target_conn.commit()
        counts['episodic_events'] = count
        print(f"  ✓ Copied {count} episodic events")

        # Copy procedures
        print("📋 Copying procedures...")
        procedures = source_cursor.execute("SELECT * FROM procedures").fetchall()
        count = 0

        for proc in procedures:
            if not dry_run:
                cols = [desc[0] for desc in source_cursor.description]
                values = tuple(proc[col] for col in cols)
                placeholders = ','.join(['?' for _ in cols])
                col_names = ','.join(cols)

                try:
                    target_cursor.execute(
                        f"INSERT INTO procedures ({col_names}) VALUES ({placeholders})",
                        values
                    )
                    count += 1
                except sqlite3.IntegrityError:
                    pass
            else:
                count += 1

        target_conn.commit()
        counts['procedures'] = count
        print(f"  ✓ Copied {count} procedures")

        # Copy prospective tasks
        print("📋 Copying prospective tasks...")
        tasks = source_cursor.execute("SELECT * FROM prospective_tasks").fetchall()
        count = 0

        for task in tasks:
            if not dry_run:
                cols = [desc[0] for desc in source_cursor.description]
                values = tuple(task[col] for col in cols)
                placeholders = ','.join(['?' for _ in cols])
                col_names = ','.join(cols)

                try:
                    target_cursor.execute(
                        f"INSERT INTO prospective_tasks ({col_names}) VALUES ({placeholders})",
                        values
                    )
                    count += 1
                except sqlite3.IntegrityError:
                    pass
            else:
                count += 1

        target_conn.commit()
        counts['prospective_tasks'] = count
        print(f"  ✓ Copied {count} prospective tasks")

        return counts

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        source_conn.close()
        target_conn.close()


def main():
    source = str(Path.home() / ".athena" / "memory.db")
    target = str(Path.home() / ".work" / "athena" / "memory.db")

    if len(sys.argv) > 1:
        target = sys.argv[1]

    # Check paths
    source_path = Path(source)
    target_path = Path(target)

    if not source_path.exists():
        print(f"❌ Source database not found: {source_path}")
        sys.exit(1)

    if not target_path.parent.exists():
        print(f"❌ Target directory does not exist: {target_path.parent}")
        sys.exit(1)

    print("🔄 Memory Copy Tool")
    print(f"Source: {source_path}")
    print(f"Target: {target_path}")
    print()

    # Dry run first
    print("📊 Dry-run to see what would be copied...")
    counts = copy_memories(str(source_path), str(target_path), dry_run=True)

    if counts:
        print()
        print("Would copy:")
        for key, value in counts.items():
            print(f"  • {key}: {value}")
        print()

        response = input("Proceed with copy? (yes/no): ")
        if response.lower() == 'yes':
            print()
            print("⏳ Copying memories...")
            print()
            counts = copy_memories(str(source_path), str(target_path), dry_run=False)

            if counts:
                print()
                print("✅ Copy complete!")
                print()
                print("Copied:")
                total = 0
                for key, value in counts.items():
                    print(f"  ✓ {key}: {value}")
                    total += value
                print()
                print(f"🎉 Total records copied: {total}")
        else:
            print("Cancelled.")
    else:
        print("❌ Failed to read source database")
        sys.exit(1)


if __name__ == "__main__":
    main()
