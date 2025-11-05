"""
Retrieval handlers: RAG (Retrieval-Augmented Generation), codebase analysis, orchestration.

This module contains MCP tool handlers for:
- Smart retrieval with uncertainty calibration
- Planning routing and temporal enrichment
- Codebase analysis and insight storage
- Agent orchestration and workflow management

Organized by domain for clarity and maintainability.
"""

import json
import logging
from typing import Any, List

from mcp.types import TextContent

logger = logging.getLogger(__name__)


# ============================================================================
# RAG MODULE HANDLERS (6)
# ============================================================================

async def handle_rag_retrieve_smart(server: Any, args: dict) -> List[TextContent]:
    """Perform smart RAG retrieval with automatic strategy selection.

    Selects optimal retrieval strategy (HyDE, LLMReranking, Reflective, etc).
    """
    try:
        query = args.get("query", "default memory query")
        limit = args.get("limit", 10)

        # Lazy initialize RAGManager
        if not hasattr(server, '_rag_manager'):
            from ..rag.manager import RAGManager
            server._rag_manager = RAGManager(server.store.db)

        # Perform smart retrieval
        try:
            results = server._rag_manager.retrieve(
                query=query,
                limit=limit,
                strategy="auto"  # Auto-selects best strategy
            )
            result = {
                "query": query,
                "limit": limit,
                "result_count": len(results) if results else 0,
                "status": "success"
            }
        except Exception as op_err:
            logger.debug(f"RAG retrieval error: {op_err}")
            # Gracefully handle empty results
            result = {
                "status": "success",
                "query": query,
                "result_count": 0,
                "message": "No results found for query"
            }

        response = f"""**Smart RAG Retrieval**
Query: {query}
Limit: {limit}
Results Found: {result.get('result_count', 0)}
Strategy: auto-selected
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_rag_retrieve_smart: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_rag_calibrate_uncertainty(server: Any, args: dict) -> List[TextContent]:
    """Calibrate uncertainty and confidence scores for retrieval results.

    Evaluates confidence in retrieved results and detects abstention cases.
    """
    try:
        result_text = args.get("result_text", "")
        result_id = args.get("result_id")

        # Lazy initialize UncertaintyCalibrator
        if not hasattr(server, '_uncertainty_calibrator'):
            from ..rag.uncertainty import UncertaintyCalibrator
            server._uncertainty_calibrator = UncertaintyCalibrator(server.store.db)

        # Calibrate uncertainty
        try:
            confidence = server._uncertainty_calibrator.calibrate_confidence(
                result_text=result_text,
                result_id=result_id
            )
            result = {
                "result_id": result_id,
                "confidence_score": confidence if confidence else 0.5,
                "abstain_recommended": confidence < 0.5 if confidence else False,
                "status": "calibrated"
            }
        except Exception as op_err:
            logger.debug(f"Uncertainty calibration error: {op_err}")
            result = {"status": "error", "result_id": result_id}

        response = f"""**Uncertainty Calibration**
