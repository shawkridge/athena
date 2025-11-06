#!/bin/bash
# Docker entrypoint for Athena MCP server
# Initializes databases before starting server

set -e

DB_PATH="/root/.athena/memory.db"
SCHEMA_FILE="/app/scripts/schema_clean.sql"

echo "Athena MCP Server Starting..."

# Initialize database if it doesn't exist
if [[ ! -f "$DB_PATH" ]]; then
    echo "First run detected - initializing databases..."

    # Initialize SQLite
    if [[ -f "$SCHEMA_FILE" ]]; then
        echo "Initializing SQLite from schema..."
        python3 /app/scripts/init_sqlite_with_vec.py "$DB_PATH" "$SCHEMA_FILE"

        # Add dashboard views
        sqlite3 "$DB_PATH" << 'EOF'
CREATE VIEW IF NOT EXISTS tasks AS SELECT * FROM prospective_tasks;
CREATE TABLE IF NOT EXISTS semantic_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    tags TEXT,
    importance REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
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
        echo "✓ SQLite initialized"
    else
        echo "⚠️  Schema file not found: $SCHEMA_FILE"
    fi

    # Initialize Qdrant (will auto-create collection on first use)
    echo "✓ Qdrant will auto-initialize on first use"
    echo "✓ Initialization complete"
else
    echo "Database already exists, skipping initialization"
fi

# Start the MCP server
echo "Starting MCP HTTP server on port 3000..."
exec python3 src/athena/http/mcp_server.py
