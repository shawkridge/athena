#!/bin/bash

################################################################################
# Athena Nightly Dream Generation and Evaluation
#
# This script:
# 1. Runs consolidation + dream generation at night
# 2. Detects pending dreams
# 3. Spawns a fresh Claude instance for evaluation
# 4. Logs all activities
#
# Setup: Add to crontab for nightly execution
#   0 2 * * * /usr/local/bin/run_athena_dreams.sh
################################################################################

set -e  # Exit on error

# Configuration
LOG_FILE="${ATHENA_LOG_FILE:-/var/log/athena-dreams.log}"
DREAM_DIR="${ATHENA_HOME:-/home/user/.work/athena}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONSOLIDATION_SCRIPT="$DREAM_DIR/scripts/run_consolidation_with_dreams.py"
STRATEGY="${DREAM_STRATEGY:-balanced}"
MAX_WAIT_FOR_EVALUATION=300  # 5 minutes max to wait for Claude

################################################################################
# Utility Functions
################################################################################

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2
}

cleanup() {
    if [ $? -ne 0 ]; then
        error "Dream cycle failed"
    fi
}

trap cleanup EXIT

################################################################################
# Main Execution
################################################################################

log "========================================================================"
log "ATHENA NIGHTLY DREAM CYCLE STARTING"
log "========================================================================"
log "Working directory: $DREAM_DIR"
log "Strategy: $STRATEGY"
log "Log file: $LOG_FILE"

# Step 1: Verify prerequisites
log ""
log "Step 1: Verifying prerequisites..."

if [ ! -f "$CONSOLIDATION_SCRIPT" ]; then
    error "Consolidation script not found: $CONSOLIDATION_SCRIPT"
    exit 1
fi

if ! command -v "$PYTHON_BIN" &> /dev/null; then
    error "Python not found: $PYTHON_BIN"
    exit 1
fi

if ! command -v claude &> /dev/null; then
    error "Claude CLI not found. Install with: pip install --upgrade claude-cli"
    exit 1
fi

log "✓ Prerequisites verified"

# Step 2: Run consolidation with dreams
log ""
log "Step 2: Running consolidation with dream generation..."

cd "$DREAM_DIR"

if "$PYTHON_BIN" "$CONSOLIDATION_SCRIPT" --strategy "$STRATEGY" >> "$LOG_FILE" 2>&1; then
    log "✓ Consolidation completed successfully"
else
    error "Consolidation failed (see log for details)"
    exit 1
fi

# Step 3: Count pending dreams
log ""
log "Step 3: Counting pending dreams..."

DREAM_COUNT=$("$PYTHON_BIN" << 'PYEOF'
import sys
sys.path.insert(0, 'src')
try:
    from athena.core.database import Database
    from athena.consolidation.dream_store import DreamStore

    db = Database()
    store = DreamStore(db)

    # Count pending dreams
    import asyncio
    pending = asyncio.run(store.get_pending_evaluation(limit=1000))
    print(len(pending))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    print(0)
PYEOF
)

if [ -z "$DREAM_COUNT" ] || [ "$DREAM_COUNT" = "0" ]; then
    DREAM_COUNT=0
    log "No dreams generated in this cycle"
else
    log "✓ Pending dreams: $DREAM_COUNT"
fi

# Step 4: Spawn Claude instance for evaluation (if dreams exist)
if [ "$DREAM_COUNT" -gt 0 ]; then
    log ""
    log "Step 4: Spawning Claude evaluation instance..."
    log "  (Claude will evaluate $DREAM_COUNT dreams)"

    # Build evaluation prompt
    EVAL_PROMPT=$(cat << EOF
=== ATHENA DREAM EVALUATION ===

I just completed a nightly consolidation cycle with dream generation enabled.

Generated: $DREAM_COUNT speculative procedure variants
- Using DeepSeek V3.1 for constraint relaxation & semantic matching
- Using Qwen2.5-Coder 32B for cross-project synthesis
- Using local models for parameter exploration & conditionals

Task: Please evaluate these dream procedures for viability.

For each dream:
1. Assess viability (0.0-1.0 score, where 1.0 = definitely viable)
2. Assign tier:
   - Tier 1 (0.6-1.0): Viable, ready to test
   - Tier 2 (0.3-0.6): Speculative, interesting but risky
   - Tier 3 (0.0-0.3): Archive, creative but not currently viable
3. Explain your reasoning briefly

Use /dream_journal to see the pending dreams.
Then provide your evaluations in this format:

Dream 1: Viability 0.8, Tier 1. [reasoning]
Dream 2: Viability 0.4, Tier 2. [reasoning]
...

The system will learn from your evaluations and improve over time.
EOF
)

    # Spawn Claude with evaluation prompt
    # Using timeout to prevent hanging
    if timeout $MAX_WAIT_FOR_EVALUATION claude << EOF >> "$LOG_FILE" 2>&1; then
        log "✓ Claude evaluation completed"
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 124 ]; then
            error "Claude evaluation timed out after ${MAX_WAIT_FOR_EVALUATION}s"
        else
            error "Claude evaluation failed with exit code $EXIT_CODE"
        fi
        # Don't exit - dreams remain pending for next cycle
    fi

else
    log ""
    log "Step 4: No dreams to evaluate (skipped)"
fi

# Step 5: Final summary
log ""
log "========================================================================"
log "ATHENA DREAM CYCLE COMPLETE"
log "========================================================================"
log "Status: SUCCESS"
log "Dreams generated: $DREAM_COUNT"
log "Time: $(date +'%Y-%m-%d %H:%M:%S')"
log "========================================================================"

exit 0