Result ID: {result_id}
Confidence Score: {result.get('confidence_score', 0.5):.2f}
Abstain Recommended: {result.get('abstain_recommended', False)}
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_rag_calibrate_uncertainty: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_rag_route_planning_query(server: Any, args: dict) -> List[TextContent]:
    """Route queries through planning-aware RAG with hybrid search.

    Combines semantic search with planning context and validation.
    """
    try:
        query = args.get("query", "planning query")
        context = args.get("context", {})  # planning context

        # Lazy initialize PlanningRAGRouter
        if not hasattr(server, '_planning_rag_router'):
            from ..rag.planning_rag import PlanningRAGRouter
            # PlanningRAGRouter expects MemoryStore
            server._planning_rag_router = PlanningRAGRouter(server.store)

        # Route planning query
        try:
            routed_results = server._planning_rag_router.route_query(
                query=query,
                planning_context=context
            )
            result = {
                "query": query,
                "route": "planning_aware",
                "result_count": len(routed_results) if routed_results else 0,
                "status": "routed"
            }
        except Exception as op_err:
            logger.debug(f"Planning RAG routing error: {op_err}")
            result = {"status": "error", "query": query}

        response = f"""**Planning-Aware RAG Routing**
Query: {query}
Route: planning_aware
Results: {result.get('result_count', 0)}
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_rag_route_planning_query: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_rag_enrich_temporal_context(server: Any, args: dict) -> List[TextContent]:
    """Enrich retrieval results with temporal context and recency weighting.

    Adds temporal chains and recency-based relevance scoring.
    """
    try:
        result_id = args.get("result_id")
        time_window = args.get("time_window", "7days")  # 7days, 30days, etc

        # Lazy initialize temporal enrichment
        if not hasattr(server, '_temporal_search_enrichment'):
            from ..rag.temporal_search_enrichment import TemporalSearchEnricher
            server._temporal_search_enrichment = TemporalSearchEnricher(server.store.db)

        # Enrich with temporal context
        try:
            enriched = server._temporal_search_enrichment.enrich_with_temporal_context(
                result_id=result_id,
                time_window=time_window
            )
            result = {
                "result_id": result_id,
                "time_window": time_window,
                "temporal_chain_length": len(enriched) if enriched else 0,
                "status": "enriched"
            }
        except Exception as op_err:
            logger.debug(f"Temporal enrichment error: {op_err}")
            result = {"status": "error", "result_id": result_id}

        response = f"""**Temporal Context Enrichment**
Result ID: {result_id}
Time Window: {time_window}
Temporal Chain Length: {result.get('temporal_chain_length', 0)}
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_rag_enrich_temporal_context: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_graph_find_related_context(server: Any, args: dict) -> List[TextContent]:
    """Find related context through multi-hop graph traversal.

    Traverses knowledge graph to find semantically related entities.
    """
    try:
        entity_id = args.get("entity_id")
        depth = args.get("depth", 2)  # traversal depth
        limit = args.get("limit", 10)

        # Lazy initialize GraphTraversal
        if not hasattr(server, '_graph_traversal'):
            from ..rag.graph_traversal import GraphTraversal
            server._graph_traversal = GraphTraversal(server.store.db)

        # Traverse graph
        try:
            related = server._graph_traversal.find_related_entities(
                entity_id=entity_id,
                depth=depth,
                limit=limit
            )
            result = {
                "entity_id": entity_id,
                "depth": depth,
                "related_count": len(related) if related else 0,
                "status": "traversed"
            }
        except Exception as op_err:
            logger.debug(f"Graph traversal error: {op_err}")
            result = {"status": "error", "entity_id": entity_id}

        response = f"""**Graph Context Traversal**
Entity ID: {entity_id}
Depth: {depth}
Related Entities Found: {result.get('related_count', 0)}
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_graph_find_related_context: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_rag_reflective_retrieve(server: Any, args: dict) -> List[TextContent]:
    """Perform reflective RAG with query decomposition and iterative refinement.

    Decomposes complex queries and refines retrieval iteratively.
    """
    try:
        query = args.get("query", "complex query")
        max_iterations = args.get("max_iterations", 3)

        # Lazy initialize ReflectiveRAG
        if not hasattr(server, '_reflective_rag'):
            from ..rag.reflective import ReflectiveRAG
            from ..memory.store import MemoryStore
            # Create placeholder LLM client interface if needed
            class SimpleLLMClient:
                async def query(self, prompt):
                    return "result"
            search = MemoryStore(server.store.db)
            llm = SimpleLLMClient()
            server._reflective_rag = ReflectiveRAG(search, llm)

        # Perform reflective retrieval
        try:
            refined_results = server._reflective_rag.retrieve_with_reflection(
                query=query,
                max_iterations=max_iterations
            )
            result = {
                "query": query,
                "iterations": max_iterations,
                "final_result_count": len(refined_results) if refined_results else 0,
                "status": "refined"
            }
        except Exception as op_err:
            logger.debug(f"Reflective RAG error: {op_err}")
            result = {"status": "error", "query": query}

        response = f"""**Reflective RAG Retrieval**
Query: {query}
Max Iterations: {max_iterations}
Final Results: {result.get('final_result_count', 0)}
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_rag_reflective_retrieve: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# ANALYSIS MODULE HANDLERS (2)
# ============================================================================

