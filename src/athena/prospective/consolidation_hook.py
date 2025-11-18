"""Consolidation hook: Bridges task learning patterns with procedural learning.

This module implements bidirectional learning:
1. Task patterns inform procedural learning (what patterns predict success)
2. Procedure feedback updates task pattern accuracy
3. Cross-layer learning for continuous improvement

Uses the FK relationship: prospective_tasks.learned_pattern_id → extracted_patterns(id)
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..core.database import Database
from .task_pattern_store import TaskPatternStore
from .task_patterns import TaskPattern, PatternStatus
from .pattern_extraction import PatternExtractor

logger = logging.getLogger(__name__)


class ConsolidationHook:
    """Bridges task learning patterns with consolidation and procedural learning."""

    def __init__(self, db: Database):
        """Initialize consolidation hook.

        Args:
            db: Database instance
        """
        self.db = db
        self.pattern_store = TaskPatternStore(db)
        self.extractor = PatternExtractor(self.pattern_store, project_id=1)

    def on_task_completed_with_pattern(
        self,
        task_id: int,
        pattern_id: int,
        success: bool,
        actual_outcome: Optional[str] = None,
    ) -> bool:
        """Called when task completes using a learned pattern.

        Links task completion with the pattern that was used (FK: learned_pattern_id).
        Enables bidirectional learning: pattern → task outcome → pattern update.

        Args:
            task_id: ID of completed task
            pattern_id: ID of pattern that informed task planning
            success: Whether the task succeeded
            actual_outcome: Free-form outcome description

        Returns:
            True if consolidation hook processed successfully
        """
        try:
            # Load pattern
            cursor = self.db.get_cursor()
            cursor.execute(
                "SELECT * FROM extracted_patterns WHERE id = %s",
                (pattern_id,),
            )
            pattern_row = cursor.fetchone()
            if not pattern_row:
                logger.warning(f"Pattern {pattern_id} not found for consolidation")
                return False

            pattern = self._row_to_pattern(pattern_row)

            # Update pattern based on task outcome
            updated_pattern = self._update_pattern_from_outcome(pattern, success, actual_outcome)

            # Save updated pattern
            self.pattern_store.save_pattern(updated_pattern)

            # Log consolidation event
            logger.info(
                f"Consolidation: Task {task_id} (success={success}) "
                f"updated pattern {pattern_id} "
                f"(confidence: {pattern.confidence_score:.2f} → {updated_pattern.confidence_score:.2f})"
            )

            return True

        except Exception as e:
            logger.error(f"Error in consolidation hook: {e}", exc_info=True)
            return False

    def _update_pattern_from_outcome(
        self,
        pattern: TaskPattern,
        success: bool,
        outcome_description: Optional[str] = None,
    ) -> TaskPattern:
        """Update pattern confidence based on actual task outcome.

        Args:
            pattern: Pattern that was used
            success: Whether the pattern prediction held true
            outcome_description: Qualitative description of outcome

        Returns:
            Updated pattern with adjusted confidence
        """
        # Create mutable copy
        updated = pattern.model_copy()

        # Adjust confidence based on prediction accuracy
        if success:
            # Pattern prediction was correct - increase confidence
            confidence_boost = 0.05
        else:
            # Pattern prediction failed - decrease confidence
            confidence_boost = -0.10

        # Apply adjustment with bounds
        updated.confidence_score = max(0.0, min(1.0, pattern.confidence_score + confidence_boost))

        # Add outcome feedback
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "description": outcome_description or "No description",
            "confidence_before": pattern.confidence_score,
            "confidence_after": updated.confidence_score,
        }

        # Store feedback (append to existing if present)
        if updated.validation_notes:
            updated.validation_notes += f"\n[Feedback] {json.dumps(feedback)}"
        else:
            updated.validation_notes = f"[Feedback] {json.dumps(feedback)}"

        # Deprecate if confidence drops too low
        if updated.confidence_score < 0.4:
            updated.status = PatternStatus.DEPRECATED
            logger.warning(
                f"Pattern {updated.pattern_name} deprecated "
                f"(confidence dropped to {updated.confidence_score:.2f})"
            )

        return updated

    def _row_to_pattern(self, row: tuple) -> TaskPattern:
        """Convert database row to TaskPattern object.

        Args:
            row: Database row from extracted_patterns table

        Returns:
            TaskPattern object
        """
        # Assuming row structure matches TaskPatternStore schema
        # Column order: id, project_id, pattern_name, pattern_type, description,
        # condition_json, prediction, sample_size, confidence_score, success_rate,
        # failure_count, extraction_method, status, validation_notes, system_2_validated,
        # learned_from_tasks
        return TaskPattern(
            id=row[0],
            project_id=row[1],
            pattern_name=row[2],
            pattern_type=row[3],
            description=row[4],
            condition_json=row[5],
            prediction=row[6],
            sample_size=row[7],
            confidence_score=row[8],
            success_rate=row[9],
            failure_count=row[10],
            extraction_method=row[11],
            status=row[12],
            validation_notes=row[13],
            system_2_validated=row[14],
            learned_from_tasks=row[15],
        )

    def consolidate_batch_outcomes(
        self,
        task_pattern_pairs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Consolidate multiple task-pattern pairs for batch learning.

        Args:
            task_pattern_pairs: List of {
                'task_id': int,
                'pattern_id': int,
                'success': bool,
                'outcome': str (optional)
            }

        Returns:
            Consolidation report with statistics
        """
        processed = 0
        successful_consolidations = 0
        patterns_updated = set()

        for pair in task_pattern_pairs:
            if self.on_task_completed_with_pattern(
                task_id=pair["task_id"],
                pattern_id=pair["pattern_id"],
                success=pair["success"],
                actual_outcome=pair.get("outcome"),
            ):
                processed += 1
                successful_consolidations += 1
                patterns_updated.add(pair["pattern_id"])

        logger.info(
            f"Batch consolidation complete: {successful_consolidations}/{processed} "
            f"consolidations, {len(patterns_updated)} unique patterns updated"
        )

        return {
            "total_pairs": len(task_pattern_pairs),
            "successful": successful_consolidations,
            "patterns_updated": len(patterns_updated),
            "timestamp": datetime.now().isoformat(),
        }
