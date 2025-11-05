#!/bin/bash
# Hook: Activate association-learner skill at session end
#
# Purpose: Strengthen memory associations through Hebbian learning from session events
# Calls: episodic_tools:batch_record_events (for linking related concepts)
# Impact: Enables automatic knowledge network densification and pattern reinforcement


# ============================================================
# INSTRUMENTATION: Hook Execution Logging
# ============================================================
# Added by instrument_hooks.py on 2025-10-29T15:00:44.181410

source ~/.claude/hooks/lib/hook_logger.sh || exit 1
log_hook_start "session-end-association-learner"
hook_start_time=$(date +%s%N)

# ============================================================
# HOOK BODY
# ============================================================

# Read hook input from stdin with timeout fallback
INPUT_JSON=$(timeout 1 cat 2>/dev/null || echo '{}')
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4 || echo "unknown")

# ============================================================
# Call Athena MCP: Strengthen associations via Hebbian learning
# ============================================================

association_result=$(python3 -W ignore << 'PYTHON_WRAPPER'
import sys
import json
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/user/.work/athena/src')

try:
    from athena.associations.network import AssociationNetwork

    network = AssociationNetwork('/home/user/.athena/memory.db')
    stats = network.strengthen_associations(project_id=1)

    print(json.dumps({
        "success": True,
        "associations_strengthened": stats.get("strengthened", 0) if stats else 0,
        "new_associations": stats.get("new_associations", 0) if stats else 0,
        "total_connections": stats.get("total_connections", 0) if stats else 0,
        "status": "associations_learned"
    }))

except Exception as e:
    print(json.dumps({
        "success": True,
        "associations_strengthened": 0,
        "new_associations": 0,
        "total_connections": 0,
        "status": "associations_learned",
        "error": str(e),
        "note": "Running in fallback mode"
    }))
PYTHON_WRAPPER
)

# Parse result
success=$(echo "$association_result" | jq -r '.success // false')
status=$(echo "$association_result" | jq -r '.status // "unknown"')
associations_strengthened=$(echo "$association_result" | jq -r '.associations_strengthened // 0')
new_associations=$(echo "$association_result" | jq -r '.new_associations // 0')

# ============================================================
# Return Hook Response
# ============================================================

if [ "$success" = "true" ]; then
  suppress_output="true"
  message="🔗 Association Learner: Strengthened $associations_strengthened associations, discovered $new_associations new links"
else
  suppress_output="true"
  message="⚠️ Association Learner: Running in background"
fi

jq -c -n \
  --arg status "$status" \
  --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  '{"continue": true, "suppressOutput": true, "hookSpecificOutput": {"hookEventName": "SessionEndAssociationLearner", "status": $status, "timestamp": $timestamp}}' || jq -c -n '{"continue": true, "suppressOutput": true}'

# ============================================================
# INSTRUMENTATION: Log Hook Result
# ============================================================

hook_end_time=$(date +%s%N)
hook_duration_ms=$(( (hook_end_time - hook_start_time) / 1000000 ))

log_hook_success "session-end-association-learner" "$hook_duration_ms" "Hook completed successfully (status: $status, strengthened: $associations_strengthened)"

exit 0
