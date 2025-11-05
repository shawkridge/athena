"""Task-memory consolidation: Extract learnings from completed tasks.

When tasks complete, consolidate outcomes into:
- Semantic memory (learnings and insights)
- Procedural memory (reusable procedures)
- Knowledge graph (entity linking)
- Pattern extraction (for workflow optimization)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database
from ..episodic.models import EpisodicEvent, EventContext, EventOutcome, EventType
from ..episodic.store import EpisodicStore
from ..memory.store import MemoryStore
from ..procedural.store import ProceduralStore
from ..procedural.models import Procedure, ProcedureCategory
from ..graph.store import GraphStore
from ..graph.models import Entity
from ..prospective.models import ProspectiveTask, TaskPhase, TaskStatus
from ..prospective.store import ProspectiveStore

logger = logging.getLogger(__name__)


class TaskConsolidation:
    """Consolidate completed tasks into learnings and procedures.

    Responsibilities:
    - Extract task outcomes and learnings
    - Create semantic memories from task execution
    - Extract reusable procedures
    - Link to knowledge graph
    - Update task patterns
    """

    def __init__(self, db: Database):
        """Initialize task consolidation.

        Args:
            db: Database instance
        """
        self.db = db
        self.prospective_store = ProspectiveStore(db)
        self.episodic_store = EpisodicStore(db)
        self.semantic_store = MemoryStore(db.db_path)
        self.procedure_store = ProceduralStore(db)
        self.graph_store = GraphStore(db)

    async def consolidate_completed_task(self, task_id: int) -> dict:
        """Consolidate a completed task into learnings and procedures.

        Args:
            task_id: Task ID to consolidate

        Returns:
            Dict with consolidation results
        """
        result = {
            "task_id": task_id,
            "status": "pending",
            "semantic_memories_created": 0,
            "procedures_extracted": 0,
            "entities_linked": 0,
            "lessons_learned": [],
        }

        try:
            # Get task
            task = self.prospective_store.get_task(task_id)
            if not task:
                result["status"] = "error"
                result["error"] = "Task not found"
                return result

            # Verify task is completed
            if task.status != TaskStatus.COMPLETED and task.phase != TaskPhase.COMPLETED:
                result["status"] = "skipped"
                result["reason"] = f"Task status {task.status}, phase {task.phase} (not completed)"
                return result

            # 1. Gather task execution events
            events = await self._gather_task_events(task_id)
            logger.info(f"Consolidating task {task_id}: {len(events)} events gathered")

            # 2. Create semantic memory (learning summary)
            semantic_count = await self._create_semantic_memories(task, events)
            result["semantic_memories_created"] = semantic_count

            # 3. Extract procedures from task execution
            procedure_count = await self._extract_procedures(task, events)
            result["procedures_extracted"] = procedure_count

            # 4. Link to knowledge graph
            entity_count = await self._link_knowledge_graph(task)
            result["entities_linked"] = entity_count

            # 5. Extract lessons learned
            lessons = await self._extract_lessons_learned(task, events)
            result["lessons_learned"] = lessons
            task.lessons_learned = "; ".join(lessons) if lessons else None

            # 6. Record consolidation event
            await self._record_consolidation_event(task, result)

            result["status"] = "success"
            logger.info(
                f"Task {task_id} consolidated: "
                f"{semantic_count} semantic, {procedure_count} procedures, {entity_count} entities"
            )

        except Exception as e:
            logger.error(f"Error consolidating task {task_id}: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _gather_task_events(self, task_id: int) -> list[dict]:
        """Gather all episodic events related to task execution.

        Args:
            task_id: Task ID

        Returns:
            List of events related to this task
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT * FROM episodic_events
                WHERE project_id = ? OR context LIKE ?
                ORDER BY timestamp
            """,
                (task_id, f"%Task {task_id}%"),
            )

            events = cursor.fetchall()
            return [dict(event) for event in events] if events else []

        except Exception as e:
            logger.error(f"Error gathering task events: {e}")
            return []

    async def _create_semantic_memories(
        self, task: ProspectiveTask, events: list[dict]
    ) -> int:
        """Create semantic memories from task execution.

        Args:
            task: Completed task
            events: Task execution events

        Returns:
            Number of semantic memories created
        """
        count = 0

        try:
            # Create high-level summary
            summary = f"Completed: {task.content}"

            if task.actual_duration_minutes:
                summary += f" (took {task.actual_duration_minutes:.1f} minutes)"

            if task.plan and task.plan.steps:
                summary += f" with {len(task.plan.steps)} execution steps"

            # Store as semantic memory
            if self.semantic_store:
                memory_id = self.semantic_store.remember(
                    content=summary,
                    memory_type="fact",
                    project_id=task.project_id,
                    tags=["task_completion", "execution_summary"],
                )
                count += 1
                logger.info(f"Created semantic memory {memory_id} for task {task.id}")

            # Create learning from phase metrics
            if task.phase_metrics:
                for metric in task.phase_metrics:
                    phase_name = metric.phase.value if hasattr(metric.phase, "value") else metric.phase
                    if metric.duration_minutes:
                        learning = f"Phase '{phase_name}' took {metric.duration_minutes:.1f} minutes"
                        if self.semantic_store:
                            self.semantic_store.remember(
                                content=learning,
                                memory_type="fact",
                                project_id=task.project_id,
                                tags=["phase_timing", "task_metrics", phase_name.lower()],
                            )
                            count += 1

        except Exception as e:
            logger.error(f"Error creating semantic memories: {e}")

        return count

    async def _extract_procedures(
        self, task: ProspectiveTask, events: list[dict]
    ) -> int:
        """Extract reusable procedures from task execution.

        Args:
            task: Completed task
            events: Task execution events

        Returns:
            Number of procedures extracted
        """
        count = 0

        try:
            # If task has a plan, extract as procedure template
            if task.plan and task.plan.steps:
                # Create procedure from successful execution
                if self.procedure_store and task.status == TaskStatus.COMPLETED:
                    # Extract first 3 words for category
                    words = task.content.split()[:3]
                    category_name = " ".join(words).lower()[:30]

                    procedure_template = "\n".join(
                        f"{i}. {step}" for i, step in enumerate(task.plan.steps, 1)
                    )

                    try:
                        procedure = Procedure(
                            name=f"{category_name}_procedure",
                            category=ProcedureCategory.GENERAL,
                            template=procedure_template,
                            trigger_pattern=task.content[:50],
                            created_by="learned",
                        )
                        self.procedure_store.create_procedure(procedure)
                        count += 1
                        logger.info(
                            f"Extracted procedure template for task {task.id}"
                        )
                    except Exception as e:
                        logger.warning(f"Could not save procedure: {e}")

        except Exception as e:
            logger.error(f"Error extracting procedures: {e}")

        return count

    async def _link_knowledge_graph(self, task: ProspectiveTask) -> int:
        """Link task to knowledge graph entities.

        Args:
            task: Completed task

        Returns:
            Number of entities linked
        """
        count = 0

        try:
            # Create task entity if needed
            if self.graph_store:
                # Create task as entity
                task_entity = Entity(
                    name=f"Task_{task.id}",
                    entity_type="Task",
                    project_id=task.project_id,
                )
                task_entity_id = self.graph_store.create_entity(task_entity)

                # Create entities from task content keywords
                if "api" in task.content.lower():
                    api_entity = Entity(
                        name="API",
                        entity_type="Concept",
                        project_id=task.project_id,
                    )
                    self.graph_store.create_entity(api_entity)
                    count += 1

                if "database" in task.content.lower() or "data" in task.content.lower():
                    db_entity = Entity(
                        name="Database",
                        entity_type="Concept",
                        project_id=task.project_id,
                    )
                    self.graph_store.create_entity(db_entity)
                    count += 1

                if "test" in task.content.lower():
                    test_entity = Entity(
                        name="Testing",
                        entity_type="Concept",
                        project_id=task.project_id,
                    )
                    self.graph_store.create_entity(test_entity)
                    count += 1

                # Link phase entity
                phase_name = task.phase.value if hasattr(task.phase, "value") else str(task.phase)
                phase_entity = Entity(
                    name=f"Phase_{phase_name}",
                    entity_type="Phase",
                    project_id=task.project_id,
                )
                self.graph_store.create_entity(phase_entity)
                count += 1

                logger.info(f"Linked {count} entities for task {task.id}")

        except Exception as e:
            logger.error(f"Error linking knowledge graph: {e}")

        return count

    async def _extract_lessons_learned(
        self, task: ProspectiveTask, events: list[dict]
    ) -> list[str]:
        """Extract lessons learned from task execution.

        Args:
            task: Completed task
            events: Task execution events

        Returns:
            List of lessons learned
        """
        lessons = []

        try:
            # Lesson 1: Duration accuracy
            if task.plan and task.actual_duration_minutes:
                estimate = task.plan.estimated_duration_minutes
                actual = task.actual_duration_minutes
                variance = ((actual - estimate) / estimate) * 100

                if variance > 20:
                    lessons.append(
                        f"Duration estimates need adjustment (+{variance:.0f}%)"
                    )
                elif variance < -20:
                    lessons.append(
                        f"Can complete similar tasks {abs(variance):.0f}% faster"
                    )
                else:
                    lessons.append("Duration estimation was accurate")

            # Lesson 2: Phase efficiency
            if task.phase_metrics and len(task.phase_metrics) > 1:
                longest_phase = max(
                    task.phase_metrics,
                    key=lambda m: m.duration_minutes or 0,
                )
                if longest_phase.duration_minutes:
                    phase_name = (
                        longest_phase.phase.value
                        if hasattr(longest_phase.phase, "value")
                        else longest_phase.phase
                    )
                    lessons.append(
                        f"'{phase_name}' phase took longest "
                        f"({longest_phase.duration_minutes:.1f} min)"
                    )

            # Lesson 3: Completion pattern
            if task.status == TaskStatus.COMPLETED:
                lessons.append("Task successfully completed with all phases")

            # Lesson 4: Errors encountered
            error_count = len([e for e in events if e.get("event_type") == "error"])
            if error_count > 0:
                lessons.append(f"Encountered {error_count} errors during execution")

        except Exception as e:
            logger.error(f"Error extracting lessons: {e}")

        return lessons

    async def _record_consolidation_event(
        self, task: ProspectiveTask, result: dict
    ) -> None:
        """Record consolidation as episodic event.

        Args:
            task: Consolidated task
            result: Consolidation result
        """
        try:
            event = EpisodicEvent(
                project_id=task.project_id,
                session_id="task-consolidation",
                event_type=EventType.DECISION,
                content=f"Task consolidated: {task.content}",
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    task=f"Task {task.id}: {task.content}",
                    phase="consolidation",
                ),
            )

            event.notes = (
                f"Semantic: {result['semantic_memories_created']}, "
                f"Procedures: {result['procedures_extracted']}, "
                f"Entities: {result['entities_linked']}"
            )

            self.episodic_store.record_event(event)

        except Exception as e:
            logger.error(f"Error recording consolidation event: {e}")

    async def consolidate_all_recent_completed_tasks(
        self, hours_back: int = 24
    ) -> dict:
        """Consolidate all recently completed tasks.

        Args:
            hours_back: How far back to look for completed tasks

        Returns:
            Summary of all consolidations
        """
        summary = {
            "tasks_consolidated": 0,
            "total_semantic_memories": 0,
            "total_procedures": 0,
            "total_entities": 0,
            "results": [],
        }

        try:
            # Get recently completed tasks
            cutoff_time = datetime.now() - timedelta(hours=hours_back)

            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT * FROM prospective_tasks
                WHERE status = 'completed' AND completed_at > ?
                ORDER BY completed_at DESC
            """,
                (int(cutoff_time.timestamp()),),
            )

            tasks = cursor.fetchall()

            for task_row in tasks:
                # Convert row to dict if needed
                task_dict = dict(task_row) if hasattr(task_row, "keys") else task_row

                result = await self.consolidate_completed_task(task_dict.get("id"))
                summary["results"].append(result)

                if result["status"] == "success":
                    summary["tasks_consolidated"] += 1
                    summary["total_semantic_memories"] += result[
                        "semantic_memories_created"
                    ]
                    summary["total_procedures"] += result["procedures_extracted"]
                    summary["total_entities"] += result["entities_linked"]

        except Exception as e:
            logger.error(f"Error consolidating recent tasks: {e}")

        return summary
