#!/usr/bin/env python3
"""Initialize SQLite database with sqlite-vec support."""

import sqlite3
import sys
from pathlib import Path

try:
    import sqlite_vec
except ImportError:
    print("❌ sqlite-vec not installed. Run: pip install sqlite-vec")
    sys.exit(1)


def init_database(db_path: str, schema_file: str):
    """Initialize database with schema.

    Args:
        db_path: Path to SQLite database
        schema_file: Path to SQL schema file
    """
    # Create database and load sqlite-vec
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    # Read and execute schema
    schema = Path(schema_file).read_text()
    conn.executescript(schema)
    conn.commit()
    conn.close()

    print(f"✓ Database initialized: {db_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python init_sqlite_with_vec.py <db_path> <schema_file>")
        sys.exit(1)

    db_path = sys.argv[1]
    schema_file = sys.argv[2]

    init_database(db_path, schema_file)
