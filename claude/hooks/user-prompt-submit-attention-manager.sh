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

INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# ============================================================
# Call Athena MCP: Update working memory with prompt context
# ============================================================

attention_result=$(python3 << 'PYTHON_WRAPPER'
import sys
import json
sys.path.insert(0, '/home/user/.work/athena/src')

from athena.core.database import Database
from athena.working_memory import CentralExecutive
from athena.working_memory.models import WorkingMemoryItem, ContentType

db = Database('/home/user/.athena/memory.db')
ce = CentralExecutive(db, project_id=1)

item = WorkingMemoryItem(
    content="User submitted prompt - updating context focus",
    content_type=ContentType.VERBAL,
    importance=0.8
)

result = ce.add_to_working_memory(item)

print(json.dumps({"success": True, "status": "memory_updated", "result": str(result)}))
PYTHON_WRAPPER
)

# Parse result - fail if invalid JSON
echo "$attention_result" | jq empty || exit 1

success=$(echo "$attention_result" | jq -r '.success')
status=$(echo "$attention_result" | jq -r '.status')
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
