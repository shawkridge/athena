#!/bin/bash

################################################################################
# Post-Response Hook: Dream Evaluation Capture
#
# Triggered after Claude responds with dream evaluations.
# Parses response and stores evaluations in the dream database.
#
# This hook is called by Claude Code's post-response event.
################################################################################

set -e

# Configuration
HOOKS_LIB="$HOME/.claude/hooks/lib"
HANDLER="$HOOKS_LIB/dream_evaluation_handler.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Get response from environment
RESPONSE="${CLAUDE_RESPONSE:-}"

# If no response in environment, skip (only process explicit dream evaluations)
if [ -z "$RESPONSE" ]; then
    exit 0
fi

# Check if response contains dream evaluation markers
if ! echo "$RESPONSE" | grep -qi "viability\|tier\|viable\|speculative"; then
    # Not a dream evaluation, skip processing
    exit 0
fi

# Log that we're processing dream evaluation
echo "[$(date)] Processing dream evaluation response ($(echo "$RESPONSE" | wc -c) bytes)" >> ~/.claude/hooks.log

# Run the handler
export CLAUDE_RESPONSE="$RESPONSE"

if "$PYTHON_BIN" "$HANDLER" >> ~/.claude/hooks.log 2>&1; then
    echo "[$(date)] Dream evaluation processed successfully" >> ~/.claude/hooks.log
else
    echo "[$(date)] Warning: Dream evaluation processing had errors" >> ~/.claude/hooks.log
fi

exit 0
