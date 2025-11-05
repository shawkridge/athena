#!/bin/bash
#
# Hook: PostMemoryTool - Track & Strengthen Memory Tool Usage
# Triggers: After any mcp__memory__* tool completes successfully
# Purpose: Record tool execution and strengthen memory associations
#
# Input (stdin): JSON with hook event data {tool_name, session_id, tool_input}
# Output (stdout): JSON with memory strengthening directives
# Exit code: 0 = success (non-blocking)


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.176905

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "post-memory-tool"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read hook input from stdin
input=$(cat)

# Extract fields
tool_name=$(echo "$input" | jq -r '.tool_name // "unknown"')
session_id=$(echo "$input" | jq -r '.session_id // "unknown"')

# Create timestamp
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log execution if debugging
if [ -n "$CLAUDE_DEBUG" ]; then
  echo "[HOOK] PostMemoryTool: tool=$tool_name session=$session_id ts=$timestamp" >&2
fi

# ============================================================
# STEP 1: Determine Tool Importance & Action Type
# ============================================================

# Classify tool by importance for memory management
importance=""
action_description=""

case "$tool_name" in
  "smart_retrieve"|"run_consolidation"|"validate_plan"|"get_project_status")
    importance="high"
    action_description="High-value query or consolidation executed"
    ;;
  "remember"|"record_event"|"create_task"|"set_goal")
    importance="medium-high"
    action_description="Memory creation or task update executed"
    ;;
  "create_entity"|"create_relation"|"add_observation")
    importance="medium"
    action_description="Knowledge graph update executed"
    ;;
  "recall"|"list_memories"|"recall_events"|"list_tasks")
    importance="medium"
    action_description="Memory retrieval executed"
    ;;
  *)
    importance="low"
    action_description="Memory tool executed"
    ;;
esac

# ============================================================
# STEP 2: Strengthen Memory Associations (Hebbian Learning)
# ============================================================

strengthening_result="{}"
strengthen_status="pending"

# Call Python utility to strengthen associations
python_cmd="python3"
if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
fi

strengthen_output=$("$python_cmd" "$(dirname "$0")/lib/strengthen_links.py" \
  --tool "$tool_name" \
  --importance "$importance" \
  --json 2>/dev/null)

if echo "$strengthen_output" | jq empty 2>/dev/null; then
  strengthening_result="$strengthen_output"
  strengthen_status="success"
else
  strengthen_status="skipped"
fi

# ============================================================
# STEP 3: Return Hook Response - Silent Mode (No User-Facing Output)
# ============================================================

# Return minimal JSON response - no system message for user visibility
# Memory associations are strengthened but output is suppressed for token efficiency
jq -n \
  --arg tool "$tool_name" \
  --arg importance_level "$importance" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "PostToolUse",
      "status": "silent",
      "tool": $tool,
      "importance": $importance_level,
      "timestamp": "'$timestamp'",
      "hebbian_learning": {
        "status": "'$strengthen_status'"
      }
    }
  }' 2>/dev/null || jq -n '{
    "continue": true,
    "suppressOutput": true
  }'

exit 0


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "post-memory-tool" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "post-memory-tool" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
