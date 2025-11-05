#!/usr/bin/env python3
"""
Context Loader Utility - Load real project context from MCP memory

Queries the MCP memory system and returns structured context:
- Active goals
- Top 3 in_progress tasks
- Recent blockers and decisions
- Cognitive load assessment
- Knowledge gaps

Usage:
    python3 context_loader.py --project <name> --cwd <path>
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any

def load_context(project_name: str, cwd: str) -> Dict[str, Any]:
    """Load complete project context from MCP memory."""

    context = {
        "project": project_name,
        "cwd": cwd,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "goals": [],
        "tasks": {"in_progress": [], "pending": [], "blocked": []},
        "blockers": [],
        "cognitive_load": {},
        "knowledge_gaps": [],
        "success": False,
        "errors": []
    }

    try:
        # Try to import and load memory
        db_path = Path.home() / '.athena' / 'memory.db'

        # Check if database exists
        if not db_path.exists():
            context["errors"].append("Memory database not found")
            return context

        # Add memory-mcp to path if available
        athena_path = Path('/home/user/.work/athena/src')
        if athena_path.exists():
            sys.path.insert(0, str(athena_path))

        # Import memory stores
        try:
            from athena.core.database import Database
            from athena.graph.store import GraphStore
            from athena.prospective.store import ProspectiveStore
            try:
                from athena.meta.store import MetaMemoryStore
                has_meta_store = True
            except ImportError:
                has_meta_store = False
        except ImportError as e:
            context["errors"].append(f"Cannot import athena: {str(e)}")
            return context

        # Initialize database and stores
        db = Database(str(db_path))
        kg_store = GraphStore(db)
        task_store = ProspectiveStore(db)

        # ============================================================
        # Load Active Goals (from active_goals table, primary source)
        # ============================================================
        try:
            cursor = db.conn.cursor()
            # First try to load from active_goals table (primary source)
            cursor.execute("""
                SELECT id, goal_text, priority, progress, status
                FROM active_goals
                ORDER BY priority DESC, created_at DESC
                LIMIT 10
            """)

            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    goal_id, goal_text, priority, progress, status = row
                    context["goals"].append({
                        "id": goal_id,
                        "name": goal_text,
                        "priority": priority or 5,
                        "description": f"Status: {status}, Progress: {progress or 0}%",
                        "progress": progress or 0
                    })

            # Fallback: also load Decision entities if active_goals table is empty
            if not context["goals"]:
                cursor.execute("""
                    SELECT id, name, metadata FROM entities
                    WHERE entity_type = 'Decision'
                    ORDER BY created_at DESC
                    LIMIT 10
                """)

                for row in cursor.fetchall():
                    entity_id, name, metadata_str = row
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                    except:
                        metadata = {}

                    context["goals"].append({
                        "id": entity_id,
                        "name": name,
                        "priority": metadata.get('priority', 5),
                        "description": metadata.get('description', '')
                    })

            # Keep top 5
            context["goals"] = context["goals"][:5]
        except Exception as e:
            context["errors"].append(f"Error loading goals: {str(e)}")

        # ============================================================
        # Load Tasks (from prospective_tasks table, primary source)
        # ============================================================
        try:
            cursor = db.conn.cursor()
            # First try prospective_tasks table (primary source)
            cursor.execute("""
                SELECT id, content, status, priority, created_at
                FROM prospective_tasks
                ORDER BY created_at DESC
                LIMIT 20
            """)

            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    task_id, content, status, priority, created_at = row
                    status = status or 'pending'
                    task_info = {
                        "id": task_id,
                        "content": content,
                        "status": status,
                        "priority": priority or 'medium',
                        "created_at": created_at
                    }

                    if status == 'in_progress':
                        context["tasks"]["in_progress"].append(task_info)
                    elif status == 'blocked':
                        context["tasks"]["blocked"].append(task_info)
                    else:
                        context["tasks"]["pending"].append(task_info)

            # Fallback: load Task entities if prospective_tasks is empty
            if not any(context["tasks"].values()):
                cursor.execute("""
                    SELECT id, name, metadata FROM entities
                    WHERE entity_type = 'Task'
                    ORDER BY created_at DESC
                    LIMIT 20
                """)

                for row in cursor.fetchall():
                    entity_id, name, metadata_str = row
                    try:
                        metadata = json.loads(metadata_str) if metadata_str else {}
                    except:
                        metadata = {}

                    status = metadata.get('status', 'pending')
                    task_info = {
                        "id": entity_id,
                        "content": name,
                        "status": status,
                        "priority": metadata.get('priority', 'medium'),
                        "description": metadata.get('description', '')
                    }

                    if status == 'in_progress':
                        context["tasks"]["in_progress"].append(task_info)
                    elif status == 'blocked':
                        context["tasks"]["blocked"].append(task_info)
                    else:
                        context["tasks"]["pending"].append(task_info)

            # Keep only top 3 for each category
            context["tasks"]["in_progress"] = context["tasks"]["in_progress"][:3]
            context["tasks"]["pending"] = context["tasks"]["pending"][:3]
            context["tasks"]["blocked"] = context["tasks"]["blocked"][:3]

        except Exception as e:
            context["errors"].append(f"Error loading tasks: {str(e)}")

        # ============================================================
        # Load Blockers (Task entities in blocked status)
        # ============================================================
        try:
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT id, name, metadata FROM entities
                WHERE entity_type = 'Task'
                ORDER BY created_at DESC
                LIMIT 5
            """)

            for row in cursor.fetchall():
                entity_id, name, metadata_str = row
                try:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                except:
                    metadata = {}

                # Only include if status is 'blocked' or if no status (consider as potential blocker)
                status = metadata.get('status', 'pending')
                if status == 'blocked':
                    context["blockers"].append({
                        "id": entity_id,
                        "name": name,
                        "description": metadata.get('description', ''),
                        "reason": metadata.get('reason', 'Unknown')
                    })
        except Exception as e:
            context["errors"].append(f"Error loading blockers: {str(e)}")

        # ============================================================
        # Cognitive Load Assessment
        # ============================================================
        try:
            # Simple heuristic: based on task count and priorities
            high_priority_tasks = len([t for t in context["tasks"]["in_progress"]
                                      if t.get("priority") in ["high", "critical"]])
            blocked_count = len(context["tasks"]["blocked"])

            if high_priority_tasks >= 3 or blocked_count > 0:
                load_level = "high"
            elif high_priority_tasks >= 1:
                load_level = "medium"
            else:
                load_level = "low"

            context["cognitive_load"] = {
                "level": load_level,
                "high_priority_tasks": high_priority_tasks,
                "blocked_tasks": blocked_count,
                "recommendation": _get_load_recommendation(load_level)
            }
        except Exception as e:
            context["errors"].append(f"Error assessing cognitive load: {str(e)}")

        # ============================================================
        # Knowledge Gaps
        # ============================================================
        try:
            # Try to detect gaps (if MetaMemoryStore available)
            try:
                meta_store = MetaMemoryStore(db)
                gaps = meta_store.detect_gaps()
                for gap in gaps[:3]:  # Top 3 gaps
                    context["knowledge_gaps"].append({
                        "area": gap.get('domain', ''),
                        "severity": gap.get('severity', 'medium')
                    })
            except:
                # MetaMemoryStore might not be available, that's okay
                pass
        except Exception as e:
            context["errors"].append(f"Error detecting knowledge gaps: {str(e)}")

        context["success"] = True

    except Exception as e:
        context["errors"].append(f"Unexpected error: {str(e)}")

    return context


