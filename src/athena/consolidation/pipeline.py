"""Episodic→Semantic consolidation pipeline.

This module implements sleep-like memory consolidation inspired by
complementary learning systems theory (Larimar, ICML 2024).

The pipeline:
1. Fetches unconsolidated episodic events
2. Clusters related events by session and spatial context
3. Extracts patterns using LLM (Claude)
4. Stores patterns as semantic memories
5. Marks events as consolidated

This is the signature feature that distinguishes this system from
all production memory systems (Mem0, Letta).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from .clustering import cluster_events_by_context
from .pattern_extraction import extract_patterns, Pattern
from .run_history import ConsolidationRunHistory, ConsolidationRunMetrics, ConsolidationStatus
from ..episodic.models import EpisodicEvent
from ..episodic.store import EpisodicStore
from ..memory.store import MemoryStore
from ..graph.store import GraphStore
from ..temporal.kg_synthesis import TemporalKGSynthesis


@dataclass
class ConsolidationReport:
    """Report from consolidation run."""

    run_id: int
    project_id: int
    started_at: datetime
    completed_at: datetime

    # What was done
    events_processed: int
    events_consolidated: int
    patterns_extracted: int

    # Quality metrics
    quality_before: float
    quality_after: float
    quality_improvement: float

    # Pattern details
    patterns: List[Pattern]

    @property
    def duration_seconds(self) -> float:
        """Calculate consolidation duration."""
        return (self.completed_at - self.started_at).total_seconds()

    def __str__(self) -> str:
        return (
            f"ConsolidationReport("
            f"patterns={self.patterns_extracted}, "
            f"events={self.events_consolidated}, "
            f"quality_improvement={self.quality_improvement:.2%})"
        )


def consolidate_episodic_to_semantic(
    project_id: int,
    episodic_store: EpisodicStore,
    semantic_store: MemoryStore,
    graph_store: Optional[GraphStore] = None,
    time_window_hours: int = 24,
    min_pattern_confidence: float = 0.7,
    dry_run: bool = False,
    database: Optional[object] = None  # Optional Database instance for run tracking
) -> ConsolidationReport:
    """
    Consolidate episodic events into semantic patterns and update knowledge graph.

    This is the core consolidation algorithm that transforms specific
    episodic memories (events) into generalized semantic knowledge (patterns),
    and synthe sizes temporal knowledge graph relations from event causality.

    Pipeline:
    1. Fetch unconsolidated episodic events
    2. Cluster related events by context
    3. Extract patterns using LLM
    4. Store patterns as semantic memories
    5. Mark events as consolidated
    6. Synthesize temporal KG (create entity relations from events)
    7. Calculate quality metrics

    Args:
        project_id: Project to consolidate
        episodic_store: Episodic memory store
        semantic_store: Semantic memory store
        graph_store: Optional knowledge graph store (enables temporal KG synthesis)
        time_window_hours: How far back to look for events
        min_pattern_confidence: Minimum confidence to store pattern
        dry_run: If True, don't actually store patterns or mark events
        database: Optional Database instance for recording consolidation runs

    Returns:
        ConsolidationReport with results

    Algorithm inspired by:
    - Larimar (Das et al. 2024, ICML): Complementary learning systems
    - Memory3 (2024): Explicit memory as third form
    - Zep (arXiv:2501.13956): Temporal knowledge graphs for infinite context
    - Compression = Intelligence (HN consensus): Lossy compression for generalization
    """
    started_at = datetime.now()
    run_id = None

    # Create run record if database available
    if database and not dry_run:
        try:
            run_history = ConsolidationRunHistory(database)
            run_id = run_history.create_run(project_id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create consolidation run record: {e}")

    # Step 1: Fetch unconsolidated events
    cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
    events = episodic_store.get_events_by_timeframe(
        project_id=project_id,
        start=cutoff_time,
        end=datetime.now(),
        consolidation_status='unconsolidated'
    )

    if not events:
        # No events to consolidate
        return ConsolidationReport(
            run_id=0,
            project_id=project_id,
            started_at=started_at,
            completed_at=datetime.now(),
            events_processed=0,
            events_consolidated=0,
            patterns_extracted=0,
            quality_before=0.0,
            quality_after=0.0,
            quality_improvement=0.0,
            patterns=[]
        )

    # Step 2: Cluster related events
    event_clusters = cluster_events_by_context(events)

    # Step 3: Extract patterns from clusters
    all_patterns: List[Pattern] = []

    for cluster in event_clusters:
        if len(cluster) < 2:
            # Skip single-event clusters (no pattern to extract)
            continue

        try:
            patterns = extract_patterns(
                event_cluster=cluster,
                use_llm=True,
                min_confidence=min_pattern_confidence
            )

            all_patterns.extend(patterns)

        except Exception as e:
            # Log error but continue with other clusters
            print(f"Warning: Pattern extraction failed for cluster: {e}")
            continue

    # Step 4: Calculate quality metrics
    quality_before = _calculate_memory_quality(semantic_store, project_id)

    # Step 5: Store patterns as semantic memories (unless dry run)
    stored_pattern_ids = []

    if not dry_run:
        for pattern in all_patterns:
            try:
                # Add consolidation metadata as tags
                enriched_tags = (pattern.tags or []) + [
                    'consolidation',
                    f'confidence:{pattern.confidence:.2f}'
                ]

                memory_id = semantic_store.remember(
                    content=pattern.description,
                    memory_type=pattern.type,
                    project_id=project_id,
                    tags=enriched_tags
                )
                stored_pattern_ids.append(memory_id)

            except Exception as e:
                print(f"Warning: Failed to store pattern: {e}")
                continue

    # Step 6: Mark events as consolidated
    if not dry_run:
        for event in events:
            episodic_store.mark_event_consolidated(
                event_id=event.id,
                consolidated_at=datetime.now()
            )

    # Step 6.5: Synthesize Temporal Knowledge Graph (create relations from episodic events)
    kg_relations_count = 0
    if graph_store and not dry_run:
        try:
            synthesis = TemporalKGSynthesis(
                episodic_store=episodic_store,
                graph_store=graph_store,
                causality_threshold=0.5,
                recency_decay_hours=1.0,
                frequency_threshold=10
            )

            # Get first event's session ID to synthesize that session
            if events:
                session_id = events[0].session_id or f"project_{project_id}"
                result = synthesis.synthesize(session_id=session_id)
                kg_relations_count = result.relations_count

        except Exception as e:
            print(f"Warning: Temporal KG synthesis failed: {e}")
            # Continue with consolidation even if KG synthesis fails

    # Step 7: Calculate quality after consolidation
    quality_after = _calculate_memory_quality(semantic_store, project_id)
    quality_improvement = quality_after - quality_before

    # Step 8: Record consolidation run metrics
    completed_at = datetime.now()

    # Update run record with metrics
    if database and run_id and not dry_run:
        try:
            run_history = ConsolidationRunHistory(database)
            metrics = ConsolidationRunMetrics(
                run_id=run_id,
                project_id=project_id,
                started_at=started_at,
                completed_at=completed_at,
                status=ConsolidationStatus.SUCCESS,
                events_processed=len(events),
                events_consolidated=len(events),
                patterns_extracted=len(stored_pattern_ids),
                patterns_validated=len([p for p in all_patterns if p.confidence >= min_pattern_confidence]),
                memories_created=len(stored_pattern_ids),
                quality_before=quality_before,
                quality_after=quality_after,
                throughput_events_per_sec=len(events) / max(completed_at.timestamp() - started_at.timestamp(), 0.001),
                avg_pattern_confidence=sum(p.confidence for p in all_patterns) / max(len(all_patterns), 1),
            )
            run_history.update_run(run_id, metrics)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to update consolidation run {run_id} with metrics: {e}")

    return ConsolidationReport(
        run_id=run_id or 0,
        project_id=project_id,
        started_at=started_at,
        completed_at=completed_at,
        events_processed=len(events),
        events_consolidated=len(events) if not dry_run else 0,
        patterns_extracted=len(stored_pattern_ids) if not dry_run else len(all_patterns),
        quality_before=quality_before,
        quality_after=quality_after,
        quality_improvement=quality_improvement,
        patterns=all_patterns
    )


def _calculate_memory_quality(semantic_store: MemoryStore, project_id: int) -> float:
    """
    Calculate overall memory quality score.

    Quality is based on:
    - Average usefulness score
    - Recency (newer memories weighted higher)
    - Coverage (diversity of memories)

    Returns:
        Quality score between 0.0 and 1.0
    """
    try:
        memories = semantic_store.get_all_memories(project_id)

        if not memories:
            return 0.0

        # Calculate average usefulness
        avg_usefulness = sum(m.usefulness_score for m in memories) / len(memories)

        # Calculate recency factor (favor recent memories)
        now = datetime.now()
        recency_scores = []
        for memory in memories:
            days_old = (now - memory.created_at).days
            recency = max(0.0, 1.0 - (days_old / 365))  # Decay over 1 year
            recency_scores.append(recency)

        avg_recency = sum(recency_scores) / len(recency_scores) if recency_scores else 0.0

        # Calculate coverage (tag diversity)
        all_tags = set()
        for memory in memories:
            all_tags.update(memory.tags)

        coverage_score = min(1.0, len(all_tags) / 20)  # Target: 20+ diverse tags

        # Composite quality score
        quality = (
            0.5 * avg_usefulness +
            0.3 * avg_recency +
            0.2 * coverage_score
        )

        return quality

    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return 0.0


# Background consolidation daemon

async def consolidation_daemon(
    episodic_store: EpisodicStore,
    semantic_store: MemoryStore,
    interval_hours: int = 24
):
    """
    Background service that runs consolidation periodically.

    Mimics sleep consolidation in human brain - runs once per day.

    Args:
        episodic_store: Episodic memory store
        semantic_store: Semantic memory store
        interval_hours: How often to run (default: 24 hours)
    """
    import asyncio

    while True:
        try:
            # Get all projects
            projects = semantic_store.project_manager.list_all_projects()

            for project in projects:
                try:
                    report = consolidate_episodic_to_semantic(
                        project_id=project.id,
                        episodic_store=episodic_store,
                        semantic_store=semantic_store,
                        time_window_hours=24
                    )

                    print(f"Consolidated {project.name}: {report}")

                except Exception as e:
                    print(f"Error consolidating project {project.name}: {e}")
                    continue

        except Exception as e:
            print(f"Error in consolidation daemon: {e}")

        finally:
            # Wait for next consolidation cycle
            await asyncio.sleep(interval_hours * 3600)
