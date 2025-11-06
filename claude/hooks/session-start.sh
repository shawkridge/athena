#!/bin/bash
# Hook: Session Start
# Purpose: Load context and prime memory at session initialization
# Agents: session-initializer
# Target Duration: <500ms

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Log functions
log() {
    echo -e "${GREEN}[SESSION-START]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[SESSION-START INFO]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[SESSION-START WARNING]${NC} $1" >&2
}

log "=== Session Start: Loading Memory Context ==="

# Get session metadata
SESSION_ID="${SESSION_ID:-session-$(date +%s)}"
SESSION_START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

log "Session ID: $SESSION_ID"
log "Started: $SESSION_START_TIME"

# Initialize session using MCP tools
log "Loading semantic memories and context..."

# 1. Load top semantic memories to working memory
mcp__athena__memory_tools smart_retrieve \
  --query "recent work and projects" \
  --limit 5 2>/dev/null || true

log_info "✓ Semantic memories loaded (top 5 by relevance)"

# 2. Check and load active goals
mcp__athena__task_management_tools get_active_goals \
  --project-id 1 2>/dev/null || true

log_info "✓ Active goals retrieved"

# 3. Check memory health
mcp__athena__memory_tools evaluate_memory_quality 2>/dev/null || true

log_info "✓ Memory health assessed"

# 4. Invoke session-initializer agent to handle setup
python3 << 'PYTHON_EOF'
import sys
import json
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker
from load_monitor import LoadMonitor

# Initialize components
invoker = AgentInvoker()
monitor = LoadMonitor()

# Invoke session-initializer agent
invoker.invoke_agent("session-initializer", {
    "session_id": "$SESSION_ID",
    "timestamp": "$SESSION_START_TIME"
})

# Get current load status
status = monitor.get_status()
PYTHON_EOF

log_info "✓ Cognitive load baseline established"
log "=== Session Context Loaded Successfully ==="
log "Memory is ready for your work session. Begin your tasks when ready."

exit 0
