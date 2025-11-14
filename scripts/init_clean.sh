#!/bin/bash
# PostgreSQL Database Initialization
#
# This script initializes PostgreSQL from scratch using migration files.
#
# Usage: ./scripts/init_clean.sh [--local]
#
# Requires: PostgreSQL connection configured via DB_* environment variables:
#   - DB_HOST (default: localhost)
#   - DB_PORT (default: 5432)
#   - DB_NAME (default: athena)
#   - DB_USER (default: postgres)
#   - DB_PASSWORD

set -e  # Exit on error

# Determine paths
if [[ "$1" == "--local" ]]; then
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
    QDRANT_URL="http://localhost:6333"
    CONTEXT="local development"
else
    DB_HOST="${DB_HOST:-db}"
    DB_PORT="${DB_PORT:-5432}"
    QDRANT_URL="http://qdrant:6333"
    CONTEXT="Docker container"
fi

DB_NAME="${DB_NAME:-athena}"
DB_USER="${DB_USER:-postgres}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================================="
echo "Athena PostgreSQL Database Initialization"
echo "======================================================================="
echo "Context:  $CONTEXT"
echo "Database: postgresql://$DB_HOST:$DB_PORT/$DB_NAME"
echo "Qdrant:   $QDRANT_URL"
echo

# Test PostgreSQL connection
echo "Testing PostgreSQL connection..."
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; then
    echo "❌ Cannot connect to PostgreSQL"
    echo "   Set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
    exit 1
fi
echo "✓ PostgreSQL connection successful"

# Initialize with migrations
echo
echo "Running database migrations..."
CONNECTION_STRING="postgresql://$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
python3 -c "
from athena.migrations.runner import MigrationRunner
runner = MigrationRunner('$CONNECTION_STRING')
runner.run_pending_migrations()
"

# Verify critical tables
echo
echo "Verifying critical tables..."
CRITICAL_TABLES="episodic_events semantic_memories procedures prospective_tasks active_goals entities entity_relations memory_quality"

for table in $CRITICAL_TABLES; do
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -t -c "SELECT 1 FROM information_schema.tables WHERE table_name='$table' AND table_schema='public'" | grep -q "1"; then
        echo "  ✓ $table"
    else
        echo "  ⚠️  $table (will be created on first use)"
    fi
done

# Initialize Qdrant (Python required)
echo
echo "Initializing Qdrant..."
if command -v python3 &> /dev/null; then
    python3 << 'PYEOF'
import sys
sys.path.insert(0, 'src')

from athena.rag.qdrant_adapter import QdrantAdapter

adapter = QdrantAdapter(url="http://localhost:6333")
if adapter.health_check():
    print(f"✓ Qdrant connected: {adapter.collection_name}")
    print(f"✓ Embedding dimension: {adapter.embedding_dim}")
    print(f"✓ Memory count: {adapter.count()}")
else
    print("⚠️  Qdrant not yet available")
    print("   It will auto-initialize on first use")
PYEOF
else
    echo "⚠️  Python3 not found, skipping Qdrant initialization"
    echo "   Qdrant will auto-initialize on first use"
fi

# Report
echo
echo "======================================================================="
echo "✅ Initialization Complete!"
echo "======================================================================="
echo "PostgreSQL: postgresql://$DB_HOST:$DB_PORT/$DB_NAME"
echo "Qdrant:     $QDRANT_URL"
echo
echo "Next steps:"
if [[ "$1" == "--local" ]]; then
    echo "  Start the application: python -m athena.http.server"
else
    echo "  Databases are ready for use"
fi
echo "======================================================================="
