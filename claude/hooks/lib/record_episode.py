#!/usr/bin/env python3
"""
Record Episodic Event Utility - Record work activities to episodic memory

Records file/code tool executions as episodic events in MCP memory.
Captures: tool name, file paths, timestamps, event type (file_change/action)

Usage:
    python3 record_episode.py --tool <tool> --event-type <type> --cwd <path> [--files <files>]
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


def record_episode(
    tool_name: str,
    event_type: str,
    cwd: str,
    files: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    project_id: Optional[int] = None,
    task: Optional[str] = None,
    phase: Optional[str] = None
) -> Dict[str, Any]:
    """Record an episodic event from tool execution."""

    result = {
        "success": False,
        "event_id": None,
        "event": None,
        "errors": []
    }

    try:
        # Add memory-mcp to path if available
        athena_path = Path('/home/user/.work/athena/src')
        if athena_path.exists():
            sys.path.insert(0, str(athena_path))

        from athena.core.database import Database
        from athena.episodic.store import EpisodicStore
        from athena.episodic.models import EpisodicEvent, EventType, EventOutcome, EventContext

        db_path = Path.home() / '/home/user/.work/athena' / 'memory.db'
        if not db_path.exists():
            result["errors"].append("Memory database not found")
            return result

        db = Database(str(db_path))
        episodic_store = EpisodicStore(db)

        # Auto-detect project_id from cwd if not provided
        if project_id is None:
            cursor = db.conn.cursor()
            cursor.execute("SELECT id FROM projects WHERE path = ? LIMIT 1", (cwd,))
            row = cursor.fetchone()
            project_id = row[0] if row else 1  # Fallback to 1 if not found
            cursor.close()

        # Generate session_id if not provided
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())[:12]

        # Create episodic event
        # Normalize event type to match EventType enum (lowercase with underscores)
        normalized_type = event_type.lower().replace(" ", "_")

        event = EpisodicEvent(
            project_id=project_id,
            session_id=session_id,
            content=f"{tool_name}: {event_type}",
            event_type=EventType(normalized_type),
            outcome=EventOutcome.SUCCESS,
            timestamp=datetime.now(),
            context=EventContext(
                cwd=cwd,
                files=files or [],
                task=task,
                phase=phase
            )
        )

        # Record the event
        event_id = episodic_store.record_event(event)

        result["success"] = True
        result["event_id"] = event_id
        result["event"] = {
            "id": event_id,
            "content": event.content,
            "type": str(event.event_type),
            "outcome": str(event.outcome) if event.outcome else None,
            "timestamp": event.timestamp.isoformat(),
            "location": cwd,
            "files": files or []
        }

    except Exception as e:
        result["errors"].append(f"Recording failed: {str(e)}")

    return result


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Record episodic event from tool execution')
    parser.add_argument('--tool', required=True, help='Tool name (SessionStart, UserPromptSubmit, SessionEnd, etc.)')
    parser.add_argument('--event-type', required=True, help='Event type (action, conversation, etc.)')
    parser.add_argument('--cwd', required=True, help='Current working directory')
    parser.add_argument('--files', nargs='*', default=[], help='Affected files')
    parser.add_argument('--session-id', default=None, help='Session ID (auto-generated if not provided)')
    parser.add_argument('--project-id', type=int, default=None, help='Project ID (auto-detected from cwd if not provided)')
    parser.add_argument('--task', default=None, help='Current task being worked on (optional)')
    parser.add_argument('--phase', default=None, help='Execution phase (optional)')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    # Record the episode
    result = record_episode(
        tool_name=args.tool,
        event_type=args.event_type,
        cwd=args.cwd,
        files=args.files if args.files else None,
        session_id=args.session_id,
        project_id=args.project_id,
        task=args.task,
        phase=args.phase
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"✅ Episodic event recorded (ID: {result['event_id']})")
            print(f"   Content: {result['event']['content']}")
            print(f"   Timestamp: {result['event']['timestamp']}")
        else:
            print(f"❌ Failed to record episodic event")
            for error in result["errors"]:
                print(f"   Error: {error}")

        # Print JSON to stdout for hooks
        print(json.dumps(result))
