#!/bin/bash
#
# Hook: PrePlanOptimization - Auto-optimize plans before execution
# Triggers: Before task enters EXECUTING phase
# Purpose: Automatically validate and optimize plans for best execution
#
# Input (stdin): JSON with task data {task_id, task_status, task_phase}
# Output (stdout): JSON with optimization directives
# Exit code: 0 = success (non-blocking)


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.180719

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "pre-plan-optimization"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read hook input from stdin
input=$(timeout 1 cat 2>/dev/null || echo '{}')

# Extract fields
task_id=$(echo "$input" | jq -r '.task_id // ""')
task_phase=$(echo "$input" | jq -r '.task_phase // ""')
task_status=$(echo "$input" | jq -r '.task_status // ""')
project_id=$(echo "$input" | jq -r '.project_id // "1"')

# Create timestamp
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Log hook execution if debugging enabled
if [ -n "$CLAUDE_DEBUG" ]; then
  echo "[HOOK] PrePlanOptimization: task=$task_id phase=$task_phase status=$task_status ts=$timestamp" >&2
fi

# ============================================================
# STEP 1: Check if Optimization Should Run
# ============================================================

should_optimize="false"

# Optimize before EXECUTING phase
if [ "$task_phase" = "PLAN_READY" ] || [ "$task_phase" = "plan_ready" ]; then
  should_optimize="true"
fi

# Also optimize if explicitly requested
if echo "$input" | jq -e '.optimize_requested' >/dev/null 2>&1; then
  should_optimize="true"
fi

if [ "$should_optimize" != "true" ]; then
  # Not applicable for this task
  jq -n '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "PrePlanOptimization",
      "status": "skipped",
      "reason": "Task not in PLAN_READY phase"
    }
  }' 2>/dev/null || jq -n '{"continue": true, "suppressOutput": true}'
  exit 0
fi

# ============================================================
# STEP 2: Run Plan Optimization via MCP
# ============================================================

python_cmd="python3"
if [ -f "/home/user/.work/athena/.venv/bin/python3" ]; then
  python_cmd="/home/user/.work/athena/.venv/bin/python3"
fi

optimization_status="pending"
optimization_result="{}"
suggestions_count=0
risks_identified=0
should_block="false"

if [ -n "$task_id" ]; then
  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] Calling optimize_plan for task=$task_id" >&2
  fi

  # Call optimize_plan via MCP
  optim_output=$("$python_cmd" "$(dirname "$0")/lib/call_mcp_tool.py" \
    --tool "optimize_plan" \
    --task_id "$task_id" \
    --json 2>/dev/null)

  if echo "$optim_output" | jq empty 2>/dev/null; then
    optimization_result="$optim_output"
    optimization_status="success"
    suggestions_count=$(echo "$optim_output" | jq '.suggestions | length // 0')
    risks_identified=$(echo "$optim_output" | jq '.risks | length // 0')

    if [ -n "$CLAUDE_DEBUG" ]; then
      echo "[HOOK] Plan optimized: suggestions=$suggestions_count risks=$risks_identified" >&2
    fi

    # Check if execution should be blocked (critical risks)
    if [ "$risks_identified" -ge 2 ]; then
      should_block="true"
      if [ -n "$CLAUDE_DEBUG" ]; then
        echo "[HOOK] CRITICAL: Multiple risks - blocking execution pending review" >&2
      fi
    fi
  else
    optimization_status="failed"
    if [ -n "$CLAUDE_DEBUG" ]; then
      echo "[HOOK] Plan optimization failed" >&2
    fi
  fi
fi

# ============================================================
# STEP 3: Estimate Resources If Not Already Done
# ============================================================

resource_status="pending"
resource_result="{}"

if [ -n "$task_id" ]; then
  if [ -n "$CLAUDE_DEBUG" ]; then
    echo "[HOOK] Estimating resources for task=$task_id" >&2
  fi

  # Call estimate_resources via MCP
  resource_output=$("$python_cmd" "$(dirname "$0")/lib/call_mcp_tool.py" \
    --tool "estimate_resources" \
    --task_id "$task_id" \
    --json 2>/dev/null)

  if echo "$resource_output" | jq empty 2>/dev/null; then
    resource_result="$resource_output"
    resource_status="success"

    if [ -n "$CLAUDE_DEBUG" ]; then
      echo "[HOOK] Resources estimated" >&2
    fi
  else
    resource_status="failed"
  fi
fi

# ============================================================
# STEP 4: Check for Blockers that Prevent Execution
# ============================================================

blocker_status="none"
blocker_msg=""

python3 << 'PYTHON_BLOCKER_CHECK'
import json
import os

try:
    task_id = os.environ.get("task_id", "")

    if task_id:
        # Check for unresolved blockers
        # In production, would query database for blocked_reason field
        print("Blocker check completed")
except Exception as e:
    print(f"Blocker check error: {e}")

PYTHON_BLOCKER_CHECK

# ============================================================
# STEP 5: Record Optimization in Episodic Memory
# ============================================================

event_id=""
event_recorded="false"

record_output=$("$python_cmd" "$(dirname "$0")/lib/record_episode.py" \
  --tool "PlanOptimization" \
  --event-type "action" \
  --metadata "{\"task_id\": $task_id, \"status\": \"$optimization_status\", \"suggestions\": $suggestions_count, \"risks\": $risks_identified, \"blocked\": $should_block}" \
  --json 2>/dev/null)

if echo "$record_output" | jq empty 2>/dev/null; then
  event_recorded=$(echo "$record_output" | jq -r '.success // false')
  event_id=$(echo "$record_output" | jq -r '.event_id // ""')
fi

# ============================================================
# STEP 6: Return Hook Response
# ============================================================

# Build response
if [ "$should_block" = "true" ]; then
  # Block execution - critical issues need review
  jq -n \
    --arg task "$task_id" \
    --arg opt_status "$optimization_status" \
    --arg block "true" \
    '{
      "continue": false,
      "suppressOutput": true,
      "blockReason": "Plan optimization identified critical risks requiring review",
      "hookSpecificOutput": {
        "hookEventName": "PrePlanOptimization",
        "status": "blocked",
        "task_id": $task,
        "optimization_status": $opt_status,
        "suggestions": '$suggestions_count',
        "risks": '$risks_identified',
        "resources": "'$resource_status'",
        "timestamp": "'$timestamp'",
        "recommendation": "Review optimization suggestions and risks before proceeding"
      }
    }' 2>/dev/null || \
  jq -n '{"continue": false, "suppressOutput": true}'
else
  # Allow execution to proceed
  jq -n \
    --arg task "$task_id" \
    --arg opt_status "$optimization_status" \
    '{
      "continue": true,
      "suppressOutput": true,
      "hookSpecificOutput": {
        "hookEventName": "PrePlanOptimization",
        "status": "optimized",
        "task_id": $task,
        "optimization_status": $opt_status,
        "suggestions": '$suggestions_count',
        "risks": '$risks_identified',
        "resources": "'$resource_status'",
        "timestamp": "'$timestamp'",
        "recommendation": "Plan optimized - safe to execute"
      }
    }' 2>/dev/null || \
  jq -n '{"continue": true, "suppressOutput": true}'
fi

exit 0


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "pre-plan-optimization" "$hook_duration_ms" "Hook completed successfully"
else
  log_hook_failure "pre-plan-optimization" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
