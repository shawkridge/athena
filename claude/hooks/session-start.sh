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
from datetime import datetime, timedelta
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
        print(f"✓ Loading working memory from previous session...", file=sys.stderr)

        mem_result = bridge.get_active_memories(project_id, limit=7)
        active_items = mem_result.get('items', [])

        # Import session managers
        from session_context_manager import SessionContextManager  # Phase 3: Token efficiency
        from advanced_context_intelligence import AdvancedContextIntelligence, CrossSessionContinuity  # Phase 4: Advanced intelligence

        session_mgr = SessionContextManager()

        # Phase 4: Initialize cross-session continuity for smart resumption
        continuity = CrossSessionContinuity(session_id="session_start", project_id=project_id)

        # Phase 4: Check for session gap and format resumption context
        last_session_time = bridge.get_last_session_time(project_id)
        if last_session_time:
            gap_analysis = continuity.analyze_session_gap(datetime.utcnow(), last_session_time)
            gap_type = gap_analysis.get("gap_type")
            gap_readable = gap_analysis.get("human_readable", "some time ago")

            # Log gap for debugging
            if gap_type != "first_session":
                print(f"  ✓ Session resumed after {gap_readable} ({gap_type})", file=sys.stderr)

        # INJECT TO CLAUDE: Working memory (stdout) - using TOON format
        if active_items:
            # Convert to session manager format
            # NOTE: content is already importance-based truncated from memory_bridge.py
            # Do NOT re-truncate here (removes redundant Layer 2 truncation)
            # ENHANCED: Include project context for better memory continuity
            memories = [
                {
                    "id": f"mem_working_{i}",
                    "title": item['content'],  # Already importance-based truncated from bridge
                    "content": item['content'],  # Full is now available in bridge
                    "type": item['type'],
                    "timestamp": item.get('timestamp'),
                    "importance": item.get('importance', 0.5),
                    "actionability": item.get('actionability', 0.5),
                    "context_completeness": item.get('context_completeness', 0.5),
                    "project": item.get('project'),  # NEW: Project context for continuity
                    "goal": item.get('goal'),  # NEW: Current goal context
                    "phase": item.get('phase'),  # NEW: Project phase
                    "combined_rank": item.get('combined_rank', 0.0),  # NEW: Ranking score
                    "composite_score": item.get('combined_rank', item.get('importance', 0.5)),
                }
                for i, item in enumerate(active_items[:7])  # Increased to 7 for 7±2 cognitive limit
            ]

            # Use TOON format for ~40% token savings (preferred)
            # Falls back to adaptive formatting if TOON not available
            formatted, injected_ids, tokens_used = session_mgr.format_context_toon(
                memories=memories,
                max_tokens=400  # TOON uses ~60% of JSON budget, so more content fits
            )

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

        # Load operational checkpoint for session resumption
        print(f"✓ Loading operational checkpoint...", file=sys.stderr)

        from checkpoint_manager import CheckpointManager
        checkpoint_mgr = CheckpointManager()
        checkpoint = checkpoint_mgr.load_latest_checkpoint(project_id)
        checkpoint_mgr.close()

        if checkpoint:
            # Add checkpoint to working memory with high importance
            checkpoint_memory = {
                "id": "checkpoint_resume",
                "title": f"Resume: {checkpoint.get('task_name', 'Task')}",
                "content": f"File: {checkpoint.get('file_path')}\nTest: {checkpoint.get('test_name')}\nNext: {checkpoint.get('next_action')}",
                "type": "checkpoint",
                "timestamp": checkpoint.get('_loaded_timestamp'),
                "importance": 0.95,  # Very high priority
                "composite_score": 0.95,
            }

            # Prepend checkpoint to active_items for priority display
            active_items.insert(0, {
                'id': checkpoint['task_name'],
                'type': 'checkpoint',
                'content': f"Resume: {checkpoint.get('task_name')} in {checkpoint.get('file_path')}. Next: {checkpoint.get('next_action')}",
                'timestamp': checkpoint.get('_loaded_timestamp'),
                'importance': 0.95,
                'actionability': 0.95,
                'context_completeness': 0.9,
                'project': project.get('name'),
                'goal': checkpoint.get('task_name'),
                'phase': 'resuming',
                'combined_rank': 0.95,
            })

            print(f"  ✓ Checkpoint loaded:", file=sys.stderr)
            print(f"    Task: {checkpoint.get('task_name', 'unknown')}", file=sys.stderr)
            print(f"    File: {checkpoint.get('file_path', 'unknown')}", file=sys.stderr)
            print(f"    Test: {checkpoint.get('test_name', 'unknown')}", file=sys.stderr)
            print(f"    Next: {checkpoint.get('next_action', 'unknown')}", file=sys.stderr)
        else:
            print(f"  ℹ No checkpoint from previous session", file=sys.stderr)

        # Phase: Auto-run checkpoint test
        if checkpoint and checkpoint.get('test_name'):
            print(f"✓ Running checkpoint test for session state...", file=sys.stderr)

            test_name = checkpoint.get('test_name')

            # Attempt to run the test
            # This is a best-effort attempt - uses common test runners
            import subprocess

            test_runners = [
                f"npm test -- {test_name}",  # npm/jest
                f"pytest {test_name}",        # pytest
                f"go test -run {test_name}",  # golang
                f"cargo test {test_name}",    # rust
                f"python -m pytest {test_name}",  # python
                f"./test.sh {test_name}",     # custom script
            ]

            test_passed = False
            test_output = ""

            for runner in test_runners:
                try:
                    result = subprocess.run(
                        runner,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    test_output = result.stdout + result.stderr
                    test_passed = result.returncode == 0

                    if "not found" not in test_output.lower() and "unknown" not in test_output.lower():
                        # Looks like we ran something
                        break
                except (subprocess.TimeoutExpired, Exception):
                    continue

            if test_output:
                # Save test results back to checkpoint
                if test_passed:
                    print(f"  ✓ Test PASSED: {test_name}", file=sys.stderr)
                    os.environ['CHECKPOINT_TEST_STATUS'] = 'passing'
                else:
                    print(f"  ✗ Test FAILED: {test_name}", file=sys.stderr)
                    os.environ['CHECKPOINT_TEST_STATUS'] = 'failing'
                    # Extract error from output
                    error_lines = [l for l in test_output.split('\n') if 'error' in l.lower() or 'fail' in l.lower()]
                    if error_lines:
                        os.environ['CHECKPOINT_ERROR'] = error_lines[0][:200]

                print(f"  Output preview: {test_output[:100]}...", file=sys.stderr)
            else:
                print(f"  ℹ Could not auto-run test '{test_name}' (test runner not found)", file=sys.stderr)
                print(f"    You can run it manually when ready", file=sys.stderr)

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

        # Phase: Load tasks into TodoWrite
        print(f"✓ Loading tasks for TodoWrite...", file=sys.stderr)

        from todowrite_sync import TodoWriteSync
        todowrite_sync = TodoWriteSync()

        # Load active tasks from PostgreSQL
        active_tasks = todowrite_sync.load_tasks_from_postgres(
            project_id=project_id,
            limit=10,
            statuses=["pending", "in_progress", "blocked"]
        )

        if active_tasks:
            # Convert to TodoWrite format
            todowrite_format = todowrite_sync.convert_to_todowrite_format(active_tasks)

            # Write to session-scoped TodoWrite file
            import os
            session_id = os.environ.get('CLAUDE_SESSION_ID', 'default')
            todowrite_path = f"/home/user/.claude/todos/{session_id}.json"

            # Ensure directory exists
            os.makedirs("/home/user/.claude/todos/", exist_ok=True)

            # Write TodoWrite JSON
            with open(todowrite_path, 'w') as f:
                json.dump(todowrite_format, f, indent=2)

            print(f"  ✓ Loaded {len(active_tasks)} active tasks into TodoWrite", file=sys.stderr)
            for i, task in enumerate(active_tasks[:3], 1):
                status_icon = "→" if task['status'] == 'in_progress' else "·"
                print(f"    {status_icon} [{task['status']}] {task['content'][:50]}", file=sys.stderr)
        else:
            print(f"  ℹ No active tasks found", file=sys.stderr)

        todowrite_sync.close()

        # Phase 3: Initialize agents for autonomous memory management
        print(f"✓ Initializing agents for autonomous learning...", file=sys.stderr)

        try:
            from agent_bridge import initialize_memory_coordinator

            agent_result = initialize_memory_coordinator()

            if agent_result.get("status") == "success":
                print(f"  ✓ MemoryCoordinatorAgent initialized", file=sys.stderr)
                print(f"    Agent ID: {agent_result.get('agent_id')}", file=sys.stderr)
                print(f"    Agent Type: {agent_result.get('agent_type')}", file=sys.stderr)
            else:
                print(f"  ⚠ MemoryCoordinatorAgent init failed: {agent_result.get('error')}", file=sys.stderr)

        except Exception as e:
            print(f"  ⚠ Could not initialize agents: {str(e)}", file=sys.stderr)

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
