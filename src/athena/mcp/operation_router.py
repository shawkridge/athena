"""Operation Router for Tool Grouping/Namespacing Strategy 1.

Consolidates 120 tools into 10 meta-tools, reducing token usage by 85%.
Routes operations to original handler methods for backward compatibility.
"""

import logging
from typing import Dict, Callable, Any

logger = logging.getLogger(__name__)


class OperationRouter:
    """Routes meta-tool operations to original handlers."""

    # MEMORY_TOOLS: 27 operations
    MEMORY_OPERATIONS = {
        "recall": "_handle_recall",
        "remember": "_handle_remember",
        "forget": "_handle_forget",
        "list_memories": "_handle_list_memories",
        "optimize": "_handle_optimize",
        "search_projects": "_handle_search_projects",
        "record_event": "_handle_record_event",
        "recall_events": "_handle_recall_events",
        "get_timeline": "_handle_get_timeline",
        "batch_record_events": "_handle_batch_record_events",
        "recall_events_by_session": "_handle_recall_events_by_session",
        "smart_retrieve": "_handle_smart_retrieve",
        "analyze_coverage": "_handle_analyze_coverage",
        "get_expertise": "_handle_get_expertise",
        "detect_knowledge_gaps": "_handle_detect_knowledge_gaps",
        "get_working_memory": "_handle_get_working_memory",
        "update_working_memory": "_handle_update_working_memory",
        "clear_working_memory": "_handle_clear_working_memory",
        "consolidate_working_memory": "_handle_consolidate_working_memory",
        "evaluate_memory_quality": "_handle_evaluate_memory_quality",
        "get_learning_rates": "_handle_get_learning_rates",
        "get_metacognition_insights": "_handle_get_metacognition_insights",
        "check_cognitive_load": "_handle_check_cognitive_load",
        "get_memory_quality_summary": "_handle_get_memory_quality_summary",
        "score_semantic_memories": "_handle_score_semantic_memories",
        "get_self_reflection": "_handle_get_self_reflection",
        "run_consolidation": "_handle_run_consolidation",
        "schedule_consolidation": "_handle_schedule_consolidation",
    }

    # EPISODIC_TOOLS: 10 operations
    EPISODIC_OPERATIONS = {
        "record_event": "_handle_record_event",
        "recall_events": "_handle_recall_events",
        "get_timeline": "_handle_get_timeline",
        "batch_record_events": "_handle_batch_record_events",
        "recall_events_by_session": "_handle_recall_events_by_session",
        "schedule_consolidation": "_handle_schedule_consolidation",
        "record_execution": "_handle_record_execution",
        "record_execution_feedback": "_handle_record_execution_feedback",
        "record_git_commit": "_handle_record_git_commit",
    }

    # GRAPH_TOOLS: 15 operations
    GRAPH_OPERATIONS = {
        "create_entity": "_handle_create_entity",
        "create_relation": "_handle_create_relation",
        "add_observation": "_handle_add_observation",
        "search_graph": "_handle_search_graph",
        "search_graph_with_depth": "_handle_search_graph_with_depth",
        "get_graph_metrics": "_handle_get_graph_metrics",
        "analyze_symbols": "_handle_analyze_symbols",
        "get_symbol_info": "_handle_get_symbol_info",
        "find_symbol_dependencies": "_handle_find_symbol_dependencies",
        "find_symbol_dependents": "_handle_find_symbol_dependents",
        "get_causal_context": "_handle_get_causal_context",
        "temporal_kg_synthesis": "_handle_temporal_kg_synthesis",
        "temporal_search_enrich": "_handle_temporal_search_enrich",
        "find_memory_path": "_handle_find_memory_path",
        "get_associations": "_handle_get_associations",
    }

    # PLANNING_TOOLS: 16 operations
    PLANNING_OPERATIONS = {
        "decompose_hierarchically": "_handle_decompose_hierarchically",
        "decompose_with_strategy": "_handle_decompose_with_strategy",
        "validate_plan": "_handle_validate_plan",
        "verify_plan": "_handle_verify_plan",
        "generate_task_plan": "_handle_generate_task_plan",
        "optimize_plan": "_handle_optimize_plan",
        "estimate_resources": "_handle_estimate_resources",
        "generate_alternative_plans": "_handle_generate_alternative_plans",
        "suggest_planning_strategy": "_handle_suggest_planning_strategy",
        "recommend_strategy": "_handle_recommend_strategy",
        "predict_task_duration": "_handle_predict_task_duration",
        "check_goal_conflicts": "_handle_check_goal_conflicts",
        "resolve_goal_conflicts": "_handle_resolve_goal_conflicts",
        "validate_plan_with_reasoning": "_handle_validate_plan_with_reasoning",
        "analyze_uncertainty": "_handle_analyze_uncertainty",
        "trigger_replanning": "_handle_trigger_replanning",
    }

    # TASK_MANAGEMENT_TOOLS: 18 operations
    TASK_OPERATIONS = {
        "create_task": "_handle_create_task",
        "create_task_with_planning": "_handle_create_task_with_planning",
        "create_task_with_milestones": "_handle_create_task_with_milestones",
        "list_tasks": "_handle_list_tasks",
        "update_task_status": "_handle_update_task_status",
        "update_milestone_progress": "_handle_update_milestone_progress",
        "start_task": "_handle_start_task",
        "verify_task": "_handle_verify_task",
        "set_goal": "_handle_set_goal",
        "get_active_goals": "_handle_get_active_goals",
        "activate_goal": "_handle_activate_goal",
        "get_goal_priority_ranking": "_handle_get_goal_priority_ranking",
        "recommend_next_goal": "_handle_recommend_next_goal",
        "record_execution_progress": "_handle_record_execution_progress",
        "complete_goal": "_handle_complete_goal",
        "get_workflow_status": "_handle_get_workflow_status",
        "get_task_health": "_handle_get_task_health",
        "get_project_dashboard": "_handle_get_project_dashboard",
        "get_project_status": "_handle_get_project_status",
    }

    # MONITORING_TOOLS: 8 operations
    MONITORING_OPERATIONS = {
        "get_task_health": "_handle_get_task_health",
        "get_project_dashboard": "_handle_get_project_dashboard",
        "get_layer_health": "_handle_get_layer_health",
        "get_project_status": "_handle_get_project_status",
        "analyze_estimation_accuracy": "_handle_analyze_estimation_accuracy",
        "discover_patterns": "_handle_discover_patterns",
        "analyze_critical_path": "_handle_analyze_critical_path",
        "detect_bottlenecks": "_handle_detect_bottlenecks",
    }

    # COORDINATION_TOOLS: 10 operations
    COORDINATION_OPERATIONS = {
        "add_project_dependency": "_handle_add_project_dependency",
        "analyze_critical_path": "_handle_analyze_critical_path",
        "detect_resource_conflicts": "_handle_detect_resource_conflicts",
        "detect_bottlenecks": "_handle_detect_bottlenecks",
        "analyze_graph_metrics": "_handle_analyze_graph_metrics",
        "analyze_uncertainty": "_handle_analyze_uncertainty",
        "generate_confidence_scores": "_handle_generate_confidence_scores",
        "estimate_confidence_interval": "_handle_estimate_confidence_interval",
        "recommend_orchestration": "_handle_recommend_orchestration",
        "detect_budget_anomalies": "_handle_detect_budget_anomalies",
    }

    # SECURITY_TOOLS: 2 operations
    SECURITY_OPERATIONS = {
        "analyze_code_security": "_handle_analyze_code_security",
        "track_sensitive_data": "_handle_track_sensitive_data",
    }

    # FINANCIAL_TOOLS: 6 operations
    FINANCIAL_OPERATIONS = {
        "calculate_task_cost": "_handle_calculate_task_cost",
        "estimate_roi": "_handle_estimate_roi",
        "suggest_cost_optimizations": "_handle_suggest_cost_optimizations",
        "track_budget": "_handle_track_budget",
        "detect_budget_anomalies": "_handle_detect_budget_anomalies",
        "calculate_roi": "_handle_calculate_roi",
    }

    # ML_INTEGRATION_TOOLS: 7 operations
    ML_OPERATIONS = {
        "train_estimation_model": "_handle_train_estimation_model",
        "recommend_strategy": "_handle_recommend_strategy",
        "predict_task_duration": "_handle_predict_task_duration",
        "forecast_resource_needs": "_handle_forecast_resource_needs",
        "get_saliency_batch": "_handle_get_saliency_batch",
        "compute_memory_saliency": "_handle_compute_memory_saliency",
        "auto_focus_top_memories": "_handle_auto_focus_top_memories",
    }

    # PROCEDURAL_TOOLS: 8 operations
    PROCEDURAL_OPERATIONS = {
        "create_procedure": "_handle_create_procedure",
        "find_procedures": "_handle_find_procedures",
        "record_execution": "_handle_record_execution",
        "get_procedure_effectiveness": "_handle_get_procedure_effectiveness",
        "suggest_procedure_improvements": "_handle_suggest_procedure_improvements",
        "generate_workflow_from_task": "_handle_generate_workflow_from_task",
        "get_pattern_suggestions": "_handle_get_pattern_suggestions",
        "apply_suggestion": "_handle_apply_suggestion",
    }

    # PHASE 1: INTEGRATION_TOOLS: 12 operations
    INTEGRATION_OPERATIONS = {
        "planning_assistance": "_handle_planning_assistance",
        "optimize_plan_suggestions": "_handle_optimize_plan_suggestions",
        "analyze_project_coordination": "_handle_analyze_project_coordination",
        "discover_patterns_advanced": "_handle_discover_patterns_advanced",
        "monitor_system_health_detailed": "_handle_monitor_system_health_detailed",
        "estimate_task_resources_detailed": "_handle_estimate_task_resources_detailed",
        "generate_alternative_plans_impl": "_handle_generate_alternative_plans_impl",
        "analyze_estimation_accuracy_adv": "_handle_analyze_estimation_accuracy_adv",
        "analyze_task_analytics_detailed": "_handle_analyze_task_analytics_detailed",
        "aggregate_analytics_summary": "_handle_aggregate_analytics_summary",
        "get_critical_path_analysis": "_handle_get_critical_path_analysis",
        "get_resource_allocation": "_handle_get_resource_allocation",
    }

    # PHASE 1: AUTOMATION_TOOLS: 5 operations
    AUTOMATION_OPERATIONS = {
        "register_automation_rule": "_handle_register_automation_rule",
        "trigger_automation_event": "_handle_trigger_automation_event",
        "list_automation_rules": "_handle_list_automation_rules",
        "update_automation_config": "_handle_update_automation_config",
        "execute_automation_workflow": "_handle_execute_automation_workflow",
    }

    # PHASE 1: CONVERSATION_TOOLS: 8 operations
    CONVERSATION_OPERATIONS = {
        "start_new_conversation": "_handle_start_new_conversation",
        "add_message_to_conversation": "_handle_add_message_to_conversation",
        "get_conversation_history": "_handle_get_conversation_history",
        "resume_conversation_session": "_handle_resume_conversation_session",
        "create_context_snapshot": "_handle_create_context_snapshot",
        "recover_conversation_context": "_handle_recover_conversation_context",
        "list_active_conversations": "_handle_list_active_conversations",
        "export_conversation_data": "_handle_export_conversation_data",
    }

    # PHASE 2: SAFETY_TOOLS: 7 operations
    SAFETY_OPERATIONS = {
        "evaluate_change_safety": "_handle_evaluate_change_safety",
        "request_approval": "_handle_request_approval",
        "get_audit_trail": "_handle_get_audit_trail",
        "monitor_execution": "_handle_monitor_execution",
        "create_code_snapshot": "_handle_create_code_snapshot",
        "check_safety_policy": "_handle_check_safety_policy",
        "analyze_change_risk": "_handle_analyze_change_risk",
    }

    # PHASE 2: IDE_CONTEXT_TOOLS: 8 operations
    IDE_CONTEXT_OPERATIONS = {
        "get_ide_context": "_handle_get_ide_context",
        "get_cursor_position": "_handle_get_cursor_position",
        "get_open_files": "_handle_get_open_files",
        "get_git_status": "_handle_get_git_status",
        "get_recent_files": "_handle_get_recent_files",
        "get_file_changes": "_handle_get_file_changes",
        "get_active_buffer": "_handle_get_active_buffer",
        "track_ide_activity": "_handle_track_ide_activity",
    }

    # PHASE 2: SKILLS_TOOLS: 7 operations
    SKILLS_OPERATIONS = {
        "analyze_project_with_skill": "_handle_analyze_project_with_skill",
        "improve_estimations": "_handle_improve_estimations",
        "learn_from_outcomes": "_handle_learn_from_outcomes",
        "detect_bottlenecks_advanced": "_handle_detect_bottlenecks_advanced",
        "analyze_health_trends": "_handle_analyze_health_trends",
        "create_task_from_template": "_handle_create_task_from_template",
        "get_skill_recommendations": "_handle_get_skill_recommendations",
    }

    # PHASE 2: RESILIENCE_TOOLS: 6 operations
    RESILIENCE_OPERATIONS = {
        "check_system_health": "_handle_check_system_health",
        "get_health_report": "_handle_get_health_report",
        "configure_circuit_breaker": "_handle_configure_circuit_breaker",
        "get_resilience_status": "_handle_get_resilience_status",
        "test_fallback_chain": "_handle_test_fallback_chain",
        "configure_retry_policy": "_handle_configure_retry_policy",
    }

    # PHASE 3: PERFORMANCE_TOOLS: 4 operations
    PERFORMANCE_OPERATIONS = {
        "get_performance_metrics": "_handle_get_performance_metrics",
        "optimize_queries": "_handle_optimize_queries",
        "manage_cache": "_handle_manage_cache",
        "batch_operations": "_handle_batch_operations",
    }

    # PHASE 3: HOOKS_TOOLS: 5 operations
    HOOKS_OPERATIONS = {
        "register_hook": "_handle_register_hook",
        "trigger_hook": "_handle_trigger_hook",
        "detect_hook_cycles": "_handle_detect_hook_cycles",
        "configure_rate_limiting": "_handle_configure_rate_limiting",
        "list_hooks": "_handle_list_hooks",
    }

    # PHASE 3: SPATIAL_TOOLS: 8 operations
    SPATIAL_OPERATIONS = {
        "build_spatial_hierarchy": "_handle_build_spatial_hierarchy",
        "spatial_storage": "_handle_spatial_storage",
        "symbol_analysis": "_handle_symbol_analysis",
        "spatial_distance": "_handle_spatial_distance",
        "spatial_query": "_handle_spatial_query",
        "spatial_indexing": "_handle_spatial_indexing",
        "code_navigation": "_handle_code_navigation",
        "get_spatial_context": "_handle_get_spatial_context",
    }

    # PHASE 4: RAG_TOOLS: 6 operations
    RAG_OPERATIONS = {
        "retrieve_smart": "_handle_rag_retrieve_smart",
        "calibrate_uncertainty": "_handle_rag_calibrate_uncertainty",
        "route_planning_query": "_handle_rag_route_planning_query",
        "enrich_temporal_context": "_handle_rag_enrich_temporal_context",
        "find_related_context": "_handle_graph_find_related_context",
        "reflective_retrieve": "_handle_rag_reflective_retrieve",
    }

    # PHASE 4: ANALYSIS_TOOLS: 2 operations
    ANALYSIS_OPERATIONS = {
        "analyze_project_codebase": "_handle_analyze_project_codebase",
        "store_project_analysis": "_handle_store_project_analysis",
    }

    # PHASE 4: ORCHESTRATION_TOOLS: 3 operations
    ORCHESTRATION_OPERATIONS = {
        "orchestrate_agent_tasks": "_handle_orchestrate_agent_tasks",
        "recommend_planning_patterns": "_handle_planning_recommend_patterns",
        "analyze_failure_patterns": "_handle_planning_analyze_failure",
    }

    # PHASE 5: CONSOLIDATION_TOOLS: 10 operations
    CONSOLIDATION_OPERATIONS = {
        "run_consolidation": "_handle_consolidation_run_consolidation",
        "extract_consolidation_patterns": "_handle_consolidation_extract_patterns",
        "cluster_consolidation_events": "_handle_consolidation_cluster_events",
        "measure_consolidation_quality": "_handle_consolidation_measure_quality",
        "measure_advanced_consolidation_metrics": "_handle_consolidation_measure_advanced",
        "analyze_strategy_effectiveness": "_handle_consolidation_analyze_strategy",
        "analyze_project_patterns": "_handle_consolidation_analyze_project",
        "analyze_validation_effectiveness": "_handle_consolidation_analyze_validation",
        "discover_orchestration_patterns": "_handle_consolidation_discover_orchestration",
        "analyze_consolidation_performance": "_handle_consolidation_analyze_performance",
    }

    # PHASE 6: PLANNING_TOOLS: 10 operations
    PHASE6_PLANNING_OPERATIONS = {
        "validate_plan_comprehensive": "_handle_planning_validate_comprehensive",
        "verify_plan_properties": "_handle_planning_verify_properties",
        "monitor_execution_deviation": "_handle_planning_monitor_deviation",
        "trigger_adaptive_replanning": "_handle_planning_trigger_replanning",
        "refine_plan_automatically": "_handle_planning_refine_plan",
        "simulate_plan_scenarios": "_handle_planning_simulate_scenarios",
        "extract_planning_patterns": "_handle_planning_extract_patterns",
        "generate_lightweight_plan": "_handle_planning_generate_lightweight",
        "validate_plan_with_llm": "_handle_planning_validate_llm",
        "create_validation_gate": "_handle_planning_create_validation_gate",
    }

    # HOOK_COORDINATION: 5 operations
    HOOK_COORDINATION_OPERATIONS = {
        "optimize_session_start": "_handle_optimize_session_start",
        "optimize_session_end": "_handle_optimize_session_end",
        "optimize_user_prompt_submit": "_handle_optimize_user_prompt_submit",
        "optimize_post_tool_use": "_handle_optimize_post_tool_use",
        "optimize_pre_execution": "_handle_optimize_pre_execution",
    }

    # AGENT_OPTIMIZATION: 5 operations
    AGENT_OPTIMIZATION_OPERATIONS = {
        "optimize_planning_orchestrator": "_handle_optimize_planning_orchestrator",
        "optimize_goal_orchestrator": "_handle_optimize_goal_orchestrator",
        "optimize_consolidation_trigger": "_handle_optimize_consolidation_trigger",
        "optimize_strategy_orchestrator": "_handle_optimize_strategy_orchestrator",
        "optimize_attention_optimizer": "_handle_optimize_attention_optimizer",
    }

    # SKILL_OPTIMIZATION: 4 operations
    SKILL_OPTIMIZATION_OPERATIONS = {
        "optimize_learning_tracker": "_handle_optimize_learning_tracker",
        "optimize_procedure_suggester": "_handle_optimize_procedure_suggester",
        "optimize_gap_detector": "_handle_optimize_gap_detector",
        "optimize_quality_monitor": "_handle_optimize_quality_monitor",
    }

    # ZETTELKASTEN_TOOLS: 6 operations
    ZETTELKASTEN_OPERATIONS = {
        "create_memory_version": "_handle_create_memory_version",
        "get_memory_evolution_history": "_handle_get_memory_evolution_history",
        "compute_memory_attributes": "_handle_compute_memory_attributes",
        "get_memory_attributes": "_handle_get_memory_attributes",
        "create_hierarchical_index": "_handle_create_hierarchical_index",
        "assign_memory_to_index": "_handle_assign_memory_to_index",
    }

    # GRAPHRAG_TOOLS: 5 operations
    GRAPHRAG_OPERATIONS = {
        "detect_graph_communities": "_handle_detect_graph_communities",
        "get_community_details": "_handle_get_community_details",
        "query_communities_by_level": "_handle_query_communities_by_level",
        "analyze_community_connectivity": "_handle_analyze_community_connectivity",
        "find_bridge_entities": "_handle_find_bridge_entities",
    }

    # CODE_SEARCH_TOOLS: 4 operations
    CODE_SEARCH_OPERATIONS = {
        "search_code_semantically": "_handle_search_code_semantically",
        "search_code_by_type": "_handle_search_code_by_type",
        "search_code_by_name": "_handle_search_code_by_name",
        "analyze_code_file": "_handle_analyze_code_file",
        "find_code_dependencies": "_handle_find_code_dependencies",
        "index_code_repository": "_handle_index_code_repository",
        "get_code_statistics": "_handle_get_code_statistics",
    }

    # CODE_ANALYSIS_TOOLS: 6 operations
    CODE_ANALYSIS_OPERATIONS = {
        "record_code_analysis": "_handle_record_code_analysis",
        "store_code_insights": "_handle_store_code_insights",
        "add_code_entities": "_handle_add_code_entities",
        "extract_code_patterns": "_handle_extract_code_patterns",
        "analyze_repository": "_handle_analyze_repository",
        "get_analysis_metrics": "_handle_get_analysis_metrics",
    }

    # EXTERNAL_KNOWLEDGE_TOOLS: 4 operations
    EXTERNAL_KNOWLEDGE_OPERATIONS = {
        "lookup_external_knowledge": "_handle_lookup_external_knowledge",
        "expand_knowledge_relations": "_handle_expand_knowledge_relations",
        "synthesize_knowledge": "_handle_synthesize_knowledge",
        "explore_concept_network": "_handle_explore_concept_network",
    }

    # All operation maps
    OPERATION_MAPS = {
        "memory_tools": MEMORY_OPERATIONS,
        "episodic_tools": EPISODIC_OPERATIONS,
        "graph_tools": GRAPH_OPERATIONS,
        "planning_tools": PLANNING_OPERATIONS,
        "task_management_tools": TASK_OPERATIONS,
        "monitoring_tools": MONITORING_OPERATIONS,
        "coordination_tools": COORDINATION_OPERATIONS,
        "security_tools": SECURITY_OPERATIONS,
        "financial_tools": FINANCIAL_OPERATIONS,
        "ml_integration_tools": ML_OPERATIONS,
        "procedural_tools": PROCEDURAL_OPERATIONS,
        "integration_tools": INTEGRATION_OPERATIONS,
        "automation_tools": AUTOMATION_OPERATIONS,
        "conversation_tools": CONVERSATION_OPERATIONS,
        "safety_tools": SAFETY_OPERATIONS,
        "ide_context_tools": IDE_CONTEXT_OPERATIONS,
        "skills_tools": SKILLS_OPERATIONS,
        "resilience_tools": RESILIENCE_OPERATIONS,
        "performance_tools": PERFORMANCE_OPERATIONS,
        "hooks_tools": HOOKS_OPERATIONS,
        "spatial_tools": SPATIAL_OPERATIONS,
        "rag_tools": RAG_OPERATIONS,
        "analysis_tools": ANALYSIS_OPERATIONS,
        "orchestration_tools": ORCHESTRATION_OPERATIONS,
        "consolidation_tools": CONSOLIDATION_OPERATIONS,
        "phase6_planning_tools": PHASE6_PLANNING_OPERATIONS,
        "hook_coordination_tools": HOOK_COORDINATION_OPERATIONS,
        "agent_optimization_tools": AGENT_OPTIMIZATION_OPERATIONS,
        "skill_optimization_tools": SKILL_OPTIMIZATION_OPERATIONS,
        "zettelkasten_tools": ZETTELKASTEN_OPERATIONS,
        "graphrag_tools": GRAPHRAG_OPERATIONS,
        "code_search_tools": CODE_SEARCH_OPERATIONS,
        "code_analysis_tools": CODE_ANALYSIS_OPERATIONS,
        "external_knowledge_tools": EXTERNAL_KNOWLEDGE_OPERATIONS,
    }

    def __init__(self, handler_instance: Any):
        """Initialize router with handler instance.

        Args:
            handler_instance: The MemoryMCPServer instance containing all handlers
        """
        self.handler = handler_instance
        self.logger = logging.getLogger(__name__)

    async def route(self, meta_tool_name: str, arguments: dict) -> Any:
        """Route operation to appropriate handler.

        Args:
            meta_tool_name: Name of meta-tool (e.g., "memory_tools")
            arguments: Arguments dict with "operation" key

        Returns:
            Handler result as dict

        Raises:
            ValueError: If operation not found
        """
        import json

        operation = arguments.get("operation")
        if not operation:
            raise ValueError(f"Missing 'operation' parameter for {meta_tool_name}")

        # Get operation map for this meta-tool
        operations = self.OPERATION_MAPS.get(meta_tool_name)
        if not operations:
            raise ValueError(f"Unknown meta-tool: {meta_tool_name}")

        # Get handler name for this operation
        handler_name = operations.get(operation)
        if not handler_name:
            raise ValueError(
                f"Unknown operation '{operation}' for meta-tool '{meta_tool_name}'. "
                f"Available operations: {list(operations.keys())}"
            )

        # Get handler method
        handler = getattr(self.handler, handler_name, None)
        if not handler:
            raise ValueError(f"Handler {handler_name} not found")

        # Call handler with arguments (minus the operation key)
        self.logger.debug(f"Routing {meta_tool_name}::{operation} to {handler_name}")
        result = await handler(arguments)

        # If result is a list of TextContent (from MCP handlers), extract the text and parse as JSON
        if isinstance(result, list) and len(result) > 0:
            # This is a list[TextContent] response from MCP handler
            text_content = result[0].text if hasattr(result[0], 'text') else str(result[0])
            try:
                return json.loads(text_content)
            except (json.JSONDecodeError, AttributeError):
                # If not JSON, return as success response
                return {"status": "success", "data": text_content}

        # If result is already a dict, return as-is
        if isinstance(result, dict):
            return result

        # Otherwise wrap in success response
        return {"status": "success", "data": result}

    @staticmethod
    def get_all_operations() -> Dict[str, list]:
        """Get all available operations by meta-tool.

        Returns:
            Dict mapping meta-tool names to list of operations
        """
        return {
            name: list(ops.keys())
            for name, ops in OperationRouter.OPERATION_MAPS.items()
        }

    @staticmethod
    def get_meta_tool_count() -> int:
        """Get number of meta-tools."""
        return len(OperationRouter.OPERATION_MAPS)

    @staticmethod
    def get_total_operations() -> int:
        """Get total number of operations across all meta-tools."""
        total = 0
        for ops in OperationRouter.OPERATION_MAPS.values():
            total += len(ops)
        return total
