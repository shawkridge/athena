"""Live agent monitoring for real-time research progress tracking."""

import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AgentStreamingStatus:
    """Real-time status of a research agent."""

    agent_name: str
    status: str  # pending|running|completed|failed
    findings_count: int = 0
    discoveries: list = field(default_factory=list)  # (timestamp, finding_count) tuples
    latencies_ms: list = field(default_factory=list)  # Individual request latencies
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None

    @property
    def avg_latency_ms(self) -> float:
        """Average latency for discoveries."""
        if not self.latencies_ms:
            return 0.0
        return sum(self.latencies_ms) / len(self.latencies_ms)

    @property
    def findings_per_second(self) -> float:
        """Discovery rate (findings/sec)."""
        if not self.started_at or self.findings_count == 0:
            return 0.0
        elapsed = (self.completed_at or time.time()) - self.started_at
        if elapsed < 1:
            return 0.0
        return self.findings_count / elapsed

    @property
    def elapsed_seconds(self) -> float:
        """Time elapsed since start."""
        if not self.started_at:
            return 0.0
        return (self.completed_at or time.time()) - self.started_at

    @property
    def estimated_completion_seconds(self) -> Optional[float]:
        """Estimate time to completion (naive linear model)."""
        if self.status in ("completed", "failed") or not self.started_at:
            return None

        # Simple linear extrapolation
        # Assume we'll get similar rate for remaining agents (3 agents typical)
        if self.findings_per_second > 0:
            estimated_total = max(self.findings_count, 10)  # At least 10 findings expected
            remaining = estimated_total - self.findings_count
            if remaining > 0:
                return remaining / self.findings_per_second
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Export for streaming."""
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "findings": self.findings_count,
            "rate": round(self.findings_per_second, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "elapsed_sec": round(self.elapsed_seconds, 1),
            "eta_sec": round(self.estimated_completion_seconds, 1)
            if self.estimated_completion_seconds
            else None,
        }


class LiveAgentMonitor:
    """Tracks real-time agent progress during research."""

    def __init__(self):
        """Initialize monitor."""
        self.agents: Dict[str, AgentStreamingStatus] = {}
        self._lock = __import__("asyncio").Lock()

    async def register_agent(self, agent_name: str) -> None:
        """Register a research agent."""
        async with self._lock:
            if agent_name not in self.agents:
                self.agents[agent_name] = AgentStreamingStatus(
                    agent_name=agent_name, status="pending", started_at=None
                )

    async def mark_agent_started(self, agent_name: str) -> None:
        """Mark agent as started."""
        async with self._lock:
            if agent_name in self.agents:
                self.agents[agent_name].status = "running"
                self.agents[agent_name].started_at = time.time()

    async def record_discovery(self, agent_name: str, latency_ms: float) -> None:
        """Record a finding discovery with latency.

        Args:
            agent_name: Agent that discovered
            latency_ms: How long the discovery took
        """
        async with self._lock:
            if agent_name not in self.agents:
                await self.register_agent(agent_name)

            agent = self.agents[agent_name]
            agent.findings_count += 1
            agent.discoveries.append((time.time(), agent.findings_count))
            agent.latencies_ms.append(latency_ms)

    async def mark_agent_completed(self, agent_name: str) -> None:
        """Mark agent as completed."""
        async with self._lock:
            if agent_name in self.agents:
                self.agents[agent_name].status = "completed"
                self.agents[agent_name].completed_at = time.time()

    async def mark_agent_failed(self, agent_name: str, error: str) -> None:
        """Mark agent as failed."""
        async with self._lock:
            if agent_name in self.agents:
                self.agents[agent_name].status = "failed"
                self.agents[agent_name].error_message = error
                self.agents[agent_name].completed_at = time.time()

    async def get_agent_status(self, agent_name: str) -> Optional[AgentStreamingStatus]:
        """Get status for a specific agent."""
        async with self._lock:
            return self.agents.get(agent_name)

    async def get_all_agents_status(self) -> Dict[str, Dict[str, Any]]:
        """Get all agents' status in exportable format."""
        async with self._lock:
            return {
                name: agent.to_dict() for name, agent in self.agents.items()
            }

    async def get_summary(self) -> Dict[str, Any]:
        """Get overall research progress summary."""
        async with self._lock:
            total_findings = sum(a.findings_count for a in self.agents.values())
            completed = sum(1 for a in self.agents.values() if a.status == "completed")
            failed = sum(1 for a in self.agents.values() if a.status == "failed")
            running = sum(1 for a in self.agents.values() if a.status == "running")

            max_eta = max(
                (a.estimated_completion_seconds for a in self.agents.values() if a.estimated_completion_seconds),
                default=None,
            )

            return {
                "total_findings": total_findings,
                "agents_completed": completed,
                "agents_running": running,
                "agents_failed": failed,
                "total_agents": len(self.agents),
                "estimated_completion_sec": round(max_eta, 1) if max_eta else None,
                "agents": {
                    name: agent.to_dict()
                    for name, agent in self.agents.items()
                },
            }
