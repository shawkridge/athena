#!/bin/bash
# Healthcheck for Athena Memory MCP System
# Used by Docker HEALTHCHECK directive

set -e

# ============================================================================
# Configuration
# ============================================================================

ATHENA_HOST="${ATHENA_HOST:-localhost}"
ATHENA_PORT="${ATHENA_PORT:-8000}"
DB_PATH="${HOME}/.athena/memory.db"
TIMEOUT=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# ============================================================================
# Checks
# ============================================================================

# 1. MCP Server HTTP Health Check
check_http_health() {
    if curl -sf --max-time $TIMEOUT \
        "http://${ATHENA_HOST}:${ATHENA_PORT}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} HTTP health check passed"
        return 0
    else
        echo -e "${RED}✗${NC} HTTP health check failed"
        return 1
    fi
}

# 2. Database Connectivity Check
check_database() {
    if [ ! -f "$DB_PATH" ]; then
        echo -e "${RED}✗${NC} Database file not found: $DB_PATH"
        return 1
    fi

    if python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('$DB_PATH', timeout=$TIMEOUT)
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    conn.close()
    print('✓ Database OK')
except Exception as e:
    print(f'✗ Database error: {e}')
    exit(1)
" 2>&1; then
        return 0
    else
        return 1
    fi
}

# 3. Memory Manager Check
check_memory_manager() {
    if python3 -c "
import sys
sys.path.insert(0, '/app/src')
try:
    from athena.manager import UnifiedMemoryManager
    manager = UnifiedMemoryManager()
    # Try a simple operation
    manager.recall('test', 'health check')
    print('✓ Memory manager OK')
except Exception as e:
    print(f'✗ Memory manager error: {e}')
    exit(1)
" 2>&1 | grep -q "OK"; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# Main
# ============================================================================

main() {
    local checks_passed=0
    local checks_total=3

    echo "Running Athena health checks..."
    echo ""

    # Run checks
    check_http_health && ((checks_passed++)) || true
    check_database && ((checks_passed++)) || true
    check_memory_manager && ((checks_passed++)) || true

    echo ""
    echo "Health Check Results: $checks_passed/$checks_total passed"
    echo ""

    # Exit with success if all critical checks pass
    # HTTP health check is critical
    if check_http_health; then
        echo -e "${GREEN}Health check PASSED${NC}"
        exit 0
    else
        echo -e "${RED}Health check FAILED${NC}"
        exit 1
    fi
}

main "$@"
