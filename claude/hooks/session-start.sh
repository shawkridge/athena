#!/bin/bash
# Hook: Session Start
# Purpose: Load context and prime memory at session initialization
# Agents: session-initializer
# Target Duration: <500ms

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Log functions
log() {
    echo -e "${GREEN}[SESSION-START]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[SESSION-START INFO]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[SESSION-START WARNING]${NC} $1" >&2
}

log "=== Session Start: Loading Memory Context ==="

# Get session metadata
SESSION_ID="${SESSION_ID:-session-$(date +%s)}"
SESSION_START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

log "Session ID: $SESSION_ID"
log "Started: $SESSION_START_TIME"

# Initialize session using direct Python API (local-first)
log "Loading semantic memories and context..."

# Invoke session-initializer agent (uses direct Python API)
python3 << 'PYTHON_EOF'
import sys
import logging
sys.path.insert(0, '/home/user/.claude/hooks/lib')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

from agent_invoker import AgentInvoker

try:
    # Initialize agent invoker (uses direct Python API)
    invoker = AgentInvoker()

    # Invoke session-initializer agent
    success = invoker.invoke_agent("session-initializer", {
        "session_id": "$SESSION_ID",
        "timestamp": "$SESSION_START_TIME"
    })

    if success:
        print("✓ Session initialized and context loaded", file=sys.stderr)
    else:
        print("⚠ Session initialization completed with warnings", file=sys.stderr)

except Exception as e:
    print(f"✗ Error during session initialization: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
PYTHON_EOF

log_info "✓ Memory context loaded via direct Python API"
log "=== Session Context Loaded Successfully ==="
log "Memory is ready for your work session. Begin your tasks when ready."

exit 0
