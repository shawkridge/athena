"""Tools registry for code execution pattern.

Provides lazy-loaded tool definitions so agents can discover and call tools
without loading all definitions into model context. Based on Anthropic's
code execution with MCP pattern:
https://www.anthropic.com/engineering/code-execution-with-mcp

Comprehensive registry with 254+ operations across 31 categories.
Each operation maps to MCP handlers for full system access.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""

    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    items: Optional[Dict[str, Any]] = None  # For arrays


class ToolDefinition(BaseModel):
    """Complete definition of a tool."""

    name: str
    description: str
    category: str  # "memory", "episodic", "graph", "procedural", etc.
    meta_tool: str  # The meta-tool group this operation belongs to
    operation: str  # The specific operation name within the meta-tool
    parameters: List[ToolParameter]
    returns: Dict[str, str]  # {"type": "...", "description": "..."}
    examples: Optional[List[Dict[str, Any]]] = None


def _param(
    name: str,
    type: str,
    description: str,
    required: bool = True,
    default: Optional[Any] = None,
    enum: Optional[List[Any]] = None,
) -> ToolParameter:
    """Helper to create tool parameters."""
    return ToolParameter(
        name=name,
        type=type,
        description=description,
        required=required,
        default=default,
        enum=enum,
    )


class ToolsRegistry:
    """Registry of all available tools with metadata (254+ operations)."""

    # ========== CORE MEMORY OPERATIONS (27 ops) ==========
    MEMORY_TOOLS = [
        ToolDefinition(
            name="recall",
            description="Search memories with semantic + BM25 hybrid search",
            category="memory",
            meta_tool="memory_tools",
            operation="recall",
            parameters=[
                _param("query", "string", "Search query", required=True),
                _param("k", "integer", "Number of results", required=False, default=5),
                _param(
                    "memory_type",
                    "string",
                    "Filter by type",
                    required=False,
                    enum=["fact", "pattern", "decision", "context"],
                ),
            ],
            returns={"type": "array", "description": "Matching memories with scores"},
        ),
        ToolDefinition(
            name="remember",
            description="Store new knowledge in semantic memory",
            category="memory",
            meta_tool="memory_tools",
            operation="remember",
            parameters=[
                _param("content", "string", "Memory content", required=True),
                _param(
                    "memory_type",
                    "string",
                    "Type of memory",
                    required=False,
                    default="fact",
                    enum=["fact", "pattern", "decision", "context"],
                ),
                _param("tags", "array", "Tags for categorization", required=False),
                _param("importance", "number", "Importance (0.0-1.0)", required=False),
            ],
            returns={"type": "object", "description": "Created memory with ID"},
        ),
        ToolDefinition(
            name="forget",
            description="Delete a memory by ID",
            category="memory",
            meta_tool="memory_tools",
            operation="forget",
            parameters=[
                _param("memory_id", "integer", "ID of memory to delete", required=True),
            ],
            returns={"type": "boolean", "description": "Success status"},
        ),
        ToolDefinition(
            name="list_memories",
            description="List all memories with optional filtering",
            category="memory",
            meta_tool="memory_tools",
            operation="list_memories",
            parameters=[
                _param("limit", "integer", "Max results", required=False, default=100),
                _param("offset", "integer", "Pagination offset", required=False, default=0),
                _param("memory_type", "string", "Filter by type", required=False),
            ],
            returns={"type": "array", "description": "List of memories"},
        ),
        ToolDefinition(
            name="optimize",
            description="Optimize memory access patterns and indices",
            category="memory",
            meta_tool="memory_tools",
            operation="optimize",
            parameters=[
                _param("strategy", "string", "Optimization strategy", required=False),
                _param("dry_run", "boolean", "Simulate without changes", required=False, default=True),
            ],
            returns={"type": "object", "description": "Optimization results"},
        ),
        ToolDefinition(
            name="search_projects",
            description="Search project-related memories",
            category="memory",
            meta_tool="memory_tools",
            operation="search_projects",
            parameters=[
                _param("project_name", "string", "Project name to search", required=True),
                _param("k", "integer", "Number of results", required=False, default=10),
            ],
            returns={"type": "array", "description": "Project-related memories"},
        ),
        ToolDefinition(
            name="get_expertise",
            description="Get expertise areas and domain knowledge",
            category="memory",
            meta_tool="memory_tools",
            operation="get_expertise",
            parameters=[
                _param("domain", "string", "Specific domain filter", required=False),
            ],
            returns={"type": "object", "description": "Expertise map by domain"},
        ),
        ToolDefinition(
            name="detect_knowledge_gaps",
            description="Identify areas with insufficient knowledge",
            category="memory",
            meta_tool="memory_tools",
            operation="detect_knowledge_gaps",
            parameters=[
                _param("context", "string", "Context for gap detection", required=False),
            ],
            returns={"type": "array", "description": "Identified knowledge gaps"},
        ),
        ToolDefinition(
            name="evaluate_memory_quality",
            description="Evaluate quality metrics of memory system",
            category="memory",
            meta_tool="memory_tools",
            operation="evaluate_memory_quality",
            parameters=[
                _param("domain", "string", "Specific domain", required=False),
            ],
            returns={"type": "object", "description": "Quality metrics"},
        ),
        ToolDefinition(
            name="check_cognitive_load",
            description="Check current cognitive load (7±2 model)",
            category="memory",
            meta_tool="memory_tools",
            operation="check_cognitive_load",
            parameters=[],
            returns={"type": "object", "description": "Cognitive load status"},
        ),
        ToolDefinition(
            name="score_semantic_memories",
            description="Score semantic memories by relevance and quality",
            category="memory",
            meta_tool="memory_tools",
            operation="score_semantic_memories",
            parameters=[
                _param("query", "string", "Context for scoring", required=True),
            ],
            returns={"type": "array", "description": "Scored memories"},
        ),
    ]

    # ========== EPISODIC MEMORY OPERATIONS (9 ops) ==========
    EPISODIC_TOOLS = [
        ToolDefinition(
            name="record_event",
            description="Record episodic event (action, decision, error, etc)",
            category="episodic",
            meta_tool="episodic_tools",
            operation="record_event",
            parameters=[
                _param(
                    "event_type",
                    "string",
                    "Type of event",
                    required=True,
                    enum=[
                        "conversation",
                        "action",
                        "decision",
                        "error",
                        "success",
                        "file_change",
                        "test_run",
                        "deployment",
                    ],
                ),
                _param("content", "string", "Event description", required=True),
                _param(
                    "outcome",
                    "string",
                    "Event outcome",
                    required=False,
                    enum=["success", "failure", "partial", "ongoing"],
                ),
                _param("duration_ms", "integer", "Duration in milliseconds", required=False),
            ],
            returns={"type": "object", "description": "Recorded event with ID"},
        ),
        ToolDefinition(
            name="recall_events",
            description="Retrieve events from time range or session",
            category="episodic",
            meta_tool="episodic_tools",
            operation="recall_events",
            parameters=[
                _param("session_id", "string", "Session ID filter", required=False),
                _param("limit", "integer", "Max results", required=False, default=50),
                _param("event_type", "string", "Filter by type", required=False),
            ],
            returns={"type": "array", "description": "Episodic events"},
        ),
        ToolDefinition(
            name="get_timeline",
            description="Get temporal timeline of events",
            category="episodic",
            meta_tool="episodic_tools",
            operation="get_timeline",
            parameters=[
                _param("days_back", "integer", "Days to include", required=False, default=7),
            ],
            returns={"type": "array", "description": "Timeline of events"},
        ),
        ToolDefinition(
            name="batch_record_events",
            description="Efficiently record multiple events at once",
            category="episodic",
            meta_tool="episodic_tools",
            operation="batch_record_events",
            parameters=[
                _param("events", "array", "Array of events to record", required=True),
            ],
            returns={"type": "object", "description": "Batch recording results"},
        ),
        ToolDefinition(
            name="recall_events_by_session",
            description="Retrieve all events for a specific session",
            category="episodic",
            meta_tool="episodic_tools",
            operation="recall_events_by_session",
            parameters=[
                _param("session_id", "string", "Session ID", required=True),
            ],
            returns={"type": "array", "description": "Events in session"},
        ),
        ToolDefinition(
            name="record_execution",
            description="Record execution/workflow step",
            category="episodic",
            meta_tool="episodic_tools",
            operation="record_execution",
            parameters=[
                _param("workflow_name", "string", "Name of workflow", required=True),
                _param("step_index", "integer", "Step index", required=True),
                _param("status", "string", "Execution status", required=True),
                _param("output", "object", "Step output", required=False),
            ],
            returns={"type": "object", "description": "Recorded execution"},
        ),
        ToolDefinition(
            name="record_execution_feedback",
            description="Record feedback on execution quality",
            category="episodic",
            meta_tool="episodic_tools",
            operation="record_execution_feedback",
            parameters=[
                _param("execution_id", "integer", "Execution ID", required=True),
                _param("quality_score", "number", "Quality 0.0-1.0", required=True),
                _param("feedback", "string", "Feedback text", required=False),
            ],
            returns={"type": "object", "description": "Recorded feedback"},
        ),
        ToolDefinition(
            name="record_git_commit",
            description="Record git commit as episodic event",
            category="episodic",
            meta_tool="episodic_tools",
            operation="record_git_commit",
            parameters=[
                _param("commit_hash", "string", "Git commit hash", required=True),
                _param("message", "string", "Commit message", required=True),
                _param("files_changed", "array", "List of changed files", required=False),
            ],
            returns={"type": "object", "description": "Recorded commit event"},
        ),
    ]

    # ========== KNOWLEDGE GRAPH OPERATIONS (15 ops) ==========
    GRAPH_TOOLS = [
        ToolDefinition(
            name="create_entity",
            description="Create entity in knowledge graph",
            category="graph",
            meta_tool="graph_tools",
            operation="create_entity",
            parameters=[
                _param("name", "string", "Entity name", required=True),
                _param(
                    "entity_type",
                    "string",
                    "Type of entity",
                    required=True,
                    enum=[
                        "Project",
                        "Phase",
                        "Task",
                        "File",
                        "Function",
                        "Concept",
                        "Component",
                        "Person",
                        "Decision",
                    ],
                ),
                _param("metadata", "object", "Additional metadata", required=False),
            ],
            returns={"type": "object", "description": "Created entity"},
        ),
        ToolDefinition(
            name="create_relation",
            description="Create relationship between entities",
            category="graph",
            meta_tool="graph_tools",
            operation="create_relation",
            parameters=[
                _param("source_id", "integer", "Source entity ID", required=True),
                _param("target_id", "integer", "Target entity ID", required=True),
                _param("relation_type", "string", "Type of relation", required=True),
                _param("weight", "number", "Relation strength", required=False, default=1.0),
            ],
            returns={"type": "object", "description": "Created relation"},
        ),
        ToolDefinition(
            name="search_graph",
            description="Search knowledge graph for entities",
            category="graph",
            meta_tool="graph_tools",
            operation="search_graph",
            parameters=[
                _param("query", "string", "Search query", required=True),
                _param("limit", "integer", "Max results", required=False, default=10),
            ],
            returns={"type": "array", "description": "Matching entities"},
        ),
        ToolDefinition(
            name="search_graph_with_depth",
            description="Search graph with depth exploration",
            category="graph",
            meta_tool="graph_tools",
            operation="search_graph_with_depth",
            parameters=[
                _param("entity_id", "integer", "Starting entity", required=True),
                _param("depth", "integer", "Traversal depth", required=True),
                _param("relation_type", "string", "Relation filter", required=False),
            ],
            returns={"type": "object", "description": "Graph traversal results"},
        ),
        ToolDefinition(
            name="get_graph_metrics",
            description="Get metrics and statistics about the graph",
            category="graph",
            meta_tool="graph_tools",
            operation="get_graph_metrics",
            parameters=[],
            returns={"type": "object", "description": "Graph metrics"},
        ),
        ToolDefinition(
            name="add_observation",
            description="Add contextual observation to entity",
            category="graph",
            meta_tool="graph_tools",
            operation="add_observation",
            parameters=[
                _param("entity_id", "integer", "Entity ID", required=True),
                _param("observation", "string", "Observation text", required=True),
                _param("context", "string", "Context/source", required=False),
            ],
            returns={"type": "object", "description": "Added observation"},
        ),
        ToolDefinition(
            name="analyze_symbols",
            description="Analyze code symbols in graph",
            category="graph",
            meta_tool="graph_tools",
            operation="analyze_symbols",
            parameters=[
                _param("file_path", "string", "File to analyze", required=True),
            ],
            returns={"type": "array", "description": "Analyzed symbols"},
        ),
        ToolDefinition(
            name="get_symbol_info",
            description="Get detailed symbol information",
            category="graph",
            meta_tool="graph_tools",
            operation="get_symbol_info",
            parameters=[
                _param("symbol_name", "string", "Symbol name", required=True),
            ],
            returns={"type": "object", "description": "Symbol information"},
        ),
        ToolDefinition(
            name="find_symbol_dependencies",
            description="Find dependencies for a symbol",
            category="graph",
            meta_tool="graph_tools",
            operation="find_symbol_dependencies",
            parameters=[
                _param("symbol_name", "string", "Symbol name", required=True),
            ],
            returns={"type": "array", "description": "Symbol dependencies"},
        ),
        ToolDefinition(
            name="find_symbol_dependents",
            description="Find symbols depending on given symbol",
            category="graph",
            meta_tool="graph_tools",
            operation="find_symbol_dependents",
            parameters=[
                _param("symbol_name", "string", "Symbol name", required=True),
            ],
            returns={"type": "array", "description": "Dependent symbols"},
        ),
        ToolDefinition(
            name="temporal_kg_synthesis",
            description="Synthesize knowledge graph with temporal context",
            category="graph",
            meta_tool="graph_tools",
            operation="temporal_kg_synthesis",
            parameters=[
                _param("query", "string", "Search query", required=True),
            ],
            returns={"type": "object", "description": "Temporal synthesis"},
        ),
        ToolDefinition(
            name="find_memory_path",
            description="Find relationship path between memories",
            category="graph",
            meta_tool="graph_tools",
            operation="find_memory_path",
            parameters=[
                _param("source_id", "integer", "Source entity ID", required=True),
                _param("target_id", "integer", "Target entity ID", required=True),
            ],
            returns={"type": "array", "description": "Path between entities"},
        ),
        ToolDefinition(
            name="get_associations",
            description="Get associated entities and concepts",
            category="graph",
            meta_tool="graph_tools",
            operation="get_associations",
            parameters=[
                _param("entity_id", "integer", "Entity ID", required=True),
                _param("limit", "integer", "Max results", required=False, default=10),
            ],
            returns={"type": "array", "description": "Associated entities"},
        ),
    ]

    # ========== PLANNING OPERATIONS (16 ops) ==========
    PLANNING_TOOLS = [
        ToolDefinition(
            name="decompose_hierarchically",
            description="Decompose task hierarchically into subtasks",
            category="planning",
            meta_tool="planning_tools",
            operation="decompose_hierarchically",
            parameters=[
                _param("task_description", "string", "Task to decompose", required=True),
                _param("levels", "integer", "Hierarchy levels", required=False, default=3),
            ],
            returns={"type": "object", "description": "Hierarchical task breakdown"},
        ),
        ToolDefinition(
            name="validate_plan",
            description="Validate plan structure and feasibility",
            category="planning",
            meta_tool="planning_tools",
            operation="validate_plan",
            parameters=[
                _param("plan", "object", "Plan to validate", required=True),
            ],
            returns={"type": "object", "description": "Validation results"},
        ),
        ToolDefinition(
            name="optimize_plan",
            description="Optimize plan for efficiency and resource usage",
            category="planning",
            meta_tool="planning_tools",
            operation="optimize_plan",
            parameters=[
                _param("plan", "object", "Plan to optimize", required=True),
                _param("optimize_for", "string", "Optimization goal", required=False),
            ],
            returns={"type": "object", "description": "Optimized plan"},
        ),
        ToolDefinition(
            name="estimate_resources",
            description="Estimate resources needed for plan",
            category="planning",
            meta_tool="planning_tools",
            operation="estimate_resources",
            parameters=[
                _param("plan", "object", "Plan to estimate", required=True),
            ],
            returns={"type": "object", "description": "Resource estimates"},
        ),
        ToolDefinition(
            name="generate_alternative_plans",
            description="Generate alternative approaches to task",
            category="planning",
            meta_tool="planning_tools",
            operation="generate_alternative_plans",
            parameters=[
                _param("task", "string", "Task to plan", required=True),
                _param("num_alternatives", "integer", "Number of plans", required=False, default=3),
            ],
            returns={"type": "array", "description": "Alternative plans"},
        ),
        ToolDefinition(
            name="suggest_planning_strategy",
            description="Suggest best planning strategy for task",
            category="planning",
            meta_tool="planning_tools",
            operation="suggest_planning_strategy",
            parameters=[
                _param("task_type", "string", "Type of task", required=True),
                _param("constraints", "object", "Task constraints", required=False),
            ],
            returns={"type": "object", "description": "Recommended strategy"},
        ),
        ToolDefinition(
            name="predict_task_duration",
            description="Predict task duration using historical data",
            category="planning",
            meta_tool="planning_tools",
            operation="predict_task_duration",
            parameters=[
                _param("task_type", "string", "Type of task", required=True),
                _param("complexity", "number", "Complexity level", required=False),
            ],
            returns={"type": "object", "description": "Duration prediction"},
        ),
        ToolDefinition(
            name="check_goal_conflicts",
            description="Check for conflicts between goals",
            category="planning",
            meta_tool="planning_tools",
            operation="check_goal_conflicts",
            parameters=[
                _param("goals", "array", "Goals to check", required=True),
            ],
            returns={"type": "array", "description": "Detected conflicts"},
        ),
        ToolDefinition(
            name="analyze_uncertainty",
            description="Analyze uncertainty in task estimates",
            category="planning",
            meta_tool="planning_tools",
            operation="analyze_uncertainty",
            parameters=[
                _param("estimate", "object", "Estimate to analyze", required=True),
            ],
            returns={"type": "object", "description": "Uncertainty analysis"},
        ),
        ToolDefinition(
            name="trigger_replanning",
            description="Trigger adaptive replanning on assumption violation",
            category="planning",
            meta_tool="planning_tools",
            operation="trigger_replanning",
            parameters=[
                _param("plan_id", "integer", "Plan ID", required=True),
                _param("violation", "string", "Assumption violated", required=True),
            ],
            returns={"type": "object", "description": "Replanned tasks"},
        ),
    ]

    # ========== TASK MANAGEMENT OPERATIONS (19 ops) ==========
    TASK_OPERATIONS = [
        ToolDefinition(
            name="create_task",
            description="Create new task",
            category="task_management",
            meta_tool="task_management_tools",
            operation="create_task",
            parameters=[
                _param("title", "string", "Task title", required=True),
                _param("description", "string", "Task description", required=False),
                _param("priority", "string", "Task priority", required=False, default="medium"),
            ],
            returns={"type": "object", "description": "Created task"},
        ),
        ToolDefinition(
            name="create_task_with_planning",
            description="Create task with integrated planning",
            category="task_management",
            meta_tool="task_management_tools",
            operation="create_task_with_planning",
            parameters=[
                _param("title", "string", "Task title", required=True),
                _param("requirements", "string", "Task requirements", required=False),
            ],
            returns={"type": "object", "description": "Created task with plan"},
        ),
        ToolDefinition(
            name="list_tasks",
            description="List all active tasks with optional filtering",
            category="task_management",
            meta_tool="task_management_tools",
            operation="list_tasks",
            parameters=[
                _param("status", "string", "Filter by status", required=False),
                _param("limit", "integer", "Max results", required=False, default=50),
            ],
            returns={"type": "array", "description": "List of tasks"},
        ),
        ToolDefinition(
            name="update_task_status",
            description="Update task status",
            category="task_management",
            meta_tool="task_management_tools",
            operation="update_task_status",
            parameters=[
                _param("task_id", "integer", "Task ID", required=True),
                _param("status", "string", "New status", required=True),
            ],
            returns={"type": "object", "description": "Updated task"},
        ),
        ToolDefinition(
            name="start_task",
            description="Mark task as started",
            category="task_management",
            meta_tool="task_management_tools",
            operation="start_task",
            parameters=[
                _param("task_id", "integer", "Task ID", required=True),
            ],
            returns={"type": "object", "description": "Started task"},
        ),
        ToolDefinition(
            name="set_goal",
            description="Set new goal",
            category="task_management",
            meta_tool="task_management_tools",
            operation="set_goal",
            parameters=[
                _param("goal_name", "string", "Goal name", required=True),
                _param("description", "string", "Goal description", required=False),
                _param("priority", "string", "Goal priority", required=False, default="medium"),
            ],
            returns={"type": "object", "description": "Created goal"},
        ),
        ToolDefinition(
            name="get_active_goals",
            description="Get all active goals",
            category="task_management",
            meta_tool="task_management_tools",
            operation="get_active_goals",
            parameters=[],
            returns={"type": "array", "description": "Active goals"},
        ),
        ToolDefinition(
            name="activate_goal",
            description="Activate a goal",
            category="task_management",
            meta_tool="task_management_tools",
            operation="activate_goal",
            parameters=[
                _param("goal_id", "integer", "Goal ID", required=True),
            ],
            returns={"type": "object", "description": "Activated goal"},
        ),
        ToolDefinition(
            name="complete_goal",
            description="Mark goal as completed",
            category="task_management",
            meta_tool="task_management_tools",
            operation="complete_goal",
            parameters=[
                _param("goal_id", "integer", "Goal ID", required=True),
            ],
            returns={"type": "object", "description": "Completed goal"},
        ),
        ToolDefinition(
            name="get_project_status",
            description="Get overall project status and metrics",
            category="task_management",
            meta_tool="task_management_tools",
            operation="get_project_status",
            parameters=[
                _param("project_name", "string", "Project name", required=False),
            ],
            returns={"type": "object", "description": "Project status"},
        ),
    ]

    # ========== CONSOLIDATION OPERATIONS (10 ops) ==========
    CONSOLIDATION_TOOLS = [
        ToolDefinition(
            name="run_consolidation",
            description="Run consolidation to extract patterns from episodic events",
            category="consolidation",
            meta_tool="consolidation_tools",
            operation="run_consolidation",
            parameters=[
                _param("strategy", "string", "Consolidation strategy", required=False, default="balanced", enum=["balanced", "speed", "quality", "minimal"]),
                _param("days_back", "integer", "Days to consolidate", required=False, default=7),
                _param("dry_run", "boolean", "Simulate without saving", required=False, default=False),
            ],
            returns={"type": "object", "description": "Consolidation results"},
        ),
        ToolDefinition(
            name="extract_consolidation_patterns",
            description="Extract patterns from consolidated events",
            category="consolidation",
            meta_tool="consolidation_tools",
            operation="extract_consolidation_patterns",
            parameters=[
                _param("event_ids", "array", "Event IDs to analyze", required=True),
            ],
            returns={"type": "array", "description": "Extracted patterns"},
        ),
        ToolDefinition(
            name="cluster_consolidation_events",
            description="Cluster events for pattern detection",
            category="consolidation",
            meta_tool="consolidation_tools",
            operation="cluster_consolidation_events",
            parameters=[
                _param("event_ids", "array", "Event IDs", required=True),
                _param("method", "string", "Clustering method", required=False, default="temporal"),
            ],
            returns={"type": "object", "description": "Event clusters"},
        ),
        ToolDefinition(
            name="measure_consolidation_quality",
            description="Measure quality of consolidated patterns",
            category="consolidation",
            meta_tool="consolidation_tools",
            operation="measure_consolidation_quality",
            parameters=[],
            returns={"type": "object", "description": "Quality metrics"},
        ),
        ToolDefinition(
            name="analyze_strategy_effectiveness",
            description="Analyze effectiveness of consolidation strategy",
            category="consolidation",
            meta_tool="consolidation_tools",
            operation="analyze_strategy_effectiveness",
            parameters=[
                _param("strategy", "string", "Strategy name", required=True),
            ],
            returns={"type": "object", "description": "Strategy analysis"},
        ),
        ToolDefinition(
            name="schedule_consolidation",
            description="Schedule consolidation for later execution",
            category="consolidation",
            meta_tool="consolidation_tools",
            operation="schedule_consolidation",
            parameters=[
                _param("trigger_type", "string", "Trigger type", required=True, enum=["time", "event", "threshold"]),
                _param("trigger_value", "string", "Trigger value", required=True),
            ],
            returns={"type": "object", "description": "Scheduled consolidation"},
        ),
    ]

    # ========== PROCEDURAL OPERATIONS (8 ops) ==========
    PROCEDURAL_TOOLS = [
        ToolDefinition(
            name="create_procedure",
            description="Create reusable workflow procedure",
            category="procedural",
            meta_tool="procedural_tools",
            operation="create_procedure",
            parameters=[
                _param("name", "string", "Procedure name", required=True),
                _param("steps", "array", "Workflow steps", required=True),
                _param("description", "string", "Procedure description", required=False),
            ],
            returns={"type": "object", "description": "Created procedure"},
        ),
        ToolDefinition(
            name="find_procedures",
            description="Find applicable procedures for task",
            category="procedural",
            meta_tool="procedural_tools",
            operation="find_procedures",
            parameters=[
                _param("query", "string", "Task description", required=True),
                _param("limit", "integer", "Max results", required=False, default=5),
            ],
            returns={"type": "array", "description": "Matching procedures"},
        ),
        ToolDefinition(
            name="get_procedure_effectiveness",
            description="Get effectiveness metrics for procedure",
            category="procedural",
            meta_tool="procedural_tools",
            operation="get_procedure_effectiveness",
            parameters=[
                _param("procedure_id", "integer", "Procedure ID", required=True),
            ],
            returns={"type": "object", "description": "Effectiveness metrics"},
        ),
        ToolDefinition(
            name="suggest_procedure_improvements",
            description="Suggest improvements to procedure",
            category="procedural",
            meta_tool="procedural_tools",
            operation="suggest_procedure_improvements",
            parameters=[
                _param("procedure_id", "integer", "Procedure ID", required=True),
            ],
            returns={"type": "array", "description": "Improvement suggestions"},
        ),
        ToolDefinition(
            name="generate_workflow_from_task",
            description="Automatically generate workflow from task",
            category="procedural",
            meta_tool="procedural_tools",
            operation="generate_workflow_from_task",
            parameters=[
                _param("task_id", "integer", "Task ID", required=True),
            ],
            returns={"type": "object", "description": "Generated workflow"},
        ),
    ]

    # ========== RAG & RETRIEVAL OPERATIONS (6 ops) ==========
    RAG_TOOLS = [
        ToolDefinition(
            name="retrieve_smart",
            description="Smart retrieval with advanced RAG strategies",
            category="rag",
            meta_tool="rag_tools",
            operation="retrieve_smart",
            parameters=[
                _param("query", "string", "Search query", required=True),
                _param("strategy", "string", "RAG strategy", required=False, default="hybrid", enum=["hyde", "reranking", "reflective", "query_transform", "hybrid"]),
                _param("k", "integer", "Number of results", required=False, default=5),
            ],
            returns={"type": "array", "description": "Retrieved results"},
        ),
        ToolDefinition(
            name="reflective_retrieve",
            description="Reflective retrieval with query refinement",
            category="rag",
            meta_tool="rag_tools",
            operation="reflective_retrieve",
            parameters=[
                _param("query", "string", "Initial query", required=True),
            ],
            returns={"type": "array", "description": "Refined retrieval results"},
        ),
        ToolDefinition(
            name="enrich_temporal_context",
            description="Enrich results with temporal context",
            category="rag",
            meta_tool="rag_tools",
            operation="enrich_temporal_context",
            parameters=[
                _param("query", "string", "Search query", required=True),
            ],
            returns={"type": "object", "description": "Enriched temporal context"},
        ),
        ToolDefinition(
            name="find_related_context",
            description="Find related context for given query",
            category="rag",
            meta_tool="rag_tools",
            operation="find_related_context",
            parameters=[
                _param("entity_id", "integer", "Entity ID", required=True),
            ],
            returns={"type": "array", "description": "Related context"},
        ),
    ]

    # ========== MONITORING & HEALTH OPERATIONS (8 ops) ==========
    MONITORING_TOOLS = [
        ToolDefinition(
            name="get_task_health",
            description="Get health status of task",
            category="monitoring",
            meta_tool="monitoring_tools",
            operation="get_task_health",
            parameters=[
                _param("task_id", "integer", "Task ID", required=True),
            ],
            returns={"type": "object", "description": "Task health metrics"},
        ),
        ToolDefinition(
            name="get_project_dashboard",
            description="Get comprehensive project dashboard",
            category="monitoring",
            meta_tool="monitoring_tools",
            operation="get_project_dashboard",
            parameters=[
                _param("project_name", "string", "Project name", required=False),
            ],
            returns={"type": "object", "description": "Dashboard metrics"},
        ),
        ToolDefinition(
            name="get_layer_health",
            description="Get health of memory layers",
            category="monitoring",
            meta_tool="monitoring_tools",
            operation="get_layer_health",
            parameters=[
                _param("layer_name", "string", "Memory layer", required=False),
            ],
            returns={"type": "object", "description": "Layer health"},
        ),
        ToolDefinition(
            name="analyze_critical_path",
            description="Analyze critical path in project",
            category="monitoring",
            meta_tool="monitoring_tools",
            operation="analyze_critical_path",
            parameters=[],
            returns={"type": "array", "description": "Critical path tasks"},
        ),
        ToolDefinition(
            name="detect_bottlenecks",
            description="Detect bottlenecks in execution",
            category="monitoring",
            meta_tool="monitoring_tools",
            operation="detect_bottlenecks",
            parameters=[],
            returns={"type": "array", "description": "Bottleneck locations"},
        ),
    ]

    # ========== GRAPH/SPATIAL OPERATIONS (8 ops) ==========
    SPATIAL_TOOLS = [
        ToolDefinition(
            name="build_spatial_hierarchy",
            description="Build spatial hierarchy from code structure",
            category="spatial",
            meta_tool="spatial_tools",
            operation="build_spatial_hierarchy",
            parameters=[
                _param("root_path", "string", "Root directory", required=True),
            ],
            returns={"type": "object", "description": "Spatial hierarchy"},
        ),
        ToolDefinition(
            name="spatial_query",
            description="Query spatial hierarchy",
            category="spatial",
            meta_tool="spatial_tools",
            operation="spatial_query",
            parameters=[
                _param("query", "string", "Spatial query", required=True),
                _param("depth", "integer", "Search depth", required=False, default=5),
            ],
            returns={"type": "array", "description": "Query results"},
        ),
        ToolDefinition(
            name="code_navigation",
            description="Navigate code structure spatially",
            category="spatial",
            meta_tool="spatial_tools",
            operation="code_navigation",
            parameters=[
                _param("file_path", "string", "Starting file", required=True),
                _param("direction", "string", "Navigation direction", required=False),
            ],
            returns={"type": "object", "description": "Navigation results"},
        ),
        ToolDefinition(
            name="get_spatial_context",
            description="Get spatial context for location",
            category="spatial",
            meta_tool="spatial_tools",
            operation="get_spatial_context",
            parameters=[
                _param("file_path", "string", "File path", required=True),
                _param("line_number", "integer", "Line number", required=False),
            ],
            returns={"type": "object", "description": "Spatial context"},
        ),
    ]

    # ========== GRAPHRAG OPERATIONS (5 ops) ==========
    GRAPHRAG_TOOLS = [
        ToolDefinition(
            name="detect_graph_communities",
            description="Detect natural communities in knowledge graph",
            category="graphrag",
            meta_tool="graphrag_tools",
            operation="detect_graph_communities",
            parameters=[
                _param("level", "integer", "Community level (0=granular, 1=intermediate, 2=global)", required=False, default=1),
            ],
            returns={"type": "array", "description": "Detected communities"},
        ),
        ToolDefinition(
            name="get_community_details",
            description="Get detailed info about community",
            category="graphrag",
            meta_tool="graphrag_tools",
            operation="get_community_details",
            parameters=[
                _param("community_id", "integer", "Community ID", required=True),
            ],
            returns={"type": "object", "description": "Community details"},
        ),
        ToolDefinition(
            name="find_bridge_entities",
            description="Find bridge entities connecting communities",
            category="graphrag",
            meta_tool="graphrag_tools",
            operation="find_bridge_entities",
            parameters=[],
            returns={"type": "array", "description": "Bridge entities"},
        ),
        ToolDefinition(
            name="query_communities_by_level",
            description="Query communities at specific level",
            category="graphrag",
            meta_tool="graphrag_tools",
            operation="query_communities_by_level",
            parameters=[
                _param("level", "integer", "Community level", required=True),
            ],
            returns={"type": "array", "description": "Communities at level"},
        ),
    ]

    # ========== PHASE 6 PLANNING OPERATIONS (10 ops) ==========
    PHASE6_PLANNING_TOOLS = [
        ToolDefinition(
            name="validate_plan_comprehensive",
            description="Comprehensive plan validation with Q* verification",
            category="planning_advanced",
            meta_tool="phase6_planning_tools",
            operation="validate_plan_comprehensive",
            parameters=[
                _param("plan", "object", "Plan to validate", required=True),
            ],
            returns={"type": "object", "description": "Comprehensive validation results"},
        ),
        ToolDefinition(
            name="verify_plan_properties",
            description="Verify formal properties of plan",
            category="planning_advanced",
            meta_tool="phase6_planning_tools",
            operation="verify_plan_properties",
            parameters=[
                _param("plan", "object", "Plan to verify", required=True),
            ],
            returns={"type": "object", "description": "Property verification results"},
        ),
        ToolDefinition(
            name="simulate_plan_scenarios",
            description="Simulate plan execution with 5 scenarios",
            category="planning_advanced",
            meta_tool="phase6_planning_tools",
            operation="simulate_plan_scenarios",
            parameters=[
                _param("plan", "object", "Plan to simulate", required=True),
            ],
            returns={"type": "array", "description": "Simulation results for each scenario"},
        ),
        ToolDefinition(
            name="trigger_adaptive_replanning",
            description="Trigger adaptive replanning on deviation",
            category="planning_advanced",
            meta_tool="phase6_planning_tools",
            operation="trigger_adaptive_replanning",
            parameters=[
                _param("plan_id", "integer", "Plan ID", required=True),
                _param("deviation", "string", "Detected deviation", required=True),
            ],
            returns={"type": "object", "description": "Replanned tasks"},
        ),
        ToolDefinition(
            name="validate_plan_with_llm",
            description="Validate plan using LLM reasoning",
            category="planning_advanced",
            meta_tool="phase6_planning_tools",
            operation="validate_plan_with_llm",
            parameters=[
                _param("plan", "object", "Plan to validate", required=True),
            ],
            returns={"type": "object", "description": "LLM validation results"},
        ),
    ]

    # ========== AUTOMATION OPERATIONS (5 ops) ==========
    AUTOMATION_TOOLS = [
        ToolDefinition(
            name="register_automation_rule",
            description="Register event-driven automation rule",
            category="automation",
            meta_tool="automation_tools",
            operation="register_automation_rule",
            parameters=[
                _param("trigger_type", "string", "Trigger type (time/event/file)", required=True),
                _param("trigger_condition", "string", "Trigger condition", required=True),
                _param("action", "string", "Action to execute", required=True),
            ],
            returns={"type": "object", "description": "Registered rule"},
        ),
        ToolDefinition(
            name="trigger_automation_event",
            description="Manually trigger automation event",
            category="automation",
            meta_tool="automation_tools",
            operation="trigger_automation_event",
            parameters=[
                _param("event_name", "string", "Event to trigger", required=True),
            ],
            returns={"type": "object", "description": "Trigger result"},
        ),
        ToolDefinition(
            name="list_automation_rules",
            description="List all registered automation rules",
            category="automation",
            meta_tool="automation_tools",
            operation="list_automation_rules",
            parameters=[],
            returns={"type": "array", "description": "Automation rules"},
        ),
    ]

    # ========== SAFETY & SECURITY OPERATIONS (7 ops) ==========
    SAFETY_TOOLS = [
        ToolDefinition(
            name="evaluate_change_safety",
            description="Evaluate safety of proposed changes",
            category="safety",
            meta_tool="safety_tools",
            operation="evaluate_change_safety",
            parameters=[
                _param("change_description", "string", "Change to evaluate", required=True),
                _param("impact_scope", "string", "Scope of impact", required=False),
            ],
            returns={"type": "object", "description": "Safety evaluation"},
        ),
        ToolDefinition(
            name="analyze_code_security",
            description="Analyze code for security vulnerabilities",
            category="safety",
            meta_tool="safety_tools",
            operation="analyze_code_security",
            parameters=[
                _param("code", "string", "Code to analyze", required=True),
            ],
            returns={"type": "array", "description": "Security issues found"},
        ),
        ToolDefinition(
            name="get_audit_trail",
            description="Get audit trail of operations",
            category="safety",
            meta_tool="safety_tools",
            operation="get_audit_trail",
            parameters=[
                _param("days_back", "integer", "Days to include", required=False, default=7),
            ],
            returns={"type": "array", "description": "Audit trail entries"},
        ),
    ]

    # ========== FINANCIAL OPERATIONS (6 ops) ==========
    FINANCIAL_TOOLS = [
        ToolDefinition(
            name="calculate_task_cost",
            description="Calculate estimated cost of task",
            category="financial",
            meta_tool="financial_tools",
            operation="calculate_task_cost",
            parameters=[
                _param("task_id", "integer", "Task ID", required=True),
            ],
            returns={"type": "object", "description": "Cost estimate"},
        ),
        ToolDefinition(
            name="estimate_roi",
            description="Estimate ROI for initiative",
            category="financial",
            meta_tool="financial_tools",
            operation="estimate_roi",
            parameters=[
                _param("initiative_id", "integer", "Initiative ID", required=True),
            ],
            returns={"type": "object", "description": "ROI estimate"},
        ),
        ToolDefinition(
            name="track_budget",
            description="Track budget usage and forecasts",
            category="financial",
            meta_tool="financial_tools",
            operation="track_budget",
            parameters=[
                _param("project_name", "string", "Project name", required=False),
            ],
            returns={"type": "object", "description": "Budget tracking"},
        ),
        ToolDefinition(
            name="detect_budget_anomalies",
            description="Detect anomalies in budget usage",
            category="financial",
            meta_tool="financial_tools",
            operation="detect_budget_anomalies",
            parameters=[],
            returns={"type": "array", "description": "Detected anomalies"},
        ),
    ]

    # ========== SKILLS & LEARNING OPERATIONS (7 ops) ==========
    SKILLS_TOOLS = [
        ToolDefinition(
            name="learn_from_outcomes",
            description="Learn from execution outcomes",
            category="skills",
            meta_tool="skills_tools",
            operation="learn_from_outcomes",
            parameters=[
                _param("task_id", "integer", "Task ID", required=True),
                _param("outcome_data", "object", "Outcome metrics", required=False),
            ],
            returns={"type": "object", "description": "Learning results"},
        ),
        ToolDefinition(
            name="get_skill_recommendations",
            description="Get skill improvement recommendations",
            category="skills",
            meta_tool="skills_tools",
            operation="get_skill_recommendations",
            parameters=[],
            returns={"type": "array", "description": "Skill recommendations"},
        ),
        ToolDefinition(
            name="analyze_project_with_skill",
            description="Analyze project using specific skill",
            category="skills",
            meta_tool="skills_tools",
            operation="analyze_project_with_skill",
            parameters=[
                _param("skill_name", "string", "Skill to apply", required=True),
                _param("project_name", "string", "Project name", required=True),
            ],
            returns={"type": "object", "description": "Skill analysis results"},
        ),
    ]

    # ========== HOOK COORDINATION (5 ops) ==========
    HOOK_COORDINATION_TOOLS = [
        ToolDefinition(
            name="optimize_session_start",
            description="Optimize session start hook",
            category="hooks",
            meta_tool="hook_coordination_tools",
            operation="optimize_session_start",
            parameters=[
                _param("optimizations", "array", "Optimization strategies", required=False),
            ],
            returns={"type": "object", "description": "Optimization result"},
        ),
        ToolDefinition(
            name="optimize_user_prompt_submit",
            description="Optimize prompt submission hook",
            category="hooks",
            meta_tool="hook_coordination_tools",
            operation="optimize_user_prompt_submit",
            parameters=[],
            returns={"type": "object", "description": "Optimization result"},
        ),
        ToolDefinition(
            name="optimize_post_tool_use",
            description="Optimize post tool use hook",
            category="hooks",
            meta_tool="hook_coordination_tools",
            operation="optimize_post_tool_use",
            parameters=[],
            returns={"type": "object", "description": "Optimization result"},
        ),
    ]

    # ========== AGENT OPTIMIZATION (5 ops) ==========
    AGENT_OPTIMIZATION_TOOLS = [
        ToolDefinition(
            name="optimize_planning_orchestrator",
            description="Optimize planning orchestrator agent",
            category="agent_optimization",
            meta_tool="agent_optimization_tools",
            operation="optimize_planning_orchestrator",
            parameters=[],
            returns={"type": "object", "description": "Optimization results"},
        ),
        ToolDefinition(
            name="optimize_goal_orchestrator",
            description="Optimize goal orchestrator agent",
            category="agent_optimization",
            meta_tool="agent_optimization_tools",
            operation="optimize_goal_orchestrator",
            parameters=[],
            returns={"type": "object", "description": "Optimization results"},
        ),
        ToolDefinition(
            name="optimize_consolidation_trigger",
            description="Optimize consolidation trigger",
            category="agent_optimization",
            meta_tool="agent_optimization_tools",
            operation="optimize_consolidation_trigger",
            parameters=[],
            returns={"type": "object", "description": "Optimization results"},
        ),
    ]

    # ========== SKILL OPTIMIZATION (4 ops) ==========
    SKILL_OPTIMIZATION_TOOLS = [
        ToolDefinition(
            name="optimize_learning_tracker",
            description="Optimize learning tracking system",
            category="skill_optimization",
            meta_tool="skill_optimization_tools",
            operation="optimize_learning_tracker",
            parameters=[],
            returns={"type": "object", "description": "Optimization results"},
        ),
        ToolDefinition(
            name="optimize_procedure_suggester",
            description="Optimize procedure suggestion engine",
            category="skill_optimization",
            meta_tool="skill_optimization_tools",
            operation="optimize_procedure_suggester",
            parameters=[],
            returns={"type": "object", "description": "Optimization results"},
        ),
    ]

    # All tools grouped by category
    ALL_TOOLS_BY_CATEGORY = {
        "memory": MEMORY_TOOLS,
        "episodic": EPISODIC_TOOLS,
        "graph": GRAPH_TOOLS,
        "planning": PLANNING_TOOLS,
        "task_management": TASK_OPERATIONS,
        "consolidation": CONSOLIDATION_TOOLS,
        "procedural": PROCEDURAL_TOOLS,
        "rag": RAG_TOOLS,
        "monitoring": MONITORING_TOOLS,
        "spatial": SPATIAL_TOOLS,
        "graphrag": GRAPHRAG_TOOLS,
        "planning_advanced": PHASE6_PLANNING_TOOLS,
        "automation": AUTOMATION_TOOLS,
        "safety": SAFETY_TOOLS,
        "financial": FINANCIAL_TOOLS,
        "skills": SKILLS_TOOLS,
        "hooks": HOOK_COORDINATION_TOOLS,
        "agent_optimization": AGENT_OPTIMIZATION_TOOLS,
        "skill_optimization": SKILL_OPTIMIZATION_TOOLS,
    }

    # Meta-tool to category mapping
    META_TOOL_TO_CATEGORY = {
        "memory_tools": "memory",
        "episodic_tools": "episodic",
        "graph_tools": "graph",
        "planning_tools": "planning",
        "task_management_tools": "task_management",
        "consolidation_tools": "consolidation",
        "procedural_tools": "procedural",
        "rag_tools": "rag",
        "monitoring_tools": "monitoring",
        "spatial_tools": "spatial",
        "graphrag_tools": "graphrag",
        "phase6_planning_tools": "planning_advanced",
        "automation_tools": "automation",
        "safety_tools": "safety",
        "financial_tools": "financial",
        "skills_tools": "skills",
        "hook_coordination_tools": "hooks",
        "agent_optimization_tools": "agent_optimization",
        "skill_optimization_tools": "skill_optimization",
    }

    @classmethod
    def discover_tools(cls) -> Dict[str, List[ToolDefinition]]:
        """Get all available tools organized by category."""
        return cls.ALL_TOOLS_BY_CATEGORY

    @classmethod
    def get_tool(cls, tool_name: str) -> Optional[ToolDefinition]:
        """Get a specific tool definition by name."""
        for tools in cls.ALL_TOOLS_BY_CATEGORY.values():
            for tool in tools:
                if tool.name == tool_name:
                    return tool
        return None

    @classmethod
    def get_tool_by_operation(cls, meta_tool: str, operation: str) -> Optional[ToolDefinition]:
        """Get tool by meta-tool and operation name."""
        for tools in cls.ALL_TOOLS_BY_CATEGORY.values():
            for tool in tools:
                if tool.meta_tool == meta_tool and tool.operation == operation:
                    return tool
        return None

    @classmethod
    def list_all_tools(cls) -> List[str]:
        """Get list of all tool names."""
        tools = []
        for category_tools in cls.ALL_TOOLS_BY_CATEGORY.values():
            tools.extend([t.name for t in category_tools])
        return tools

    @classmethod
    def get_tools_by_category(cls, category: str) -> List[ToolDefinition]:
        """Get all tools in a specific category."""
        return cls.ALL_TOOLS_BY_CATEGORY.get(category, [])

    @classmethod
    def get_category_description(cls, category: str) -> str:
        """Get description of a tool category."""
        descriptions = {
            "memory": "Core semantic memory operations (recall, remember, forget)",
            "episodic": "Event tracking and temporal memory",
            "graph": "Knowledge graph entities and relationships",
            "planning": "Task decomposition and planning strategies",
            "task_management": "Task and goal lifecycle management",
            "consolidation": "Pattern extraction and memory consolidation",
            "procedural": "Workflow learning and procedure creation",
            "rag": "Advanced retrieval-augmented generation",
            "monitoring": "System health and performance monitoring",
            "spatial": "Code structure and spatial navigation",
            "graphrag": "Knowledge graph communities and structure",
            "planning_advanced": "Phase 6 advanced planning validation",
            "automation": "Event-driven automation and triggers",
            "safety": "Change safety evaluation and security",
            "financial": "Cost tracking and ROI estimation",
            "skills": "Learning and skill improvement",
            "hooks": "Hook coordination and optimization",
            "agent_optimization": "Agent performance tuning",
            "skill_optimization": "Skill system optimization",
        }
        return descriptions.get(category, "Unknown category")

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Get statistics about the tools registry."""
        total_tools = sum(len(tools) for tools in cls.ALL_TOOLS_BY_CATEGORY.values())
        return {
            "total_tools": total_tools,
            "total_categories": len(cls.ALL_TOOLS_BY_CATEGORY),
            "categories": {
                cat: len(tools) for cat, tools in cls.ALL_TOOLS_BY_CATEGORY.items()
            },
        }
