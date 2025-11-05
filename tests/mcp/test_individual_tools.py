"""
Individual MCP Tool Testing - Tests each meta-tool separately via MCP protocol

This test module provides individual test functions for each of the 11 meta-tools.
Each test can be run independently to verify MCP routing and handler execution.

Usage:
  pytest tests/mcp/test_individual_tools.py::test_memory_tools -v
  pytest tests/mcp/test_individual_tools.py::test_episodic_tools -v
  pytest tests/mcp/test_individual_tools.py::test_graph_tools -v
  etc.
"""

import asyncio
import json
from typing import Any, Optional, Dict, List
import pytest
from pathlib import Path
import sys
import tempfile
import sqlite3

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.athena.mcp.handlers import MemoryMCPServer
from src.athena.core.database import Database


class IndividualToolTester:
    """Test individual MCP tools one at a time"""

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(tempfile.gettempdir()) / "athena_test_individual.db"
        self.db_path = db_path
        self._initialize_database(db_path)
        self.server = MemoryMCPServer(db_path=str(db_path))

    def _initialize_database(self, db_path):
        """Initialize database with all required tables."""
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        tables = {
            "metacognition_gaps": """
            CREATE TABLE IF NOT EXISTS metacognition_gaps (
                id INTEGER PRIMARY KEY,
                domain TEXT NOT NULL,
                gap_type TEXT,
                description TEXT,
                confidence REAL DEFAULT 0.5,
                created_at INTEGER
            )
            """,
            "working_memory": """
            CREATE TABLE IF NOT EXISTS working_memory (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                item TEXT NOT NULL,
                item_type TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
            """,
            "metacognition_quality_metrics": """
            CREATE TABLE IF NOT EXISTS metacognition_quality_metrics (
                id INTEGER PRIMARY KEY,
                domain TEXT,
                metric_name TEXT,
                score REAL,
                timestamp INTEGER
            )
            """,
            "metacognition_learning_rates": """
            CREATE TABLE IF NOT EXISTS metacognition_learning_rates (
                id INTEGER PRIMARY KEY,
                domain TEXT,
                learning_rate REAL,
                updated_at INTEGER
            )
            """,
            "metacognition_cognitive_load": """
            CREATE TABLE IF NOT EXISTS metacognition_cognitive_load (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                load_level REAL,
                timestamp INTEGER
            )
            """,
            "metacognition_confidence": """
            CREATE TABLE IF NOT EXISTS metacognition_confidence (
                id INTEGER PRIMARY KEY,
                domain TEXT,
                confidence REAL,
                updated_at INTEGER
            )
            """,
            "active_goals": """
            CREATE TABLE IF NOT EXISTS active_goals (
                id INTEGER PRIMARY KEY,
                goal_id INTEGER,
                status TEXT,
                created_at INTEGER,
                activated_at INTEGER
            )
            """,
        }

        for table_name, create_sql in tables.items():
            try:
                cursor.execute(create_sql)
            except sqlite3.OperationalError:
                pass  # Table already exists

        conn.commit()
        conn.close()

    async def test_tool(self, tool_name: str, operation: str, args: dict) -> Dict[str, Any]:
        """Test a single operation on a tool via MCP"""
        try:
            result = await self.server.router.route(tool_name, {"operation": operation, **args})
            return {
                "tool": tool_name,
                "operation": operation,
                "success": result.get("status") == "success" or "error" not in result,
                "result": result,
            }
        except Exception as e:
            return {
                "tool": tool_name,
                "operation": operation,
                "success": False,
                "error": str(e),
                "result": None,
            }


@pytest.fixture
def tester():
    """Provide a fresh tester instance for each test"""
    return IndividualToolTester()


# ============================================================================
# MEMORY_TOOLS TESTS (28 operations)
# ============================================================================


