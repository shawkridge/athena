"""Event ingestion orchestrator for multi-source coordination.

This module implements the EventIngestionOrchestrator, which coordinates ingestion
from multiple event sources with batching, cursor management, and error handling.

Key Features:
1. Single-source ingestion with batched processing
2. Multi-source concurrent ingestion with per-source error isolation
3. Scheduled ingestion with cron-style or interval-based triggers
4. Dual-trigger batching (size + latency)
5. Automatic cursor persistence after successful sync
6. Retry logic with exponential backoff
7. Comprehensive statistics and metrics tracking
8. Per-source error handling (one failure doesn't affect others)

Architecture:
    Multiple Event Sources (concurrent)
        ↓
    EventIngestionOrchestrator (coordinator)
        ↓
    EventProcessingPipeline (batching + deduplication)
        ↓
    CursorManager (incremental sync state)
        ↓
    EpisodicStore (persistence)

Performance Characteristics:
- Target throughput: 1000+ events/sec per source
- Batch latency: <200ms (configurable)
- Batch size: 64 events (configurable)
- Max retries: 3 attempts with exponential backoff
- Concurrent sources: Limited by asyncio task capacity

Usage Example (Single Source):
    >>> from athena.episodic.orchestrator import EventIngestionOrchestrator
    >>> from athena.episodic.pipeline import EventProcessingPipeline
    >>> from athena.episodic.cursor import CursorManager
    >>> from athena.episodic.sources.factory import EventSourceFactory
    >>>
    >>> # Initialize components
    >>> pipeline = EventProcessingPipeline(store, embedder, hasher)
    >>> cursor_mgr = CursorManager(db)
    >>> factory = EventSourceFactory(cursor_store=cursor_mgr)
    >>>
    >>> # Create orchestrator
    >>> orchestrator = EventIngestionOrchestrator(
    ...     pipeline=pipeline,
    ...     cursor_manager=cursor_mgr,
    ...     batch_size=64,
    ...     max_batch_latency_ms=200
    ... )
    >>>
    >>> # Create source
    >>> source = await factory.create_source(
    ...     source_type='filesystem',
    ...     source_id='athena-codebase',
    ...     credentials={},
    ...     config={'root_dir': '/path/to/athena'}
    ... )
    >>>
    >>> # Ingest from single source
    >>> stats = await orchestrator.ingest_from_source(source)
    >>> print(f"Inserted {stats['inserted']} events")

Usage Example (Multiple Sources):
    >>> # Create multiple sources
    >>> github_source = await factory.create_source(...)
    >>> slack_source = await factory.create_source(...)
    >>>
    >>> # Ingest concurrently from all sources
    >>> results = await orchestrator.ingest_from_multiple_sources([
    ...     github_source,
    ...     slack_source
    ... ])
    >>>
    >>> # Check per-source results
    >>> for source_id, stats in results.items():
    ...     print(f"{source_id}: {stats['inserted']} inserted, {stats['errors']} errors")

Usage Example (Scheduled Ingestion):
    >>> # Run ingestion every 5 minutes
    >>> await orchestrator.run_scheduled_ingest(
    ...     sources=[github_source, slack_source],
    ...     schedule='*/5 * * * *'  # Cron syntax
    ... )
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional

from .pipeline import EventProcessingPipeline
from .cursor import CursorManager
from .sources._base import BaseEventSource
from .models import EpisodicEvent


logger = logging.getLogger(__name__)


class EventIngestionOrchestrator:
    """Orchestrates multi-source event ingestion with batching and cursor management.

    Coordinates ingestion from multiple event sources, managing:
    - Batched processing with dual triggers (size + latency)
    - Cursor persistence for incremental sync
    - Concurrent multi-source ingestion
    - Error handling and retry logic
    - Statistics aggregation and reporting

    The orchestrator sits between event sources and the processing pipeline,
    handling coordination concerns while delegating actual processing to the
    pipeline and storage layers.

    Design Principles:
    - Per-source error isolation: One source failure doesn't affect others
    - Graceful degradation: Partial failures are tracked but don't fail entire batch
    - Resource efficiency: Batching reduces database round-trips and API calls
    - Observability: Comprehensive metrics for monitoring and debugging
    - Resumability: Cursor persistence enables incremental sync

    Configuration:
    - batch_size: Events per batch (default: 64)
        - Smaller: Lower latency, more overhead
        - Larger: Higher throughput, more memory
    - max_batch_latency_ms: Max wait before flush (default: 200ms)
        - Smaller: Lower latency, less batching efficiency
        - Larger: Better batching, higher latency
    - max_retries: Retry attempts on failure (default: 3)
    - enable_parallel: Run sources in parallel (default: True)
    """

    def __init__(
        self,
        pipeline: EventProcessingPipeline,
        cursor_manager: CursorManager,
        batch_size: int = 64,
        max_batch_latency_ms: int = 200,
        max_retries: int = 3,
        enable_parallel: bool = True,
    ):
        """Initialize event ingestion orchestrator.

        Args:
            pipeline: Event processing pipeline for batching and deduplication
            cursor_manager: Cursor manager for incremental sync state
            batch_size: Number of events per batch (default: 64)
            max_batch_latency_ms: Max wait before flushing batch (default: 200ms)
            max_retries: Max retry attempts on failure (default: 3)
            enable_parallel: Enable parallel multi-source ingestion (default: True)
        """
        self.pipeline = pipeline
        self.cursor_manager = cursor_manager
        self.batch_size = batch_size
        self.max_batch_latency_ms = max_batch_latency_ms
        self.max_retries = max_retries
        self.enable_parallel = enable_parallel

        # Global statistics
        self._total_sources_processed = 0
        self._total_sources_succeeded = 0
        self._total_sources_failed = 0
        self._total_events_ingested = 0

    # ========================================================================
    # Single-Source Ingestion
    # ========================================================================

    async def ingest_from_source(
        self, source: BaseEventSource, retry_count: int = 0
    ) -> Dict[str, Any]:
        """Ingest events from a single source with batching and cursor management.

        Process flow:
        1. Validate source health
        2. Generate events from source (async iterator)
        3. Batch events (flush on size or latency trigger)
        4. Process batches through pipeline
        5. Save cursor after successful sync
        6. Aggregate statistics

        Args:
            source: Event source to ingest from
            retry_count: Current retry attempt (internal, for recursion)

        Returns:
            Statistics dictionary with:
                - source_id: Source identifier
                - source_type: Source type
                - total: Total events generated
                - inserted: Events inserted into database
                - skipped_duplicate: Duplicates within batch
                - skipped_existing: Events already in database
                - errors: Number of errors encountered
                - duration_ms: Total ingestion duration
                - throughput: Events per second
                - cursor_saved: Whether cursor was saved
                - retry_count: Number of retries performed

        Raises:
            ValueError: Invalid source
            ConnectionError: Source validation failed after retries
            Exception: Unrecoverable error during ingestion

        Example:
            >>> source = await factory.create_source('github', ...)
            >>> stats = await orchestrator.ingest_from_source(source)
            >>> print(f"Inserted {stats['inserted']} events in {stats['duration_ms']}ms")
            >>> print(f"Throughput: {stats['throughput']:.0f} events/sec")
        """
        start_time = time.time()
        source_id = source.source_id
        source_type = source.source_type

        logger.info(
            f"Starting ingestion from source '{source_id}' (type: {source_type}, "
            f"attempt: {retry_count + 1}/{self.max_retries + 1})"
        )

        # Initialize stats
        stats = {
            "source_id": source_id,
            "source_type": source_type,
            "total": 0,
            "inserted": 0,
            "skipped_duplicate": 0,
            "skipped_existing": 0,
            "errors": 0,
            "duration_ms": 0.0,
            "throughput": 0.0,
            "cursor_saved": False,
            "retry_count": retry_count,
        }

        try:
            # Validate source health
            if not await source.validate():
                raise ConnectionError(
                    f"Source validation failed for '{source_id}' (type: {source_type})"
                )

            # Initialize batching state
            current_batch: List[EpisodicEvent] = []
            batch_start_time = time.time()
            total_events = 0
            total_inserted = 0
            total_skipped_duplicate = 0
            total_skipped_existing = 0
            total_errors = 0

            # Generate and batch events
            async for event in source.generate_events():
                current_batch.append(event)
                total_events += 1

                # Check if batch should be flushed
                time_elapsed_ms = (time.time() - batch_start_time) * 1000
                if self._should_flush_batch(current_batch, time_elapsed_ms):
                    # Process batch
                    batch_stats = await self._process_batch(current_batch, source_id)

                    # Aggregate stats
                    total_inserted += batch_stats["inserted"]
                    total_skipped_duplicate += batch_stats["skipped_duplicate"]
                    total_skipped_existing += batch_stats["skipped_existing"]
                    total_errors += batch_stats["errors"]

                    # Reset batch
                    current_batch = []
                    batch_start_time = time.time()

                    logger.debug(
                        f"Processed batch for '{source_id}': "
                        f"{batch_stats['inserted']} inserted, "
                        f"{batch_stats['skipped_existing']} skipped"
                    )

            # Flush remaining events
            if current_batch:
                batch_stats = await self._process_batch(current_batch, source_id)
                total_inserted += batch_stats["inserted"]
                total_skipped_duplicate += batch_stats["skipped_duplicate"]
                total_skipped_existing += batch_stats["skipped_existing"]
                total_errors += batch_stats["errors"]

                logger.debug(
                    f"Processed final batch for '{source_id}': "
                    f"{batch_stats['inserted']} inserted"
                )

            # Persist cursor after successful sync
            cursor_saved = await self._persist_cursor(source)

            # Compute final stats
            duration_ms = (time.time() - start_time) * 1000
            throughput = total_events / (duration_ms / 1000) if duration_ms > 0 else 0.0

            stats.update(
                {
                    "total": total_events,
                    "inserted": total_inserted,
                    "skipped_duplicate": total_skipped_duplicate,
                    "skipped_existing": total_skipped_existing,
                    "errors": total_errors,
                    "duration_ms": duration_ms,
                    "throughput": throughput,
                    "cursor_saved": cursor_saved,
                }
            )

            # Update global stats
            self._total_sources_processed += 1
            self._total_sources_succeeded += 1
            self._total_events_ingested += total_inserted

            logger.info(
                f"Ingestion complete for '{source_id}': "
                f"{total_inserted} inserted, {total_events} total, "
                f"{duration_ms:.1f}ms ({throughput:.0f} events/sec)"
            )

            return stats

        except Exception as e:
            # Log error with context
            error_msg = f"Ingestion failed for '{source_id}': {e}"
            logger.error(error_msg, exc_info=True)

            # Handle error classification and retry
            should_retry = self._should_retry_error(e, retry_count)

            if should_retry:
                # Exponential backoff
                backoff_ms = min(1000 * (2**retry_count), 10000)  # Max 10s
                logger.info(
                    f"Retrying '{source_id}' after {backoff_ms}ms backoff "
                    f"(attempt {retry_count + 2}/{self.max_retries + 1})"
                )
                await asyncio.sleep(backoff_ms / 1000)

                # Recursive retry
                return await self.ingest_from_source(source, retry_count + 1)
            else:
                # No retry - return error stats
                stats["errors"] = 1
                stats["duration_ms"] = (time.time() - start_time) * 1000
                stats["error_message"] = str(e)

                self._total_sources_processed += 1
                self._total_sources_failed += 1

                return stats

    # ========================================================================
    # Multi-Source Ingestion
    # ========================================================================

    async def ingest_from_multiple_sources(
        self, sources: List[BaseEventSource]
    ) -> Dict[str, Dict[str, Any]]:
        """Ingest events from multiple sources concurrently.

        Each source is processed independently with its own error handling.
        A failure in one source does not affect other sources.

        Args:
            sources: List of event sources to ingest from

        Returns:
            Dict mapping source_id -> statistics dict
            Example:
            {
                'github-athena-repo': {
                    'total': 142,
                    'inserted': 135,
                    'errors': 0,
                    'duration_ms': 3500.0,
                    'throughput': 40.6
                },
                'slack-dev-channel': {
                    'total': 58,
                    'inserted': 52,
                    'errors': 1,
                    'duration_ms': 2200.0,
                    'throughput': 26.4
                }
            }

        Example:
            >>> sources = [github_source, slack_source, filesystem_source]
            >>> results = await orchestrator.ingest_from_multiple_sources(sources)
            >>>
            >>> # Check overall success
            >>> total_inserted = sum(s['inserted'] for s in results.values())
            >>> total_errors = sum(s['errors'] for s in results.values())
            >>> print(f"Total inserted: {total_inserted}, Total errors: {total_errors}")
            >>>
            >>> # Check per-source results
            >>> for source_id, stats in results.items():
            ...     if stats['errors'] > 0:
            ...         print(f"⚠️  {source_id}: {stats['error_message']}")
            ...     else:
            ...         print(f"✓ {source_id}: {stats['inserted']} events")
        """
        if not sources:
            logger.warning("No sources provided for ingestion")
            return {}

        logger.info(
            f"Starting multi-source ingestion: {len(sources)} sources "
            f"(parallel={self.enable_parallel})"
        )

        start_time = time.time()

        # Create ingestion tasks
        if self.enable_parallel:
            # Concurrent ingestion
            tasks = [self.ingest_from_source(source) for source in sources]

            # Gather results (exceptions are caught per-source)
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results (handle exceptions that escaped per-source handling)
            source_stats = {}
            for source, result in zip(sources, results):
                source_id = source.source_id

                if isinstance(result, Exception):
                    # Unexpected exception - create error stats
                    logger.error(f"Unexpected error for '{source_id}': {result}", exc_info=result)
                    source_stats[source_id] = {
                        "source_id": source_id,
                        "source_type": source.source_type,
                        "total": 0,
                        "inserted": 0,
                        "errors": 1,
                        "error_message": str(result),
                    }
                else:
                    source_stats[source_id] = result

        else:
            # Sequential ingestion
            source_stats = {}
            for source in sources:
                try:
                    stats = await self.ingest_from_source(source)
                    source_stats[source.source_id] = stats
                except Exception as e:
                    logger.error(f"Unexpected error for '{source.source_id}': {e}", exc_info=True)
                    source_stats[source.source_id] = {
                        "source_id": source.source_id,
                        "source_type": source.source_type,
                        "total": 0,
                        "inserted": 0,
                        "errors": 1,
                        "error_message": str(e),
                    }

        # Compute aggregated stats
        total_duration_ms = (time.time() - start_time) * 1000
        total_events = sum(s.get("total", 0) for s in source_stats.values())
        total_inserted = sum(s.get("inserted", 0) for s in source_stats.values())
        total_errors = sum(s.get("errors", 0) for s in source_stats.values())
        success_count = sum(1 for s in source_stats.values() if s.get("errors", 0) == 0)
        success_rate = (success_count / len(sources) * 100) if sources else 0.0

        logger.info(
            f"Multi-source ingestion complete: "
            f"{total_inserted} inserted from {len(sources)} sources "
            f"({success_rate:.1f}% success rate, {total_errors} errors, "
            f"{total_duration_ms:.1f}ms)"
        )

        return source_stats

    # ========================================================================
    # Scheduled Ingestion
    # ========================================================================

    async def run_scheduled_ingest(
        self, sources: List[BaseEventSource], schedule: str, max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run scheduled ingestion with cron-style or interval-based triggers.

        Supports two schedule formats:
        1. Interval-based: "5m", "1h", "30s" (minutes, hours, seconds)
        2. Cron-style: "*/5 * * * *" (every 5 minutes)

        Args:
            sources: List of event sources to ingest from
            schedule: Schedule specification
                Examples:
                - "5m": Every 5 minutes
                - "1h": Every hour
                - "30s": Every 30 seconds
                - "*/5 * * * *": Cron format (every 5 minutes)
            max_iterations: Optional max number of sync cycles (for testing)

        Returns:
            Aggregated statistics across all sync cycles:
                - total_cycles: Number of sync cycles executed
                - total_events: Total events ingested
                - total_errors: Total errors encountered
                - success_rate: Percentage of successful cycles
                - avg_duration_ms: Average cycle duration

        Example:
            >>> # Run every 5 minutes
            >>> stats = await orchestrator.run_scheduled_ingest(
            ...     sources=[github_source, slack_source],
            ...     schedule='5m'
            ... )

            >>> # Run every hour with max 10 iterations (testing)
            >>> stats = await orchestrator.run_scheduled_ingest(
            ...     sources=[github_source],
            ...     schedule='1h',
            ...     max_iterations=10
            ... )

        Note:
            This method runs indefinitely unless max_iterations is specified.
            Use Ctrl+C or asyncio cancellation to stop.
        """
        logger.info(
            f"Starting scheduled ingestion: {len(sources)} sources, " f"schedule='{schedule}'"
        )

        # Parse schedule
        interval_seconds = self._parse_schedule(schedule)

        # Statistics tracking
        total_cycles = 0
        total_events = 0
        total_errors = 0
        successful_cycles = 0
        cycle_durations = []

        try:
            while True:
                cycle_start = time.time()
                total_cycles += 1

                logger.info(f"Starting sync cycle {total_cycles}")

                # Run multi-source ingestion
                try:
                    results = await self.ingest_from_multiple_sources(sources)

                    # Aggregate stats
                    cycle_events = sum(s.get("inserted", 0) for s in results.values())
                    cycle_errors = sum(s.get("errors", 0) for s in results.values())

                    total_events += cycle_events
                    total_errors += cycle_errors

                    if cycle_errors == 0:
                        successful_cycles += 1

                    logger.info(
                        f"Sync cycle {total_cycles} complete: "
                        f"{cycle_events} events, {cycle_errors} errors"
                    )

                except Exception as e:
                    logger.error(f"Sync cycle {total_cycles} failed: {e}", exc_info=True)
                    total_errors += 1

                cycle_duration = (time.time() - cycle_start) * 1000
                cycle_durations.append(cycle_duration)

                # Check if we've reached max iterations
                if max_iterations and total_cycles >= max_iterations:
                    logger.info(f"Reached max iterations ({max_iterations}), stopping")
                    break

                # Sleep until next cycle
                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info("Scheduled ingestion cancelled")
            raise

        # Compute final stats
        success_rate = (successful_cycles / total_cycles * 100) if total_cycles > 0 else 0.0
        avg_duration_ms = sum(cycle_durations) / len(cycle_durations) if cycle_durations else 0.0

        final_stats = {
            "total_cycles": total_cycles,
            "successful_cycles": successful_cycles,
            "failed_cycles": total_cycles - successful_cycles,
            "total_events": total_events,
            "total_errors": total_errors,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration_ms,
        }

        logger.info(
            f"Scheduled ingestion complete: "
            f"{total_cycles} cycles, {total_events} events, "
            f"{success_rate:.1f}% success rate"
        )

        return final_stats

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _should_flush_batch(self, batch: List[EpisodicEvent], time_elapsed_ms: float) -> bool:
        """Check if batch should be flushed based on dual triggers.

        Batch is flushed when:
        1. Batch size reaches configured limit (size trigger), OR
        2. Elapsed time exceeds configured latency limit (latency trigger)

        Args:
            batch: Current batch of events
            time_elapsed_ms: Time since batch started (milliseconds)

        Returns:
            True if batch should be flushed, False otherwise

        Design rationale:
            - Size trigger: Ensures efficient batch processing
            - Latency trigger: Ensures bounded event processing delay
            - Dual trigger: Balances throughput and latency
        """
        # Size trigger
        if len(batch) >= self.batch_size:
            return True

        # Latency trigger
        if time_elapsed_ms >= self.max_batch_latency_ms:
            return True

        return False

    async def _process_batch(self, batch: List[EpisodicEvent], source_id: str) -> Dict[str, Any]:
        """Process a batch of events through the pipeline.

        Args:
            batch: Batch of events to process
            source_id: Source identifier (for logging)

        Returns:
            Batch processing statistics

        Note:
            Delegates to EventProcessingPipeline for actual processing.
            Handles exceptions and ensures they don't propagate.
        """
        if not batch:
            return {
                "total": 0,
                "inserted": 0,
                "skipped_duplicate": 0,
                "skipped_existing": 0,
                "errors": 0,
            }

        try:
            stats = await self.pipeline.process_batch(batch)
            return stats

        except Exception as e:
            logger.error(f"Batch processing failed for '{source_id}': {e}", exc_info=True)
            return {
                "total": len(batch),
                "inserted": 0,
                "skipped_duplicate": 0,
                "skipped_existing": 0,
                "errors": len(batch),
            }

    async def _persist_cursor(self, source: BaseEventSource) -> bool:
        """Persist cursor for a source after successful sync.

        Args:
            source: Event source to save cursor for

        Returns:
            True if cursor saved successfully, False otherwise

        Side effects:
            Updates cursor_manager with current source cursor
        """
        try:
            # Check if source supports incremental sync
            if not await source.supports_incremental():
                logger.debug(
                    f"Source '{source.source_id}' doesn't support incremental sync, "
                    f"skipping cursor save"
                )
                return False

            # Get current cursor
            cursor_data = await source.get_cursor()
            if not cursor_data:
                logger.debug(
                    f"No cursor to save for '{source.source_id}' "
                    f"(source may not have generated any events)"
                )
                return False

            # Save cursor
            self.cursor_manager.update_cursor(source.source_id, cursor_data)

            logger.info(
                f"Saved cursor for '{source.source_id}': "
                f"{self._format_cursor_summary(cursor_data)}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to persist cursor for '{source.source_id}': {e}", exc_info=True)
            return False

    def _format_cursor_summary(self, cursor_data: Dict[str, Any]) -> str:
        """Format cursor data for logging (truncated).

        Args:
            cursor_data: Cursor data dict

        Returns:
            Formatted string (max 100 chars)
        """
        cursor_str = str(cursor_data)
        if len(cursor_str) > 100:
            cursor_str = cursor_str[:97] + "..."
        return cursor_str

    def _should_retry_error(self, error: Exception, retry_count: int) -> bool:
        """Determine if error is retryable.

        Args:
            error: Exception that occurred
            retry_count: Current retry attempt

        Returns:
            True if error should be retried, False otherwise

        Retryable errors:
        - ConnectionError (network issues)
        - TimeoutError (temporary unavailability)
        - OSError (transient I/O errors)

        Non-retryable errors:
        - ValueError (configuration errors)
        - PermissionError (authentication failures)
        - Other exceptions (unknown errors, likely permanent)
        """
        # Check retry limit
        if retry_count >= self.max_retries:
            return False

        # Check error type
        retryable_errors = (ConnectionError, TimeoutError, OSError)

        if isinstance(error, retryable_errors):
            return True

        # Non-retryable
        return False

    def _parse_schedule(self, schedule: str) -> float:
        """Parse schedule string to interval in seconds.

        Supports:
        1. Interval format: "5m", "1h", "30s"
        2. Cron format: "*/5 * * * *" (simplified, only interval patterns)

        Args:
            schedule: Schedule specification string

        Returns:
            Interval in seconds

        Raises:
            ValueError: Invalid schedule format

        Examples:
            >>> _parse_schedule("5m")
            300.0  # 5 minutes = 300 seconds

            >>> _parse_schedule("1h")
            3600.0  # 1 hour = 3600 seconds

            >>> _parse_schedule("30s")
            30.0  # 30 seconds

            >>> _parse_schedule("*/5 * * * *")
            300.0  # Every 5 minutes (cron format)
        """
        # Interval format: "5m", "1h", "30s"
        if schedule.endswith("s"):
            return float(schedule[:-1])
        elif schedule.endswith("m"):
            return float(schedule[:-1]) * 60
        elif schedule.endswith("h"):
            return float(schedule[:-1]) * 3600
        elif schedule.endswith("d"):
            return float(schedule[:-1]) * 86400

        # Cron format (simplified): "*/N * * * *" = every N minutes
        if schedule.startswith("*/"):
            parts = schedule.split()
            if len(parts) >= 1:
                interval_str = parts[0].replace("*/", "")
                try:
                    interval_minutes = int(interval_str)
                    return interval_minutes * 60
                except ValueError:
                    pass

        raise ValueError(
            f"Invalid schedule format: '{schedule}'. "
            f"Use interval format (e.g., '5m', '1h', '30s') or "
            f"cron format (e.g., '*/5 * * * *')"
        )

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global orchestrator statistics.

        Returns:
            Dict with global metrics:
                - total_sources_processed: Total sources processed
                - total_sources_succeeded: Sources with zero errors
                - total_sources_failed: Sources with errors
                - total_events_ingested: Total events inserted
                - success_rate: Percentage of successful sources
                - config: Orchestrator configuration

        Example:
            >>> stats = orchestrator.get_global_stats()
            >>> print(f"Success rate: {stats['success_rate']:.1f}%")
            >>> print(f"Total events: {stats['total_events_ingested']}")
        """
        success_rate = (
            (self._total_sources_succeeded / self._total_sources_processed * 100)
            if self._total_sources_processed > 0
            else 0.0
        )

        return {
            "total_sources_processed": self._total_sources_processed,
            "total_sources_succeeded": self._total_sources_succeeded,
            "total_sources_failed": self._total_sources_failed,
            "total_events_ingested": self._total_events_ingested,
            "success_rate": success_rate,
            "config": {
                "batch_size": self.batch_size,
                "max_batch_latency_ms": self.max_batch_latency_ms,
                "max_retries": self.max_retries,
                "enable_parallel": self.enable_parallel,
            },
        }


# ============================================================================
# Example Usage Patterns
# ============================================================================


async def example_single_source():
    """Example: Single-source ingestion with statistics."""
    from .store import EpisodicStore
    from .hashing import EventHasher
    from .sources.factory import EventSourceFactory
    from ..core.database import Database
    from ..core.embeddings import EmbeddingModel

    # Initialize components
    db = Database("memory.db")
    store = EpisodicStore(db)
    hasher = EventHasher()
    embedder = EmbeddingModel()
    cursor_mgr = CursorManager(db)

    # Create pipeline and orchestrator
    pipeline = EventProcessingPipeline(store, embedder, hasher)
    orchestrator = EventIngestionOrchestrator(
        pipeline=pipeline, cursor_manager=cursor_mgr, batch_size=64, max_batch_latency_ms=200
    )

    # Create event source
    factory = EventSourceFactory(cursor_store=cursor_mgr)
    source = await factory.create_source(
        source_type="filesystem",
        source_id="athena-codebase",
        credentials={},
        config={"root_dir": "/home/user/.work/athena"},
    )

    # Ingest events
    stats = await orchestrator.ingest_from_source(source)

    # Print results
    print(f"Source: {stats['source_id']}")
    print(f"Total events: {stats['total']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Skipped (existing): {stats['skipped_existing']}")
    print(f"Duration: {stats['duration_ms']:.1f}ms")
    print(f"Throughput: {stats['throughput']:.0f} events/sec")
    print(f"Cursor saved: {stats['cursor_saved']}")


async def example_multi_source():
    """Example: Multi-source concurrent ingestion."""
    from .store import EpisodicStore
    from .hashing import EventHasher
    from .sources.factory import EventSourceFactory
    from ..core.database import Database
    from ..core.embeddings import EmbeddingModel

    # Initialize components
    db = Database("memory.db")
    store = EpisodicStore(db)
    hasher = EventHasher()
    embedder = EmbeddingModel()
    cursor_mgr = CursorManager(db)

    # Create pipeline and orchestrator
    pipeline = EventProcessingPipeline(store, embedder, hasher)
    orchestrator = EventIngestionOrchestrator(
        pipeline=pipeline, cursor_manager=cursor_mgr, enable_parallel=True  # Concurrent ingestion
    )

    # Create multiple sources
    factory = EventSourceFactory(cursor_store=cursor_mgr)

    github_source = await factory.create_source(
        source_type="github",
        source_id="athena-repo",
        credentials={"token": "ghp_xxx"},
        config={"owner": "user", "repo": "athena"},
    )

    slack_source = await factory.create_source(
        source_type="slack",
        source_id="dev-channel",
        credentials={"bot_token": "xoxb-xxx"},
        config={"channel_id": "C123456"},
    )

    # Ingest from all sources concurrently
    results = await orchestrator.ingest_from_multiple_sources([github_source, slack_source])

    # Print per-source results
    for source_id, stats in results.items():
        print(f"\n{source_id}:")
        print(f"  Inserted: {stats['inserted']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Duration: {stats['duration_ms']:.1f}ms")

    # Print global stats
    global_stats = orchestrator.get_global_stats()
    print("\nGlobal stats:")
    print(f"  Total events: {global_stats['total_events_ingested']}")
    print(f"  Success rate: {global_stats['success_rate']:.1f}%")


async def example_scheduled_ingestion():
    """Example: Scheduled ingestion (every 5 minutes)."""
    from .store import EpisodicStore
    from .hashing import EventHasher
    from .sources.factory import EventSourceFactory
    from ..core.database import Database
    from ..core.embeddings import EmbeddingModel

    # Initialize components
    db = Database("memory.db")
    store = EpisodicStore(db)
    hasher = EventHasher()
    embedder = EmbeddingModel()
    cursor_mgr = CursorManager(db)

    # Create pipeline and orchestrator
    pipeline = EventProcessingPipeline(store, embedder, hasher)
    orchestrator = EventIngestionOrchestrator(pipeline=pipeline, cursor_manager=cursor_mgr)

    # Create sources
    factory = EventSourceFactory(cursor_store=cursor_mgr)
    sources = [
        await factory.create_source("github", "athena-repo", {...}, {...}),
        await factory.create_source("slack", "dev-channel", {...}, {...}),
    ]

    # Run scheduled ingestion (every 5 minutes)
    # Note: This runs indefinitely until cancelled
    try:
        stats = await orchestrator.run_scheduled_ingest(
            sources=sources,
            schedule="5m",  # Every 5 minutes
            max_iterations=10,  # For testing (remove for production)
        )

        print("Scheduled ingestion complete:")
        print(f"  Total cycles: {stats['total_cycles']}")
        print(f"  Total events: {stats['total_events']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")

    except asyncio.CancelledError:
        print("Scheduled ingestion cancelled")


if __name__ == "__main__":
    """Demonstrate event ingestion orchestrator."""
    import asyncio

    print("Event Ingestion Orchestrator Demonstration")
    print("=" * 80)

    # Run single-source example
    print("\n1. Single-source ingestion")
    print("-" * 80)
    asyncio.run(example_single_source())

    # Run multi-source example
    print("\n2. Multi-source ingestion")
    print("-" * 80)
    asyncio.run(example_multi_source())

    # Run scheduled ingestion example
    print("\n3. Scheduled ingestion")
    print("-" * 80)
    asyncio.run(example_scheduled_ingestion())

    print("\n" + "=" * 80)
    print("Orchestrator demonstration complete!")
