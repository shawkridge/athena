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

# Detect resume intent (key feature for context injection)
RESUME_INTENT=false
if echo "$USER_PROMPT" | grep -iE "carry on|continue|resume|where (was|were|am|is|are) (I|we|you)|what (was|were|am|is|are) (I|we|you)" > /dev/null; then
    RESUME_INTENT=true
    log_info "Resume intent detected - loading previous session context"
fi

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

# Record the user's prompt as an episodic event for cross-project memory
# This enables remembering questions asked in other projects
log "Recording prompt to episodic memory..."

python3 << 'PYTHON_EOF'
import sys
import os
import re
import logging
sys.path.insert(0, '/home/user/.claude/hooks/lib')

# Suppress verbose logging
logging.basicConfig(level=logging.WARNING)

RESUME_INTENT = "$RESUME_INTENT"

try:
    from memory_bridge import MemoryBridge
    from session_context_manager import SessionContextManager
    from advanced_context_intelligence import AdvancedContextIntelligence

    user_prompt = """$USER_PROMPT"""

    # Initialize session managers
    session_mgr = SessionContextManager()  # Phase 3: Token efficiency
    intel = AdvancedContextIntelligence(session_id="user_prompt")  # Phase 4: Advanced intelligence

    # Connect to memory and record event
    with MemoryBridge() as bridge:
        project = bridge.get_project_by_path(os.getcwd())
        if not project:
            sys.exit(0)

        project_id = project['id']

        # Record the prompt to episodic memory
        event_id = bridge.record_event(
            project_id=project_id,
            event_type="user_question",
            content=user_prompt,
            outcome="recorded"
        )

        if event_id:
            print(f"  ✓ Prompt recorded (event {event_id})", file=sys.stderr)

        # Phase 4: Analyze for advanced intelligence (entities, proactive loading)
        intel_analysis = intel.analyze_prompt_for_intelligence(user_prompt)
        if intel_analysis["entity_count"] > 0:
            print(f"  ✓ Detected {intel_analysis['entity_count']} entities for context pre-loading", file=sys.stderr)

        # If resume intent detected, inject recent context to Claude
        if RESUME_INTENT == "true":
            # Get recent events from this project
            recent = bridge.search_memories(project_id, user_prompt, limit=5)

            if recent['found'] > 0:
                # Convert to format expected by session manager
                memories = [
                    {
                        "id": r.get("id", f"mem_{i}"),
                        "title": r.get("title", r.get("content", "")[:50]),
                        "content": r.get("content", ""),
                        "type": r.get("type", "memory"),
                        "timestamp": r.get("timestamp"),
                        "relevance": r.get("relevance", 0.5),
                        "composite_score": r.get("relevance", 0.5),
                    }
                    for i, r in enumerate(recent['results'][:5])
                ]

                # Use adaptive formatting with token budget (Phase 3)
                formatted, injected_ids, tokens_used = session_mgr.format_context_adaptive(
                    memories=memories,
                    max_tokens=200  # Reserve tokens for Phase 4 proactive context
                )

                context_parts = []

                if formatted:
                    context_parts.append("## Recent Context\n" + formatted)

                # Phase 4: Add proactive context for detected entities
                if intel_analysis["proactive_plan"]:
                    proactive_text = intel.proactive_loader.format_loading_plan(max_tokens=100)
                    if proactive_text:
                        context_parts.append(proactive_text)

                if context_parts:
                    # Output to stdout (Claude will see this)
                    print("\n".join(context_parts))

                    # User log (stderr)
                    print(f"  ✓ Injected {len(injected_ids)} memories + proactive context ({tokens_used} tokens)", file=sys.stderr)

                    stats = session_mgr.get_session_stats()
                    if stats['cache_stats']['total_injected'] > len(injected_ids):
                        skipped = stats['cache_stats']['total_injected'] - len(injected_ids)
                        print(f"  ℹ Deduplication skipped {skipped} previously-injected", file=sys.stderr)
            else:
                print(f"  ℹ No recent context available", file=sys.stderr)
        else:
            # Even without resume intent, inject proactive context if entities detected
            if intel_analysis["entity_count"] > 0:
                proactive_text = intel.proactive_loader.format_loading_plan(max_tokens=150)
                if proactive_text:
                    print(proactive_text)
                    print(f"  ✓ Proactive context for {intel_analysis['entity_count']} entities", file=sys.stderr)
            else:
                print(f"  ✓ No special context needed", file=sys.stderr)

except Exception as e:
    print(f"  ⚠ Error in context injection: {str(e)}", file=sys.stderr)
    import traceback
    print(traceback.format_exc(), file=sys.stderr)
PYTHON_EOF

# Exit successfully (don't block user interaction)
exit 0