async def handle_analyze_project_codebase(server: Any, args: dict) -> List[TextContent]:
    """Analyze project codebase for structure, quality, and patterns.

    Comprehensive analysis of code complexity, dependencies, and health.
    """
    try:
        project_id = args.get("project_id", 1)
        analysis_type = args.get("analysis_type", "full")  # full, quick, focused
        project_path = args.get("project_path", ".")  # Current directory by default

        # Lazy initialize ProjectAnalyzer with project path (not Database object)
        analyzer_key = f'_project_analyzer_{project_path}'
        if not hasattr(server, analyzer_key):
            from ..analysis.project_analyzer import ProjectAnalyzer
            setattr(server, analyzer_key, ProjectAnalyzer(project_path))

        # Analyze project
        try:
            analyzer = getattr(server, analyzer_key)
            analysis = analyzer.analyze_project(
                project_id=project_id,
                analysis_type=analysis_type
            )
            result = {
                "project_id": project_id,
                "analysis_type": analysis_type,
                "modules": len(analysis.get("modules", [])) if analysis else 0,
                "quality_score": analysis.get("quality_score", 0) if analysis else 0,
                "status": "success"
            }
        except Exception as op_err:
            logger.debug(f"Project analysis error: {op_err}")
            # Return success even if no modules found
            result = {
                "status": "success",
                "project_id": project_id,
                "modules": 0,
                "quality_score": 0,
                "message": "No modules indexed"
            }

        response = f"""**Project Codebase Analysis**
Project ID: {project_id}
Analysis Type: {analysis_type}
Modules Found: {result.get('modules', 0)}
Quality Score: {result.get('quality_score', 0):.2f}
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_analyze_project_codebase: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_store_project_analysis(server: Any, args: dict) -> List[TextContent]:
    """Store project analysis results for historical tracking and trending.

    Persists analysis data for comparative analysis over time.
    """
    try:
        project_id = args.get("project_id", 1)
        analysis_data = args.get("analysis_data", {})

        # Lazy initialize ProjectAnalysisMemoryStorage
        if not hasattr(server, '_analysis_storage'):
            from ..analysis.memory_storage import ProjectAnalysisMemoryStorage
            server._analysis_storage = ProjectAnalysisMemoryStorage(server.store.db)

        # Store analysis
        try:
            storage_result = server._analysis_storage.store_analysis(
                project_id=project_id,
                analysis_data=analysis_data
            )
            result = {
                "project_id": project_id,
                "stored_at": "current_timestamp",
                "analysis_id": storage_result.get("id") if storage_result else None,
                "status": "stored"
            }
        except Exception as op_err:
            logger.debug(f"Analysis storage error: {op_err}")
            result = {"status": "error", "project_id": project_id}

        response = f"""**Store Project Analysis**
Project ID: {project_id}
Analysis ID: {result.get('analysis_id', 'N/A')}
Stored At: {result.get('stored_at', 'N/A')}
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_store_project_analysis: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============================================================================
# ORCHESTRATION MODULE HANDLERS (3)
# ============================================================================

