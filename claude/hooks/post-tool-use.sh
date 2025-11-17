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

# DEBUG: Log raw hook input to a file for inspection (optional, for troubleshooting)
# Disabled by default - enable with: DEBUG_HOOKS_RECORD=1
if [ "${DEBUG_HOOKS_RECORD:-0}" = "1" ]; then
    echo "$hook_input" >> /tmp/claude_hook_inputs.jsonl 2>/dev/null
fi

# Also log to stderr if DEBUG_HOOKS is set
if [ "${DEBUG_HOOKS:-0}" = "1" ]; then
    log "DEBUG: Raw hook input:"
    echo "$hook_input" | jq '.' >&2 || echo "$hook_input" >&2
fi

# Extract key variables from hook input for use in shell conditionals later
TOOL_NAME=$(echo "$hook_input" | jq -r '.tool_name // "unknown"')
TOOL_STATUS=$(echo "$hook_input" | jq -r '.tool_response.status // "unknown"')
EXECUTION_TIME_MS=$(echo "$hook_input" | jq -r '.tool_response.duration_ms // 0')

# Increment operation counter
OPERATIONS_COUNTER_FILE="/tmp/.claude_operations_counter_$$"
if [ -f "$OPERATIONS_COUNTER_FILE" ]; then
    COUNTER=$(cat "$OPERATIONS_COUNTER_FILE")
    COUNTER=$((COUNTER + 1))
else
    COUNTER=1
fi
echo "$COUNTER" > "$OPERATIONS_COUNTER_FILE"

# Source environment variables for database connections
if [ -f "/home/user/.work/athena/.env.local" ]; then
    export $(grep -v '^#' /home/user/.work/athena/.env.local | xargs)
fi

# Call Python directly to record episodic event using memory bridge
# Pass hook input JSON as an environment variable (since heredoc doesn't accept piped stdin)
# This stores tool execution details in memory for later consolidation and response capture
export HOOK_INPUT_JSON="$hook_input"

python3 << 'PYTHON_EOF'
import sys
import os
import json
from datetime import datetime

