#!/bin/bash
#
# Hook: UserPromptSubmit - Tag User Queries & Discover Related Memories
# Triggers: When user submits a prompt/message
# Purpose: Auto-tag queries and discover related memories for context
#
# Input (stdin): JSON with hook event data {transcript_path, session_id, cwd}
# Output (stdout): JSON with query tags and discovered memories
# Exit code: 0 = success (non-blocking)


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.183626

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "user-prompt-submit"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read hook input from stdin
input=$(cat)

# Extract fields
cwd=$(echo "$input" | jq -r '.cwd // "."')
session_id=$(echo "$input" | jq -r '.session_id // "unknown"')
transcript_path=$(echo "$input" | jq -r '.transcript_path // ""')

# Create timestamp
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log execution if debugging
if [ -n "$CLAUDE_DEBUG" ]; then
  echo "[HOOK] UserPromptSubmit: session=$session_id cwd=$cwd ts=$timestamp" >&2
fi

# ============================================================
# STEP 1: Extract Last User Query from Transcript
# ============================================================

user_query=""

if [ -n "$transcript_path" ] && [ -f "$transcript_path" ]; then
  # Try to extract last user message from transcript
  # This is a simplified approach - real implementation would parse full transcript
  user_query=$(tail -c 500 "$transcript_path" 2>/dev/null | grep -o "^[^:]*: .*" | tail -1 | cut -d':' -f2- | sed 's/^ *//' || echo "")
fi

# Fallback: if no query extracted, note it
if [ -z "$user_query" ]; then
  user_query="[Query extraction pending]"
fi

# ============================================================
# STEP 1A: CHECK FOR CONTEXT RECOVERY REQUEST
# ============================================================
# NEW: Auto-detect if user is asking for context recovery
# This runs BEFORE normal context injection to prioritize recovery

recovery_detected="false"
recovery_banner=""
recovered_context="{}"

if [ "$user_query" != "[Query extraction pending]" ] && [ -n "$user_query" ]; then
  python_cmd="python3"
  if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
    python_cmd="/home/user/.work/athena/.venv/bin/python3"
  fi

  recovery_output=$(PYTHONPATH="/home/user/.work/athena/src:$PYTHONPATH" "$python_cmd" "$(dirname "$0")/lib/recover_context.py" \
    --query "$user_query" \
    --db-path "${MEMORY_MCP_DB_PATH:-$HOME/.memory-mcp/memory.db}" \
    --json 2>/dev/null)

  if echo "$recovery_output" | jq empty 2>/dev/null; then
    recovery_detected=$(echo "$recovery_output" | jq -r '.recovery_detected // false')
    recovery_banner=$(echo "$recovery_output" | jq -r '.recovery_banner // ""')
    recovered_context=$(echo "$recovery_output" | jq -r '.recovered_context // {}')

    if [ "$recovery_detected" = "true" ] && [ -n "$recovery_banner" ]; then
      if [ -n "$CLAUDE_DEBUG" ]; then
        echo "[HOOK] Context recovery detected - synthesizing context" >&2
      fi
    fi
  fi
fi

# ============================================================
# STEP 1B: Detect Query Characteristics & Select RAG Strategy
# ============================================================
# NEW: Auto-select RAG strategy based on query analysis
# Strategies:
#   - HyDE: For short/ambiguous queries (<5 words)
#   - QueryTransform: For queries with pronouns/references
#   - LLMReranking: For standard queries (default)

rag_strategy="LLMReranking"  # Default strategy

if [ "$user_query" != "[Query extraction pending]" ] && [ -n "$user_query" ]; then
  query_words=$(echo "$user_query" | wc -w)

  # Check for short/ambiguous queries
  if [ "$query_words" -lt 5 ]; then
    rag_strategy="HyDE"
    [ -n "$CLAUDE_DEBUG" ] && echo "[HOOK] Using HyDE strategy for short query ($query_words words)" >&2
  fi

  # Check for pronouns and context-dependent references
  if echo "$user_query" | grep -qiE "\b(it|that|which|this|them|their|there|the same|the one|as mentioned|as discussed)\b"; then
    rag_strategy="QueryTransform"
    [ -n "$CLAUDE_DEBUG" ] && echo "[HOOK] Using QueryTransform strategy (detected references/pronouns)" >&2
  fi

  [ -n "$CLAUDE_DEBUG" ] && echo "[HOOK] RAG Strategy: $rag_strategy" >&2
fi

# ============================================================
# STEP 2: Auto-Inject Relevant Memories into Context
# ============================================================

context_injection="{}"
context_status="pending"
injected_memories=0
formatted_context=""
injection_confidence=0

# Call Python utility to inject memories
python_cmd="python3"
if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
fi

# Only process if we have a meaningful query
if [ "$user_query" != "[Query extraction pending]" ] && [ -n "$user_query" ]; then
  inject_output=$(PYTHONPATH="/home/user/.work/athena/src:$PYTHONPATH" "$python_cmd" "$(dirname "$0")/lib/inject_context.py" \
    --query "$user_query" \
    --cwd "$cwd" \
    --token-budget 1000 \
    --min-usefulness 0.4 \
    --max-memories 5 \
    --strategy "$rag_strategy" \
    --json 2>/dev/null)

  if echo "$inject_output" | jq empty 2>/dev/null; then
    context_injection="$inject_output"
    context_status=$(echo "$inject_output" | jq -r '.status // "pending"')

    # Extract injection details
    if [ "$context_status" = "success" ]; then
      injected_memories=$(echo "$inject_output" | jq -r '.memory_count // 0')
      formatted_context=$(echo "$inject_output" | jq -r '.formatted_context // ""')
      injection_confidence=$(echo "$inject_output" | jq -r '.injection_confidence // 0')
    fi
  else
    context_status="skipped"
  fi
