"""Prospective memory storage and trigger management."""

import time
from datetime import datetime
from typing import Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import (
    Plan,
    PhaseMetrics,
    ProspectiveTask,
    TaskDependency,
    TaskPhase,
    TaskPriority,
    TaskStatus,
    TaskTrigger,
    TriggerType,
)


class ProspectiveStore(BaseStore):
    """Manages prospective tasks and triggers."""

    table_name = "prospective_tasks"
    model_class = ProspectiveTask

    def __init__(self, db: Database):
        """Initialize prospective store.

        Args:
            db: Database instance
        """
        super().__init__(db)
        # Ensure phase tracking schema is present

    def _row_to_model(self, row: Dict[str, Any]) -> ProspectiveTask:
        """Convert database row to ProspectiveTask model.

        Args:
            row: Database row as dict

        Returns:
            ProspectiveTask instance
        """
        return self._row_to_task(row if isinstance(row, dict) else dict(row))

    def _ensure_schema(self):
        """Ensure prospective memory tables exist."""

        # For PostgreSQL async databases, skip sync schema initialization
        if not hasattr(self.db, "conn"):
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(
                f"{self.__class__.__name__}: PostgreSQL async database detected. Schema management handled by _init_schema()."
            )
            return
        cursor = self.db.get_cursor()

        # Tasks table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prospective_tasks (
                id SERIAL PRIMARY KEY,
                project_id INTEGER,
                content TEXT NOT NULL,
                active_form TEXT NOT NULL,

                created_at INTEGER NOT NULL,
                due_at INTEGER,
                completed_at INTEGER,

                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',

                -- Phase tracking (agentic workflow)
                phase TEXT DEFAULT 'planning',
                plan_json TEXT,
                plan_created_at INTEGER,
                phase_started_at INTEGER,
                phase_metrics_json TEXT,
                actual_duration_minutes REAL,

                assignee TEXT DEFAULT 'user',

                notes TEXT,
                blocked_reason TEXT,
                failure_reason TEXT,
                lessons_learned TEXT,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """
        )

        # Add missing columns if they don't exist (for backward compatibility)
        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN phase TEXT DEFAULT 'planning'")
        except psycopg.errors.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN plan_json TEXT")
        except psycopg.errors.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN plan_created_at INTEGER")
        except psycopg.errors.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN phase_started_at INTEGER")
        except psycopg.errors.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN phase_metrics_json TEXT")
        except psycopg.errors.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN actual_duration_minutes REAL")
        except psycopg.errors.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN lessons_learned TEXT")
        except psycopg.errors.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN blocked_reason TEXT")
        except psycopg.errors.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN failure_reason TEXT")
        except psycopg.errors.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN notes TEXT")
        except psycopg.errors.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE prospective_tasks ADD COLUMN assignee TEXT")
        except psycopg.errors.OperationalError:
            pass

        # Task triggers
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_triggers (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_condition TEXT NOT NULL,
                fired BOOLEAN DEFAULT 0,
                fired_at INTEGER,
                FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
            )
        """
        )

        # Task dependencies
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id INTEGER NOT NULL,
                depends_on_task_id INTEGER NOT NULL,
                dependency_type TEXT DEFAULT 'blocks',
                PRIMARY KEY (task_id, depends_on_task_id),
                FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (depends_on_task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
            )
        """
        )

        # Task phases/milestones
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS phases (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                phase_name TEXT NOT NULL,
                sequence_number INTEGER,
                start_date INTEGER,
                end_date INTEGER,
                status TEXT DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES prospective_tasks(id) ON DELETE CASCADE
            )
        """
        )

        # Indices
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_project ON prospective_tasks(project_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON prospective_tasks(status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON prospective_tasks(priority)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_triggers_task ON task_triggers(task_id)")

        # commit handled by cursor context

    def create_task(self, task: ProspectiveTask) -> int:
        """Create a new prospective task.

        Args:
            task: Task to create

        Returns:
            ID of created task
        """
        status_str = task.status.value if isinstance(task.status, TaskStatus) else task.status
        priority_str = (
            task.priority.value if isinstance(task.priority, TaskPriority) else task.priority
        )
        phase_str = task.phase.value if isinstance(task.phase, TaskPhase) else task.phase
        plan_json = self.serialize_json(task.plan.dict()) if task.plan else None

        cursor = self.execute(
            """
            INSERT INTO prospective_tasks (
                project_id, content, active_form,
                created_at, due_at, completed_at,
                status, priority, assignee,
                phase, plan_json, plan_created_at,
                notes, blocked_reason, failure_reason, lessons_learned
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                task.project_id,
                task.content,
                task.active_form,
                int(task.created_at.timestamp()),
                int(task.due_at.timestamp()) if task.due_at else None,
                int(task.completed_at.timestamp()) if task.completed_at else None,
                status_str,
                priority_str,
                task.assignee,
                phase_str,
                plan_json,
                int(task.plan_created_at.timestamp()) if task.plan_created_at else None,
                task.notes,
                task.blocked_reason,
                task.failure_reason,
                task.lessons_learned,
            ),
        )
        self.commit()
        return cursor.lastrowid

    def get_task(self, task_id: int) -> Optional[ProspectiveTask]:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        row = self.execute(
            "SELECT * FROM prospective_tasks WHERE id = %s", (task_id,), fetch_one=True
        )

        if not row:
            return None

        return self._row_to_task(row if isinstance(row, dict) else dict(row))

    def update_task_status(self, task_id: int, status: TaskStatus, reason: Optional[str] = None):
        """Update task status.

        Args:
            task_id: Task ID
            status: New status
            reason: Optional reason (for blocked status)
        """
        status_str = status.value if isinstance(status, TaskStatus) else status

        if status == TaskStatus.COMPLETED:
            self.execute(
                """
                UPDATE prospective_tasks
                SET status = ?, completed_at = ?
                WHERE id = %s
            """,
                (status_str, int(time.time()), task_id),
            )
        elif status == TaskStatus.BLOCKED:
            self.execute(
                """
                UPDATE prospective_tasks
                SET status = ?, blocked_reason = ?
                WHERE id = %s
            """,
                (status_str, reason, task_id),
            )
        else:
            self.execute(
                "UPDATE prospective_tasks SET status = %s WHERE id = %s",
                (status_str, task_id),
            )

        self.commit()

        # Wire to ConsolidationHook for task pattern learning
        # This triggers learning when a task completes
        if status == TaskStatus.COMPLETED:
            try:
                from .consolidation_hook import ConsolidationHook

                hook = ConsolidationHook(self.db)

                # Get task to check if it has a learned_pattern_id
                task = self.get_task(task_id)
                if task and hasattr(task, "learned_pattern_id") and task.learned_pattern_id:
                    # Success if status is COMPLETED
                    hook.on_task_completed_with_pattern(
                        task_id=task_id,
                        pattern_id=task.learned_pattern_id,
                        success=True,
                        actual_outcome=reason,
                    )
            except ImportError:
                # Task pattern consolidation optional (degradation)
                pass
            except Exception as e:
                # Log but don't fail on consolidation errors
                import logging

                logging.warning(f"Failed to consolidate task {task_id}: {e}")

    def update_task_phase(
        self, task_id: int, new_phase: TaskPhase, plan: Optional[Plan] = None
    ) -> Optional[ProspectiveTask]:
        """Update task phase (agentic workflow).

        Args:
            task_id: Task ID
            new_phase: New phase
            plan: Optional plan (if planning phase)

        Returns:
            Updated task or None if not found
        """
        phase_str = new_phase.value if isinstance(new_phase, TaskPhase) else new_phase
        now_ts = int(time.time())

        # Serialize plan if provided
        plan_json = self.serialize_json(plan.dict()) if plan else None

        self.execute(
            """
            UPDATE prospective_tasks
            SET phase = ?, phase_started_at = ?, plan_json = ?, plan_created_at = ?
            WHERE id = %s
        """,
            (phase_str, now_ts, plan_json, now_ts if plan else None, task_id),
        )

        self.commit()

        return self.get_task(task_id)

    def complete_phase(self, task_id: int, next_phase: TaskPhase) -> Optional[ProspectiveTask]:
        """Complete current phase and move to next phase.

        Records phase metrics and transitions to new phase.

        Args:
            task_id: Task ID
            next_phase: Phase to transition to

        Returns:
            Updated task or None if not found
        """
        task = self.get_task(task_id)
        if not task:
            return None

        # Calculate phase duration
        if task.phase_started_at:
            duration = (datetime.now() - task.phase_started_at).total_seconds() / 60  # minutes
        else:
            duration = None

        # Record phase metrics
        metrics = PhaseMetrics(
            phase=task.phase,
            started_at=task.phase_started_at or datetime.now(),
            completed_at=datetime.now(),
            duration_minutes=duration,
        )

        task.phase_metrics.append(metrics)

        # Update actual duration if task is completing
        if next_phase == TaskPhase.COMPLETED or next_phase == TaskPhase.FAILED:
            if task.created_at:
                total_duration = (datetime.now() - task.created_at).total_seconds() / 60
                task.actual_duration_minutes = total_duration

        # Serialize phase metrics
        metrics_json = self.serialize_json([m.dict() for m in task.phase_metrics])

        # Update database
        next_phase_str = next_phase.value if isinstance(next_phase, TaskPhase) else next_phase
        now_ts = int(time.time())

        self.execute(
            """
            UPDATE prospective_tasks
            SET phase = ?, phase_started_at = ?, phase_metrics_json = ?,
                actual_duration_minutes = ?
            WHERE id = %s
        """,
            (
                next_phase_str,
                now_ts,
                metrics_json,
                task.actual_duration_minutes,
                task_id,
            ),
        )

        self.commit()

        return self.get_task(task_id)

    def create_plan_for_task(
        self,
        task_id: int,
        steps: list[str],
        estimated_duration_minutes: int = 30,
    ) -> Optional[ProspectiveTask]:
        """Create and attach a plan to a task.

        Args:
            task_id: Task ID
            steps: List of execution steps
            estimated_duration_minutes: Estimated total duration

        Returns:
            Updated task with plan, or None if task not found
        """
        task = self.get_task(task_id)
        if not task:
            return None

        # Create plan
        plan = Plan(
            task_id=task_id,
            steps=steps,
            estimated_duration_minutes=estimated_duration_minutes,
            validated=False,
        )

        # Update task with plan
        task.plan = plan
        task.plan_created_at = datetime.now()

        # Serialize and persist (use model_dump with mode='json' for proper datetime serialization)
        plan_data = plan.dict()
        # Convert datetime to ISO string for JSON serialization
        if "created_at" in plan_data and isinstance(plan_data["created_at"], datetime):
            plan_data["created_at"] = plan_data["created_at"].isoformat()
        plan_json = self.serialize_json(plan_data)

        self.execute(
            """
            UPDATE prospective_tasks
            SET plan_json = ?, plan_created_at = ?
            WHERE id = %s
        """,
            (plan_json, int(task.plan_created_at.timestamp()), task_id),
        )

        self.commit()
        return self.get_task(task_id)

    def validate_plan(self, task_id: int, notes: Optional[str] = None) -> Optional[ProspectiveTask]:
        """Mark plan as validated.

        Args:
            task_id: Task ID
            notes: Optional validation notes

        Returns:
            Updated task or None if not found
        """
        task = self.get_task(task_id)
        if not task or not task.plan:
            return None

        # Update plan validation
        task.plan.validated = True
        task.plan.validation_notes = notes

        # Serialize and persist
        plan_json = self.serialize_json(task.plan.dict())

        self.execute(
            """
            UPDATE prospective_tasks
            SET plan_json = ?
            WHERE id = %s
        """,
            (plan_json, task_id),
        )

        self.commit()
        return self.get_task(task_id)

    def mark_plan_ready(self, task_id: int) -> Optional[ProspectiveTask]:
        """Mark task as ready for execution (transition to PLAN_READY phase).

        Requires:
        - Task exists
        - Task has a plan
        - Plan is validated

        Args:
            task_id: Task ID

        Returns:
            Updated task in PLAN_READY phase, or None if preconditions not met
        """
        task = self.get_task(task_id)
        if not task:
            return None

        # Verify plan exists and is validated
        if not task.plan:
            return None

        if not task.plan.validated:
            return None

        # Transition to PLAN_READY phase
        return self.update_task_phase(task_id, TaskPhase.PLAN_READY)

    def get_tasks_by_phase(
        self,
        phase: TaskPhase,
        project_id: Optional[int] = None,
        limit: int = 50,
    ) -> list[ProspectiveTask]:
        """Get all tasks in a specific phase.

        Args:
            phase: Target phase
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of tasks in the specified phase
        """
        phase_str = phase.value if isinstance(phase, TaskPhase) else phase

        sql = "SELECT * FROM prospective_tasks WHERE phase = %s"
        params = [phase_str]

        if project_id is not None:
            sql += " AND project_id = %s"
            params.append(project_id)

        sql += " ORDER BY priority DESC, created_at DESC LIMIT %s"
        params.append(limit)

        rows = self.execute(sql, tuple(params), fetch_all=True)
        return [
            self._row_to_task(row if isinstance(row, dict) else dict(row)) for row in (rows or [])
        ]

    def get_tasks_by_project(self, project_id: int, limit: int = 100) -> list[ProspectiveTask]:
        """Get all tasks in a project.

        Args:
            project_id: Project ID
            limit: Maximum results

        Returns:
            List of all tasks in the project
        """
        rows = self.execute(
            "SELECT * FROM prospective_tasks WHERE project_id = %s ORDER BY created_at DESC LIMIT %s",
            (project_id, limit),
            fetch_all=True,
        )
        return [
            self._row_to_task(row if isinstance(row, dict) else dict(row)) for row in (rows or [])
        ]

    def list_tasks(
        self,
        project_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        assignee: Optional[str] = None,
        limit: int = 50,
    ) -> list[ProspectiveTask]:
        """List tasks with filters.

        Args:
            project_id: Optional project filter
            status: Optional status filter
            assignee: Optional assignee filter
            limit: Maximum results

        Returns:
            List of tasks
        """
        sql = "SELECT * FROM prospective_tasks WHERE 1=1"
        params = []

        if project_id is not None:
            sql += " AND project_id = %s"
            params.append(project_id)

        if status:
            status_str = status.value if isinstance(status, TaskStatus) else status
            sql += " AND status = %s"
            params.append(status_str)

        if assignee:
            sql += " AND assignee = %s"
            params.append(assignee)

        sql += " ORDER BY priority DESC, created_at DESC LIMIT %s"
        params.append(limit)

        rows = self.execute(sql, tuple(params), fetch_all=True)
        return [
            self._row_to_task(row if isinstance(row, dict) else dict(row)) for row in (rows or [])
        ]

    def get_ready_tasks(self, project_id: Optional[int] = None) -> list[ProspectiveTask]:
        """Get tasks that are ready to work on (pending with no blocking dependencies).

        Args:
            project_id: Optional project filter

        Returns:
            List of ready tasks
        """
        sql = """
            SELECT t.* FROM prospective_tasks t
            WHERE t.status = 'pending'
            AND NOT EXISTS (
                SELECT 1 FROM task_dependencies d
                JOIN prospective_tasks dt ON d.depends_on_task_id = dt.id
                WHERE d.task_id = t.id AND dt.status != 'completed'
            )
        """

        params = []
        if project_id is not None:
            sql += " AND t.project_id = %s"
            params.append(project_id)

        sql += " ORDER BY t.priority DESC, t.created_at ASC"

        rows = self.execute(sql, tuple(params) if params else None, fetch_all=True)
        return [
            self._row_to_task(row if isinstance(row, dict) else dict(row)) for row in (rows or [])
        ]

    def add_trigger(self, trigger: TaskTrigger) -> int:
        """Add a trigger to a task.

        Args:
            trigger: Trigger to add

        Returns:
            ID of created trigger
        """
        trigger_type_str = (
            trigger.trigger_type.value
            if isinstance(trigger.trigger_type, TriggerType)
            else trigger.trigger_type
        )

        cursor = self.execute(
            """
            INSERT INTO task_triggers (task_id, trigger_type, trigger_condition, fired, fired_at)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (
                trigger.task_id,
                trigger_type_str,
                self.serialize_json(trigger.trigger_condition),
                trigger.fired,
                int(trigger.fired_at.timestamp()) if trigger.fired_at else None,
            ),
        )
        self.commit()
        return cursor.lastrowid

    def get_triggers(self, task_id: int) -> list[TaskTrigger]:
        """Get all triggers for a task.

        Args:
            task_id: Task ID

        Returns:
            List of triggers
        """
        rows = self.execute(
            "SELECT * FROM task_triggers WHERE task_id = %s", (task_id,), fetch_all=True
        )

        triggers = []
        for row in rows or []:
            row_dict = row if isinstance(row, dict) else dict(row)
            triggers.append(
                TaskTrigger(
                    id=row_dict.get("id"),
                    task_id=row_dict.get("task_id"),
                    trigger_type=TriggerType(row_dict.get("trigger_type")),
                    trigger_condition=self._safe_json_loads(row_dict.get("trigger_condition"), {}),
                    fired=bool(row_dict.get("fired")),
                    fired_at=(
                        datetime.fromtimestamp(row_dict.get("fired_at"))
                        if row_dict.get("fired_at")
                        else None
                    ),
                )
            )

        return triggers

    def fire_trigger(self, trigger_id: int):
        """Mark a trigger as fired.

        Args:
            trigger_id: Trigger ID
        """
        self.execute(
            """
            UPDATE task_triggers
            SET fired = 1, fired_at = %s
            WHERE id = %s
        """,
            (int(time.time()), trigger_id),
        )
        self.commit()

    def check_triggers(self, context: dict) -> list[tuple[ProspectiveTask, TaskTrigger]]:
        """Check which triggers should fire based on context.

        Args:
            context: Current context (cwd, files, time, etc.)

        Returns:
            List of (task, trigger) tuples that should fire
        """
        # Get all unfired triggers for pending tasks
        rows = self.execute(
            """
            SELECT t.*, tr.* FROM task_triggers tr
            JOIN prospective_tasks t ON tr.task_id = t.id
            WHERE tr.fired = 0 AND t.status = 'pending'
        """,
            fetch_all=True,
        )

        fired_tasks = []
        for row in rows or []:
            row_dict = row if isinstance(row, dict) else dict(row)
            trigger = TaskTrigger(
                id=row_dict.get("id"),
                task_id=row_dict.get("task_id"),
                trigger_type=TriggerType(row_dict.get("trigger_type")),
                trigger_condition=self._safe_json_loads(row_dict.get("trigger_condition"), {}),
                fired=False,
            )

            # Evaluate trigger condition
            if self._should_fire(trigger, context):
                task = self.get_task(trigger.task_id)
                if task:
                    fired_tasks.append((task, trigger))

        return fired_tasks

    def _should_fire(self, trigger: TaskTrigger, context: dict) -> bool:
        """Check if trigger should fire.

        Args:
            trigger: Trigger to check
            context: Current context

        Returns:
            True if trigger should fire
        """
        condition = trigger.trigger_condition

        if trigger.trigger_type == TriggerType.TIME:
            # Check if current time >= trigger time
            trigger_time = datetime.fromisoformat(condition.get("time", ""))
            return datetime.now() >= trigger_time

        elif trigger.trigger_type == TriggerType.CONTEXT:
            # Check if current cwd matches
            return context.get("cwd", "").startswith(condition.get("cwd", ""))

        elif trigger.trigger_type == TriggerType.FILE:
            # Check if file is in active files
            trigger_file = condition.get("file", "")
            return trigger_file in context.get("files", [])

        elif trigger.trigger_type == TriggerType.EVENT:
            # Check if event matches
            return condition.get("event") == context.get("last_event")

        return False

    def add_dependency(self, dependency: TaskDependency):
        """Add a dependency between tasks.

        Args:
            dependency: Dependency to add
        """
        self.execute(
            """
            INSERT OR REPLACE INTO task_dependencies (task_id, depends_on_task_id, dependency_type)
            VALUES (%s, %s, %s)
        """,
            (dependency.task_id, dependency.depends_on_task_id, dependency.dependency_type),
        )
        self.commit()

    def get_dependencies(self, task_id: int) -> list[ProspectiveTask]:
        """Get all tasks that this task depends on.

        Args:
            task_id: Task ID

        Returns:
            List of dependency tasks
        """
        rows = self.execute(
            """
            SELECT t.* FROM prospective_tasks t
            JOIN task_dependencies d ON t.id = d.depends_on_task_id
            WHERE d.task_id = %s
        """,
            (task_id,),
            fetch_all=True,
        )

        return [
            self._row_to_task(row if isinstance(row, dict) else dict(row)) for row in (rows or [])
        ]

    def find_similar_tasks(
        self,
        task: ProspectiveTask,
        project_id: Optional[int] = None,
        status: TaskStatus = TaskStatus.COMPLETED,
        limit: int = 5,
    ) -> list[ProspectiveTask]:
        """Find tasks similar to the given task (for pattern detection).

        Uses simple string similarity on task content.

        Args:
            task: Reference task
            project_id: Optional project filter
            status: Status filter (default: COMPLETED)
            limit: Maximum results

        Returns:
            List of similar tasks
        """
        sql = """
            SELECT * FROM prospective_tasks
            WHERE status = %s AND id != %s
        """
        params = [status.value if isinstance(status, TaskStatus) else status, task.id or -1]

        if project_id is not None:
            sql += " AND project_id = %s"
            params.append(project_id)

        sql += " ORDER BY completed_at DESC LIMIT %s"
        params.append(limit)

        rows = self.execute(sql, tuple(params), fetch_all=True)
        return [
            self._row_to_task(row if isinstance(row, dict) else dict(row)) for row in (rows or [])
        ]

    def find_recent_completed_tasks(
        self,
        project_id: Optional[int] = None,
        limit: int = 20,
        hours_back: int = 168,  # 1 week
    ) -> list[ProspectiveTask]:
        """Find recently completed tasks for pattern analysis.

        Args:
            project_id: Optional project filter
            limit: Maximum results
            hours_back: How far back to look (default: 1 week)

        Returns:
            List of recently completed tasks
        """
        cutoff_time = int(time.time()) - (hours_back * 3600)

        sql = """
            SELECT * FROM prospective_tasks
            WHERE status = %s AND completed_at > %s
        """
        params = [TaskStatus.COMPLETED.value, cutoff_time]

        if project_id is not None:
            sql += " AND project_id = %s"
            params.append(project_id)

        sql += " ORDER BY completed_at DESC LIMIT %s"
        params.append(limit)

        rows = self.execute(sql, tuple(params), fetch_all=True)
        return [
            self._row_to_task(row if isinstance(row, dict) else dict(row)) for row in (rows or [])
        ]

    def detect_task_patterns(
        self,
        project_id: Optional[int] = None,
        min_occurrences: int = 2,
        time_window_hours: int = 168,
    ) -> list[dict]:
        """Detect patterns in completed tasks (e.g., repeated task types).

        Args:
            project_id: Optional project filter
            min_occurrences: Minimum task repetitions to detect pattern
            time_window_hours: Time window for pattern detection

        Returns:
            List of pattern dicts with 'content', 'count', 'tasks'
        """
        recent_tasks = self.find_recent_completed_tasks(
            project_id=project_id,
            limit=100,
            hours_back=time_window_hours,
        )

        if len(recent_tasks) < min_occurrences:
            return []

        # Simple pattern detection: group by first N words of content
        patterns = {}
        for task in recent_tasks:
            # Extract first 3 words as pattern key
            words = task.content.split()[:3]
            pattern_key = " ".join(words) if words else task.content

            if pattern_key not in patterns:
                patterns[pattern_key] = {"content": pattern_key, "count": 0, "tasks": []}

            patterns[pattern_key]["count"] += 1
            patterns[pattern_key]["tasks"].append(task)

        # Filter to min_occurrences
        return [p for p in patterns.values() if p["count"] >= min_occurrences]

    def _safe_json_loads(self, data: str, default=None):
        """Safely load JSON string with default fallback.

        Args:
            data: JSON string to load
            default: Default value if parsing fails

        Returns:
            Parsed JSON or default value
        """
        if not data:
            return default
        try:
            from athena.core.error_handling import safe_json_loads

            return safe_json_loads(data, default)
        except (ImportError, AttributeError):
            return default

    def _row_to_task(self, row) -> ProspectiveTask:
        """Convert database row to ProspectiveTask.

        Args:
            row: Database row

        Returns:
            ProspectiveTask instance
        """
        # Convert psycopg Record to dict if needed
        if hasattr(row, "keys"):
            # Row-like object, convert to dict
            row_dict = dict(row)
        else:
            row_dict = row

        # Helper function for safe value retrieval
        def safe_get(d, key, default=None):
            try:
                return d[key] if key in d else default
            except (KeyError, TypeError):
                return default

        # Deserialize plan JSON if present
        plan = None
        plan_json = safe_get(row_dict, "plan_json")
        if plan_json:
            try:
                plan_data = self._safe_json_loads(plan_json, {})
                if plan_data:
                    plan = Plan(**plan_data)
            except (ValueError, TypeError):
                plan = None

        # Deserialize phase metrics JSON if present
        phase_metrics = []
        phase_metrics_json = safe_get(row_dict, "phase_metrics_json")
        if phase_metrics_json:
            try:
                metrics_data = self._safe_json_loads(phase_metrics_json, [])
                if metrics_data and isinstance(metrics_data, list):
                    phase_metrics = [PhaseMetrics(**m) for m in metrics_data]
            except (ValueError, TypeError):
                phase_metrics = []

        # Get phase with default
        phase_str = safe_get(row_dict, "phase", "planning")
        phase = TaskPhase(phase_str) if phase_str else TaskPhase.PLANNING

        # Get timestamps with safe conversion
        # PostgreSQL returns datetime objects directly, not timestamps
        def _to_datetime(val):
            """Convert value to datetime, handling both timestamps and datetime objects."""
            if not val:
                return None
            if isinstance(val, datetime):
                return val
            if isinstance(val, (int, float)):
                return datetime.fromtimestamp(val)
            return val

        created_at = safe_get(row_dict, "created_at")
        due_at = safe_get(row_dict, "due_at")
        completed_at = safe_get(row_dict, "completed_at")
        plan_created_at = safe_get(row_dict, "plan_created_at")
        phase_started_at = safe_get(row_dict, "phase_started_at")

        # Handle legacy status values: convert "in_progress" to "active"
        status_val = safe_get(row_dict, "status")
        if status_val == "in_progress":
            status_val = "active"

        # Handle priority: convert numeric values to enum strings
        priority_val = safe_get(row_dict, "priority", "medium")
        if isinstance(priority_val, int):
            # Map numeric priority to enum: 1=low, 2=medium, 3=high, 4=critical
            priority_map = {1: "low", 2: "medium", 3: "high", 4: "critical"}
            priority_val = priority_map.get(priority_val, "medium")
        elif priority_val is None or priority_val == "":
            priority_val = "medium"

        return ProspectiveTask(
            id=safe_get(row_dict, "id"),
            project_id=safe_get(row_dict, "project_id"),
            content=safe_get(row_dict, "content") or "[No content]",
            active_form=safe_get(row_dict, "active_form") or "[No description]",
            created_at=_to_datetime(created_at),
            due_at=_to_datetime(due_at),
            completed_at=_to_datetime(completed_at),
            status=TaskStatus(status_val) if status_val else TaskStatus.PENDING,
            priority=TaskPriority(priority_val) if priority_val else TaskPriority.MEDIUM,
            # Phase tracking
            phase=phase,
            plan=plan,
            plan_created_at=_to_datetime(plan_created_at),
            phase_started_at=_to_datetime(phase_started_at),
            phase_metrics=phase_metrics,
            actual_duration_minutes=safe_get(row_dict, "actual_duration_minutes"),
            assignee=safe_get(row_dict, "assignee") or "",
            notes=safe_get(row_dict, "notes") or "",
            blocked_reason=safe_get(row_dict, "blocked_reason"),
            failure_reason=safe_get(row_dict, "failure_reason"),
            lessons_learned=safe_get(row_dict, "lessons_learned"),
        )

    # ==================== ASYNC WRAPPER API ====================
    # These methods provide async wrappers for operations.py compatibility
    # Map generic CRUD operations to domain-specific store methods

    async def get(self, task_id: int) -> Optional["ProspectiveTask"]:
        """Get a task by ID (async wrapper for get_task).

        Args:
            task_id: Task ID

        Returns:
            ProspectiveTask or None if not found
        """
        return self.get_task(task_id)

    async def list(
        self, status: Optional[str] = None, limit: int = 100, **filters
    ) -> list["ProspectiveTask"]:
        """List tasks optionally filtered by status (async wrapper for list_tasks).

        Args:
            status: Optional status filter (pending, in_progress, completed, blocked)
            limit: Maximum tasks to return
            **filters: Additional filters

        Returns:
            List of tasks
        """
        tasks = self.list_tasks(limit=limit)

        # Filter by status if specified
        if status:
            tasks = [t for t in tasks if t.status.value == status]

        return tasks

    async def update(self, task: "ProspectiveTask") -> bool:
        """Update a task (async wrapper).

        Args:
            task: Task with updated values

        Returns:
            True if updated successfully
        """
        # Update task status which persists changes
        try:
            if task.status:
                self.update_task_status(
                    task_id=task.id,
                    new_status=task.status.value,
                    phase=task.phase.value if task.phase else None,
                )
            return True
        except Exception:
            return False
