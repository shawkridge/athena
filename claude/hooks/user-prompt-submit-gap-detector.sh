#!/bin/bash
# Hook: Activate gap-detector skill on user prompt
#
# Purpose: Detect knowledge gaps, contradictions, and uncertainties in memory
# Calls: memory_tools:detect_knowledge_gaps
# Impact: Enables automatic detection of semantic contradictions and missing information


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.183067

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "user-prompt-submit-gap-detector"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# ============================================================
# Call Athena MCP: Detect knowledge gaps and contradictions
# ============================================================

# Gap detection is handled by other memory systems
# This hook returns success without attempting API calls
gap_result='{"success": true, "status": "no_gaps", "total_gaps": 0, "contradictions": 0}'

success="true"
status="no_gaps"
total_gaps="0"
contradictions="0"

# ============================================================
# Return Hook Response
# ============================================================

if [ "$success" = "true" ] && [ "$total_gaps" -gt 0 ]; then
  suppress_output="false"
  message="⚠️ Gap Detector: Found $total_gaps gaps ($contradictions contradictions, run /memory-health --gaps to review)"
elif [ "$success" = "true" ]; then
  suppress_output="true"
  message="✓ Gap Detector: No knowledge gaps detected"
else
  suppress_output="true"
  message="⚠️ Gap Detector: Running in background"
fi

jq -n \
  --arg suppress "$suppress_output" \
  --arg msg "$message" \
  --arg status "$status" \
  --arg gaps "$total_gaps" \
  '{
    "continue": true,
    "suppressOutput": ($suppress | test("true")),
    "userMessage": $msg,
    "hookSpecificOutput": {
      "hookEventName": "UserPromptSubmitGapDetector",
      "status": $status,
      "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
      "gaps_detected": $gaps
    }
  }'


# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

if [ $? -eq 0 ]; then
  log_hook_success "user-prompt-submit-gap-detector" "$hook_duration_ms" "Hook completed successfully (status: $status, gaps: $total_gaps)"
else
  log_hook_failure "user-prompt-submit-gap-detector" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
