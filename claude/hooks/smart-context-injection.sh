#!/bin/bash
# Hook: Smart Context Injection
# Purpose: Automatically inject relevant memory context into user queries
# Uses direct Python API to search episodic events and tasks
# Target Duration: <300ms (transparent to user)

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Log functions
log() {
    echo -e "${GREEN}[CONTEXT-INJECT]${NC} $1" >&2
}

log_found() {
    echo -e "${CYAN}[FOUND]${NC} $1" >&2
}

# Get user prompt from environment
USER_PROMPT="${1:-}"

if [ -z "$USER_PROMPT" ]; then
    exit 0
fi

log "Searching memory for relevant context..."

# Call Python directly using MemoryBridge for synchronous PostgreSQL access
python3 << 'PYTHON_EOF'
import sys
import logging
import os

# Suppress verbose logging
logging.basicConfig(level=logging.WARNING)

sys.path.insert(0, '/home/user/.claude/hooks/lib')

USER_PROMPT = """$USER_PROMPT"""

try:
    from memory_bridge import MemoryBridge, PerformanceTimer

    # Initialize MemoryBridge (synchronous PostgreSQL access)
    bridge = MemoryBridge()

    # Get current project
    project_path = os.getcwd()
    project = bridge.get_project_by_path(project_path)

    if not project:
        project = bridge.get_project_by_path("/home/user/.work/default")

    if not project:
        print(f"⚠ No project context found", file=sys.stderr)
        bridge.close()
        sys.exit(0)

    project_id = project['id']

    # Phase 1: Get active working memory (7±2 items)
    with PerformanceTimer("get_active_memories"):
        active_mem = bridge.get_active_memories(project_id, limit=7)

    if active_mem['count'] > 0:
        print(f"✓ Active memory ({active_mem['count']} items):", file=sys.stderr)
        for i, item in enumerate(active_mem['items'][:3], 1):
            print(f"  {i}. [{item['type']}] {item['content']}", file=sys.stderr)

    # Phase 2: Search for memories matching query
    with PerformanceTimer("search_memories"):
        results = bridge.search_memories(project_id, USER_PROMPT, limit=5)

    if results['found'] > 0:
        print(f"✓ Found {results['found']} matching memories:", file=sys.stderr)
        for i, result in enumerate(results['results'][:3], 1):
            print(f"  {i}. [{result['type']}] {result['content']}", file=sys.stderr)
    else:
        print(f"✓ No matching memories found", file=sys.stderr)

    # Phase 3: Get active goals
    with PerformanceTimer("get_active_goals"):
        goals = bridge.get_active_goals(project_id, limit=5)

    if goals['count'] > 0:
        print(f"✓ Active goals ({goals['count']}):", file=sys.stderr)
        for i, goal in enumerate(goals['goals'][:2], 1):
            print(f"  {i}. [{goal['status']}] {goal['title']} (priority: {goal['priority']})", file=sys.stderr)

    bridge.close()

except ImportError as e:
    print(f"⚠ Could not import MemoryBridge: {str(e)}", file=sys.stderr)
except Exception as e:
    print(f"⚠ Memory search: {str(e)}", file=sys.stderr)

PYTHON_EOF

log "Context search complete"
exit 0
