#!/bin/bash
# Hook: Session Start
# Purpose: Load working memory from previous session
# Loads 7±2 working memory items, active goals, and recent context
# Target Duration: <300ms

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Log functions
log() {
    echo -e "${GREEN}[SESSION-START]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[SESSION-INFO]${NC} $1" >&2
}

log_context() {
    echo -e "${CYAN}[CONTEXT]${NC} $1" >&2
}

log "Loading session context from memory..."

# Load working memory and active goals using direct PostgreSQL bridge
python3 << 'PYTHON_EOF'
import sys
import logging
import os
from datetime import datetime
import time

# Suppress verbose logging
logging.basicConfig(level=logging.WARNING)

sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from memory_bridge import MemoryBridge

    start_time = time.time()

    # Connect to PostgreSQL
    with MemoryBridge() as bridge:
        # Get current project (based on working directory)
        project_path = os.getcwd()
        project = bridge.get_project_by_path(project_path)

        if not project:
            print("⚠ No project context found", file=sys.stderr)
            sys.exit(0)

        project_id = project['id']

        # Load working memory (7±2 items with highest importance)
        print(f"✓ Loading working memory from previous session...", file=sys.stderr)

        mem_result = bridge.get_active_memories(project_id, limit=7)
        active_items = mem_result.get('items', [])

        if active_items:
            print(f"  ✓ {len(active_items)} active memory items (7±2 capacity):", file=sys.stderr)
            for i, item in enumerate(active_items[:5], 1):
                content_preview = item['content'][:40] + "..." if len(item['content']) > 40 else item['content']
                importance = item['importance']
                print(f"    {i}. [{item['type']}] {content_preview} (importance: {importance:.1%})", file=sys.stderr)
        else:
            print(f"  No previous context found", file=sys.stderr)

        # Load active goals/tasks
        print(f"✓ Loading active goals...", file=sys.stderr)

        goals_result = bridge.get_active_goals(project_id, limit=5)
        goals = goals_result.get('goals', [])

        if goals:
            print(f"  ✓ {len(goals)} active goals:", file=sys.stderr)
            for i, goal in enumerate(goals[:3], 1):
                title_preview = goal['title'][:40] + "..." if len(goal['title']) > 40 else goal['title']
                print(f"    {i}. [{goal['status']}] {title_preview}", file=sys.stderr)
        else:
            print(f"  No active goals found", file=sys.stderr)

        elapsed_ms = (time.time() - start_time) * 1000
        print(f"✓ Session context initialized ({elapsed_ms:.0f}ms)", file=sys.stderr)

        if elapsed_ms > 300:
            print(f"⚠ Session init took {elapsed_ms:.0f}ms (target: <300ms)", file=sys.stderr)

except ImportError as e:
    print(f"⚠ Could not import memory bridge: {str(e)}", file=sys.stderr)
except Exception as e:
    print(f"⚠ Session initialization: {str(e)}", file=sys.stderr)

PYTHON_EOF

log_info "Session ready - memory loaded"
exit 0