fi

# ============================================================
# STEP 3: Record Episodic Event - User Interaction
# ============================================================

event_recorded="false"
event_id=""

# ============================================================
# STEP 3A: Attempt to Extract Task/Phase Context
# ============================================================
# Try to get current active task and phase from memory
context_task=""
context_phase=""

if [ -f "$python_cmd" ] || command -v "$python_cmd" &> /dev/null; then
  # Try to get active task from memory system
  task_context=$("$python_cmd" << 'PYTHON_EOF' 2>/dev/null
import sys
import json
try:
    sys.path.insert(0, str(__import__('pathlib').Path.home() / '.work/claude/memory-mcp/src'))
    from memory_mcp.core.database import Database
    from pathlib import Path

    db_path = Path.home() / '.memory-mcp/memory.db'
    if db_path.exists():
        db = Database(str(db_path))
        cursor = db.conn.cursor()

        # Get most recent task context
        cursor.execute("""
            SELECT context_task, context_phase FROM episodic_events
            WHERE context_task IS NOT NULL
            ORDER BY timestamp DESC LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            print(json.dumps({"task": row[0], "phase": row[1]}))
except:
    pass
PYTHON_EOF
)

  if [ -n "$task_context" ]; then
    context_task=$(echo "$task_context" | jq -r '.task // ""' 2>/dev/null)
    context_phase=$(echo "$task_context" | jq -r '.phase // ""' 2>/dev/null)
  fi
fi

# ============================================================
# STEP 3: Record Episodic Event - User Interaction
# ============================================================

record_output=$(PYTHONPATH="/home/user/.work/athena/src:$PYTHONPATH" "$python_cmd" "$(dirname "$0")/lib/record_episode.py" \
  --tool "UserPromptSubmit" \
  --event-type "conversation" \
  --cwd "$cwd" \
  --task "$context_task" \
  --phase "$context_phase" \
  --json 2>/dev/null)

if echo "$record_output" | jq empty 2>/dev/null; then
  event_recorded=$(echo "$record_output" | jq -r '.success // false')
  event_id=$(echo "$record_output" | jq -r '.event_id // ""')
  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] UserPromptSubmit event recorded: id=$event_id success=$event_recorded" >&2
  fi
fi

# ============================================================
# STEP 4: Return Hook Response - With Recovery + Auto-Injected Context
# ============================================================

# Return hook response with recovered context (if recovery detected) or auto-injected memories
# Priority: Recovery context > Normal context injection
# If recovery banner exists, prepend it to formatted context
final_context="$formatted_context"
if [ "$recovery_detected" = "true" ] && [ -n "$recovery_banner" ]; then
  final_context="${recovery_banner}"$'\n\n'"${formatted_context}"
  context_status="success"
  injected_memories=1

  # IMPORTANT: Write recovery banner to stdout so Claude Code displays it
  # This makes the recovery visible to the user
  echo "" >&2  # Empty line to stderr for spacing
  echo "🔄 CONTEXT RECOVERY - Recovered the following context:" >&2
  echo "$recovery_banner" >&2
  echo "" >&2
fi

# Build the hook response JSON carefully to handle complex nested objects
# Important: suppressOutput must be false to allow hook messages to be visible
suppress_output="false"
if [ "$recovery_detected" = "true" ]; then
  # Don't suppress output when recovery is active
  suppress_output="false"
fi

jq -n \
  --arg event_id "$event_id" \
  --arg event_recorded "$event_recorded" \
  --arg formatted_context "$final_context" \
  --argjson injected_memories "$injected_memories" \
  --argjson injection_confidence "$injection_confidence" \
  --arg context_status "$context_status" \
  --argjson recovery_detected "$recovery_detected" \
  --arg suppress_output "$suppress_output" \
  --slurpfile recovered_context <(echo "$recovered_context" | jq -c '.' 2>/dev/null) \
  '{
    "continue": true,
    "suppressOutput": ($suppress_output == "true"),
    "hookSpecificOutput": {
      "hookEventName": "UserPromptSubmit",
      "additionalContext": (if ($formatted_context | length) > 0 then $formatted_context else "" end),
      "status": (if ($recovery_detected and $context_status == "success") then "context_recovered" elif ($context_status == "success") then "context_injected" else "silent" end),
      "timestamp": "'$timestamp'",
      "episodic_event": {
        "recorded": ($event_recorded | test("true")),
        "event_id": $event_id
      },
      "context_injection": {
        "status": $context_status,
        "memories_injected": $injected_memories,
        "confidence": $injection_confidence,
        "formatted_context": (if ($formatted_context | length) > 0 then $formatted_context else "" end)
      },
      "context_recovery": {
        "detected": $recovery_detected,
        "recovered_context": (if $recovered_context | length > 0 then $recovered_context[0] else null end)
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
  log_hook_success "user-prompt-submit" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "user-prompt-submit" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
