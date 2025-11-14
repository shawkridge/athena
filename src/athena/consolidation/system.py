"""Consolidation system for background optimization."""

import json
import time
from datetime import datetime, timedelta
from typing import Optional

from ..core.database import Database
from ..episodic.store import EpisodicStore
from ..memory.store import MemoryStore
from ..meta.store import MetaMemoryStore
from ..procedural.models import Procedure, ProcedureCategory
from ..procedural.store import ProceduralStore
from .metrics_store import ConsolidationMetricsStore
from .quality_metrics import ConsolidationQualityMetrics
from .models import (
    ConsolidationRun,
    ConsolidationType,
    ExtractedPattern,
    MemoryConflict,
    PatternType,
)


class ConsolidationSystem:
    """Manages background memory optimization and learning."""

    def __init__(
        self,
        db: Database,
        memory_store: MemoryStore,
        episodic_store: EpisodicStore,
        procedural_store: ProceduralStore,
        meta_store: MetaMemoryStore,
    ):
        """Initialize consolidation system.

        Args:
            db: Database instance
            memory_store: Semantic memory store
            episodic_store: Episodic memory store
            procedural_store: Procedural memory store
            meta_store: Meta-memory store
        """
        self.db = db
        self.memory_store = memory_store
        self.episodic_store = episodic_store
        self.procedural_store = procedural_store
        self.meta_store = meta_store
        # Ensure consolidation schema is created
        self._ensure_schema()
    def _ensure_schema(self):
        """Ensure consolidation tables exist."""
        cursor = self.db.get_cursor()

        # Consolidation runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consolidation_runs (
                id SERIAL PRIMARY KEY,
                project_id INTEGER,
                started_at INTEGER NOT NULL,
                completed_at INTEGER,
                status TEXT DEFAULT 'running',

                memories_scored INTEGER DEFAULT 0,
                memories_pruned INTEGER DEFAULT 0,
                patterns_extracted INTEGER DEFAULT 0,
                conflicts_resolved INTEGER DEFAULT 0,

                avg_quality_before REAL,
                avg_quality_after REAL,

                consolidation_type TEXT DEFAULT 'scheduled',
                notes TEXT,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Extracted patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_patterns (
                id SERIAL PRIMARY KEY,
                consolidation_run_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_content TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                occurrences INTEGER DEFAULT 1,

                source_events TEXT,

                created_procedure BOOLEAN DEFAULT FALSE,
                created_semantic_memory BOOLEAN DEFAULT FALSE,
                updated_entity BOOLEAN DEFAULT FALSE,

                FOREIGN KEY (consolidation_run_id) REFERENCES consolidation_runs(id) ON DELETE CASCADE
            )
        """)

        # Memory conflicts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_conflicts (
                id SERIAL PRIMARY KEY,
                discovered_at INTEGER NOT NULL,
                resolved_at INTEGER,
                status TEXT DEFAULT 'pending',

                item1_layer TEXT NOT NULL,
                item1_id INTEGER NOT NULL,
                item2_layer TEXT NOT NULL,
                item2_id INTEGER NOT NULL,

                conflict_type TEXT NOT NULL,
                description TEXT,

                resolution_strategy TEXT,
                resolution_notes TEXT,

                severity TEXT DEFAULT 'medium'
            )
        """)

        # Indices
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_consolidation_project ON consolidation_runs(project_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_consolidation_time ON consolidation_runs(started_at DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conflicts_status ON memory_conflicts(status)"
        )

        # commit handled by cursor context

    def run_consolidation(
        self,
        project_id: Optional[int] = None,
        consolidation_type: ConsolidationType = ConsolidationType.SCHEDULED,
    ) -> int:
        """Run full consolidation process with quality metrics measurement.

        Args:
            project_id: Optional project ID (None for global)
            consolidation_type: Type of consolidation

        Returns:
            ID of consolidation run
        """
        # Create run record
        run = ConsolidationRun(
            project_id=project_id,
            consolidation_type=consolidation_type,
            started_at=datetime.now(),
        )
        run_id = self._create_run(run)

        try:
            # 1. Score all memories
            avg_before = self._score_memories(project_id)

            # 2. Prune low-value memories
            pruned_count = self._prune_memories(project_id, threshold=0.1)

            # 3. Extract patterns from episodic events
            patterns_count = self._extract_patterns(project_id, run_id)

            # 4. Detect and resolve conflicts
            conflicts_count = self._resolve_conflicts(project_id)

            # 5. Strengthen frequently accessed memories
            self._strengthen_memories(project_id)

            # 6. Update meta-memory statistics
            self._update_meta_statistics(project_id)

            # Calculate final average quality
            avg_after = self._calculate_average_quality(project_id)

            # NEW: Measure consolidation quality metrics (research targets)
            metrics = self._measure_consolidation_metrics(project_id, run_id)

            # Update run record with both traditional stats and quality metrics
            self._complete_run(
                run_id,
                memories_scored=self._count_memories(project_id),
                memories_pruned=pruned_count,
                patterns_extracted=patterns_count,
                conflicts_resolved=conflicts_count,
                avg_quality_before=avg_before,
                avg_quality_after=avg_after,
                status="completed",
                # NEW: Add quality metrics
                compression_ratio=metrics.get("compression_ratio"),
                retrieval_recall=metrics.get("retrieval_recall"),
                pattern_consistency=metrics.get("pattern_consistency"),
                avg_information_density=metrics.get("avg_information_density"),
            )

        except Exception as e:
            self._complete_run(run_id, status="failed", notes=str(e))
            raise

        return run_id

    def _score_memories(self, project_id: Optional[int]) -> float:
        """Score all memories based on access patterns and usefulness."""
        cursor = self.db.get_cursor()

        # Get all memories
        if project_id:
            cursor.execute("SELECT id, access_count, usefulness_score FROM memories WHERE project_id = %s", (project_id,))
        else:
            cursor.execute("SELECT id, access_count, usefulness_score FROM memories")

        total_score = 0.0
        count = 0

        for row in cursor.fetchall():
            memory_id = row["id"]
            access_count = row["access_count"]
            current_score = row["usefulness_score"]

            # Calculate new score based on access patterns
            # More recent accesses = higher score
            new_score = min(1.0, current_score * 0.8 + (min(access_count, 10) / 10.0) * 0.2)

            cursor.execute(
                "UPDATE memories SET usefulness_score = %s WHERE id = %s",
                (new_score, memory_id)
            )

            total_score += new_score
            count += 1

        # commit handled by cursor context

        return total_score / count if count > 0 else 0.0

    def _prune_memories(self, project_id: Optional[int], threshold: float = 0.1) -> int:
        """Prune low-value memories below threshold."""
        cursor = self.db.get_cursor()

        # Find low-value memories
        if project_id:
            cursor.execute(
                "SELECT id FROM memories WHERE project_id = %s AND usefulness_score < %s AND access_count < 2",
                (project_id, threshold)
            )
        else:
            cursor.execute(
                "SELECT id FROM memories WHERE usefulness_score < %s AND access_count < 2",
                (threshold,)
            )

        memory_ids = [row["id"] for row in cursor.fetchall()]

        # Delete them
        for memory_id in memory_ids:
            self.memory_store.forget(memory_id)

        return len(memory_ids)

    def _extract_patterns(self, project_id: Optional[int], run_id: int) -> int:
        """Extract patterns from episodic events using surprise-based segmentation.

        Enhanced approach:
        1. Segment events using Bayesian surprise (research-backed)
        2. Extract context-specific patterns from surprise-based clusters
        3. Fall back to event-type grouping for cross-cluster patterns
        4. Create procedures from high-confidence patterns

        Research: Fountas et al. 2024, Kumar et al. 2023
        """
        if not project_id:
            return 0  # Pattern extraction requires project context

        try:
            # Get recent successful events
            recent_events = self.episodic_store.get_recent_events(project_id, hours=168)  # 1 week

            patterns_found = 0

            # STEP 1: Surprise-based segmentation (research-backed approach)
            # Group events by surprise boundaries for better context-aware patterns
            try:
                event_clusters = self.episodic_store.segment_events_by_surprise(
                    recent_events,
                    entropy_threshold=2.5,
                    min_event_spacing=3,
                )

                # Extract patterns within each surprise-based cluster
                for cluster in event_clusters:
                    if len(cluster) >= 2:
                        # Extract cluster-specific patterns
                        cluster_pattern = self._extract_pattern_from_cluster(cluster)
                        if cluster_pattern:
                            # Set the consolidation run ID
                            cluster_pattern.consolidation_run_id = run_id
                            self._save_pattern(cluster_pattern)
                            patterns_found += 1

                            # Consider creating procedure
                            if len(cluster) >= 5:
                                self._maybe_create_procedure(cluster_pattern, cluster)

            except Exception as e:
                # Log warning but continue to fallback method
                print(f"Warning: Surprise-based segmentation failed: {e}")

            # STEP 2: Fallback to event-type grouping for cross-cluster patterns
            # This captures patterns that span surprise boundaries
            event_sequences = {}

            for event in recent_events:
                if event.outcome and event.outcome == "success":
                    # Group similar events across clusters
                    key = f"{event.event_type}:{event.content[:50]}"
                    if key not in event_sequences:
                        event_sequences[key] = []
                    event_sequences[key].append(event)

            # Find recurring patterns (3+ occurrences)
            for key, events in event_sequences.items():
                if len(events) >= 3:
                    # Extract common pattern
                    pattern_content = self._extract_common_pattern(events)

                    pattern = ExtractedPattern(
                        consolidation_run_id=run_id,
                        pattern_type=PatternType.WORKFLOW,
                        pattern_content=pattern_content,
                        confidence=min(1.0, len(events) / 10.0),  # Confidence based on occurrences
                        occurrences=len(events),
                        source_events=[e.id for e in events if e.id],
                    )

                    self._save_pattern(pattern)
                    patterns_found += 1

                    # Consider creating a procedure from this pattern
                    if len(events) >= 5:
                        self._maybe_create_procedure(pattern, events)

            return patterns_found
        except Exception as e:
            # Log error but don't fail consolidation over pattern extraction
            print(f"Warning: Pattern extraction failed: {e}")
            return 0

    def _extract_common_pattern(self, events: list) -> str:
        """Extract common pattern from similar events."""
        # Simple heuristic: use the most common content
        contents = [e.content for e in events]
        # Return the shortest common content as template
        return min(contents, key=len)

    def _extract_pattern_from_cluster(self, cluster: list) -> Optional[ExtractedPattern]:
        """Extract pattern from a surprise-based event cluster.

        Uses cluster context to extract more meaningful patterns than
        simple event-type grouping.

        Args:
            cluster: List of events from a surprise-based cluster

        Returns:
            ExtractedPattern if found, None otherwise
        """
        if len(cluster) < 2:
            return None

        try:
            # Extract common context from cluster
            successful_events = [e for e in cluster if e.outcome == "success"]
            if len(successful_events) < 2:
                return None

            # Get common properties across cluster
            common_type = successful_events[0].event_type
            all_same_type = all(e.event_type == common_type for e in successful_events)

            if not all_same_type:
                # Mixed event types in cluster - find pattern in content
                contents = [e.content for e in successful_events]
                pattern_content = " → ".join([c[:30] for c in contents[:3]])  # Show sequence
            else:
                # Same event type - extract common template
                pattern_content = self._extract_common_pattern(successful_events)

            # Create pattern from cluster
            pattern = ExtractedPattern(
                consolidation_run_id=0,  # Will be set by caller
                pattern_type=PatternType.WORKFLOW,
                pattern_content=pattern_content,
                confidence=min(1.0, len(successful_events) / 5.0),  # Confidence from cluster size
                occurrences=len(successful_events),
                source_events=[e.id for e in cluster if e.id],
            )

            return pattern

        except Exception:
            return None

    def _maybe_create_procedure(self, pattern: ExtractedPattern, events: list):
        """Maybe create a procedure from an extracted pattern."""
        # Check if procedure already exists
        existing = self.procedural_store.search_procedures(pattern.pattern_content[:50])

        if not existing:
            # Create new procedure
            # Handle both enum and string types (due to Pydantic use_enum_values=True)
            pattern_type_str = (
                pattern.pattern_type.value
                if hasattr(pattern.pattern_type, "value")
                else pattern.pattern_type
            )
            # Use microsecond precision to ensure uniqueness (allows multiple consolidations per second)
            unique_id = int(time.time() * 1000000)
            procedure = Procedure(
                name=f"learned_{pattern_type_str}_{unique_id}",
                category=ProcedureCategory.REFACTORING,  # Default category
                description=f"Learned from {pattern.occurrences} occurrences",
                template=pattern.pattern_content,
                success_rate=0.8,  # High confidence from repeated success
                usage_count=pattern.occurrences,
                created_by="learned",
            )
            try:
                self.procedural_store.create_procedure(procedure)
            except Exception as e:
                # If procedure creation fails (e.g., UNIQUE constraint), skip silently
                # This can happen if procedure already exists with same name
                pass

    def _resolve_conflicts(self, project_id: Optional[int]) -> int:
        """Detect and resolve memory conflicts."""
        # Simple conflict detection: find duplicate or contradictory memories
        cursor = self.db.get_cursor()

        if project_id:
            cursor.execute("""
                SELECT m1.id as id1, m2.id as id2, m1.content as content1, m2.content as content2
                FROM memories m1
                JOIN memories m2 ON m1.project_id = m2.project_id AND m1.id < m2.id
                WHERE m1.project_id = %s AND m1.content = m2.content
            """, (project_id,))
        else:
            cursor.execute("""
                SELECT m1.id as id1, m2.id as id2, m1.content as content1, m2.content as content2
                FROM memories m1
                JOIN memories m2 ON m1.project_id = m2.project_id AND m1.id < m2.id
                WHERE m1.content = m2.content
            """)

        conflicts_resolved = 0
        for row in cursor.fetchall():
            # Duplicate found - keep the one with higher usefulness
            cursor.execute(
                "SELECT usefulness_score FROM memories WHERE id IN (%s, %s)",
                (row["id1"], row["id2"])
            )
            scores = cursor.fetchall()

            # Delete the lower scoring one
            if scores[0]["usefulness_score"] < scores[1]["usefulness_score"]:
                self.memory_store.forget(row["id1"])
            else:
                self.memory_store.forget(row["id2"])

            conflicts_resolved += 1

        return conflicts_resolved

    def _strengthen_memories(self, project_id: Optional[int]):
        """Strengthen frequently accessed memories."""
        cursor = self.db.get_cursor()

        if project_id:
            cursor.execute("""
                UPDATE memories
                SET usefulness_score = MIN(1.0, usefulness_score + 0.1)
                WHERE project_id = %s AND access_count > 5
            """, (project_id,))
        else:
            cursor.execute("""
                UPDATE memories
                SET usefulness_score = MIN(1.0, usefulness_score + 0.1)
                WHERE access_count > 5
            """)

        # commit handled by cursor context

    def _update_meta_statistics(self, project_id: Optional[int]):
        """Update meta-memory statistics."""
        # Update domain coverage for all domains
        cursor = self.db.get_cursor()

        if project_id:
            cursor.execute(
                "SELECT DISTINCT tags FROM memories WHERE project_id = %s",
                (project_id,)
            )
        else:
            cursor.execute("SELECT DISTINCT tags FROM memories")

        # Note: Domain coverage updates would be done here if MetaMemoryStore.update_domain_coverage() existed
        # For now, we skip this step as the method is not implemented in MetaMemoryStore

    def _calculate_average_quality(self, project_id: Optional[int]) -> float:
        """Calculate average quality score."""
        cursor = self.db.get_cursor()

        if project_id:
            cursor.execute(
                "SELECT AVG(usefulness_score) as avg FROM memories WHERE project_id = %s",
                (project_id,)
            )
        else:
            cursor.execute("SELECT AVG(usefulness_score) as avg FROM memories")

        row = cursor.fetchone()
        return row["avg"] if row and row["avg"] else 0.0

    def _count_memories(self, project_id: Optional[int]) -> int:
        """Count memories."""
        cursor = self.db.get_cursor()

        if project_id:
            cursor.execute("SELECT COUNT(*) as count FROM memories WHERE project_id = %s", (project_id,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM memories")

        return cursor.fetchone()["count"]

    def _create_run(self, run: ConsolidationRun) -> int:
        """Create a consolidation run record."""
        cursor = self.db.get_cursor()

        consolidation_type_str = (
            run.consolidation_type.value
            if isinstance(run.consolidation_type, ConsolidationType)
            else run.consolidation_type
        )

        cursor.execute("""
            INSERT INTO consolidation_runs (
                project_id, started_at, status, consolidation_type
            ) VALUES (%s, %s, %s, %s)
        """, (
            run.project_id,
            int(run.started_at.timestamp()),
            run.status,
            consolidation_type_str,
        ))

        # commit handled by cursor context
        return cursor.lastrowid

    def _complete_run(
        self,
        run_id: int,
        memories_scored: int = 0,
        memories_pruned: int = 0,
        patterns_extracted: int = 0,
        conflicts_resolved: int = 0,
        avg_quality_before: Optional[float] = None,
        avg_quality_after: Optional[float] = None,
        status: str = "completed",
        notes: Optional[str] = None,
        compression_ratio: Optional[float] = None,
        retrieval_recall: Optional[float] = None,
        pattern_consistency: Optional[float] = None,
        avg_information_density: Optional[float] = None,
    ):
        """Complete a consolidation run and store quality metrics."""
        cursor = self.db.get_cursor()

        # Calculate overall quality score if metrics available
        overall_score = None
        if all(v is not None for v in [compression_ratio, retrieval_recall, pattern_consistency, avg_information_density]):
            overall_score = (
                compression_ratio * 0.25
                + retrieval_recall * 0.25
                + pattern_consistency * 0.25
                + avg_information_density * 0.25
            )

        cursor.execute("""
            UPDATE consolidation_runs
            SET completed_at = %s, status = %s,
                memories_scored = %s, memories_pruned = %s,
                patterns_extracted = %s, conflicts_resolved = %s,
                avg_quality_before = %s, avg_quality_after = %s,
                compression_ratio = %s, retrieval_recall = %s,
                pattern_consistency = %s, avg_information_density = %s,
                overall_quality_score = %s,
                notes = %s
            WHERE id = %s
        """, (
            int(time.time()),
            status,
            memories_scored,
            memories_pruned,
            patterns_extracted,
            conflicts_resolved,
            avg_quality_before,
            avg_quality_after,
            compression_ratio,
            retrieval_recall,
            pattern_consistency,
            avg_information_density,
            overall_score,
            notes,
            run_id,
        ))

        # commit handled by cursor context

    def _measure_consolidation_metrics(
        self,
        project_id: Optional[int],
        run_id: int
    ) -> dict:
        """Measure consolidation quality metrics (research targets).

        Measures:
        - Compression ratio: 70-85% (episodic→semantic)
        - Retrieval recall: >80% (information preservation)
        - Pattern consistency: >75% (generalization quality)
        - Information density: >70% (efficiency)

        Args:
            project_id: Project ID (None for global)
            run_id: Consolidation run ID

        Returns:
            Dict with quality metrics
        """
        try:
            quality_metrics = ConsolidationQualityMetrics(
                self.episodic_store,
                self.memory_store
            )

            # Get session ID for this project's consolidation
            cursor = self.db.get_cursor()
            if project_id:
                cursor.execute(
                    "SELECT session_id FROM episodic_events WHERE project_id = %s ORDER BY timestamp DESC LIMIT 1",
                    (project_id,)
                )
            else:
                cursor.execute(
                    "SELECT session_id FROM episodic_events ORDER BY timestamp DESC LIMIT 1"
                )

            result = cursor.fetchone()
            if not result:
                return {
                    "compression_ratio": 0.0,
                    "retrieval_recall": 0.0,
                    "pattern_consistency": 0.0,
                    "avg_information_density": 0.0,
                }

            session_id = result[0]

            # Measure all metrics
            compression = quality_metrics.measure_compression_ratio(session_id)
            recall_metrics = quality_metrics.measure_retrieval_recall(session_id)
            consistency = quality_metrics.measure_pattern_consistency(session_id)
            density_metrics = quality_metrics.measure_information_density(session_id)

            metrics = {
                "compression_ratio": compression,
                "retrieval_recall": recall_metrics.get("relative_recall", 0.0),
                "pattern_consistency": consistency,
                "avg_information_density": density_metrics.get("avg_density", 0.0),
            }

            # Store metrics via metrics store
            metrics_store = ConsolidationMetricsStore(self.db)
            metrics_store.store_run_metrics(
                run_id,
                metrics["compression_ratio"],
                metrics["retrieval_recall"],
                metrics["pattern_consistency"],
                metrics["avg_information_density"],
            )

            return metrics

        except Exception as e:
            print(f"Error measuring consolidation metrics: {e}")
            return {
                "compression_ratio": 0.0,
                "retrieval_recall": 0.0,
                "pattern_consistency": 0.0,
                "avg_information_density": 0.0,
            }

    def _save_pattern(self, pattern: ExtractedPattern):
        """Save an extracted pattern."""
        cursor = self.db.get_cursor()

        pattern_type_str = (
            pattern.pattern_type.value
            if isinstance(pattern.pattern_type, PatternType)
            else pattern.pattern_type
        )

        cursor.execute("""
            INSERT INTO extracted_patterns (
                consolidation_run_id, pattern_type, pattern_content,
                confidence, occurrences, source_events
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            pattern.consolidation_run_id,
            pattern_type_str,
            pattern.pattern_content,
            pattern.confidence,
            pattern.occurrences,
            json.dumps(pattern.source_events),
        ))

        # commit handled by cursor context

    def get_latest_run(self, project_id: Optional[int] = None) -> Optional[ConsolidationRun]:
        """Get latest consolidation run."""
        cursor = self.db.get_cursor()

        if project_id:
            cursor.execute(
                "SELECT * FROM consolidation_runs WHERE project_id = %s ORDER BY started_at DESC LIMIT 1",
                (project_id,)
            )
        else:
            cursor.execute("SELECT * FROM consolidation_runs ORDER BY started_at DESC LIMIT 1")

        row = cursor.fetchone()
        if not row:
            return None

        return ConsolidationRun(
            id=row["id"],
            project_id=row["project_id"],
            started_at=datetime.fromtimestamp(row["started_at"]),
            completed_at=datetime.fromtimestamp(row["completed_at"]) if row["completed_at"] else None,
            status=row["status"],
            memories_scored=row["memories_scored"],
            memories_pruned=row["memories_pruned"],
            patterns_extracted=row["patterns_extracted"],
            conflicts_resolved=row["conflicts_resolved"],
            avg_quality_before=row["avg_quality_before"],
            avg_quality_after=row["avg_quality_after"],
            consolidation_type=ConsolidationType(row["consolidation_type"]),
            notes=row["notes"],
        )
