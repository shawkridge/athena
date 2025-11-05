#!/bin/bash
#
# Hook: SessionEnd - Minimal JSON Response (No-Fail Design)
# Purpose: Record session end and always output valid JSON
#
# Input (stdin): JSON with hook event data {cwd, session_id, reason}
# Output (stdout): Valid JSON response
# Exit code: Always 0
#


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.181945

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "session-end"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read hook input
input=$(timeout 1 cat 2>/dev/null || echo '{}')

# Extract fields (best effort, no error if missing)
cwd=$(echo "$input" | jq -r '.cwd // "."' 2>/dev/null || echo ".")
session_id=$(echo "$input" | jq -r '.session_id // "unknown"' 2>/dev/null || echo "unknown")

# Redirect all errors to null - nothing goes to stdout except the final JSON
{
  # Record episodic event (non-critical)
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
  if [ ! -f "$python_cmd" ]; then
    python_cmd="python3"
  fi

  # Silent event recording
  "$python_cmd" ~/.claude/hooks/lib/record_episode.py \
    --tool "SessionEnd" \
    --event-type "action" \
    --cwd "$cwd" \
    --json > /dev/null 2>&1

  # Silent consolidation
  "$python_cmd" ~/.claude/hooks/lib/auto_consolidate.py \
    --session-id "$session_id" \
    --session-duration 60 \
    --json > /dev/null 2>&1

} 2>/dev/null

# Output valid JSON - GUARANTEED, no matter what
cat << 'JSON'
{"continue": true, "suppressOutput": true}
JSON

exit 0


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "session-end" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "session-end" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
