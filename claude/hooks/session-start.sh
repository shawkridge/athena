#!/bin/bash
#
# Hook: SessionStart - Load Full Project Context
# Triggers: When Claude Code starts a new session or resumes existing one
# Purpose: Automatically load project goals, tasks, and context from MCP memory
#
# Input (stdin): JSON with hook event data {cwd, session_id, source}
# Output (stdout): JSON with system message + context queries
# Exit code: 0 = success (non-blocking)


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.182529

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "session-start"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read hook input from stdin
input=$(cat)

# Extract fields
cwd=$(echo "$input" | jq -r '.cwd // "."')
session_id=$(echo "$input" | jq -r '.session_id // "unknown"')
source=$(echo "$input" | jq -r '.source // "startup"')

# Create timestamp
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log execution if debugging
if [ -n "$CLAUDE_DEBUG" ]; then
  echo "[HOOK] SessionStart: source=$source cwd=$cwd session=$session_id" >&2
fi

# ============================================================
# STEP 1: Detect Project from Working Directory
# ============================================================

project_name=""
project_marker=""

# Check for project markers in order of specificity
if [ -f "$cwd/CLAUDE.md" ]; then
  project_name=$(basename "$cwd")
  project_marker="CLAUDE.md"
elif [ -d "$cwd/.git" ]; then
  project_name=$(basename "$cwd")
  project_marker="git repository"
elif [ -f "$cwd/.claude/settings.json" ]; then
  project_name=$(basename "$cwd")
  project_marker=".claude/settings.json"
else
  project_name="unknown"
  project_marker="no project markers found"
fi

# ============================================================
# STEP 2: Load Real Context from MCP
# ============================================================

context_json="{}"
system_msg=""
context_available="false"

if [ "$project_name" != "unknown" ]; then
  # Call Python utility to load actual context from MCP
  # Use the memory-mcp venv if available, otherwise system python
  python_cmd="python3"
  if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
    python_cmd="/home/user/.work/athena/.venv/bin/python3"
  fi

  # Get JSON output only
  context_json=$("$python_cmd" "$(dirname "$0")/lib/context_loader.py" \
    --project "$project_name" \
    --cwd "$cwd" \
    --json 2>/dev/null)

  # Check if we got valid JSON
  if echo "$context_json" | jq empty 2>/dev/null; then
    context_available="true"
    # Build user-friendly message from context
    success=$(echo "$context_json" | jq -r '.success')
    if [ "$success" = "true" ]; then
      system_msg="✅ Project context loaded from MCP memory

Project: $project_name
Cognitive Load: $(echo "$context_json" | jq -r '.cognitive_load.level // "unknown"' | tr '[:lower:]' '[:upper:]')
$(echo "$context_json" | jq -r '.cognitive_load.recommendation // ""')"
    else
      system_msg="⚠️  Project context partially loaded (some errors occurred)"
    fi
  else
    # Python failed or returned invalid JSON
    system_msg="Could not load context from MCP memory. Context loading failed."
    if [ -n "$CLAUDE_DEBUG" ]; then
      echo "[HOOK] Context load failed: $context_json" >&2
    fi
  fi
else
  system_msg="No project detected in current directory. Unable to load context."
fi

# ============================================================
# STEP 3: Record Episodic Event - Session Started
# ============================================================

event_recorded="false"
event_id=""

python_cmd="python3"
if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
fi

# Record session start event
record_output=$("$python_cmd" "$(dirname "$0")/lib/record_episode.py" \
  --tool "SessionStart" \
  --event-type "action" \
  --cwd "$cwd" \
  --json 2>/dev/null)

if echo "$record_output" | jq empty 2>/dev/null; then
  event_recorded=$(echo "$record_output" | jq -r '.success // false')
  event_id=$(echo "$record_output" | jq -r '.event_id // ""')
  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] SessionStart event recorded: id=$event_id success=$event_recorded" >&2
  fi
fi

# ============================================================
# STEP 4: Determine Context Status
# ============================================================

if [ "$context_available" = "true" ]; then
  context_status="success"
  action_msg="Full context loaded from MCP memory"
else
  context_status="partial"
  action_msg="Project detected but context loading unavailable"
  # Fallback: suggest memory queries
  system_msg="${system_msg}

FALLBACK: Load context manually by running:
1. /memory-query \"active goal for $project_name\"
2. /memory-query \"in_progress tasks for $project_name\"
3. /memory-query \"recent blockers and decisions\""
fi

# ============================================================
# STEP 5: Return Hook Response - Show context if available
# ============================================================

# Show context message if context was successfully loaded
suppress_output="true"
hook_output_message=""

if [ "$context_available" = "true" ] && [ -n "$system_msg" ]; then
  suppress_output="false"
  hook_output_message="$system_msg"
fi

jq -n 2>/dev/null \
  --arg project "$project_name" \
  --arg session "$session_id" \
  --arg event_id "$event_id" \
  --arg event_recorded "$event_recorded" \
  --arg suppress "$suppress_output" \
  --arg msg "$hook_output_message" \
  '{
    "continue": true,
    "suppressOutput": ($suppress | test("true")),
    "userMessage": $msg,
    "hookSpecificOutput": {
      "hookEventName": "SessionStart",
      "status": "context_loaded",
      "project": $project,
      "session_id": $session,
      "timestamp": "'$timestamp'",
      "episodic_event": {
        "recorded": ($event_recorded | test("true")),
        "event_id": $event_id
      }
    }
  }' 2>/dev/null || \
# Fallback if jq fails
jq -n '{
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
  log_hook_success "session-start" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "session-start" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
