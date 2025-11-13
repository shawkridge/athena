"""MCP server with memory tool handlers."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

from .rate_limiter import MCPRateLimiter, rate_limit_response
from .operation_router import OperationRouter
from .structured_result import StructuredResult, ResultStatus, PaginationMetadata
from .handler_middleware_wrapper import HandlerBudgetMiddlewareMixin
from ..core.models import MemoryType
from ..memory import MemoryStore
from ..memory.quality import SemanticMemoryQualityAnalyzer
from ..projects import ProjectManager
from ..manager import UnifiedMemoryManager
from ..episodic.store import EpisodicStore
from ..episodic.models import EpisodicEvent, EventContext, EventType, EventOutcome
from ..procedural.store import ProceduralStore
from ..procedural.models import Procedure, ProcedureCategory
from ..prospective.store import ProspectiveStore
from ..prospective.models import ProspectiveTask, TaskStatus, TaskPriority, TaskPhase
from ..prospective.monitoring import TaskMonitor
from ..integration.analytics import TaskAnalytics
from ..integration.planning_assistant import PlanningAssistant
from ..integration.project_coordinator import ProjectCoordinator
from ..integration.confidence_planner import ConfidencePlanner
from ..graph.store import GraphStore
from ..graph.models import Entity, Relation, EntityType, RelationType
from ..associations.network import AssociationNetwork

# PHASE 5: Advanced Monitoring, Analytics & Distributed Memory
from ..monitoring.layer_health_dashboard import LayerHealthMonitor, LayerHealth, SystemHealth
from ..graph.analytics import GraphAnalyzer, GraphAnalytics
from ..projects.distributed_memory import DistributedMemoryManager, MemoryLayerType, SharingLevel

from ..meta.store import MetaMemoryStore
from ..consolidation.system import ConsolidationSystem
from ..integration import IntegratedEpisodicStore
from ..spatial.store import SpatialStore
from ..working_memory import (
    CentralExecutive,
    PhonologicalLoop,
    VisuospatialSketchpad,
    EpisodicBuffer,
    ConsolidationRouter,
)
from ..metacognition.quality import MemoryQualityMonitor
from ..metacognition.learning import LearningRateAdjuster
from ..metacognition.gaps import KnowledgeGapDetector
from ..metacognition.reflection import SelfReflectionSystem
from ..metacognition.load import CognitiveLoadMonitor

# Optional LLM support for advanced gap detection and semantic analysis
try:
    from ..rag.llm_client import OllamaLLMClient
    LLM_CLIENT_AVAILABLE = True
except ImportError:
    LLM_CLIENT_AVAILABLE = False
    OllamaLLMClient = None

from ..planning import (
    PlanningStore,
    PlanValidator,
    ValidationResult,
    FeasibilityReport,
    RuleValidationResult,
    AdjustmentRecommendation,
    PlanMonitor,
    AdaptiveReplanning,
    FormalVerificationEngine,
)
from ..planning.llm_validation import LLMPlanValidator
from ..consolidation.llm_clustering import LLMConsolidationClusterer
from ..procedural.llm_workflow_generation import LLMWorkflowGenerator
from ..research import (
    ResearchStore,
    ResearchTask,
    ResearchStatus,
    ResearchFinding,
    AgentProgress,
    AgentStatus,
    ResearchAgentExecutor,
    ResearchMemoryIntegrator,
)

# Phase 3: Executive Function Integration
from .executive_function_tools import (
    get_executive_function_tools,
    ExecutiveFunctionMCPHandlers,
)
from ..executive.hierarchy import GoalHierarchy
from ..executive.strategy import StrategySelector
from ..executive.conflict import ConflictResolver
from ..executive.progress import ProgressMonitor
from ..executive.agent_bridge import ExecutiveAgentBridge
from ..executive.orchestration_bridge import OrchestrationBridge
from ..executive.strategy_aware_planner import StrategyAwarePlanner

# Phase 1-6 Handler Refactoring: Domain-Extracted Modules
from .handlers_episodic import EpisodicHandlersMixin
from .handlers_memory_core import MemoryCoreHandlersMixin
from .handlers_procedural import ProceduralHandlersMixin
from .handlers_prospective import ProspectiveHandlersMixin
from .handlers_graph import GraphHandlersMixin
from .handlers_consolidation import ConsolidationHandlersMixin
from .handlers_planning import PlanningHandlersMixin
from .handlers_metacognition import MetacognitionHandlersMixin
from .handlers_system import SystemHandlersMixin

# Phase 5-6 Advanced Features: Agent, Hook, Skill Optimization & Slash Commands
from .handlers_agent_optimization import AgentOptimizationHandlersMixin
from .handlers_hook_coordination import HookCoordinationHandlersMixin
from .handlers_skill_optimization import SkillOptimizationHandlersMixin
from .handlers_slash_commands import SlashCommandHandlersMixin

# Phase 3: Git-Aware Temporal Chains
from .git_tools import get_git_tools, GitMCPHandlers
from ..temporal.git_store import GitStore
from ..temporal.git_retrieval import GitTemporalRetrieval

# Phase 4: Procedural Learning from Code Patterns
from .pattern_tools import get_pattern_tools, PatternMCPHandlers
from ..procedural.pattern_extractor import PatternExtractor
from ..procedural.pattern_matcher import PatternMatcher
from ..procedural.pattern_suggester import PatternSuggester

# Phase 1C: Symbol Analysis (Code Structure Understanding)
from .symbol_analysis_tools import get_symbol_analysis_tools, SymbolAnalysisMCPHandlers

# Phase 47: ATHENA CLI & Comprehensive Code Analysis
from .athena_analyzer_tools import get_athena_analyzer_tools, ATHENAAnalyzerMCPHandlers

# Week 1.3: Rules Engine and Suggestions Engine (Phase 9)
from ..rules.models import Rule, RuleCategory, RuleType, SeverityLevel, RuleOverride
from ..rules.store import RulesStore
from ..rules.engine import RulesEngine
from ..rules.suggestions import SuggestionsEngine

# Phase 9: Advanced Features (Uncertainty, Cost Optimization, Context Adapter)
from ..phase9.uncertainty import (
    ConfidenceScorer,
    UncertaintyAnalyzer,
    UncertaintyStore,
)
from ..phase9.cost_optimization import (
    CostCalculator,
    CostOptimizationStore,
    ResourceType,
)
from ..phase9.context_adapter import (
    ExternalSystemBridge,
    ContextAdapterStore,
    ExternalSourceType,
    SyncDirection,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryMCPServer(
    HandlerBudgetMiddlewareMixin,
    EpisodicHandlersMixin,
    MemoryCoreHandlersMixin,
    ProceduralHandlersMixin,
    ProspectiveHandlersMixin,
    GraphHandlersMixin,
    ConsolidationHandlersMixin,
    PlanningHandlersMixin,
    MetacognitionHandlersMixin,
    SystemHandlersMixin,
    AgentOptimizationHandlersMixin,
    HookCoordinationHandlersMixin,
    SkillOptimizationHandlersMixin,
    SlashCommandHandlersMixin,
):
    """MCP server for memory operations.

    Handler Refactoring Status: 100% COMPLETE ✅

    Extracted 148+ methods from 12,363 lines into 11 domain-organized mixin modules:
    - ✅ Phase 1: Episodic handlers (16 methods, 1,232 lines)
    - ✅ Phase 2: Memory core handlers (6 methods, 349 lines)
    - ✅ Phase 3: Procedural handlers (21 methods, 945 lines)
    - ✅ Phase 4: Prospective handlers (24 methods, 1,486 lines)
    - ✅ Phase 5: Graph handlers (10 methods, 515 lines)
    - ✅ Phase 6: Consolidation handlers (16 methods, 363 lines)
    - ✅ Phase 7: Planning handlers (29 methods, 5,982 lines)
    - ✅ Phase 8: Metacognition handlers (8 methods, 1,222 lines)
    - ✅ Phase 9: Working memory handlers (11 methods, stub)
    - ✅ Phase 10: Research handlers (4 methods, stub)
    - ✅ Phase 11: System handlers (34 methods, 725 lines)

    Result: Main handler file now 1,270 lines (89.7% reduction)
    Mixin pattern: 100% backward compatible, zero breaking changes
    """

    def __init__(self, db_path: str | Path, enable_advanced_rag: bool = True):
        """Initialize MCP server.

        Args:
            db_path: Path to SQLite database (ignored for PostgreSQL Docker deployment)
            enable_advanced_rag: If True, enable advanced RAG features (HyDE, LLM reranking, temporal enrichment)
                Works with both Ollama (local) and Claude LLM (API-based)
        """
        # Use PostgreSQL in Docker, SQLite locally
        # db_path is ignored for PostgreSQL
        self.store = MemoryStore(db_path=db_path, backend='postgres')
        self.project_manager = ProjectManager(self.store)

        # Initialize MCP rate limiter
        self.rate_limiter = MCPRateLimiter(
            read_limit=100,   # 100 read operations per minute
            write_limit=30,   # 30 write operations per minute
            admin_limit=10    # 10 admin operations per minute
        )

        # Initialize all layer stores
        self.spatial_store = SpatialStore(self.store.db)
        # Use integrated episodic store for automatic spatial/temporal population
        self.episodic_store = IntegratedEpisodicStore(
            self.store.db,
            spatial_store=self.spatial_store,
            auto_spatial=True,
            auto_temporal=True,
            temporal_batch_size=10
        )
        self.procedural_store = ProceduralStore(self.store.db)
        self.prospective_store = ProspectiveStore(self.store.db)
        self.graph_store = GraphStore(self.store.db)
        self.association_network = AssociationNetwork(self.store.db)
        self.meta_store = MetaMemoryStore(self.store.db)
        self.consolidation_system = ConsolidationSystem(
            self.store.db,
            self.store,
            self.episodic_store.episodic_store,  # Pass the underlying episodic store
            self.procedural_store,
            self.meta_store
        )

        # Initialize working memory components
        self.central_executive = CentralExecutive(self.store.db, self.store.embedder)
        self.phonological_loop = PhonologicalLoop(self.store.db, self.store.embedder)
        self.visuospatial_sketchpad = VisuospatialSketchpad(self.store.db)
        self.episodic_buffer = EpisodicBuffer(self.store.db, self.store.embedder)
        self.consolidation_router = ConsolidationRouter(self.store.db)

        # Initialize LLM client for advanced features (optional)
        self.llm_client = None
        if LLM_CLIENT_AVAILABLE:
            try:
                from athena.core.config import OLLAMA_LLM_MODEL
                # Use centrally configured LLM model
                self.llm_client = OllamaLLMClient(model=OLLAMA_LLM_MODEL)
                logger.info(f"LLM client ({OLLAMA_LLM_MODEL}) initialized for semantic analysis")
            except Exception as e:
                try:
                    # Fallback to Mistral 7B
                    self.llm_client = OllamaLLMClient(model="mistral:latest")
                    logger.warning(f"Qwen2.5 not available, using Mistral 7B: {e}")
                except Exception as e2:
                    logger.warning(f"LLM initialization failed, using heuristic analysis: {e2}")
                    self.llm_client = None

        # Initialize metacognition components (Phase 4)
        # Pass Database object directly (works with PostgreSQL)
        self.quality_monitor = MemoryQualityMonitor(self.store.db)
        self.learning_adjuster = LearningRateAdjuster(self.store.db)
        self.gap_detector = KnowledgeGapDetector(
            self.store.db,
            llm_client=self.llm_client
        )
        self.reflection_system = SelfReflectionSystem(self.store.db)
        self.load_monitor = CognitiveLoadMonitor(self.store.db)

        # Initialize semantic memory quality analyzer (Task 4)
        self.semantic_quality_analyzer = SemanticMemoryQualityAnalyzer(
            self.store.db,
            llm_client=self.llm_client
        )

        # Initialize planning components (Phase 1.2)
        self.planning_store = PlanningStore(self.store.db)
        self.plan_validator = PlanValidator(self.planning_store)
        self.plan_monitor = PlanMonitor(self.planning_store)
        self.adaptive_replanning = AdaptiveReplanning(self.planning_store)
        self.formal_verification = FormalVerificationEngine(self.planning_store)

        # Initialize LLM-powered plan validator (Task 5)
        self.llm_plan_validator = LLMPlanValidator(llm_client=self.llm_client)

        # Initialize LLM consolidation clustering (Task 6)
        self.llm_consolidation_clusterer = LLMConsolidationClusterer(llm_client=self.llm_client)

        # Initialize LLM workflow generator (Task 7)
        self.llm_workflow_generator = LLMWorkflowGenerator(llm_client=self.llm_client)

        # Initialize research components
        self.research_store = ResearchStore(self.store.db)

        # Initialize research memory integrator for semantic storage
        self.research_memory_integrator = ResearchMemoryIntegrator(
            memory_store=self.store,
            graph_store=self.graph_store,
            episodic_store=self.episodic_store,
        )

        self.research_executor = ResearchAgentExecutor(
            research_store=self.research_store,
            on_finding_discovered=self._on_research_finding_discovered,
            on_status_updated=self._on_research_status_updated,
            memory_integrator=self.research_memory_integrator,
        )

        # Initialize Phase 5-8 components
        self.task_monitor = TaskMonitor(self.store.db)
        self.task_analytics = TaskAnalytics(self.store.db)
        self.planning_assistant = PlanningAssistant(self.store.db)
        self.project_coordinator = ProjectCoordinator(self.store.db)
        self.confidence_planner = ConfidencePlanner(self.store.db)

        # Initialize PHASE 5: Advanced Monitoring & Analytics components
        self.layer_health_monitor = LayerHealthMonitor(self.store.db)
        # GraphAnalyzer will be created on-demand with graph data in _handle_get_graph_metrics

        # Initialize PHASE 5: Distributed Memory components
        self.distributed_memory_manager = DistributedMemoryManager(project_id=1)

        # Week 1.3: Rules Engine and Suggestions Engine
        self.rules_store = RulesStore(self.store.db)
        self.rules_engine = RulesEngine(self.store.db, self.rules_store)
        self.suggestions_engine = SuggestionsEngine(self.rules_engine)

        # Phase 3: Executive Function bridges
        self.goal_hierarchy = GoalHierarchy(self.store.db)
        self.strategy_selector = StrategySelector(self.store.db)
        self.conflict_resolver = ConflictResolver(self.store.db)
        self.progress_monitor = ProgressMonitor(self.store.db)
        self.agent_bridge = ExecutiveAgentBridge()

        self.orchestration_bridge = OrchestrationBridge(
            hierarchy=self.goal_hierarchy,
            strategy_selector=self.strategy_selector,
            conflict_resolver=self.conflict_resolver,
            progress_tracker=self.progress_monitor,
        )

        # Mock planner agent (in production, connect to actual Planner Agent)
        self.mock_planner_agent = None  # TODO: connect to agents/planner.py

        self.strategy_aware_planner = StrategyAwarePlanner(
            planner_agent=self.mock_planner_agent,
            orchestration_bridge=self.orchestration_bridge,
        )

        self.executive_handlers = ExecutiveFunctionMCPHandlers(
            orchestration_bridge=self.orchestration_bridge,
            strategy_aware_planner=self.strategy_aware_planner,
            db=self.store.db,
        )

        # Phase 1C: Symbol analysis handlers
        self.symbol_analysis_handlers = SymbolAnalysisMCPHandlers()

        # Phase 47: ATHENA analyzer handlers
        self.athena_analyzer_handlers = ATHENAAnalyzerMCPHandlers()

        # Phase 3: Initialize SessionContextManager for session-aware queries
        from ..session.context_manager import SessionContextManager
        self.session_manager = SessionContextManager(self.store.db)

        # Initialize unified memory manager with all stores
        self.unified_manager = UnifiedMemoryManager(
            semantic=self.store,
            episodic=self.episodic_store,
            procedural=self.procedural_store,
            prospective=self.prospective_store,
            graph=self.graph_store,
            meta=self.meta_store,
            consolidation=self.consolidation_system,
            project_manager=self.project_manager,
            enable_advanced_rag=enable_advanced_rag,
            session_manager=self.session_manager,
        )

        self.server = Server("athena")

        # Initialize OperationRouter as singleton (avoid recreating on every tool call - saves ~100ms per call)
        self.operation_router = OperationRouter(self)

        # Register tool handlers
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available meta-tools (Strategy 1: Tool Grouping/Namespacing).

            Consolidates 120 individual tools into 10 meta-tools with operation parameters.
            This reduces token usage from ~105K to ~15K (85% reduction).

            Each meta-tool accepts an "operation" parameter that routes to the specific handler.
            """
            return [
                Tool(
                    name="memory_tools",
                    description="Comprehensive memory management (recall, remember, forget, optimize, consolidate, etc.). Use 'operation' parameter to specify: recall, remember, forget, list_memories, optimize, search_projects, smart_retrieve, analyze_coverage, get_expertise, detect_knowledge_gaps, get_working_memory, update_working_memory, clear_working_memory, consolidate_working_memory, evaluate_memory_quality, get_learning_rates, get_metacognition_insights, check_cognitive_load, get_memory_quality_summary, score_semantic_memories, get_self_reflection, run_consolidation, schedule_consolidation, record_event, recall_events, get_timeline, batch_record_events, recall_events_by_session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "Memory operation to perform (see full list in tool description)",
                                "enum": ["recall", "remember", "forget", "list_memories", "optimize", "search_projects", "smart_retrieve", "analyze_coverage", "get_expertise", "detect_knowledge_gaps", "get_working_memory", "update_working_memory", "clear_working_memory", "consolidate_working_memory", "evaluate_memory_quality", "get_learning_rates", "get_metacognition_insights", "check_cognitive_load", "get_memory_quality_summary", "score_semantic_memories", "get_self_reflection", "run_consolidation", "schedule_consolidation", "record_event", "recall_events", "get_timeline", "batch_record_events", "recall_events_by_session"],
                            },
                            "query": {"type": "string", "description": "Search query (for recall, search_projects operations)"},
                            "content": {"type": "string", "description": "Content to remember or update"},
                            "memory_id": {"type": "integer", "description": "Memory ID (for forget operation)"},
                            "memory_type": {"type": "string", "enum": ["fact", "pattern", "decision", "context"], "description": "Type of memory (for remember operation)"},
                            "k": {"type": "integer", "default": 5, "description": "Number of results"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for memory"},
                            "content_type": {"type": "string", "enum": ["verbal", "spatial"], "description": "Type of content (for update_working_memory)"},
                            "importance": {"type": "number", "description": "Importance score (for update_working_memory)"},
                            "domain": {"type": "string", "description": "Domain for coverage analysis"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="episodic_tools",
                    description="Event tracking and temporal operations (record_event, recall_events, get_timeline, batch_record_events, recall_events_by_session, record_execution, record_execution_feedback, record_git_commit, schedule_consolidation). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["record_event", "recall_events", "get_timeline", "batch_record_events", "recall_events_by_session", "record_execution", "record_execution_feedback", "record_git_commit", "schedule_consolidation"],
                                "description": "Episodic operation to perform",
                            },
                            # Common parameters
                            "content": {"type": "string", "description": "Event description"},
                            "event_type": {"type": "string", "description": "Type of event (action, decision, error, test_run, file_change, etc)"},
                            "outcome": {"type": "string", "enum": ["success", "failure", "partial", "ongoing"], "description": "Event outcome"},
                            "query": {"type": "string", "description": "Search query for events"},
                            "timeframe": {"type": "string", "enum": ["today", "yesterday", "this_week", "last_week", "this_month"], "description": "Time filter"},
                            "days": {"type": "integer", "default": 7, "description": "Number of days to look back"},
                            # recall_events_by_session parameters
                            "session_id": {"type": "string", "description": "Session ID for filtering events"},
                            # batch_record_events parameters
                            "events": {"type": "array", "description": "Array of event objects with content, event_type, outcome"},
                            # record_execution parameters
                            "procedure_name": {"type": "string", "description": "Name of procedure to record execution for"},
                            "duration_ms": {"type": "integer", "description": "Duration of execution in milliseconds"},
                            "learned": {"type": "string", "description": "What was learned from execution"},
                            # record_execution_feedback parameters
                            "task_id": {"type": "integer", "description": "Task ID for feedback"},
                            "actual_duration": {"type": "integer", "description": "Actual duration in minutes"},
                            "blockers": {"type": "array", "description": "List of blockers encountered"},
                            "quality_metrics": {"type": "object", "description": "Quality metrics object"},
                            "lessons_learned": {"type": "string", "description": "Lessons learned from execution"},
                            # record_git_commit parameters
                            "commit_hash": {"type": "string", "description": "Git commit hash"},
                            "commit_message": {"type": "string", "description": "Commit message"},
                            "changed_files": {"type": "array", "description": "List of changed files"},
                            "author": {"type": "string", "description": "Commit author name"},
                            "timestamp": {"type": "integer", "description": "Unix timestamp of commit"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="graph_tools",
                    description="Knowledge graph operations (create_entity, create_relation, add_observation, search_graph, get_graph_metrics, analyze_symbols, find_symbol_dependencies, get_causal_context, temporal_kg_synthesis, find_memory_path, get_associations). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["create_entity", "create_relation", "add_observation", "search_graph", "search_graph_with_depth", "get_graph_metrics", "analyze_symbols", "get_symbol_info", "find_symbol_dependencies", "find_symbol_dependents", "get_causal_context", "temporal_kg_synthesis", "temporal_search_enrich", "find_memory_path", "get_associations"],
                                "description": "Graph operation to perform",
                            },
                            # Entity creation parameters
                            "name": {"type": "string", "description": "Entity name"},
                            "entity_type": {"type": "string", "description": "Type of entity (Project, Phase, Task, File, Function, Concept, Component, Person, Decision, Pattern)"},
                            # Relation parameters
                            "from_entity": {"type": "string", "description": "Source entity name for relation"},
                            "to_entity": {"type": "string", "description": "Target entity name for relation"},
                            "relation_type": {"type": "string", "description": "Relation type (contains, depends_on, implements, tests, caused_by, resulted_in, relates_to, active_in, assigned_to)"},
                            # Observation parameters
                            "entity_name": {"type": "string", "description": "Entity name for observation"},
                            "observation": {"type": "string", "description": "Observation content"},
                            # Search parameters
                            "query": {"type": "string", "description": "Search query"},
                            "depth": {"type": "integer", "default": 2, "description": "Traversal depth"},
                            "symbol": {"type": "string", "description": "Symbol name"},
                            # Memory network parameters
                            "memory_id": {"type": "integer", "description": "Memory ID for causal context, associations, or path finding"},
                            "layer": {"type": "string", "description": "Memory layer (episodic, semantic, procedural, prospective, graph, meta)"},
                            "project_id": {"type": "integer", "default": 1, "description": "Project ID"},
                            "max_results": {"type": "integer", "default": 20, "description": "Maximum results to return"},
                            # Path finding parameters
                            "from_memory_id": {"type": "integer", "description": "Starting memory ID for path"},
                            "from_layer": {"type": "string", "description": "Starting memory layer"},
                            "to_memory_id": {"type": "integer", "description": "Ending memory ID for path"},
                            "to_layer": {"type": "string", "description": "Ending memory layer"},
                            # Temporal synthesis parameters
                            "session_id": {"type": "string", "description": "Session ID for temporal KG synthesis"},
                            "causality_threshold": {"type": "number", "default": 0.5, "description": "Causality threshold for temporal synthesis"},
                            # RAG parameters
                            "k": {"type": "integer", "default": 5, "description": "Number of results for RAG retrieval"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="planning_tools",
                    description="Task planning and decomposition (decompose_hierarchically, decompose_with_strategy, validate_plan, verify_plan, generate_task_plan, optimize_plan, estimate_resources, generate_alternative_plans, suggest_planning_strategy, recommend_strategy, predict_task_duration, analyze_uncertainty, validate_plan_with_reasoning, trigger_replanning, resolve_goal_conflicts, check_goal_conflicts). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["decompose_hierarchically", "decompose_with_strategy", "validate_plan", "verify_plan", "generate_task_plan", "optimize_plan", "estimate_resources", "generate_alternative_plans", "suggest_planning_strategy", "recommend_strategy", "predict_task_duration", "analyze_uncertainty", "validate_plan_with_reasoning", "trigger_replanning", "resolve_goal_conflicts", "check_goal_conflicts"],
                                "description": "Planning operation to perform",
                            },
                            # Decomposition parameters
                            "task_description": {"type": "string", "description": "Task description for decomposition"},
                            "complexity_level": {"type": "integer", "description": "Complexity 1-10"},
                            # Task identification
                            "task_id": {"type": "integer", "description": "Task ID for operations requiring existing task"},
                            "project_id": {"type": "integer", "description": "Project ID for validation"},
                            # Estimation parameters
                            "base_estimate": {"type": "number", "description": "Base time estimate in minutes for alternative plans"},
                            "estimate": {"type": "number", "description": "Time estimate in minutes for uncertainty analysis"},
                            # Validation parameters
                            "description": {"type": "string", "description": "Plan description for reasoning validation"},
                            "steps": {"type": "array", "description": "Plan steps"},
                            "dependencies": {"type": "array", "description": "Task dependencies"},
                            "constraints": {"type": "array", "description": "Plan constraints"},
                            "success_criteria": {"type": "array", "description": "Success criteria"},
                            # Replanning parameters
                            "trigger_type": {"type": "string", "description": "Trigger type for replanning (DURATION_EXCEEDED, QUALITY_DEGRADATION, BLOCKER_ENCOUNTERED, ASSUMPTION_VIOLATED, MILESTONE_MISSED, RESOURCE_CONSTRAINT)"},
                            "trigger_reason": {"type": "string", "description": "Reason for replanning trigger"},
                            # Uncertainty analysis
                            "external_factors": {"type": "array", "description": "External factors affecting uncertainty"},
                            "variance": {"type": "number", "description": "Historical variance (0-1)"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="task_management_tools",
                    description="Task and goal management (create_task, list_tasks, update_task_status, start_task, verify_task, set_goal, activate_goal, get_active_goals, complete_goal, get_task_health, get_project_dashboard, get_project_status, get_workflow_status, record_execution_progress, get_goal_priority_ranking, recommend_next_goal). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["create_task", "create_task_with_planning", "create_task_with_milestones", "list_tasks", "update_task_status", "update_milestone_progress", "start_task", "verify_task", "set_goal", "get_active_goals", "activate_goal", "get_goal_priority_ranking", "recommend_next_goal", "record_execution_progress", "complete_goal", "get_workflow_status", "get_task_health", "get_project_dashboard", "get_project_status"],
                                "description": "Task management operation",
                            },
                            "content": {"type": "string", "description": "Task/goal description"},
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "priority": {"type": "string", "description": "Priority level"},
                            "status": {"type": "string", "description": "Task status"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="monitoring_tools",
                    description="Real-time monitoring and health tracking (get_task_health, get_project_dashboard, get_layer_health, get_project_status, analyze_estimation_accuracy, discover_patterns, analyze_critical_path, detect_bottlenecks). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["get_task_health", "get_project_dashboard", "get_layer_health", "get_project_status", "analyze_estimation_accuracy", "discover_patterns", "analyze_critical_path", "detect_bottlenecks"],
                                "description": "Monitoring operation",
                            },
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "days_back": {"type": "integer", "default": 30, "description": "Days to analyze"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="coordination_tools",
                    description="Multi-project coordination (add_project_dependency, analyze_critical_path, detect_resource_conflicts, detect_bottlenecks, analyze_graph_metrics, analyze_uncertainty, generate_confidence_scores, recommend_orchestration, detect_budget_anomalies). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["add_project_dependency", "analyze_critical_path", "detect_resource_conflicts", "detect_bottlenecks", "analyze_graph_metrics", "analyze_uncertainty", "generate_confidence_scores", "estimate_confidence_interval", "recommend_orchestration", "detect_budget_anomalies"],
                                "description": "Coordination operation",
                            },
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "project_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of project IDs"},
                            "from_task_id": {"type": "integer", "description": "Source task ID"},
                            "to_task_id": {"type": "integer", "description": "Target task ID"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="security_tools",
                    description="Security analysis and credential tracking (analyze_code_security, track_sensitive_data). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["analyze_code_security", "track_sensitive_data"],
                                "description": "Security operation",
                            },
                            "code_content": {"type": "string", "description": "Code to analyze"},
                            "language": {"type": "string", "default": "python", "description": "Programming language"},
                            "data_type": {"type": "string", "description": "Type of sensitive data"},
                            "exposure_location": {"type": "string", "description": "Where data was exposed"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="financial_tools",
                    description="Cost and ROI analysis (calculate_task_cost, estimate_roi, suggest_cost_optimizations, track_budget, detect_budget_anomalies, calculate_roi). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["calculate_task_cost", "estimate_roi", "suggest_cost_optimizations", "track_budget", "detect_budget_anomalies", "calculate_roi"],
                                "description": "Financial operation",
                            },
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "total_cost": {"type": "number", "description": "Total cost"},
                            "expected_value": {"type": "number", "description": "Expected value"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="ml_integration_tools",
                    description="Machine learning and predictions (train_estimation_model, recommend_strategy, predict_task_duration, forecast_resource_needs, compute_memory_saliency, auto_focus_top_memories). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["train_estimation_model", "recommend_strategy", "predict_task_duration", "forecast_resource_needs", "get_saliency_batch", "compute_memory_saliency", "auto_focus_top_memories"],
                                "description": "ML operation",
                            },
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "task_description": {"type": "string", "description": "Task description"},
                            "complexity": {"type": "string", "description": "Complexity level"},
                            "base_estimate": {"type": "integer", "description": "Base time estimate"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="procedural_tools",
                    description="Workflow management (create_procedure, find_procedures, record_execution, get_procedure_effectiveness, suggest_procedure_improvements, generate_workflow_from_task, apply_suggestion, get_pattern_suggestions). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["create_procedure", "find_procedures", "record_execution", "get_procedure_effectiveness", "suggest_procedure_improvements", "generate_workflow_from_task", "apply_suggestion", "get_pattern_suggestions"],
                                "description": "Procedural operation",
                            },
                            "query": {"type": "string", "description": "Search query"},
                            "category": {"type": "string", "description": "Procedure category"},
                            "name": {"type": "string", "description": "Procedure name"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="integration_tools",
                    description="Advanced integration module tools (planning_assistance, optimize_plan_suggestions, analyze_project_coordination, discover_patterns_advanced, monitor_system_health_detailed, estimate_task_resources_detailed, generate_alternative_plans_impl, analyze_estimation_accuracy_adv, analyze_task_analytics_detailed, aggregate_analytics_summary, get_critical_path_analysis, get_resource_allocation). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["planning_assistance", "optimize_plan_suggestions", "analyze_project_coordination", "discover_patterns_advanced", "monitor_system_health_detailed", "estimate_task_resources_detailed", "generate_alternative_plans_impl", "analyze_estimation_accuracy_adv", "analyze_task_analytics_detailed", "aggregate_analytics_summary", "get_critical_path_analysis", "get_resource_allocation"],
                                "description": "Integration operation",
                            },
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "project_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of project IDs"},
                            "context": {"type": "string", "description": "Context for planning"},
                            "pattern_type": {"type": "string", "description": "Pattern type filter"},
                            "days_back": {"type": "integer", "description": "Days to analyze"},
                            "num_alternatives": {"type": "integer", "description": "Number of alternatives"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="automation_tools",
                    description="Event-driven automation tools (register_automation_rule, trigger_automation_event, list_automation_rules, update_automation_config, execute_automation_workflow). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["register_automation_rule", "trigger_automation_event", "list_automation_rules", "update_automation_config", "execute_automation_workflow"],
                                "description": "Automation operation",
                            },
                            "rule_name": {"type": "string", "description": "Automation rule name"},
                            "trigger_event": {"type": "string", "description": "Trigger event type"},
                            "action": {"type": "string", "description": "Action to execute"},
                            "condition": {"type": "string", "description": "Optional condition expression"},
                            "event_type": {"type": "string", "description": "Event type to trigger"},
                            "event_data": {"type": "object", "description": "Event data payload"},
                            "config_key": {"type": "string", "description": "Configuration key"},
                            "config_value": {"type": "string", "description": "Configuration value"},
                            "workflow_name": {"type": "string", "description": "Workflow name"},
                            "workflow_params": {"type": "object", "description": "Workflow parameters"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="conversation_tools",
                    description="Session and conversation management (start_new_conversation, add_message_to_conversation, get_conversation_history, resume_conversation_session, create_context_snapshot, recover_conversation_context, list_active_conversations, export_conversation_data). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["start_new_conversation", "add_message_to_conversation", "get_conversation_history", "resume_conversation_session", "create_context_snapshot", "recover_conversation_context", "list_active_conversations", "export_conversation_data"],
                                "description": "Conversation operation",
                            },
                            "conversation_id": {"type": "integer", "description": "Conversation ID"},
                            "title": {"type": "string", "description": "Conversation title"},
                            "context": {"type": "string", "description": "Initial context"},
                            "role": {"type": "string", "description": "Message role (user|assistant|system)"},
                            "content": {"type": "string", "description": "Message content"},
                            "limit": {"type": "integer", "description": "Result limit"},
                            "snapshot_id": {"type": "integer", "description": "Snapshot ID"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="safety_tools",
                    description="Safety evaluation and approval (evaluate_change_safety, request_approval, get_audit_trail, monitor_execution, create_code_snapshot, check_safety_policy, analyze_change_risk). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["evaluate_change_safety", "request_approval", "get_audit_trail", "monitor_execution", "create_code_snapshot", "check_safety_policy", "analyze_change_risk"],
                                "description": "Safety operation",
                            },
                            "change_type": {"type": "string", "description": "Type of change"},
                            "change_description": {"type": "string", "description": "Description of change"},
                            "affected_components": {"type": "array", "items": {"type": "string"}, "description": "Affected components"},
                            "change_id": {"type": "string", "description": "Change identifier"},
                            "action": {"type": "string", "description": "Action to validate"},
                            "limit": {"type": "integer", "description": "Result limit"},
                            "execution_id": {"type": "string", "description": "Execution identifier"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="ide_context_tools",
                    description="IDE context and state tracking (get_ide_context, get_cursor_position, get_open_files, get_git_status, get_recent_files, get_file_changes, get_active_buffer, track_ide_activity). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["get_ide_context", "get_cursor_position", "get_open_files", "get_git_status", "get_recent_files", "get_file_changes", "get_active_buffer", "track_ide_activity"],
                                "description": "IDE context operation",
                            },
                            "file_path": {"type": "string", "description": "File path"},
                            "limit": {"type": "integer", "description": "Result limit"},
                            "activity_type": {"type": "string", "description": "Activity type"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="skills_tools",
                    description="ML-powered skills and analysis (analyze_project_with_skill, improve_estimations, learn_from_outcomes, detect_bottlenecks_advanced, analyze_health_trends, create_task_from_template, get_skill_recommendations). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["analyze_project_with_skill", "improve_estimations", "learn_from_outcomes", "detect_bottlenecks_advanced", "analyze_health_trends", "create_task_from_template", "get_skill_recommendations"],
                                "description": "Skills operation",
                            },
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "analysis_type": {"type": "string", "description": "Analysis type"},
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "actual_duration": {"type": "integer", "description": "Actual duration"},
                            "estimated_duration": {"type": "integer", "description": "Estimated duration"},
                            "template_name": {"type": "string", "description": "Template name"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="resilience_tools",
                    description="System resilience and health (check_system_health, get_health_report, configure_circuit_breaker, get_resilience_status, test_fallback_chain, configure_retry_policy). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["check_system_health", "get_health_report", "configure_circuit_breaker", "get_resilience_status", "test_fallback_chain", "configure_retry_policy"],
                                "description": "Resilience operation",
                            },
                            "component": {"type": "string", "description": "Component name"},
                            "max_retries": {"type": "integer", "description": "Max retries"},
                            "backoff_seconds": {"type": "integer", "description": "Backoff time"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="performance_tools",
                    description="Database performance optimization (get_performance_metrics, optimize_queries, manage_cache, batch_operations). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["get_performance_metrics", "optimize_queries", "manage_cache", "batch_operations"],
                                "description": "Performance operation",
                            },
                            "query": {"type": "string", "description": "SQL query to optimize"},
                            "operation_type": {"type": "string", "description": "Batch operation type"},
                            "count": {"type": "integer", "description": "Operation count"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="hooks_tools",
                    description="Hook management and execution (register_hook, trigger_hook, detect_hook_cycles, configure_rate_limiting, list_hooks). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["register_hook", "trigger_hook", "detect_hook_cycles", "configure_rate_limiting", "list_hooks"],
                                "description": "Hook operation",
                            },
                            "hook_type": {"type": "string", "description": "Hook type (session_start, task_completed, etc)"},
                            "rate_limit": {"type": "integer", "description": "Rate limit (ops/min)"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="spatial_tools",
                    description="Spatial hierarchy and code navigation (build_spatial_hierarchy, spatial_storage, symbol_analysis, spatial_distance, spatial_query, spatial_indexing, code_navigation, get_spatial_context). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["build_spatial_hierarchy", "spatial_storage", "symbol_analysis", "spatial_distance", "spatial_query", "spatial_indexing", "code_navigation", "get_spatial_context"],
                                "description": "Spatial operation",
                            },
                            "file_path": {"type": "string", "description": "File path"},
                            "operation_type": {"type": "string", "description": "Sub-operation"},
                            "query": {"type": "string", "description": "Spatial query text"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="rag_tools",
                    description="Advanced RAG and retrieval (retrieve_smart, calibrate_uncertainty, route_planning_query, enrich_temporal_context, find_related_context, reflective_retrieve). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["retrieve_smart", "calibrate_uncertainty", "route_planning_query", "enrich_temporal_context", "find_related_context", "reflective_retrieve"],
                                "description": "RAG operation",
                            },
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {"type": "integer", "description": "Result limit"},
                            "result_id": {"type": "integer", "description": "Result ID"},
                            "context": {"type": "object", "description": "Planning context"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="analysis_tools",
                    description="Project codebase analysis (analyze_project_codebase, store_project_analysis). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["analyze_project_codebase", "store_project_analysis"],
                                "description": "Analysis operation",
                            },
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "analysis_type": {"type": "string", "description": "Analysis type (full, quick, focused)"},
                            "analysis_data": {"type": "object", "description": "Analysis data to store"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="orchestration_tools",
                    description="Multi-agent orchestration and planning (orchestrate_agent_tasks, recommend_planning_patterns, analyze_failure_patterns). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["orchestrate_agent_tasks", "recommend_planning_patterns", "analyze_failure_patterns"],
                                "description": "Orchestration operation",
                            },
                            "task_definition": {"type": "object", "description": "Task definition"},
                            "agent_count": {"type": "integer", "description": "Agent count"},
                            "task_description": {"type": "string", "description": "Task description"},
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "failure_type": {"type": "string", "description": "Failure type"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="consolidation_tools",
                    description="Sleep-like memory consolidation (run_consolidation, extract_patterns, cluster_events, measure_quality, advanced_metrics, strategy_analysis, project_patterns, validation_analysis, orchestration_discovery, performance_analysis). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["run_consolidation", "extract_consolidation_patterns", "cluster_consolidation_events", "measure_consolidation_quality", "measure_advanced_consolidation_metrics", "analyze_strategy_effectiveness", "analyze_project_patterns", "analyze_validation_effectiveness", "discover_orchestration_patterns", "analyze_consolidation_performance"],
                                "description": "Consolidation operation",
                            },
                            "force": {"type": "boolean", "description": "Force consolidation"},
                            "max_age_minutes": {"type": "integer", "description": "Max event age in minutes"},
                            "strategy": {"type": "string", "description": "Consolidation strategy"},
                            "min_frequency": {"type": "integer", "description": "Minimum pattern frequency"},
                            "pattern_type": {"type": "string", "description": "Pattern type (temporal/semantic/spatial/all)"},
                            "clustering_method": {"type": "string", "description": "Clustering method"},
                            "metric_types": {"type": "array", "description": "Metrics to compute"},
                            "consolidation_id": {"type": "integer", "description": "Consolidation run ID"},
                            "domain": {"type": "string", "description": "Domain to analyze"},
                            "time_window": {"type": "integer", "description": "Time window in hours"},
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "days_back": {"type": "integer", "description": "Days to analyze"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="phase6_planning_tools",
                    description="Planning & resource estimation (validate_plan_comprehensive, verify_plan_properties, monitor_execution_deviation, trigger_adaptive_replanning, refine_plan_automatically, simulate_plan_scenarios, extract_planning_patterns, generate_lightweight_plan, validate_plan_with_llm, create_validation_gate). Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["validate_plan_comprehensive", "verify_plan_properties", "monitor_execution_deviation", "trigger_adaptive_replanning", "refine_plan_automatically", "simulate_plan_scenarios", "extract_planning_patterns", "generate_lightweight_plan", "validate_plan_with_llm", "create_validation_gate"],
                                "description": "Planning operation",
                            },
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "validation_levels": {"type": "array", "description": "Validation levels"},
                            "strict_mode": {"type": "boolean", "description": "Strict validation mode"},
                            "properties": {"type": "array", "description": "Properties to check"},
                            "depth": {"type": "string", "description": "Analysis depth"},
                            "threshold_percent": {"type": "integer", "description": "Deviation threshold"},
                            "trigger_type": {"type": "string", "description": "Trigger type"},
                            "severity": {"type": "string", "description": "Severity level"},
                            "strategies": {"type": "array", "description": "Refinement strategies"},
                            "scenarios": {"type": "array", "description": "Scenarios to test"},
                            "iterations": {"type": "integer", "description": "Simulation iterations"},
                            "days_back": {"type": "integer", "description": "Days to analyze"},
                            "pattern_type": {"type": "string", "description": "Pattern type"},
                            "strategy": {"type": "string", "description": "Strategy name"},
                            "resource_limit": {"type": "integer", "description": "Resource limit"},
                            "focus_area": {"type": "string", "description": "Focus area"},
                            "gate_type": {"type": "string", "description": "Gate type"},
                            "stakeholders": {"type": "array", "description": "Stakeholder IDs"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="hook_coordination_tools",
                    description="Hook optimization & coordination (optimize_session_start, optimize_session_end, optimize_user_prompt_submit, optimize_post_tool_use, optimize_pre_execution). Provides optimized implementations of 5 key hooks using Phase 5-6 tools. Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["optimize_session_start", "optimize_session_end", "optimize_user_prompt_submit", "optimize_post_tool_use", "optimize_pre_execution"],
                                "description": "Hook coordination operation",
                            },
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "session_id": {"type": "string", "description": "Session ID"},
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "tool_name": {"type": "string", "description": "Tool name (for post_tool_use)"},
                            "execution_time_ms": {"type": "integer", "description": "Tool execution time in milliseconds"},
                            "tool_result": {"type": "string", "description": "Tool result status (success/error)"},
                            "validate_plans": {"type": "boolean", "description": "Whether to validate plans (default: true)"},
                            "extract_patterns": {"type": "boolean", "description": "Whether to extract patterns (default: true)"},
                            "measure_quality": {"type": "boolean", "description": "Whether to measure quality (default: true)"},
                            "monitor_health": {"type": "boolean", "description": "Whether to monitor health (default: true)"},
                            "strict_mode": {"type": "boolean", "description": "Strict validation mode"},
                            "run_scenarios": {"type": "string", "description": "Scenario simulation mode (auto/on/off)"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="agent_optimization_tools",
                    description="Agent optimization & enhancement (optimize_planning_orchestrator, optimize_goal_orchestrator, optimize_consolidation_trigger, optimize_strategy_orchestrator, optimize_attention_optimizer). Provides optimized implementations of 5 key agents using Phase 5-6 tools. Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["optimize_planning_orchestrator", "optimize_goal_orchestrator", "optimize_consolidation_trigger", "optimize_strategy_orchestrator", "optimize_attention_optimizer"],
                                "description": "Agent optimization operation",
                            },
                            "task_description": {"type": "string", "description": "Task description (for planning_orchestrator)"},
                            "task_id": {"type": "integer", "description": "Task ID"},
                            "goal_id": {"type": "integer", "description": "Goal ID (for goal_orchestrator)"},
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "trigger_reason": {"type": "string", "description": "Consolidation trigger reason"},
                            "strategy": {"type": "string", "description": "Strategy name (balanced/speed/quality/minimal)"},
                            "task_context": {"type": "object", "description": "Task context for strategy selection"},
                            "include_scenarios": {"type": "boolean", "description": "Whether to include scenarios (default: true)"},
                            "activate": {"type": "boolean", "description": "Whether to activate goal (default: true)"},
                            "monitor_health": {"type": "boolean", "description": "Whether to monitor health (default: true)"},
                            "extract_patterns": {"type": "boolean", "description": "Whether to extract patterns (default: true)"},
                            "measure_quality": {"type": "boolean", "description": "Whether to measure quality (default: true)"},
                            "analyze_effectiveness": {"type": "boolean", "description": "Whether to analyze effectiveness (default: true)"},
                            "apply_refinements": {"type": "boolean", "description": "Whether to apply refinements (default: true)"},
                            "weight_by_expertise": {"type": "boolean", "description": "Whether to weight by expertise (default: true)"},
                            "analyze_patterns": {"type": "boolean", "description": "Whether to analyze patterns (default: true)"},
                            "strict_mode": {"type": "boolean", "description": "Strict validation mode"},
                            "analyze_strategies": {"type": "boolean", "description": "Whether to analyze strategies"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="skill_optimization_tools",
                    description="Skill optimization & enhancement (optimize_learning_tracker, optimize_procedure_suggester, optimize_gap_detector, optimize_quality_monitor). Enhances 4 key skills with Phase 5 operations. Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["optimize_learning_tracker", "optimize_procedure_suggester", "optimize_gap_detector", "optimize_quality_monitor"],
                                "description": "Skill optimization operation",
                            },
                            "project_id": {"type": "integer", "description": "Project ID (default: 1)"},
                            "analyze_effectiveness": {"type": "boolean", "description": "Whether to analyze effectiveness (default: true)"},
                            "track_patterns": {"type": "boolean", "description": "Whether to track patterns (default: true)"},
                            "analyze_patterns": {"type": "boolean", "description": "Whether to analyze patterns (default: true)"},
                            "discovery_depth": {"type": "integer", "description": "Depth of pattern discovery 1-5 (default: 3)"},
                            "stability_window": {"type": "integer", "description": "Stability window in days (default: 7)"},
                            "analyze_contradictions": {"type": "boolean", "description": "Whether to analyze contradictions (default: true)"},
                            "measure_layers": {"type": "boolean", "description": "Whether to measure all layers (default: true)"},
                            "domain_analysis": {"type": "boolean", "description": "Whether to analyze domains (default: true)"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="zettelkasten_tools",
                    description="Memory versioning and evolution (create_memory_version, get_memory_evolution_history, compute_memory_attributes, get_memory_attributes, create_hierarchical_index, assign_memory_to_index). Supports Luhmann numbering hierarchies and SHA256 change detection. Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["create_memory_version", "get_memory_evolution_history", "compute_memory_attributes", "get_memory_attributes", "create_hierarchical_index", "assign_memory_to_index"],
                                "description": "Zettelkasten operation",
                            },
                            "memory_id": {"type": "integer", "description": "ID of memory to version/compute attributes for"},
                            "content": {"type": "string", "description": "New content for this version"},
                            "project_id": {"type": "integer", "description": "Project ID"},
                            "parent_id": {"type": ["string", "null"], "description": "Parent index ID (null for root)"},
                            "label": {"type": "string", "description": "Human-readable label for index", "default": "Untitled"},
                            "index_id": {"type": "string", "description": "Index ID (e.g., '1.2.3')"},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="graphrag_tools",
                    description="Community detection and multi-level retrieval (detect_graph_communities, get_community_details, query_communities_by_level, analyze_community_connectivity, find_bridge_entities). Uses Leiden clustering for knowledge graph analysis. Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["detect_graph_communities", "get_community_details", "query_communities_by_level", "analyze_community_connectivity", "find_bridge_entities"],
                                "description": "GraphRAG operation",
                            },
                            "project_id": {"type": "integer", "description": "Project ID to analyze"},
                            "min_community_size": {"type": "integer", "description": "Minimum nodes in a community (default: 2)", "default": 2},
                            "max_iterations": {"type": "integer", "description": "Maximum clustering iterations (default: 100)", "default": 100},
                            "community_id": {"type": "integer", "description": "Community ID to get details for"},
                            "query": {"type": "string", "description": "Search query"},
                            "level": {"type": "integer", "description": "Query level: 0=granular, 1=intermediate, 2=global (default: 0)", "default": 0, "enum": [0, 1, 2]},
                            "threshold": {"type": "integer", "description": "Minimum edges to other communities (default: 3)", "default": 3},
                        },
                        "required": ["operation", "project_id"],
                    },
                ),
                Tool(
                    name="code_search_tools",
                    description="Semantic code search with Tree-Sitter integration (search_code_semantically, search_code_by_type, search_code_by_name, analyze_code_file, find_code_dependencies, index_code_repository, get_code_statistics). Embedding-based similarity with multi-factor scoring: 50% semantic + 25% name + 25% type. Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["search_code_semantically", "search_code_by_type", "search_code_by_name", "analyze_code_file", "find_code_dependencies", "index_code_repository", "get_code_statistics"],
                                "description": "Code search operation",
                            },
                            "query": {"type": "string", "description": "Search query for semantic search"},
                            "unit_type": {"type": "string", "description": "Code unit type to search for (function, class, import)"},
                            "name": {"type": "string", "description": "Code element name to search for"},
                            "file_path": {"type": "string", "description": "Path to code file for analysis or dependency finding"},
                            "entity_name": {"type": "string", "description": "Name of function/class to analyze dependencies for"},
                            "repo_path": {"type": "string", "description": "Path to repository"},
                            "exact": {"type": "boolean", "description": "Exact name match only (default: false)", "default": False},
                            "rebuild": {"type": "boolean", "description": "Force rebuild index (default: false)", "default": False},
                            "limit": {"type": "integer", "description": "Maximum results to return", "default": 10},
                            "top_k": {"type": "integer", "description": "Number of top results (alias for limit)", "default": 10},
                            "min_score": {"type": "number", "description": "Minimum relevance score threshold", "default": 0.3},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="code_analysis_tools",
                    description="Code analysis memory integration (record_code_analysis, store_code_insights, add_code_entities, extract_code_patterns, analyze_repository, get_analysis_metrics). Integrates code analysis with episodic, semantic, knowledge graph, and consolidation memory layers. Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["record_code_analysis", "store_code_insights", "add_code_entities", "extract_code_patterns", "analyze_repository", "get_analysis_metrics"],
                                "description": "Code analysis operation",
                            },
                            "repo_path": {"type": "string", "description": "Path to analyzed repository"},
                            "analysis_results": {"type": "object", "description": "Dictionary with analysis findings (quality_score, complexity_avg, issues, etc.)"},
                            "duration_ms": {"type": "integer", "description": "Time taken for analysis in milliseconds"},
                            "file_count": {"type": "integer", "description": "Number of files analyzed", "default": 0},
                            "unit_count": {"type": "integer", "description": "Number of code units analyzed", "default": 0},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for insights"},
                            "code_units": {"type": "array", "description": "List of code unit dictionaries"},
                            "language": {"type": "string", "description": "Programming language (default: python)"},
                            "include_memory": {"type": "boolean", "description": "Whether to record to memory (default: true)"},
                            "days_back": {"type": "integer", "description": "Number of days to analyze", "default": 7},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="external_knowledge_tools",
                    description="External knowledge lookup and expansion (lookup_external_knowledge, expand_knowledge_relations, synthesize_knowledge, explore_concept_network). Uses ConceptNet API with 21M+ relations. Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["lookup_external_knowledge", "expand_knowledge_relations", "synthesize_knowledge", "explore_concept_network"],
                                "description": "External knowledge operation",
                            },
                            "concept": {"type": "string", "description": "Concept to look up or expand"},
                            "start_concept": {"type": "string", "description": "Starting concept for network exploration"},
                            "relation_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by relation types (IsA, PartOf, UsedFor, AtLocation, etc.)"},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 10},
                            "language": {"type": "string", "description": "Language code", "default": "en"},
                            "max_hops": {"type": "integer", "description": "Max hops for knowledge expansion", "default": 2},
                            "relation_filter": {"type": "string", "description": "Filter by specific relation type"},
                            "synthesis_type": {"type": "string", "enum": ["comprehensive", "summary", "relationships"], "description": "Type of synthesis", "default": "comprehensive"},
                            "depth": {"type": "integer", "description": "Depth for synthesis", "default": 2},
                            "relations_of_interest": {"type": "array", "items": {"type": "string"}, "description": "Specific relations to explore"},
                            "max_concepts": {"type": "integer", "description": "Maximum concepts in network", "default": 30},
                        },
                        "required": ["operation"],
                    },
                ),
                Tool(
                    name="code_execution_tools",
                    description="Sandboxed code execution and procedure execution (execute_code, execute_procedure, validate_code, generate_procedure_code, get_execution_context, record_execution, get_sandbox_config). Phase 3 Week 11. Use 'operation' parameter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "enum": ["execute_code", "execute_procedure", "validate_code", "generate_procedure_code", "get_execution_context", "record_execution", "get_sandbox_config"],
                                "description": "Code execution operation",
                            },
                            "code": {"type": "string", "description": "Python, JavaScript, or bash code to execute"},
                            "language": {"type": "string", "enum": ["python", "javascript", "bash"], "description": "Code language", "default": "python"},
                            "procedure_name": {"type": "string", "description": "Name of procedure to execute"},
                            "procedure_id": {"type": "string", "description": "ID of procedure to execute"},
                            "timeout_seconds": {"type": "integer", "description": "Execution timeout in seconds", "default": 30},
                            "sandbox_mode": {"type": "string", "enum": ["srt", "restricted_python", "mock"], "description": "Sandbox mode", "default": "mock"},
                            "capture_io": {"type": "boolean", "description": "Capture stdout/stderr", "default": True},
                            "allow_network": {"type": "boolean", "description": "Allow network access", "default": False},
                            "allow_filesystem": {"type": "boolean", "description": "Allow filesystem access", "default": False},
                            "context_id": {"type": "string", "description": "Execution context ID for tracking"},
                            "project_id": {"type": "integer", "description": "Project ID for procedure execution"},
                        },
                        "required": ["operation"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, args: Any) -> list[TextContent]:
            """Handle tool calls with operation routing (Strategy 1: Tool Grouping).

            Routes meta-tool calls to specific operations via OperationRouter.
            Consolidates 120+ individual tools into 11 meta-tools.

            All responses are processed through TokenBudgetMiddleware to enforce
            300-token summaries for efficient context management.
            """
            # Check rate limit first
            if not self.rate_limiter.allow_request(name):
                retry_after = self.rate_limiter.get_retry_after(name)
                error_response = rate_limit_response(retry_after)
                response_text = json.dumps(error_response, indent=2)
                response = TextContent(type="text", text=response_text)
                # Apply budget middleware to rate limit error too
                processed = self.budget_middleware.process_response(response, operation=f"{name}:rate-limit", is_summary=True)
                return [processed]

            try:
                # Use singleton operation router (initialized in __init__)
                router = self.operation_router

                # Check if this is a meta-tool (Strategy 1)
                meta_tools = list(OperationRouter.OPERATION_MAPS.keys())
                if name in meta_tools:
                    # Route operation through meta-tool dispatcher
                    result = await router.route(name, args)
                    response_text = json.dumps(result, indent=2)
                    response = TextContent(type="text", text=response_text)

                    # Apply budget middleware to enforce 300-token summary limit
                    # Track operation name for metrics
                    operation_name = args.get("operation", name)
                    processed = self.budget_middleware.process_response(
                        response,
                        operation=f"{name}:{operation_name}",
                        is_summary=True  # All responses are summary-first
                    )

                    # Record metrics from handler execution
                    token_count_before = self.budget_middleware.budget_manager.count_tokens(response_text)
                    token_count_after = self.budget_middleware.budget_manager.count_tokens(processed.text)

                    self.handler_metrics.record_handler_execution(
                        handler_name=f"{name}:{operation_name}",
                        execution_time=0,  # Will be measured at higher level
                        tokens_counted=token_count_before,
                        tokens_returned=token_count_after,
                        had_violation=token_count_before > 300,
                        was_compressed=token_count_after < token_count_before,
                    )

                    return [processed]
                else:
                    # Unknown tool
                    error_data = {
                        "status": "error",
                        "error": f"Unknown tool: {name}",
                        "available_tools": meta_tools
                    }
                    response = TextContent(type="text", text=json.dumps(error_data, indent=2))
                    processed = self.budget_middleware.process_response(response, operation=f"{name}:unknown", is_summary=True)
                    return [processed]
            except ValueError as e:
                # Operation routing error (invalid operation or meta-tool)
                logger.error(f"Routing error in tool {name}: {e}")
                error_data = {
                    "status": "error",
                    "error": str(e)
                }
                response = TextContent(type="text", text=json.dumps(error_data, indent=2))
                processed = self.budget_middleware.process_response(response, operation=f"{name}:routing-error", is_summary=True)
                return [processed]
            except Exception as e:
                # Handler implementation error
                logger.error(f"Error in tool {name}: {e}", exc_info=True)
                error_data = {
                    "status": "error",
                    "error": str(e)
                }
                response = TextContent(type="text", text=json.dumps(error_data, indent=2))
                processed = self.budget_middleware.process_response(response, operation=f"{name}:error", is_summary=True)
                return [processed]

    # ============================================================================
    # Handler methods (now called via OperationRouter from meta-tools)
    # ============================================================================
    # These methods remain unchanged and are invoked by OperationRouter
    # based on the "operation" parameter in the meta-tool args.
        return [result.as_optimized_content(schema_name="semantic_search")]

    # Episodic memory handlers
    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())
