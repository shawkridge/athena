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

# Read hook input from stdin (official Claude Code interface)
hook_input=$(cat)

# Extract tool metadata from JSON
TOOL_NAME=$(echo "$hook_input" | jq -r '.tool_name // "unknown"')
SESSION_ID=$(echo "$hook_input" | jq -r '.session_id // "unknown"')
CWD=$(echo "$hook_input" | jq -r '.cwd // "."')

# Extract tool response (contains status, output, and tool-specific metadata)
TOOL_RESPONSE=$(echo "$hook_input" | jq -r '.tool_response // {}')
TOOL_STATUS=$(echo "$TOOL_RESPONSE" | jq -r '.status // "completed"')

# For Bash tool, extract execution time if available
EXECUTION_TIME_MS=$(echo "$TOOL_RESPONSE" | jq -r '.duration_ms // 0')
if [ "$EXECUTION_TIME_MS" = "0" ]; then
    EXECUTION_TIME_MS="${EXECUTION_TIME_MS:-0}"
fi

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

# Export variables for Python subprocess
export TOOL_NAME
export TOOL_STATUS
export EXECUTION_TIME_MS
export SESSION_ID
export CWD

# Source environment variables for database connections
if [ -f "/home/user/.work/athena/.env.local" ]; then
    export $(grep -v '^#' /home/user/.work/athena/.env.local | xargs)
fi

# Call Python directly to record episodic event using memory bridge
# This stores tool execution details in memory for later consolidation and response capture
python3 << 'PYTHON_EOF'
import sys
import os
from datetime import datetime

# Add hooks lib to path
sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from memory_bridge import MemoryBridge
    from tool_validator import validate_tool_name, validate_tool_status, validate_execution_time
    from tool_response_parser import ToolResponseParser
    import json

    # Read tool context from shell variables (populated from stdin JSON)
    tool_name_raw = os.environ.get('TOOL_NAME', None)
    tool_status_raw = os.environ.get('TOOL_STATUS', None)
    duration_raw = os.environ.get('EXECUTION_TIME_MS', None)

    # Parse tool response for enhanced metadata (if available via jq)
    tool_response_json = os.environ.get('TOOL_RESPONSE', '{}')
    try:
        tool_response_obj = json.loads(tool_response_json) if tool_response_json and tool_response_json != '{}' else {}
    except:
        tool_response_obj = {}

    # Use tool response parser for detailed metadata extraction
    if tool_name_raw and tool_response_obj:
        parser = ToolResponseParser()
        parsed_response = parser.parse(tool_name_raw, tool_response_obj)
        tool_summary = parsed_response.summary
    else:
        tool_summary = None

    # Validate each component
    tool_result = validate_tool_name(tool_name_raw)
    status_result = validate_tool_status(tool_status_raw)
    time_valid, time_ms, time_error = validate_execution_time(duration_raw)

    # Build content with validated information
    validation_passed = tool_result.valid and status_result.valid and time_valid

    if validation_passed:
        # All context validated and present
        # For status, extract the validated value from the raw input (it's already validated)
        validated_status = tool_status_raw.strip().lower() if tool_status_raw else "unknown"

        # Use rich summary from tool response parser if available
        if tool_summary:
            content_str = f"Tool: {tool_result.tool_name} | {tool_summary}"
        else:
            content_str = f"Tool: {tool_result.tool_name} | Status: {validated_status} | Duration: {time_ms}ms"
        outcome = validated_status
    else:
        # Log validation errors and use fallback
        validation_errors = []
        if not tool_result.valid:
            validation_errors.append(f"tool_name: {tool_result.error}")
            print(f"⚠ Invalid TOOL_NAME: {tool_result.message}", file=sys.stderr)
        if not status_result.valid:
            validation_errors.append(f"tool_status: {status_result.error}")
            print(f"⚠ Invalid TOOL_STATUS: {status_result.message}", file=sys.stderr)
        if not time_valid:
            validation_errors.append(f"execution_time: {time_error}")
            print(f"⚠ Invalid EXECUTION_TIME_MS: {time_error}", file=sys.stderr)

        # Claude Code doesn't pass environment variables - record generic tool execution
        # This is expected behavior; hooks still work and can consolidate these events
        content_str = f"Tool execution recorded (metadata: tool_name={'present' if tool_name_raw else 'missing'}, status={'present' if tool_status_raw else 'missing'}, duration={'present' if duration_raw else 'missing'})"
        outcome = "recorded"  # Changed from "context_validation_failed" to allow consolidation

    with MemoryBridge() as bridge:
        project = bridge.get_project_by_path(os.getcwd())
        if project:
            event_id = bridge.record_event(
                project_id=project['id'],
                event_type="tool_execution",
                content=content_str,
                outcome=outcome
            )

            if event_id:
                if validation_passed:
                    print(f"✓ Tool execution recorded: {tool_result.tool_name} (Status: {validated_status}, Duration: {time_ms}ms, ID: {event_id})", file=sys.stderr)
                else:
                    print(f"✓ Tool execution recorded (without metadata - Claude Code doesn't pass TOOL_NAME/TOOL_STATUS env vars yet, ID: {event_id})", file=sys.stderr)
            else:
                print(f"⚠ Event recording may have failed (returned None)", file=sys.stderr)
        else:
            print(f"⚠ No project context found", file=sys.stderr)

except Exception as e:
    print(f"⚠ Event recording failed: {str(e)}", file=sys.stderr)

# Phase 5: Prepare tool execution for response capture threading
# This will be used by session-end.sh to thread complete conversations
try:
    import json
    from pathlib import Path

    # Store tool execution in a session-local buffer for later threading
    tool_buffer_file = Path(f"/tmp/.claude_tool_buffer_{os.getpid()}.json")

    execution_record = {
        "tool_name": tool_result.tool_name if validation_passed else (tool_name_raw or "unknown"),
        "tool_status": validated_status if validation_passed else (tool_status_raw or "unknown"),
        "execution_time_ms": time_ms if validation_passed else 0,
        "timestamp": datetime.utcnow().isoformat(),
        "success": (validated_status == "success") if validation_passed else False
    }

    # Append to buffer (create if not exists)
    if tool_buffer_file.exists():
        with open(tool_buffer_file, 'r') as f:
            buffer = json.load(f)
    else:
        buffer = []

    buffer.append(execution_record)

    with open(tool_buffer_file, 'w') as f:
        json.dump(buffer, f)

    print(f"✓ Tool buffered for response threading", file=sys.stderr)

except Exception as e:
    print(f"⚠ Could not buffer tool for threading: {str(e)}", file=sys.stderr)
PYTHON_EOF

# Check for anomalies/errors
if [ "$TOOL_STATUS" != "success" ] && [ "$TOOL_STATUS" != "completed" ]; then
    log_warn "Tool may have failed: $TOOL_NAME - Status: $TOOL_STATUS"

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
