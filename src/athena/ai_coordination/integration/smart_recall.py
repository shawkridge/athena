"""Smart recall for intelligent memory retrieval in AI Coordination.

Queries Memory-MCP to retrieve relevant knowledge for planning:
- Find similar problems solved before
- Retrieve procedures that worked
- Get code context from spatial memory
- Rank by relevance and success rate

This enables reuse: Pattern → Procedure → Better Planning
"""

import json
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.database import Database


class RecallContext:
    """Context for a recall operation."""

    def __init__(
        self,
        query: str,
        problem_type: Optional[str] = None,
        search_depth: int = 3,
        max_results: int = 10
    ):
        """Initialize recall context.

        Args:
            query: Search query/problem description
            problem_type: Optional type of problem (bug, feature, optimization, etc)
            search_depth: How deep to search in graph (1-5)
            max_results: Maximum results to return
        """
        self.query = query
        self.problem_type = problem_type
        self.search_depth = min(search_depth, 5)
        self.max_results = max_results
        self.timestamp = int(datetime.now().timestamp() * 1000)


class SmartRecall:
    """Intelligently retrieves relevant knowledge from Memory-MCP.

    Purpose:
    - Query semantic memory for similar problems
    - Retrieve procedures that solved similar problems
    - Get relevant code context from spatial hierarchy
    - Rank results by relevance and success rate
    - Enable knowledge reuse in planning

    This enables the learning loop closure:
    Old Problem → Similar Pattern Found → Procedure Retrieved → Better Plan
    """

    def __init__(self, db: "Database"):
        """Initialize SmartRecall.

        Args:
            db: Database connection
        """
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self):
        """Create smart recall tracking tables."""
        cursor = self.db.conn.cursor()

        # Table: Recall operations log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recall_operations (
                id INTEGER PRIMARY KEY,
                query_text TEXT NOT NULL,
                problem_type TEXT,
                session_id TEXT,
                goal_id TEXT,
                recall_timestamp INTEGER NOT NULL,
                results_found INTEGER,
                best_match_id INTEGER,
                best_match_type TEXT,
                match_confidence REAL,
                used_in_planning BOOLEAN DEFAULT 0,
                planning_success BOOLEAN
            )
        """)

        # Table: Reuse effectiveness tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reuse_effectiveness (
                id INTEGER PRIMARY KEY,
                original_problem TEXT,
                retrieved_solution_id INTEGER,
                solution_type TEXT,  -- procedure, pattern, example
                recall_operation_id INTEGER,
                reused_in_goal TEXT,
                outcome TEXT,  -- success, partial, failure
                effectiveness_score REAL,  -- 0.0-1.0
                recorded_at INTEGER NOT NULL,
                FOREIGN KEY (recall_operation_id) REFERENCES recall_operations(id)
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recall_operations_query
            ON recall_operations(problem_type, recall_timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reuse_effectiveness_solution
            ON reuse_effectiveness(solution_type, outcome)
        """)

        self.db.conn.commit()

    def recall_for_problem(
        self,
        query: str,
        problem_type: Optional[str] = None,
        max_results: int = 10
    ) -> dict:
        """Recall knowledge for a problem.

        Args:
            query: Problem description/query
            problem_type: Optional problem type
            max_results: Maximum results to return

        Returns:
            Dict with recalled knowledge
        """
        context = RecallContext(query, problem_type, max_results=max_results)

        # Get procedures that might help
        procedures = self._find_relevant_procedures(query, max_results)

        # Get patterns that might apply
        patterns = self._find_relevant_patterns(query, max_results)

        # Get code examples
        code_examples = self._find_relevant_code_context(query, max_results)

        # Log the recall operation
        recall_id = self._log_recall_operation(
            query,
            problem_type,
            len(procedures) + len(patterns) + len(code_examples)
        )

        return {
            "recall_id": recall_id,
            "query": query,
            "problem_type": problem_type,
            "procedures": procedures,
            "patterns": patterns,
            "code_examples": code_examples,
            "total_results": len(procedures) + len(patterns) + len(code_examples),
        }

    def recall_for_goal(
        self,
        goal_description: str,
        goal_id: str,
        session_id: str
    ) -> dict:
        """Recall knowledge for a goal.

        Args:
            goal_description: Description of goal
            goal_id: Goal identifier
            session_id: Session identifier

        Returns:
            Dict with recalled knowledge
        """
        result = self.recall_for_problem(goal_description)
        result["goal_id"] = goal_id
        result["session_id"] = session_id

        return result

    def get_procedure_candidates(
        self,
        goal_type: str,
        min_success_rate: float = 0.6
    ) -> list[dict]:
        """Get procedure candidates for a goal type.

        Args:
            goal_type: Type of goal
            min_success_rate: Minimum success rate (0.0-1.0)

        Returns:
            List of procedure candidates
        """
        cursor = self.db.conn.cursor()

        # Query procedure_creations table for relevant procedures
        cursor.execute("""
            SELECT id, procedure_name, category, success_rate, total_uses
            FROM procedure_creations
            WHERE success_rate >= ? AND total_uses > 0
            ORDER BY success_rate DESC
            LIMIT 10
        """, (min_success_rate,))

        candidates = []
        for row in cursor.fetchall():
            candidates.append({
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "success_rate": row[3],
                "times_used": row[4],
            })

        return candidates

    def find_similar_problems_solved(
        self,
        current_problem: str,
        limit: int = 5
    ) -> list[dict]:
        """Find problems similar to current one that were already solved.

        Args:
            current_problem: Current problem description
            limit: Maximum results

        Returns:
            List of similar problems with their solutions
        """
        cursor = self.db.conn.cursor()

        # Query semantic memory or episodic events for similar problems
        cursor.execute("""
            SELECT id, content, outcome
            FROM episodic_events
            WHERE event_type = 'action' AND outcome = 'success'
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        similar = []
        for row in cursor.fetchall():
            similar.append({
                "event_id": row[0],
                "description": row[1],
                "outcome": row[2],
            })

        return similar

    def rank_by_relevance(
        self,
        query: str,
        candidates: list[dict]
    ) -> list[dict]:
        """Rank candidates by relevance to query.

        Args:
            query: Query/problem description
            candidates: List of candidate solutions

        Returns:
            Ranked list of candidates
        """
        # Simple keyword-based ranking
        query_words = set(query.lower().split())

        ranked = []
        for candidate in candidates:
            # Calculate relevance score
            score = 0.5  # Base score

            # Check for keyword matches
            cand_text = candidate.get("name", "") + candidate.get("description", "")
            cand_words = set(cand_text.lower().split())
            matches = len(query_words & cand_words)
            score += matches * 0.1

            # Boost by success rate if available
            if "success_rate" in candidate:
                score += candidate["success_rate"] * 0.2

            candidate["relevance_score"] = min(score, 1.0)
            ranked.append(candidate)

        # Sort by relevance
        ranked.sort(key=lambda x: x["relevance_score"], reverse=True)
        return ranked

    def record_reuse(
        self,
        recall_id: int,
        solution_id: int,
        solution_type: str,
        goal_id: str,
        outcome: str,
        effectiveness: float
    ) -> int:
        """Record usage of recalled solution.

        Args:
            recall_id: Recall operation ID
            solution_id: ID of recalled solution
            solution_type: Type (procedure, pattern, example)
            goal_id: Goal it was used for
            outcome: Outcome (success, partial, failure)
            effectiveness: Effectiveness score (0.0-1.0)

        Returns:
            Reuse record ID
        """
        cursor = self.db.conn.cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO reuse_effectiveness
            (original_problem, retrieved_solution_id, solution_type,
             recall_operation_id, reused_in_goal, outcome,
             effectiveness_score, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "",  # Original problem text would come from recall_operations
            solution_id,
            solution_type,
            recall_id,
            goal_id,
            outcome,
            min(effectiveness, 1.0),
            now
        ))

        reuse_id = cursor.lastrowid
        self.db.conn.commit()
        return reuse_id

    def get_recall_metrics(self) -> dict:
        """Get overall recall metrics.

        Returns:
            Metrics dict
        """
        cursor = self.db.conn.cursor()

        # Total recalls
        cursor.execute("SELECT COUNT(*) FROM recall_operations")
        total_recalls = cursor.fetchone()[0]

        # Successful reuses
        cursor.execute("""
            SELECT COUNT(*), AVG(effectiveness_score)
            FROM reuse_effectiveness
            WHERE outcome = 'success'
        """)

        row = cursor.fetchone()
        successful_reuses = row[0] or 0
        avg_effectiveness = row[1] or 0

        # Overall effectiveness
        cursor.execute("""
            SELECT AVG(effectiveness_score)
            FROM reuse_effectiveness
        """)

        overall_effectiveness = cursor.fetchone()[0] or 0

        return {
            "total_recall_operations": total_recalls,
            "successful_reuses": successful_reuses,
            "average_reuse_effectiveness": avg_effectiveness,
            "overall_effectiveness": overall_effectiveness,
        }

    def _find_relevant_procedures(self, query: str, limit: int) -> list[dict]:
        """Find relevant procedures for query."""
        cursor = self.db.conn.cursor()

        try:
            # Query procedures - simple keyword matching
            cursor.execute("""
                SELECT id, procedure_name, category, success_rate
                FROM procedure_creations
                WHERE success_rate > 0.5
                ORDER BY success_rate DESC
                LIMIT ?
            """, (limit,))

            procedures = []
            for row in cursor.fetchall():
                procedures.append({
                    "id": row[0],
                    "name": row[1],
                    "category": row[2],
                    "success_rate": row[3],
                    "type": "procedure",
                })

            return procedures
        except Exception:
            # Table doesn't exist yet - return empty list
            return []

    def _find_relevant_patterns(self, query: str, limit: int) -> list[dict]:
        """Find relevant patterns for query."""
        # Query semantic memory for patterns
        return []  # Placeholder for semantic memory integration

    def _find_relevant_code_context(self, query: str, limit: int) -> list[dict]:
        """Find relevant code examples for query."""
        # Query spatial hierarchy for code context
        return []  # Placeholder for spatial memory integration

    def _log_recall_operation(
        self,
        query: str,
        problem_type: Optional[str],
        results_count: int
    ) -> int:
        """Log a recall operation.

        Args:
            query: Query text
            problem_type: Problem type
            results_count: Number of results found

        Returns:
            Recall operation ID
        """
        cursor = self.db.conn.cursor()
        now = int(datetime.now().timestamp() * 1000)

        cursor.execute("""
            INSERT INTO recall_operations
            (query_text, problem_type, recall_timestamp, results_found)
            VALUES (?, ?, ?, ?)
        """, (query, problem_type, now, results_count))

        recall_id = cursor.lastrowid
        self.db.conn.commit()
        return recall_id
