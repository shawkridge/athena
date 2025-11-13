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

# Record episodic event to memory via direct Python import
log "Recording episodic event: $TOOL_NAME ($TOOL_STATUS)"

# Source environment variables for database connections
if [ -f "/home/user/.work/athena/.env.local" ]; then
    export $(grep -v '^#' /home/user/.work/athena/.env.local | xargs)
fi

# Call Python directly to record episodic event using memory bridge
# This stores tool execution details in memory for later consolidation
python3 << 'PYTHON_EOF'
import sys
import os
from datetime import datetime

# Add hooks lib to path
sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from memory_bridge import MemoryBridge

    tool_name = os.environ.get('TOOL_NAME', 'unknown')
    tool_status = os.environ.get('TOOL_STATUS', 'unknown')
    duration_ms = int(os.environ.get('EXECUTION_TIME_MS', '0'))

    # Record the tool execution event
    content_str = f"Tool: {tool_name} | Status: {tool_status} | Duration: {duration_ms}ms"

    with MemoryBridge() as bridge:
        project = bridge.get_project_by_path(os.getcwd())
        if project:
            event_id = bridge.record_event(
                project_id=project['id'],
                event_type="tool_execution",
                content=content_str,
                outcome=tool_status
            )

            if event_id:
                print(f"✓ Tool execution recorded (ID: {event_id})", file=sys.stderr)
            else:
                print(f"⚠ Event recording may have failed (returned None)", file=sys.stderr)
        else:
            print(f"⚠ No project context found", file=sys.stderr)

except Exception as e:
    print(f"⚠ Event recording failed: {str(e)}", file=sys.stderr)
PYTHON_EOF

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
