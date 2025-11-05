#!/usr/bin/env python3
"""
Spatial-Temporal Integration - Phase 5 Implementation

Integrates spatial hierarchy and temporal chains for enhanced episodic memory.

Provides convenience functions to:
1. Record events with spatial-temporal grounding
2. Query events by spatial location and temporal proximity
3. Analyze causal chains
4. Track project structure evolution

Integration points:
- record_episode.py: Call ground_event() for each episodic event
- inject_context.py: Use spatial_temporal_query() for context retrieval
- hooks: Automatic spatial-temporal grounding at hook recording time
"""

import logging
from typing import Dict, List, Optional, Tuple
from spatial_hierarchy import SpatialStore, SpatialHierarchy
from temporal_chains import TemporalStore, TemporalChain

logger = logging.getLogger("spatial_temporal_integration")


class SpatialTemporalStore:
    """
    Combined spatial and temporal store for enhanced episodic memory queries.

    Enables:
    - "What happened in src/auth?"
    - "What happened after task X?"
    - "What happened in src/auth right after task X?"
    """

    def __init__(self, db_path: str):
        """
        Initialize combined spatial-temporal store.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.spatial = SpatialStore(db_path)
        self.temporal = TemporalStore(db_path)

    def ground_event(self, event_id: int, file_path: str,
                    event_timestamp: int, previous_event_id: Optional[int] = None,
                    previous_timestamp: Optional[int] = None,
                    same_session: bool = True) -> Dict:
        """
        Ground an episodic event in space and time.

        Creates:
        1. Spatial hierarchy for the file path
        2. Links to spatial nodes
        3. Temporal links to previous events

        Args:
            event_id: ID of the episodic event
            file_path: File or directory path where event occurred
            event_timestamp: Unix timestamp of event
            previous_event_id: ID of previous event (for temporal linking)
            previous_timestamp: Timestamp of previous event
            same_session: True if in same session as previous event

        Returns:
            Dict with grounding results and metrics
        """
        result = {
            "event_id": event_id,
            "spatial_nodes_created": 0,
            "temporal_links_created": 0,
            "file_path": file_path
        }

        # 1. Spatial grounding: Create hierarchy and link event
        try:
            spatial_nodes = self.spatial.create_hierarchy(file_path)
            self.spatial.link_event_to_spatial(event_id, file_path)
            result["spatial_nodes_created"] = len(spatial_nodes)
            logger.debug(f"Created {len(spatial_nodes)} spatial nodes for {file_path}")
        except Exception as e:
            logger.error(f"Failed to ground event spatially: {e}")
            result["spatial_error"] = str(e)

        # 2. Temporal grounding: Link to previous events
        if previous_event_id and previous_timestamp and event_timestamp:
            try:
                time_delta = event_timestamp - previous_timestamp

                # Check file overlap (are events in same directory?)
                file_overlap = self._check_file_overlap(
                    self.spatial, file_path, previous_event_id
                )

                link = self.temporal.create_link(
                    from_event_id=previous_event_id,
                    to_event_id=event_id,
                    time_delta_seconds=time_delta,
                    session_same=same_session,
                    file_overlap=file_overlap
                )

                if link:
                    result["temporal_links_created"] = 1
                    result["temporal_link_type"] = link.link_type
                    result["temporal_confidence"] = link.confidence
                    result["temporal_causal_strength"] = link.causal_strength
                    logger.debug(f"Created temporal link: {previous_event_id} → {event_id} ({link.link_type})")

            except Exception as e:
                logger.error(f"Failed to ground event temporally: {e}")
                result["temporal_error"] = str(e)

        return result

    def _check_file_overlap(self, spatial_store: SpatialStore, file_path: str,
                           previous_event_id: int) -> bool:
        """
        Check if file path overlaps with previous event's location.

        Simple heuristic: same directory = overlap.

        Args:
            spatial_store: SpatialStore instance
            file_path: Current event's file path
            previous_event_id: Previous event ID

        Returns:
            True if files are in same directory
        """
        # For now, simple implementation
        # In production, would query spatial store for previous event's location
        return False

    def query_spatial(self, directory_path: str,
                     include_subdirectories: bool = True) -> List[int]:
        """
        Query events in a spatial location.

        Args:
            directory_path: Directory to query
            include_subdirectories: Include subdirectories?

        Returns:
            List of event IDs
        """
        if include_subdirectories:
            return self.spatial.get_events_under_spatial(directory_path)
        else:
            return self.spatial.get_events_in_spatial(directory_path)

    def query_temporal(self, event_id: int, direction: str = "forward",
                      link_type: Optional[str] = None) -> List[Tuple[int, Dict]]:
        """
        Query events linked temporally to an event.

        Args:
            event_id: Source event ID
            direction: "forward" (after) or "backward" (before)
            link_type: Filter by link type

        Returns:
            List of (event_id, link_metadata) tuples
        """
        if direction == "forward":
            chain = self.temporal.get_forward_chain(event_id, link_type)
        else:
            chain = self.temporal.get_backward_chain(event_id, link_type)

        return [(eid, link.to_dict()) for eid, link in chain]

    def query_spatial_temporal(self, directory_path: str, event_id: int,
                              direction: str = "forward",
                              include_subdirectories: bool = True) -> List[int]:
        """
        Query events in both space and time.

        Intersection of:
        - Events in spatial location
        - Events temporally linked to event_id

        Args:
            directory_path: Directory to filter by
            event_id: Temporal anchor event
            direction: "forward" or "backward"
            include_subdirectories: Include subdirectories?

        Returns:
            List of event IDs matching both criteria
        """
        spatial_events = set(self.query_spatial(
            directory_path, include_subdirectories
        ))

        temporal_chain = self.query_temporal(event_id, direction)
        temporal_events = set(eid for eid, _ in temporal_chain)

        # Return intersection
        return list(spatial_events.intersection(temporal_events))

    def get_grounding_stats(self) -> Dict:
        """
        Get statistics about spatial-temporal grounding.

        Returns:
            Dict with statistics
        """
        return {
            "temporal_chains": self.temporal.get_chain_stats()
        }

    def close(self):
        """Close connections."""
        self.spatial.close()
        self.temporal.close()


def example_usage():
    """
    Example usage of spatial-temporal integration.
    """
    print("""
    # Example 1: Ground a series of events
    store = SpatialTemporalStore("/home/user/.claude/memory.db")

    # Event 1: Started task in src/auth
    store.ground_event(
        event_id=1,
        file_path="/home/user/project/src/auth/jwt.py",
        event_timestamp=1672502400  # Jan 1, 2023 10:00 UTC
    )

    # Event 2: Added feature (4 minutes later, same file)
    store.ground_event(
        event_id=2,
        file_path="/home/user/project/src/auth/jwt.py",
        event_timestamp=1672502640,  # 10:04 UTC
        previous_event_id=1,
        previous_timestamp=1672502400
    )

    # Event 3: Code review (45 minutes later, different directory)
    store.ground_event(
        event_id=3,
        file_path="/home/user/project/tests/test_auth.py",
        event_timestamp=1672505040,  # 10:50 UTC
        previous_event_id=2,
        previous_timestamp=1672502640
    )

    # Queries
    # "What happened in src/auth?"
    events_in_auth = store.query_spatial("/home/user/project/src/auth")
    # → [1, 2] (events 1 and 2 occurred in src/auth)

    # "What happened after event 1?"
    after_event_1 = store.query_temporal(1, direction="forward")
    # → [(2, link_metadata), (3, link_metadata)]

    # "What happened in src/auth after event 1?"
    in_auth_after_1 = store.query_spatial_temporal(
        "/home/user/project/src/auth", 1, direction="forward"
    )
    # → [2] (event 2 is in src/auth and after event 1)

    store.close()
    """)


if __name__ == "__main__":
    example_usage()
