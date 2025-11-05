#!/usr/bin/env python3
"""
MCP Tool Caller - Execute MCP tools from hooks

Allows hooks to invoke MCP operations (like get_task_health, discover_patterns)
without requiring full MCP server setup.

Usage:
    call_mcp_tool.py --tool <tool_name> [options] --json

Example:
    call_mcp_tool.py --tool get_task_health --task_id 123 --json
    call_mcp_tool.py --tool discover_patterns --project_id 1 --json
"""

import sys
import json
import os
from pathlib import Path
from typing import Any, Dict

# Add hooks lib to path
sys.path.insert(0, str(Path.home() / ".claude" / "hooks" / "lib"))
sys.path.insert(0, "/home/user/.work/athena/src")

def get_mcp_tool_result(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Call an MCP tool and return the result"""
    try:
        from mcp_wrapper import MCPWrapper

        # Convert tool name to operation name format
        # e.g., "get_task_health" -> "get_task_health"
        operation_name = tool_name

        # Call via MCPWrapper with safe fallbacks
        result = MCPWrapper.safe_call(operation_name, **params)

        return {
            "success": True,
            "result": result,
            "tool": tool_name
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool": tool_name
        }

def main():
    """Parse arguments and call MCP tool"""
    import argparse

    parser = argparse.ArgumentParser(description="Call MCP tools from hooks")
    parser.add_argument("--tool", required=True, help="Tool name")
    parser.add_argument("--task_id", help="Task ID parameter")
    parser.add_argument("--project_id", help="Project ID parameter")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    # Build parameters dict
    params = {}
    if args.task_id:
        params["task_id"] = int(args.task_id)
    if args.project_id:
        params["project_id"] = int(args.project_id)

    # Get result
    result = get_mcp_tool_result(args.tool, params)

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Tool: {result['tool']}")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Result: {result['result']}")
        else:
            print(f"Error: {result['error']}")

    sys.exit(0 if result['success'] else 1)

if __name__ == "__main__":
    main()
