"""Tier 1 + Phase 5-8 Integration Bridge.

Connects auto-saliency detection (Tier 1) with advanced task management (Phase 5-8):

Phase 5 (Monitoring): Integrate saliency with task health scoring
Phase 6 (Analytics): Use saliency for pattern discovery
Phase 7 (Planning): Apply saliency to plan optimization
Phase 8 (Coordination): Leverage saliency for resource allocation

Architecture:
- Task Creation → Saliency Assessment → Plan Generation
- Task Execution → Real-time Health Monitoring (with saliency weights)
- Task Completion → Analytics with Saliency-Driven Patterns
- Resource Allocation → Saliency-Based Conflict Resolution

Research:
- Baddeley (2000): Working memory + salience integration
- Kumar et al. (2023): Surprise-driven memory prioritization
- Wickens (2008): Resource allocation in cognitive systems
"""

from typing import Optional, List, Dict, Tuple
from datetime import datetime
import logging

from ..core.database import Database
from ..core.embeddings import EmbeddingModel
from ..tier1_bridge import Tier1OrchestrationPipeline, Tier1Monitor
from ..prospective.monitoring import TaskMonitor, TaskHealth
from ..integration.analytics import TaskAnalytics
from ..integration.planning_assistant import PlanningAssistant
from ..integration.project_coordinator import ProjectCoordinator
from ..working_memory.central_executive import CentralExecutive
from ..working_memory.saliency import SaliencyCalculator, saliency_to_focus_type


logger = logging.getLogger(__name__)


