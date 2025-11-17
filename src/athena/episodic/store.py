"""Episodic memory storage and query operations."""

import json
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from ..core.database import Database
from ..core.base_store import BaseStore
from .models import EpisodicEvent, EventContext, EventMetric, EventOutcome, EventType
from .surprise import BayesianSurprise, SurpriseEvent


class EpisodicStore(BaseStore):
    """Manages episodic event storage and queries."""

    table_name = "episodic_events"
    model_class = EpisodicEvent

    def __init__(self, db: Database):
        """Initialize episodic store.

        Args:
            db: Database instance
        """
        super().__init__(db)
        self._embedding_model = None  # Lazy-load and cache embedding model
        # Schema is initialized centrally in database.py
        #
    def _row_to_model(self, row: Dict[str, Any]) -> EpisodicEvent:
        """Convert database row to EpisodicEvent model.

        Args:
            row: Database row as dict

        Returns:
            EpisodicEvent instance
        """
        # Convert tuple to dict if needed
        row_dict = row if isinstance(row, dict) else dict(row)

        # Deserialize context files as list
        context_files = self._safe_json_loads(row_dict.get("context_files"), []) if row_dict.get("context_files") else []
        if not isinstance(context_files, list):
            context_files = []

        context = EventContext(
            cwd=row_dict.get("context_cwd"),
            files=context_files,
            task=row_dict.get("context_task"),
            phase=row_dict.get("context_phase"),
        )

        # Parse code-aware fields
        from .models import CodeEventType
        code_event_type = None
        if row_dict.get("code_event_type"):
            try:
                code_event_type = CodeEventType(row_dict.get("code_event_type"))
            except (ValueError, KeyError):
                pass

        # Parse performance metrics from JSON
        perf_metrics = None
        if row_dict.get("performance_metrics"):
            perf_metrics = self._safe_json_loads(row_dict.get("performance_metrics"))

        # Convert test_passed from SQLite integer (0/1) to boolean
        test_passed = None
        if row_dict.get("test_passed") is not None:
            test_passed = bool(row_dict.get("test_passed"))

        return EpisodicEvent(
            id=row_dict.get("id"),
            project_id=row_dict.get("project_id"),
            session_id=row_dict.get("session_id"),
            timestamp=datetime.fromtimestamp(row_dict.get("timestamp")) if row_dict.get("timestamp") else None,
            event_type=EventType(row_dict.get("event_type")) if row_dict.get("event_type") else None,
            content=row_dict.get("content"),
            outcome=EventOutcome(row_dict.get("outcome")) if row_dict.get("outcome") else None,
            context=context,
            duration_ms=row_dict.get("duration_ms"),
            files_changed=row_dict.get("files_changed", 0),
            lines_added=row_dict.get("lines_added", 0),
            lines_deleted=row_dict.get("lines_deleted", 0),
            learned=row_dict.get("learned"),
            confidence=row_dict.get("confidence", 1.0),
            consolidation_status=row_dict.get("consolidation_status", "unconsolidated"),
            consolidated_at=datetime.fromtimestamp(row_dict.get("consolidated_at")) if row_dict.get("consolidated_at") else None,
            # Code-aware fields
            code_event_type=code_event_type,
            file_path=row_dict.get("file_path"),
            symbol_name=row_dict.get("symbol_name"),
            symbol_type=row_dict.get("symbol_type"),
            language=row_dict.get("language"),
            diff=row_dict.get("diff"),
            git_commit=row_dict.get("git_commit"),
            git_author=row_dict.get("git_author"),
            test_name=row_dict.get("test_name"),
            test_passed=test_passed,
            error_type=row_dict.get("error_type"),
            stack_trace=row_dict.get("stack_trace"),
            performance_metrics=perf_metrics,
            code_quality_score=row_dict.get("code_quality_score"),
            # Enhanced context metadata for working memory optimization
            project_name=row_dict.get("project_name"),
            project_goal=row_dict.get("project_goal"),
            project_phase_status=row_dict.get("project_phase_status"),
            importance_score=row_dict.get("importance_score", 0.5),
            actionability_score=row_dict.get("actionability_score", 0.5),
            context_completeness_score=row_dict.get("context_completeness_score", 0.5),
            has_next_step=bool(row_dict.get("has_next_step", 0)),
            has_blocker=bool(row_dict.get("has_blocker", 0)),
            required_decisions=row_dict.get("required_decisions"),
        )

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
            from ..core.error_handling import safe_json_loads
            return safe_json_loads(data, default)
        except (json.JSONDecodeError, ValueError, TypeError):
            return default

    def _get_embedding_model(self):
        """Get or create cached embedding model (lazy-loaded)."""
        if self._embedding_model is None:
            from ..core.embeddings import EmbeddingModel
            self._embedding_model = EmbeddingModel()
        return self._embedding_model

    def _ensure_schema(self):
        """Ensure episodic memory tables exist."""

        # For PostgreSQL async databases, skip sync schema initialization
        if not hasattr(self.db, 'conn'):
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"{self.__class__.__name__}: PostgreSQL async database detected. Schema management handled by _init_schema().")
            return
        cursor = self.db.get_cursor()

        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_events (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                outcome TEXT,

                context_cwd TEXT,
                context_files TEXT,
                context_task TEXT,
                context_phase TEXT,

                duration_ms INTEGER,
                files_changed INTEGER DEFAULT 0,
                lines_added INTEGER DEFAULT 0,
                lines_deleted INTEGER DEFAULT 0,

                learned TEXT,
                confidence REAL DEFAULT 1.0,

                consolidation_status TEXT DEFAULT 'unconsolidated',
                consolidated_at INTEGER,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Event outcomes/metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_outcomes (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
            )
        """)

        # Event relations (cause → effect)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_relations (
                from_event_id INTEGER NOT NULL,
                to_event_id INTEGER NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (from_event_id, to_event_id),
                FOREIGN KEY (from_event_id) REFERENCES episodic_events(id) ON DELETE CASCADE,
                FOREIGN KEY (to_event_id) REFERENCES episodic_events(id) ON DELETE CASCADE
            )
        """)

        # Vector embeddings for semantic search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS event_vectors USING vec0(
                embedding FLOAT[768]
            )
        """)

        # Indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON episodic_events(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_project ON episodic_events(project_id, timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_consolidation ON episodic_events(project_id, consolidation_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON episodic_events(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON episodic_events(event_type)")

        # Event relation indices (temporal chains)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_from ON event_relations(from_event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_to ON event_relations(to_event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON event_relations(relation_type)")

        # Event outcomes index
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_event ON event_outcomes(event_id)")

        self.commit()

    def record_event(
        self,
        event: EpisodicEvent,
        surprise_score: Optional[float] = None,
        surprise_normalized: Optional[float] = None,
        surprise_coherence: Optional[float] = None,
    ) -> int:
        """Record a new episodic event with optional surprise metrics.

        Args:
            event: Event to record
            surprise_score: Raw Bayesian surprise value (optional)
            surprise_normalized: Normalized surprise (0-1) (optional)
            surprise_coherence: Semantic coherence score (optional)

        Returns:
            ID of recorded event
        """
        event_type_str = (
            event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        )
        outcome_str = (
            event.outcome.value if isinstance(event.outcome, EventOutcome) else event.outcome
        ) if event.outcome else None

        # Generate embedding before insert (for pgvector)
        embedding = None
        try:
            embedding = self._generate_embedding(event.content)
        except Exception as e:
            import logging
            logging.debug(f"Failed to generate embedding: {e}")

        cursor = self.execute(
            """
            INSERT INTO episodic_events (
                project_id, session_id, timestamp, event_type, content, outcome,
                context_cwd, context_files, context_task, context_phase,
                duration_ms, files_changed, lines_added, lines_deleted,
                learned, confidence, surprise_score, surprise_normalized, surprise_coherence,
                embedding, project_name, project_goal, project_phase_status,
                importance_score, actionability_score, context_completeness_score,
                has_next_step, has_blocker, required_decisions
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                event.project_id,
                event.session_id,
                int(event.timestamp.timestamp()),
                event_type_str,
                event.content,
                outcome_str,
                event.context.cwd,
                self.serialize_json(event.context.files) if event.context.files else None,
                event.context.task,
                event.context.phase,
                event.duration_ms,
                event.files_changed,
                event.lines_added,
                event.lines_deleted,
                event.learned,
                event.confidence,
                surprise_score,
                surprise_normalized,
                surprise_coherence,
                self.serialize_json(embedding) if embedding else None,
                event.project_name,
                event.project_goal,
                event.project_phase_status,
                event.importance_score,
                event.actionability_score,
                event.context_completeness_score,
                int(event.has_next_step),
                int(event.has_blocker),
                event.required_decisions,
            ),
        )

        # Get the ID from RETURNING clause
        event_id = None
        try:
            # Try to fetch the result from cursor if it has fetchone
            if hasattr(cursor, 'fetchone'):
                row = cursor.fetchone()
                if row:
                    # Handle both dict-like Row objects and tuples
                    if hasattr(row, 'get'):
                        event_id = row.get('id')
                    else:
                        # Try tuple access
                        try:
                            event_id = row[0]
                        except (KeyError, TypeError):
                            # Try converting to tuple
                            event_id = tuple(row)[0] if row else None
        except (IndexError, TypeError, AttributeError, KeyError):
            event_id = None

        self.commit()

        # Wire to EpisodicGraphBridge for automatic entity extraction
        # This integrates the event into the knowledge graph automatically
        if event_id:
            try:
                from ..integration.episodic_graph_bridge import EpisodicGraphBridge
                bridge = EpisodicGraphBridge(self.db)
                bridge.integrate_events_to_graph(event_ids=[event_id])
            except ImportError:
                # Graph integration optional (degradation)
                pass
            except Exception as e:
                # Log but don't fail on graph integration errors
                import logging
                logging.warning(f"Failed to integrate event {event_id} to graph: {e}")

        return event_id

    def batch_record_events(self, events: List[EpisodicEvent]) -> List[int]:
        """Record multiple episodic events with embeddings in a single transaction (optimized).

        Args:
            events: List of events to record

        Returns:
            List of event IDs
        """
        if not events:
            return []

        cursor = self.db.get_cursor()
        event_ids = []

        try:
            # Prepare data for batch insert
            data = []
            for event in events:
                event_type_str = (
                    event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
                )
                outcome_str = (
                    event.outcome.value if isinstance(event.outcome, EventOutcome) else event.outcome
                ) if event.outcome else None

                data.append((
                    event.project_id,
                    event.session_id,
                    int(event.timestamp.timestamp()),
                    event_type_str,
                    event.content,
                    outcome_str,
                    event.context.cwd,
                    self.serialize_json(event.context.files) if event.context.files else None,
                    event.context.task,
                    event.context.phase,
                    event.duration_ms,
                    event.files_changed,
                    event.lines_added,
                    event.lines_deleted,
                    event.learned,
                    event.confidence,
                    event.project_name,
                    event.project_goal,
                    event.project_phase_status,
                    event.importance_score,
                    event.actionability_score,
                    event.context_completeness_score,
                    int(event.has_next_step),
                    int(event.has_blocker),
                    event.required_decisions,
                ))

            # Batch insert all events
            cursor.executemany("""
                INSERT INTO episodic_events (
                    project_id, session_id, timestamp, event_type, content, outcome,
                    context_cwd, context_files, context_task, context_phase,
                    duration_ms, files_changed, lines_added, lines_deleted,
                    learned, confidence, project_name, project_goal, project_phase_status,
                    importance_score, actionability_score, context_completeness_score,
                    has_next_step, has_blocker, required_decisions
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, data)

            # Get the last inserted ID and work backward
            # Note: cursor.lastrowid may be None after executemany, so we query instead
            cursor.execute("SELECT MAX(id) FROM episodic_events")
            max_id_result = cursor.fetchone()
            last_id = max_id_result[0] if max_id_result and max_id_result[0] else 0
            first_id = last_id - len(events) + 1
            event_ids = list(range(first_id, last_id + 1))

            # Batch generate and store embeddings (parallel if possible)
            try:
                embedding_model = self._get_embedding_model()
                embedding_data = []

                for i, event in enumerate(events):
                    try:
                        embedding = embedding_model.embed(event.content)
                        event_id = event_ids[i]
                        embedding_data.append((event_id, self.serialize_json(embedding)))
                    except Exception as e:
                        import logging
                        logging.warning(f"Failed to generate embedding for event {event_ids[i]}: {e}")

                # Batch insert embeddings
                if embedding_data:
                    cursor.executemany("""
                        INSERT INTO event_vectors (rowid, embedding)
                        VALUES (%s, %s)
                    """, embedding_data)

            except Exception as e:
                import logging
                logging.warning(f"Failed to batch generate embeddings: {e}")

            self.commit()
            return event_ids

        except Exception as e:
            # rollback handled by cursor context
            raise e

    def get_event(self, event_id: int) -> Optional[EpisodicEvent]:
        """Get event by ID.

        Args:
            event_id: Event ID

        Returns:
            Event if found, None otherwise
        """
        row = self.execute("SELECT * FROM episodic_events WHERE id = %s", (event_id,), fetch_one=True)

        if not row:
            return None

        return self._row_to_model(row)

    def get_events_by_date(
        self, project_id: int, start_date: datetime, end_date: Optional[datetime] = None
    ) -> list[EpisodicEvent]:
        """Get events within a date range.

        Args:
            project_id: Project ID
            start_date: Start of date range
            end_date: End of date range (defaults to now)

        Returns:
            List of events
        """
        end_date = end_date or datetime.now()
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())

        rows = self.execute(
            """
            SELECT * FROM episodic_events
            WHERE project_id = %s AND timestamp BETWEEN %s AND %s
            ORDER BY timestamp DESC
        """,
            (project_id, start_ts, end_ts),
            fetch_all=True
        )

        return [self._row_to_model(row) for row in rows]

    def get_events_by_session(self, session_id: str) -> list[EpisodicEvent]:
        """Get all events in a session.

        Args:
            session_id: Session ID

        Returns:
            List of events in chronological order
        """
        rows = self.execute(
            """
            SELECT * FROM episodic_events
            WHERE session_id = %s
            ORDER BY timestamp ASC
        """,
            (session_id,),
            fetch_all=True
        )

        return [self._row_to_model(row) for row in rows]

    def get_events_by_type(
        self, project_id: int, event_type: EventType, limit: int = 50
    ) -> list[EpisodicEvent]:
        """Get events of a specific type.

        Args:
            project_id: Project ID
            event_type: Type of events to retrieve
            limit: Maximum number of events

        Returns:
            List of events
        """
        event_type_str = event_type.value if isinstance(event_type, EventType) else event_type

        rows = self.execute(
            """
            SELECT * FROM episodic_events
            WHERE project_id = %s AND event_type = %s
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (project_id, event_type_str, limit),
            fetch_all=True
        )

        return [self._row_to_model(row) for row in rows]

    def get_recent_events(self, project_id: int, hours: int = 24, limit: int = 50) -> list[EpisodicEvent]:
        """Get recent events.

        Args:
            project_id: Project ID
            hours: Number of hours to look back
            limit: Maximum number of events

        Returns:
            List of recent events
        """
        cutoff = int((datetime.now() - timedelta(hours=hours)).timestamp())

        rows = self.execute(
            """
            SELECT * FROM episodic_events
            WHERE project_id = %s AND timestamp > %s
            ORDER BY timestamp DESC
            LIMIT %s
        """,
            (project_id, cutoff, limit),
            fetch_all=True
        )

        return [self._row_to_model(row) for row in rows]

    def search_events(
        self, project_id: int, query: str, limit: int = 20
    ) -> list[EpisodicEvent]:
        """Search events by content using keyword matching.

        Args:
            project_id: Project ID
            query: Search query (supports multiple keywords)
            limit: Maximum results

        Returns:
            List of matching events
        """
        # Split query into keywords and create LIKE conditions
        keywords = query.lower().split()
        if not keywords:
            return []

        # Build WHERE clause for keyword matching
        where_conditions = []
        params = [project_id]

        for keyword in keywords:
            # Skip very short words and common stop words
            if len(keyword) < 3 or keyword in ['the', 'and', 'or', 'but', 'for', 'are', 'was', 'were', 'what', 'when', 'where', 'how', 'why', 'who']:
                continue
            where_conditions.append("LOWER(content) LIKE %s")
            params.append(f"%{keyword}%")

        if not where_conditions:
            # If no valid keywords, fall back to original behavior
            where_conditions = ["content LIKE %s"]
            params = [project_id, f"%{query}%"]

        where_clause = " OR ".join(where_conditions)

        sql = f"""
            SELECT * FROM episodic_events
            WHERE project_id = %s AND ({where_clause})
            ORDER BY timestamp DESC
            LIMIT %s
        """

        rows = self.execute(sql, params + [limit], fetch_all=True)

        return [self._row_to_model(row) for row in rows]

    def get_event_timeline(
        self, project_id: int, start_date: datetime, end_date: datetime
    ) -> dict:
        """Get event timeline with aggregations.

        Args:
            project_id: Project ID
            start_date: Start date
            end_date: End date

        Returns:
            Timeline data with events grouped by day
        """
        events = self.get_events_by_date(project_id, start_date, end_date)

        timeline = {}
        for event in events:
            date_key = event.timestamp.strftime("%Y-%m-%d")
            if date_key not in timeline:
                timeline[date_key] = {
                    "events": [],
                    "count": 0,
                    "types": {},
                    "outcomes": {},
                }

            timeline[date_key]["events"].append(event)
            timeline[date_key]["count"] += 1

            event_type = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
            timeline[date_key]["types"][event_type] = timeline[date_key]["types"].get(event_type, 0) + 1

            if event.outcome:
                outcome = event.outcome.value if isinstance(event.outcome, EventOutcome) else event.outcome
                timeline[date_key]["outcomes"][outcome] = timeline[date_key]["outcomes"].get(outcome, 0) + 1

        return timeline

    def add_event_metric(self, metric: EventMetric) -> int:
        """Add a metric to an event.

        Args:
            metric: Event metric

        Returns:
            ID of created metric
        """
        cursor = self.execute(
            """
            INSERT INTO event_outcomes (event_id, metric_name, metric_value)
            VALUES (%s, %s, %s)
        """,
            (metric.event_id, metric.metric_name, metric.metric_value),
        )
        self.commit()
        return cursor.lastrowid

    def get_event_metrics(self, event_id: int) -> list[EventMetric]:
        """Get all metrics for an event.

        Args:
            event_id: Event ID

        Returns:
            List of metrics
        """
        rows = self.execute(
            "SELECT * FROM event_outcomes WHERE event_id = %s", (event_id,), fetch_all=True
        )

        metrics = []
        for row in rows:
            metrics.append(
                EventMetric(
                    id=row["id"],
                    event_id=row["event_id"],
                    metric_name=row["metric_name"],
                    metric_value=row["metric_value"],
                )
            )

        return metrics

    def create_event_relation(
        self, from_event_id: int, to_event_id: int, relation_type: str, strength: float = 1.0
    ):
        """Create a relation between events.

        Args:
            from_event_id: Source event ID
            to_event_id: Target event ID
            relation_type: Type of relation (caused_by, led_to, related_to)
            strength: Relation strength (0-1)
        """
        self.execute(
            """
            INSERT OR REPLACE INTO event_relations (from_event_id, to_event_id, relation_type, strength)
            VALUES (%s, %s, %s, %s)
        """,
            (from_event_id, to_event_id, relation_type, strength),
        )
        self.commit()

    def segment_events_by_surprise(
        self,
        events: List[EpisodicEvent],
        entropy_threshold: float = 2.5,
        min_event_spacing: int = 3,
    ) -> List[List[EpisodicEvent]]:
        """Segment events into clusters using Bayesian surprise.

        Uses surprise-based event boundaries instead of time-based heuristics.
        Events with high surprise scores mark important boundaries where
        expectations were violated.

        Algorithm:
        1. Convert event contents to token sequence
        2. Compute Bayesian surprise (KL divergence) at each position
        3. Identify boundaries where surprise > threshold
        4. Group events into surprise-based clusters
        5. Return ordered list of event clusters

        Research: Fountas et al. 2024 "Human-like Episodic Memory for Infinite Context LLMs"
                  Kumar et al. 2023 "Bayesian Surprise Predicts Human Event Segmentation"

        Args:
            events: List of episodic events to segment
            entropy_threshold: Surprise threshold for event boundaries (default 2.5)
            min_event_spacing: Minimum events between boundaries (default 3)

        Returns:
            List of event clusters, where each cluster is a list of events
        """
        if not events or len(events) < 2:
            return [events] if events else []

        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # Step 1: Convert events to token sequence (using event content as tokens)
        # For Bayesian surprise, we treat each event's content as a "token"
        tokens = [e.content[:100] for e in sorted_events]  # Use content prefix as token

        # Step 2: Initialize Bayesian surprise calculator
        surprise_calc = BayesianSurprise(
            entropy_threshold=entropy_threshold,
            min_event_spacing=min_event_spacing,
        )

        # Step 3: Find surprise-based event boundaries
        surprise_events = surprise_calc.find_event_boundaries(
            tokens,
            threshold=entropy_threshold,
            use_kl_divergence=True,
        )

        if not surprise_events:
            # No boundaries found - return all events as single cluster
            return [sorted_events]

        # Step 4: Extract boundary indices (where new clusters should start)
        boundary_indices = sorted(
            [se.index for se in surprise_events],
            reverse=False
        )

        # Step 5: Group events into clusters based on boundaries
        clusters = []
        current_cluster = []
        boundary_set = set(boundary_indices)

        for i, event in enumerate(sorted_events):
            if i in boundary_set and current_cluster:
                # Start new cluster at boundary
                clusters.append(current_cluster)
                current_cluster = [event]
            else:
                current_cluster.append(event)

        # Add final cluster
        if current_cluster:
            clusters.append(current_cluster)

        return clusters if clusters else [sorted_events]

    def get_events_by_timeframe(
        self,
        project_id: int,
        start: datetime,
        end: datetime,
        consolidation_status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list[EpisodicEvent]:
        """Get events within a time range.

        Args:
            project_id: Project ID to filter by
            start: Start time (inclusive)
            end: End time (inclusive)
            consolidation_status: Optional filter ('consolidated', 'unconsolidated', None for all)
            limit: Optional maximum number of events to return

        Returns:
            List of events in time range
        """
        query = """
            SELECT * FROM episodic_events
            WHERE project_id = %s
            AND timestamp >= ?
            AND timestamp <= ?
        """
        params = [project_id, int(start.timestamp()), int(end.timestamp())]

        if consolidation_status:
            if consolidation_status == 'unconsolidated':
                query += " AND (consolidation_status IS NULL OR consolidation_status = 'unconsolidated')"
            else:
                query += " AND consolidation_status = ?"
                params.append(consolidation_status)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = self.execute(query, params, fetch_all=True)

        return [self._row_to_model(row) for row in rows]

    def mark_event_consolidated(
        self,
        event_id: int,
        consolidated_at: Optional[datetime] = None
    ) -> None:
        """Mark an event as consolidated.

        Args:
            event_id: Event ID to mark
            consolidated_at: When consolidation occurred (default: now)
        """
        if consolidated_at is None:
            consolidated_at = datetime.now()

        self.execute(
            """
            UPDATE episodic_events
            SET consolidation_status = 'consolidated',
                consolidated_at = ?
            WHERE id = %s
        """,
            (int(consolidated_at.timestamp()), event_id)
        )

        self.commit()

    def get_event_relations(
        self,
        event_id: int,
        relation_types: Optional[list] = None
    ) -> list:
        """
        Get relations for an event.

        Args:
            event_id: Event ID to get relations for
            relation_types: Filter by specific relation types

        Returns:
            List of relations (from_event_id, to_event_id, relation_type, strength)
        """
        if relation_types:
            placeholders = ','.join('?' * len(relation_types))
            query = f"""
                SELECT from_event_id, to_event_id, relation_type, strength
                FROM event_relations
                WHERE (from_event_id = %s OR to_event_id = %s)
                AND relation_type IN ({placeholders})
            """
            params = [event_id, event_id] + relation_types
        else:
            query = """
                SELECT from_event_id, to_event_id, relation_type, strength
                FROM event_relations
                WHERE from_event_id = %s OR to_event_id = %s
            """
            params = [event_id, event_id]

        rows = self.execute(query, params, fetch_all=True)

        relations = []
        for row in rows:
            relations.append({
                'from_event_id': row['from_event_id'],
                'to_event_id': row['to_event_id'],
                'relation_type': row['relation_type'],
                'strength': row['strength']
            })

        return relations

    def get_related_events(
        self,
        event_id: int,
        relation_type: Optional[str] = None,
        direction: str = 'both'  # 'forward', 'backward', 'both'
    ) -> List[EpisodicEvent]:
        """
        Get events related to a given event.

        Args:
            event_id: Event ID to start from
            relation_type: Optional filter by relation type
            direction: Which direction to traverse ('forward', 'backward', 'both')

        Returns:
            List of related events
        """
        # Build query based on direction
        if direction == 'forward':
            where_clause = "from_event_id = ?"
            event_field = "to_event_id"
        elif direction == 'backward':
            where_clause = "to_event_id = ?"
            event_field = "from_event_id"
        else:  # 'both'
            where_clause = "(from_event_id = ? OR to_event_id = ?)"
            event_field = "CASE WHEN from_event_id = ? THEN to_event_id ELSE from_event_id END"

        if relation_type:
            where_clause += " AND relation_type = ?"

        query = f"""
            SELECT DISTINCT {event_field} as related_id
            FROM event_relations
            WHERE {where_clause}
        """

        # Build params
        if direction == 'both':
            params = [event_id, event_id, event_id]
        else:
            params = [event_id]

        if relation_type:
            params.append(relation_type)

        rows = self.execute(query, params, fetch_all=True)

        # Fetch related events
        related_ids = [row['related_id'] for row in rows]
        related_events = []

        for related_id in related_ids:
            event = self.get_event(related_id)
            if event:
                related_events.append(event)

        return related_events

    def get_event_embedding(self, event_id: int) -> Optional[list[float]]:
        """Get embedding vector for an event.

        Args:
            event_id: Event ID

        Returns:
            768-dimensional embedding vector, or None if not found
        """
        try:
            row = self.execute("""
                SELECT embedding FROM event_vectors WHERE rowid = %s
            """, (event_id,), fetch_one=True)

            if row and row['embedding']:
                return json.loads(row['embedding'])

        except Exception as e:
            import logging
            logging.debug(f"No embedding found for event {event_id}: {e}")

        return None

    def get_high_surprise_events(
        self, project_id: int, threshold: float = 3.5, limit: int = 100
    ) -> List[EpisodicEvent]:
        """Get events with high Bayesian surprise (important event boundaries).

        Used for consolidation clustering - high-surprise events become cluster centers.

        Args:
            project_id: Project ID to filter events
            threshold: Surprise score threshold (default 3.5)
            limit: Maximum events to return (default 100)

        Returns:
            List of high-surprise events, sorted by surprise descending
        """
        rows = self.execute(
            """
            SELECT * FROM episodic_events
            WHERE project_id = %s AND surprise_score IS NOT NULL AND surprise_score > %s
            ORDER BY surprise_score DESC, timestamp DESC
            LIMIT ?
        """,
            (project_id, threshold, limit),
            fetch_all=True
        )

        events = []
        for row in rows:
            try:
                event = self._row_to_model(row)
                events.append(event)
            except Exception as e:
                import logging
                logging.warning(f"Error loading high-surprise event {row['id']}: {e}")

        return events

    # ========================================================================
    # Code-Aware Event Methods
    # ========================================================================

    def create_code_event(
        self,
        project_id: int,
        session_id: str,
        code_event_type: str,
        file_path: str,
        content: str,
        symbol_name: Optional[str] = None,
        symbol_type: Optional[str] = None,
        language: Optional[str] = None,
        diff: Optional[str] = None,
        git_commit: Optional[str] = None,
        git_author: Optional[str] = None,
        outcome: Optional[str] = None,
        code_quality_score: Optional[float] = None,
        **kwargs
    ) -> EpisodicEvent:
        """Create a code-aware episodic event.

        Args:
            project_id: Project ID
            session_id: Session ID
            code_event_type: Type from CodeEventType enum
            file_path: File path (absolute or relative)
            content: Human-readable description
            symbol_name: Function/class name (optional)
            symbol_type: 'function', 'class', 'method', 'module'
            language: Programming language
            diff: Unified diff format
            git_commit: Git commit hash
            git_author: Git author
            outcome: 'success', 'failure', 'partial'
            code_quality_score: Quality rating (0.0-1.0)
            **kwargs: Additional fields (duration_ms, test_passed, error_type, etc.)

        Returns:
            Created EpisodicEvent instance
        """
        from .models import CodeEventType, EventType, EventOutcome

        event = EpisodicEvent(
            project_id=project_id,
            session_id=session_id,
            event_type=EventType.ACTION,
            code_event_type=CodeEventType(code_event_type),
            file_path=file_path,
            symbol_name=symbol_name,
            symbol_type=symbol_type,
            language=language,
            content=content,
            diff=diff,
            git_commit=git_commit,
            git_author=git_author,
            outcome=EventOutcome(outcome) if outcome else None,
            code_quality_score=code_quality_score,
            **kwargs
        )

        # Insert into database
        cursor = self.db.get_cursor()
        perf_metrics_json = json.dumps(event.performance_metrics) if event.performance_metrics else None

        cursor.execute("""
            INSERT INTO episodic_events (
                project_id, session_id, timestamp, event_type, content, outcome,
                context_cwd, context_files, context_task, context_phase, context_branch,
                duration_ms, files_changed, lines_added, lines_deleted, learned, confidence,
                consolidation_status, code_event_type, file_path, symbol_name, symbol_type,
                language, diff, git_commit, git_author, test_name, test_passed,
                error_type, stack_trace, performance_metrics, code_quality_score
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            event.project_id,
            event.session_id,
            int(event.timestamp.timestamp()),
            event.event_type,
            event.content,
            event.outcome,
            event.context.cwd,
            json.dumps(event.context.files),
            event.context.task,
            event.context.phase,
            event.context.branch,
            event.duration_ms,
            event.files_changed,
            event.lines_added,
            event.lines_deleted,
            event.learned,
            event.confidence,
            event.consolidation_status,
            event.code_event_type,
            event.file_path,
            event.symbol_name,
            event.symbol_type,
            event.language,
            event.diff,
            event.git_commit,
            event.git_author,
            event.test_name,
            1 if event.test_passed else (0 if event.test_passed is False else None),
            event.error_type,
            event.stack_trace,
            perf_metrics_json,
            event.code_quality_score,
        ))
        # commit handled by cursor context

        event.id = cursor.lastrowid
        return event

    def list_code_events_by_file(
        self,
        project_id: int,
        file_path: str,
        limit: int = 50
    ) -> list[EpisodicEvent]:
        """List code events for a specific file.

        Args:
            project_id: Project ID
            file_path: File path to filter
            limit: Maximum results

        Returns:
            List of EpisodicEvent instances
        """
        rows = self.execute(
            """
            SELECT * FROM episodic_events
            WHERE project_id = %s AND file_path = %s AND code_event_type IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (project_id, file_path, limit),
            fetch_all=True
        )

        return [self._row_to_model(row) for row in rows]

    def list_code_events_by_symbol(
        self,
        project_id: int,
        symbol_name: str,
        file_path: Optional[str] = None,
        limit: int = 50
    ) -> list[EpisodicEvent]:
        """List code events for a specific symbol (function/class).

        Args:
            project_id: Project ID
            symbol_name: Symbol name
            file_path: Optional file path filter
            limit: Maximum results

        Returns:
            List of EpisodicEvent instances
        """
        if file_path:
            rows = self.execute(
                """
                SELECT * FROM episodic_events
                WHERE project_id = %s AND symbol_name = %s AND file_path = %s
                    AND code_event_type IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (project_id, symbol_name, file_path, limit),
                fetch_all=True
            )
        else:
            rows = self.execute(
                """
                SELECT * FROM episodic_events
                WHERE project_id = %s AND symbol_name = %s AND code_event_type IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (project_id, symbol_name, limit),
                fetch_all=True
            )

        return [self._row_to_model(row) for row in rows]

    def list_code_events_by_type(
        self,
        project_id: int,
        code_event_type: str,
        limit: int = 50
    ) -> list[EpisodicEvent]:
        """List code events by type (CODE_EDIT, BUG_DISCOVERY, etc).

        Args:
            project_id: Project ID
            code_event_type: Code event type string
            limit: Maximum results

        Returns:
            List of EpisodicEvent instances
        """
        rows = self.execute(
            """
            SELECT * FROM episodic_events
            WHERE project_id = %s AND code_event_type = %s
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (project_id, code_event_type, limit),
            fetch_all=True
        )

        return [self._row_to_model(row) for row in rows]

    def list_code_events_by_language(
        self,
        project_id: int,
        language: str,
        limit: int = 50
    ) -> list[EpisodicEvent]:
        """List code events by programming language.

        Args:
            project_id: Project ID
            language: Language name (python, typescript, etc)
            limit: Maximum results

        Returns:
            List of EpisodicEvent instances
        """
        rows = self.execute(
            """
            SELECT * FROM episodic_events
            WHERE project_id = %s AND language = %s AND code_event_type IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (project_id, language, limit),
            fetch_all=True
        )

        return [self._row_to_model(row) for row in rows]

    def list_test_events(
        self,
        project_id: int,
        failed_only: bool = False,
        limit: int = 50
    ) -> list[EpisodicEvent]:
        """List test run events.

        Args:
            project_id: Project ID
            failed_only: Only return failed tests
            limit: Maximum results

        Returns:
            List of EpisodicEvent instances
        """
        if failed_only:
            rows = self.execute(
                """
                SELECT * FROM episodic_events
                WHERE project_id = %s AND test_name IS NOT NULL AND test_passed = 0
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (project_id, limit),
                fetch_all=True
            )
        else:
            rows = self.execute(
                """
                SELECT * FROM episodic_events
                WHERE project_id = %s AND test_name IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (project_id, limit),
                fetch_all=True
            )

        return [self._row_to_model(row) for row in rows]

    def list_bug_events(
        self,
        project_id: int,
        language: Optional[str] = None,
        limit: int = 50
    ) -> list[EpisodicEvent]:
        """List bug discovery events (exceptions, errors).

        Args:
            project_id: Project ID
            language: Optional language filter
            limit: Maximum results

        Returns:
            List of EpisodicEvent instances
        """
        if language:
            rows = self.execute(
                """
                SELECT * FROM episodic_events
                WHERE project_id = %s AND code_event_type = 'bug_discovery' AND language = %s
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (project_id, language, limit),
                fetch_all=True
            )
        else:
            rows = self.execute(
                """
                SELECT * FROM episodic_events
                WHERE project_id = %s AND code_event_type = 'bug_discovery'
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (project_id, limit),
                fetch_all=True
            )

        return [self._row_to_model(row) for row in rows]

    def find_duplicate_events(
        self,
        project_id: int,
        similarity_threshold: float = 0.85,
        time_window_minutes: int = 60,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Find near-duplicate events that can be merged.

        This implements event deduplication using content similarity and temporal
        proximity. Events within time_window_minutes with similarity > threshold
        are candidates for merging.

        Args:
            project_id: Project ID
            similarity_threshold: Minimum similarity score (0-1, default 0.85)
            time_window_minutes: Consider events within this time window (default 60 minutes)
            limit: Maximum events to analyze (default 100)

        Returns:
            Dictionary with:
            - duplicate_groups: List of event groups that are duplicates
            - total_duplicates: Count of duplicate events found
            - merge_opportunities: Count of merge operations that could be done
            - estimated_savings: Estimated reduction in event count after merging
        """
        from datetime import timedelta

        # Get recent events for the project
        events = self.recall_by_timeframe(
            project_id,
            start_time=datetime.now() - timedelta(days=1),
            end_time=datetime.now(),
            limit=limit
        )

        if len(events) < 2:
            return {
                "duplicate_groups": [],
                "total_duplicates": 0,
                "merge_opportunities": 0,
                "estimated_savings": 0,
            }

        duplicate_groups = []
        processed = set()

        # Compare events pairwise
        for i, event1 in enumerate(events):
            if event1.id in processed:
                continue

            group = [event1]

            for j, event2 in enumerate(events[i+1:], i+1):
                if event2.id in processed:
                    continue

                # Check temporal proximity
                if event1.timestamp and event2.timestamp:
                    time_diff = abs((event2.timestamp - event1.timestamp).total_seconds() / 60)
                    if time_diff > time_window_minutes:
                        continue

                # Calculate similarity
                similarity = self._calculate_event_similarity(event1, event2)

                if similarity >= similarity_threshold:
                    group.append(event2)
                    processed.add(event2.id)

            if len(group) > 1:
                duplicate_groups.append(group)
                processed.add(event1.id)

        total_duplicates = sum(len(group) - 1 for group in duplicate_groups)
        merge_opportunities = len(duplicate_groups)
        estimated_savings = total_duplicates  # Can reduce by merging

        return {
            "duplicate_groups": [
                {
                    "ids": [e.id for e in group],
                    "count": len(group),
                    "first_timestamp": min((e.timestamp for e in group if e.timestamp), default=None),
                    "last_timestamp": max((e.timestamp for e in group if e.timestamp), default=None),
                }
                for group in duplicate_groups
            ],
            "total_duplicates": total_duplicates,
            "merge_opportunities": merge_opportunities,
            "estimated_savings": estimated_savings,
        }

    def _calculate_event_similarity(self, event1: EpisodicEvent, event2: EpisodicEvent) -> float:
        """Calculate similarity between two events (0-1 scale).

        Uses multiple signals:
        - Content similarity (string similarity)
        - Event type matching
        - File context matching
        - Outcome matching

        Args:
            event1: First event
            event2: Second event

        Returns:
            Similarity score (0.0 - 1.0)
        """
        import difflib

        if not event1.content or not event2.content:
            return 0.0

        # Content similarity (sequence matcher ratio)
        content_sim = difflib.SequenceMatcher(None, event1.content, event2.content).ratio()

        # Type matching bonus
        type_bonus = 0.15 if event1.event_type == event2.event_type else 0.0

        # File context matching bonus
        file_bonus = 0.0
        if event1.context.files and event2.context.files:
            common_files = set(event1.context.files) & set(event2.context.files)
            if common_files:
                file_bonus = 0.1 * (len(common_files) / max(len(event1.context.files), len(event2.context.files)))

        # Outcome matching bonus
        outcome_bonus = 0.1 if event1.outcome == event2.outcome else 0.0

        # Final weighted similarity
        total_sim = content_sim + type_bonus + file_bonus + outcome_bonus
        return min(1.0, total_sim)

    def merge_duplicate_events(
        self,
        project_id: int,
        primary_event_id: int,
        duplicate_event_ids: list[int],
        keep_duplicate_ids: bool = False
    ) -> Dict[str, Any]:
        """Merge duplicate events into a single event.

        Consolidates near-duplicate events by:
        - Keeping primary event's metadata
        - Aggregating metrics (files changed, lines added/deleted)
        - Combining confidence scores
        - Preserving all unique information

        Args:
            project_id: Project ID
            primary_event_id: Event ID to keep (will contain merged data)
            duplicate_event_ids: Event IDs to merge into primary
            keep_duplicate_ids: If False, delete duplicates after merge (default: False)

        Returns:
            Dictionary with:
            - merged: True if successful
            - primary_event_id: ID of merged event
            - merged_count: Count of events merged
            - aggregated_metrics: Summary of aggregated data
        """
        if not duplicate_event_ids:
            return {
                "merged": False,
                "primary_event_id": primary_event_id,
                "merged_count": 0,
                "aggregated_metrics": {},
            }

        # Get all events
        primary_event = self.get_by_id(primary_event_id)
        if not primary_event:
            return {
                "merged": False,
                "primary_event_id": primary_event_id,
                "error": f"Primary event {primary_event_id} not found",
            }

        duplicate_events = []
        for dup_id in duplicate_event_ids:
            event = self.get_by_id(dup_id)
            if event:
                duplicate_events.append(event)

        if not duplicate_events:
            return {
                "merged": False,
                "primary_event_id": primary_event_id,
                "merged_count": 0,
                "error": "No duplicate events found",
            }

        # Aggregate metrics
        total_files_changed = primary_event.files_changed or 0
        total_lines_added = primary_event.lines_added or 0
        total_lines_deleted = primary_event.lines_deleted or 0
        total_duration_ms = primary_event.duration_ms or 0
        all_files = set(primary_event.context.files) if primary_event.context.files else set()

        confidence_scores = [primary_event.confidence or 1.0]

        for dup_event in duplicate_events:
            total_files_changed += dup_event.files_changed or 0
            total_lines_added += dup_event.lines_added or 0
            total_lines_deleted += dup_event.lines_deleted or 0
            total_duration_ms += dup_event.duration_ms or 0

            if dup_event.context.files:
                all_files.update(dup_event.context.files)

            confidence_scores.append(dup_event.confidence or 1.0)

        # Calculate average confidence (weighted by number of events)
        avg_confidence = sum(confidence_scores) / len(confidence_scores)

        # Update primary event with aggregated data
        self.execute(
            """
            UPDATE episodic_events
            SET files_changed = %s,
                lines_added = %s,
                lines_deleted = %s,
                duration_ms = %s,
                confidence = %s,
                context_files = %s
            WHERE id = %s
            """,
            (
                total_files_changed,
                total_lines_added,
                total_lines_deleted,
                total_duration_ms,
                avg_confidence,
                json.dumps(list(all_files)),
                primary_event_id,
            ),
        )

        # Delete duplicates if requested
        deleted_count = 0
        if not keep_duplicate_ids:
            for dup_id in duplicate_event_ids:
                try:
                    self.delete_event(dup_id)
                    deleted_count += 1
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Could not delete event {dup_id}: {e}")

        return {
            "merged": True,
            "primary_event_id": primary_event_id,
            "merged_count": len(duplicate_events),
            "deleted_count": deleted_count,
            "aggregated_metrics": {
                "files_changed": total_files_changed,
                "lines_added": total_lines_added,
                "lines_deleted": total_lines_deleted,
                "duration_ms": total_duration_ms,
                "avg_confidence": round(avg_confidence, 4),
                "unique_files": len(all_files),
            },
        }

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using llamacpp service.

        Args:
            text: Text to embed

        Returns:
            768-dimensional embedding vector or None if unavailable
        """
        if not text:
            return None

        try:
            import requests
            response = requests.post(
                "http://localhost:8001/embeddings",
                json={"input": text},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                embedding = data.get("embedding")
                if embedding:
                    return embedding
            else:
                import logging
                logging.warning(f"Embedding service returned {response.status_code}: {response.text[:200]}")
        except requests.exceptions.ConnectionError:
            import logging
            logging.warning("Embedding service (llamacpp:8001) is not available - semantic search will fall back to keyword matching")
        except Exception as e:
            # Log but don't fail - embeddings are optional fallback
            import logging
            logging.debug(f"Embedding generation failed: {e}")

        return None

    def store_event(
        self,
        project_id: int,
        content: str,
        event_type: str,
        session_id: str,
        outcome: Optional[str] = None,
        context_cwd: Optional[str] = None,
        context_files: Optional[list] = None,
        context_task: Optional[str] = None,
        context_phase: Optional[str] = None,
        duration_ms: Optional[int] = None,
        learned: Optional[str] = None,
        confidence: float = 1.0,
    ) -> int:
        """Store an event with individual parameters (convenience method).

        This is a wrapper around record_event() for easier integration.

        Args:
            project_id: Project ID
            content: Event content/description
            event_type: Type of event (action, decision, discovery, error)
            session_id: Session ID for grouping related events
            outcome: Outcome of the event (success, failure, unknown)
            context_cwd: Current working directory
            context_files: List of involved files
            context_task: Task being performed
            context_phase: Development phase (design, coding, testing, etc.)
            duration_ms: Duration in milliseconds
            learned: What was learned from this event
            confidence: Confidence score (0.0-1.0)

        Returns:
            ID of stored event
        """
        # Create EpisodicEvent model from parameters
        event = EpisodicEvent(
            project_id=project_id,
            session_id=session_id,
            timestamp=datetime.now(),
            event_type=EventType(event_type) if event_type else EventType.ACTION,
            content=content,
            outcome=EventOutcome(outcome) if outcome else None,
            context=EventContext(
                cwd=context_cwd,
                files=context_files or [],
                task=context_task,
                phase=context_phase,
            ),
            duration_ms=duration_ms,
            learned=learned,
            confidence=confidence,
        )

        return self.record_event(event)

    def list_events(
        self,
        project_id: int,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "timestamp DESC"
    ) -> List[EpisodicEvent]:
        """List events for a project with pagination.

        Args:
            project_id: Project ID
            limit: Maximum events to return
            offset: Offset for pagination
            order_by: Order clause (e.g., 'timestamp DESC')

        Returns:
            List of EpisodicEvent instances
        """
        query = f"""
            SELECT * FROM episodic_events
            WHERE project_id = %s
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
        """

        rows = self.execute(
            query,
            (project_id, limit, offset),
            fetch_all=True
        )

        if not rows:
            return []

        return [self._row_to_model(row) for row in rows]

    def delete_event(self, event_id: int) -> bool:
        """Delete a single event and its associated data.

        Args:
            event_id: Event ID to delete

        Returns:
            True if deleted, False if not found
        """
        cursor = self.execute(
            "DELETE FROM episodic_events WHERE id = %s",
            (event_id,),
            fetch_one=False
        )
        return cursor and cursor.rowcount > 0 if hasattr(cursor, 'rowcount') else False
