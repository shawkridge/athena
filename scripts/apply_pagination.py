#!/usr/bin/env python3
"""
Automated Pagination Implementation Script

This script automatically applies the TIER 1 pagination pattern to all handlers
that return lists of items. It intelligently detects SQL queries, adds LIMIT/OFFSET,
creates COUNT queries, and wraps results with paginate_results().

Usage:
    python scripts/apply_pagination.py --dry-run          # Preview changes
    python scripts/apply_pagination.py --tier 2           # Apply to TIER 2 only
    python scripts/apply_pagination.py --file FILE        # Apply to specific file
    python scripts/apply_pagination.py --all              # Apply to all handlers
    python scripts/apply_pagination.py --validate         # Validate syntax only

Author: Claude Code
Date: November 13, 2025
"""

import re
import sys
import argparse
import ast
from pathlib import Path
from typing import List, Tuple, Optional
import shutil

# Handler file paths
SRC_PATH = Path("/home/user/.work/athena/src/athena/mcp")
HANDLER_FILES = [
    "handlers_episodic.py",
    "handlers_prospective.py",
    "handlers_procedural.py",
    "handlers_planning.py",
    "handlers_graph.py",
    "handlers_metacognition.py",
    "handlers_consolidation.py",
]

# TIER 2 handlers (core list operations - highest priority)
TIER2_HANDLERS = {
    "handlers_episodic.py": [
        "_handle_recall_events_by_context",
        "_handle_recall_events_by_session",
        "_handle_recall_episodic_events",
        "_handle_timeline_query",
        "_handle_trace_consolidation",
        "_handle_temporal_chain_events",
    ],
    "handlers_prospective.py": [
        "_handle_list_active_tasks",
        "_handle_list_overdue_tasks",
        "_handle_list_completed_tasks",
        "_handle_list_goals",
        "_handle_list_milestones",
        "_handle_list_triggers",
        "_handle_list_recurring_tasks",
        "_handle_get_task_dependencies",
    ],
    "handlers_procedural.py": [
        "_handle_list_procedure_versions",
        "_handle_list_similar_procedures",
        "_handle_list_procedure_executions",
        "_handle_search_procedures",
        "_handle_list_workflows",
        "_handle_list_procedure_templates",
    ],
    "handlers_graph.py": [
        "_handle_list_relations",
        "_handle_search_graph_with_depth",
        "_handle_detect_graph_communities",
        "_handle_expand_knowledge_relations",
    ],
    "handlers_planning.py": [
        "_handle_decompose_hierarchically",
        "_handle_list_validation_rules",
        "_handle_list_decomposition_strategies",
        "_handle_list_orchestrator_patterns",
        "_handle_research_findings",
        "_handle_list_planning_history",
        "_handle_list_scenarios",
        "_handle_list_assumptions",
        "_handle_list_risks",
        "_handle_list_dependencies",
    ],
    "handlers_metacognition.py": [
        "_handle_list_domains",
        "_handle_list_learning_gaps",
        "_handle_list_attention_priorities",
        "_handle_list_inhibited_memories",
        "_handle_list_associations",
        "_handle_list_working_memory_items",
    ],
}