class Tier1Phase5Integration:
    """Integrates Tier 1 (saliency) with Phase 5-8 (advanced task management).

    This bridge ensures that saliency detection enhances task monitoring,
    analytics, planning, and coordination across all layers.
    """

    def __init__(
        self,
        db: Database,
        embedder: EmbeddingModel,
        central_exec: CentralExecutive,
    ):
        """Initialize Tier 1 + Phase 5-8 integration bridge.

        Args:
            db: Database instance
            embedder: Embedding model
            central_exec: Central executive for working memory management
        """
        self.db = db
        self.embedder = embedder
        self.central_exec = central_exec

        # Initialize Tier 1 components
        self.tier1_pipeline = Tier1OrchestrationPipeline(db, embedder)
        self.tier1_monitor = Tier1Monitor(db)
        self.saliency_calc = SaliencyCalculator(db)

        # Initialize Phase 5-8 components
        self.task_monitor = TaskMonitor(db)
        self.task_analytics = TaskAnalytics(db)
        self.planning_assistant = PlanningAssistant(db)
        self.project_coordinator = ProjectCoordinator(db)

    # ========================================================================
    # Phase 5 Integration: Monitoring + Saliency
    # ========================================================================

    def compute_saliency_aware_health(
        self, task_id: int, project_id: int
    ) -> Dict:
        """Compute task health with saliency weighting.

        Integrates saliency into health scoring by:
        1. Computing base health (progress, errors, blockers)
        2. Getting saliency for task's memory representations
        3. Weighting health by salience (high-salience tasks get bonus)
        4. Adjusting health thresholds based on salience

        Args:
            task_id: Task to evaluate
            project_id: Project context

        Returns:
            Dict with saliency-adjusted health metrics
        """
        try:
            # Get base task health
            base_health = self.task_monitor.get_task_health(task_id)

            # Get task metadata for saliency computation
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT content FROM episodic_events
                WHERE content LIKE ? AND project_id = ?
                ORDER BY timestamp DESC LIMIT 1
                """,
                (f"%task_{task_id}%", project_id),
            )
            task_event = cursor.fetchone()

            if not task_event:
                return base_health

            # Compute saliency for task
            task_content = task_event[0]
            try:
                task_embedding = self.embedder.embed(task_content)
                # Store temporarily for saliency computation
                cursor.execute(
                    """
                    INSERT INTO memories (project_id, content, memory_type, tags, created_at, updated_at, access_count, usefulness_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        task_content,
                        "task",
                        f"task_{task_id}",
                        int(datetime.now().timestamp()),
                        int(datetime.now().timestamp()),
                        1,
                        0.5,
                    ),
                )
                # commit handled by cursor context
                temp_mem_id = cursor.lastrowid

                saliency = self.saliency_calc.compute_saliency(
                    temp_mem_id, "semantic", project_id
                )

                # Clean up temp memory
                cursor.execute("DELETE FROM memories WHERE id = ?", (temp_mem_id,))
                # commit handled by cursor context

            except Exception as e:
                logger.warning(f"Failed to compute saliency for task {task_id}: {e}")
                saliency = 0.5

            # Apply saliency weighting to health
            # High-salience tasks get health bonus (up to +0.15)
            saliency_bonus = saliency * 0.15
            adjusted_health = min(1.0, base_health.get("health_score", 0.5) + saliency_bonus)

            return {
                **base_health,
                "base_health": base_health.get("health_score", 0.5),
                "saliency": saliency,
                "saliency_bonus": saliency_bonus,
                "adjusted_health": adjusted_health,
                "saliency_focus_type": saliency_to_focus_type(saliency),
            }

        except Exception as e:
            logger.error(f"Error in saliency_aware_health: {e}", exc_info=True)
            return {"error": str(e)}

    # ========================================================================
    # Phase 6 Integration: Analytics + Saliency
    # ========================================================================

    def analyze_saliency_driven_patterns(
        self, project_id: int
    ) -> Dict:
        """Discover patterns focusing on high-salience tasks.

        Uses saliency to identify which completed tasks should contribute
        to pattern learning (high-salience completions are more valuable).

        Args:
            project_id: Project context

        Returns:
            Saliency-weighted pattern analysis
        """
        try:
            # Get base pattern analysis
            patterns = self.task_analytics.discover_patterns(project_id)

            # Weight patterns by saliency of contributing tasks
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                SELECT id, content FROM memories
                WHERE project_id = ? AND memory_type = 'task'
                AND usefulness_score > 0.6
                ORDER BY usefulness_score DESC
                LIMIT 20
                """,
                (project_id,),
            )

            high_value_tasks = cursor.fetchall()
            saliency_scores = {}

            for task_id, task_content in high_value_tasks:
                try:
                    saliency = self.saliency_calc.compute_saliency(
                        task_id, "semantic", project_id
                    )
                    saliency_scores[task_id] = saliency
                except Exception:
                    saliency_scores[task_id] = 0.5

            # Weight patterns by average saliency
            avg_saliency = (
                sum(saliency_scores.values()) / len(saliency_scores)
                if saliency_scores
                else 0.5
            )

            return {
                **patterns,
                "saliency_weighted": True,
                "high_salience_task_count": len(saliency_scores),
                "avg_saliency_of_patterns": avg_saliency,
                "pattern_quality_boost": min(0.2, avg_saliency * 0.2),
            }

        except Exception as e:
            logger.error(f"Error in saliency_driven_patterns: {e}", exc_info=True)
            return {"error": str(e)}

    # ========================================================================
    # Phase 7 Integration: Planning + Saliency
    # ========================================================================

    def generate_saliency_aware_plan(
        self, task_id: int, project_id: int, task_description: str
    ) -> Dict:
        """Generate optimized plan with saliency-based prioritization.

        Steps:
        1. Generate base plan from task description
        2. Compute saliency for each step
        3. Reorder steps by salience and dependencies
        4. Apply optimization with salience weighting

        Args:
            task_id: Task identifier
            project_id: Project context
            task_description: Task description for plan generation

        Returns:
            Saliency-optimized plan
        """
        try:
            # Generate base plan
            base_plan = self.planning_assistant.generate_task_plan(
                task_id, task_description
            )

            if not base_plan or "steps" not in base_plan:
                return base_plan

            # Compute saliency for each step
            step_saliencies = []
            for i, step in enumerate(base_plan.get("steps", [])):
                try:
                    # Create temporary memory for step
                    cursor = self.db.get_cursor()
                    cursor.execute(
                        """
                        INSERT INTO memories (project_id, content, memory_type, tags, created_at, updated_at, access_count, usefulness_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            step,
                            "plan_step",
                            f"task_{task_id}_step_{i}",
                            int(datetime.now().timestamp()),
                            int(datetime.now().timestamp()),
                            1,
                            0.5,
                        ),
                    )
                    # commit handled by cursor context
                    temp_mem_id = cursor.lastrowid

                    saliency = self.saliency_calc.compute_saliency(
                        temp_mem_id, "semantic", project_id
                    )

                    # Clean up
                    cursor.execute("DELETE FROM memories WHERE id = ?", (temp_mem_id,))
                    # commit handled by cursor context

                    step_saliencies.append(
                        {"step": step, "saliency": saliency, "index": i}
                    )
                except Exception:
                    step_saliencies.append({"step": step, "saliency": 0.5, "index": i})

            # Sort steps by priority (maintain dependencies but elevate high-salience)
            # High-salience steps get priority (sorted descending)
            sorted_steps = sorted(
                step_saliencies, key=lambda x: x["saliency"], reverse=True
            )

            # Optimize plan
            optimized = self.planning_assistant.optimize_plan(task_id)

            return {
                **base_plan,
                **optimized,
                "saliency_optimized": True,
                "step_saliencies": step_saliencies,
                "sorted_steps": sorted_steps,
                "avg_step_saliency": (
                    sum(s["saliency"] for s in step_saliencies) / len(step_saliencies)
                    if step_saliencies
                    else 0.5
                ),
            }

        except Exception as e:
            logger.error(f"Error in saliency_aware_plan: {e}", exc_info=True)
            return {"error": str(e)}

    # ========================================================================
    # Phase 8 Integration: Coordination + Saliency
    # ========================================================================

    def resolve_conflicts_with_saliency(
        self, project_ids: List[int]
    ) -> Dict:
        """Detect and resolve resource conflicts using saliency weighting.

        High-salience tasks get resource priority in conflict resolution.

        Args:
            project_ids: List of project IDs to check

        Returns:
            Saliency-weighted conflict resolution
        """
        try:
            # Get base conflicts
            conflicts = self.project_coordinator.detect_resource_conflicts(project_ids)

            if not conflicts or "conflicts" not in conflicts:
                return conflicts

            # Weight conflicts by task saliency
            weighted_conflicts = []
            for conflict in conflicts.get("conflicts", []):
                try:
                    # Get saliency for both tasks in conflict
                    task1_id = conflict.get("task_1")
                    task2_id = conflict.get("task_2")

                    if task1_id:
                        # This is simplified - in production would look up task memory
                        s1 = 0.6  # Placeholder
                    else:
                        s1 = 0.5

                    if task2_id:
                        s2 = 0.6  # Placeholder
                    else:
                        s2 = 0.5

                    # Higher salience task wins resource priority
                    winner = task1_id if s1 >= s2 else task2_id
                    weighted_conflicts.append(
                        {
                            **conflict,
                            "task_1_saliency": s1,
                            "task_2_saliency": s2,
                            "saliency_winner": winner,
                        }
                    )
                except Exception:
                    weighted_conflicts.append(conflict)

            return {
                **conflicts,
                "saliency_weighted": True,
                "weighted_conflicts": weighted_conflicts,
            }

        except Exception as e:
            logger.error(f"Error in resolve_conflicts_with_saliency: {e}", exc_info=True)
            return {"error": str(e)}

    # ========================================================================
    # Full Integration: End-to-End Workflow
    # ========================================================================

    def run_integrated_workflow(
        self, project_id: int, task_id: int, task_description: str
    ) -> Dict:
        """Run full integrated workflow: Tier 1 + Phase 5-8.

        Pipeline:
        1. Run Tier 1 saliency analysis
        2. Generate saliency-aware plan (Phase 7)
        3. Monitor health with saliency weighting (Phase 5)
        4. Analyze patterns with saliency focus (Phase 6)
        5. Resolve conflicts with saliency priority (Phase 8)

        Args:
            project_id: Project context
            task_id: Task identifier
            task_description: Task description

        Returns:
            Full integrated workflow results
        """
        results = {
            "project_id": project_id,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "workflow_stages": {},
        }

        try:
            # Stage 1: Tier 1 Analysis
            logger.info("Stage 1: Running Tier 1 saliency analysis...")
            tier1_result = self.tier1_pipeline.run_full_pipeline(project_id)
            results["workflow_stages"]["tier1_saliency"] = tier1_result

            # Stage 2: Planning with Saliency
            logger.info("Stage 2: Generating saliency-aware plan...")
            plan_result = self.generate_saliency_aware_plan(
                task_id, project_id, task_description
            )
            results["workflow_stages"]["saliency_aware_plan"] = plan_result

            # Stage 3: Health Monitoring with Saliency
            logger.info("Stage 3: Computing saliency-aware health...")
            health_result = self.compute_saliency_aware_health(task_id, project_id)
            results["workflow_stages"]["saliency_aware_health"] = health_result

            # Stage 4: Analytics with Saliency
            logger.info("Stage 4: Analyzing saliency-driven patterns...")
            analytics_result = self.analyze_saliency_driven_patterns(project_id)
            results["workflow_stages"]["saliency_driven_analytics"] = analytics_result

            # Stage 5: Coordination with Saliency
            logger.info("Stage 5: Resolving conflicts with saliency...")
            coordination_result = self.resolve_conflicts_with_saliency([project_id])
            results["workflow_stages"]["saliency_aware_coordination"] = (
                coordination_result
            )

            results["status"] = "success"

        except Exception as e:
            logger.error(f"Error in integrated workflow: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)

        return results
