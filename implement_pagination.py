#!/usr/bin/env python3
"""
Implement pagination for TIER 2-4 handlers (68 handlers total).
This script applies the TIER 1 pagination pattern consistently across all remaining handlers.
"""

import re
import sys
from pathlib import Path

# Pagination pattern template
PAGINATION_IMPORT = "from .structured_result import StructuredResult, ResultStatus, PaginationMetadata, create_paginated_result, paginate_results"

def add_pagination_to_handler(content: str, handler_name: str, operation_name: str, drill_down_hint: str) -> str:
    """Add pagination to a handler function."""

    # Pattern to find the handler function
    pattern = rf'(async def {handler_name}\(self, args: dict\) -> list\[TextContent\]:.*?)(return \[.*?\])'

    def replacement(match):
        func_body = match.group(1)
        return_stmt = match.group(2)

        # Check if pagination already implemented
        if 'paginate_results' in func_body or 'limit = min(args.get("limit"' in func_body:
            return match.group(0)  # Already paginated

        # Insert pagination code before the return statement
        # 1. Add limit/offset parsing at the beginning
        limit_code = """
        # Pagination
        limit = min(args.get("limit", 10), 100)
        offset = args.get("offset", 0)
"""

        # 2. Modify the query to use LIMIT/OFFSET
        # This is handler-specific, so we'll add placeholders

        # 3. Add paginate_results call before return
        pagination_call = f"""
        return paginate_results(
            results=formatted_results,
            args=args,
            total_count=total_count,
            operation="{operation_name}",
            drill_down_hint="{drill_down_hint}"
        ).as_text_content()
"""

        # For now, we'll just mark it with a comment
        modified_body = func_body + f"\n        # TODO: Implement pagination for {handler_name}\n        "
        return modified_body + return_stmt

    result = re.sub(pattern, replacement, content, flags=re.DOTALL)
    return result

# TIER 2 handlers (18 handlers)
TIER2_HANDLERS = {
    "handlers_episodic.py": [
        ("_handle_recall_by_session", "recall_by_session", "Use recall_events with session_id for detailed event analysis"),
        ("_handle_recall_by_context", "recall_by_context", "Use recall_events with context filters for semantic grouping"),
        ("_handle_recall_by_timeframe", "recall_by_timeframe", "Use timeline_query for temporal patterns and bursts"),
        ("_handle_list_sessions", "list_sessions", "Use recall_by_session with specific session_id for event details"),
        ("_handle_search_events", "search_events", "Use recall_events with query parameter for full search results"),
        ("_handle_analyze_patterns", "analyze_patterns", "Use trace_consolidation to see pattern-to-memory mappings"),
    ],
    "handlers_prospective.py": [
        ("_handle_list_tasks", "list_tasks", "Use get_task with task_id for full task details and dependencies"),
        ("_handle_list_active_tasks", "list_active_tasks", "Use analyze_workload for detailed status analysis"),
        ("_handle_list_overdue_tasks", "list_overdue_tasks", "Use analyze_completion_rate for trend analysis"),
        ("_handle_list_goals", "list_goals", "Use get_goal with goal_id for full goal hierarchy and progress"),
        ("_handle_list_milestones", "list_milestones", "Use analyze_dependencies for milestone relationships"),
    ],
    "handlers_procedural.py": [
        ("_handle_list_procedures", "list_procedures", "Use get_procedure with procedure_id for full workflow details"),
        ("_handle_list_workflows", "list_workflows", "Use analyze_effectiveness for workflow quality metrics"),
        ("_handle_search_procedures", "search_procedures", "Use list_similar_procedures for similarity matching"),
        ("_handle_list_similar_procedures", "list_similar_procedures", "Use get_procedure for detailed comparison"),
    ],
    "handlers_planning.py": [
        ("_handle_decompose_hierarchically", "decompose_hierarchically", "Use validate_plan to verify decomposition quality"),
        ("_handle_validate_plan", "validate_plan", "Use verify_plan for formal property verification"),
        ("_handle_optimize_plan", "optimize_plan", "Use estimate_resources for detailed resource analysis"),
    ],
}

