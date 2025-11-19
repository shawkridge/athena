"""Research agent executor - Coordinates research-coordinator agent invocation."""

import asyncio
import logging
from typing import Optional, Callable, Any
from datetime import datetime

from .store import ResearchStore
from .models import ResearchFinding, AgentProgress, AgentStatus, ResearchStatus

# Note: agents module now contains ResearchCoordinator and specialized agents
# RESEARCH_AGENTS defined locally in this module
from .aggregation import FindingAggregator
from .semantic_integration import ResearchMemoryIntegrator
from .cache import ResearchQueryCache
from .rate_limit import RateLimiter
from .metrics import ResearchMetricsCollector
from .circuit_breaker import CircuitBreakerManager
from .consolidation import ResearchConsolidationStore
from .consolidation_system import ResearchConsolidationSystem
from .streaming import StreamingResultCollector, StreamingUpdate
from .agent_monitor import LiveAgentMonitor
from .query_refinement import QueryRefinement

logger = logging.getLogger(__name__)


class ResearchAgentExecutor:
    """Manages research agent execution and findings aggregation."""

    # Hardcoded research sources matching /research command specification
    RESEARCH_AGENTS = [
        {"name": "arxiv-researcher", "source": "arXiv", "credibility": 1.0},
        {"name": "anthropic-docs-researcher", "source": "Anthropic Docs", "credibility": 0.95},
        {"name": "github-researcher", "source": "GitHub", "credibility": 0.85},
        {"name": "paperswithcode-researcher", "source": "Papers with Code", "credibility": 0.90},
        {"name": "techblogs-researcher", "source": "Tech Blogs", "credibility": 0.88},
        {"name": "hackernews-researcher", "source": "HackerNews", "credibility": 0.70},
        {"name": "medium-researcher", "source": "Medium", "credibility": 0.68},
        {"name": "x-researcher", "source": "X/Twitter", "credibility": 0.62},
    ]

    def __init__(
        self,
        research_store: ResearchStore,
        on_finding_discovered: Optional[Callable[[ResearchFinding], Any]] = None,
        on_status_updated: Optional[Callable[[int, ResearchStatus], Any]] = None,
        aggregator: Optional[FindingAggregator] = None,
        memory_integrator: Optional[ResearchMemoryIntegrator] = None,
        enable_cache: bool = True,
        cache_ttl_seconds: int = 3600,
        enable_rate_limiting: bool = True,
    ):
        """Initialize research executor.

        Args:
            research_store: ResearchStore instance
            on_finding_discovered: Callback when finding discovered
            on_status_updated: Callback when status updated
            aggregator: Optional FindingAggregator for deduplication/cross-validation
            memory_integrator: Optional ResearchMemoryIntegrator for memory storage
            enable_cache: Enable query result caching
            cache_ttl_seconds: Cache entry time-to-live in seconds
            enable_rate_limiting: Enable rate limiting per source
        """
        self.research_store = research_store
        self.on_finding_discovered = on_finding_discovered
        self.on_status_updated = on_status_updated
        self.aggregator = aggregator or FindingAggregator()
        self.memory_integrator = memory_integrator

        # Production hardening components
        self.cache = (
            ResearchQueryCache(default_ttl_seconds=cache_ttl_seconds) if enable_cache else None
        )
        self.rate_limiter = RateLimiter() if enable_rate_limiting else None
        self.metrics = ResearchMetricsCollector()
        self.circuit_breakers = CircuitBreakerManager()

        # Phase 3.4: Real-time streaming components
        self.streaming_collector: Optional[StreamingResultCollector] = None
        self.agent_monitor: Optional[LiveAgentMonitor] = None
        self.on_streaming_update: Optional[Callable[[StreamingUpdate], Any]] = None

    async def execute_research(
        self, task_id: int, topic: str, constraints: Optional[QueryRefinement] = None
    ) -> int:
        """Execute research for a topic with parallel agent coordination.

        Args:
            task_id: Research task ID
            topic: Research topic
            constraints: Optional QueryRefinement with search constraints
              - excluded_sources: Sources to skip
              - focused_sources: Sources to prioritize
              - time_constraint: Time range filter (e.g., "2024")
              - quality_threshold: Minimum result quality (0-1)
              - agent_directives: Per-agent instructions

        Returns:
            Total findings count
        """
        # Start metrics tracking
        task_metrics = self.metrics.start_operation("research_task", task_id=task_id)

        try:
            # Check cache first
            if self.cache:
                cached_findings = self.cache.get(topic)
                if cached_findings:
                    logger.info(f"Cache hit for topic: {topic}")
                    task_metrics.complete(success=True, items_output=len(cached_findings))
                    return len(cached_findings)

            # Initialize agent progress records
            for agent in self.RESEARCH_AGENTS:
                progress = AgentProgress(
                    research_task_id=task_id,
                    agent_name=agent["name"],
                    status=AgentStatus.PENDING,
                )
                self.research_store.record_agent_progress(progress)

            logger.info(f"Starting research execution for task {task_id}: {topic}")
            logger.info(f"Coordinating {len(self.RESEARCH_AGENTS)} parallel research agents")
            if constraints:
                logger.info(f"Applied constraints: {constraints.summary()}")

            # Execute all agents in parallel
            tasks = []
            for agent_info in self.RESEARCH_AGENTS:
                # Skip excluded sources
                if constraints and agent_info["source"] in constraints.excluded_sources:
                    logger.info(f"Skipping {agent_info['name']} (excluded source)")
                    continue

                # Update agent status to running
                self.research_store.update_agent_progress(
                    task_id, agent_info["name"], AgentStatus.RUNNING
                )

                # Create async task for agent execution
                task = self._execute_agent_with_timeout(task_id, topic, agent_info, constraints)
                tasks.append(task)

            # Wait for all agents to complete (with timeout protection)
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Aggregate results from all agents
            raw_findings = []
            failed_agents = []

            for i, result in enumerate(results):
                agent_info = self.RESEARCH_AGENTS[i]
                agent_name = agent_info["name"]

                if isinstance(result, Exception):
                    # Agent failed
                    logger.warning(f"Agent {agent_name} failed: {result}")
                    self.research_store.update_agent_progress(
                        task_id, agent_name, AgentStatus.FAILED
                    )
                    failed_agents.append(agent_name)
                else:
                    # Agent succeeded - result is list of findings
                    findings_count = len(result) if result else 0
                    raw_findings.extend(result)

                    self.research_store.update_agent_progress(
                        task_id, agent_name, AgentStatus.COMPLETED, findings_count=findings_count
                    )

                    logger.info(f"Agent {agent_name} completed: {findings_count} findings")

            # Phase 2: Deduplicate, cross-validate, and rank findings
            logger.info(
                f"Aggregating {len(raw_findings)} raw findings for deduplication and cross-validation"
            )

            # Convert ResearchFinding objects to dict format for aggregator
            findings_dict_list = [
                {
                    "title": f.title,
                    "summary": f.summary,
                    "url": f.url,
                    "source": f.source,
                    "credibility_score": f.credibility_score,
                    "relevance_score": 0.85,  # Default relevance
                }
                for f in raw_findings
            ]

            # Run aggregation pipeline (dedup → cross-validate → filter)
            aggregated_findings = self.aggregator.aggregate(
                findings_dict_list, high_confidence_only=False
            )

            logger.info(f"Aggregated to {len(aggregated_findings)} deduplicated findings")

            # Get summary statistics
            agg_stats = self.aggregator.get_summary_stats(aggregated_findings)
            total_findings = agg_stats["total"]

            # Phase 3: Integrate findings into semantic memory (if integrator available)
            entities_created = 0
            if self.memory_integrator and aggregated_findings:
                logger.info(f"Integrating {len(aggregated_findings)} findings into semantic memory")

                # Get task for project_id
                task = self.research_store.get_task(task_id)
                project_id = task.project_id if task else None

                for finding in aggregated_findings:
                    try:
                        # Index finding in semantic memory
                        memory_id = self.memory_integrator.index_finding(
                            finding,
                            task_id=task_id,
                            project_id=project_id,
                            tags=[
                                f"research-task-{task_id}",
                                f"topic-{topic.replace(' ', '-').lower()}",
                            ],
                        )

                        # Build knowledge graph for finding
                        if memory_id:
                            self.memory_integrator.build_finding_graph(
                                finding, task_id=task_id, project_id=project_id
                            )
                            entities_created += 1

                            # Update finding record with memory info
                            for raw_finding in raw_findings:
                                if raw_finding.title == finding.title:
                                    raw_finding.stored_to_memory = True
                                    raw_finding.memory_id = memory_id
                                    self.research_store.record_finding(raw_finding)
                                    break
                    except Exception as e:
                        logger.error(f"Error integrating finding to memory: {e}")
                        continue

                # Record research session event
                try:
                    self.memory_integrator.record_research_session(
                        task_id=task_id,
                        topic=topic,
                        findings_count=total_findings,
                        high_confidence_count=agg_stats["high_confidence_count"],
                        sources_used=agg_stats["sources_represented"],
                        project_id=project_id or 0,
                    )
                except Exception as e:
                    logger.error(f"Error recording research session: {e}")

            # Update task statistics with aggregated data
            self.research_store.increment_task_stats(
                task_id, findings=total_findings, entities=entities_created, relations=0
            )

            # Mark task as completed (even if some agents failed)
            final_status = (
                ResearchStatus.COMPLETED if len(failed_agents) == 0 else ResearchStatus.COMPLETED
            )
            self.research_store.update_status(task_id, final_status)

            if self.on_status_updated:
                self.on_status_updated(task_id, final_status)

            result_msg = f"Research task {task_id} completed"
            if failed_agents:
                result_msg += f" ({len(failed_agents)} agents failed)"
            result_msg += f" with {total_findings} total findings"
            logger.info(result_msg)

            # PHASE 4: Automatic consolidation (Phase 3.3)
            # Trigger consolidation in background (non-blocking)
            try:
                asyncio.create_task(self._trigger_consolidation_async(task_id))
            except Exception as e:
                logger.warning(f"Failed to trigger consolidation: {e}")
                # Don't fail the research task if consolidation fails

            # Cache results if enabled
            if self.cache and aggregated_findings:
                cache_data = [
                    {
                        "title": f.title,
                        "summary": f.summary,
                        "url": f.url,
                        "source": f.primary_source,
                        "credibility_score": f.final_credibility,
                        "relevance_score": 0.85,
                    }
                    for f in aggregated_findings
                ]
                self.cache.set(topic, cache_data)

            # Complete metrics tracking
            task_metrics.complete(success=True, items_output=total_findings)

            return total_findings

        except Exception as e:
            logger.error(f"Error executing research task {task_id}: {e}", exc_info=True)
            self.research_store.update_status(task_id, ResearchStatus.FAILED)
            if self.on_status_updated:
                self.on_status_updated(task_id, ResearchStatus.FAILED)
            task_metrics.complete(success=False, error=str(e))
            raise

    async def _execute_agent_with_timeout(
        self,
        task_id: int,
        topic: str,
        agent_info: dict,
        constraints: Optional[QueryRefinement] = None,
    ) -> list[ResearchFinding]:
        """Execute single agent with timeout and circuit breaker protection.

        Args:
            task_id: Research task ID
            topic: Research topic
            agent_info: Agent configuration dict
            constraints: Optional QueryRefinement with search constraints

        Returns:
            List of findings from agent

        Raises:
            Exception: If agent times out, fails, or source is unhealthy
        """
        agent_name = agent_info["name"]
        source = agent_info["source"]
        credibility = agent_info["credibility"]

        # Check circuit breaker status
        breaker = self.circuit_breakers.get_breaker(source)
        if breaker.state.value == "open":
            logger.warning(f"Circuit breaker OPEN for {source} ({agent_name}). Skipping.")
            raise Exception(f"Circuit breaker open for {source}")

        try:
            # Execute agent research with circuit breaker and timeout protection
            def execute_agent_research():
                # Note: asyncio.run() doesn't work here since we're already in async context
                # Instead, we'll wrap the coroutine execution
                pass

            # Execute with 60-second timeout per agent
            findings = await asyncio.wait_for(
                self._simulate_agent_research(
                    task_id, topic, agent_name, source, credibility, constraints
                ),
                timeout=60.0,
            )

            # Record success in circuit breaker
            breaker.on_success()
            logger.debug(f"Circuit breaker success recorded for {source}")

            return findings
        except asyncio.TimeoutError:
            # Record timeout as failure
            breaker.on_failure()
            logger.warning(
                f"Agent {agent_name} timed out after 60 seconds - circuit breaker failure recorded"
            )
            raise Exception(f"Agent {agent_name} timeout")
        except Exception as e:
            # Record failure in circuit breaker
            breaker.on_failure()
            logger.warning(f"Agent {agent_name} error: {e} - circuit breaker failure recorded")
            raise

    async def _simulate_agent_research(
        self,
        task_id: int,
        topic: str,
        agent_name: str,
        source: str,
        credibility: float,
        constraints: Optional[QueryRefinement] = None,
    ) -> list[ResearchFinding]:
        """Execute agent research using specialized search strategies.

        Uses specialized agents per source to:
        1. Check rate limits
        2. Search the specific source (with optional constraints)
        3. Extract structured findings
        4. Score credibility
        5. Store to database

        Args:
            task_id: Research task ID
            topic: Research topic
            agent_name: Agent name
            source: Source name
            credibility: Base credibility score
            constraints: Optional QueryRefinement with search constraints
              - time_constraint: Filter by time range
              - quality_threshold: Minimum result quality
              - agent_directives: Per-agent instructions

        Returns:
            List of findings discovered
        """
        findings = []
        try:
            # Rate limiting: Check if request is allowed
            if self.rate_limiter:
                if not self.rate_limiter.allow_request(source):
                    # Rate limited - wait and try again
                    wait_time = self.rate_limiter.wait_if_needed(source)
                    logger.info(f"Rate limited for {source}. Waited {wait_time:.2f}s")

            # Get the agent class for this source
            if agent_name not in AGENT_CLASSES:
                logger.warning(f"Unknown agent: {agent_name}")
                return findings

            # Instantiate and execute agent search
            agent_class = AGENT_CLASSES[agent_name]
            agent = agent_class()

            # Start operation metrics tracking
            agent_metrics = self.metrics.start_operation(f"agent_search_{agent_name}")

            # Build search query with constraints
            search_query = topic
            if constraints:
                # Add time constraint to query
                if constraints.time_constraint:
                    search_query += f" {constraints.time_constraint}"
                    logger.debug(
                        f"Added time constraint to {agent_name}: {constraints.time_constraint}"
                    )

                # Get agent-specific directives if available
                if agent_name in constraints.agent_directives:
                    directives = constraints.agent_directives[agent_name]
                    logger.debug(f"Agent {agent_name} directives: {directives}")
                    # Directives are applied by the agent implementation
                    # (passed via metadata/context)

            # Execute search asynchronously
            search_results = await agent.search(search_query)
            agent_metrics.complete(
                success=True, items_output=len(search_results) if search_results else 0
            )

            # Store findings to database, filtering by quality threshold
            quality_threshold = constraints.quality_threshold if constraints else 0.5
            for result in search_results:
                result_quality = result.get("credibility", credibility)

                # Skip results below quality threshold
                if result_quality < quality_threshold:
                    logger.debug(
                        f"Skipping finding (quality {result_quality:.2f} < threshold {quality_threshold:.2f}): "
                        f"{result['title']}"
                    )
                    continue

                finding_id = self.record_finding(
                    task_id,
                    source=source,
                    title=result["title"],
                    summary=result["summary"],
                    url=result.get("url"),
                )
                findings.append(
                    ResearchFinding(
                        id=finding_id,
                        research_task_id=task_id,
                        source=source,
                        title=result["title"],
                        summary=result["summary"],
                        url=result.get("url"),
                        credibility_score=result_quality,
                    )
                )

            logger.info(
                f"Agent {agent_name} found {len(findings)} results for '{topic}' "
                f"(quality threshold: {quality_threshold:.2f})"
            )

        except Exception as e:
            logger.error(f"Error in agent research for {agent_name}: {e}", exc_info=True)
            # Record failure in metrics
            try:
                agent_metrics.complete(success=False, error=str(e))
            except (AttributeError, TypeError):
                pass  # Metrics tracking failed, but continue

        return findings

    def record_finding(
        self, task_id: int, source: str, title: str, summary: str, url: Optional[str] = None
    ) -> int:
        """Record a finding during research.

        Args:
            task_id: Research task ID
            source: Source of finding
            title: Finding title
            summary: Finding summary
            url: Optional URL to source

        Returns:
            Finding ID
        """
        finding = ResearchFinding(
            research_task_id=task_id,
            source=source,
            title=title,
            summary=summary,
            url=url,
            credibility_score=self._get_source_credibility(source),
        )

        finding_id = self.research_store.record_finding(finding)

        # Notify listeners
        if self.on_finding_discovered:
            finding.id = finding_id
            self.on_finding_discovered(finding)

        return finding_id

    def _get_source_credibility(self, source: str) -> float:
        """Get credibility score for a source.

        Args:
            source: Source name

        Returns:
            Credibility score (0.0-1.0)
        """
        for agent in self.RESEARCH_AGENTS:
            if agent["source"].lower() == source.lower():
                return agent["credibility"]
        return 0.5  # Default credibility

    def get_research_status(self, task_id: int) -> dict:
        """Get detailed research status.

        Args:
            task_id: Research task ID

        Returns:
            Status dictionary
        """
        task = self.research_store.get_task(task_id)
        if not task:
            return {}

        agent_progress_list = self.research_store.get_agent_progress(task_id)
        findings = self.research_store.get_task_findings(task_id)

        return {
            "task_id": task.id,
            "topic": task.topic,
            "status": task.status,
            "findings_count": task.findings_count,
            "entities_created": task.entities_created,
            "relations_created": task.relations_created,
            "agents": [
                {
                    "name": p.agent_name,
                    "status": p.status,
                    "findings_count": p.findings_count,
                    "started_at": p.started_at,
                    "completed_at": p.completed_at,
                }
                for p in agent_progress_list
            ],
            "findings_by_source": self._group_findings_by_source(findings),
            "timestamps": {
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
            },
        }

    def _group_findings_by_source(self, findings: list[ResearchFinding]) -> dict:
        """Group findings by source.

        Args:
            findings: List of findings

        Returns:
            Dictionary mapping source to finding count
        """
        by_source = {}
        for finding in findings:
            if finding.source not in by_source:
                by_source[finding.source] = 0
            by_source[finding.source] += 1
        return by_source

    def get_diagnostics(self) -> dict:
        """Get comprehensive diagnostics for the research executor.

        Returns:
            Diagnostics dict with cache, rate limit, metrics, and circuit breaker status
        """
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
        }

        # Cache diagnostics
        if self.cache:
            diagnostics["cache"] = self.cache.get_stats()
        else:
            diagnostics["cache"] = {"enabled": False}

        # Rate limiting diagnostics
        if self.rate_limiter:
            diagnostics["rate_limiting"] = self.rate_limiter.get_stats()
        else:
            diagnostics["rate_limiting"] = {"enabled": False}

        # Metrics diagnostics
        diagnostics["metrics"] = self.metrics.get_all_stats()

        # Circuit breaker diagnostics
        diagnostics["circuit_breakers"] = self.circuit_breakers.get_all_status()
        diagnostics["healthy_sources"] = self.circuit_breakers.get_healthy_sources()
        diagnostics["failing_sources"] = self.circuit_breakers.get_failing_sources()

        return diagnostics

    def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Cache stats or empty dict if caching disabled
        """
        if self.cache:
            return self.cache.get_stats()
        return {"enabled": False}

    def get_metrics_summary(self) -> dict:
        """Get metrics summary.

        Returns:
            Metrics summary
        """
        return self.metrics.get_all_stats()

    def get_source_health(self) -> dict:
        """Get health status of all research sources.

        Returns:
            Health status dict
        """
        return {
            "healthy": self.circuit_breakers.get_healthy_sources(),
            "failing": self.circuit_breakers.get_failing_sources(),
            "details": self.circuit_breakers.get_all_status(),
        }

    # =========================================================================
    # PHASE 3.4: REAL-TIME STREAMING
    # =========================================================================

    def enable_streaming(self, on_streaming_update: Callable[[StreamingUpdate], Any]) -> None:
        """Enable real-time streaming of research results.

        Args:
            on_streaming_update: Callback called when streaming update available
        """
        self.on_streaming_update = on_streaming_update
        logger.info("Real-time streaming enabled")

    async def set_up_streaming(self, task_id: int, topic: str) -> None:
        """Initialize streaming for a research task.

        Args:
            task_id: Research task ID
            topic: Research topic
        """
        self.streaming_collector = StreamingResultCollector(
            task_id=task_id, query=topic, batch_size=5
        )
        self.agent_monitor = LiveAgentMonitor()
        logger.info(f"Streaming initialized for task {task_id}")

    async def add_finding_to_stream(self, finding: ResearchFinding, agent_name: str) -> None:
        """Add finding to streaming collector.

        Args:
            finding: Finding to add
            agent_name: Agent that discovered it
        """
        if not self.streaming_collector:
            return

        # Add to streaming collector
        update = await self.streaming_collector.add_finding_async(finding, agent_name)

        # Record discovery in agent monitor
        if self.agent_monitor:
            await self.agent_monitor.record_discovery(agent_name, latency_ms=0)

        # Stream update if batch ready
        if update and self.on_streaming_update:
            try:
                self.on_streaming_update(update)
            except Exception as e:
                logger.warning(f"Failed to call streaming update callback: {e}")

    async def finalize_streaming(self) -> StreamingUpdate:
        """Finalize streaming and return final update.

        Returns:
            Final StreamingUpdate with all findings
        """
        if not self.streaming_collector:
            return None

        return await self.streaming_collector.finalize()

    # =========================================================================
    # PHASE 3.3: CONSOLIDATION INTEGRATION
    # =========================================================================

    async def _trigger_consolidation_async(self, task_id: int) -> None:
        """Trigger automatic consolidation on research task completion.

        Runs in background (non-blocking). Consolidates findings into:
        - Research patterns (11 types)
        - Domain expertise
        - Source credibility maps
        - Quality thresholds
        - Search strategies
        - Knowledge graph entities/relations

        Args:
            task_id: Research task ID to consolidate
        """
        try:
            logger.info(f"Triggering automatic consolidation for task {task_id}")

            # Get database instance (from research_store's db)
            if not hasattr(self.research_store, "db") or self.research_store.db is None:
                logger.warning("Database not available for consolidation")
                return

            db = self.research_store.db

            # Initialize consolidation stores and systems
            consolidation_store = ResearchConsolidationStore(db)
            consolidation_system = ResearchConsolidationSystem(
                db=db,
                research_store=self.research_store,
                consolidation_store=consolidation_store,
                procedural_store=None,  # Optional - will be set if available
                graph_store=None,  # Optional - will be set if available
                meta_store=None,  # Optional - will be set if available
            )

            # Run consolidation (sync method, but safe to call from async context)
            result = consolidation_system.consolidate_research_task(task_id)

            logger.info(
                f"Consolidation completed for task {task_id}: "
                f"{result.patterns_extracted} patterns, "
                f"{result.procedures_created} procedures, "
                f"{result.entities_created} entities"
            )

        except Exception as e:
            logger.error(f"Consolidation failed for task {task_id}: {e}")
            # Don't raise - consolidation failure shouldn't impact research task
