"""Research task orchestration and finding storage."""

import json
from typing import Optional

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import (
    ResearchTask,
    ResearchStatus,
    ResearchFinding,
    AgentProgress,
    AgentStatus,
    ResearchFeedback,
    FeedbackType,
)


class ResearchStore(BaseStore):
    """Manages research tasks and findings."""

    table_name = "research_tasks"
    model_class = ResearchTask

    def __init__(self, db: Database):
        """Initialize research store.

        Args:
            db: Database instance
        """
        super().__init__(db)

    def _row_to_model(self, row) -> ResearchTask:
        """Convert database row to ResearchTask model.

        Args:
            row: Database row (psycopg Record or dict)

        Returns:
            ResearchTask instance
        """
        # Convert Row to dict if needed (psycopg Record is dict-like but needs explicit conversion)
        row_dict = dict(row) if hasattr(row, "keys") else row

        agent_results = {}
        agent_results_str = row_dict.get("agent_results")
        if agent_results_str:
            agent_results = json.loads(agent_results_str)

        return ResearchTask(
            id=row_dict["id"],
            topic=row_dict["topic"],
            status=row_dict["status"],
            project_id=row_dict["project_id"],
            created_at=row_dict["created_at"],
            started_at=row_dict["started_at"],
            completed_at=row_dict["completed_at"],
            findings_count=row_dict["findings_count"],
            entities_created=row_dict["entities_created"],
            relations_created=row_dict["relations_created"],
            notes=row_dict.get("notes") or "",
            agent_results=agent_results,
        )

    def create_task(self, topic: str, project_id: Optional[int] = None) -> int:
        """Create a new research task.

        Args:
            topic: Research topic
            project_id: Optional project ID

        Returns:
            Task ID
        """
        now = self.now_timestamp()
        return self.create(
            columns=["topic", "status", "created_at", "project_id"],
            values=(topic, ResearchStatus.PENDING.value, now, project_id),
        )

    def get_task(self, task_id: int) -> Optional[ResearchTask]:
        """Get a research task by ID.

        Args:
            task_id: Task ID

        Returns:
            ResearchTask or None
        """
        return self.get(task_id)

    def update_status(self, task_id: int, status: ResearchStatus) -> bool:
        """Update research task status.

        Args:
            task_id: Task ID
            status: New status

        Returns:
            Success
        """
        now = self.now_timestamp()
        updates = {"status": status.value}

        # If transitioning to running, set started_at
        if status == ResearchStatus.RUNNING:
            updates["started_at"] = now
        # If transitioning to completed/failed/cancelled, set completed_at
        elif status in [ResearchStatus.COMPLETED, ResearchStatus.FAILED, ResearchStatus.CANCELLED]:
            updates["completed_at"] = now

        return self.update(task_id, updates)

    def record_finding(self, finding: ResearchFinding) -> int:
        """Record a research finding.

        Args:
            finding: Finding to record

        Returns:
            Finding ID
        """
        return self.create(
            table_name="research_findings",
            columns=[
                "research_task_id",
                "source",
                "title",
                "summary",
                "url",
                "credibility_score",
                "created_at",
                "stored_to_memory",
                "memory_id",
            ],
            values=(
                finding.research_task_id,
                finding.source,
                finding.title,
                finding.summary,
                finding.url,
                finding.credibility_score,
                finding.created_at,
                finding.stored_to_memory,
                finding.memory_id,
            ),
        )

    def update_finding_memory_status(self, finding_id: int, memory_id: int) -> bool:
        """Mark finding as stored to memory.

        Args:
            finding_id: Finding ID
            memory_id: Memory ID where stored

        Returns:
            Success
        """
        return self.update(
            finding_id,
            {"stored_to_memory": 1, "memory_id": memory_id},
            table_name="research_findings",
        )

    def increment_task_stats(
        self, task_id: int, findings: int = 0, entities: int = 0, relations: int = 0
    ) -> bool:
        """Increment task statistics.

        Args:
            task_id: Task ID
            findings: Number of findings to add
            entities: Number of entities to add
            relations: Number of relations to add

        Returns:
            Success
        """
        query = """
            UPDATE research_tasks
            SET findings_count = findings_count + ?,
                entities_created = entities_created + ?,
                relations_created = relations_created + ?
            WHERE id = ?
        """
        cursor = self.execute(query, (findings, entities, relations, task_id))
        self.commit()
        return cursor.rowcount > 0

    def record_agent_progress(self, progress: AgentProgress) -> int:
        """Record progress for a research agent.

        Args:
            progress: Agent progress to record

        Returns:
            Progress record ID
        """
        # Handle status - it might be an enum or a string due to use_enum_values
        status_str = progress.status if isinstance(progress.status, str) else progress.status.value

        return self.create(
            table_name="agent_progress",
            columns=[
                "research_task_id",
                "agent_name",
                "status",
                "findings_count",
                "started_at",
                "completed_at",
                "error_message",
            ],
            values=(
                progress.research_task_id,
                progress.agent_name,
                status_str,
                progress.findings_count,
                progress.started_at,
                progress.completed_at,
                progress.error_message,
            ),
        )

    def update_agent_progress(
        self, research_task_id: int, agent_name: str, status: AgentStatus, findings_count: int = 0
    ) -> bool:
        """Update agent progress status.

        Args:
            research_task_id: Research task ID
            agent_name: Agent name
            status: New status
            findings_count: Number of findings found

        Returns:
            Success
        """
        # Handle status - might be enum or string
        status_str = status if isinstance(status, str) else status.value
        status_enum = AgentStatus(status_str) if isinstance(status, str) else status
        now = self.now_timestamp()

        query = "UPDATE agent_progress SET status = ?"
        params = [status_str]

        if status_enum == AgentStatus.RUNNING:
            query += ", started_at = ?"
            params.append(now)
        elif status_enum in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.SKIPPED]:
            query += ", completed_at = ?, findings_count = ?"
            params.extend([now, findings_count])

        query += " WHERE research_task_id = ? AND agent_name = ?"
        params.extend([research_task_id, agent_name])

        cursor = self.execute(query, tuple(params))
        self.commit()
        return cursor.rowcount > 0

    def get_task_findings(self, task_id: int, limit: int = 100) -> list[ResearchFinding]:
        """Get findings for a research task.

        Args:
            task_id: Task ID
            limit: Maximum number of findings

        Returns:
            List of findings
        """
        query = """
            SELECT id, research_task_id, source, title, summary, url, credibility_score,
                   created_at, stored_to_memory, memory_id
            FROM research_findings
            WHERE research_task_id = ?
            ORDER BY credibility_score DESC
            LIMIT ?
        """
        rows = self.execute(query, (task_id, limit), fetch_all=True)

        findings = []
        for row in rows:
            findings.append(
                ResearchFinding(
                    id=row[0],
                    research_task_id=row[1],
                    source=row[2],
                    title=row[3],
                    summary=row[4],
                    url=row[5],
                    credibility_score=row[6],
                    created_at=row[7],
                    stored_to_memory=bool(row[8]),
                    memory_id=row[9],
                )
            )

        return findings

    def get_agent_progress(self, task_id: int) -> list[AgentProgress]:
        """Get progress for all agents on a task.

        Args:
            task_id: Task ID

        Returns:
            List of agent progress records
        """
        query = """
            SELECT id, research_task_id, agent_name, status, findings_count, started_at, completed_at, error_message
            FROM agent_progress
            WHERE research_task_id = ?
        """
        rows = self.execute(query, (task_id,), fetch_all=True)

        progress_list = []
        for row in rows:
            progress_list.append(
                AgentProgress(
                    id=row[0],
                    research_task_id=row[1],
                    agent_name=row[2],
                    status=row[3],
                    findings_count=row[4],
                    started_at=row[5],
                    completed_at=row[6],
                    error_message=row[7],
                )
            )

        return progress_list

    def list_tasks(
        self, status: Optional[ResearchStatus] = None, limit: int = 50
    ) -> list[ResearchTask]:
        """List research tasks.

        Args:
            status: Filter by status
            limit: Maximum number of tasks

        Returns:
            List of tasks
        """
        query = """
            SELECT id, topic, status, project_id, created_at, started_at, completed_at,
                   findings_count, entities_created, relations_created, notes, agent_results
            FROM research_tasks
        """
        params = []

        if status:
            query += " WHERE status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.execute(query, tuple(params), fetch_all=True)

        tasks = []
        for row in rows:
            agent_results = {}
            if row[11]:
                agent_results = json.loads(row[11])

            tasks.append(
                ResearchTask(
                    id=row[0],
                    topic=row[1],
                    status=row[2],
                    project_id=row[3],
                    created_at=row[4],
                    started_at=row[5],
                    completed_at=row[6],
                    findings_count=row[7],
                    entities_created=row[8],
                    relations_created=row[9],
                    notes=row[10] or "",
                    agent_results=agent_results,
                )
            )

        return tasks


