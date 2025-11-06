#!/bin/bash
# Hook: Post Tool Use
# Purpose: Record episodic events, track execution patterns, manage cognitive load
# Agents: Every 10 operations: attention-optimizer
# Target Duration: <100ms per operation, <1s per 10-op batch

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log functions (to stderr so they don't pollute stdout)
log() {
    echo -e "${GREEN}[POST-TOOL-USE]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[POST-TOOL-USE]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[POST-TOOL-USE ERROR]${NC} $1" >&2
}

# Get tool execution data from environment
TOOL_NAME="${TOOL_NAME:-unknown}"
TOOL_STATUS="${TOOL_STATUS:-unknown}"
EXECUTION_TIME_MS="${EXECUTION_TIME_MS:-0}"

# Increment operation counter
OPERATIONS_COUNTER_FILE="/tmp/.claude_operations_counter_$$"
if [ -f "$OPERATIONS_COUNTER_FILE" ]; then
    COUNTER=$(cat "$OPERATIONS_COUNTER_FILE")
    COUNTER=$((COUNTER + 1))
else
    COUNTER=1
fi
echo "$COUNTER" > "$OPERATIONS_COUNTER_FILE"

# Record episodic event to memory
log "Recording episodic event: $TOOL_NAME ($TOOL_STATUS)"

# Build JSON payload for episodic event
EVENT_PAYLOAD=$(cat <<'EOF'
{
  "event_type": "tool_execution",
  "tool_name": "'$TOOL_NAME'",
  "status": "'$TOOL_STATUS'",
  "duration_ms": '$EXECUTION_TIME_MS',
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}
EOF
)

# Call MCP tool to record episodic event
# This stores tool execution details in episodic memory for later consolidation
mcp__athena__episodic_tools record_event \
  --event-type "tool_execution" \
  --content "$EVENT_PAYLOAD" \
  --outcome "$TOOL_STATUS" 2>/dev/null || true

log "✓ Episodic event recorded"

# Check for anomalies/errors
if [ "$TOOL_STATUS" != "success" ]; then
    log_warn "Tool failed: $TOOL_NAME - Status: $TOOL_STATUS"

    # Invoke error-handler agent to analyze failure
    # Uses agent_invoker to log the agent invocation
    python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker
invoker = AgentInvoker()
invoker.invoke_agent("error-handler", {
    "tool_name": "$TOOL_NAME",
    "error_status": "$TOOL_STATUS"
})
PYTHON_EOF
fi

# Check execution time
if [ "$EXECUTION_TIME_MS" -gt 5000 ]; then
    log_warn "Slow operation: $TOOL_NAME took ${EXECUTION_TIME_MS}ms (threshold: 5000ms)"
fi

# Every 10 operations: trigger attention-optimizer
if [ $((COUNTER % 10)) -eq 0 ]; then
    log "Batch complete ($COUNTER operations) - Triggering attention-optimizer"

    # Invoke attention-optimizer agent to check cognitive load and consolidate if needed
    python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker
from load_monitor import LoadMonitor

invoker = AgentInvoker()
monitor = LoadMonitor()

# Get current cognitive load status
status = monitor.get_status()

# Invoke attention-optimizer with load information
invoker.invoke_agent("attention-optimizer", {
    "current_load": status["items"],
    "load_zone": status["zone"],
    "should_consolidate": status["should_consolidate"]
})

log "✓ Attention optimization check complete (load: {status['items']}/7)"
PYTHON_EOF
fi

# Clean up old counter files occasionally
if [ $((COUNTER % 100)) -eq 0 ]; then
    find /tmp -name ".claude_operations_counter_*" -mtime +1 -delete 2>/dev/null || true
fi

# Exit successfully (non-blocking)
exit 0
