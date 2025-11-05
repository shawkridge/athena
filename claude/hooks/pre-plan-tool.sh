#!/bin/bash
#
# Hook: PreToolUse - Validate Goals and Plans Before Creation
# Triggers: Before set_goal, create_task, validate_plan tools execute
# Purpose: Lightweight validation before goal/task creation
#
# Input (stdin): JSON with hook event data
# Output (stdout): JSON response with continue flag
# Exit code: 0 = success (non-blocking)


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.181082

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "pre-plan-tool"
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

# Log hook execution if debugging enabled
if [ -n "$CLAUDE_DEBUG" ]; then
  echo "[HOOK] PrePlanTool: tool=$tool_name ts=$timestamp" >&2
fi

# Extract tool input
tool_input=$(echo "$input" | jq -r '.tool_input // "{}"')
cwd=$(echo "$input" | jq -r '.cwd // "."')

# Only process plan-related tools
if [[ "$tool_name" != "set_goal" ]] && [[ "$tool_name" != "create_task" ]] && [[ "$tool_name" != "validate_plan" ]]; then
  # Not a plan tool, skip
  jq -n '{
    "continue": true,
    "suppressOutput": false
  }'
  exit 0
fi

# ============================================================
# STEP 2: Validate Plan Element
# ============================================================

validation_result="{}"
validation_status="pending"
is_valid="true"

# Call Python utility to validate
python_cmd="python3"
if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
fi

# Extract content from tool input
content=$(echo "$tool_input" | jq -r '.content // .goal_text // .goal // ""')

if [ -n "$content" ]; then
  validate_output=$("$python_cmd" "$(dirname "$0")/lib/validate_plan.py" \
    --tool "$tool_name" \
    --content "$content" \
    --json 2>/dev/null)

  if echo "$validate_output" | jq empty 2>/dev/null; then
    validation_result="$validate_output"
    validation_status="success"
    is_valid=$(echo "$validate_output" | jq -r '.valid // true')
  else
    validation_status="skipped"
  fi
fi

# ============================================================
# STEP 3: Build Validation Message
# ============================================================

validation_msg=$(cat <<EOF
✓ Plan Element Pre-Validated

Tool: $tool_name
Validation Status: $validation_status
Valid: $is_valid
Timestamp: $timestamp

📋 Validation Checks:
- Duplicate detection
- Conflict checking
- Structure validation
- Task load assessment

Next: Plan tool will execute with pre-validation complete
EOF
)

# ============================================================
# STEP 4: Return Validation Results
# ============================================================

jq -n \
  --arg tool "$tool_name" \
  --arg validation_msg "$validation_msg" \
  --arg is_valid_str "$is_valid" \
  --argjson validation_data "$validation_result" \
  '{
    "continue": true,
    "suppressOutput": false,
    "systemMessage": $validation_msg,
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "tool": $tool,
      "status": "pre_validated",
      "validation_status": "'$validation_status'",
      "valid": ($is_valid_str == "true"),
      "timestamp": "'$timestamp'",
      "validation_result": $validation_data
    }
  }' 2>/dev/null || jq -n '{
    "continue": true,
    "suppressOutput": false
  }'

exit 0


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "pre-plan-tool" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "pre-plan-tool" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