def _get_load_recommendation(load_level: str) -> str:
    """Get recommendation based on cognitive load."""
    recommendations = {
        "high": "High cognitive load detected. Consider breaking work into smaller chunks.",
        "medium": "Moderate cognitive load. You have capacity for focused work.",
        "low": "Low cognitive load. Good opportunity for complex tasks."
    }
    return recommendations.get(load_level, "")


def format_context_message(context: Dict[str, Any]) -> str:
    """Format context as human-readable message."""

    msg = f"""
═══════════════════════════════════════════════════════════
PROJECT CONTEXT LOADED: {context['project']}
═══════════════════════════════════════════════════════════

🎯 ACTIVE GOALS ({len(context['goals'])} total)
"""

    for i, goal in enumerate(context['goals'][:3], 1):
        msg += f"{i}. {goal['name']} (Priority: {goal['priority']}/10)\n"

    msg += f"""
📋 TASKS STATUS
   In Progress: {len(context['tasks']['in_progress'])} | Pending: {len(context['tasks']['pending'])} | Blocked: {len(context['tasks']['blocked'])}
"""

    if context['tasks']['in_progress']:
        msg += "\n   🟢 Currently Working On:\n"
        for task in context['tasks']['in_progress'][:3]:
            msg += f"      • {task['content']}\n"

    if context['tasks']['blocked']:
        msg += "\n   🔴 Blocked Tasks:\n"
        for task in context['tasks']['blocked'][:3]:
            msg += f"      • {task['content']}\n"

    msg += f"""
⚡ COGNITIVE LOAD: {context['cognitive_load'].get('level', 'unknown').upper()}
   {context['cognitive_load'].get('recommendation', '')}

"""

    if context['knowledge_gaps']:
        msg += f"❓ KNOWLEDGE GAPS DETECTED:\n"
        for gap in context['knowledge_gaps']:
            msg += f"   • {gap['area']} (severity: {gap['severity']})\n"

    msg += f"""
═══════════════════════════════════════════════════════════
Ready to work with full context loaded!
═══════════════════════════════════════════════════════════
"""

    return msg


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Load project context from MCP memory')
    parser.add_argument('--project', required=True, help='Project name')
    parser.add_argument('--cwd', required=True, help='Current working directory')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of formatted text')

    args = parser.parse_args()

    # Load context
    context = load_context(args.project, args.cwd)

    # Output
    if args.json:
        print(json.dumps(context, indent=2))
    else:
        # Print formatted message first
        message = format_context_message(context)
        print(message)

        # Then print JSON to stderr for hook to parse
        sys.stderr.write(json.dumps(context) + '\n')
