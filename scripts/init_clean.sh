#!/bin/bash
# Clean Database Initialization - No Migrations!
#
# This script initializes BOTH SQLite and Qdrant from scratch using a single
# master schema file extracted from a working database.
#
# Usage: ./scripts/init_clean.sh [--local]

set -e  # Exit on error

# Determine paths
if [[ "$1" == "--local" ]]; then
    SQLITE_PATH="$HOME/.athena/memory.db"
    QDRANT_URL="http://localhost:6333"
    CONTEXT="local development"
else
    SQLITE_PATH="/root/.athena/memory.db"
    QDRANT_URL="http://qdrant:6333"
    CONTEXT="Docker container"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_FILE="$SCRIPT_DIR/schema_clean.sql"

echo "======================================================================="
echo "Athena Clean Database Initialization"
echo "======================================================================="
echo "Context:  $CONTEXT"
echo "SQLite:   $SQLITE_PATH"
echo "Qdrant:   $QDRANT_URL"
echo "Schema:   $SCHEMA_FILE"
echo

# Check if schema file exists
if [[ ! -f "$SCHEMA_FILE" ]]; then
    echo "❌ Schema file not found: $SCHEMA_FILE"
    echo "   Run this from project root: ./scripts/init_clean.sh"
    exit 1
fi

# Backup existing database if it exists
if [[ -f "$SQLITE_PATH" ]]; then
    BACKUP_PATH="${SQLITE_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "⚠️  Database exists, creating backup: $BACKUP_PATH"
    cp "$SQLITE_PATH" "$BACKUP_PATH"
    rm "$SQLITE_PATH"
    echo "✓ Deleted old database"
fi

# Ensure directory exists
mkdir -p "$(dirname "$SQLITE_PATH")"

# Initialize SQLite with master schema (requires sqlite-vec)
echo
echo "Initializing SQLite..."
python3 "$SCRIPT_DIR/init_sqlite_with_vec.py" "$SQLITE_PATH" "$SCHEMA_FILE"

# Add dashboard-specific views and tables
echo "Adding dashboard compatibility layer..."
sqlite3 "$SQLITE_PATH" << 'EOF'
-- View: tasks → prospective_tasks
CREATE VIEW IF NOT EXISTS tasks AS SELECT * FROM prospective_tasks;

-- Table: semantic_memories (metadata only, embeddings in Qdrant)
CREATE TABLE IF NOT EXISTS semantic_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    tags TEXT,
    importance REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: knowledge_gaps (dashboard requirement)
CREATE TABLE IF NOT EXISTS knowledge_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gap_type TEXT NOT NULL,
    domain TEXT,
    severity TEXT DEFAULT 'medium',
    description TEXT NOT NULL,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT
);
EOF

# Count tables
TABLE_COUNT=$(sqlite3 "$SQLITE_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type IN ('table', 'view');")
echo "✓ SQLite initialized: $TABLE_COUNT tables/views"

# Verify critical tables
echo
echo "Verifying critical tables..."
CRITICAL_TABLES="episodic_events semantic_memories procedures tasks active_goals entities entity_relations memory_quality knowledge_gaps"
MISSING=""

for table in $CRITICAL_TABLES; do
    if sqlite3 "$SQLITE_PATH" "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name='$table';" | grep -q "$table"; then
        echo "  ✓ $table"
    else
        echo "  ✗ $table MISSING"
        MISSING="$MISSING $table"
    fi
done

if [[ -n "$MISSING" ]]; then
    echo
    echo "❌ Missing tables:$MISSING"
    exit 1
fi

# Initialize Qdrant (Python required)
echo
echo "Initializing Qdrant..."
if command -v python3 &> /dev/null; then
    python3 << 'PYEOF'
import sys
sys.path.insert(0, 'src')

from athena.rag.qdrant_adapter import QdrantAdapter

adapter = QdrantAdapter(url="$QDRANT_URL")
if adapter.health_check():
    print(f"✓ Qdrant connected: {adapter.collection_name}")
    print(f"✓ Embedding dimension: {adapter.embedding_dim}")
    print(f"✓ Memory count: {adapter.count()}")
else:
    print("❌ Qdrant connection failed")
    sys.exit(1)
PYEOF
else
    echo "⚠️  Python3 not found, skipping Qdrant initialization"
    echo "   Qdrant will auto-initialize on first use"
fi

# Report
SIZE=$(du -h "$SQLITE_PATH" | cut -f1)
echo
echo "======================================================================="
echo "✅ Initialization Complete!"
echo "======================================================================="
echo "SQLite:  $SQLITE_PATH ($SIZE)"
echo "Qdrant:  $QDRANT_URL"
echo "Tables:  $TABLE_COUNT"
echo
echo "Next steps:"
if [[ "$1" == "--local" ]]; then
    echo "  docker-compose up -d"
else
    echo "  Databases are ready for use"
fi
echo "======================================================================="
