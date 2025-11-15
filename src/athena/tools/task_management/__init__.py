"""Phase 3a Task Management Tools - Filesystem Discoverable.

Agents can discover and use these tools by exploring the filesystem.

Available tools:
- create_dependency: Create task blocking relationship
- check_task_blocked: Check if a task is blocked
- get_unblocked_tasks: Get tasks ready to work on
- set_task_metadata: Set effort, complexity, tags
- record_task_effort: Record actual effort spent
- get_task_metadata: Get full task metadata
- get_project_analytics: Get project-wide analytics

Usage:
    1. Discover tools: ls /athena/tools/task_management/
    2. Read tool definition: cat /athena/tools/task_management/create_dependency.py
    3. Use the tool (see tool file for import path)
"""