class PaginationInjector:
    """Injects pagination into handler methods."""

    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            "files_processed": 0,
            "handlers_modified": 0,
            "handlers_skipped": 0,
            "syntax_errors": 0,
        }

    def log(self, message: str, level="INFO"):
        """Log a message."""
        if self.verbose or level != "DEBUG":
            prefix = "  " if level == "DEBUG" else ""
            print(f"{prefix}{level}: {message}")

    def is_paginated(self, handler_code: str) -> bool:
        """Check if handler already has pagination."""
        return (
            "paginate_results(" in handler_code
            or 'limit = min(args.get("limit"' in handler_code
        )

    def extract_handler(self, content: str, handler_name: str) -> Optional[Tuple[str, int, int]]:
        """Extract handler code and its position."""
        pattern = rf"(async def {handler_name}\(self, args: dict\) -> list\[TextContent\]:.*?)(?=\n    async def |\n\nclass |\Z)"
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            return None

        handler_code = match.group(1)
        start_pos = match.start()
        end_pos = match.end()

        return handler_code, start_pos, end_pos

    def inject_pagination(self, handler_code: str, handler_name: str) -> str:
        """Inject pagination into handler code."""

        # Step 1: Add limit/offset parsing at the top of try block
        try_pattern = r"(try:\s+)"
        limit_code = r"\1# Pagination\n        limit = min(args.get(\"limit\", 10), 100)\n        offset = args.get(\"offset\", 0)\n\n        "

        modified_code = re.sub(try_pattern, limit_code, handler_code, count=1)

        # Step 2: Detect and modify SQL queries
        # Find SELECT queries
        select_pattern = r'(sql\s*=\s*"""[\s\S]*?SELECT\s+.*?FROM\s+\w+)(.*?)(ORDER BY.*?)(""")(\s*cursor\.execute\(sql,\s*\((.*?)\)\))'

        def add_limit_offset(match):
            select_clause = match.group(1)
            where_clause = match.group(2)
            order_clause = match.group(3)
            closing = match.group(4)
            execute_line = match.group(5)
            params = match.group(6)

            # Add COUNT query
            count_sql = f"""
        # Get total count for pagination
        count_sql = \"\"\"
{select_clause.replace('SELECT *', 'SELECT COUNT(*)')}
{where_clause}
        \"\"\"
        cursor = self.database.conn.cursor()
        cursor.execute(count_sql, ({params}))
        total_count = cursor.fetchone()[0]

        # Get paginated results
"""

            # Modify original query to add LIMIT/OFFSET
            paginated_sql = f'{select_clause}{where_clause}{order_clause}\n        LIMIT ? OFFSET ?\n        {closing}'

            # Update execute params
            new_params = f"{params}, limit, offset" if params else "limit, offset"
            new_execute = f'\n        cursor.execute(sql, ({new_params}))'

            return count_sql + "        sql = " + paginated_sql + new_execute

        modified_code = re.sub(select_pattern, add_limit_offset, modified_code)

        # Step 3: Wrap return statement with paginate_results
        # Find the last return statement (usually at the end)
        return_pattern = r'return \[TextContent\(type="text", text=json\.dumps\((.*?), indent=2\)\)\]'

        def wrap_with_pagination(match):
            response_var = match.group(1)

            # Extract results from response
            # Assuming response is a dict with results list
            wrapper = f"""# Format for pagination
        formatted_results = {response_var}.get("results", []) if isinstance({response_var}, dict) else []
        total = {response_var}.get("total", len(formatted_results)) if isinstance({response_var}, dict) else len(formatted_results)

        return paginate_results(
            results=formatted_results,
            args=args,
            total_count=total if 'total_count' not in locals() else total_count,
            operation="{handler_name.replace('_handle_', '')}",
            drill_down_hint="Use specific retrieval operation for full details"
        ).as_text_content()"""

            return wrapper

        # Try to wrap return statement
        if 'return [TextContent(type="text", text=json.dumps(' in modified_code:
            modified_code = re.sub(return_pattern, wrap_with_pagination, modified_code)

        return modified_code

    def validate_syntax(self, code: str) -> bool:
        """Validate Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.log(f"Syntax error: {e}", "ERROR")
            return False

    def process_file(
        self, file_path: Path, handlers: Optional[List[str]] = None
    ) -> int:
        """Process a single file."""
        self.log(f"\nProcessing {file_path.name}...")

        if not file_path.exists():
            self.log(f"File not found: {file_path}", "ERROR")
            return 0

        content = file_path.read_text()
        original_content = content
        modified_count = 0

        # If no handlers specified, process all handlers in file
        if handlers is None:
            handlers = re.findall(r"async def (_handle_\w+)\(", content)

        for handler_name in handlers:
            self.log(f"Processing {handler_name}...", "DEBUG")

            # Extract handler
            result = self.extract_handler(content, handler_name)
            if not result:
                self.log(f"Handler not found: {handler_name}", "WARNING")
                continue

            handler_code, start_pos, end_pos = result

            # Check if already paginated
            if self.is_paginated(handler_code):
                self.log(f"Already paginated: {handler_name}", "DEBUG")
                self.stats["handlers_skipped"] += 1
                continue

            # Inject pagination
            modified_handler = self.inject_pagination(handler_code, handler_name)

            # Validate syntax
            if not self.validate_syntax(modified_handler):
                self.log(f"Syntax error in modified handler: {handler_name}", "ERROR")
                self.stats["syntax_errors"] += 1
                continue

            # Replace handler in content
            content = content[:start_pos] + modified_handler + content[end_pos:]
            modified_count += 1
            self.stats["handlers_modified"] += 1
            self.log(f"✓ Injected pagination: {handler_name}")

        # Write modified content
        if modified_count > 0 and not self.dry_run:
            # Backup original file
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy2(file_path, backup_path)
            self.log(f"Backup created: {backup_path.name}", "DEBUG")

            # Write modified content
            file_path.write_text(content)
            self.log(f"✓ Modified {modified_count} handlers in {file_path.name}")
        elif modified_count > 0:
            self.log(f"[DRY RUN] Would modify {modified_count} handlers in {file_path.name}")

        self.stats["files_processed"] += 1
        return modified_count

    def process_tier(self, tier: int):
        """Process handlers for a specific tier."""
        if tier == 2:
            handlers_dict = TIER2_HANDLERS
            self.log(f"\n{'='*80}\nProcessing TIER 2: Core List Operations (40 handlers)\n{'='*80}")
        else:
            self.log(f"TIER {tier} not yet defined", "ERROR")
            return

        for filename, handlers in handlers_dict.items():
            file_path = SRC_PATH / filename
            self.process_file(file_path, handlers)

    def print_stats(self):
        """Print execution statistics."""
        print(f"\n{'='*80}")
        print("PAGINATION INJECTION SUMMARY")
        print(f"{'='*80}")
        print(f"Files Processed: {self.stats['files_processed']}")
        print(f"Handlers Modified: {self.stats['handlers_modified']}")
        print(f"Handlers Skipped (already paginated): {self.stats['handlers_skipped']}")
        print(f"Syntax Errors: {self.stats['syntax_errors']}")
        print(f"{'='*80}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated Pagination Implementation Script"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--tier",
        type=int,
        choices=[2, 3, 4],
        help="Apply to specific tier only",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Apply to specific file only",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Apply to all handlers",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate syntax only",
    )

    args = parser.parse_args()

    injector = PaginationInjector(dry_run=args.dry_run, verbose=args.verbose)

    if args.validate:
        print("Validation mode - checking syntax of existing files...")
        for filename in HANDLER_FILES:
            file_path = SRC_PATH / filename
            if file_path.exists():
                content = file_path.read_text()
                if injector.validate_syntax(content):
                    print(f"✓ {filename}: Syntax valid")
                else:
                    print(f"✗ {filename}: Syntax errors")
        return 0

    if args.file:
        file_path = SRC_PATH / args.file
        injector.process_file(file_path)
    elif args.tier:
        injector.process_tier(args.tier)
    elif args.all:
        for filename in HANDLER_FILES:
            file_path = SRC_PATH / filename
            injector.process_file(file_path)
    else:
        parser.print_help()
        return 1

    injector.print_stats()
    return 0


if __name__ == "__main__":
    sys.exit(main())
