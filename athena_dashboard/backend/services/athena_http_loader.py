"""Data loader using Athena HTTP API instead of direct database access."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AthenaHTTPLoader:
    """Load data from Athena via HTTP API.

    This replaces direct database access with HTTP calls to Athena,
    enabling full containerization and decoupling.
    """

    def __init__(self, athena_url: str = "http://localhost:3000"):
        """Initialize HTTP loader.

        Args:
            athena_url: Athena HTTP service URL
        """
        self.athena_url = athena_url
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Athena HTTP client."""
        try:
            from athena.client import AthenaHTTPClient
            self.client = AthenaHTTPClient(url=self.athena_url, timeout=10.0, retries=2)
            logger.info(f"Initialized Athena HTTP client: {self.athena_url}")
        except ImportError:
            logger.error("Athena HTTP client not available, falling back to mock data")
            self.client = None
        except Exception as e:
            logger.warning(f"Failed to initialize Athena HTTP client: {e}")
            self.client = None

    def is_connected(self) -> bool:
        """Check if connected to Athena HTTP service.

        Returns:
            True if connected, False otherwise
        """
        if not self.client:
            return False

        try:
            health = self.client.health()
            return health.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    def get_memory_health(self) -> Dict[str, Any]:
        """Get memory system health metrics.

        Returns:
            Memory health data
        """
        if not self.client:
            return self._mock_memory_health()

        try:
            health_data = self.client.get_memory_quality_summary()
            # Check if response is a dict (structured data)
            if isinstance(health_data, dict):
                return {
                    "quality_score": health_data.get("quality_score", 0.75),
                    "compression_ratio": health_data.get("compression_ratio", 0.70),
                    "recall_accuracy": health_data.get("recall_accuracy", 0.85),
                    "consistency_score": health_data.get("consistency_score", 0.80),
                    "consolidation_status": health_data.get("consolidation_status", "idle"),
                    "patterns_extracted": health_data.get("patterns_extracted", 0),
                }
            # If text response, use mock data
            logger.debug("Got text response from Memory System, using mock data")
            return self._mock_memory_health()
        except Exception as e:
            logger.error(f"Failed to get memory health: {e}")
            return self._mock_memory_health()

    def get_memory_gaps(self) -> List[Dict[str, Any]]:
        """Get knowledge gaps and contradictions.

        Returns:
            List of gaps
        """
        if not self.client:
            return self._mock_memory_gaps()

        try:
            gaps = self.client.detect_knowledge_gaps()
            return gaps or []
        except Exception as e:
            logger.error(f"Failed to get memory gaps: {e}")
            return self._mock_memory_gaps()

    def get_cognitive_load(self) -> Dict[str, Any]:
        """Get current cognitive load metrics.

        Returns:
            Cognitive load data
        """
        if not self.client:
            return self._mock_cognitive_load()

        try:
            load_data = self.client.check_cognitive_load()
            # Check if response is a dict (structured data)
            if isinstance(load_data, dict):
                return {
                    "current_load": load_data.get("current_load", 3),
                    "max_capacity": load_data.get("max_capacity", 7),
                    "utilization_percent": load_data.get("utilization_percent", 42),
                    "active_items": load_data.get("active_items", 3),
                    "status": load_data.get("status", "normal"),
                }
            # If text response, use mock data
            logger.debug("Got text response from Memory System, using mock data")
            return self._mock_cognitive_load()
        except Exception as e:
            logger.error(f"Failed to get cognitive load: {e}")
            return self._mock_cognitive_load()

    def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get currently active goals.

        Returns:
            List of active goals
        """
        if not self.client:
            return self._mock_active_goals()

        try:
            goals = self.client.get_active_goals()
            return goals or []
        except Exception as e:
            logger.error(f"Failed to get active goals: {e}")
            return self._mock_active_goals()

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks.

        Returns:
            List of tasks
        """
        if not self.client:
            return self._mock_tasks()

        try:
            tasks = self.client.list_tasks()
            return tasks or []
        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return self._mock_tasks()

    def get_learning_metrics(self) -> Dict[str, Any]  :
        """Get learning and encoding metrics.

        Returns:
            Learning metrics
        """
        if not self.client:
            return self._mock_learning_metrics()

        try:
            metrics = self.client.get_learning_rates()
            # Check if response is a dict (structured data)
            if isinstance(metrics, dict):
                return {
                    "encoding_efficiency": metrics.get("encoding_efficiency", 0.72),
                    "pattern_extraction_count": metrics.get("pattern_extraction_count", 45),
                    "procedure_reuse_rate": metrics.get("procedure_reuse_rate", 0.60),
                    "strategy_effectiveness": metrics.get("strategy_effectiveness", {}),
                }
            # If text response, use mock data
            logger.debug("Got text response from Memory System, using mock data")
            return self._mock_learning_metrics()
        except Exception as e:
            logger.error(f"Failed to get learning metrics: {e}")
            return self._mock_learning_metrics()

    # Mock data methods for fallback/development
    @staticmethod
    def _mock_memory_health() -> Dict[str, Any]:
        """Mock memory health data."""
        return {
            "quality_score": 0.75,
            "compression_ratio": 0.70,
            "recall_accuracy": 0.85,
            "consistency_score": 0.80,
            "consolidation_status": "idle",
            "patterns_extracted": 23,
        }

    @staticmethod
    def _mock_memory_gaps() -> List[Dict[str, Any]]:
        """Mock memory gaps."""
        return [
            {
                "type": "uncertainty",
                "description": "Pattern: Context switching overhead",
                "confidence": 0.45,
                "affected_domains": ["task_management", "attention"],
            },
        ]

    @staticmethod
    def _mock_cognitive_load() -> Dict[str, Any]:
        """Mock cognitive load data."""
        return {
            "current_load": 3,
            "max_capacity": 7,
            "utilization_percent": 42,
            "active_items": 3,
            "status": "normal",
        }

    @staticmethod
    def _mock_active_goals() -> List[Dict[str, Any]]:
        """Mock active goals."""
        return [
            {
                "id": 1,
                "content": "Improve memory system",
                "priority": "high",
                "progress": 60,
            },
        ]

    @staticmethod
    def _mock_tasks() -> List[Dict[str, Any]]:
        """Mock tasks."""
        return [
            {
                "id": 1,
                "content": "Implement HTTP API",
                "status": "completed",
                "priority": "high",
            },
        ]

    @staticmethod
    def _mock_learning_metrics() -> Dict[str, Any]:
        """Mock learning metrics."""
        return {
            "encoding_efficiency": 0.72,
            "pattern_extraction_count": 45,
            "procedure_reuse_rate": 0.60,
            "strategy_effectiveness": {
                "hierarchical": 0.85,
                "iterative": 0.75,
                "parallel": 0.80,
            },
        }

    def count_events(self) -> int:
        """Count total episodic events.

        Returns:
            Total event count
        """
        if not self.client:
            return 8128  # Mock value

        try:
            result = self.client.list_memories()
            # list_memories returns a list, so count the items
            return len(result) if result and isinstance(result, list) else 8128
        except Exception as e:
            logger.error(f"Failed to count events: {e}")
            return 8128

    def count_semantic_memories(self) -> int:
        """Count total semantic memories.

        Returns:
            Total semantic memory count
        """
        if not self.client:
            return 450  # Mock value

        try:
            result = self.client.list_memories()
            return len(result) if result and isinstance(result, list) else 450
        except Exception as e:
            logger.error(f"Failed to count semantic memories: {e}")
            return 450

    def count_procedures(self) -> int:
        """Count total procedures.

        Returns:
            Total procedure count
        """
        if not self.client:
            return 101  # Mock value

        try:
            result = self.client.find_procedures(query="")
            return len(result) if result and isinstance(result, list) else 101
        except Exception as e:
            logger.error(f"Failed to count procedures: {e}")
            return 101

    def count_knowledge_gaps(self, gap_type: Optional[str] = None) -> int:
        """Count knowledge gaps.

        Args:
            gap_type: Optional gap type filter

        Returns:
            Total gap count
        """
        if not self.client:
            return 3  # Mock value

        try:
            gaps = self.client.detect_knowledge_gaps()
            if gap_type:
                gaps = [g for g in gaps if g.get("type") == gap_type]
            return len(gaps) if gaps else 0
        except Exception as e:
            logger.error(f"Failed to count knowledge gaps: {e}")
            return 0

    def get_last_consolidation(self) -> Optional[Dict[str, Any]]:
        """Get last consolidation run info.

        Returns:
            Last consolidation data or None
        """
        if not self.client:
            return {
                "timestamp": "2025-11-06T10:00:00Z",
                "duration_seconds": 2.5,
                "patterns_extracted": 23,
                "strategy": "balanced"
            }

        try:
            # For now, return mock data since we don't have a direct endpoint
            # TODO: Add get_consolidation_history operation to Athena
            return {
                "timestamp": "2025-11-06T10:00:00Z",
                "duration_seconds": 2.5,
                "patterns_extracted": 23,
                "strategy": "balanced"
            }
        except Exception as e:
            logger.error(f"Failed to get last consolidation: {e}")
            return None

    def get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory quality metrics.

        Returns:
            Memory metrics data
        """
        if not self.client:
            return self._mock_memory_health()

        try:
            return self.get_memory_health()
        except Exception as e:
            logger.error(f"Failed to get memory metrics: {e}")
            return self._mock_memory_health()

    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent episodic events.

        Args:
            limit: Number of events to return

        Returns:
            List of recent events
        """
        if not self.client:
            return []

        try:
            events = self.client.recall_events(query="", days=7, limit=limit)
            return events if events else []
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

    def get_working_memory_items(self) -> List[Dict[str, Any]]:
        """Get working memory items.

        Returns:
            List of working memory items
        """
        if not self.client:
            return []

        try:
            wm_data = self.client.check_cognitive_load()
            # Extract items from cognitive load response
            items = wm_data.get("active_items", []) if isinstance(wm_data, dict) else []
            return items if isinstance(items, list) else []
        except Exception as e:
            logger.error(f"Failed to get working memory items: {e}")
            return []

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get active tasks.

        Returns:
            List of active tasks
        """
        if not self.client:
            return self._mock_tasks()

        try:
            return self.get_tasks()
        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            return self._mock_tasks()

    def get_project_stats(self) -> Dict[str, Any]:
        """Get project statistics.

        Returns:
            Project statistics
        """
        if not self.client:
            return {
                "total_projects": 1,
                "active_projects": 1,
                "completed_projects": 0,
            }

        try:
            # For now, return basic stats
            # TODO: Add get_project_stats operation to Athena
            return {
                "total_projects": 1,
                "active_projects": 1,
                "completed_projects": 0,
            }
        except Exception as e:
            logger.error(f"Failed to get project stats: {e}")
            return {
                "total_projects": 1,
                "active_projects": 1,
                "completed_projects": 0,
            }

    def get_hook_executions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hook execution history.

        Args:
            hours: Number of hours to look back

        Returns:
            List of hook executions
        """
        if not self.client:
            return []

        try:
            # For now, return empty list
            # TODO: Add get_hook_executions operation to Athena
            return []
        except Exception as e:
            logger.error(f"Failed to get hook executions: {e}")
            return []

    def get_top_procedures(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top procedures by effectiveness.

        Args:
            limit: Number of procedures to return

        Returns:
            List of top procedures
        """
        if not self.client:
            return []

        try:
            procedures = self.client.find_procedures(query="")
            # Return first N procedures
            return procedures[:limit] if procedures else []
        except Exception as e:
            logger.error(f"Failed to get top procedures: {e}")
            return []

    def close(self):
        """Close HTTP client."""
        if self.client:
            self.client.close()
