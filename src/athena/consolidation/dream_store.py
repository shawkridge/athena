"""Dream procedure storage and query operations."""

from typing import Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .dream_models import (
    DreamProcedure,
    DreamStatus,
)


class DreamStore(BaseStore[DreamProcedure]):
    """Manages dream procedure storage and query operations."""

    table_name = "dream_procedures"
    model_class = DreamProcedure

    def __init__(self, db: Database):
        """Initialize dream store.

        Args:
            db: Database instance
        """
        super().__init__(db)

    def _row_to_model(self, row: Dict[str, Any]) -> DreamProcedure:
        """Convert database row to DreamProcedure model."""
        return DreamProcedure(
            id=row.get("id"),
            base_procedure_id=row.get("base_procedure_id"),
            base_procedure_name=row.get("base_procedure_name"),
            dream_type=row.get("dream_type"),
            code=row.get("code"),
            model_used=row.get("model_used"),
            reasoning=row.get("reasoning"),
            generated_description=row.get("generated_description"),
            status=row.get("status", DreamStatus.PENDING_EVALUATION.value),
            tier=int(row.get("tier")) if row.get("tier") else None,
            viability_score=row.get("viability_score"),
            claude_reasoning=row.get("claude_reasoning"),
            test_outcome=row.get("test_outcome"),
            test_error=row.get("test_error"),
            test_timestamp=(
                self.from_timestamp(row.get("test_timestamp"))
                if row.get("test_timestamp")
                else None
            ),
            novelty_score=row.get("novelty_score"),
            cross_project_matches=row.get("cross_project_matches", 0),
            effectiveness_metric=row.get("effectiveness_metric"),
            generated_at=self.from_timestamp(row.get("generated_at")),
            evaluated_at=(
                self.from_timestamp(row.get("evaluated_at")) if row.get("evaluated_at") else None
            ),
            created_by=row.get("created_by"),
        )