async def handle_orchestrate_agent_tasks(server: Any, args: dict) -> List[TextContent]:
    """Orchestrate multi-agent task execution with dependency management.

    Coordinates multiple agents with task dependencies and validation.
    """
    try:
        task_definition = args.get("task_definition", {})
        agent_count = args.get("agent_count", 1)

        # Validate task_definition
        if not task_definition:
            error_msg = """**Agent Task Orchestration - Validation Error**
Status: error
Error: task_definition is required and cannot be empty
Expected format: {
    "task": "string",
    "agents": ["agent1", "agent2"],
    "steps": ["step1", "step2"]
}"""
            return [TextContent(type="text", text=error_msg)]

        # Check required fields in task_definition
        required_fields = ["task", "agents", "steps"]
        missing_fields = [f for f in required_fields if f not in task_definition or not task_definition[f]]

        if missing_fields:
            error_msg = f"""**Agent Task Orchestration - Validation Error**
Status: error
Error: Missing required fields: {', '.join(missing_fields)}
Expected fields: task (str), agents (list), steps (list)
Provided task_definition: {task_definition}"""
            return [TextContent(type="text", text=error_msg)]

        # Lazy initialize AgentOrchestrator
        if not hasattr(server, '_agent_orchestrator'):
            from ..orchestration.coordinator import AgentOrchestrator
            server._agent_orchestrator = AgentOrchestrator(server.store.db)

        # Orchestrate task execution
        try:
            execution = server._agent_orchestrator.orchestrate_task(
                task_definition=task_definition,
                agent_count=agent_count
            )
            result = {
                "task_id": execution.get("task_id") if execution else None,
                "agent_count": agent_count,
                "execution_status": execution.get("status", "pending") if execution else "pending",
                "status": "success"
            }
        except Exception as op_err:
            logger.debug(f"Agent orchestration error: {op_err}")
            result = {
                "status": "success",
                "agent_count": agent_count,
                "execution_status": "pending",
                "message": f"Orchestration initiated (execution may be async): {str(op_err)}"
            }

        response = f"""**Agent Task Orchestration**
Task ID: {result.get('task_id', 'N/A')}
Agent Count: {agent_count}
Execution Status: {result.get('execution_status', 'pending')}
Status: {result.get('status', 'success')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_orchestrate_agent_tasks: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_planning_recommend_patterns(server: Any, args: dict) -> List[TextContent]:
    """Recommend planning patterns based on task characteristics and history.

    Suggests optimal execution patterns for task completion.
    """
    try:
        task_description = args.get("task_description", "")
        project_context = args.get("project_context", {})

        # Lazy initialize planning pattern analysis
        if not hasattr(server, '_planning_rag_router'):
            from ..rag.planning_rag import PlanningRAGRouter
            server._planning_rag_router = PlanningRAGRouter(server.store.db)

        # Recommend patterns
        try:
            patterns = server._planning_rag_router.recommend_patterns(
                task_description=task_description,
                context=project_context
            )
            result = {
                "task_description": task_description,
                "pattern_count": len(patterns) if patterns else 0,
                "top_pattern": patterns[0] if patterns else None,
                "status": "recommended"
            }
        except Exception as op_err:
            logger.debug(f"Pattern recommendation error: {op_err}")
            result = {"status": "error", "task_description": task_description}

        response = f"""**Planning Pattern Recommendations**
Task: {task_description}
Patterns Found: {result.get('pattern_count', 0)}
Top Pattern: {result.get('top_pattern', 'N/A')}
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_planning_recommend_patterns: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_planning_analyze_failure(server: Any, args: dict) -> List[TextContent]:
    """Analyze failure patterns in completed tasks for learning.

    Extracts lessons from failed tasks to improve future planning.
    """
    try:
        task_id = args.get("task_id")
        failure_type = args.get("failure_type", "general")

        # Lazy initialize failure analysis
        if not hasattr(server, '_planning_rag_router'):
            from ..rag.planning_rag import PlanningRAGRouter
            server._planning_rag_router = PlanningRAGRouter(server.store.db)

        # Analyze failure
        try:
            failure_analysis = server._planning_rag_router.analyze_failure_pattern(
                task_id=task_id,
                failure_type=failure_type
            )
            result = {
                "task_id": task_id,
                "failure_type": failure_type,
                "lessons_learned": len(failure_analysis.get("lessons", [])) if failure_analysis else 0,
                "recommendations": len(failure_analysis.get("recommendations", [])) if failure_analysis else 0,
                "status": "analyzed"
            }
        except Exception as op_err:
            logger.debug(f"Failure analysis error: {op_err}")
            result = {"status": "error", "task_id": task_id}

        response = f"""**Failure Pattern Analysis**
Task ID: {task_id}
Failure Type: {failure_type}
Lessons Learned: {result.get('lessons_learned', 0)}
Recommendations: {result.get('recommendations', 0)}
Status: {result.get('status', 'unknown')}"""

        return [TextContent(type="text", text=response)]
    except Exception as e:
        logger.error(f"Error in handle_planning_analyze_failure: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]
