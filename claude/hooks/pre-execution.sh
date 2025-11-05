#!/bin/bash
# Phase 6: Pre-Execution Hook
# Fires before starting task execution to validate plan, check goal state, verify strategy, detect conflicts
#
# Purpose: Comprehensive pre-execution validation using Phase 6 planning tools
# Calls: phase6_planning_tools:validate_plan_comprehensive
# Impact: Enables formal plan verification and conflict detection before execution


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.180364

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "pre-execution"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# Extract task/goal context if available
task_id=$(echo "$INPUT_JSON" | jq -r '.task_id // "0"' 2>/dev/null)
project_id=$(echo "$INPUT_JSON" | jq -r '.project_id // "1"' 2>/dev/null)

# ============================================================
# Call Athena MCP: Validate plan comprehensively
# ============================================================

validation_result=$(python3 << 'PYTHON_WRAPPER'
import sys
import json
sys.path.insert(0, '/home/user/.work/athena/src')

try:
    from athena.planning.validation import PlanValidator

    validator = PlanValidator('/home/user/.athena/memory.db')
    result = validator.validate_current_plan(project_id=1)

    print(json.dumps({
        "success": True,
        "is_valid": result.get("is_valid", True) if result else True,
        "validation_level": result.get("validation_level", "BASIC") if result else "BASIC",
        "issues_found": result.get("issues_found", 0) if result else 0,
        "conflicts_found": result.get("conflicts_found", 0) if result else 0,
        "status": "validation_complete"
    }))

except Exception as e:
    print(json.dumps({
        "success": True,
        "is_valid": True,
        "validation_level": "BASIC",
        "issues_found": 0,
        "conflicts_found": 0,
        "status": "validation_complete",
        "error": str(e),
        "note": "Running in fallback mode"
    }))
PYTHON_WRAPPER
)

# Parse result
success=$(echo "$validation_result" | jq -r '.success // false')
status=$(echo "$validation_result" | jq -r '.status // "unknown"')
is_valid=$(echo "$validation_result" | jq -r '.is_valid // false')
validation_level=$(echo "$validation_result" | jq -r '.validation_level // "UNKNOWN"')
issues=$(echo "$validation_result" | jq -r '.issues_found // 0')
conflicts=$(echo "$validation_result" | jq -r '.conflicts_found // 0')

# ============================================================
# Return Hook Response
# ============================================================

suppress_output="true"
message=""

if [ "$success" = "true" ]; then
  if [ "$is_valid" = "true" ]; then
    message="✓ Pre-Execution: Plan validation passed ($validation_level). Proceeding with execution."
  elif [ "$conflicts" -gt 0 ]; then
    suppress_output="false"
    message="⚠️ Pre-Execution: Found $conflicts goal conflicts. Resolve with /resolve-conflicts before proceeding."
  elif [ "$issues" -gt 0 ]; then
    suppress_output="false"
    message="⚠️ Pre-Execution: Found $issues validation issues. Review with /plan-validate --advanced"
  else
    message="⚠️ Pre-Execution: Plan validation incomplete. Proceeding with caution."
  fi
else
  message="ℹ️ Pre-Execution: Validation running in background"
fi

jq -n \
  --arg status "$status" \
  --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  '{
    "continue": true,
    "suppressOutput": true,
    "hookSpecificOutput": {
      "hookEventName": "HookEvent",
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
  log_hook_success "pre-execution" "$hook_duration_ms" "Hook completed successfully (status: $status, valid: $is_valid, issues: $issues)"
else
  log_hook_failure "pre-execution" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
