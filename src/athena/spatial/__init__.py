"""Spatial hierarchy for location-aware episodic memory.

Implements cognitive mapping inspired by hippocampal place cells.
Enables two-stage retrieval: spatial filtering then semantic search.
"""

from .hierarchy import (
    build_spatial_hierarchy,
    calculate_spatial_distance,
    extract_spatial_relations,
    get_ancestors,
    get_parent_path,
    get_spatial_neighbors,
)
from .models import (
    SpatialNode,
    SpatialQuery,
    SpatialQueryResult,
    SpatialRelation,
)
from .retrieval import query_episodic_spatial
from .store import SpatialStore

__all__ = [
    # Models
    "SpatialNode",
    "SpatialRelation",
    "SpatialQuery",
    "SpatialQueryResult",
    # Store
    "SpatialStore",
    # Hierarchy
    "build_spatial_hierarchy",
    "extract_spatial_relations",
    "calculate_spatial_distance",
    "get_spatial_neighbors",
    "get_parent_path",
    "get_ancestors",
    # Retrieval
    "query_episodic_spatial",
]
