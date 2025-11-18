"""Memory integration for code analysis - episodic, semantic, and knowledge graph."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from ..episodic.models import EpisodicEvent, EventType, CodeEventType, EventOutcome, EventContext
from ..graph.models import Entity

logger = logging.getLogger(__name__)


class CodeAnalysisMemory:
    """
    Integrates code analysis with Athena memory system.

    Records:
    - Episodic memory: Code analysis as temporal events
    - Semantic memory: Insights and patterns about code
    - Knowledge graph: Code entities and relationships
    - Consolidation: Patterns extracted from multiple analyses
    """

    def __init__(
        self,
        episodic_store=None,
        semantic_store=None,
        graph_store=None,
        consolidator=None,
        project_id: int = 0,
        session_id: Optional[str] = None,
    ):
        """
        Initialize code analysis memory integration.

        Args:
            episodic_store: EpisodicStore for recording analysis events
            semantic_store: SemanticStore for storing insights
            graph_store: GraphStore for storing code entities
            consolidator: Consolidator for pattern extraction
            project_id: Project identifier
            session_id: Session identifier (auto-generated if not provided)
        """
        self.episodic_store = episodic_store
        self.semantic_store = semantic_store
        self.graph_store = graph_store
        self.consolidator = consolidator
        self.project_id = project_id
        self.session_id = session_id or str(uuid4())

    def record_code_analysis(
        self,
        repo_path: str,
        analysis_results: Dict[str, Any],
        duration_ms: int,
        file_count: int = 0,
        unit_count: int = 0,
    ) -> Optional[int]:
        """
        Record code analysis as episodic event.

        Args:
            repo_path: Path to analyzed repository
            analysis_results: Dictionary with analysis findings
            duration_ms: Time taken for analysis
            file_count: Number of files analyzed
            unit_count: Number of code units analyzed

        Returns:
            Event ID if recorded, None if no episodic store
        """
        if not self.episodic_store:
            logger.debug("Episodic store not available, skipping event recording")
            return None

        try:
            # Prepare event content
            summary = self._summarize_analysis(analysis_results)

            # Create episodic event
            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self.session_id,
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                code_event_type=CodeEventType.CODE_REVIEW,
                content=json.dumps(
                    {
                        "repo_path": str(repo_path),
                        "summary": summary,
                        "analysis_results": analysis_results,
                    }
                ),
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    cwd=str(repo_path),
                    files=[repo_path],
                    phase="code_analysis",
                ),
                duration_ms=duration_ms,
                files_changed=file_count,
                performance_metrics={
                    "files_analyzed": file_count,
                    "units_analyzed": unit_count,
                    "duration_ms": duration_ms,
                    "units_per_second": (unit_count / duration_ms * 1000) if duration_ms > 0 else 0,
                },
                code_quality_score=analysis_results.get("quality_score", 0.5),
                learned=self._extract_learnings(analysis_results),
                confidence=0.9,
            )

            # Store event
            event_id = self.episodic_store.store_event(event)
            logger.info(f"Recorded code analysis event {event_id} for {repo_path}")

            return event_id

        except Exception as e:
            logger.error(f"Failed to record code analysis event: {e}")
            return None

    def store_code_insights(
        self,
        analysis_results: Dict[str, Any],
        repo_path: str,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Store analysis insights in semantic memory.

        Args:
            analysis_results: Analysis results dictionary
            repo_path: Path to analyzed repository
            tags: Optional tags for the insights

        Returns:
            True if stored successfully, False otherwise
        """
        if not self.semantic_store:
            logger.debug("Semantic store not available, skipping insight storage")
            return False

        try:
            tags = tags or ["code_analysis", "insights"]

            # Create insights from analysis results
            insights = [
                f"Code quality score: {analysis_results.get('quality_score', 0.5):.2f}",
                f"Complexity average: {analysis_results.get('complexity_avg', 0):.2f}",
                f"Test coverage: {analysis_results.get('test_coverage', 'N/A')}",
                f"Found {len(analysis_results.get('issues', []))} issues",
            ]

            # Store each insight
            for insight in insights:
                try:
                    self.semantic_store.remember(
                        content=insight,
                        tags=tags + ["code_analysis"],
                        metadata={
                            "repo": str(repo_path),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                except Exception as e:
                    logger.warning(f"Failed to store insight: {e}")

            logger.info(f"Stored {len(insights)} insights for {repo_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to store code insights: {e}")
            return False

    def add_code_entities_to_graph(
        self,
        code_units: List[Dict[str, Any]],
        repo_path: str,
    ) -> int:
        """
        Add discovered code entities to knowledge graph.

        Args:
            code_units: List of code unit dictionaries from analysis
            repo_path: Path to analyzed repository

        Returns:
            Number of entities added
        """
        if not self.graph_store:
            logger.debug("Graph store not available, skipping entity recording")
            return 0

        count = 0
        try:
            for unit in code_units:
                try:
                    # Create entity for code unit
                    entity = Entity(
                        name=unit.get("name", ""),
                        entity_type=unit.get("type", "code_unit"),
                        description=unit.get("docstring", ""),
                        metadata={
                            "repo": str(repo_path),
                            "file": unit.get("file", ""),
                            "line": unit.get("line", 0),
                            "language": unit.get("language", ""),
                            "complexity": unit.get("complexity", 0),
                        },
                    )

                    # Store entity
                    self.graph_store.add_entity(entity)
                    count += 1

                except Exception as e:
                    logger.warning(f"Failed to add entity {unit.get('name', 'unknown')}: {e}")

            logger.info(f"Added {count} code entities to graph for {repo_path}")

        except Exception as e:
            logger.error(f"Failed to add code entities to graph: {e}")

        return count

    def record_code_metrics_trend(
        self,
        metrics: Dict[str, float],
        repo_path: str,
    ) -> bool:
        """
        Record code quality metrics for trend analysis.

        Args:
            metrics: Dictionary of metric_name -> value
            repo_path: Path to analyzed repository

        Returns:
            True if recorded successfully
        """
        if not self.episodic_store:
            logger.debug("Episodic store not available for metrics recording")
            return False

        try:
            event = EpisodicEvent(
                project_id=self.project_id,
                session_id=self.session_id,
                timestamp=datetime.now(),
                event_type=EventType.ACTION,
                code_event_type=CodeEventType.PERFORMANCE_PROFILE,
                content=json.dumps(
                    {
                        "repo_path": str(repo_path),
                        "metrics": metrics,
                    }
                ),
                outcome=EventOutcome.SUCCESS,
                context=EventContext(
                    cwd=str(repo_path),
                    phase="metrics_tracking",
                ),
                performance_metrics=metrics,
            )

            self.episodic_store.store_event(event)
            logger.info(f"Recorded metrics event for {repo_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
            return False

    def extract_analysis_patterns(
        self,
        days_back: int = 7,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract patterns from multiple code analyses using consolidation.

        Args:
            days_back: Number of days of analysis events to consolidate

        Returns:
            Dictionary with extracted patterns, or None if consolidator not available
        """
        if not self.consolidator or not self.episodic_store:
            logger.debug("Consolidator/episodic store not available")
            return None

        try:
            # Get all code review events from the past N days
            events = self.episodic_store.get_events_by_type(
                event_type=EventType.ACTION,
                code_event_type=CodeEventType.CODE_REVIEW,
                days_back=days_back,
                project_id=self.project_id,
            )

            if not events:
                logger.info(f"No code analysis events in past {days_back} days")
                return None

            # Run consolidation to extract patterns
            patterns = self.consolidator.consolidate(
                events=events,
                strategy="code_metrics",
            )

            logger.info(f"Extracted patterns from {len(events)} code analysis events")
            return patterns

        except Exception as e:
            logger.error(f"Failed to extract analysis patterns: {e}")
            return None

    # Helper methods

    def _summarize_analysis(self, analysis_results: Dict[str, Any]) -> str:
        """Create a summary of analysis results."""
        quality = analysis_results.get("quality_score", 0)
        issues = len(analysis_results.get("issues", []))
        complexity = analysis_results.get("complexity_avg", 0)

        return (
            f"Code Quality: {quality:.2%}, Issues: {issues}, " f"Avg Complexity: {complexity:.2f}"
        )

    def _extract_learnings(self, analysis_results: Dict[str, Any]) -> str:
        """Extract key learnings from analysis."""
        learnings = []

        if analysis_results.get("quality_score", 0) < 0.5:
            learnings.append("Code quality is below target - consider refactoring")

        if len(analysis_results.get("issues", [])) > 10:
            learnings.append("High number of issues detected - prioritize fixes")

        if analysis_results.get("complexity_avg", 0) > 5:
            learnings.append("High average complexity - break down complex functions")

        # Handle test_coverage as string or float
        test_coverage = analysis_results.get("test_coverage", "N/A")
        if isinstance(test_coverage, (int, float)) and test_coverage < 0.7:
            learnings.append("Test coverage below 70% - add more tests")
        elif isinstance(test_coverage, str) and test_coverage != "N/A":
            try:
                coverage_value = float(test_coverage.rstrip("%")) / 100
                if coverage_value < 0.7:
                    learnings.append("Test coverage below 70% - add more tests")
            except (ValueError, AttributeError):
                pass

        return "; ".join(learnings) if learnings else "Analysis complete"


class CodeAnalysisMemoryManager:
    """Manager for code analysis memory integration with unified interface."""

    def __init__(self, memory_manager=None):
        """
        Initialize manager with unified memory system.

        Args:
            memory_manager: UnifiedMemoryManager instance
        """
        self.memory_manager = memory_manager
        self.analysis_memory = None

        if memory_manager:
            self._initialize_from_manager()

    def _initialize_from_manager(self):
        """Initialize CodeAnalysisMemory from UnifiedMemoryManager."""
        try:
            self.analysis_memory = CodeAnalysisMemory(
                episodic_store=self.memory_manager.episodic_store,
                semantic_store=self.memory_manager.semantic_store,
                graph_store=self.memory_manager.graph_store,
                consolidator=self.memory_manager.consolidator,
                project_id=getattr(self.memory_manager, "project_id", 0),
                session_id=getattr(self.memory_manager, "session_id", None),
            )
            logger.info("Initialized CodeAnalysisMemory from UnifiedMemoryManager")
        except Exception as e:
            logger.warning(f"Failed to initialize CodeAnalysisMemory: {e}")

    def record_analysis(self, **kwargs) -> Optional[int]:
        """Record code analysis event."""
        if not self.analysis_memory:
            return None
        return self.analysis_memory.record_code_analysis(**kwargs)

    def store_insights(self, **kwargs) -> bool:
        """Store analysis insights to semantic memory."""
        if not self.analysis_memory:
            return False
        return self.analysis_memory.store_code_insights(**kwargs)

    def add_entities(self, **kwargs) -> int:
        """Add code entities to knowledge graph."""
        if not self.analysis_memory:
            return 0
        return self.analysis_memory.add_code_entities_to_graph(**kwargs)

    def extract_patterns(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Extract patterns from code analyses."""
        if not self.analysis_memory:
            return None
        return self.analysis_memory.extract_analysis_patterns(**kwargs)
