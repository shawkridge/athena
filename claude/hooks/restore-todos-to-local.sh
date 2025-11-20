#!/bin/bash
# Hook: Restore TodoWrite items to local JSON file after session-start
# Purpose: Populate Claude Code's local todo storage with restored todos from Athena
# Fires on: SessionStart (after memory is loaded)
# Target Duration: <100ms
#
# This bridges the gap between:
# - session-start.sh (loads todos from PostgreSQL to stdout)
# - TodoWrite tool (reads from local ~/.claude/todos/*.json files)
#
# Without this, session-start would load todos to stdout but TodoWrite UI wouldn't see them.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[RESTORE-TODOS]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[RESTORE-TODOS]${NC} $1" >&2
}

log "Restoring TodoWrite items to local JSON file..."

python3 << 'PYTHON_EOF'
import sys
import os
import json
import uuid
from pathlib import Path

sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from todowrite_helper import TodoWriteSyncHelper
    from memory_bridge import MemoryBridge

    # Detect current session ID from environment or process
    # Claude Code sets CLAUDE_SESSION_ID when running
    session_id = os.environ.get('CLAUDE_SESSION_ID')

    if not session_id:
        # Fallback: check recently modified todo files
        # The most recent file is the current session
        todos_dir = Path(os.path.expanduser('~/.claude/todos'))
        if todos_dir.exists():
            recent_files = sorted(
                todos_dir.glob('*-agent-*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if recent_files:
                # Parse session ID from filename
                # Format: {session-id}-agent-{agent-id}.json
                parts = recent_files[0].name.rsplit('-agent-', 1)
                if len(parts) == 2:
                    session_id = parts[0]

    if not session_id:
        print("⚠ Could not detect session ID (CLAUDE_SESSION_ID env var not set)", file=sys.stderr)
        print("  TodoWrite restoration will be skipped", file=sys.stderr)
        print("  To fix: ensure Claude Code is setting CLAUDE_SESSION_ID environment variable", file=sys.stderr)
        sys.exit(0)

    print(f"✓ Detected session: {session_id}", file=sys.stderr)

    # Get restored todos from Athena
    sync_helper = TodoWriteSyncHelper()

    with MemoryBridge() as bridge:
        project_path = os.getcwd()
        project = bridge.get_project_by_path(project_path)

        if not project:
            project = {'id': 1}

        project_id = project['id']

    # Retrieve active todos from database
    todos_from_athena = sync_helper.get_active_todos(project_id=project_id)

    if not todos_from_athena:
        print(f"  No active todos found in Athena", file=sys.stderr)
        sys.exit(0)

    print(f"✓ Retrieved {len(todos_from_athena)} active todos from Athena", file=sys.stderr)

    # Find the local todo JSON file for this session
    todos_dir = Path(os.path.expanduser('~/.claude/todos'))
    todos_dir.mkdir(parents=True, exist_ok=True)

    # Look for existing todo file for this session
    todo_file = None
    for agent_id_candidate in [session_id]:  # Try exact match first
        candidate = todos_dir / f"{session_id}-agent-{agent_id_candidate}.json"
        if candidate.exists():
            todo_file = candidate
            break

    # If not found, look for ANY file matching this session
    if not todo_file:
        for f in todos_dir.glob(f"{session_id}-agent-*.json"):
            todo_file = f
            break

    # If still not found, create a new one
    if not todo_file:
        # Generate an agent ID (matches Claude Code's format)
        agent_id = session_id  # Default to session_id as agent_id
        todo_file = todos_dir / f"{session_id}-agent-{agent_id}.json"
        print(f"  Creating new todo file: {todo_file.name}", file=sys.stderr)

    print(f"✓ Using todo file: {todo_file.name}", file=sys.stderr)

    # Write todos to local file
    # Format: array of {content, status, activeForm}
    with open(todo_file, 'w') as f:
        json.dump(todos_from_athena, f, indent=2)

    print(f"✓ Restored {len(todos_from_athena)} todos to {todo_file.name}", file=sys.stderr)
    print(f"✓ TodoWrite list is now populated with restored items", file=sys.stderr)

except ImportError as e:
    print(f"⚠ Could not import sync helper: {str(e)}", file=sys.stderr)
    sys.exit(0)
except Exception as e:
    import traceback
    print(f"⚠ Todo restoration error: {str(e)}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(0)

PYTHON_EOF

exit 0
