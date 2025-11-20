"""Visualization helpers for memory flow analysis.

Provides methods to generate data for visualization of:
- Tier distribution over time
- Activation decay curves
- Consolidation progress
- RIF effects on similar items
"""

import logging
from datetime import datetime

from .metrics import FlowMetricsTracker
from ..core.database import Database

logger = logging.getLogger(__name__)


class FlowVisualizationHelper:
    """Helper for generating visualization data."""

    def __init__(self, db: Database):
        """Initialize visualization helper.

        Args:
            db: Database instance
        """
        self.db = db
        self.metrics = FlowMetricsTracker(db)

    async def get_tier_distribution_chart_data(self, hours: int = 24) -> dict:
        """Get data for tier distribution visualization.

        Returns data suitable for a pie chart or bar chart showing
        how many items are in each tier.

        Args:
            hours: Time period to analyze

        Returns:
            Dict with chart data
        """
        try:
            distribution = await self.metrics.get_tier_distribution(hours)

            # Format for chart
            labels = []
            data = []
            colors = {
                "active": "#4CAF50",  # Green
                "session": "#2196F3",  # Blue
                "archived": "#9E9E9E",  # Gray
            }

            for tier, count in sorted(distribution.items()):
                labels.append(tier.capitalize())
                data.append(count)

            return {
                "type": "pie",
                "labels": labels,
                "data": data,
                "colors": [colors.get(tier, "#999") for tier in distribution.keys()],
                "title": f"Memory Tier Distribution (last {hours}h)",
            }
        except Exception as e:
            logger.error(f"Error generating tier distribution chart: {e}")
            return {}

    async def get_activation_decay_chart_data(self, event_id: int, hours: int = 24) -> dict:
        """Get data for activation decay curve visualization.

        Shows how an item's activation decreases over time due to
        temporal decay and interference.

        Args:
            event_id: ID of event to analyze
            hours: Time period

        Returns:
            Dict with chart data
        """
        try:
            timeline = await self.metrics.get_activation_timeline(event_id, hours)

            if not timeline:
                return {}

            timestamps = []
            activations = []
            interference = []

            for record in timeline:
                # Format timestamp for display
                ts = record["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                timestamps.append(ts.strftime("%H:%M"))

                activations.append(record["activation_value"])
                interference.append(record["interference_factor"])

            return {
                "type": "line",
                "labels": timestamps,
                "datasets": [
                    {
                        "label": "Activation",
                        "data": activations,
                        "color": "#4CAF50",
                        "fill": False,
                    },
                    {
                        "label": "Interference Factor",
                        "data": interference,
                        "color": "#FF6B6B",
                        "fill": False,
                    },
                ],
                "title": f"Activation Decay: Event {event_id}",
            }
        except Exception as e:
            logger.error(f"Error generating decay chart: {e}")
            return {}

    async def get_consolidation_progress_data(self, hours: int = 24) -> dict:
        """Get data showing consolidation progress over time.

        Shows:
        - Mean activation level
        - Items promoted to semantic (consolidation > 0.7)
        - Items decayed (consolidation < 0.4)

        Args:
            hours: Time period to analyze

        Returns:
            Dict with visualization data
        """
        try:
            metrics = await self.metrics.get_consolidation_metrics(hours)

            if not metrics:
                return {}

            return {
                "type": "gauge",
                "metrics": {
                    "mean_activation": metrics.get("mean_activation", 0),
                    "promoted_count": metrics.get("promoted_to_semantic", 0),
                    "decayed_count": metrics.get("decayed_items", 0),
                    "total_events": metrics.get("total_events", 0),
                },
                "title": f"Consolidation Progress (last {hours}h)",
                "summary": (
                    f"Mean activation: {metrics.get('mean_activation', 0):.2f} | "
                    f"Promoted: {metrics.get('promoted_to_semantic', 0)} | "
                    f"Decayed: {metrics.get('decayed_items', 0)}"
                ),
            }
        except Exception as e:
            logger.error(f"Error generating consolidation data: {e}")
            return {}

    async def get_rif_analysis_chart_data(self, hours: int = 24) -> dict:
        """Get data for RIF (Retrieval-Induced Forgetting) analysis.

        Shows the suppression effect of RIF on similar items.

        Args:
            hours: Time period to analyze

        Returns:
            Dict with chart data
        """
        try:
            rif_data = await self.metrics.get_interference_analysis(hours)

            if not rif_data:
                return {}

            return {
                "type": "gauge",
                "metrics": {
                    "mean_interference": rif_data.get("mean_interference", 1.0),
                    "min_interference": rif_data.get("min_interference", 1.0),
                    "suppressed_items": rif_data.get("suppressed_items", 0),
                },
                "title": f"RIF Analysis (last {hours}h)",
                "summary": (
                    f"Mean suppression: {(1 - rif_data.get('mean_interference', 1.0)) * 100:.1f}% | "
                    f"Suppressed items: {rif_data.get('suppressed_items', 0)}"
                ),
            }
        except Exception as e:
            logger.error(f"Error generating RIF chart: {e}")
            return {}

    async def get_access_pattern_data(self, hours: int = 24, top_n: int = 10) -> dict:
        """Get data showing access patterns.

        Shows which items are accessed most frequently.

        Args:
            hours: Time period to analyze
            top_n: Number of top items to show

        Returns:
            Dict with chart data
        """
        try:
            patterns = await self.metrics.get_access_patterns(hours, top_n)

            if not patterns:
                return {}

            event_ids = [f"Event {p['event_id']}" for p in patterns]
            access_counts = [p["access_count"] for p in patterns]

            return {
                "type": "bar",
                "labels": event_ids,
                "data": access_counts,
                "title": f"Top {top_n} Most Accessed Items (last {hours}h)",
                "color": "#FF9800",
            }
        except Exception as e:
            logger.error(f"Error generating access pattern data: {e}")
            return {}

    async def get_memory_health_dashboard(self, hours: int = 24) -> dict:
        """Get comprehensive memory health dashboard data.

        Combines multiple metrics into a single dashboard view.

        Args:
            hours: Time period to analyze

        Returns:
            Dict with dashboard data
        """
        try:
            # Gather all metrics
            consolidation = await self.metrics.get_consolidation_metrics(hours)
            rif = await self.metrics.get_interference_analysis(hours)
            distribution = await self.metrics.get_tier_distribution(hours)

            return {
                "timestamp": datetime.now().isoformat(),
                "period_hours": hours,
                "consolidation": consolidation,
                "rif": rif,
                "tier_distribution": distribution,
                "summary": {
                    "total_events": consolidation.get("total_events", 0),
                    "mean_activation": consolidation.get("mean_activation", 0),
                    "working_memory_size": distribution.get("active", 0),
                    "session_cache_size": distribution.get("session", 0),
                    "suppression_rate": ((1 - rif.get("mean_interference", 1.0)) * 100),
                },
            }
        except Exception as e:
            logger.error(f"Error generating health dashboard: {e}")
            return {}
