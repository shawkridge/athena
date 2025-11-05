#!/bin/bash
# Hook: Activate wm-monitor skill at session start
#
# Purpose: Check working memory capacity and warn if near saturation
# Calls: memory_tools:check_cognitive_load
# Impact: Enables automatic cognitive overload detection at session start


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.182227

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "session-start-wm-monitor"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Input: Standard hook JSON
read -r INPUT_JSON

# Extract session_id
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

# ============================================================
# Call Athena MCP: Check cognitive load
# ============================================================

wm_result=$(python3 << 'PYTHON_WRAPPER'
import sys
import json
sys.path.insert(0, '/home/user/.claude/hooks/lib')

from mcp_wrapper import call_mcp

# Call MCP operation with graceful fallback
result = call_mcp("update_working_memory")

print(json.dumps(result))
PYTHON_WRAPPER
)

# Parse result
success=$(echo "$wm_result" | jq -r '.success // false')
current_load=$(echo "$wm_result" | jq -r '.current_load // 0')
max_capacity=$(echo "$wm_result" | jq -r '.max_capacity // 7')
utilization=$(echo "$wm_result" | jq -r '.utilization_percent // 0')
status=$(echo "$wm_result" | jq -r '.status // "unknown"')
recommendation=$(echo "$wm_result" | jq -r '.recommendation // ""')

# ============================================================
# Return Hook Response
# ============================================================

suppress_output="true"
message=""

if [ "$success" = "true" ]; then
  # Determine appropriate response based on load
  if [ "${current_load%.*}" -ge 6 ] && [ "$max_capacity" = "7" ]; then
    # CRITICAL: Near capacity
    suppress_output="false"
    message="🚨 CRITICAL: Cognitive load at $current_load/$max_capacity. Run /consolidate to free capacity."
  elif [ "${current_load%.*}" -ge 5 ] && [ "$max_capacity" = "7" ]; then
    # WARNING: High load
    suppress_output="false"
    message="⚠️ WARNING: Cognitive load at $current_load/$max_capacity (${utilization}%). Consider consolidating."
  else
    # OK: Normal load
    suppress_output="true"
    message="✅ Cognitive load OK: $current_load/$max_capacity items"
  fi
else
  suppress_output="true"
  message="ℹ️ WM Monitor: Running in background"
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
  log_hook_success "session-start-wm-monitor" "$hook_duration_ms" "Hook completed successfully (status: $status, load: $current_load/$max_capacity)"
else
  log_hook_failure "session-start-wm-monitor" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
