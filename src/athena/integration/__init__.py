"""Integration layer for automatic memory population."""

from .auto_populate import (
    IntegratedEpisodicStore,
    auto_populate_spatial,
    auto_populate_temporal,
)

__all__ = [
    "IntegratedEpisodicStore",
    "auto_populate_spatial",
    "auto_populate_temporal",
]
