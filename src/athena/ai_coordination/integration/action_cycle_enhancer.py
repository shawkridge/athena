"""Action cycle enhancement with recalled knowledge.

Improves ActionCycle planning by:
- Injecting recalled procedures into plan steps
- Using semantic patterns to guide planning
- Adjusting based on prior success rates
- Learning from reuse results

This closes the learning loop: Past Execution → Pattern → Better Planning
"""

import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.database import Database


class PlanEnhancement:
    """Enhancement suggested for a plan."""

    def __init__(
        self,
        step_number: int,
        enhancement_type: str,  # procedure_suggestion, pattern_match, code_reference
        description: str,
        confidence: float,
        source_id: int,
        source_type: str
    ):
        """Initialize plan enhancement.

        Args:
            step_number: Which plan step to enhance
            enhancement_type: Type of enhancement
            description: Human-readable description
            confidence: Confidence in enhancement (0.0-1.0)
            source_id: ID of source (procedure, pattern, etc)
            source_type: Type of source
        """
        self.step_number = step_number
        self.enhancement_type = enhancement_type
        self.description = description
        self.confidence = min(confidence, 1.0)
        self.source_id = source_id
        self.source_type = source_type


class ActionCycleEnhancer:
    """Enhances ActionCycle planning with recalled knowledge.

    Purpose:
    - Analyze action cycle plans
    - Inject procedures from Memory-MCP
    - Suggest patterns that worked before
    - Adjust based on prior success rates
    - Track learning from reuse

    This enables improvement over time:
    Plan V1 → Execute → Learn → Plan V2 (improved)
    """

    def __init__(self, db: "Database"):
        """Initialize ActionCycleEnhancer.

        Args:
            db: Database connection
        """
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self):
        """Create action cycle enhancement tables."""
        cursor = self.db.get_cursor()

        # Table: Plan enhancements applied
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plan_enhancements (
                id INTEGER PRIMARY KEY,
                cycle_id TEXT NOT NULL,
                goal_id TEXT NOT NULL,
                enhancement_type TEXT NOT NULL,
                step_number INTEGER,
                description TEXT,
                source_id INTEGER,
                source_type TEXT,
                confidence REAL,
                applied BOOLEAN DEFAULT 0,
                effectiveness REAL,
                created_at INTEGER NOT NULL
            )
        """)

        # Table: Enhancement feedback
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enhancement_feedback (
                id INTEGER PRIMARY KEY,
                enhancement_id INTEGER NOT NULL,
                outcome TEXT,  -- helped, neutral, hindered
                feedback_text TEXT,
                recorded_at INTEGER NOT NULL,
                FOREIGN KEY (enhancement_id) REFERENCES plan_enhancements(id)
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_plan_enhancements_cycle
            ON plan_enhancements(cycle_id, goal_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_enhancement_feedback_outcome
            ON enhancement_feedback(outcome)
        """)

        # commit handled by cursor context

    def analyze_plan(
        self,
        cycle_id: str,
        goal_description: str,
        plan_steps: list[str]
    ) -> dict:
        """Analyze a plan and suggest enhancements.

        Args:
            cycle_id: ActionCycle ID
            goal_description: Description of goal
            plan_steps: List of planned steps

        Returns:
            Dict with suggested enhancements
        """
        enhancements = []

        # Analyze each step
        for step_num, step_desc in enumerate(plan_steps):
            # Find relevant procedures
            procedure_enhancements = self._find_procedure_suggestions(step_desc)
            enhancements.extend(procedure_enhancements)

            # Find pattern matches
            pattern_enhancements = self._find_pattern_matches(step_desc)
            enhancements.extend(pattern_enhancements)

        # Rank enhancements by confidence
        enhancements.sort(key=lambda x: x.confidence, reverse=True)

        return {
            "cycle_id": cycle_id,
            "goal_description": goal_description,
            "total_steps": len(plan_steps),
            "suggested_enhancements": [
                {
                    "step": e.step_number,
                    "type": e.enhancement_type,
                    "description": e.description,
                    "confidence": e.confidence,
                    "source_type": e.source_type,
                }
                for e in enhancements[:5]  # Top 5 enhancements
            ],
            "enhancement_count": len(enhancements),
        }

    def apply_enhancement(
        self,
        cycle_id: str,
        goal_id: str,
        step_number: int,
        enhancement: PlanEnhancement
    ) -> int:
        """Apply an enhancement to a plan.

        Args:
            cycle_id: ActionCycle ID
            goal_id: Goal ID
            step_number: Step number being enhanced
            enhancement: Enhancement to apply

        Returns:
            Enhancement record ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO plan_enhancements
            (cycle_id, goal_id, enhancement_type, step_number,
             description, source_id, source_type, confidence,
             applied, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cycle_id,
            goal_id,
            enhancement.enhancement_type,
            step_number,
            enhancement.description,
            enhancement.source_id,
            enhancement.source_type,
            enhancement.confidence,
            1,  # Applied
            now
        ))

        enhancement_id = cursor.lastrowid
        # commit handled by cursor context
        return enhancement_id

    def record_enhancement_feedback(
        self,
        enhancement_id: int,
        outcome: str,  # helped, neutral, hindered
        feedback_text: Optional[str] = None
    ) -> int:
        """Record feedback on enhancement effectiveness.

        Args:
            enhancement_id: Enhancement ID
            outcome: How the enhancement worked out
            feedback_text: Optional feedback text

        Returns:
            Feedback record ID
        """
        cursor = self.db.get_cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO enhancement_feedback
            (enhancement_id, outcome, feedback_text, recorded_at)
            VALUES (?, ?, ?, ?)
        """, (enhancement_id, outcome, feedback_text, now))

        feedback_id = cursor.lastrowid

        # Update enhancement effectiveness
        effectiveness_map = {
            "helped": 1.0,
            "neutral": 0.5,
            "hindered": 0.0,
        }

        effectiveness = effectiveness_map.get(outcome, 0.5)

        cursor.execute("""
            UPDATE plan_enhancements
            SET effectiveness = ?
            WHERE id = ?
        """, (effectiveness, enhancement_id))

        # commit handled by cursor context
        return feedback_id

    def get_enhancement_effectiveness(self) -> dict:
        """Get effectiveness of applied enhancements.

        Returns:
            Effectiveness metrics dict
        """
        cursor = self.db.get_cursor()

        # By enhancement type
        cursor.execute("""
            SELECT enhancement_type, COUNT(*), AVG(effectiveness)
            FROM plan_enhancements
            WHERE applied = 1 AND effectiveness IS NOT NULL
            GROUP BY enhancement_type
        """)

        by_type = {}
        for row in cursor.fetchall():
            by_type[row[0]] = {
                "count": row[1],
                "average_effectiveness": row[2],
            }

        # Overall feedback
        cursor.execute("""
            SELECT outcome, COUNT(*)
            FROM enhancement_feedback
            GROUP BY outcome
        """)

        feedback_summary = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "enhancements_by_type": by_type,
            "feedback_summary": feedback_summary,
            "total_applied": sum(by_type[k]["count"] for k in by_type),
        }

    def _find_procedure_suggestions(self, step_description: str) -> list[PlanEnhancement]:
        """Find procedure suggestions for a plan step.

        Args:
            step_description: Description of plan step

        Returns:
            List of enhancement suggestions
        """
        cursor = self.db.get_cursor()

        # Find procedures with high success rate
        cursor.execute("""
            SELECT id, procedure_name, success_rate
            FROM procedure_creations
            WHERE success_rate > 0.7
            ORDER BY success_rate DESC
            LIMIT 3
        """)

        enhancements = []
        for idx, row in enumerate(cursor.fetchall()):
            enhancements.append(PlanEnhancement(
                step_number=0,  # Could be refined
                enhancement_type="procedure_suggestion",
                description=f"Use procedure: {row[1]}",
                confidence=row[2],
                source_id=row[0],
                source_type="procedure"
            ))

        return enhancements

    def _find_pattern_matches(self, step_description: str) -> list[PlanEnhancement]:
        """Find pattern matches for a plan step.

        Args:
            step_description: Description of plan step

        Returns:
            List of pattern suggestions
        """
        # Query semantic memory for patterns
        # For now, return empty (would integrate with semantic layer)
        return []

    def suggest_plan_improvement(
        self,
        goal_id: str,
        current_plan: list[str],
        execution_history: Optional[list[dict]] = None
    ) -> dict:
        """Suggest improvements to a plan based on history.

        Args:
            goal_id: Goal being planned for
            current_plan: Current plan steps
            execution_history: Optional history of past executions

        Returns:
            Improvement suggestions
        """
        cursor = self.db.get_cursor()

        # Find similar past goals
        cursor.execute("""
            SELECT id, step_number, description, source_type
            FROM plan_enhancements
            WHERE goal_id LIKE ?
            ORDER BY confidence DESC
            LIMIT 5
        """, (goal_id[:5] + "%",))

        similar_enhancements = []
        for row in cursor.fetchall():
            similar_enhancements.append({
                "step": row[1],
                "description": row[2],
                "source_type": row[3],
            })

        return {
            "goal_id": goal_id,
            "current_plan_length": len(current_plan),
            "suggested_improvements": similar_enhancements,
            "improvement_count": len(similar_enhancements),
        }
