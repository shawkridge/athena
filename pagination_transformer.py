#!/usr/bin/env python3
"""
Pagination Transformer - Generates transformation patches for MCP handlers.

This script analyzes handlers that return lists and generates the code changes
needed to add pagination using the Anthropic pattern.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Handlers to update per file
HANDLERS_TO_UPDATE = {
    "src/athena/mcp/handlers_planning.py": [
        "_handle_decompose_hierarchically",
        "_handle_validate_plan",
        "_handle_recommend_orchestration",
        "_handle_verify_plan",
        "_handle_research_task",
        "_handle_research_findings",
        "_handle_analyze_estimation_accuracy",
        "_handle_optimize_plan",
        "_handle_analyze_critical_path",
        "_handle_detect_resource_conflicts",
        "_handle_list_rules",
        "_handle_validate_task_against_rules",
        "_handle_get_suggestions",
        "_handle_score_semantic_memories",
        "_handle_get_memory_quality_summary",
    ],
    "src/athena/mcp/handlers_prospective.py": [
        "_handle_list_tasks",
        "_handle_get_active_goals",
    ],
    "src/athena/mcp/handlers_episodic.py": [
        "_handle_recall_events",
        "_handle_recall_events_by_context",
        "_handle_recall_events_by_session",
        "_handle_recall_events_by_tool_usage",
        "_handle_recall_episodic_events",
    ],
    "src/athena/mcp/handlers_procedural.py": [
        "_handle_get_procedure_effectiveness",
        "_handle_find_procedures",
        "_handle_list_procedure_versions",
    ],
    "src/athena/mcp/handlers_metacognition.py": [
        "_handle_get_expertise",
        "_handle_smart_retrieve",
        "_handle_get_working_memory",
        "_handle_detect_knowledge_gaps",
    ],
    "src/athena/mcp/handlers_graph.py": [
        "_handle_search_graph",
        "_handle_search_graph_with_depth",
    ],
    "src/athena/mcp/handlers_consolidation.py": [
        "_handle_consolidate_working_memory",
    ],
}


def extract_handler_body(content: str, handler_name: str) -> Tuple[str, int, int]:
    """Extract handler method body and its position."""
    pattern = rf'(async def {re.escape(handler_name)}\(self, args: dict\) -> list\[TextContent\]:.*?)(\n    async def |\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return None, -1, -1

    handler_body = match.group(1)
    start_pos = match.start(1)
    end_pos = match.end(1)

    return handler_body, start_pos, end_pos


def generate_pagination_code(handler_name: str, handler_body: str) -> str:
    """Generate pagination transformation for a handler.

    This generates a template that needs to be manually adapted per handler.
    """
    # Extract handler operation name
    operation = handler_name.replace("_handle_", "")

    # Generate template
    template = f'''
# PAGINATION TRANSFORMATION FOR: {handler_name}
# Operation: {operation}

# ADD THESE LINES after fetching results (before formatting):
# ----------------------------------------------------------------
limit = min(args.get("limit", 10), 100)
offset = args.get("offset", 0)

# Modify your database/store query to use limit/offset:
# Example: results = store.list_items(limit=limit, offset=offset)

# Get total count (add separate COUNT query):
# total_count = store.count_items(filters...)

# REPLACE THE RETURN STATEMENT:
# OLD: return [TextContent(type="text", text=json.dumps(result))]
# NEW:
return [paginate_results(
    results=items,  # Replace 'items' with your result list
    args=args,
    total_count=total_count,  # From COUNT query
    operation="{operation}",
    drill_down_hint="Use /{operation}_detail with ID for full details"
).as_optimized_content(schema_name="your_schema")]
# ----------------------------------------------------------------

'''
    return template


def analyze_file(filepath: str) -> Dict[str, str]:
    """Analyze a file and generate pagination patches."""
    path = Path(filepath)

    if not path.exists():
        print(f"ERROR: File not found: {filepath}")
        return {}

    with open(path, 'r') as f:
        content = f.read()

    handler_names = HANDLERS_TO_UPDATE.get(filepath, [])

    patches = {}

    for handler_name in handler_names:
        handler_body, start, end = extract_handler_body(content, handler_name)

        if not handler_body:
            patches[handler_name] = f"ERROR: Handler not found in file"
            continue

        # Generate transformation template
        patch = generate_pagination_code(handler_name, handler_body)
        patches[handler_name] = patch

    return patches


def main():
    """Generate pagination transformation patches for all handlers."""
    print("="*70)
    print("PAGINATION TRANSFORMATION GENERATOR")
    print("="*70)
    print()
    print("This script generates transformation templates for adding pagination")
    print("to MCP handlers. Each template needs manual adaptation based on the")
    print("handler's specific data source and return pattern.")
    print()

    all_patches = {}

    for filepath in HANDLERS_TO_UPDATE.keys():
        print(f"\n{'='*70}")
        print(f"Analyzing: {filepath}")
        print('='*70)

        patches = analyze_file(filepath)
        all_patches[filepath] = patches

        for handler_name, patch in patches.items():
            if patch.startswith("ERROR"):
                print(f"\n✗ {handler_name}: {patch}")
            else:
                print(f"\n✓ {handler_name}: Template generated")

    # Write patches to output file
    output_file = "pagination_patches.txt"
    with open(output_file, 'w') as f:
        f.write("PAGINATION TRANSFORMATION PATCHES\n")
        f.write("="*70 + "\n\n")
        f.write("Instructions:\n")
        f.write("1. For each handler, locate the section marked in the code\n")
        f.write("2. Add limit/offset parameter parsing\n")
        f.write("3. Modify database queries to use limit/offset\n")
        f.write("4. Add COUNT query for total_count\n")
        f.write("5. Replace return statement with paginate_results()\n\n")

        for filepath, patches in all_patches.items():
            f.write(f"\n\n{'='*70}\n")
            f.write(f"FILE: {filepath}\n")
            f.write('='*70 + "\n")

            for handler_name, patch in patches.items():
                f.write(f"\n{patch}\n")

    print(f"\n\n{'='*70}")
    print(f"✓ Transformation patches written to: {output_file}")
    print(f"✓ Total handlers: {sum(len(p) for p in all_patches.values())}")
    print('='*70)


if __name__ == "__main__":
    main()
