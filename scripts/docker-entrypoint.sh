#!/bin/bash
# Application startup script for Athena Memory System
# Initializes PostgreSQL and starts the application server

set -e

# PostgreSQL connection configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-athena}"
DB_USER="${DB_USER:-postgres}"

echo "Athena Memory System Starting..."
echo "Database: $DB_HOST:$DB_PORT/$DB_NAME"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
max_attempts=30
attempt=0
while ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -gt $max_attempts ]; then
        echo "❌ PostgreSQL not available after $max_attempts attempts"
        exit 1
    fi
    echo "  Attempt $attempt/$max_attempts..."
    sleep 1
done

echo "✓ PostgreSQL is ready"

# Run database migrations
echo "Running database migrations..."
python3 -c "
import sys
sys.path.insert(0, 'src')
from athena.migrations.runner import MigrationRunner
runner = MigrationRunner('postgresql://$DB_USER@$DB_HOST:$DB_PORT/$DB_NAME')
runner.run_pending_migrations()
"

echo "✓ Database initialization complete"

# Start the HTTP server
echo "Starting HTTP server on port 8000..."
exec python3 src/athena/http/server.py
