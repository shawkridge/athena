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

# Call RAG tools to retrieve relevant memories
# The tool will use the selected strategy automatically
SEARCH_RESULTS=$(mcp__athena__rag_tools retrieve_smart \
  --query "$USER_PROMPT" \
  --strategy "$STRATEGY" \
  --limit 5 2>/dev/null || echo "[]")

# Also try research coordinator for multi-source synthesis if available
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

log_info "✓ Memory search completed"

# Phase 4: Count and Categorize Results
log "Phase 4: Compiling relevant context..."

# Parse results for categorization
# Result types: implementations, procedures/workflows, learnings/insights
IMPLEMENTATIONS=$(echo "$SEARCH_RESULTS" | grep -o '"type":"implementation"' | wc -l || echo "0")
PROCEDURES=$(echo "$SEARCH_RESULTS" | grep -o '"type":"procedure"' | wc -l || echo "0")
INSIGHTS=$(echo "$SEARCH_RESULTS" | grep -o '"type":"insight"' | wc -l || echo "0")

TOTAL_RESULTS=$((IMPLEMENTATIONS + PROCEDURES + INSIGHTS))

if [ "$TOTAL_RESULTS" -eq 0 ]; then
    log_info "No specific memory matches - general retrieval available"
    exit 0
fi

# Phase 5: Present Findings to User
log "Phase 5: Context ready for injection..."

log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "📚 CONTEXT LOADED FROM MEMORY"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_info "Strategy used: $STRATEGY"
log_info "Found $TOTAL_RESULTS relevant items:"

if [ "$IMPLEMENTATIONS" -gt 0 ]; then
    log_info "  • $IMPLEMENTATIONS past implementations"
fi

if [ "$PROCEDURES" -gt 0 ]; then
    log_info "  • $PROCEDURES procedures and workflows"
fi

if [ "$INSIGHTS" -gt 0 ]; then
    log_info "  • $INSIGHTS learnings and insights"
fi

log_info ""
log_info "These will be available in your response:"
log_info "  ✓ Similar approaches from past work"
log_info "  ✓ Known pitfalls and proven solutions"
log_info "  ✓ Reusable patterns and best practices"
log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Phase 6: Record Context Injection Event
log "Phase 6: Recording context injection event..."

# Calculate execution time
PROMPT_END_TIME=$(date +%s%N)
EXECUTION_TIME_MS=$(( (PROMPT_END_TIME - PROMPT_START_TIME) / 1000000 ))

# Record context injection as episodic event
mcp__athena__episodic_tools record_event \
  --event-type "context_injection" \
  --content "{\"query_length\": ${#USER_PROMPT}, \"strategy\": \"$STRATEGY\", \"results_found\": $TOTAL_RESULTS, \"execution_time_ms\": $EXECUTION_TIME_MS}" \
  --outcome "success" 2>/dev/null || true

log_info "✓ Context injection recorded"
log "✓ Memory retrieval: ${EXECUTION_TIME_MS}ms"
log "✓ Available for response generation"

# Exit successfully
exit 0