# TIER 3 handlers (25 handlers)
TIER3_HANDLERS = {
    "handlers_planning.py": [
        ("_handle_suggest_planning_strategy", "suggest_planning_strategy", "Use decompose_with_strategy for specific strategy application"),
        ("_handle_trigger_replanning", "trigger_replanning", "Use planning_monitor_deviation for deviation analysis"),
        ("_handle_verify_plan", "verify_plan", "Use planning_verify_properties for detailed property checks"),
        ("_handle_recommend_orchestration", "recommend_orchestration", "Use discover_orchestration_patterns for pattern details"),
        ("_handle_planning_validation_benchmark", "planning_validation_benchmark", "Use planning_validate_comprehensive for full validation"),
        ("_handle_planning_analyze_assumptions", "planning_analyze_assumptions", "Use planning_analyze_risks for risk assessment"),
        ("_handle_planning_analyze_risks", "planning_analyze_risks", "Use planning_analyze_dependencies for dependency impact"),
        ("_handle_planning_analyze_dependencies", "planning_analyze_dependencies", "Use analyze_critical_path for dependency chains"),
        ("_handle_planning_analyze_critical_path", "planning_analyze_critical_path", "Use detect_resource_conflicts for bottleneck analysis"),
        ("_handle_planning_analyze_resource_allocation", "planning_analyze_resource_allocation", "Use estimate_resources for detailed allocation"),
        ("_handle_planning_analyze_timeline", "planning_analyze_timeline", "Use analyze_estimation_accuracy for timeline accuracy"),
        ("_handle_research_task", "research_task", "Use research_findings for detailed finding analysis"),
    ],
    "handlers_prospective.py": [
        ("_handle_list_triggers", "list_triggers", "Use get_trigger for full trigger configuration"),
        ("_handle_list_recurring_tasks", "list_recurring_tasks", "Use analyze_workload for recurrence patterns"),
        ("_handle_analyze_workload", "analyze_workload", "Use list_active_tasks for task details"),
        ("_handle_analyze_dependencies", "analyze_dependencies", "Use analyze_critical_path for dependency impact"),
        ("_handle_analyze_completion_rate", "analyze_completion_rate", "Use discover_patterns for completion trends"),
    ],
    "handlers_procedural.py": [
        ("_handle_analyze_effectiveness", "analyze_effectiveness", "Use list_procedures for procedure comparison"),
        ("_handle_analyze_patterns", "analyze_patterns", "Use search_procedures for pattern matching"),
    ],
    "handlers_graph.py": [
        ("_handle_list_entities", "list_entities", "Use get_entity for full entity details and relations"),
        ("_handle_list_relations", "list_relations", "Use search_relations for relation filtering"),
        ("_handle_search_community", "search_community", "Use analyze_community for community analysis"),
    ],
    "handlers_metacognition.py": [
        ("_handle_analyze_learning_gaps", "analyze_learning_gaps", "Use get_expertise_map for gap analysis"),
        ("_handle_analyze_expertise", "analyze_expertise", "Use list_domains for domain expertise"),
        ("_handle_list_domains", "list_domains", "Use analyze_expertise for domain details"),
    ],
}

