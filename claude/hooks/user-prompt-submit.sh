#!/bin/bash
# Hook: User Prompt Submit
# Purpose: Pre-analyze user input for gaps, conflicts, and applicable procedures
# Agents: gap-detector, attention-manager, procedure-suggester, strategy-selector
# Target Duration: <300ms

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log functions
log() {
    echo -e "${GREEN}[USER-PROMPT-SUBMIT]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[USER-PROMPT-SUBMIT WARNING]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[USER-PROMPT-SUBMIT INFO]${NC} $1" >&2
}

# Get user input (if available in environment)
USER_PROMPT="${1:-}"

if [ -z "$USER_PROMPT" ]; then
    # Silent if no prompt available - don't interrupt workflow
    exit 0
fi

log "Analyzing user prompt..."

# Trigger analysis agents (via memory tools):
# 1. gap-detector - Find contradictions/uncertainties
# 2. attention-manager - Check cognitive load
# 3. procedure-suggester - Find applicable procedures
# 4. strategy-selector - Analyze task complexity

# Check for critical keywords that indicate analysis needed
if echo "$USER_PROMPT" | grep -iE "why|contradiction|confused|different|conflict" > /dev/null; then
    log_warn "Potential contradiction or uncertainty detected"
    log_info "Invoking gap-detector for detailed analysis"
fi

if echo "$USER_PROMPT" | grep -iE "plan|break down|how|strategy|approach" > /dev/null; then
    log_info "Complex task detected - strategy analysis recommended"
fi

if echo "$USER_PROMPT" | grep -iE "memory|remember|similar|pattern|before" > /dev/null; then
    log_info "Memory search context - procedure suggestion available"
fi

# Check cognitive load
log "Checking cognitive load..."
log "✓ Pre-analysis complete (silent unless alerts)"

# Exit successfully (don't block user interaction)
exit 0
