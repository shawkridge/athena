"""Enhanced consolidation pipeline with local LLM reasoning.

Extends the standard consolidation pipeline to use local Qwen2.5-7B reasoning
alongside existing heuristics, with optional Claude validation.

This module shows the integration pattern for using LocalLLMClient in the
consolidation pipeline.

Usage:
    # Standard pipeline (existing)
    report = consolidate_episodic_to_semantic(
        project_id=1,
        episodic_store=episodic_store,
        semantic_store=semantic_store
    )

    # Enhanced with local reasoning
    report = consolidate_with_local_reasoning(
        project_id=1,
        episodic_store=episodic_store,
        semantic_store=semantic_store,
        use_local_reasoning=True,
        use_claude_validation=False,
        enable_compression=True
    )
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from .clustering import cluster_events_by_context
from .pattern_extraction import extract_patterns, Pattern
from .local_reasoning import (
    LocalConsolidationReasoner,
    ConsolidationWithDualProcess,
)
from .pipeline import (
    ConsolidationReport,
    _calculate_memory_quality,
)
from ..core.llm_client import LocalLLMClient
from ..episodic.store import EpisodicStore
from ..memory.store import MemoryStore
from ..graph.store import GraphStore
from ..monitoring.model_metrics import get_monitor
from ..temporal.kg_synthesis import TemporalKGSynthesis
from ..evaluation.token_tracking import (
    ConsolidationTokenMetrics,
)

logger = logging.getLogger(__name__)


@dataclass
class EnhancedConsolidationReport(ConsolidationReport):
    """Consolidation report with local reasoning and token optimization metrics."""

    # Local reasoning metrics
    used_local_reasoning: bool = False
    local_patterns_extracted: int = 0
    local_reasoning_latency_ms: float = 0.0
    compression_tokens_saved: int = 0
    dual_process_confidence: float = 0.0

    # Claude validation metrics (if enabled)
    used_claude_validation: bool = False
    claude_validations: int = 0

    # Token metrics (Phase 4)
    token_metrics: Optional[ConsolidationTokenMetrics] = None

    # Cost analysis (legacy, computed from token_metrics if available)
    estimated_claude_tokens_saved: int = 0
    cost_savings_percent: float = 0.0

    def __str__(self) -> str:
        base = super().__str__()
        if self.used_local_reasoning:
            parts = [
                f"{base} | local={self.local_patterns_extracted}, "
                f"confidence={self.dual_process_confidence:.2%}, "
                f"saved={self.compression_tokens_saved} tokens"
            ]

            # Add token metrics if available
            if self.token_metrics:
                parts.append(
                    f" | tokens: {self.token_metrics.compression_percentage:.1f}% compression"
                )
                if self.token_metrics.cache_result:
                    cache_str = "HIT" if self.token_metrics.cache_result.cache_hit else "MISS"
                    parts.append(f", cache {cache_str}")

            return "".join(parts)
        return base


async def consolidate_with_local_reasoning(
    project_id: int,
    episodic_store: EpisodicStore,
    semantic_store: MemoryStore,
    graph_store: Optional[GraphStore] = None,
    time_window_hours: int = 24,
    min_pattern_confidence: float = 0.7,
    use_local_reasoning: bool = True,
    use_claude_validation: bool = False,
    enable_compression: bool = True,
    dry_run: bool = False,
) -> EnhancedConsolidationReport:
    """
    Consolidate episodic events with local reasoning (Qwen2.5-7B).

    Enhances the standard consolidation pipeline by:
    1. Using local reasoning (System 2) for complex pattern extraction
    2. Optionally compressing prompts before Claude validation
    3. Tracking all metrics (latency, tokens saved, confidence)

    Pipeline:
    1. Fetch unconsolidated events (same as standard)
    2. Cluster events by context (same as standard)
    3. Extract patterns:
       a. Fast heuristics (System 1)
       b. Local reasoning (Qwen2.5-7B, System 2) - NEW
       c. Claude validation (optional) - NEW
    4. Store patterns (same as standard)
    5. Mark events consolidated (same as standard)
    6. Calculate quality metrics (same as standard)

    Args:
        project_id: Project to consolidate
        episodic_store: Episodic memory store
        semantic_store: Semantic memory store
        graph_store: Optional knowledge graph store
        time_window_hours: How far back to look
        min_pattern_confidence: Minimum confidence threshold
        use_local_reasoning: Use Qwen2.5-7B for pattern extraction
        use_claude_validation: Use Claude to validate local patterns
        enable_compression: Compress prompts before Claude
        dry_run: Don't store results

    Returns:
        EnhancedConsolidationReport with detailed metrics
    """
    started_at = datetime.now()
    monitor = get_monitor()

    # Initialize local reasoning if requested
    local_reasoner = None
    dual_processor = None

    if use_local_reasoning:
        try:
            llm_client = LocalLLMClient(enable_compression=enable_compression)

            # Check health
            health = await llm_client.check_health()
            if not health.get("embedding") or not health.get("reasoning"):
                logger.warning("Local LLM services not healthy, falling back to standard pipeline")
                use_local_reasoning = False
            else:
                local_reasoner = LocalConsolidationReasoner(
                    llm_client=llm_client, enable_compression=enable_compression
                )
                dual_processor = ConsolidationWithDualProcess(local_reasoner=local_reasoner)
                logger.info("Local reasoning enabled")

        except Exception as e:
            logger.warning(f"Failed to initialize local reasoning: {e}, falling back")
            use_local_reasoning = False

    # Step 1: Fetch unconsolidated events
    cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
    events = episodic_store.get_events_by_timeframe(
        project_id=project_id,
        start=cutoff_time,
        end=datetime.now(),
        consolidation_status="unconsolidated",
    )

    if not events:
        return EnhancedConsolidationReport(
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
            patterns=[],
            used_local_reasoning=use_local_reasoning,
        )

    # Step 2: Cluster events
    event_clusters = cluster_events_by_context(events)

    # Step 3: Extract patterns (with local reasoning if enabled)
    all_patterns: List[Pattern] = []
    local_pattern_count = 0
    total_compression_savings = 0
    total_dual_confidence = 0.0
    dual_process_count = 0

    for cluster_idx, cluster in enumerate(event_clusters):
        if len(cluster) < 2:
            continue

        logger.info(
            f"Processing cluster {cluster_idx + 1}/{len(event_clusters)} "
            f"({len(cluster)} events)"
        )

        try:
            if use_local_reasoning and dual_processor:
                # Use dual-process reasoning
                system_1_patterns = extract_patterns(
                    event_cluster=cluster, use_llm=False, min_confidence=0.0
                )

                dual_result = await dual_processor.extract_patterns_dual_process(
                    event_cluster=cluster,
                    system_1_patterns=system_1_patterns,
                    use_local=True,
                    use_claude_validation=use_claude_validation,
                )

                all_patterns.extend(dual_result.patterns)
                local_pattern_count += len(dual_result.local_patterns)
                total_compression_savings += int(dual_result.cost_saved_percent * 100)
                total_dual_confidence += dual_result.validation_score
                dual_process_count += 1

                logger.info(
                    f"Dual-process extracted {len(dual_result.patterns)} patterns "
                    f"(confidence: {dual_result.validation_score:.2%}, "
                    f"latency: {dual_result.total_latency_ms:.1f}ms)"
                )

            else:
                # Standard extraction (System 1 only)
                patterns = extract_patterns(
                    event_cluster=cluster,
                    use_llm=True,
                    min_confidence=min_pattern_confidence,
                )
                all_patterns.extend(patterns)

        except Exception as e:
            logger.error(f"Pattern extraction failed for cluster {cluster_idx}: {e}")
            continue

    # Step 4: Calculate quality metrics
    quality_before = _calculate_memory_quality(semantic_store, project_id)

    # Step 5: Store patterns (unless dry run)
    stored_pattern_ids = []

    if not dry_run:
        for pattern in all_patterns:
            try:
                # Add consolidation metadata
                enriched_tags = (pattern.tags or []) + [
                    "consolidation",
                    f"confidence:{pattern.confidence:.2f}",
                ]

                if use_local_reasoning:
                    enriched_tags.append("local_reasoning")

                memory_id = semantic_store.remember(
                    content=pattern.description,
                    memory_type=pattern.type,
                    project_id=project_id,
                    tags=enriched_tags,
                )
                stored_pattern_ids.append(memory_id)

            except Exception as e:
                logger.error(f"Failed to store pattern: {e}")
                continue

    # Step 6: Mark events as consolidated
    if not dry_run:
        for event in events:
            episodic_store.mark_event_consolidated(
                event_id=event.id, consolidated_at=datetime.now()
            )

    # Step 7: Temporal KG synthesis
    kg_relations_count = 0
    if graph_store and not dry_run:
        try:
            synthesis = TemporalKGSynthesis(
                episodic_store=episodic_store,
                graph_store=graph_store,
                causality_threshold=0.5,
                recency_decay_hours=1.0,
                frequency_threshold=10,
            )

            if events:
                session_id = events[0].session_id or f"project_{project_id}"
                result = synthesis.synthesize(session_id=session_id)
                kg_relations_count = result.relations_count

        except Exception as e:
            logger.error(f"Temporal KG synthesis failed: {e}")

    # Step 8: Calculate quality after
    quality_after = _calculate_memory_quality(semantic_store, project_id)
    quality_improvement = quality_after - quality_before

    # Step 9: Calculate metrics
    avg_dual_confidence = (
        total_dual_confidence / dual_process_count if dual_process_count > 0 else 0.0
    )

    estimated_savings = (
        int(total_compression_savings / max(dual_process_count, 1)) if dual_process_count > 0 else 0
    )

    completed_at = datetime.now()

    report = EnhancedConsolidationReport(
        run_id=0,
        project_id=project_id,
        started_at=started_at,
        completed_at=completed_at,
        events_processed=len(events),
        events_consolidated=len(events) if not dry_run else 0,
        patterns_extracted=len(stored_pattern_ids) if not dry_run else len(all_patterns),
        quality_before=quality_before,
        quality_after=quality_after,
        quality_improvement=quality_improvement,
        patterns=all_patterns,
        # Enhanced metrics
        used_local_reasoning=use_local_reasoning,
        local_patterns_extracted=local_pattern_count,
        local_reasoning_latency_ms=0.0,  # TODO: Aggregate from dual processor
        compression_tokens_saved=estimated_savings,
        dual_process_confidence=avg_dual_confidence,
        used_claude_validation=use_claude_validation,
        estimated_claude_tokens_saved=estimated_savings,
        cost_savings_percent=(estimated_savings / 10000) * 100 if estimated_savings > 0 else 0.0,
    )

    logger.info(f"Consolidation complete: {report}")

    return report


# Synchronous wrapper for existing code
def consolidate_with_local_reasoning_sync(
    project_id: int,
    episodic_store: EpisodicStore,
    semantic_store: MemoryStore,
    graph_store: Optional[GraphStore] = None,
    time_window_hours: int = 24,
    min_pattern_confidence: float = 0.7,
    use_local_reasoning: bool = True,
    use_claude_validation: bool = False,
    enable_compression: bool = True,
    dry_run: bool = False,
) -> EnhancedConsolidationReport:
    """Synchronous wrapper for consolidate_with_local_reasoning.

    For use in code that doesn't support async yet.

    Args:
        (same as consolidate_with_local_reasoning)

    Returns:
        EnhancedConsolidationReport
    """
    return asyncio.run(
        consolidate_with_local_reasoning(
            project_id=project_id,
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            graph_store=graph_store,
            time_window_hours=time_window_hours,
            min_pattern_confidence=min_pattern_confidence,
            use_local_reasoning=use_local_reasoning,
            use_claude_validation=use_claude_validation,
            enable_compression=enable_compression,
            dry_run=dry_run,
        )
    )