# Add hooks lib to path
sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from memory_bridge import MemoryBridge
    from tool_validator import validate_tool_name, validate_tool_status, validate_execution_time
    from tool_response_parser import ToolResponseParser

    # Parse hook input from environment variable (passed from shell export)
    try:
        hook_input_json = os.environ.get('HOOK_INPUT_JSON', '{}')
        if not hook_input_json or hook_input_json == '{}':
            print(f"⚠ HOOK_INPUT_JSON environment variable is empty or missing!", file=sys.stderr)
            hook_input = {}
        else:
            hook_input = json.loads(hook_input_json)
    except json.JSONDecodeError as e:
        print(f"⚠ Failed to parse hook input JSON: {e}", file=sys.stderr)
        print(f"   HOOK_INPUT_JSON (first 200 chars): {hook_input_json[:200]}", file=sys.stderr)
        hook_input = {}

    # Extract tool metadata directly from hook input
    tool_name_raw = hook_input.get('tool_name')
    session_id = hook_input.get('session_id', 'unknown')
    cwd = hook_input.get('cwd', '.')

    # Extract tool response object (contains tool-specific metadata)
    # Note: Claude Code does NOT provide 'status' or 'duration_ms' fields
    tool_response_obj = hook_input.get('tool_response', {})

    # Infer status from tool response presence (no errors means success)
    # Claude Code only calls PostToolUse hooks for successful tool executions
    tool_status_raw = "success" if tool_response_obj else "failure"

    # Duration is not provided by Claude Code hooks, so we skip it
    duration_raw = None

    # Use tool response parser for detailed metadata extraction
    if tool_name_raw and tool_response_obj:
        parser = ToolResponseParser()
        parsed_response = parser.parse(tool_name_raw, tool_response_obj)
        tool_summary = parsed_response.summary
    else:
        tool_summary = None

    # Validate tool name (status and duration not needed since Claude Code doesn't provide them)
    tool_result = validate_tool_name(tool_name_raw)

    # Tool successfully executed (PostToolUse is only called on success)
    # So we always treat this as "success" outcome
    if tool_result.valid:
        # Tool name is valid
        content_str = f"Tool: {tool_result.tool_name}"

        # Add detailed summary if available from parser
        if tool_summary:
            content_str = f"Tool: {tool_result.tool_name} | {tool_summary}"

        outcome = "success"
    else:
        # Invalid tool name (log the error)
        if tool_result.message:
            print(f"⚠ TOOL_NAME validation failed: {tool_result.message}", file=sys.stderr)

        # Create fallback content with whatever info we have
        if tool_name_raw:
            content_str = f"Tool: {tool_name_raw} (validation: {tool_result.error})"
        else:
            content_str = f"Tool execution recorded (no tool_name in hook input)"

        outcome = "recorded"

    # Calculate self-improvement metrics
    # These help Athena learn and optimize over time
    importance_score = 0.5  # Default
    if tool_result.valid:
        # Successful, validated tool executions are important
        importance_score = 0.7

    actionability_score = 0.5
    if tool_name_raw in ("Bash", "Edit", "Write"):
        # Tools that modify state are more actionable for learning
        actionability_score = 0.8

    # Extract what was actually done from tool input
    tool_input_obj = hook_input.get('tool_input', {})
    context_task = None
    context_files = None
    files_changed = 0

    # Extract context based on tool type
    if tool_name_raw == "Bash":
        command = tool_input_obj.get('command', '')
        context_task = f"Execute: {command[:100]}"
    elif tool_name_raw == "Read":
        file_path = tool_input_obj.get('file_path', '')
        context_task = f"Read: {file_path}"
        context_files = [file_path] if file_path else None
    elif tool_name_raw == "Write":
        file_path = tool_input_obj.get('file_path', '')
        context_task = f"Write: {file_path}"
        context_files = [file_path] if file_path else None
        files_changed = 1
    elif tool_name_raw == "Edit":
        file_path = tool_input_obj.get('file_path', '')
        context_task = f"Edit: {file_path}"
        context_files = [file_path] if file_path else None
        files_changed = 1
    elif tool_name_raw == "Glob":
        pattern = tool_input_obj.get('pattern', '')
        context_task = f"Search: {pattern}"
    elif tool_name_raw == "Grep":
        pattern = tool_input_obj.get('pattern', '')
        context_task = f"Search: {pattern}"
    elif tool_name_raw == "TodoWrite":
        todos = tool_input_obj.get('todos', [])
        context_task = f"Update todos: {len(todos)} items"
    elif tool_name_raw == "AskUserQuestion":
        context_task = "Collect user input"

    # Compute what we learned from this tool execution
    learned_str = None
    if tool_result.valid:
        learned_str = f"Tool {tool_result.tool_name} executed successfully with metadata: {tool_summary if tool_summary else 'generic execution'}"

    with MemoryBridge() as bridge:
        project = bridge.get_project_by_path(os.getcwd())
        if project:
            # First, record the basic event
            event_id = bridge.record_event(
                project_id=project['id'],
                event_type="tool_execution",
                content=content_str,
                outcome=outcome
            )

            # Then enhance it with self-improvement metadata via direct update
            if event_id:
                try:
                    from connection_pool import PooledConnection
                    with PooledConnection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE episodic_events
                            SET
                                importance_score = %s,
                                actionability_score = %s,
                                context_cwd = %s,
                                context_task = %s,
                                context_files = %s,
                                files_changed = %s,
                                learned = %s,
                                consolidation_status = %s,
                                context_completeness_score = %s
                            WHERE id = %s
                        """, (
                            importance_score,
                            actionability_score,
                            cwd,
                            context_task,
                            context_files,
                            files_changed,
                            learned_str,
                            "unconsolidated",  # Fresh events ready for consolidation
                            0.8 if tool_result.valid else 0.3,  # How much context we captured
                            event_id
                        ))
                        conn.commit()
                except Exception as e:
                    print(f"⚠ Could not enhance event metadata: {e}", file=sys.stderr)

            if event_id:
                if tool_result.valid:
                    print(f"✓ Tool execution recorded: {tool_result.tool_name} (Status: success, ID: {event_id})", file=sys.stderr)
                else:
                    print(f"✓ Tool execution recorded with available metadata (tool_name={tool_name_raw}, ID: {event_id})", file=sys.stderr)
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
        "tool_name": tool_result.tool_name if tool_result.valid else (tool_name_raw or "unknown"),
        "tool_status": "success" if tool_result.valid else (tool_status_raw or "unknown"),
        "execution_time_ms": 0,
        "timestamp": datetime.utcnow().isoformat(),
        "success": tool_result.valid if 'tool_result' in locals() else (tool_status_raw == "success")
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

# Phase 4.5: Notify MemoryCoordinatorAgent of tool execution
# The agent will decide if this tool execution should be remembered
python3 << 'MEMORY_COORD_EOF'
import sys
import os
import json

sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from agent_bridge import notify_tool_execution

    # Extract tool details from hook input
    hook_input_str = os.environ.get('HOOK_INPUT_JSON', '{}')
    try:
        hook_input = json.loads(hook_input_str)
    except:
        hook_input = {}

    tool_name = hook_input.get('tool_name', 'unknown')
    tool_status = hook_input.get('tool_response', {}).get('status', 'unknown')
    duration_ms = hook_input.get('tool_response', {}).get('duration_ms', 0)

    # Get input and output summaries
    input_summary = str(hook_input.get('parameters', {}))[:100]
    output_summary = str(hook_input.get('tool_response', {}).get('content', ''))[:100]
    success = tool_status == 'success'

    # Notify agent
    result = notify_tool_execution(
        tool_name=tool_name,
        input_summary=input_summary,
        output_summary=output_summary,
        success=success,
    )

    if result.get('decided'):
        print(f"✓ MemoryCoordinatorAgent decided to remember this ({result.get('memory_type')})", file=sys.stderr)
    else:
        print(f"· MemoryCoordinatorAgent: Skipped (not important enough)", file=sys.stderr)

except Exception as e:
    # Don't fail hook if agent notification fails
    print(f"· MemoryCoordinatorAgent notification skipped: {str(e)}", file=sys.stderr)

MEMORY_COORD_EOF

# Phase 4.6: Track decision outcome and performance in learning system
# This enables the adaptive learning system to learn from agent decisions
python3 << 'LEARNING_TRACK_EOF'
import sys
import os
import json
import time

sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from learning_bridge import track_decision, record_perf, get_success_rate

    # Extract tool details from hook input
    hook_input_str = os.environ.get('HOOK_INPUT_JSON', '{}')
    try:
        hook_input = json.loads(hook_input_str)
    except:
        hook_input = {}

    tool_name = hook_input.get('tool_name', 'unknown')
    tool_status = hook_input.get('tool_response', {}).get('status', 'success')
    duration_ms = hook_input.get('tool_response', {}).get('duration_ms', 0)

    # Determine success rate based on tool status
    success_rate = 1.0 if tool_status in ['success', 'completed'] else 0.0

    # Track MemoryCoordinatorAgent decision
    # Agent decides whether to remember this tool execution
    agent_decision_context = {
        'tool_name': tool_name,
        'tool_status': tool_status,
        'importance_determined_by': 'memory-coordinator-heuristics'
    }

    result = track_decision(
        agent_name='memory-coordinator',
        decision='should_remember',
        outcome='success' if success_rate > 0.5 else 'failure',
        success_rate=success_rate,
        execution_time_ms=float(duration_ms) if duration_ms else 0.0,
        context=agent_decision_context
    )

    if result.get('status') == 'success':
        print(f"✓ Learning tracked: memory-coordinator decision (rate: {success_rate:.2f})", file=sys.stderr)
    else:
        print(f"· Learning tracking skipped: {result.get('error', 'unknown error')}", file=sys.stderr)

    # Record performance metrics for this agent operation
    perf_result = record_perf(
        agent_name='memory-coordinator',
        operation=f'notify_{tool_name.lower()}',
        execution_time_ms=50.0,  # Approximate: agent notification is fast
        memory_mb=None,
        result_size=None
    )

    if perf_result.get('status') == 'success':
        perf_score = perf_result.get('perf_score', 0.0)
        perf_status = perf_result.get('perf_status', 'unknown')
        print(f"✓ Performance recorded: {perf_status} (score: {perf_score:.2f})", file=sys.stderr)

except Exception as e:
    # Don't fail hook if learning tracking fails
    print(f"· Learning tracking skipped: {str(e)}", file=sys.stderr)

LEARNING_TRACK_EOF

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

print(f"✓ Attention optimization check complete (load: {status['items']}/7)", file=sys.stderr)
PYTHON_EOF
fi

# Clean up old counter files occasionally
if [ $((COUNTER % 100)) -eq 0 ]; then
    find /tmp -name ".claude_operations_counter_*" -mtime +1 -delete 2>/dev/null || true
fi

# Exit successfully (non-blocking)
exit 0
