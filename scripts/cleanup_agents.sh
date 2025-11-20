#!/bin/bash
# Cleanup Agent Session
#
# Kill the agents tmux session and optionally archive logs.
#
# Usage:
#   ./cleanup_agents.sh [session_name] [archive_logs]
#
# Example:
#   ./cleanup_agents.sh athena_agents true

set -e

SESSION="${1:-athena_agents}"
ARCHIVE="${2:-false}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[cleanup]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }
info() { echo -e "${BLUE}[info]${NC} $1"; }

log "Cleaning up agent session: $SESSION"

# Check if session exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    warn "Session '$SESSION' not found"
    exit 0
fi

# Archive logs if requested
if [ "$ARCHIVE" = "true" ]; then
    log "Archiving session logs..."

    LOGS_DIR="logs/agents"
    mkdir -p "$LOGS_DIR"

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ARCHIVE_DIR="$LOGS_DIR/$SESSION-$TIMESTAMP"

    mkdir -p "$ARCHIVE_DIR"

    # Capture pane output
    WINDOW="$SESSION:0"
    PANE_COUNT=$(tmux list-panes -t "$WINDOW" | wc -l)

    for ((pane = 0; pane < PANE_COUNT; pane++)); do
        log "Archiving pane $pane"
        tmux capture-pane -t "$WINDOW.$pane" -p > "$ARCHIVE_DIR/pane_$pane.log"
    done

    info "Logs archived to: $ARCHIVE_DIR"
fi

# Kill the session
log "Killing tmux session: $SESSION"
tmux kill-session -t "$SESSION"

info "Cleanup complete"
