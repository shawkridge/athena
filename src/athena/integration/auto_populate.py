"""Automatic population of spatial and temporal layers from episodic events.

This module provides integration between memory layers, automatically:
- Building spatial hierarchy from event file contexts
- Creating temporal chains from event sequences
- Updating procedural patterns from workflows
"""

import logging
from datetime import datetime
from typing import Optional

from ..core.database import Database
from ..episodic.models import EpisodicEvent
from ..episodic.store import EpisodicStore
from ..spatial.hierarchy import build_spatial_hierarchy, extract_spatial_relations
from ..spatial.store import SpatialStore
from ..temporal.chains import create_temporal_relations

logger = logging.getLogger(__name__)


def auto_populate_spatial(
    event: EpisodicEvent, spatial_store: SpatialStore, project_id: int
) -> int:
    """
    Automatically build spatial hierarchy from event context.

    Extracts file paths from event context and builds spatial nodes
    and relations in the spatial store. Uses batch operations for performance.

    Args:
        event: Episodic event with context
        spatial_store: Spatial store instance
        project_id: Project ID

    Returns:
        Number of spatial nodes created
    """
    if not event.context or not event.context.files:
        # Also check context.cwd for spatial context
        if event.context and event.context.cwd:
            paths = [event.context.cwd]
        else:
            return 0
    else:
        paths = event.context.files.copy()
        if event.context.cwd:
            paths.append(event.context.cwd)

    all_nodes = []

    # Build spatial nodes for each file path
    for file_path in paths:
        try:
            nodes = build_spatial_hierarchy(file_path)
            all_nodes.extend(nodes)
        except Exception as e:
            logger.warning(f"Failed to build spatial hierarchy for {file_path}: {e}")

    # Batch store all nodes in a single transaction (optimized)
    nodes_created = 0
    if all_nodes:
        try:
            nodes_created = spatial_store.batch_store_nodes(project_id, all_nodes)
            logger.debug(f"Batch-stored {nodes_created} spatial nodes")
        except Exception as e:
            logger.warning(f"Failed to batch-store spatial nodes: {e}")

    # Extract and batch store spatial relations (optimized)
    if all_nodes:
        try:
            relations = extract_spatial_relations(all_nodes)
            if relations:
                relations_stored = spatial_store.batch_store_relations(project_id, relations)
                logger.debug(f"Batch-stored {relations_stored} spatial relations")
        except Exception as e:
            logger.warning(f"Failed to batch-store spatial relations: {e}")

    return nodes_created


def auto_populate_temporal(
    episodic_store: EpisodicStore, project_id: int, hours_lookback: int = 24, min_events: int = 2
) -> int:
    """
    Automatically create temporal relations from recent events.

    Analyzes recent events and creates temporal relations between
    consecutive events.

    Args:
        episodic_store: Episodic store instance
        project_id: Project ID
        hours_lookback: How many hours back to analyze
        min_events: Minimum events needed to create relations

    Returns:
        Number of temporal relations created
    """
    # Get recent events
    recent_events = episodic_store.get_recent_events(
        project_id=project_id, hours=hours_lookback, limit=1000
    )

    if len(recent_events) < min_events:
        logger.debug(f"Not enough events ({len(recent_events)}) to create temporal relations")
        return 0

    # Create temporal relations
    relations = create_temporal_relations(recent_events)

    # Store relations in episodic store
    relations_created = 0
    for relation in relations:
        try:
            episodic_store.create_event_relation(
                from_event_id=relation.from_event_id,
                to_event_id=relation.to_event_id,
                relation_type=relation.relation_type,
                strength=relation.strength,
            )
            relations_created += 1
        except Exception as e:
            # Relation might already exist
            logger.debug(f"Temporal relation already exists or error: {e}")

    return relations_created


