#!/bin/bash
#
# Hook: PostWorkTool - Track File/Code Tool Executions
# Triggers: After Read, Edit, Write, Bash, Glob, Grep tools complete
# Purpose: Track file changes and work activity for episodic memory
#
# Input (stdin): JSON with hook event data {tool_name, tool_input, cwd}
# Output (stdout): JSON with episodic recording directives
# Exit code: 0 = success (non-blocking)


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.179591

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "post-work-tool"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read hook input from stdin
input=$(timeout 1 cat 2>/dev/null || echo '{}')

# Extract fields
tool_name=$(echo "$input" | jq -r '.tool_name // "unknown"')
cwd=$(echo "$input" | jq -r '.cwd // "."')

# Create timestamp
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log execution if debugging
if [ -n "$CLAUDE_DEBUG" ]; then
  echo "[HOOK] PostWorkTool: tool=$tool_name cwd=$cwd ts=$timestamp" >&2
fi

# ============================================================
# STEP 1: Classify Tool & Activity Type
# ============================================================

event_type=""
activity_desc=""

case "$tool_name" in
  "Edit")
    event_type="file_change"
    activity_desc="Code modification (Edit)"
    ;;
  "Write")
    event_type="file_change"
    activity_desc="File creation/overwrite (Write)"
    ;;
  "Read")
    event_type="action"
    activity_desc="File inspection (Read)"
    ;;
  "Bash")
    event_type="action"
    activity_desc="Command execution (Bash)"
    ;;
  "Glob"|"Grep")
    event_type="action"
    activity_desc="Code search ($tool_name)"
    ;;
  *)
    event_type="action"
    activity_desc="Tool execution"
    ;;
esac

# ============================================================
# STEP 2: Record Episodic Event
# ============================================================

recording_result="{}"
recording_status="pending"
event_id=""

# Call Python utility to record the episodic event
python_cmd="python3"
if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
fi

# Extract files from input if available
files_str=""
files_array=()
if [ -n "$(echo "$input" | jq -r '.file_paths // empty')" ]; then
  files_str="$(echo "$input" | jq -r '.file_paths[]' | tr '\n' ' ')"
  mapfile -t files_array < <(echo "$input" | jq -r '.file_paths[]')
fi

record_output=$("$python_cmd" "$(dirname "$0")/lib/record_episode.py" \
  --tool "$tool_name" \
  --event-type "$event_type" \
  --cwd "$cwd" \
  $([[ -n "$files_str" ]] && echo "--files $files_str") \
  --json 2>/dev/null)

if echo "$record_output" | jq empty 2>/dev/null; then
  recording_result="$record_output"
  recording_status="success"
  event_id=$(echo "$record_output" | jq -r '.event_id // ""')
else
  recording_status="skipped"
fi

# ============================================================
# STEP 3: Map Files to Tasks and Update Task Status
# ============================================================
# NEW: Automatically detect which tasks are affected by file changes

if [ "$tool_name" = "Edit" ] || [ "$tool_name" = "Write" ]; then
  # File modification - map to tasks and update status

  python3 << 'PYTHON_TASK_BLOCK'
import sys
import os
from pathlib import Path

# Add hooks lib to path
sys.path.insert(0, str(Path.home() / ".claude" / "hooks" / "lib"))

try:
    from task_manager import TaskManager
except ImportError:
    sys.exit(0)  # Silent fail if task_manager not available

tm = TaskManager()

# Get files from environment
files_env = os.environ.get("FILES_ENV", "")
files = [f for f in files_env.split() if f]

if not files:
    sys.exit(0)

# For each file, find task and update status
tasks_updated = set()
for file_path in files:
    # Normalize path (remove leading ./)
    file_path = file_path.lstrip('./')

    task = tm.find_task_by_file(file_path)

    if task and task not in tasks_updated:
        # Update task to in_progress
        tm.update_task_status(
            task,
            "in_progress",
            f"File changed: {file_path}"
        )
        tm.record_task_event(
            task,
            "file_change",
            f"Modified {file_path}",
            "success"
        )
        tasks_updated.add(task)

if tasks_updated:
    print(f"Updated {len(tasks_updated)} tasks")

PYTHON_TASK_BLOCK

fi

# ============================================================
# STEP 4: Phase 5-8 - Task Completion Analytics
# ============================================================
# NEW: Record health metrics when tasks complete

# Extract task_id from input if present (for completion tracking)
task_id=$(echo "$input" | jq -r '.task_id // ""')
task_status=$(echo "$input" | jq -r '.task_status // ""')

if [ -n "$task_id" ] && [ "$task_status" = "completed" ]; then
  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] Phase 5-8: Recording completion analytics for task=$task_id" >&2
  fi

  # Get final health metrics for completed task
  health_output=$("$python_cmd" "$(dirname "$0")/lib/call_mcp_tool.py" \
    --tool "get_task_health" \
    --task_id "$task_id" \
    --json 2>/dev/null)

  if echo "$health_output" | jq empty 2>/dev/null; then
    if [ -n "$CLAUDE_DEBUG" ]; then
      final_score=$(echo "$health_output" | jq -r '.health_score // 0')
      echo "[HOOK] Final health for task $task_id: score=$final_score" >&2
    fi
  fi

  # Trigger pattern discovery if >10 completed tasks
  project_id="${PROJECT_ID:-}"
  if [ -z "$project_id" ] && [ -n "$(echo "$input" | jq -r '.project_id // ""')" ]; then
    project_id=$(echo "$input" | jq -r '.project_id')
  fi

  if [ -n "$project_id" ]; then
    # Check if we should run pattern discovery (after 10+ completions)
    patterns_output=$("$python_cmd" "$(dirname "$0")/lib/call_mcp_tool.py" \
      --tool "discover_patterns" \
      --project_id "$project_id" \
      --json 2>/dev/null)

    if echo "$patterns_output" | jq empty 2>/dev/null; then
      if [ -n "$CLAUDE_DEBUG" ]; then
        echo "[HOOK] Task patterns re-discovered" >&2
      fi
    fi
  fi
fi

# ============================================================
# STEP 5: Return Hook Response - Silent Mode (No User-Facing Output)
# ============================================================

# Return minimal JSON response - no system message for user visibility
# Events are recorded but output is suppressed for token efficiency
jq -n \
  --arg tool "$tool_name" \
  --arg event_type_val "$event_type" \
  --arg event_id_str "$event_id" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "PostToolUse",
      "status": "silent",
      "tool": $tool,
      "eventType": $event_type_val,
      "timestamp": "'$timestamp'",
      "episodic_recording": {
        "status": "'$recording_status'",
        "event_id": $event_id_str
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
  log_hook_success "post-work-tool" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "post-work-tool" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