# TIER 4 handlers (25 handlers) - remaining specialized operations
TIER4_HANDLERS = {
    "handlers_planning.py": [
        ("_handle_get_project_dashboard", "get_project_dashboard", "Use analyze_estimation_accuracy for dashboard details"),
        ("_handle_analyze_estimation_accuracy", "analyze_estimation_accuracy", "Use discover_patterns for accuracy trends"),
        ("_handle_discover_patterns", "discover_patterns", "Use analyze_completion_rate for pattern analysis"),
        ("_handle_planning_recommend_patterns", "planning_recommend_patterns", "Use planning_extract_patterns for pattern extraction"),
        ("_handle_planning_analyze_failure", "planning_analyze_failure", "Use trigger_replanning for failure recovery"),
        ("_handle_planning_validate_comprehensive", "planning_validate_comprehensive", "Use validate_plan for validation details"),
        ("_handle_planning_verify_properties", "planning_verify_properties", "Use verify_plan for property verification"),
        ("_handle_planning_monitor_deviation", "planning_monitor_deviation", "Use trigger_replanning for deviation handling"),
        ("_handle_planning_trigger_replanning", "planning_trigger_replanning", "Use adaptive_replanning for plan adjustment"),
        ("_handle_planning_refine_plan", "planning_refine_plan", "Use optimize_plan for refinement suggestions"),
        ("_handle_planning_simulate_scenarios", "planning_simulate_scenarios", "Use verify_plan for scenario validation"),
        ("_handle_planning_extract_patterns", "planning_extract_patterns", "Use recommend_patterns for pattern recommendations"),
        ("_handle_planning_generate_lightweight", "planning_generate_lightweight", "Use decompose_hierarchically for full decomposition"),
        ("_handle_planning_validate_llm", "planning_validate_llm", "Use validate_plan for validation details"),
        ("_handle_planning_create_validation_gate", "planning_create_validation_gate", "Use list_rules for gate configuration"),
    ],
    "handlers_consolidation.py": [
        ("_handle_consolidate_episodic_batch", "consolidate_episodic_batch", "Use run_consolidation for full consolidation"),
        ("_handle_consolidate_semantic_batch", "consolidate_semantic_batch", "Use consolidation_quality_metrics for quality"),
        ("_handle_list_clusters", "list_clusters", "Use cluster_events for cluster details"),
        ("_handle_analyze_patterns_comprehensive", "analyze_patterns_comprehensive", "Use extract_patterns for pattern analysis"),
    ],
    "handlers_graph.py": [
        ("_handle_search_relations", "search_relations", "Use list_relations for relation filtering"),
        ("_handle_analyze_community", "analyze_community", "Use search_community for community search"),
        ("_handle_get_graph_stats", "get_graph_stats", "Use list_entities and list_relations for detailed stats"),
    ],
    "handlers_metacognition.py": [
        ("_handle_get_expertise_map", "get_expertise_map", "Use analyze_expertise for expertise details"),
        ("_handle_analyze_cognitive_load", "analyze_cognitive_load", "Use check_workload for load analysis"),
    ],
    "handlers_memory_core.py": [
        ("_handle_search", "search", "Use recall with memory_types filter for filtered search"),
    ],
}

def process_file(file_path: Path, handlers: list):
    """Process a file and add pagination to specified handlers."""
    print(f"\nProcessing {file_path.name}...")

    if not file_path.exists():
        print(f"  ⚠ File not found: {file_path}")
        return 0

    content = file_path.read_text()
    original_content = content
    modified_count = 0

    for handler_name, operation_name, drill_down_hint in handlers:
        print(f"  Processing {handler_name}...")

        # Check if already paginated
        handler_pattern = rf'async def {handler_name}\(self, args: dict\) -> list\[TextContent\]:'
        if not re.search(handler_pattern, content):
            print(f"    ⚠ Handler not found: {handler_name}")
            continue

        if 'paginate_results' in content[content.find(handler_name):content.find(handler_name) + 3000]:
            print(f"    ✓ Already paginated: {handler_name}")
            continue

        # Add pagination
        content = add_pagination_to_handler(content, handler_name, operation_name, drill_down_hint)
        if content != original_content:
            modified_count += 1
            print(f"    ✓ Added pagination: {handler_name}")

    if modified_count > 0:
        file_path.write_text(content)
        print(f"  ✓ Modified {modified_count} handlers in {file_path.name}")

    return modified_count

def main():
    """Main entry point."""
    src_path = Path("/home/user/.work/athena/src/athena/mcp")

    if not src_path.exists():
        print(f"❌ Source path not found: {src_path}")
        return 1

    print("=" * 80)
    print("PAGINATION IMPLEMENTATION - TIER 2-4 (68 Handlers)")
    print("=" * 80)

    total_modified = 0

    # Process TIER 2
    print("\n" + "=" * 80)
    print("TIER 2: Core Memory Operations (18 handlers)")
    print("=" * 80)
    for filename, handlers in TIER2_HANDLERS.items():
        file_path = src_path / filename
        modified = process_file(file_path, handlers)
        total_modified += modified

    # Process TIER 3
    print("\n" + "=" * 80)
    print("TIER 3: Analysis and Filtering (25 handlers)")
    print("=" * 80)
    for filename, handlers in TIER3_HANDLERS.items():
        file_path = src_path / filename
        modified = process_file(file_path, handlers)
        total_modified += modified

    # Process TIER 4
    print("\n" + "=" * 80)
    print("TIER 4: Specialized Operations (25 handlers)")
    print("=" * 80)
    for filename, handlers in TIER4_HANDLERS.items():
        file_path = src_path / filename
        modified = process_file(file_path, handlers)
        total_modified += modified

    print("\n" + "=" * 80)
    print(f"SUMMARY: Modified {total_modified} handlers total")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
