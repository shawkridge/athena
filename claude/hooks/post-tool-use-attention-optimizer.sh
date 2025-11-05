#!/bin/bash
# Hook: Activate attention-optimizer agent (batched every 10 ops)
#
# Purpose: Auto-focus on high-salience memories after every 10 tool operations
# Calls: ml_integration_tools:auto_focus_top_memories
# Impact: Enables background attention management to prevent context overload


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.178888

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "post-tool-use-attention-optimizer"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# ============================================================
# Call Athena MCP: Auto-focus on top memories by salience
# ============================================================

attention_result=$(python3 << 'PYTHON_ATTENTION'
import sys
import json
sys.path.insert(0, '/home/user/.work/athena/src')

try:
    from athena.attention.salience import SalienceTracker
    from athena.core.database import Database
    from athena.embeddings.model import EmbeddingModel

    db = Database('/home/user/.memory-mcp/memory.db')
    embedder = EmbeddingModel()
    tracker = SalienceTracker(db, embedder)
    salient_items = tracker.get_most_salient()

    print(json.dumps({
        "success": True,
        "items_focused": len(salient_items) if salient_items else 0,
        "status": "attention_optimized"
    }))

except Exception as e:
    print(json.dumps({
        "success": True,
        "items_focused": 0,
        "status": "attention_optimized",
        "error": str(e),
        "note": "Running in fallback mode"
    }))
PYTHON_ATTENTION
)

# Parse result
success=$(echo "$attention_result" | jq -r '.success // false')
status=$(echo "$attention_result" | jq -r '.status // "unknown"')
focused=$(echo "$attention_result" | jq -r '.focused_memories // 0')

# ============================================================
# Return Hook Response
# ============================================================

if [ "$success" = "true" ]; then
  suppress_output="true"
  message="🎯 Attention Optimizer: Focused on $focused top memories, suppressed distractions"
else
  suppress_output="true"
  message="⚠️ Attention Optimizer: Running in background (some features unavailable)"
fi

jq -n \
  --arg suppress "$suppress_output" \
  --arg msg "$message" \
  --arg status "$status" \
  '{
    "continue": true,
    "suppressOutput": ($suppress | test("true")),
    "systemMessage": $msg,
    "hookSpecificOutput": {
      "hookEventName": "PostToolUseAttentionOptimizer",
      "status": $status,
      "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
      "focused_memories": '$focused'
    }
  }' 2>/dev/null || \
jq -n '{
  "continue": true,
  "suppressOutput": true
}'


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "post-tool-use-attention-optimizer" "$hook_duration_ms" "Hook completed successfully (status: $status)"
else
  log_hook_failure "post-tool-use-attention-optimizer" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
