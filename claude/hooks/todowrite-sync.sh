#!/bin/bash
# Hook: TodoWrite Status Change Sync
# Purpose: Capture TodoWrite status changes and sync to Athena planning system
# This keeps todos persistent across /clear by storing them in PostgreSQL
# Fires on: UserPromptSubmit (captures todo list state)
# Target Duration: <100ms

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Log functions
log() {
    echo -e "${GREEN}[TODOWRITE-SYNC]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[TODOWRITE-INFO]${NC} $1" >&2
}

log_debug() {
    if [ "$DEBUG" = "1" ]; then
        echo -e "${CYAN}[TODOWRITE-DEBUG]${NC} $1" >&2
    fi
}

log "Syncing TodoWrite items to Athena..."

# Sync TodoWrite todos to Athena planning system
python3 << 'PYTHON_EOF'
import sys
import json
import os
import logging
from datetime import datetime

# Suppress verbose logging
logging.basicConfig(level=logging.WARNING)

sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from todowrite_helper import TodoWriteSyncHelper
    from memory_bridge import MemoryBridge

    start_time = datetime.now()

    # Initialize sync helper
    sync_helper = TodoWriteSyncHelper()

    # Get current project context
    with MemoryBridge() as bridge:
        project_path = os.getcwd()
        project = bridge.get_project_by_path(project_path)

        if not project:
            # Default to athena project (id=2) - this is the primary development project
            project = {'id': 2}

        project_id = project['id']

    log_info = lambda msg: print(f"  ✓ {msg}", file=sys.stderr)
    log_error = lambda msg: print(f"  ✗ {msg}", file=sys.stderr)
    log_debug = lambda msg: None  # Suppress debug

    if os.environ.get('DEBUG') == '1':
        log_debug = lambda msg: print(f"  [DEBUG] {msg}", file=sys.stderr)

    # Ensure table exists
    if not sync_helper.ensure_todowrite_plans_table():
        log_error("Failed to ensure todowrite_plans table")
        sys.exit(0)

    log_info("Todowrite sync ready")

    # Note: Actual todo capture happens via Claude Code's TodoWrite tool
    # This hook ensures the table exists and handles syncing when triggered
    # TODO: Integrate with Claude Code's todo list capture mechanism

    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
    print(f"✓ TodoWrite sync initialized ({elapsed_ms:.0f}ms)", file=sys.stderr)

except ImportError as e:
    print(f"✗ Could not import TodoWrite sync: {str(e)}", file=sys.stderr)
    sys.exit(0)
except Exception as e:
    print(f"✗ TodoWrite sync error: {str(e)}", file=sys.stderr)
    sys.exit(0)

PYTHON_EOF

exit 0