class IntegratedEpisodicStore:
    """
    Wrapper around EpisodicStore that automatically populates other layers.

    When events are recorded, this automatically:
    - Builds spatial hierarchy from file contexts
    - Creates temporal relations (periodically)
    """

    def __init__(
        self,
        db: Database,
        spatial_store: Optional[SpatialStore] = None,
        auto_spatial: bool = True,
        auto_temporal: bool = True,
        temporal_batch_size: int = 10,
        spatial_batch_size: int = 50,  # NEW: batch size for spatial processing
    ):
        """
        Initialize integrated episodic store.

        Args:
            db: Database instance
            spatial_store: Spatial store instance (created if None)
            auto_spatial: Enable automatic spatial hierarchy building
            auto_temporal: Enable automatic temporal chain creation
            temporal_batch_size: Create temporal relations every N events
            spatial_batch_size: Batch spatial processing every N events
        """
        self.episodic_store = EpisodicStore(db)
        self.spatial_store = spatial_store or SpatialStore(db)

        self.auto_spatial = auto_spatial
        self.auto_temporal = auto_temporal
        self.temporal_batch_size = temporal_batch_size
        self.spatial_batch_size = spatial_batch_size

        # Track events for batch temporal processing
        self._event_count = 0
        self._last_temporal_update = datetime.now()

        # Track events for batch spatial processing
        self._batch_events = []
        self._current_project_id = None

    def _flush_spatial_batch(self, project_id: int) -> int:
        """Flush accumulated spatial hierarchy updates."""
        if not self._batch_events:
            return 0

        nodes_created = 0
        try:
            # Combine spatial hierarchy from all events in batch
            all_nodes = []
            for event in self._batch_events:
                if not event.context or not event.context.files:
                    if event.context and event.context.cwd:
                        paths = [event.context.cwd]
                    else:
                        continue
                else:
                    paths = event.context.files.copy()
                    if event.context.cwd:
                        paths.append(event.context.cwd)

                for file_path in paths:
                    try:
                        nodes = build_spatial_hierarchy(file_path)
                        all_nodes.extend(nodes)
                    except Exception as e:
                        logger.warning(f"Failed to build spatial hierarchy for {file_path}: {e}")

            # Batch store all nodes
            if all_nodes:
                nodes_created = self.spatial_store.batch_store_nodes(project_id, all_nodes)
                logger.debug(
                    f"Batch-stored {nodes_created} spatial nodes from {len(self._batch_events)} events"
                )

            # Extract and batch store relations
            if all_nodes:
                relations = extract_spatial_relations(all_nodes)
                if relations:
                    relations_stored = self.spatial_store.batch_store_relations(
                        project_id, relations
                    )
                    logger.debug(f"Batch-stored {relations_stored} spatial relations")

        except Exception as e:
            logger.warning(f"Failed to flush spatial batch: {e}")
        finally:
            self._batch_events = []

        return nodes_created

    def record_event(self, event: EpisodicEvent, project_id: Optional[int] = None) -> int:
        """
        Record event and automatically populate spatial/temporal layers (with batching).

        Args:
            event: Event to record
            project_id: Project ID (uses event.project_id if None)

        Returns:
            Event ID
        """
        # Record the event
        event_id = self.episodic_store.record_event(event)

        proj_id = project_id or event.project_id
        self._current_project_id = proj_id

        # Auto-populate spatial hierarchy (batched)
        if self.auto_spatial:
            self._batch_events.append(event)

            # Flush batch every N events
            if len(self._batch_events) >= self.spatial_batch_size:
                self._flush_spatial_batch(proj_id)

        # Auto-populate temporal relations (batched)
        if self.auto_temporal:
            self._event_count += 1

            # Trigger temporal update every N events or every hour
            should_update = (
                self._event_count >= self.temporal_batch_size
                or (datetime.now() - self._last_temporal_update).total_seconds() > 3600
            )

            if should_update:
                try:
                    relations_created = auto_populate_temporal(
                        episodic_store=self.episodic_store, project_id=proj_id, hours_lookback=24
                    )
                    logger.debug(f"Auto-created {relations_created} temporal relations")

                    self._event_count = 0
                    self._last_temporal_update = datetime.now()
                except Exception as e:
                    logger.warning(f"Failed to auto-populate temporal relations: {e}")

        return event_id

    def flush(self, project_id: Optional[int] = None):
        """Flush any pending batched operations."""
        if self.auto_spatial and self._batch_events:
            proj_id = project_id or self._current_project_id
            if proj_id:
                self._flush_spatial_batch(proj_id)

    def __getattr__(self, name):
        """Delegate all other methods to underlying episodic store."""
        return getattr(self.episodic_store, name)
