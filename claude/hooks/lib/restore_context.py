#!/usr/bin/env python3
"""
Restore Context Utility - Restore critical context after compaction

After Claude Code compacts context, restore critical information:
1. Active goals
2. Current tasks (in_progress)
3. Recent blockers
4. Knowledge gaps
5. Cognitive load status

Usage:
    python3 restore_context.py --project <project> --cwd <path>
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


def restore_context(project: str, cwd: str) -> Dict[str, Any]:
    """Restore critical context from memory after compaction."""

    context = {
        "project": project,
        "cwd": cwd,
        "timestamp": datetime.now().isoformat(),
        "restored": False,
        "critical_goals": [],
        "active_tasks": [],
        "recent_blockers": [],
        "knowledge_gaps": [],
        "cognitive_load": {},
        "recommendations": [],
        "errors": []
    }

    try:
        # Add memory-mcp to path if available
        athena_path = Path('/home/user/.work/athena/src')
        if athena_path.exists():
            sys.path.insert(0, str(athena_path))

        from athena.core.database import Database
        from athena.graph.store import GraphStore
        from athena.prospective.store import ProspectiveStore

        db_path = Path.home() / '/home/user/.work/athena' / 'memory.db'
        if not db_path.exists():
            context["errors"].append("Memory database not found")
            return context

        db = Database(str(db_path))
        graph_store = GraphStore(db)
        task_store = ProspectiveStore(db)

        # ============================================================
        # Restore Critical Goals
        # ============================================================
        try:
            goals = graph_store.search_entities("goal", entity_type="Decision")
            for goal in goals[:3]:  # Top 3 goals
                context["critical_goals"].append({
                    "name": goal.name,
                    "priority": goal.metadata.get("priority", 5),
                    "description": goal.metadata.get("description", "")
                })
        except Exception as e:
            context["errors"].append(f"Could not restore goals: {str(e)}")

        # ============================================================
        # Restore Active Tasks
        # ============================================================
        try:
            all_tasks = task_store.list_tasks()
            for task in all_tasks:
                status = task.status.value if hasattr(task.status, "value") else str(task.status)
                if status == "in_progress":
                    context["active_tasks"].append({
                        "id": task.id,
                        "content": task.content,
                        "priority": task.priority.value if hasattr(task.priority, "value") else str(task.priority),
                        "due_at": task.due_at.isoformat() if task.due_at else None
                    })
            context["active_tasks"] = context["active_tasks"][:5]  # Top 5 active
        except Exception as e:
            context["errors"].append(f"Could not restore tasks: {str(e)}")

        # ============================================================
        # Restore Recent Blockers
        # ============================================================
        try:
            blockers = graph_store.search_entities("blocker", entity_type="Decision")
            for blocker in blockers[:3]:  # Top 3 blockers
                context["recent_blockers"].append({
                    "name": blocker.name,
                    "description": blocker.metadata.get("description", "")
                })
        except Exception as e:
            context["errors"].append(f"Could not restore blockers: {str(e)}")

        # ============================================================
        # Cognitive Load Assessment
        # ============================================================
        try:
            high_priority_count = len([t for t in context["active_tasks"]
                                      if t.get("priority") in ["high", "critical"]])
            blocker_count = len(context["recent_blockers"])

            if high_priority_count >= 3 or blocker_count > 0:
                load_level = "high"
            elif high_priority_count >= 1:
                load_level = "medium"
            else:
                load_level = "low"

            context["cognitive_load"] = {
                "level": load_level,
                "high_priority_tasks": high_priority_count,
                "blocked_tasks": blocker_count
            }
        except Exception as e:
            context["errors"].append(f"Could not assess cognitive load: {str(e)}")

        # ============================================================
        # Generate Recommendations
        # ============================================================
        if context["cognitive_load"].get("level") == "high":
            context["recommendations"].append(
                "High cognitive load detected - focus on current tasks before adding new work"
            )

        if context["active_tasks"]:
            context["recommendations"].append(
                f"Continuing {len(context['active_tasks'])} in_progress task(s)"
            )

        if context["critical_goals"]:
            context["recommendations"].append(
                f"Working towards {len(context['critical_goals'])} active goal(s)"
            )

        context["restored"] = True

    except Exception as e:
        context["errors"].append(f"Critical error during restoration: {str(e)}")

    return context


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Restore critical context after compaction')
    parser.add_argument('--project', required=True, help='Project name')
    parser.add_argument('--cwd', required=True, help='Current working directory')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    # Restore context
    result = restore_context(
        project=args.project,
        cwd=args.cwd
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["restored"]:
            print(f"✅ Context Restored After Compaction")
            print(f"   Project: {result['project']}")
            print(f"   Goals: {len(result['critical_goals'])}")
            print(f"   Active tasks: {len(result['active_tasks'])}")
            print(f"   Cognitive load: {result['cognitive_load'].get('level', 'unknown').upper()}")

            if result["recommendations"]:
                print(f"\n   Recommendations:")
                for rec in result["recommendations"]:
                    print(f"   - {rec}")
        else:
            print(f"❌ Could not restore context")

        # Print JSON for hooks
        print(json.dumps(result))
