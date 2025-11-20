#!/bin/bash
# Spawn Agents in Tmux Session
#
# Creates a tmux session with agent workers running in tiled layout.
#
# Usage:
#   ./spawn_agents.sh [session_name] [num_agents]
#
# Example:
#   ./spawn_agents.sh athena_agents 4

set -e

SESSION="${1:-athena_agents}"
NUM_AGENTS="${2:-4}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[spawn_agents]${NC} $1"; }
info() { echo -e "${BLUE}[info]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }

log "Spawning $NUM_AGENTS agent workers in session '$SESSION'"

# Kill existing session if present
if tmux has-session -t "$SESSION" 2>/dev/null; then
    log "Killing existing session: $SESSION"
    tmux kill-session -t "$SESSION"
    sleep 1
fi

# Create new session with initial window
log "Creating tmux session: $SESSION"
tmux new-session -d -s "$SESSION" -x 200 -y 50

WINDOW="$SESSION:0"

# Create monitor pane (will show dashboard)
log "Setting up monitor pane"
tmux send-keys -t "$WINDOW" "cd \"$PROJECT_ROOT\" && python3 -m athena.coordination.monitor 2>&1" C-m

# Split window into panes for agents (tiled layout)
for ((i = 1; i < NUM_AGENTS; i++)); do
    if [ $((i % 2)) -eq 0 ]; then
        # Split vertically
        tmux split-window -v -t "$WINDOW"
    else
        # Split horizontally
        tmux split-window -h -t "$WINDOW"
    fi
done

# Set tiled layout for even distribution
tmux select-layout -t "$WINDOW" tiled

# Start agent workers in each pane (skip pane 0 which is monitor)
PANE_COUNT=$(tmux list-panes -t "$WINDOW" | wc -l)
AGENT_TYPES=("research" "analysis" "synthesis" "validation" "documentation" "testing")

for ((pane = 1; pane < PANE_COUNT; pane++)); do
    AGENT_TYPE="${AGENT_TYPES[$((pane % ${#AGENT_TYPES[@]}))]}"

    log "Starting agent worker (type: $AGENT_TYPE) in pane $pane"

    tmux send-keys -t "$WINDOW.$pane" \
        "cd \"$PROJECT_ROOT\" && python3 -m athena.coordination.agent_worker --type $AGENT_TYPE 2>&1" \
        C-m

    # Give each agent a moment to start
    sleep 0.5
done

info "Started $((PANE_COUNT - 1)) agent workers"
info "Monitor dashboard running in pane 0"
info ""
info "Attach to session with:"
info "  tmux attach -t $SESSION"
info ""
info "Kill session with:"
info "  tmux kill-session -t $SESSION"

# Optionally attach to session
if [ -t 0 ]; then
    read -p "Attach to session now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        exec tmux attach -t "$SESSION"
    fi
fi
