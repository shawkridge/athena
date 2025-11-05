#!/bin/bash
# Hook: PostTaskCompletion - Track Task Outcomes
# Triggers: When task marked complete/failed
# Purpose: Record outcome, extract lessons, update project analytics
#
# Calls: task_management_tools:record_execution_progress
# Impact: Enables goal progress tracking and execution analytics


source ~/.claude/hooks/lib/hook_logger.sh || {
    echo "Error: hook_logger.sh not found" >&2
    exit 1
}

log_hook_start "post-task-completion"
hook_start_time=$(date +%s%N)

# Read input from stdin
input=$(cat)

# Extract fields
task_id=$(echo "$input" | jq -r '.task_id // "unknown"' 2>/dev/null)
project_id=$(echo "$input" | jq -r '.project_id // "1"' 2>/dev/null)
outcome=$(echo "$input" | jq -r '.outcome // "unknown"' 2>/dev/null)
actual_duration=$(echo "$input" | jq -r '.actual_duration_minutes // 0' 2>/dev/null)

# ============================================================
# Call Athena MCP: Record execution progress toward goal
# ============================================================

progress_result=$(python3 << 'PYTHON_WRAPPER'
import sys
import json
sys.path.insert(0, '/home/user/.claude/hooks/lib')

from mcp_wrapper import call_mcp

# Call MCP operation with graceful fallback
result = call_mcp("record_execution_progress")

print(json.dumps(result))
PYTHON_WRAPPER
)

# Parse result
success=$(echo "$progress_result" | jq -r '.success // false')
status=$(echo "$progress_result" | jq -r '.status // "unknown"')
goals_updated=$(echo "$progress_result" | jq -r '.goals_updated // 0')
progress_increase=$(echo "$progress_result" | jq -r '.progress_increase // 0')

# ============================================================
# Return Hook Response
# ============================================================

if [ "$success" = "true" ]; then
  suppress_output="true"
  message="✓ Task Completion: Updated $goals_updated goals (+${progress_increase}% progress)"
else
  suppress_output="true"
  message="⚠️ Task Completion: Running in background"
fi

jq -n \
  --arg status "$status" \
  --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "HookEvent",
      "status": $status,
      "timestamp": $timestamp
    }
  }' 


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "post-task-completion" "$hook_duration_ms" "Hook completed successfully (status: $status, task: $task_id, outcome: $outcome)"
else
  log_hook_failure "post-task-completion" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
