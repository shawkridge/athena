#!/bin/bash
# Hook: Architecture Context Injection
# Purpose: Automatically inject architectural context (ADRs, patterns, constraints) into conversations
# Uses MemoryBridge to access architecture layer via PostgreSQL
# Target Duration: <300ms (transparent to user)

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Log functions
log() {
    echo -e "${GREEN}[ARCH-CONTEXT]${NC} $1" >&2
}

log_found() {
    echo -e "${CYAN}[FOUND]${NC} $1" >&2
}

# Get user prompt from environment
USER_PROMPT="${1:-}"

if [ -z "$USER_PROMPT" ]; then
    exit 0
fi

# Only inject architecture context when discussing design/architecture/patterns
# Check for relevant keywords
if ! echo "$USER_PROMPT" | grep -qiE "(design|architect|pattern|constraint|decision|adr|refactor|implement|structure|component)"; then
    # Not architecture-related, skip injection
    exit 0
fi

log "Checking architectural context..."

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

    # Phase 1: Get active ADRs (accepted decisions)
    with PerformanceTimer("get_active_adrs"):
        adrs = bridge.get_active_adrs(project_id, limit=5)

    if adrs['count'] > 0:
        print(f"✓ Active architectural decisions ({adrs['count']}):", file=sys.stderr)
        for i, adr in enumerate(adrs['adrs'][:3], 1):
            print(f"  {i}. {adr['title']}", file=sys.stderr)
            print(f"     → {adr['decision']}", file=sys.stderr)

    # Phase 2: Get unsatisfied hard constraints
    with PerformanceTimer("get_unsatisfied_constraints"):
        constraints = bridge.get_unsatisfied_constraints(project_id, limit=5)

    if constraints['count'] > 0:
        print(f"⚠️  Unsatisfied constraints ({constraints['count']}):", file=sys.stderr)
        for i, constraint in enumerate(constraints['constraints'][:3], 1):
            print(f"  {i}. [{constraint['type']}] {constraint['description']} (priority: {constraint['priority']})", file=sys.stderr)

    # Phase 3: Get effective patterns for this project
    with PerformanceTimer("get_effective_patterns"):
        patterns = bridge.get_effective_patterns(project_id, limit=5)

    if patterns['count'] > 0:
        print(f"✓ Effective patterns ({patterns['count']}):", file=sys.stderr)
        for i, pattern in enumerate(patterns['patterns'][:3], 1):
            effectiveness_pct = int(pattern['effectiveness'] * 100) if pattern['effectiveness'] else 0
            print(f"  {i}. {pattern['name']} [{pattern['type']}] ({effectiveness_pct}% effective)", file=sys.stderr)

    # Summary
    if adrs['count'] == 0 and constraints['count'] == 0 and patterns['count'] == 0:
        print(f"ℹ️  No architectural context available yet", file=sys.stderr)
        print(f"   Consider creating ADRs for important decisions", file=sys.stderr)

    bridge.close()

except ImportError as e:
    print(f"⚠ Could not import MemoryBridge: {str(e)}", file=sys.stderr)
except Exception as e:
    print(f"⚠ Architecture context: {str(e)}", file=sys.stderr)

PYTHON_EOF

log "Architecture context check complete"
exit 0
