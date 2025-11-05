#!/bin/bash
# Hook: Activate learning-tracker skill at session end
#
# Purpose: Analyze encoding effectiveness and learning patterns across domains
# Calls: skills_tools:get_learning_rates via analysis of episodic events
# Impact: Enables tracking of learning strategy effectiveness over time


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.181675

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "session-end-learning-tracker"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

read -r INPUT_JSON
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

# ============================================================
# Call Athena MCP: Analyze learning effectiveness
# ============================================================

learning_result=$(python3 << 'PYTHON_WRAPPER'
import sys
import json
sys.path.insert(0, '/home/user/.claude/hooks/lib')

from mcp_wrapper import call_mcp

# Call MCP operation with graceful fallback
result = call_mcp("get_learning_rates")

print(json.dumps(result))
PYTHON_WRAPPER
)

# Parse result
success=$(echo "$learning_result" | jq -r '.success // false')
status=$(echo "$learning_result" | jq -r '.status // "unknown"')
top_strategy=$(echo "$learning_result" | jq -r '.top_strategy // "unknown"')
effectiveness=$(echo "$learning_result" | jq -r '.effectiveness_score // 0')

# ============================================================
# Return Hook Response
# ============================================================

if [ "$success" = "true" ]; then
  suppress_output="false"
  message="📊 Learning Tracker: Top strategy: $top_strategy (effectiveness: $effectiveness). Run /learning for detailed analysis."
else
  suppress_output="true"
  message="⚠️ Learning Tracker: Running in background"
fi

jq -n \
  --arg status "$status" \
  --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "SessionEndLearningTracker",
      "status": $status,
      "timestamp": $timestamp
    }
  }' || jq -n '{
  "continue": true,
  "suppressOutput": true
}'

# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

log_hook_success "session-end-learning-tracker" "$hook_duration_ms" "Hook completed successfully (status: $status, top_strategy: $top_strategy)"

exit 0
