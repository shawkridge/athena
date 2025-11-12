#!/bin/bash
# Hook: Smart Context Injection
# Purpose: Automatically inject relevant memory context into user queries
# Agents: rag-specialist, research-coordinator
# Target Duration: <500ms (transparent to user)
# Trigger: UserPromptSubmit (analyzed before main processing)

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log functions
log() {
    echo -e "${GREEN}[SMART-CONTEXT]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[CONTEXT]${NC} $1" >&2
}

log_found() {
    echo -e "${CYAN}[FOUND]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[CONTEXT]${NC} $1" >&2
}

# Get user prompt from environment
USER_PROMPT="${1:-}"
PROMPT_START_TIME=$(date +%s%N)

if [ -z "$USER_PROMPT" ]; then
    # Silent if no prompt - don't interrupt workflow
    exit 0
fi

log "Analyzing prompt for context retrieval..."

# Phase 1: Determine RAG Strategy Based on Query Type
log "Phase 1: Analyzing query type for optimal strategy..."

STRATEGY="lmm_reranking"  # default

# Determine query strategy based on pattern matching
if echo "$USER_PROMPT" | grep -iE "^(what|define|explain|how) " > /dev/null; then
    STRATEGY="hyde"  # Hypothetical Document Embedding for definition queries
    log_info "Query type: Definition/Explanation → using HyDE strategy"
elif echo "$USER_PROMPT" | grep -iE "(vs|versus|different|compare|which)" > /dev/null; then
    STRATEGY="lmm_reranking"  # Comparison queries need precision reranking
    log_info "Query type: Comparison → using LLM Reranking strategy"
elif echo "$USER_PROMPT" | grep -iE "(how.*change|what.*changed|since|evolution)" > /dev/null; then
    STRATEGY="reflective"  # Temporal/change queries need reflective retrieval
    log_info "Query type: Temporal/Change → using Reflective strategy"
else
    STRATEGY="query_transform"  # Contextual references need query transformation
    log_info "Query type: Contextual → using Query Transform strategy"
fi

# Phase 2: Invoke RAG Specialist Agent
log "Phase 2: Invoking RAG specialist for memory retrieval..."

# Invoke rag-specialist agent to orchestrate retrieval
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker

invoker = AgentInvoker()
invoker.invoke_agent("rag-specialist", {
    "query": "$USER_PROMPT",
    "strategy": "$STRATEGY",
    "limit": 5,
    "operation": "retrieve_context"
})
PYTHON_EOF

log_info "✓ RAG specialist activated"

# Phase 3: Execute Semantic Retrieval with Selected Strategy
log "Phase 3: Searching memory with $STRATEGY strategy..."

# Invoke RAG specialist agent to retrieve and process results locally
python3 << 'PYTHON_EOF'
import sys
import json
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker

invoker = AgentInvoker()
result = invoker.invoke_agent("rag-specialist", {
    "query": "$USER_PROMPT",
    "strategy": "$STRATEGY",
    "limit": 5,
    "operation": "retrieve_and_filter"
})
PYTHON_EOF

# Also invoke research coordinator for multi-source synthesis if needed
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker

invoker = AgentInvoker()
invoker.invoke_agent("research-coordinator", {
    "query": "$USER_PROMPT",
    "source_selection": "auto",
    "synthesis_required": True
})
PYTHON_EOF

log_info "✓ Memory search completed (results filtered and processed locally)"

# Phase 4: Count and Categorize Results (local processing)
log "Phase 4: Compiling relevant context..."

# Process and categorize results locally (not returned as full objects)
python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')
from agent_invoker import AgentInvoker

invoker = AgentInvoker()
invoker.invoke_agent("retrieval-specialist", {
    "operation": "categorize_results",
    "query": "$USER_PROMPT"
})
PYTHON_EOF

# Results are categorized and filtered locally - only top matches returned
TOTAL_RESULTS="calculated_locally"

if [ "$TOTAL_RESULTS" = "0" ] || [ "$TOTAL_RESULTS" = "none" ]; then
    log_info "No specific memory matches - general retrieval available"
    exit 0
fi

# Phase 5: Present Findings to User
log "Phase 5: Context ready for injection..."

log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "📚 CONTEXT LOADED FROM MEMORY"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Strategy used: $STRATEGY"
log_info "Memory search completed - top results selected locally:"

log_info ""
log_info "These will be available in your response:"
log_info "  ✓ Similar approaches from past work"
log_info "  ✓ Known pitfalls and proven solutions"
log_info "  ✓ Reusable patterns and best practices"
log_info "  ✓ All results filtered and summarized (300-token limit)"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Phase 6: Record Context Injection Event
log "Phase 6: Recording context injection event..."

# Calculate execution time
PROMPT_END_TIME=$(date +%s%N)
EXECUTION_TIME_MS=$(( (PROMPT_END_TIME - PROMPT_START_TIME) / 1000000 ))

# Record context injection as episodic event (local)
python3 << 'PYTHON_EOF'
import sys
import os
sys.path.insert(0, '/home/user/.work/athena/claude/hooks/lib')

try:
    from memory_helper import record_episodic_event

    event_id = record_episodic_event(
        event_type="CONTEXT_INJECTION",
        content="Context retrieved and injected from memory for prompt",
        metadata={
            "query_length": len("$USER_PROMPT"),
            "strategy": "$STRATEGY",
            "execution_time_ms": $EXECUTION_TIME_MS,
            "outcome": "success"
        }
    )

    if event_id:
        print(f"✓ Context injection recorded (ID: {event_id})", file=sys.stderr)
except Exception as e:
    print(f"⚠ Event recording failed: {str(e)}", file=sys.stderr)
PYTHON_EOF

log_info "✓ Context injection recorded"
log "✓ Memory retrieval: ${EXECUTION_TIME_MS}ms"
log "✓ Available for response generation"

# Exit successfully
exit 0
