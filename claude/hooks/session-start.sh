#!/bin/bash
# Hook: Session Start
# Purpose: Load working memory from previous session
# Loads 7±2 working memory items, active goals, and recent context
# Target Duration: <300ms

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Log functions
log() {
    echo -e "${GREEN}[SESSION-START]${NC} $1" >&2
}

log_info() {
    echo -e "${BLUE}[SESSION-INFO]${NC} $1" >&2
}

log_context() {
    echo -e "${CYAN}[CONTEXT]${NC} $1" >&2
}

log "Checking PostgreSQL health..."

# Check PostgreSQL health first
python3 << 'HEALTH_CHECK_EOF'
import sys
sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from postgres_health_check import PostgreSQLHealthCheck

    checker = PostgreSQLHealthCheck(verbose=False)
    health = checker.get_full_status()

    if not health.healthy:
        print(f"⚠️  PostgreSQL Health Check Failed", file=sys.stderr)
        print(f"   Status: {health.status.value}", file=sys.stderr)
        if health.error:
            print(f"   Error: {health.error}", file=sys.stderr)
        if health.recommendations:
            print(f"", file=sys.stderr)
            print(f"   Recommendations:", file=sys.stderr)
            for rec in health.recommendations:
                print(f"   → {rec}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"   Session will continue, but memory recording may not work", file=sys.stderr)
    else:
        print(f"✓ PostgreSQL is healthy", file=sys.stderr)

except Exception as e:
    print(f"⚠️  Could not check PostgreSQL health: {str(e)}", file=sys.stderr)

HEALTH_CHECK_EOF

log "Loading session context from memory..."

# Load working memory and active goals using direct PostgreSQL bridge
python3 << 'PYTHON_EOF'
import sys
import logging
import os
from datetime import datetime, timedelta, timezone
import time

# Suppress verbose logging
logging.basicConfig(level=logging.WARNING)

sys.path.insert(0, '/home/user/.claude/hooks/lib')

try:
    from memory_bridge import MemoryBridge

    start_time = time.time()

    # Connect to PostgreSQL
    with MemoryBridge() as bridge:
        # Get current project (based on working directory)
        project_path = os.getcwd()
        project = bridge.get_project_by_path(project_path)

        if not project:
            print("⚠ No project context found", file=sys.stderr)
            sys.exit(0)

        project_id = project['id']

        # Load working memory (7±2 items with highest importance)
        # Session checkpoints (importance_score=0.95) are automatically ranked high
        # by get_active_memories() and appear naturally in the top items
        print(f"✓ Loading working memory from previous session...", file=sys.stderr)

        mem_result = bridge.get_active_memories(project_id, limit=7)
        active_items = mem_result.get('items', [])

        # Import session managers
        from session_context_manager import SessionContextManager  # Phase 3: Token efficiency
        from advanced_context_intelligence import AdvancedContextIntelligence, CrossSessionContinuity  # Phase 4: Advanced intelligence

        # Create NEW session manager (not tied to old session cache)
        # This ensures working memory is shown even if it was recently injected
        import uuid
        new_session_id = f"session_start_{uuid.uuid4().hex[:8]}"
        session_mgr = SessionContextManager(session_id=new_session_id)

        # Phase 4: Initialize cross-session continuity for smart resumption
        continuity = CrossSessionContinuity(session_id="session_start", project_id=project_id)

        # Phase 4: Check for session gap and format resumption context
        # Use timezone-aware UTC datetime (matches memory_bridge.get_last_session_time())
        last_session_time = bridge.get_last_session_time(project_id)
        if last_session_time:
            current_time = datetime.now(timezone.utc).replace(tzinfo=None)
            gap_analysis = continuity.analyze_session_gap(current_time, last_session_time)
            gap_type = gap_analysis.get("gap_type")
            gap_readable = gap_analysis.get("human_readable", "some time ago")

            # Log gap for debugging
            if gap_type != "first_session":
                print(f"  ✓ Session resumed after {gap_readable} ({gap_type})", file=sys.stderr)

        # INJECT TO CLAUDE: Working memory (stdout)
        if active_items:
            # Get full content for each memory (not truncated summary)
            memories = []
            for i, item in enumerate(active_items[:5]):
                full_content = bridge.get_memory_content(item['id'])
                if full_content is None:
                    full_content = item['content']  # Fallback to truncated if full retrieval fails

                # Working memory at session start is CRITICAL - boost composite score to ensure full formatting
                # Uses HIGH_RELEVANCE_THRESHOLD (0.85) to trigger _format_full() instead of _format_reference()
                memories.append({
                    "id": f"mem_working_{i}",
                    "title": full_content[:60] if len(full_content) > 60 else full_content,
                    "content": full_content,
                    "type": item['type'],
                    "timestamp": item.get('timestamp'),
                    "importance": 0.9,  # Boost: session-start context is critical
                    "composite_score": 0.9,  # Triggers _format_full() instead of _format_reference()
                })

            # Format memories directly (skip prioritizer to preserve pre-set composite_score)
            # Working memory at session start is critical - format as full context
            from session_context_manager import AdaptiveFormatter

            formatted_lines = []
            for mem in memories[:5]:
                formatted_line, _ = AdaptiveFormatter.format_memory(
                    memory_id=mem["id"],
                    title=mem.get("title", "Memory"),
                    content=mem.get("content", ""),
                    relevance_score=mem.get("composite_score", 0.9),  # Use pre-set score
                    memory_type=mem.get("type", "memory"),
                    timestamp=mem.get("timestamp"),
                )
                formatted_lines.append(formatted_line)

            formatted = "".join(formatted_lines)

            if formatted:
                print("## Working Memory (Resuming)")
                print(formatted)

            # User log (stderr)
            print(f"  ✓ {len(active_items)} active memory items (7±2 capacity):", file=sys.stderr)
            for i, item in enumerate(active_items[:3], 1):
                content_preview = item['content'][:40] + "..." if len(item['content']) > 40 else item['content']
                importance = item.get('importance', 0.5)
                print(f"    {i}. [{item['type']}] {content_preview} (importance: {importance:.1%})", file=sys.stderr)
        else:
            print(f"  No previous context found", file=sys.stderr)

        # Load active goals/tasks
        print(f"✓ Loading active goals...", file=sys.stderr)

        goals_result = bridge.get_active_goals(project_id, limit=5)
        goals = goals_result.get('goals', [])

        # INJECT TO CLAUDE: Active goals (stdout)
        if goals:
            # Convert to session manager format
            goal_memories = [
                {
                    "id": f"goal_{i}",
                    "title": goal['title'],
                    "content": f"Status: {goal.get('status', 'unknown')}, Priority: {goal.get('priority', 'normal')}",
                    "type": "goal",
                    "timestamp": goal.get('created_at'),
                    "importance": 0.8 if goal.get('status') == 'active' else 0.5,
                    "composite_score": 0.8 if goal.get('status') == 'active' else 0.5,
                }
                for i, goal in enumerate(goals[:3])
            ]

            # Use adaptive formatting
            formatted_goals, goal_ids, goal_tokens = session_mgr.format_context_adaptive(
                memories=goal_memories,
                max_tokens=200
            )

            if formatted_goals:
                print("## Active Goals")
                print(formatted_goals)

            # User log (stderr)
            print(f"  ✓ {len(goals)} active goals:", file=sys.stderr)
            for i, goal in enumerate(goals[:3], 1):
                title_preview = goal['title'][:40] + "..." if len(goal['title']) > 40 else goal['title']
                print(f"    {i}. [{goal.get('status', 'unknown')}] {title_preview}", file=sys.stderr)
        else:
            print(f"  No active goals found", file=sys.stderr)

        # Load active TodoWrite items (restored from Athena after /clear)
        print(f"✓ Loading active TodoWrite items...", file=sys.stderr)

        try:
            from todowrite_helper import TodoWriteSyncHelper

            sync_helper = TodoWriteSyncHelper()
            todos = sync_helper.get_active_todos(project_id=project_id)

            # INJECT TO CLAUDE: Active TodoWrite items (stdout)
            if todos:
                todo_memories = [
                    {
                        "id": f"todo_{i}",
                        "title": todo.get('content', 'Unnamed task')[:60],
                        "content": f"Status: {todo.get('status', 'pending')} | Action: {todo.get('activeForm', todo.get('content', ''))}",
                        "type": "todo",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "importance": 0.85 if todo.get('status') == 'in_progress' else 0.7,
                        "composite_score": 0.85 if todo.get('status') == 'in_progress' else 0.7,
                    }
                    for i, todo in enumerate(todos[:5])
                ]

                # Use adaptive formatting
                formatted_todos, todo_ids, todo_tokens = session_mgr.format_context_adaptive(
                    memories=todo_memories,
                    max_tokens=300
                )

                if formatted_todos:
                    print("## Restored Task List (from Previous Session)")
                    print()
                    print("Your previous session had the following active tasks:")
                    print()
                    print(formatted_todos)
                    print()
                    print("**ACTION REQUIRED**: Please add these restored tasks to your TodoWrite to resume your workflow.")
                    print("Use the TodoWrite tool to recreate each task with its original status and description.")

                # User log (stderr)
                print(f"  ✓ {len(todos)} active TodoWrite items (restored from memory):", file=sys.stderr)
                for i, todo in enumerate(todos[:3], 1):
                    content_preview = todo.get('content', 'Unnamed')[:40]
                    status = todo.get('status', 'unknown')
                    print(f"    {i}. [{status}] {content_preview}", file=sys.stderr)
            else:
                print(f"  No active TodoWrite items found", file=sys.stderr)

        except ImportError:
            print(f"  TodoWrite sync module not available (skipping)", file=sys.stderr)
        except Exception as e:
            print(f"  TodoWrite restoration error: {str(e)}", file=sys.stderr)

        # RESTORE todos to local Claude Code JSON file
        # This ensures the TodoWrite tool UI shows restored items, not just stdout
        print(f"✓ Restoring TodoWrite items to local file...", file=sys.stderr)

        try:
            import json
            from pathlib import Path
            import glob as glob_module
            import uuid

            todos_dir = Path(os.path.expanduser('~/.claude/todos'))
            todos_dir.mkdir(parents=True, exist_ok=True)

            # Strategy: Use CLAUDE_SESSION_ID if available, fall back to most recent file
            session_id = os.environ.get('CLAUDE_SESSION_ID')
            todo_file = None

            if session_id:
                # Look for todo files matching this session ID
                session_files = list(todos_dir.glob(f"{session_id}-agent-*.json"))
                if session_files:
                    # Use the first matching file (should only be one per session)
                    todo_file = session_files[0]

            if not todo_file:
                # Fallback: Find the most recently modified agent todo file
                todo_files = list(todos_dir.glob("*-agent-*.json"))
                if todo_files:
                    todo_file = max(todo_files, key=lambda f: f.stat().st_mtime)

            if not todo_file and todos:
                # Last resort: Create a new file with a reasonable name
                # Use session_id if available, otherwise generate a unique name
                if session_id:
                    agent_id = session_id
                else:
                    agent_id = str(uuid.uuid4())[:8]

                todo_file = todos_dir / f"{agent_id}-agent-{agent_id}.json"
                print(f"  ℹ Creating new todo file: {todo_file.name}", file=sys.stderr)

            if todo_file and todos:
                with open(todo_file, 'w') as f:
                    json.dump(todos, f, indent=2)
                print(f"  ✓ Restored {len(todos)} todos to {todo_file.name}", file=sys.stderr)
            elif todos:
                print(f"  ⚠ Could not determine todo file location", file=sys.stderr)
            else:
                print(f"  ℹ No todos to restore", file=sys.stderr)

        except Exception as e:
            print(f"  ⚠ Could not restore todos to local file: {str(e)}", file=sys.stderr)

        elapsed_ms = (time.time() - start_time) * 1000
        print(f"✓ Session context initialized ({elapsed_ms:.0f}ms)", file=sys.stderr)

        if elapsed_ms > 300:
            print(f"⚠ Session init took {elapsed_ms:.0f}ms (target: <300ms)", file=sys.stderr)

except ImportError as e:
    print(f"⚠ Could not import memory bridge: {str(e)}", file=sys.stderr)
except Exception as e:
    print(f"⚠ Session initialization: {str(e)}", file=sys.stderr)

PYTHON_EOF

log_info "Session ready - memory loaded"
exit 0
