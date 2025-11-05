"""Phase 7.4 Recall & Reuse unit tests.

Tests for:
- SmartRecall: Intelligent memory retrieval
- ActionCycleEnhancer: Planning improvement
- ProspectiveIntegration: Task triggers
- Phase74MCPTools: MCP tool integration
"""

import pytest
from athena.core.database import Database
from athena.ai_coordination.integration.smart_recall import SmartRecall, RecallContext
from athena.ai_coordination.integration.action_cycle_enhancer import ActionCycleEnhancer, PlanEnhancement
from athena.ai_coordination.integration.prospective_integration import ProspectiveIntegration, ProspectiveTask
from athena.ai_coordination.integration.phase7_4_mcp_tools import Phase74MCPTools


class TestSmartRecall:
    """Tests for SmartRecall intelligent retrieval."""

    def test_smart_recall_initialization(self, tmp_path):
        """Test SmartRecall initializes and creates schema."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recall_operations'")
        assert cursor.fetchone() is not None

    def test_recall_context_creation(self):
        """Test RecallContext initialization."""
        context = RecallContext(
            query="How to fix authentication",
            problem_type="bug",
            search_depth=3,
            max_results=10
        )
        assert context.query == "How to fix authentication"
        assert context.problem_type == "bug"
        assert context.search_depth == 3

    def test_recall_for_problem(self, tmp_path):
        """Test recalling knowledge for a problem."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        
        result = recall.recall_for_problem("Debug authentication issue")
        assert result["status"] == "success" or "recall_id" in result

    def test_recall_for_goal(self, tmp_path):
        """Test recalling knowledge for a goal."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        
        result = recall.recall_for_goal("Implement login", "goal_1", "session_1")
        assert "goal_id" in result

    def test_record_reuse(self, tmp_path):
        """Test recording reuse outcome."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        
        reuse_id = recall.record_reuse(1, 100, "procedure", "goal_1", "success", 0.9)
        assert reuse_id is not None

    def test_get_recall_metrics(self, tmp_path):
        """Test retrieving recall metrics."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        
        metrics = recall.get_recall_metrics()
        assert "total_recall_operations" in metrics


class TestActionCycleEnhancer:
    """Tests for ActionCycleEnhancer planning improvement."""

    def test_enhancer_initialization(self, tmp_path):
        """Test ActionCycleEnhancer initializes."""
        db = Database(tmp_path / "test.db")
        enhancer = ActionCycleEnhancer(db)
        
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='plan_enhancements'")
        assert cursor.fetchone() is not None

    def test_plan_enhancement_creation(self):
        """Test PlanEnhancement initialization."""
        enhancement = PlanEnhancement(
            step_number=1,
            enhancement_type="procedure_suggestion",
            description="Use debug procedure",
            confidence=0.85,
            source_id=10,
            source_type="procedure"
        )
        assert enhancement.step_number == 1
        assert enhancement.confidence == 0.85

    def test_analyze_plan(self, tmp_path):
        """Test analyzing a plan."""
        db = Database(tmp_path / "test.db")
        enhancer = ActionCycleEnhancer(db)
        
        plan_steps = ["Identify bug", "Check logs", "Fix code", "Test fix"]
        result = enhancer.analyze_plan("cycle_1", "Fix authentication bug", plan_steps)
        
        assert result["cycle_id"] == "cycle_1"
        assert result["total_steps"] == 4

    def test_apply_enhancement(self, tmp_path):
        """Test applying an enhancement."""
        db = Database(tmp_path / "test.db")
        enhancer = ActionCycleEnhancer(db)
        
        enhancement = PlanEnhancement(0, "procedure_suggestion", "Use X", 0.8, 1, "procedure")
        enhancement_id = enhancer.apply_enhancement("cycle_1", "goal_1", 1, enhancement)
        assert enhancement_id is not None

    def test_get_enhancement_effectiveness(self, tmp_path):
        """Test retrieving enhancement effectiveness."""
        db = Database(tmp_path / "test.db")
        enhancer = ActionCycleEnhancer(db)
        
        metrics = enhancer.get_enhancement_effectiveness()
        assert "enhancements_by_type" in metrics


class TestProspectiveIntegration:
    """Tests for ProspectiveIntegration task management."""

    def test_prospective_initialization(self, tmp_path):
        """Test ProspectiveIntegration initializes."""
        db = Database(tmp_path / "test.db")
        prospective = ProspectiveIntegration(db)
        
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prospective_tasks'")
        assert cursor.fetchone() is not None

    def test_prospective_task_creation(self):
        """Test ProspectiveTask initialization."""
        task = ProspectiveTask(
            content="Review code quality",
            priority="high",
            trigger_type="time",
            trigger_value="daily_9am",
            source_pattern_id=5,
            estimated_effort_hours=2.0
        )
        assert task.content == "Review code quality"
        assert task.priority == "high"

    def test_create_prospective_task(self, tmp_path):
        """Test creating a prospective task."""
        db = Database(tmp_path / "test.db")
        prospective = ProspectiveIntegration(db)
        
        task = ProspectiveTask(
            "Run automated tests", "medium", "time", "daily_6am", 1, 1.5
        )
        task_id = prospective.create_prospective_task(task)
        assert task_id is not None

    def test_get_pending_tasks(self, tmp_path):
        """Test retrieving pending tasks."""
        db = Database(tmp_path / "test.db")
        prospective = ProspectiveIntegration(db)
        
        tasks = prospective.get_pending_tasks()
        assert isinstance(tasks, list)

    def test_get_task_effectiveness_metrics(self, tmp_path):
        """Test retrieving task effectiveness metrics."""
        db = Database(tmp_path / "test.db")
        prospective = ProspectiveIntegration(db)
        
        metrics = prospective.get_task_effectiveness_metrics()
        assert "total_tasks_tracked" in metrics


class TestPhase74MCPTools:
    """Tests for Phase 7.4 MCP tool integration."""

    def test_mcp_tools_initialization(self, tmp_path):
        """Test Phase74MCPTools initializes."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        enhancer = ActionCycleEnhancer(db)
        prospective = ProspectiveIntegration(db)
        
        tools = Phase74MCPTools(recall, enhancer, prospective)
        assert tools.recall is not None

    def test_smart_recall_tool(self, tmp_path):
        """Test smart_recall_for_problem MCP tool."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        enhancer = ActionCycleEnhancer(db)
        prospective = ProspectiveIntegration(db)
        
        tools = Phase74MCPTools(recall, enhancer, prospective)
        result = tools.smart_recall_for_problem("Debug timeout issue")
        
        assert result["status"] == "success"

    def test_get_procedure_candidates_tool(self, tmp_path):
        """Test get_procedure_candidates MCP tool."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        enhancer = ActionCycleEnhancer(db)
        prospective = ProspectiveIntegration(db)
        
        tools = Phase74MCPTools(recall, enhancer, prospective)
        result = tools.get_procedure_candidates("debugging")
        
        assert result["status"] == "success"

    def test_suggest_plan_enhancements_tool(self, tmp_path):
        """Test suggest_plan_enhancements MCP tool."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        enhancer = ActionCycleEnhancer(db)
        prospective = ProspectiveIntegration(db)
        
        tools = Phase74MCPTools(recall, enhancer, prospective)
        
        plan = ["Analyze", "Plan", "Execute"]
        result = tools.suggest_plan_enhancements("cycle_1", "Fix bug", plan)
        
        assert result["status"] == "success"

    def test_create_prospective_task_tool(self, tmp_path):
        """Test create_prospective_task MCP tool."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        enhancer = ActionCycleEnhancer(db)
        prospective = ProspectiveIntegration(db)
        
        tools = Phase74MCPTools(recall, enhancer, prospective)
        
        result = tools.create_prospective_task(
            "Review code", "high", "time", "daily", 1, 2.0
        )
        
        assert result["status"] == "success"

    def test_get_recall_metrics_tool(self, tmp_path):
        """Test get_recall_metrics MCP tool."""
        db = Database(tmp_path / "test.db")
        recall = SmartRecall(db)
        enhancer = ActionCycleEnhancer(db)
        prospective = ProspectiveIntegration(db)
        
        tools = Phase74MCPTools(recall, enhancer, prospective)
        result = tools.get_recall_metrics()
        
        assert result["status"] == "success"
