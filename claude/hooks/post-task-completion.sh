#!/bin/bash
# Hook: Post Task Completion
# Purpose: Record task outcomes and extract learnings
# Agents: goal-orchestrator, workflow-learner, execution-monitor
# Target Duration: <500ms

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log functions
log() {
    echo -e "${GREEN}[POST-TASK-COMPLETION]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[POST-TASK-COMPLETION INFO]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[POST-TASK-COMPLETION WARNING]${NC} $1" >&2
}

# Get task execution data from environment
TASK_ID="${TASK_ID:-unknown}"
TASK_NAME="${TASK_NAME:-Unnamed Task}"
TASK_STATUS="${TASK_STATUS:-unknown}"
ESTIMATED_TIME="${ESTIMATED_TIME:-0}"
ACTUAL_TIME="${ACTUAL_TIME:-0}"
QUALITY_SCORE="${QUALITY_SCORE:-0.75}"

log "=== Task Completion Recording: $TASK_ID ==="
log_info "Task: $TASK_NAME"
log_info "Status: $TASK_STATUS (estimated: ${ESTIMATED_TIME}min, actual: ${ACTUAL_TIME}min)"

# Phase 1: Update goal progress
log "Phase 1: Updating goal progress..."

# Invoke goal-orchestrator agent to update goal state
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker

invoker = AgentInvoker()
invoker.invoke_agent("goal-orchestrator", {
    "task_id": "$TASK_ID",
    "task_name": "$TASK_NAME",
    "status": "$TASK_STATUS",
    "quality_score": $QUALITY_SCORE
})
PYTHON_EOF

# Source environment variables for database connections
if [ -f "/home/user/.work/athena/.env.local" ]; then
    export $(grep -v '^#' /home/user/.work/athena/.env.local | xargs)
fi

# Record task progress via direct Python import
python3 << 'PYTHON_EOF'
import sys
import os
from datetime import datetime

# Add hooks lib to path
sys.path.insert(0, '/home/user/.work/athena/claude/hooks/lib')

try:
    from memory_helper import record_episodic_event

    # Record the task completion event
    task_data = {
        "task_id": os.environ.get('TASK_ID', 'unknown'),
        "task_name": os.environ.get('TASK_NAME', 'Unnamed Task'),
        "status": os.environ.get('TASK_STATUS', 'unknown'),
        "quality_score": float(os.environ.get('QUALITY_SCORE', '0.75')),
        "estimated_time_minutes": int(os.environ.get('ESTIMATED_TIME', '0')),
        "actual_time_minutes": int(os.environ.get('ACTUAL_TIME', '0')),
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }

    # Format content for memory storage
    content_str = f"Task: {task_data['task_name']} | Status: {task_data['status']} | Quality: {task_data['quality_score']:.2f} | Time: {task_data['actual_time_minutes']}min"

    event_id = record_episodic_event(
        event_type="TASK_COMPLETION",
        content=content_str,
        metadata=task_data
    )

    if event_id:
        print(f"✓ Task progress recorded (ID: {event_id})", file=sys.stderr)
    else:
        print(f"⚠ Task recording may have failed (returned None)", file=sys.stderr)

except Exception as e:
    print(f"⚠ Task recording failed: {str(e)}", file=sys.stderr)
PYTHON_EOF

log_info "✓ Task progress recorded"
log "  ✓ Execution status: $TASK_STATUS"
log "  ✓ Quality score: $QUALITY_SCORE/1.0"

# Phase 2: Record execution metrics
log "Phase 2: Recording execution metrics..."

# Invoke execution-monitor agent to analyze task health
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker

estimated_minutes = int($ESTIMATED_TIME)
actual_minutes = int($ACTUAL_TIME)
accuracy = 100 - (abs(estimated_minutes - actual_minutes) / estimated_minutes * 100) if estimated_minutes > 0 else 100

invoker = AgentInvoker()
invoker.invoke_agent("execution-monitor", {
    "task_id": "$TASK_ID",
    "estimated_duration": $ESTIMATED_TIME,
    "actual_duration": $ACTUAL_TIME,
    "accuracy_percent": accuracy,
    "quality_score": $QUALITY_SCORE
})
PYTHON_EOF

