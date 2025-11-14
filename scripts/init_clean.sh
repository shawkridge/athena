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
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
CONTEXT="local development"

DB_NAME="${DB_NAME:-athena}"
DB_USER="${DB_USER:-postgres}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================================="
echo "Athena PostgreSQL Database Initialization"
echo "======================================================================="
echo "Database: postgresql://$DB_HOST:$DB_PORT/$DB_NAME"
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


# Report
echo
echo "======================================================================="
echo "✅ Initialization Complete!"
echo "======================================================================="
echo "PostgreSQL: postgresql://$DB_HOST:$DB_PORT/$DB_NAME"
echo
echo "Next step: Start the application"
echo "  python -m athena.http.server"
echo
echo "======================================================================="
