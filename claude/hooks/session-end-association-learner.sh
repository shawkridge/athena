#!/bin/bash
# Hook: Activate association-learner skill at session end
#
# Purpose: Strengthen memory associations through Hebbian learning from session events
# Calls: episodic_tools:batch_record_events (for linking related concepts)
# Impact: Enables automatic knowledge network densification and pattern reinforcement


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.181410

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "session-end-association-learner"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

read -r INPUT_JSON
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)

# ============================================================
# Call Athena MCP: Strengthen associations via Hebbian learning
# ============================================================

association_result=$(python3 << 'PYTHON_WRAPPER'
import sys
import json
sys.path.insert(0, '/home/user/.claude/hooks/lib')

from mcp_wrapper import call_mcp

# Call MCP operation with graceful fallback
result = call_mcp("strengthen_associations")

print(json.dumps(result))
PYTHON_WRAPPER
)

# Parse result
success=$(echo "$association_result" | jq -r '.success // false')
status=$(echo "$association_result" | jq -r '.status // "unknown"')
associations_strengthened=$(echo "$association_result" | jq -r '.associations_strengthened // 0')
new_associations=$(echo "$association_result" | jq -r '.new_associations // 0')

# ============================================================
# Return Hook Response
# ============================================================

if [ "$success" = "true" ]; then
  suppress_output="true"
  message="🔗 Association Learner: Strengthened $associations_strengthened associations, discovered $new_associations new links"
else
  suppress_output="true"
  message="⚠️ Association Learner: Running in background"
fi

jq -n \
  --arg status "$status" \
  --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "SessionEndAssociationLearner",
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

log_hook_success "session-end-association-learner" "$hook_duration_ms" "Hook completed successfully (status: $status, strengthened: $associations_strengthened)"

exit 0