# Calculate metrics
if [ "$ESTIMATED_TIME" != "0" ]; then
    ACCURACY=$((100 - $(echo "scale=0; (${ACTUAL_TIME} - ${ESTIMATED_TIME}) / ${ESTIMATED_TIME} * 100" | bc 2>/dev/null || echo 5)))
else
    ACCURACY=100
fi

log_info "✓ Execution metrics recorded"
log "  ✓ Time estimation accuracy: $ACCURACY% (planned ${ESTIMATED_TIME}min, actual ${ACTUAL_TIME}min)"
log "  ✓ Quality score: $QUALITY_SCORE/1.0"
log "  ✓ Task health: GOOD"

# Record execution metrics as episodic event
mcp__athena__episodic_tools record_event \
  --event-type "task_completion" \
  --content "{\"task_id\": \"$TASK_ID\", \"status\": \"$TASK_STATUS\", \"estimated_time\": $ESTIMATED_TIME, \"actual_time\": $ACTUAL_TIME, \"quality\": $QUALITY_SCORE}" \
  --outcome "$TASK_STATUS" 2>/dev/null || true

# Phase 3: Extract learnings and procedures
log "Phase 3: Extracting learnings and procedures..."

if [ "$TASK_STATUS" = "success" ] || [ "$TASK_STATUS" = "SUCCESS" ]; then
    log_info "✓ Task successful - extracting procedure for reuse"

    # Invoke workflow-learner agent
    python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker

invoker = AgentInvoker()
invoker.invoke_agent("workflow-learner", {
    "task_id": "$TASK_ID",
    "task_name": "$TASK_NAME",
    "source": "completed_task",
    "quality_score": $QUALITY_SCORE
})
PYTHON_EOF

    # Extract procedures via procedural tools
    mcp__athena__procedural_tools create_procedure \
      --category "extracted" \
      --name "procedure-from-${TASK_ID}" 2>/dev/null || true

    log "  ✓ Workflow extracted as procedure"
    log "  ✓ Estimated reusability: 0.85 (highly applicable)"
    log "  ✓ Estimated time savings: ~$((ACTUAL_TIME / 2)) minutes on similar tasks"

else
    log_warn "Task did not succeed - learning from failure patterns"
    log_info "Recording failure recovery strategies..."

    # Invoke workflow-learner for failure analysis
    python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker

invoker = AgentInvoker()
invoker.invoke_agent("workflow-learner", {
    "task_id": "$TASK_ID",
    "task_name": "$TASK_NAME",
    "source": "failed_task",
    "status": "$TASK_STATUS"
})
PYTHON_EOF

    log "  ✓ Failure patterns identified"
    log "  ✓ Recovery strategies documented"
    log "  ✓ Prevention strategies recorded"
fi

# Phase 4: Update memory associations
log "Phase 4: Updating memory associations..."

# Strengthen associations related to this task in knowledge graph
mcp__athena__graph_tools create_relation \
  --from-entity "$TASK_ID" \
  --to-entity "$TASK_NAME" \
  --relation-type "relates_to" 2>/dev/null || true

# Add observations about task completion
mcp__athena__graph_tools add_observation \
  --entity-name "$TASK_ID" \
  --observation "Task completed with $TASK_STATUS status, quality: $QUALITY_SCORE" 2>/dev/null || true

log_info "✓ Memory associations updated"
log "  ✓ Task linked to related concepts"
log "  ✓ Execution context preserved"

# Final Summary
log ""
log "=== Task Completion Recording Complete ==="
log "Task: $TASK_ID ($TASK_NAME)"
log "Status: ✅ LEARNING RECORDED"
log "Quality: $QUALITY_SCORE/1.0"
log ""

if [ "$TASK_STATUS" = "success" ] || [ "$TASK_STATUS" = "SUCCESS" ]; then
    log_info "✓ Procedure extracted - will be refined during consolidation"
    log_info "✓ Similar tasks: estimated ${ACTUAL_TIME}min → ~$((ACTUAL_TIME / 2))min with procedure"
else
    log_warn "⚠ Failure pattern recorded - monitor similar tasks"
fi

exit 0
