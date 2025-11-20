"""
Monitor Dashboard for Agent Status

Live monitoring dashboard showing:
- Agent status and health
- Task progress and queue
- Overall orchestration metrics
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class MonitorDashboard:
    """Live dashboard for agent coordination monitoring."""

    def __init__(self, db, refresh_interval_seconds: int = 2):
        """
        Initialize monitor.

        Args:
            db: Database connection
            refresh_interval_seconds: How often to refresh display
        """
        self.db = db
        self.refresh_interval_seconds = refresh_interval_seconds
        self.is_running = False

    async def run(self) -> None:
        """Start the monitoring loop."""
        self.is_running = True

        while self.is_running:
            try:
                # Clear screen
                os.system("clear" if os.name != "nt" else "cls")

                # Render dashboard
                await self._render_dashboard()

                await asyncio.sleep(self.refresh_interval_seconds)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(self.refresh_interval_seconds)

        self.is_running = False

    async def _render_dashboard(self) -> None:
        """Render the dashboard to stdout."""
        # Header
        self._print_header()

        # Agent status
        print()
        await self._print_agent_status()

        # Task status
        print()
        await self._print_task_status()

        # Orchestration metrics
        print()
        await self._print_metrics()

        # Footer
        print()
        self._print_footer()

    def _print_header(self) -> None:
        """Print dashboard header."""
        print("=" * 100)
        print("ATHENA AGENT COORDINATION MONITOR".center(100))
        print("=" * 100)
        print(f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()

    async def _print_agent_status(self) -> None:
        """Print agent status table."""
        print("AGENTS".ljust(50) + "Status".ljust(15) + "Task ID".ljust(25) + "Heartbeat")
        print("-" * 100)

        agents = await self.db.fetch(
            """
            SELECT agent_id, agent_type, status, current_task_id, last_heartbeat
            FROM agents
            ORDER BY created_at ASC
            """
        )

        if not agents:
            print("  (no agents)")
            return

        for agent in agents:
            agent_id = agent["agent_id"][:30]
            status = agent["status"]
            task_id = (agent["current_task_id"] or "-")[:20]

            # Status indicator
            if status == "idle":
                status_str = "🟢 idle"
            elif status == "busy":
                status_str = "🟡 busy"
            elif status == "failed":
                status_str = "🔴 failed"
            else:
                status_str = "⚫ offline"

            # Heartbeat indicator
            if agent["last_heartbeat"]:
                elapsed = (datetime.now(timezone.utc) - agent["last_heartbeat"]).total_seconds()
                if elapsed < 60:
                    heartbeat_str = f"{int(elapsed)}s ago ✓"
                else:
                    heartbeat_str = f"{int(elapsed/60)}m ago ✗"
            else:
                heartbeat_str = "never"

            print(
                f"  {agent_id:<48} {status_str:<15} {task_id:<25} {heartbeat_str}"
            )

    async def _print_task_status(self) -> None:
        """Print task status summary."""
        print("TASKS".ljust(50) + "Status".ljust(15) + "Progress".ljust(25))
        print("-" * 100)

        task_counts = await self.db.fetch(
            """
            SELECT status, COUNT(*) as count
            FROM prospective_tasks
            GROUP BY status
            ORDER BY status
            """
        )

        total = 0
        pending = 0
        in_progress = 0
        completed = 0
        failed = 0

        for row in task_counts:
            status = row["status"]
            count = row["count"]
            total += count

            if status == "PENDING":
                pending = count
            elif status == "IN_PROGRESS":
                in_progress = count
            elif status == "COMPLETED":
                completed = count
            elif status == "FAILED":
                failed = count

        # Print summary
        print(f"  Pending:     {pending:>4}  ⏳ waiting")
        print(f"  In Progress: {in_progress:>4}  ⚙️  working")
        print(f"  Completed:   {completed:>4}  ✓ done")
        print(f"  Failed:      {failed:>4}  ✗ error")
        print(f"  {'─' * 98}")
        print(f"  Total:       {total:>4}")

    async def _print_metrics(self) -> None:
        """Print coordination metrics."""
        print("METRICS")
        print("-" * 100)

        # Agent metrics
        agents = await self.db.fetch("SELECT COUNT(*) as count FROM agents WHERE status != %s", "offline")
        active_agents = agents[0]["count"] if agents else 0

        # Task metrics
        in_progress = await self.db.fetch(
            "SELECT COUNT(*) as count FROM prospective_tasks WHERE status = %s",
            "IN_PROGRESS"
        )
        in_progress_count = in_progress[0]["count"] if in_progress else 0

        # Stale agents
        stale = await self.db.fetch(
            """
            SELECT COUNT(*) as count FROM agents
            WHERE status != %s
            AND (NOW() - last_heartbeat) > INTERVAL '1 minute'
            """,
            "offline"
        )
        stale_count = stale[0]["count"] if stale else 0

        print(f"  Active Agents:      {active_agents}")
        print(f"  Tasks In Progress:  {in_progress_count}")
        print(f"  Stale Agents:       {stale_count}")

    def _print_footer(self) -> None:
        """Print dashboard footer."""
        print("=" * 100)
        print(
            "Commands: (q)uit | Refreshing every "
            + str(self.refresh_interval_seconds)
            + " seconds"
        )


async def main():
    """Entry point for monitor dashboard."""
    # This would integrate with the actual database
    # For now, stub implementation

    from athena.core.database import Database

    db = Database()
    await db.initialize()

    monitor = MonitorDashboard(db)
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
