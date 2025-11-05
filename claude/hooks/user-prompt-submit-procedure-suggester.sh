#!/bin/bash
# Hook: Activate procedure-suggester skill on user prompt
#
# Purpose: Find and suggest applicable reusable workflows based on user context
# Calls: procedural_tools:find_procedures
# Impact: Enables automatic procedure discovery and reuse


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.183349

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "user-prompt-submit-procedure-suggester"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')

# ============================================================
# Call Athena MCP: Find applicable procedures
# ============================================================

procedure_result=$(python3 << 'PYTHON_WRAPPER'
import sys
import json
sys.path.insert(0, '/home/user/.work/athena/src')

from athena.procedural.pattern_suggester import PatternSuggester

suggester = PatternSuggester('/home/user/.athena/memory.db')
procedures = suggester.find_matching_patterns(context="user_prompt", limit=5)

procedures_found = len(procedures)
avg_effectiveness = sum(p.get('effectiveness', 0) for p in procedures) / max(procedures_found, 1)

print(json.dumps({
    "success": True,
    "procedures_found": procedures_found,
    "avg_effectiveness": round(avg_effectiveness, 2),
    "status": "procedures_found" if procedures_found > 0 else "no_procedures_found"
}))
PYTHON_WRAPPER
)

# Parse result - fail if invalid JSON
echo "$procedure_result" | jq empty || exit 1

success=$(echo "$procedure_result" | jq -r '.success')
status=$(echo "$procedure_result" | jq -r '.status')
procedures_found=$(echo "$procedure_result" | jq -r '.procedures_found')
effectiveness=$(echo "$procedure_result" | jq -r '.avg_effectiveness')

# ============================================================
# Return Hook Response
# ============================================================

if [ "$success" = "true" ] && [ "$procedures_found" -gt 0 ]; then
  suppress_output="false"
  message="💡 Procedure Suggester: Found $procedures_found applicable workflows (avg effectiveness: $effectiveness)"
elif [ "$success" = "true" ]; then
  suppress_output="true"
  message="💡 Procedure Suggester: No matching procedures for current context"
else
  suppress_output="true"
  message="⚠️ Procedure Suggester: Running in background"
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
  log_hook_success "user-prompt-submit-procedure-suggester" "$hook_duration_ms" "Hook completed successfully (status: $status, procedures: $procedures_found)"
else
  log_hook_failure "user-prompt-submit-procedure-suggester" "$hook_duration_ms" "Hook exited with error"
fi

exit 0
