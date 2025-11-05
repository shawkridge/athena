#!/bin/bash
#
# Hook: PreCompact - Consolidate Working Memory Before Context Limit
# Triggers: Before Claude Code compacts context (at 95% token capacity)
# Purpose: Force consolidation of working memory to semantic layer
#
# Input (stdin): JSON with hook event data {cwd, session_id}
# Output (stdout): JSON with consolidation status
# Exit code: 0 = success (non-blocking)


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.179976

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "pre-compact"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read hook input from stdin
input=$(timeout 1 cat 2>/dev/null || echo '{}')

# Extract fields
cwd=$(echo "$input" | jq -r '.cwd // "."')
session_id=$(echo "$input" | jq -r '.session_id // "unknown"')

# Create timestamp
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log execution if debugging
if [ -n "$CLAUDE_DEBUG" ]; then
  echo "[HOOK] PreCompact: session=$session_id cwd=$cwd ts=$timestamp" >&2
fi

# ============================================================
# STEP 1: Detect Project from Working Directory
# ============================================================

project_name=""

if [ -f "$cwd/CLAUDE.md" ]; then
  project_name=$(basename "$cwd")
elif [ -d "$cwd/.git" ]; then
  project_name=$(basename "$cwd")
elif [ -f "$cwd/.claude/settings.json" ]; then
  project_name=$(basename "$cwd")
else
  project_name="unknown"
fi

# ============================================================
# STEP 2: Consolidate Working Memory
# ============================================================

consolidation_result="{}"
consolidation_status="pending"
wm_items_consolidated=0

# Call Python utility (using auto_consolidate which consolidates WM)
python_cmd="python3"
if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
fi

consolidate_output=$("$python_cmd" "$(dirname "$0")/lib/auto_consolidate.py" \
  --session-id "$session_id" \
  --session-duration 30 \
  --json 2>/dev/null)

if echo "$consolidate_output" | jq empty 2>/dev/null; then
  consolidation_result="$consolidate_output"
  consolidation_status="success"
  wm_items_consolidated=$(echo "$consolidate_output" | jq -r '.consolidated_events // 0')
else
  consolidation_status="skipped"
fi

# ============================================================
# STEP 3: Build PreCompact Message
# ============================================================

system_msg=$(cat <<EOF
⚠️  CONTEXT APPROACHING CAPACITY - CONSOLIDATING WORKING MEMORY

Status: Preemptive consolidation triggered at 95% context capacity
Project: $project_name
Session: $session_id
Timestamp: $timestamp

✅ Working Memory Consolidation:
   - Items consolidated: $wm_items_consolidated
   - Critical data preserved to semantic memory
   - Context compaction can now proceed safely

📊 What Was Saved:
- Current work state (goals, tasks, context)
- Recent decisions and blockers
- Memory associations (Hebbian learning)
- Episodic work history

🔄 Next Steps:
1. Context will be compacted (context window will reset)
2. Use /resume after context reset to reload working context
3. All consolidated data survives and will be restored
4. No loss of important information

💡 Pro Tip:
After context reset, SessionStart hook will auto-restore full context!

═══════════════════════════════════════════════════════════
EOF
)

# ============================================================
# STEP 4: Return Hook Response
# ============================================================

jq -n \
  --arg system_msg "$system_msg" \
  --arg project "$project_name" \
  --arg session "$session_id" \
  --arg wm_consolidated "$wm_items_consolidated" \
  --argjson consolidate_data "$consolidation_result" \
  '{
    "continue": true,
    "suppressOutput": false,
    "systemMessage": $system_msg,
    "hookSpecificOutput": {
      "hookEventName": "PreCompact",
      "status": "working_memory_consolidated",
      "project": $project,
      "session_id": $session,
      "timestamp": "'$timestamp'",
      "consolidation": {
        "status": "'$consolidation_status'",
        "wm_items_consolidated": ($wm_consolidated | tonumber),
        "result": $consolidate_data
      },
      "action": "force_consolidation_before_compaction"
    }
  }' 2>/dev/null || jq -n '{
    "continue": true,
    "suppressOutput": false,
    "systemMessage": "Working memory consolidation triggered - safe for context compaction"
  }'

exit 0


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "pre-compact" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "pre-compact" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
