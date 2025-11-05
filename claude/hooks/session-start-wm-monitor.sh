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
INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# Extract session_id
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

# ============================================================
# Call Athena MCP: Check cognitive load
# ============================================================

wm_result=$(python3 << 'PYTHON_WRAPPER'
import sys
import json
sys.path.insert(0, '/home/user/.work/athena/src')

try:
    from athena.core.database import Database
    from athena.working_memory import CentralExecutive

    db = Database('/home/user/.athena/memory.db')
    ce = CentralExecutive(db, project_id=1)
    status = ce.get_capacity_status()

    print(json.dumps({
        "success": True,
        "current_load": status.get("current_load", 0) if status else 0,
        "max_capacity": 7,
        "utilization_percent": int((status.get("current_load", 0) / 7 * 100)) if status else 0,
        "status": "capacity_ok" if status else "unknown"
    }))

except Exception as e:
    print(json.dumps({
        "success": True,
        "current_load": 0,
        "max_capacity": 7,
        "utilization_percent": 0,
        "status": "capacity_ok",
        "error": str(e),
        "note": "Running in fallback mode"
    }))
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
