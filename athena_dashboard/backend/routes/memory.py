"""
Memory layer endpoints - One endpoint per layer.

Each endpoint returns real data from Athena memory system:
- Current count/size from actual storage
- Recent activity from episodic events
- Health/quality metrics from meta-memory
- Simplified data for dashboard display

All endpoints are async and use the Athena API.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from athena_connector import (
    get_episodic_stats,
    get_semantic_stats,
    get_procedural_stats,
    get_prospective_stats,
    get_graph_stats,
    get_meta_stats,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/episodic")
async def get_episodic_memory():
    """Episodic memory - Events with spatial-temporal grounding."""
    return await get_episodic_stats()


@router.get("/semantic")
async def get_semantic_memory():
    """Semantic memory - Learned facts and insights."""
    return await get_semantic_stats()


@router.get("/procedural")
async def get_procedural_memory():
    """Procedural memory - Reusable workflows and procedures."""
    return await get_procedural_stats()


@router.get("/prospective")
async def get_prospective_memory():
    """Prospective memory - Tasks, goals, and future-oriented items."""
    return await get_prospective_stats()


@router.get("/graph")
async def get_knowledge_graph():
    """Knowledge graph - Entities, relationships, and communities."""
    return await get_graph_stats()


@router.get("/meta")
async def get_meta_memory():
    """Meta-memory - Quality tracking, attention, and cognitive load."""
    return await get_meta_stats()