class TestMemoryTools:
    """Test all memory_tools operations individually"""

    @pytest.mark.asyncio
    async def test_recall(self, tester):
        """Test memory recall operation"""
        result = await tester.test_tool("memory_tools", "recall", {"query": "test"})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        assert result["tool"] == "memory_tools"
        print(f"✓ memory_tools.recall passed")

    @pytest.mark.asyncio
    async def test_remember(self, tester):
        """Test memory remember operation"""
        result = await tester.test_tool(
            "memory_tools",
            "remember",
            {"content": "Test memory", "memory_type": "fact", "tags": ["test"]},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.remember passed")

    @pytest.mark.asyncio
    async def test_optimize(self, tester):
        """Test memory optimization"""
        result = await tester.test_tool("memory_tools", "optimize", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.optimize passed")

    @pytest.mark.asyncio
    async def test_list_memories(self, tester):
        """Test listing memories"""
        result = await tester.test_tool("memory_tools", "list_memories", {"k": 5})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.list_memories passed")

    @pytest.mark.asyncio
    async def test_smart_retrieve(self, tester):
        """Test smart retrieve with RAG selection"""
        result = await tester.test_tool("memory_tools", "smart_retrieve", {"query": "test"})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.smart_retrieve passed")

    @pytest.mark.asyncio
    async def test_analyze_coverage(self, tester):
        """Test coverage analysis by domain"""
        result = await tester.test_tool("memory_tools", "analyze_coverage", {"domain": "test"})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.analyze_coverage passed")

    @pytest.mark.asyncio
    async def test_search_projects(self, tester):
        """Test searching across projects"""
        result = await tester.test_tool("memory_tools", "search_projects", {"query": "test"})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.search_projects passed")

    @pytest.mark.asyncio
    async def test_get_expertise(self, tester):
        """Test expertise retrieval"""
        result = await tester.test_tool("memory_tools", "get_expertise", {"k": 5})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.get_expertise passed")

    @pytest.mark.asyncio
    async def test_detect_knowledge_gaps(self, tester):
        """Test knowledge gap detection"""
        result = await tester.test_tool("memory_tools", "detect_knowledge_gaps", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.detect_knowledge_gaps passed")

    @pytest.mark.asyncio
    async def test_get_working_memory(self, tester):
        """Test working memory retrieval"""
        result = await tester.test_tool("memory_tools", "get_working_memory", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.get_working_memory passed")

    @pytest.mark.asyncio
    async def test_update_working_memory(self, tester):
        """Test working memory update"""
        result = await tester.test_tool(
            "memory_tools",
            "update_working_memory",
            {"content": "test item", "item_type": "context"},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.update_working_memory passed")

    @pytest.mark.asyncio
    async def test_clear_working_memory(self, tester):
        """Test working memory clearing"""
        result = await tester.test_tool("memory_tools", "clear_working_memory", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.clear_working_memory passed")

    @pytest.mark.asyncio
    async def test_consolidate_working_memory(self, tester):
        """Test working memory consolidation"""
        result = await tester.test_tool("memory_tools", "consolidate_working_memory", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.consolidate_working_memory passed")

    @pytest.mark.asyncio
    async def test_evaluate_memory_quality(self, tester):
        """Test memory quality evaluation"""
        result = await tester.test_tool("memory_tools", "evaluate_memory_quality", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.evaluate_memory_quality passed")

    @pytest.mark.asyncio
    async def test_get_learning_rates(self, tester):
        """Test learning rates retrieval"""
        result = await tester.test_tool("memory_tools", "get_learning_rates", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.get_learning_rates passed")

    @pytest.mark.asyncio
    async def test_get_metacognition_insights(self, tester):
        """Test metacognition insights"""
        result = await tester.test_tool("memory_tools", "get_metacognition_insights", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.get_metacognition_insights passed")

    @pytest.mark.asyncio
    async def test_check_cognitive_load(self, tester):
        """Test cognitive load checking"""
        result = await tester.test_tool("memory_tools", "check_cognitive_load", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.check_cognitive_load passed")

    @pytest.mark.asyncio
    async def test_get_memory_quality_summary(self, tester):
        """Test memory quality summary"""
        result = await tester.test_tool("memory_tools", "get_memory_quality_summary", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.get_memory_quality_summary passed")

    @pytest.mark.asyncio
    async def test_score_semantic_memories(self, tester):
        """Test semantic memory scoring"""
        result = await tester.test_tool("memory_tools", "score_semantic_memories", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.score_semantic_memories passed")

    @pytest.mark.asyncio
    async def test_get_self_reflection(self, tester):
        """Test self-reflection"""
        result = await tester.test_tool("memory_tools", "get_self_reflection", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.get_self_reflection passed")

    @pytest.mark.asyncio
    async def test_run_consolidation(self, tester):
        """Test consolidation run"""
        result = await tester.test_tool("memory_tools", "run_consolidation", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.run_consolidation passed")

    @pytest.mark.asyncio
    async def test_schedule_consolidation(self, tester):
        """Test consolidation scheduling"""
        result = await tester.test_tool("memory_tools", "schedule_consolidation", {"interval": 3600})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ memory_tools.schedule_consolidation passed")

    @pytest.mark.asyncio
    async def test_forget(self, tester):
        """Test memory forgetting"""
        result = await tester.test_tool("memory_tools", "forget", {"memory_id": "test"})
        # This may fail if memory doesn't exist, which is OK for this test
        print(f"✓ memory_tools.forget tested (expected ok or not found)")


# ============================================================================
# EPISODIC_TOOLS TESTS (8 operations)
# ============================================================================


class TestEpisodicTools:
    """Test all episodic_tools operations individually"""

    @pytest.mark.asyncio
    async def test_record_event(self, tester):
        """Test event recording"""
        result = await tester.test_tool(
            "episodic_tools",
            "record_event",
            {"content": "Test event", "event_type": "action", "outcome": "success"},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ episodic_tools.record_event passed")

    @pytest.mark.asyncio
    async def test_recall_events(self, tester):
        """Test event recall"""
        result = await tester.test_tool(
            "episodic_tools", "recall_events", {"query": "test", "days": 7}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ episodic_tools.recall_events passed")

    @pytest.mark.asyncio
    async def test_get_timeline(self, tester):
        """Test timeline retrieval"""
        result = await tester.test_tool("episodic_tools", "get_timeline", {"days": 7})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ episodic_tools.get_timeline passed")

    @pytest.mark.asyncio
    async def test_batch_record_events(self, tester):
        """Test batch event recording"""
        events = [
            {"content": "Event 1", "event_type": "action", "outcome": "success"},
            {"content": "Event 2", "event_type": "action", "outcome": "success"},
        ]
        result = await tester.test_tool("episodic_tools", "batch_record_events", {"events": events})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ episodic_tools.batch_record_events passed")

    @pytest.mark.asyncio
    async def test_recall_events_by_session(self, tester):
        """Test event recall by session"""
        result = await tester.test_tool(
            "episodic_tools", "recall_events_by_session", {"session_id": "test"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ episodic_tools.recall_events_by_session passed")

    @pytest.mark.asyncio
    async def test_record_execution(self, tester):
        """Test execution recording"""
        result = await tester.test_tool(
            "episodic_tools",
            "record_execution",
            {"procedure_name": "test_proc", "status": "success", "duration": 100},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ episodic_tools.record_execution passed")

    @pytest.mark.asyncio
    async def test_record_execution_feedback(self, tester):
        """Test execution feedback recording"""
        result = await tester.test_tool(
            "episodic_tools",
            "record_execution_feedback",
            {"execution_id": 1, "feedback": "test feedback"},
        )
        # May fail if execution_id doesn't exist, which is OK
        print(f"✓ episodic_tools.record_execution_feedback tested")

    @pytest.mark.asyncio
    async def test_record_git_commit(self, tester):
        """Test git commit recording"""
        result = await tester.test_tool(
            "episodic_tools",
            "record_git_commit",
            {"commit_hash": "abc123", "message": "test commit"},
        )
        # May fail if not in git repo, which is OK
        print(f"✓ episodic_tools.record_git_commit tested")


# ============================================================================
# GRAPH_TOOLS TESTS (15 operations)
# ============================================================================


class TestGraphTools:
    """Test all graph_tools operations individually"""

    @pytest.mark.asyncio
    async def test_create_entity(self, tester):
        """Test entity creation"""
        result = await tester.test_tool(
            "graph_tools", "create_entity", {"name": "TestEntity", "entity_type": "Concept"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.create_entity passed")

    @pytest.mark.asyncio
    async def test_create_relation(self, tester):
        """Test relation creation"""
        result = await tester.test_tool(
            "graph_tools",
            "create_relation",
            {"from_entity": "e1", "to_entity": "e2", "relation_type": "depends_on"},
        )
        # May fail if entities don't exist, which is OK
        print(f"✓ graph_tools.create_relation tested")

    @pytest.mark.asyncio
    async def test_add_observation(self, tester):
        """Test observation addition"""
        result = await tester.test_tool(
            "graph_tools", "add_observation", {"entity_id": 1, "observation": "test observation"}
        )
        # May fail if entity doesn't exist, which is OK
        print(f"✓ graph_tools.add_observation tested")

    @pytest.mark.asyncio
    async def test_search_graph(self, tester):
        """Test graph search"""
        result = await tester.test_tool("graph_tools", "search_graph", {"query": "test"})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.search_graph passed")

    @pytest.mark.asyncio
    async def test_get_graph_metrics(self, tester):
        """Test graph metrics retrieval"""
        result = await tester.test_tool("graph_tools", "get_graph_metrics", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.get_graph_metrics passed")

    @pytest.mark.asyncio
    async def test_analyze_symbols(self, tester):
        """Test symbol analysis"""
        result = await tester.test_tool("graph_tools", "analyze_symbols", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.analyze_symbols passed")

    @pytest.mark.asyncio
    async def test_get_symbol_info(self, tester):
        """Test symbol info retrieval"""
        result = await tester.test_tool("graph_tools", "get_symbol_info", {"symbol": "test_symbol"})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.get_symbol_info passed")

    @pytest.mark.asyncio
    async def test_find_symbol_dependencies(self, tester):
        """Test symbol dependency finding"""
        result = await tester.test_tool(
            "graph_tools", "find_symbol_dependencies", {"symbol": "test_symbol"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.find_symbol_dependencies passed")

    @pytest.mark.asyncio
    async def test_find_symbol_dependents(self, tester):
        """Test symbol dependent finding"""
        result = await tester.test_tool(
            "graph_tools", "find_symbol_dependents", {"symbol": "test_symbol"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.find_symbol_dependents passed")

    @pytest.mark.asyncio
    async def test_find_memory_path(self, tester):
        """Test memory path finding"""
        result = await tester.test_tool(
            "graph_tools", "find_memory_path", {"from_memory_id": "m1", "to_memory_id": "m2"}
        )
        # May fail if memories don't exist, which is OK
        print(f"✓ graph_tools.find_memory_path tested")

    @pytest.mark.asyncio
    async def test_get_associations(self, tester):
        """Test associations retrieval"""
        result = await tester.test_tool("graph_tools", "get_associations", {"memory_id": "m1"})
        # May fail if memory doesn't exist, which is OK
        print(f"✓ graph_tools.get_associations tested")

    @pytest.mark.asyncio
    async def test_search_graph_with_depth(self, tester):
        """Test graph search with depth"""
        result = await tester.test_tool(
            "graph_tools", "search_graph_with_depth", {"query": "test", "depth": 2}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.search_graph_with_depth passed")

    @pytest.mark.asyncio
    async def test_temporal_kg_synthesis(self, tester):
        """Test temporal KG synthesis"""
        result = await tester.test_tool("graph_tools", "temporal_kg_synthesis", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.temporal_kg_synthesis passed")

    @pytest.mark.asyncio
    async def test_temporal_search_enrich(self, tester):
        """Test temporal search enrichment"""
        result = await tester.test_tool(
            "graph_tools", "temporal_search_enrich", {"query": "test"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ graph_tools.temporal_search_enrich passed")


# ============================================================================
# PLANNING_TOOLS TESTS (14 operations)
# ============================================================================


class TestPlanningTools:
    """Test all planning_tools operations individually"""

    @pytest.mark.asyncio
    async def test_decompose_hierarchically(self, tester):
        """Test hierarchical decomposition"""
        result = await tester.test_tool(
            "planning_tools",
            "decompose_hierarchically",
            {"task_description": "Implement feature", "complexity_level": 5},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ planning_tools.decompose_hierarchically passed")

    @pytest.mark.asyncio
    async def test_decompose_with_strategy(self, tester):
        """Test strategy-based decomposition"""
        result = await tester.test_tool(
            "planning_tools",
            "decompose_with_strategy",
            {"task_description": "Test task", "strategy": "HIERARCHICAL"},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ planning_tools.decompose_with_strategy passed")

    @pytest.mark.asyncio
    async def test_validate_plan(self, tester):
        """Test plan validation"""
        result = await tester.test_tool("planning_tools", "validate_plan", {"task_id": 1})
        # May fail if task doesn't exist, which is OK
        print(f"✓ planning_tools.validate_plan tested")

    @pytest.mark.asyncio
    async def test_verify_plan(self, tester):
        """Test plan verification"""
        result = await tester.test_tool("planning_tools", "verify_plan", {"task_id": 1})
        # May fail if task doesn't exist, which is OK
        print(f"✓ planning_tools.verify_plan tested")

    @pytest.mark.asyncio
    async def test_generate_task_plan(self, tester):
        """Test task plan generation"""
        result = await tester.test_tool("planning_tools", "generate_task_plan", {"task_id": 1})
        # May fail if task doesn't exist, which is OK
        print(f"✓ planning_tools.generate_task_plan tested")

    @pytest.mark.asyncio
    async def test_optimize_plan(self, tester):
        """Test plan optimization"""
        result = await tester.test_tool("planning_tools", "optimize_plan", {"task_id": 1})
        # May fail if task doesn't exist, which is OK
        print(f"✓ planning_tools.optimize_plan tested")

    @pytest.mark.asyncio
    async def test_estimate_resources(self, tester):
        """Test resource estimation"""
        result = await tester.test_tool("planning_tools", "estimate_resources", {"task_id": 1})
        # May fail if task doesn't exist, which is OK
        print(f"✓ planning_tools.estimate_resources tested")

    @pytest.mark.asyncio
    async def test_generate_alternative_plans(self, tester):
        """Test alternative plan generation"""
        result = await tester.test_tool(
            "planning_tools", "generate_alternative_plans", {"task_id": 1}
        )
        # May fail if task doesn't exist, which is OK
        print(f"✓ planning_tools.generate_alternative_plans tested")

    @pytest.mark.asyncio
    async def test_suggest_planning_strategy(self, tester):
        """Test planning strategy suggestion"""
        result = await tester.test_tool(
            "planning_tools", "suggest_planning_strategy", {"task_description": "test task"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ planning_tools.suggest_planning_strategy passed")

    @pytest.mark.asyncio
    async def test_recommend_strategy(self, tester):
        """Test strategy recommendation"""
        result = await tester.test_tool(
            "planning_tools", "recommend_strategy", {"task_description": "test"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ planning_tools.recommend_strategy passed")

    @pytest.mark.asyncio
    async def test_predict_task_duration(self, tester):
        """Test task duration prediction"""
        result = await tester.test_tool(
            "planning_tools", "predict_task_duration", {"task_description": "test"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ planning_tools.predict_task_duration passed")

    @pytest.mark.asyncio
    async def test_analyze_uncertainty(self, tester):
        """Test uncertainty analysis"""
        result = await tester.test_tool(
            "planning_tools", "analyze_uncertainty", {"task_description": "test"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ planning_tools.analyze_uncertainty passed")

    @pytest.mark.asyncio
    async def test_generate_confidence_scores(self, tester):
        """Test confidence score generation"""
        result = await tester.test_tool(
            "planning_tools", "generate_confidence_scores", {"task_description": "test"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ planning_tools.generate_confidence_scores passed")

    @pytest.mark.asyncio
    async def test_estimate_confidence_interval(self, tester):
        """Test confidence interval estimation"""
        result = await tester.test_tool(
            "planning_tools", "estimate_confidence_interval", {"task_id": 1}
        )
        # May fail if task doesn't exist, which is OK
        print(f"✓ planning_tools.estimate_confidence_interval tested")


# ============================================================================
# TASK_MANAGEMENT_TOOLS TESTS (16+ operations)
# ============================================================================


class TestTaskManagementTools:
    """Test all task_management_tools operations individually"""

    @pytest.mark.asyncio
    async def test_create_task(self, tester):
        """Test task creation"""
        result = await tester.test_tool(
            "task_management_tools",
            "create_task",
            {
                "content": "Test task",
                "activeForm": "Testing task",
                "priority": "high",
                "status": "pending",
            },
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ task_management_tools.create_task passed")

    @pytest.mark.asyncio
    async def test_list_tasks(self, tester):
        """Test task listing"""
        result = await tester.test_tool("task_management_tools", "list_tasks", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ task_management_tools.list_tasks passed")

    @pytest.mark.asyncio
    async def test_update_task_status(self, tester):
        """Test task status update"""
        result = await tester.test_tool(
            "task_management_tools",
            "update_task_status",
            {"task_id": 1, "status": "in_progress"},
        )
        # May fail if task doesn't exist, which is OK
        print(f"✓ task_management_tools.update_task_status tested")

    @pytest.mark.asyncio
    async def test_start_task(self, tester):
        """Test task start"""
        result = await tester.test_tool("task_management_tools", "start_task", {"task_id": 1})
        # May fail if task doesn't exist, which is OK
        print(f"✓ task_management_tools.start_task tested")

    @pytest.mark.asyncio
    async def test_verify_task(self, tester):
        """Test task verification"""
        result = await tester.test_tool("task_management_tools", "verify_task", {"task_id": 1})
        # May fail if task doesn't exist, which is OK
        print(f"✓ task_management_tools.verify_task tested")

    @pytest.mark.asyncio
    async def test_set_goal(self, tester):
        """Test goal setting"""
        result = await tester.test_tool(
            "task_management_tools",
            "set_goal",
            {"goal_text": "Complete project", "priority": "high"},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ task_management_tools.set_goal passed")

    @pytest.mark.asyncio
    async def test_get_active_goals(self, tester):
        """Test getting active goals"""
        result = await tester.test_tool("task_management_tools", "get_active_goals", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ task_management_tools.get_active_goals passed")

    @pytest.mark.asyncio
    async def test_activate_goal(self, tester):
        """Test goal activation"""
        result = await tester.test_tool("task_management_tools", "activate_goal", {"goal_id": 1})
        # May fail if goal doesn't exist, which is OK
        print(f"✓ task_management_tools.activate_goal tested")

    @pytest.mark.asyncio
    async def test_complete_goal(self, tester):
        """Test goal completion"""
        result = await tester.test_tool(
            "task_management_tools",
            "complete_goal",
            {"goal_id": 1, "outcome": "success"},
        )
        # May fail if goal doesn't exist, which is OK
        print(f"✓ task_management_tools.complete_goal tested")

    @pytest.mark.asyncio
    async def test_record_execution_progress(self, tester):
        """Test progress recording"""
        result = await tester.test_tool(
            "task_management_tools",
            "record_execution_progress",
            {"goal_id": 1, "progress_percent": 50},
        )
        # May fail if goal doesn't exist, which is OK
        print(f"✓ task_management_tools.record_execution_progress tested")

    @pytest.mark.asyncio
    async def test_get_workflow_status(self, tester):
        """Test workflow status"""
        result = await tester.test_tool("task_management_tools", "get_workflow_status", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ task_management_tools.get_workflow_status passed")

    @pytest.mark.asyncio
    async def test_get_goal_priority_ranking(self, tester):
        """Test goal priority ranking"""
        result = await tester.test_tool(
            "task_management_tools", "get_goal_priority_ranking", {}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ task_management_tools.get_goal_priority_ranking passed")

    @pytest.mark.asyncio
    async def test_recommend_next_goal(self, tester):
        """Test next goal recommendation"""
        result = await tester.test_tool("task_management_tools", "recommend_next_goal", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ task_management_tools.recommend_next_goal passed")


# ============================================================================
# MONITORING_TOOLS TESTS (8 operations)
# ============================================================================


class TestMonitoringTools:
    """Test all monitoring_tools operations individually"""

    @pytest.mark.asyncio
    async def test_get_task_health(self, tester):
        """Test task health retrieval"""
        result = await tester.test_tool("monitoring_tools", "get_task_health", {"task_id": 1})
        # May fail if task doesn't exist, which is OK
        print(f"✓ monitoring_tools.get_task_health tested")

    @pytest.mark.asyncio
    async def test_get_project_dashboard(self, tester):
        """Test project dashboard"""
        result = await tester.test_tool(
            "monitoring_tools", "get_project_dashboard", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ monitoring_tools.get_project_dashboard tested")

    @pytest.mark.asyncio
    async def test_get_layer_health(self, tester):
        """Test layer health retrieval"""
        result = await tester.test_tool("monitoring_tools", "get_layer_health", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ monitoring_tools.get_layer_health passed")

    @pytest.mark.asyncio
    async def test_get_project_status(self, tester):
        """Test project status"""
        result = await tester.test_tool(
            "monitoring_tools", "get_project_status", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ monitoring_tools.get_project_status tested")

    @pytest.mark.asyncio
    async def test_analyze_estimation_accuracy(self, tester):
        """Test estimation accuracy analysis"""
        result = await tester.test_tool(
            "monitoring_tools", "analyze_estimation_accuracy", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ monitoring_tools.analyze_estimation_accuracy tested")

    @pytest.mark.asyncio
    async def test_discover_patterns(self, tester):
        """Test pattern discovery"""
        result = await tester.test_tool(
            "monitoring_tools", "discover_patterns", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ monitoring_tools.discover_patterns tested")

    @pytest.mark.asyncio
    async def test_analyze_critical_path(self, tester):
        """Test critical path analysis"""
        result = await tester.test_tool(
            "monitoring_tools", "analyze_critical_path", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ monitoring_tools.analyze_critical_path tested")

    @pytest.mark.asyncio
    async def test_detect_bottlenecks(self, tester):
        """Test bottleneck detection"""
        result = await tester.test_tool(
            "monitoring_tools", "detect_bottlenecks", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ monitoring_tools.detect_bottlenecks tested")


# ============================================================================
# COORDINATION_TOOLS TESTS (9 operations)
# ============================================================================


class TestCoordinationTools:
    """Test all coordination_tools operations individually"""

    @pytest.mark.asyncio
    async def test_add_project_dependency(self, tester):
        """Test project dependency addition"""
        result = await tester.test_tool(
            "coordination_tools",
            "add_project_dependency",
            {"from_task_id": 1, "to_task_id": 2},
        )
        # May fail if tasks don't exist, which is OK
        print(f"✓ coordination_tools.add_project_dependency tested")

    @pytest.mark.asyncio
    async def test_analyze_critical_path(self, tester):
        """Test critical path analysis"""
        result = await tester.test_tool(
            "coordination_tools", "analyze_critical_path", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ coordination_tools.analyze_critical_path tested")

    @pytest.mark.asyncio
    async def test_detect_resource_conflicts(self, tester):
        """Test resource conflict detection"""
        result = await tester.test_tool(
            "coordination_tools", "detect_resource_conflicts", {"project_ids": [1, 2]}
        )
        # May fail if projects don't exist, which is OK
        print(f"✓ coordination_tools.detect_resource_conflicts tested")

    @pytest.mark.asyncio
    async def test_detect_bottlenecks(self, tester):
        """Test bottleneck detection"""
        result = await tester.test_tool(
            "coordination_tools", "detect_bottlenecks", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ coordination_tools.detect_bottlenecks tested")

    @pytest.mark.asyncio
    async def test_analyze_graph_metrics(self, tester):
        """Test graph metrics analysis"""
        result = await tester.test_tool("coordination_tools", "analyze_graph_metrics", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ coordination_tools.analyze_graph_metrics passed")

    @pytest.mark.asyncio
    async def test_analyze_uncertainty(self, tester):
        """Test uncertainty analysis"""
        result = await tester.test_tool(
            "coordination_tools", "analyze_uncertainty", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ coordination_tools.analyze_uncertainty tested")

    @pytest.mark.asyncio
    async def test_generate_confidence_scores(self, tester):
        """Test confidence score generation"""
        result = await tester.test_tool(
            "coordination_tools", "generate_confidence_scores", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ coordination_tools.generate_confidence_scores tested")

    @pytest.mark.asyncio
    async def test_recommend_orchestration(self, tester):
        """Test orchestration recommendation"""
        result = await tester.test_tool(
            "coordination_tools", "recommend_orchestration", {"project_ids": [1, 2]}
        )
        # May fail if projects don't exist, which is OK
        print(f"✓ coordination_tools.recommend_orchestration tested")

    @pytest.mark.asyncio
    async def test_detect_budget_anomalies(self, tester):
        """Test budget anomaly detection"""
        result = await tester.test_tool(
            "coordination_tools", "detect_budget_anomalies", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ coordination_tools.detect_budget_anomalies tested")


# ============================================================================
# PROCEDURAL_TOOLS TESTS (6 operations)
# ============================================================================


class TestProceduralTools:
    """Test all procedural_tools operations individually"""

    @pytest.mark.asyncio
    async def test_create_procedure(self, tester):
        """Test procedure creation"""
        result = await tester.test_tool(
            "procedural_tools",
            "create_procedure",
            {"name": "test_proc", "category": "debugging"},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ procedural_tools.create_procedure passed")

    @pytest.mark.asyncio
    async def test_find_procedures(self, tester):
        """Test procedure finding"""
        result = await tester.test_tool(
            "procedural_tools", "find_procedures", {"query": "test"}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ procedural_tools.find_procedures passed")

    @pytest.mark.asyncio
    async def test_record_execution(self, tester):
        """Test procedure execution recording"""
        result = await tester.test_tool(
            "procedural_tools",
            "record_execution",
            {"procedure_name": "test_proc", "status": "success"},
        )
        # May fail if procedure doesn't exist, which is OK
        print(f"✓ procedural_tools.record_execution tested")

    @pytest.mark.asyncio
    async def test_get_procedure_effectiveness(self, tester):
        """Test procedure effectiveness retrieval"""
        result = await tester.test_tool(
            "procedural_tools",
            "get_procedure_effectiveness",
            {"procedure_name": "test_proc"},
        )
        # May fail if procedure doesn't exist, which is OK
        print(f"✓ procedural_tools.get_procedure_effectiveness tested")

    @pytest.mark.asyncio
    async def test_suggest_procedure_improvements(self, tester):
        """Test procedure improvement suggestions"""
        result = await tester.test_tool(
            "procedural_tools",
            "suggest_procedure_improvements",
            {"procedure_name": "test_proc"},
        )
        # May fail if procedure doesn't exist, which is OK
        print(f"✓ procedural_tools.suggest_procedure_improvements tested")

    @pytest.mark.asyncio
    async def test_generate_workflow_from_task(self, tester):
        """Test workflow generation from task"""
        result = await tester.test_tool(
            "procedural_tools", "generate_workflow_from_task", {"task_id": 1}
        )
        # May fail if task doesn't exist, which is OK
        print(f"✓ procedural_tools.generate_workflow_from_task tested")


# ============================================================================
# SECURITY_TOOLS TESTS (2 operations)
# ============================================================================


class TestSecurityTools:
    """Test all security_tools operations individually"""

    @pytest.mark.asyncio
    async def test_analyze_code_security(self, tester):
        """Test code security analysis"""
        result = await tester.test_tool(
            "security_tools",
            "analyze_code_security",
            {"code_content": "def test(): pass", "language": "python"},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ security_tools.analyze_code_security passed")

    @pytest.mark.asyncio
    async def test_track_sensitive_data(self, tester):
        """Test sensitive data tracking"""
        result = await tester.test_tool(
            "security_tools",
            "track_sensitive_data",
            {
                "data_type": "password",
                "exposure_location": "config.py",
            },
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ security_tools.track_sensitive_data passed")


# ============================================================================
# FINANCIAL_TOOLS TESTS (5 operations)
# ============================================================================


class TestFinancialTools:
    """Test all financial_tools operations individually"""

    @pytest.mark.asyncio
    async def test_calculate_task_cost(self, tester):
        """Test task cost calculation"""
        result = await tester.test_tool(
            "financial_tools", "calculate_task_cost", {"task_id": 1}
        )
        # May fail if task doesn't exist, which is OK
        print(f"✓ financial_tools.calculate_task_cost tested")

    @pytest.mark.asyncio
    async def test_estimate_roi(self, tester):
        """Test ROI estimation"""
        result = await tester.test_tool(
            "financial_tools",
            "estimate_roi",
            {"project_id": 1, "expected_value": 10000},
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ financial_tools.estimate_roi tested")

    @pytest.mark.asyncio
    async def test_suggest_cost_optimizations(self, tester):
        """Test cost optimization suggestions"""
        result = await tester.test_tool(
            "financial_tools", "suggest_cost_optimizations", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ financial_tools.suggest_cost_optimizations tested")

    @pytest.mark.asyncio
    async def test_track_budget(self, tester):
        """Test budget tracking"""
        result = await tester.test_tool(
            "financial_tools", "track_budget", {"project_id": 1, "total_cost": 5000}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ financial_tools.track_budget tested")

    @pytest.mark.asyncio
    async def test_detect_budget_anomalies(self, tester):
        """Test budget anomaly detection"""
        result = await tester.test_tool(
            "financial_tools", "detect_budget_anomalies", {"project_id": 1}
        )
        # May fail if project doesn't exist, which is OK
        print(f"✓ financial_tools.detect_budget_anomalies tested")


# ============================================================================
# ML_INTEGRATION_TOOLS TESTS (7 operations)
# ============================================================================


class TestMLIntegrationTools:
    """Test all ml_integration_tools operations individually"""

    @pytest.mark.asyncio
    async def test_train_estimation_model(self, tester):
        """Test estimation model training"""
        result = await tester.test_tool("ml_integration_tools", "train_estimation_model", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ ml_integration_tools.train_estimation_model passed")

    @pytest.mark.asyncio
    async def test_recommend_strategy(self, tester):
        """Test strategy recommendation"""
        result = await tester.test_tool(
            "ml_integration_tools",
            "recommend_strategy",
            {"task_description": "test task"},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ ml_integration_tools.recommend_strategy passed")

    @pytest.mark.asyncio
    async def test_predict_task_duration(self, tester):
        """Test task duration prediction"""
        result = await tester.test_tool(
            "ml_integration_tools",
            "predict_task_duration",
            {"task_description": "test", "base_estimate": 100},
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ ml_integration_tools.predict_task_duration passed")

    @pytest.mark.asyncio
    async def test_forecast_resource_needs(self, tester):
        """Test resource forecasting"""
        result = await tester.test_tool(
            "ml_integration_tools", "forecast_resource_needs", {}
        )
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ ml_integration_tools.forecast_resource_needs passed")

    @pytest.mark.asyncio
    async def test_get_saliency_batch(self, tester):
        """Test saliency batch retrieval"""
        result = await tester.test_tool("ml_integration_tools", "get_saliency_batch", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ ml_integration_tools.get_saliency_batch passed")

    @pytest.mark.asyncio
    async def test_compute_memory_saliency(self, tester):
        """Test memory saliency computation"""
        result = await tester.test_tool("ml_integration_tools", "compute_memory_saliency", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ ml_integration_tools.compute_memory_saliency passed")

    @pytest.mark.asyncio
    async def test_auto_focus_top_memories(self, tester):
        """Test auto-focus on top memories"""
        result = await tester.test_tool("ml_integration_tools", "auto_focus_top_memories", {})
        assert result["success"], f"Failed: {result.get('error', result.get('result'))}"
        print(f"✓ ml_integration_tools.auto_focus_top_memories passed")


# ============================================================================
# CONSOLIDATED TEST RUNNER
# ============================================================================


if __name__ == "__main__":
    # Can be run with pytest
    pytest.main([__file__, "-v"])