class ResearchFeedbackStore(BaseStore):
    """Manages research feedback for task refinement (Phase 3.2)."""

    table_name = "research_feedback"
    model_class = ResearchFeedback

    def __init__(self, db: Database):
        """Initialize feedback store.

        Args:
            db: Database instance
        """
        super().__init__(db)

    def _row_to_model(self, row) -> ResearchFeedback:
        """Convert database row to ResearchFeedback model."""
        row_dict = dict(row) if hasattr(row, "keys") else row

        return ResearchFeedback(
            id=row_dict["id"],
            research_task_id=row_dict["research_task_id"],
            feedback_type=row_dict["feedback_type"],
            content=row_dict["content"],
            agent_target=row_dict.get("agent_target"),
            created_at=row_dict["created_at"],
            parent_feedback_id=row_dict.get("parent_feedback_id"),
            applied=bool(row_dict.get("applied", False)),
            applied_at=row_dict.get("applied_at"),
        )

    def record_feedback(self, feedback: ResearchFeedback) -> int:
        """Record user feedback for a research task.

        Args:
            feedback: Feedback to record

        Returns:
            Feedback ID
        """
        now = self.now_timestamp()
        return self.create(
            columns=[
                "research_task_id",
                "feedback_type",
                "content",
                "agent_target",
                "created_at",
                "parent_feedback_id",
            ],
            values=(
                feedback.research_task_id,
                (
                    feedback.feedback_type
                    if isinstance(feedback.feedback_type, str)
                    else feedback.feedback_type.value
                ),
                feedback.content,
                feedback.agent_target,
                now,
                feedback.parent_feedback_id,
            ),
        )

    def get_task_feedback(self, task_id: int, limit: int = 100) -> list[ResearchFeedback]:
        """Get all feedback for a research task.

        Args:
            task_id: Research task ID
            limit: Maximum feedback items to return

        Returns:
            List of feedback items
        """
        query = """
            SELECT id, research_task_id, feedback_type, content, agent_target,
                   created_at, parent_feedback_id, applied, applied_at
            FROM research_feedback
            WHERE research_task_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        rows = self.db.execute_sync(query, (task_id, limit))

        feedback_list = []
        for row in rows:
            feedback_list.append(
                ResearchFeedback(
                    id=row[0],
                    research_task_id=row[1],
                    feedback_type=row[2],
                    content=row[3],
                    agent_target=row[4],
                    created_at=row[5],
                    parent_feedback_id=row[6],
                    applied=bool(row[7]),
                    applied_at=row[8],
                )
            )

        return feedback_list

    def get_unapplied_feedback(self, task_id: int) -> list[ResearchFeedback]:
        """Get unapplied feedback for a research task.

        Args:
            task_id: Research task ID

        Returns:
            List of unapplied feedback items
        """
        query = """
            SELECT id, research_task_id, feedback_type, content, agent_target,
                   created_at, parent_feedback_id, applied, applied_at
            FROM research_feedback
            WHERE research_task_id = %s AND applied = FALSE
            ORDER BY created_at ASC
        """
        rows = self.db.execute_sync(query, (task_id,))

        feedback_list = []
        for row in rows:
            feedback_list.append(
                ResearchFeedback(
                    id=row[0],
                    research_task_id=row[1],
                    feedback_type=row[2],
                    content=row[3],
                    agent_target=row[4],
                    created_at=row[5],
                    parent_feedback_id=row[6],
                    applied=bool(row[7]),
                    applied_at=row[8],
                )
            )

        return feedback_list

    def mark_feedback_applied(self, feedback_id: int) -> bool:
        """Mark feedback as applied.

        Args:
            feedback_id: Feedback ID

        Returns:
            Success
        """
        now = self.now_timestamp()
        query = """
            UPDATE research_feedback
            SET applied = TRUE, applied_at = %s
            WHERE id = %s
        """
        self.db.execute_sync(query, (now, feedback_id))
        return True

    def get_feedback_by_type(
        self, task_id: int, feedback_type: FeedbackType
    ) -> list[ResearchFeedback]:
        """Get feedback of a specific type for a task.

        Args:
            task_id: Research task ID
            feedback_type: Type of feedback to retrieve

        Returns:
            List of matching feedback items
        """
        feedback_type_str = feedback_type if isinstance(feedback_type, str) else feedback_type.value
        query = """
            SELECT id, research_task_id, feedback_type, content, agent_target,
                   created_at, parent_feedback_id, applied, applied_at
            FROM research_feedback
            WHERE research_task_id = %s AND feedback_type = %s
            ORDER BY created_at DESC
        """
        rows = self.db.execute_sync(query, (task_id, feedback_type_str))

        feedback_list = []
        for row in rows:
            feedback_list.append(
                ResearchFeedback(
                    id=row[0],
                    research_task_id=row[1],
                    feedback_type=row[2],
                    content=row[3],
                    agent_target=row[4],
                    created_at=row[5],
                    parent_feedback_id=row[6],
                    applied=bool(row[7]),
                    applied_at=row[8],
                )
            )

        return feedback_list

    def get_feedback_by_agent(self, task_id: int, agent_name: str) -> list[ResearchFeedback]:
        """Get feedback targeting a specific agent.

        Args:
            task_id: Research task ID
            agent_name: Target agent name

        Returns:
            List of feedback items for agent
        """
        query = """
            SELECT id, research_task_id, feedback_type, content, agent_target,
                   created_at, parent_feedback_id, applied, applied_at
            FROM research_feedback
            WHERE research_task_id = %s AND agent_target = %s
            ORDER BY created_at DESC
        """
        rows = self.db.execute_sync(query, (task_id, agent_name))

        feedback_list = []
        for row in rows:
            feedback_list.append(
                ResearchFeedback(
                    id=row[0],
                    research_task_id=row[1],
                    feedback_type=row[2],
                    content=row[3],
                    agent_target=row[4],
                    created_at=row[5],
                    parent_feedback_id=row[6],
                    applied=bool(row[7]),
                    applied_at=row[8],
                )
            )

        return feedback_list
