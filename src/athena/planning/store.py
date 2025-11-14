"""Planning memory storage and query operations."""

import json
from datetime import datetime
from typing import Any, List, Optional, Tuple

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import (
    DecompositionStrategy,
    ExecutionFeedback,
    OrchestratorPattern,
    PlanningPattern,
    ValidationRule,
)


class PlanningStore:
    """Manages planning memory storage and queries."""

    def __init__(self, db: Database):
        """Initialize planning store.

        Args:
            db: Database instance
        """
        self.db = db
    # ==================== HELPER METHODS ====================

    def execute(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False) -> Any:
        """Execute SQL query with consistent error handling.

        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return first row only
            fetch_all: Return all rows as list

        Returns:
            Query result (row, list, or cursor based on parameters)
        """
        cursor = self.db.get_cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor

        except Exception as e:
            # rollback handled by cursor context
            raise

    def commit(self):
        """Commit database transaction."""
        # commit handled by cursor context

    @staticmethod
    def serialize_json(obj: Any) -> Optional[str]:
        """Safely serialize object to JSON.

        Args:
            obj: Object to serialize

        Returns:
            JSON string or None
        """
        return json.dumps(obj) if obj is not None else None

    @staticmethod
    def deserialize_json(json_str: str, default=None):
        """Safely deserialize JSON string.

        Args:
            json_str: JSON string to deserialize
            default: Default value if deserialization fails

        Returns:
            Deserialized object or default
        """
        if not json_str:
            return default
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def now_timestamp() -> int:
        """Get current Unix timestamp.

        Returns:
            Unix timestamp
        """
        return int(datetime.now().timestamp())

    @staticmethod
    def from_timestamp(ts: Optional[int]) -> Optional[datetime]:
        """Convert timestamp to datetime.

        Args:
            ts: Unix timestamp (or None)

        Returns:
            Datetime object or None
        """
        if ts is None:
            return None
        return datetime.fromtimestamp(ts)

    def _ensure_schema(self):
        """Ensure planning memory tables exist."""

        # For PostgreSQL async databases, skip sync schema initialization
        if not hasattr(self.db, 'conn'):
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"{self.__class__.__name__}: PostgreSQL async database detected. Schema management handled by _init_schema().")
            return
        cursor = self.db.get_cursor()

        # Planning patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS planning_patterns (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                success_rate REAL DEFAULT 0.0,
                quality_score REAL DEFAULT 0.0,
                execution_count INTEGER DEFAULT 0,
                applicable_domains TEXT,
                applicable_task_types TEXT,
                complexity_min INTEGER DEFAULT 1,
                complexity_max INTEGER DEFAULT 10,
                conditions TEXT,
                source TEXT DEFAULT 'user',
                research_reference TEXT,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                feedback_count INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, name)
            )
        """)

        # Decomposition strategies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decomposition_strategies (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                strategy_name TEXT NOT NULL,
                description TEXT NOT NULL,
                decomposition_type TEXT NOT NULL,
                chunk_size_minutes INTEGER DEFAULT 30,
                max_depth INTEGER,
                adaptive_depth INTEGER DEFAULT 0,
                validation_gates TEXT,
                applicable_task_types TEXT,
                success_rate REAL DEFAULT 0.0,
                avg_actual_vs_planned_ratio REAL DEFAULT 1.0,
                quality_improvement_pct REAL DEFAULT 0.0,
                token_efficiency REAL DEFAULT 1.0,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                usage_count INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, strategy_name)
            )
        """)

        # Orchestrator patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orchestrator_patterns (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                pattern_name TEXT NOT NULL,
                description TEXT NOT NULL,
                agent_roles TEXT NOT NULL,
                coordination_type TEXT NOT NULL,
                num_agents INTEGER DEFAULT 1,
                effectiveness_improvement_pct REAL DEFAULT 0.0,
                handoff_success_rate REAL DEFAULT 0.0,
                speedup_factor REAL DEFAULT 1.0,
                token_overhead_multiplier REAL DEFAULT 1.0,
                applicable_domains TEXT,
                applicable_task_types TEXT,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                execution_count INTEGER DEFAULT 0,
                successful_executions INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, pattern_name)
            )
        """)

        # Validation rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_rules (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                rule_name TEXT NOT NULL,
                description TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                check_function TEXT NOT NULL,
                parameters TEXT,
                applicable_to_task_types TEXT,
                applies_to_phases TEXT,
                risk_level TEXT DEFAULT 'medium',
                dependencies TEXT,
                accuracy_pct REAL DEFAULT 0.0,
                precision REAL DEFAULT 0.0,
                recall REAL DEFAULT 0.0,
                f1_score REAL DEFAULT 0.0,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                execution_count INTEGER DEFAULT 0,
                violations_caught INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, rule_name)
            )
        """)

        # Execution feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_feedback (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                task_id INTEGER,
                pattern_id INTEGER,
                orchestration_pattern_id INTEGER,
                execution_outcome TEXT NOT NULL,
                execution_quality_score REAL DEFAULT 0.0,
                planned_duration_minutes INTEGER,
                actual_duration_minutes INTEGER,
                duration_variance_pct REAL DEFAULT 0.0,
                blockers_encountered TEXT,
                adjustments_made TEXT,
                assumption_violations TEXT,
                learning_extracted TEXT,
                confidence_in_learning REAL DEFAULT 0.0,
                quality_metrics TEXT,
                created_at INTEGER NOT NULL,
                executor_agent TEXT,
                phase_number INTEGER,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (pattern_id) REFERENCES planning_patterns(id) ON DELETE SET NULL,
                FOREIGN KEY (orchestration_pattern_id) REFERENCES orchestrator_patterns(id) ON DELETE SET NULL
            )
        """)

        # Indices for efficient querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_patterns_project_type
            ON planning_patterns(project_id, pattern_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_patterns_success
            ON planning_patterns(project_id, success_rate DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_strategies_project
            ON decomposition_strategies(project_id, success_rate DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orchestration_project
            ON orchestrator_patterns(project_id, speedup_factor DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_rules_project_risk
            ON validation_rules(project_id, risk_level)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_pattern
            ON execution_feedback(pattern_id, execution_outcome)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback_created
            ON execution_feedback(project_id, created_at DESC)
        """)

        # commit handled by cursor context

    # ==================== PLANNING PATTERNS ====================

    def create_planning_pattern(self, pattern: PlanningPattern) -> int:
        """Create a new planning pattern.

        Args:
            pattern: PlanningPattern instance

        Returns:
            ID of created pattern
        """
        pattern_type_str = (
            pattern.pattern_type.value
            if hasattr(pattern.pattern_type, "value")
            else pattern.pattern_type
        )

        cursor = self.execute(
            """
            INSERT INTO planning_patterns (
                project_id, pattern_type, name, description,
                success_rate, quality_score, execution_count,
                applicable_domains, applicable_task_types,
                complexity_min, complexity_max, conditions,
                source, research_reference, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                pattern.project_id,
                pattern_type_str,
                pattern.name,
                pattern.description,
                pattern.success_rate,
                pattern.quality_score,
                pattern.execution_count,
                self.serialize_json(pattern.applicable_domains),
                self.serialize_json(pattern.applicable_task_types),
                pattern.complexity_range[0],
                pattern.complexity_range[1],
                self.serialize_json(pattern.conditions),
                pattern.source,
                pattern.research_reference,
                int(pattern.created_at.timestamp()),
            ),
        )

        pattern_id = cursor.lastrowid
        self.commit()
        return pattern_id

    def get_planning_pattern(self, pattern_id: int) -> Optional[PlanningPattern]:
        """Retrieve a planning pattern by ID.

        Args:
            pattern_id: Pattern ID

        Returns:
            PlanningPattern or None if not found
        """
        row = self.execute(
            "SELECT * FROM planning_patterns WHERE id = ?", (pattern_id,), fetch_one=True
        )

        if not row:
            return None

        return self._row_to_planning_pattern(row)

    def find_patterns_by_task_type(
        self, project_id: int, task_type: str, complexity: int = 5, limit: int = 3
    ) -> List[PlanningPattern]:
        """Find planning patterns applicable to a task type.

        Args:
            project_id: Project ID
            task_type: Task type to find patterns for
            complexity: Task complexity (1-10)
            limit: Maximum results

        Returns:
            List of matching PlanningPattern objects
        """
        rows = self.execute(
            """
            SELECT * FROM planning_patterns
            WHERE project_id = ?
            AND applicable_task_types LIKE ?
            AND complexity_min <= ? AND complexity_max >= ?
            ORDER BY success_rate DESC, quality_score DESC
            LIMIT ?
        """,
            (project_id, f"%{task_type}%", complexity, complexity, limit),
            fetch_all=True,
        )

        patterns = []
        for row in (rows or []):
            pattern = self._row_to_planning_pattern(row)
            if pattern:
                patterns.append(pattern)

        return patterns

    def find_patterns_by_domain(
        self, project_id: int, domain: str, limit: int = 5
    ) -> List[PlanningPattern]:
        """Find planning patterns applicable to a domain.

        Args:
            project_id: Project ID
            domain: Domain (e.g., 'robotics', 'web', 'project-mgmt')
            limit: Maximum results

        Returns:
            List of matching PlanningPattern objects
        """
        rows = self.execute(
            """
            SELECT * FROM planning_patterns
            WHERE project_id = ?
            AND applicable_domains LIKE ?
            ORDER BY success_rate DESC
            LIMIT ?
        """,
            (project_id, f"%{domain}%", limit),
            fetch_all=True,
        )

        patterns = []
        for row in (rows or []):
            pattern = self._row_to_planning_pattern(row)
            if pattern:
                patterns.append(pattern)

        return patterns

    def update_planning_pattern_metrics(
        self,
        pattern_id: int,
        success_rate: float,
        quality_score: float,
        execution_count: int,
    ) -> bool:
        """Update pattern metrics based on execution results.

        Args:
            pattern_id: Pattern ID
            success_rate: New success rate
            quality_score: New quality score
            execution_count: New execution count

        Returns:
            True if updated
        """
        cursor = self.execute(
            """
            UPDATE planning_patterns
            SET success_rate = ?, quality_score = ?, execution_count = ?,
                last_used = ?
            WHERE id = ?
        """,
            (
                success_rate,
                quality_score,
                execution_count,
                self.now_timestamp(),
                pattern_id,
            ),
        )

        self.commit()
        return cursor.rowcount > 0

    # ==================== DECOMPOSITION STRATEGIES ====================

    def create_decomposition_strategy(self, strategy: DecompositionStrategy) -> int:
        """Create a new decomposition strategy.

        Args:
            strategy: DecompositionStrategy instance

        Returns:
            ID of created strategy
        """
        decomp_type_str = (
            strategy.decomposition_type.value
            if hasattr(strategy.decomposition_type, "value")
            else strategy.decomposition_type
        )

        cursor = self.execute(
            """
            INSERT INTO decomposition_strategies (
                project_id, strategy_name, description, decomposition_type,
                chunk_size_minutes, max_depth, adaptive_depth,
                validation_gates, applicable_task_types,
                success_rate, avg_actual_vs_planned_ratio,
                quality_improvement_pct, token_efficiency,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                strategy.project_id,
                strategy.strategy_name,
                strategy.description,
                decomp_type_str,
                strategy.chunk_size_minutes,
                strategy.max_depth,
                1 if strategy.adaptive_depth else 0,
                self.serialize_json(strategy.validation_gates),
                self.serialize_json(strategy.applicable_task_types),
                strategy.success_rate,
                strategy.avg_actual_vs_planned_ratio,
                strategy.quality_improvement_pct,
                strategy.token_efficiency,
                int(strategy.created_at.timestamp()),
            ),
        )

        strategy_id = cursor.lastrowid
        self.commit()
        return strategy_id

    def get_decomposition_strategy(self, strategy_id: int) -> Optional[DecompositionStrategy]:
        """Retrieve a decomposition strategy by ID.

        Args:
            strategy_id: Strategy ID

        Returns:
            DecompositionStrategy or None if not found
        """
        row = self.execute(
            "SELECT * FROM decomposition_strategies WHERE id = ?", (strategy_id,), fetch_one=True
        )

        if not row:
            return None

        return self._row_to_decomposition_strategy(row)

    def find_strategies_by_type(
        self, project_id: int, task_type: str, limit: int = 3
    ) -> List[DecompositionStrategy]:
        """Find decomposition strategies for a task type.

        Args:
            project_id: Project ID
            task_type: Task type
            limit: Maximum results

        Returns:
            List of matching DecompositionStrategy objects
        """
        rows = self.execute(
            """
            SELECT * FROM decomposition_strategies
            WHERE project_id = ?
            AND applicable_task_types LIKE ?
            ORDER BY success_rate DESC
            LIMIT ?
        """,
            (project_id, f"%{task_type}%", limit),
            fetch_all=True,
        )

        strategies = []
        for row in (rows or []):
            strategy = self._row_to_decomposition_strategy(row)
            if strategy:
                strategies.append(strategy)

        return strategies

    # ==================== ORCHESTRATOR PATTERNS ====================

    def create_orchestrator_pattern(self, pattern: OrchestratorPattern) -> int:
        """Create a new orchestrator pattern.

        Args:
            pattern: OrchestratorPattern instance

        Returns:
            ID of created pattern
        """
        coord_type_str = (
            pattern.coordination_type.value
            if hasattr(pattern.coordination_type, "value")
            else pattern.coordination_type
        )

        cursor = self.execute(
            """
            INSERT INTO orchestrator_patterns (
                project_id, pattern_name, description,
                agent_roles, coordination_type, num_agents,
                effectiveness_improvement_pct, handoff_success_rate,
                speedup_factor, token_overhead_multiplier,
                applicable_domains, applicable_task_types,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                pattern.project_id,
                pattern.pattern_name,
                pattern.description,
                self.serialize_json(pattern.agent_roles),
                coord_type_str,
                pattern.num_agents,
                pattern.effectiveness_improvement_pct,
                pattern.handoff_success_rate,
                pattern.speedup_factor,
                pattern.token_overhead_multiplier,
                self.serialize_json(pattern.applicable_domains),
                self.serialize_json(pattern.applicable_task_types),
                int(pattern.created_at.timestamp()),
            ),
        )

        pattern_id = cursor.lastrowid
        self.commit()
        return pattern_id

    def get_orchestrator_pattern(self, pattern_id: int) -> Optional[OrchestratorPattern]:
        """Retrieve an orchestrator pattern by ID.

        Args:
            pattern_id: Pattern ID

        Returns:
            OrchestratorPattern or None if not found
        """
        row = self.execute(
            "SELECT * FROM orchestrator_patterns WHERE id = ?", (pattern_id,), fetch_one=True
        )

        if not row:
            return None

        return self._row_to_orchestrator_pattern(row)

    def find_orchestration_patterns(
        self,
        project_id: int,
        num_agents: int,
        domain: Optional[str] = None,
        limit: int = 3,
    ) -> List[OrchestratorPattern]:
        """Find orchestration patterns for given configuration.

        Args:
            project_id: Project ID
            num_agents: Number of agents
            domain: Optional domain filter
            limit: Maximum results

        Returns:
            List of matching OrchestratorPattern objects
        """
        if domain:
            rows = self.execute(
                """
                SELECT * FROM orchestrator_patterns
                WHERE project_id = ?
                AND num_agents = ?
                AND applicable_domains LIKE ?
                ORDER BY speedup_factor DESC
                LIMIT ?
            """,
                (project_id, num_agents, f"%{domain}%", limit),
                fetch_all=True,
            )
        else:
            rows = self.execute(
                """
                SELECT * FROM orchestrator_patterns
                WHERE project_id = ?
                AND num_agents = ?
                ORDER BY speedup_factor DESC
                LIMIT ?
            """,
                (project_id, num_agents, limit),
                fetch_all=True,
            )

        patterns = []
        for row in (rows or []):
            pattern = self._row_to_orchestrator_pattern(row)
            if pattern:
                patterns.append(pattern)

        return patterns

    # ==================== VALIDATION RULES ====================

    def create_validation_rule(self, rule: ValidationRule) -> int:
        """Create a new validation rule.

        Args:
            rule: ValidationRule instance

        Returns:
            ID of created rule
        """
        rule_type_str = (
            rule.rule_type.value if hasattr(rule.rule_type, "value") else rule.rule_type
        )

        cursor = self.execute(
            """
            INSERT INTO validation_rules (
                project_id, rule_name, description, rule_type,
                check_function, parameters, applicable_to_task_types,
                applies_to_phases, risk_level, dependencies,
                accuracy_pct, precision, recall, f1_score,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                rule.project_id,
                rule.rule_name,
                rule.description,
                rule_type_str,
                rule.check_function,
                self.serialize_json(rule.parameters),
                self.serialize_json(rule.applicable_to_task_types),
                self.serialize_json(rule.applies_to_phases),
                rule.risk_level,
                self.serialize_json(rule.dependencies),
                rule.accuracy_pct,
                rule.precision,
                rule.recall,
                rule.f1_score,
                int(rule.created_at.timestamp()),
            ),
        )

        rule_id = cursor.lastrowid
        self.commit()
        return rule_id

    def get_validation_rule(self, rule_id: int) -> Optional[ValidationRule]:
        """Retrieve a validation rule by ID.

        Args:
            rule_id: Rule ID

        Returns:
            ValidationRule or None if not found
        """
        row = self.execute("SELECT * FROM validation_rules WHERE id = ?", (rule_id,), fetch_one=True)

        if not row:
            return None

        return self._row_to_validation_rule(row)

    def find_validation_rules_by_task_type(
        self, project_id: int, task_type: str, limit: int = 5
    ) -> List[ValidationRule]:
        """Find validation rules for a task type.

        Args:
            project_id: Project ID
            task_type: Task type
            limit: Maximum results

        Returns:
            List of matching ValidationRule objects
        """
        rows = self.execute(
            """
            SELECT * FROM validation_rules
            WHERE project_id = ?
            AND applicable_to_task_types LIKE ?
            ORDER BY f1_score DESC, accuracy_pct DESC
            LIMIT ?
        """,
            (project_id, f"%{task_type}%", limit),
            fetch_all=True,
        )

        rules = []
        for row in (rows or []):
            rule = self._row_to_validation_rule(row)
            if rule:
                rules.append(rule)

        return rules

    def find_validation_rules_by_risk(
        self, project_id: int, risk_level: str, limit: int = 5
    ) -> List[ValidationRule]:
        """Find validation rules by risk level.

        Args:
            project_id: Project ID
            risk_level: Risk level (low, medium, high, critical)
            limit: Maximum results

        Returns:
            List of matching ValidationRule objects
        """
        rows = self.execute(
            """
            SELECT * FROM validation_rules
            WHERE project_id = ?
            AND risk_level = ?
            ORDER BY f1_score DESC
            LIMIT ?
        """,
            (project_id, risk_level, limit),
            fetch_all=True,
        )

        rules = []
        for row in (rows or []):
            rule = self._row_to_validation_rule(row)
            if rule:
                rules.append(rule)

        return rules

    # ==================== EXECUTION FEEDBACK ====================

    def record_execution_feedback(self, feedback: ExecutionFeedback) -> int:
        """Record execution feedback.

        Args:
            feedback: ExecutionFeedback instance

        Returns:
            ID of recorded feedback
        """
        outcome_str = (
            feedback.execution_outcome.value
            if hasattr(feedback.execution_outcome, "value")
            else feedback.execution_outcome
        )

        # Calculate duration variance if needed
        if feedback.planned_duration_minutes and feedback.actual_duration_minutes:
            feedback.calculate_duration_variance()

        cursor = self.execute(
            """
            INSERT INTO execution_feedback (
                project_id, task_id, pattern_id,
                orchestration_pattern_id, execution_outcome,
                execution_quality_score, planned_duration_minutes,
                actual_duration_minutes, duration_variance_pct,
                blockers_encountered, adjustments_made,
                assumption_violations, learning_extracted,
                confidence_in_learning, quality_metrics,
                created_at, executor_agent, phase_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                feedback.project_id,
                feedback.task_id,
                feedback.pattern_id,
                feedback.orchestration_pattern_id,
                outcome_str,
                feedback.execution_quality_score,
                feedback.planned_duration_minutes,
                feedback.actual_duration_minutes,
                feedback.duration_variance_pct,
                self.serialize_json(feedback.blockers_encountered),
                self.serialize_json(feedback.adjustments_made),
                self.serialize_json(feedback.assumption_violations),
                feedback.learning_extracted,
                feedback.confidence_in_learning,
                self.serialize_json(feedback.quality_metrics),
                int(feedback.created_at.timestamp()),
                feedback.executor_agent,
                feedback.phase_number,
            ),
        )

        feedback_id = cursor.lastrowid
        self.commit()
        return feedback_id

    def get_execution_feedback(self, feedback_id: int) -> Optional[ExecutionFeedback]:
        """Retrieve execution feedback by ID.

        Args:
            feedback_id: Feedback ID

        Returns:
            ExecutionFeedback or None if not found
        """
        row = self.execute(
            "SELECT * FROM execution_feedback WHERE id = ?", (feedback_id,), fetch_one=True
        )

        if not row:
            return None

        return self._row_to_execution_feedback(row)

    def get_feedback_for_pattern(
        self, pattern_id: int, limit: int = 10
    ) -> List[ExecutionFeedback]:
        """Get execution feedback for a specific pattern.

        Args:
            pattern_id: Pattern ID
            limit: Maximum results

        Returns:
            List of ExecutionFeedback objects
        """
        rows = self.execute(
            """
            SELECT * FROM execution_feedback
            WHERE pattern_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (pattern_id, limit),
            fetch_all=True,
        )

        feedback_list = []
        for row in (rows or []):
            feedback = self._row_to_execution_feedback(row)
            if feedback:
                feedback_list.append(feedback)

        return feedback_list

    # ==================== HELPER METHODS ====================

    @staticmethod
    def _row_to_planning_pattern(row: tuple) -> Optional[PlanningPattern]:
        """Convert database row to PlanningPattern object."""
        if not row:
            return None

        try:
            return PlanningPattern(
                id=row[0],
                project_id=row[1],
                pattern_type=row[2],
                name=row[3],
                description=row[4],
                success_rate=row[5],
                quality_score=row[6],
                execution_count=row[7],
                applicable_domains=json.loads(row[8]) if row[8] else [],
                applicable_task_types=json.loads(row[9]) if row[9] else [],
                complexity_range=(row[10], row[11]),
                conditions=json.loads(row[12]) if row[12] else {},
                source=row[13],
                research_reference=row[14],
                created_at=datetime.fromtimestamp(row[15]),
                last_used=datetime.fromtimestamp(row[16]) if row[16] else None,
                feedback_count=row[17],
            )
        except Exception:
            return None

    @staticmethod
    def _row_to_decomposition_strategy(row: tuple) -> Optional[DecompositionStrategy]:
        """Convert database row to DecompositionStrategy object."""
        if not row:
            return None

        try:
            return DecompositionStrategy(
                id=row[0],
                project_id=row[1],
                strategy_name=row[2],
                description=row[3],
                decomposition_type=row[4],
                chunk_size_minutes=row[5],
                max_depth=row[6],
                adaptive_depth=bool(row[7]),
                validation_gates=json.loads(row[8]) if row[8] else [],
                applicable_task_types=json.loads(row[9]) if row[9] else [],
                success_rate=row[10],
                avg_actual_vs_planned_ratio=row[11],
                quality_improvement_pct=row[12],
                token_efficiency=row[13],
                created_at=datetime.fromtimestamp(row[14]),
                last_used=datetime.fromtimestamp(row[15]) if row[15] else None,
                usage_count=row[16],
            )
        except Exception:
            return None

    @staticmethod
    def _row_to_orchestrator_pattern(row: tuple) -> Optional[OrchestratorPattern]:
        """Convert database row to OrchestratorPattern object."""
        if not row:
            return None

        try:
            return OrchestratorPattern(
                id=row[0],
                project_id=row[1],
                pattern_name=row[2],
                description=row[3],
                agent_roles=json.loads(row[4]) if row[4] else [],
                coordination_type=row[5],
                num_agents=row[6],
                effectiveness_improvement_pct=row[7],
                handoff_success_rate=row[8],
                speedup_factor=row[9],
                token_overhead_multiplier=row[10],
                applicable_domains=json.loads(row[11]) if row[11] else [],
                applicable_task_types=json.loads(row[12]) if row[12] else [],
                created_at=datetime.fromtimestamp(row[13]),
                last_used=datetime.fromtimestamp(row[14]) if row[14] else None,
                execution_count=row[15],
                successful_executions=row[16],
            )
        except Exception:
            return None

    @staticmethod
    def _row_to_validation_rule(row: tuple) -> Optional[ValidationRule]:
        """Convert database row to ValidationRule object."""
        if not row:
            return None

        try:
            return ValidationRule(
                id=row[0],
                project_id=row[1],
                rule_name=row[2],
                description=row[3],
                rule_type=row[4],
                check_function=row[5],
                parameters=json.loads(row[6]) if row[6] else {},
                applicable_to_task_types=json.loads(row[7]) if row[7] else [],
                applies_to_phases=json.loads(row[8]) if row[8] else [],
                risk_level=row[9],
                dependencies=json.loads(row[10]) if row[10] else [],
                accuracy_pct=row[11],
                precision=row[12],
                recall=row[13],
                f1_score=row[14],
                created_at=datetime.fromtimestamp(row[15]),
                last_used=datetime.fromtimestamp(row[16]) if row[16] else None,
                execution_count=row[17],
                violations_caught=row[18],
            )
        except Exception:
            return None

    @staticmethod
    def _row_to_execution_feedback(row: tuple) -> Optional[ExecutionFeedback]:
        """Convert database row to ExecutionFeedback object."""
        if not row:
            return None

        try:
            return ExecutionFeedback(
                id=row[0],
                project_id=row[1],
                task_id=row[2],
                pattern_id=row[3],
                orchestration_pattern_id=row[4],
                execution_outcome=row[5],
                execution_quality_score=row[6],
                planned_duration_minutes=row[7],
                actual_duration_minutes=row[8],
                duration_variance_pct=row[9],
                blockers_encountered=json.loads(row[10]) if row[10] else [],
                adjustments_made=json.loads(row[11]) if row[11] else [],
                assumption_violations=json.loads(row[12]) if row[12] else [],
                learning_extracted=row[13],
                confidence_in_learning=row[14],
                quality_metrics=json.loads(row[15]) if row[15] else {},
                created_at=datetime.fromtimestamp(row[16]),
                executor_agent=row[17],
                phase_number=row[18],
            )
        except Exception:
            return None
