#!/bin/bash
# Hook: Activate attention-manager skill on user prompt
#
# Purpose: Update working memory with context from current prompt, manage attention focus
# Calls: memory_tools:update_working_memory
# Impact: Enables dynamic working memory management based on prompt context


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.182809

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "user-prompt-submit-attention-manager"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

read -r INPUT_JSON

# ============================================================
# Call Athena MCP: Update working memory with prompt context
# ============================================================

attention_result=$(python3 << 'PYTHON_WRAPPER'
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
success=$(echo "$attention_result" | jq -r '.success // false')
status=$(echo "$attention_result" | jq -r '.status // "unknown"')
current_items=$(echo "$attention_result" | jq -r '.current_items // 0')
capacity=$(echo "$attention_result" | jq -r '.capacity // 7')

# ============================================================
# Return Hook Response
# ============================================================

jq -n \
  --arg status "$status" \
  --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "UserPromptSubmitAttentionManager",
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
  log_hook_success "user-prompt-submit-attention-manager" "$hook_duration_ms" "Hook completed successfully (status: $status, items: $current_items/$capacity)"
else
  log_hook_failure "user-prompt-submit-attention-manager" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
