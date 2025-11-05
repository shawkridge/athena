#!/usr/bin/env python3
"""
Validate Plan Utility - Pre-validate goals and tasks before creation

Checks for conflicts, duplicates, and ensures plan coherence.
Provides validation warnings/errors before tool execution.

Usage:
    python3 validate_plan.py --tool <tool> --content <content> [--project <project>]
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


def validate_plan(
    tool_name: str,
    content: str,
    project: Optional[str] = None
) -> Dict[str, Any]:
    """Validate a plan element before creation."""

    result = {
        "success": True,
        "tool": tool_name,
        "valid": True,
        "warnings": [],
        "errors": [],
        "suggestions": [],
        "validation_details": {}
    }

    try:
        # Add memory-mcp to path if available
        athena_path = Path('/home/user/.work/athena/src')
        if athena_path.exists():
            sys.path.insert(0, str(athena_path))

        from athena.core.database import Database
        from athena.prospective.store import ProspectiveStore
        from athena.graph.store import GraphStore

        db_path = Path.home() / '/home/user/.work/athena' / 'memory.db'
        if not db_path.exists():
            result["warnings"].append("Memory database not found - skipping conflict check")
            return result

        db = Database(str(db_path))
        task_store = ProspectiveStore(db)
        graph_store = GraphStore(db)

        # Check what we're validating
        if tool_name == "set_goal":
            # Validate goal
            result["validation_details"]["type"] = "goal"

            # Check for similar existing goals
            similar_goals = graph_store.search_entities(content, entity_type="Decision")
            if similar_goals:
                result["warnings"].append(
                    f"Found {len(similar_goals)} similar goal(s) - ensure this is a new goal"
                )
                result["validation_details"]["similar_goals"] = len(similar_goals)

            # Check goal structure
            if len(content) < 10:
                result["errors"].append("Goal too short (min 10 chars)")
                result["valid"] = False
            elif len(content) > 500:
                result["warnings"].append("Goal description very long (>500 chars)")

        elif tool_name == "create_task":
            # Validate task
            result["validation_details"]["type"] = "task"

            # Check for duplicate tasks
            existing_tasks = task_store.list_tasks(limit=100)
            similar_tasks = [t for t in existing_tasks if content.lower() in t.content.lower()]
            if similar_tasks:
                result["warnings"].append(
                    f"Found {len(similar_tasks)} similar task(s) - check for duplicates"
                )
                result["validation_details"]["similar_tasks"] = len(similar_tasks)

            # Check task structure
            if len(content) < 5:
                result["errors"].append("Task too short (min 5 chars)")
                result["valid"] = False

            # Count active tasks
            active_tasks = [t for t in existing_tasks if t.status.value in ["pending", "in_progress"]]
            if len(active_tasks) >= 20:
                result["warnings"].append(
                    f"High task load ({len(active_tasks)} active) - prioritize existing tasks"
                )

        elif tool_name == "validate_plan":
            # Validate the plan tool itself
            result["validation_details"]["type"] = "plan_validation"
            result["suggestions"].append("Plan validation will check structure, feasibility, and rules")

        result["timestamp"] = datetime.now().isoformat()

    except Exception as e:
        result["warnings"].append(f"Validation check failed: {str(e)}")
        result["success"] = False

    return result


def format_validation_message(validation: Dict[str, Any]) -> str:
    """Format validation result as human-readable message."""
    msg = f"✓ Plan Element Validation\n"
    msg += f"  Tool: {validation['tool']}\n"

    if validation["valid"]:
        msg += f"  Status: ✅ Valid\n"
    else:
        msg += f"  Status: ❌ Invalid\n"

    if validation["errors"]:
        msg += f"\n  Errors:\n"
        for error in validation["errors"]:
            msg += f"    - {error}\n"

    if validation["warnings"]:
        msg += f"\n  Warnings:\n"
        for warning in validation["warnings"]:
            msg += f"    - {warning}\n"

    if validation["suggestions"]:
        msg += f"\n  Suggestions:\n"
        for suggestion in validation["suggestions"]:
            msg += f"    - {suggestion}\n"

    return msg


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Validate plan element before creation')
    parser.add_argument('--tool', required=True, help='Tool (set_goal, create_task, validate_plan)')
    parser.add_argument('--content', required=True, help='Goal/task content to validate')
    parser.add_argument('--project', help='Project context (optional)')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    # Validate
    result = validate_plan(
        tool_name=args.tool,
        content=args.content,
        project=args.project
    )

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        msg = format_validation_message(result)
        print(msg)
        # Also print JSON for hooks
        print(json.dumps(result))
