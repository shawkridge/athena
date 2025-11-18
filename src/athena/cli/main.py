#!/usr/bin/env python3
"""Athena CLI - Command-line interface for slash commands.

Implements Anthropic's code-execution-with-MCP pattern:
- Discover operations
- Execute locally
- Return summaries (300 tokens max)

Usage:
    python3 -m athena.cli memory-search "query" [--limit 5] [--offset 0] [--json]
    python3 -m athena.cli plan-task "task description" [--levels 3] [--json]
    python3 -m athena.cli validate-plan "plan" [--json]
    python3 -m athena.cli session-start [--project /path] [--json]
    python3 -m athena.cli manage-goal create "goal name" [--details] [--json]
"""

import sys
import json
import argparse
import logging
from typing import Any, Dict

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Import commands
from .commands import (
    MemorySearchCommand,
    PlanTaskCommand,
    ValidatePlanCommand,
    SessionStartCommand,
    ManageGoalCommand,
)


def format_output(result: Dict[str, Any], json_output: bool = False) -> str:
    """Format command result for display."""
    if json_output:
        return json.dumps(result, indent=2, default=str)
    else:
        # Pretty print for terminal
        output = []
        output.append(f"Status: {result.get('status', 'unknown')}")

        if result.get("status") == "success":
            # Show key results
            for key, value in result.items():
                if key not in ["status", "execution_time_ms"] and not isinstance(
                    value, (dict, list)
                ):
                    output.append(f"{key}: {value}")

        if result.get("error"):
            output.append(f"Error: {result['error']}")

        output.append(f"\nExecution time: {result.get('execution_time_ms', 0)}ms")
        return "\n".join(output)


def cmd_memory_search(args: argparse.Namespace) -> int:
    """Handle memory-search command."""
    try:
        with MemorySearchCommand() as cmd:
            result = cmd.execute(
                query=args.query,
                limit=args.limit,
                offset=args.offset,
            )

        output = format_output(result, args.json)
        print(output)
        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"memory-search failed: {e}")
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 1


def cmd_plan_task(args: argparse.Namespace) -> int:
    """Handle plan-task command."""
    try:
        with PlanTaskCommand() as cmd:
            result = cmd.execute(
                task_description=args.task,
                levels=args.levels,
                strategy=args.strategy,
            )

        output = format_output(result, args.json)
        print(output)
        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"plan-task failed: {e}")
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 1


def cmd_validate_plan(args: argparse.Namespace) -> int:
    """Handle validate-plan command."""
    try:
        with ValidatePlanCommand() as cmd:
            result = cmd.execute(
                plan_description=args.plan,
                include_scenarios=args.scenarios,
            )

        output = format_output(result, args.json)
        print(output)
        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"validate-plan failed: {e}")
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 1


def cmd_session_start(args: argparse.Namespace) -> int:
    """Handle session-start command."""
    try:
        with SessionStartCommand() as cmd:
            result = cmd.execute(project_path=args.project)

        output = format_output(result, args.json)
        print(output)
        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"session-start failed: {e}")
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 1


def cmd_manage_goal(args: argparse.Namespace) -> int:
    """Handle manage-goal command."""
    try:
        with ManageGoalCommand() as cmd:
            result = cmd.execute(
                action=args.action,
                goal_name=args.name,
                goal_details=args.details,
            )

        output = format_output(result, args.json)
        print(output)
        return 0 if result.get("status") == "success" else 1

    except Exception as e:
        logger.error(f"manage-goal failed: {e}")
        print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Athena memory system CLI - slash command implementations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search memory
  python3 -m athena.cli memory-search "hooks validation"

  # Plan task
  python3 -m athena.cli plan-task "implement context injection" --levels 3

  # Validate plan
  python3 -m athena.cli validate-plan "my plan here"

  # Session start
  python3 -m athena.cli session-start

  # Manage goals
  python3 -m athena.cli manage-goal list
  python3 -m athena.cli manage-goal create "implement slash commands"
        """,
    )

    # Global options
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (for script consumption)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # memory-search command
    memory_search_parser = subparsers.add_parser(
        "memory-search",
        help="Search episodic and semantic memory",
    )
    memory_search_parser.add_argument("query", help="Search query")
    memory_search_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum results (default: 5)",
    )
    memory_search_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Result offset for pagination (default: 0)",
    )
    memory_search_parser.set_defaults(func=cmd_memory_search)

    # plan-task command
    plan_task_parser = subparsers.add_parser(
        "plan-task",
        help="Decompose task into steps",
    )
    plan_task_parser.add_argument("task", help="Task description")
    plan_task_parser.add_argument(
        "--levels",
        type=int,
        default=3,
        help="Decomposition levels (default: 3)",
    )
    plan_task_parser.add_argument(
        "--strategy",
        help="Decomposition strategy",
    )
    plan_task_parser.set_defaults(func=cmd_plan_task)

    # validate-plan command
    validate_plan_parser = subparsers.add_parser(
        "validate-plan",
        help="Validate plan feasibility",
    )
    validate_plan_parser.add_argument("plan", help="Plan description")
    validate_plan_parser.add_argument(
        "--scenarios",
        action="store_true",
        help="Include scenario analysis",
    )
    validate_plan_parser.set_defaults(func=cmd_validate_plan)

    # session-start command
    session_start_parser = subparsers.add_parser(
        "session-start",
        help="Initialize session context",
    )
    session_start_parser.add_argument(
        "--project",
        help="Project path (default: current directory)",
    )
    session_start_parser.set_defaults(func=cmd_session_start)

    # manage-goal command
    manage_goal_parser = subparsers.add_parser(
        "manage-goal",
        help="Manage project goals",
    )
    manage_goal_parser.add_argument(
        "action",
        choices=["list", "create", "update", "complete"],
        help="Goal action",
    )
    manage_goal_parser.add_argument(
        "--name",
        help="Goal name",
    )
    manage_goal_parser.add_argument(
        "--details",
        help="Goal details/description",
    )
    manage_goal_parser.set_defaults(func=cmd_manage_goal)

    # Parse arguments
    args = parser.parse_args()

    # Enable debug logging if requested
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # Execute command
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
