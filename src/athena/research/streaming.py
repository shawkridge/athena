"""Real-time streaming result aggregation for Phase 3.4.

Enables incremental finding aggregation with streaming updates as agents complete.
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import asyncio

from .models import ResearchFinding

logger = logging.getLogger(__name__)


class StreamingFinding:
    """A single finding ready for streaming."""

    def __init__(self, finding: ResearchFinding, agent_name: str, discovered_at: datetime):
        self.finding = finding
        self.agent_name = agent_name
        self.discovered_at = discovered_at

    def to_dict(self) -> Dict[str, Any]:
        """Export for JSON/streaming."""
        return {
            "source": self.finding.source,
            "title": self.finding.title,
            "summary": self.finding.summary,
            "url": self.finding.url,
            "credibility": self.finding.credibility_score,
            "agent": self.agent_name,
            "discovered_at": self.discovered_at.isoformat(),
        }


class StreamingUpdate:
    """Update to stream to client (findings since last update + agent status)."""

    def __init__(
        self,
        task_id: int,
        new_findings: List[StreamingFinding],
        total_findings: int,
        agent_status: Dict[str, Any],
        is_complete: bool,
    ):
        self.task_id = task_id
        self.new_findings = new_findings
        self.total_findings = total_findings
        self.agent_status = agent_status
        self.is_complete = is_complete
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Export for JSON transmission."""
        return {
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "new_findings": [f.to_dict() for f in self.new_findings],
            "total_findings": self.total_findings,
            "agent_status": self.agent_status,
            "is_complete": self.is_complete,
        }

    def to_markdown(self) -> str:
        """Export for Claude consumption."""
        lines = ["## Research Progress Update\n"]
        lines.append(f"**Found so far**: {self.total_findings} findings")
        lines.append(f"**Status**: {'Complete' if self.is_complete else 'In progress'}\n")

        if self.new_findings:
            lines.append("### New Findings")
            for finding in self.new_findings:
                f = finding.finding
                lines.append(f"- **{f.title}** ({finding.agent_name}, {f.credibility_score:.0%})")
                if f.url:
                    lines.append(f"  {f.url}")

        if self.agent_status:
            lines.append("\n### Agent Status")
            for agent, status in self.agent_status.items():
                status_str = status.get("status", "unknown")
                count = status.get("findings", 0)
                lines.append(f"- {agent}: {status_str} ({count} findings)")

        return "\n".join(lines)


class StreamingResultCollector:
    """Incrementally collects and streams research findings as agents discover them."""

    def __init__(self, task_id: int, query: str, batch_size: int = 5):
        """Initialize streaming collector.

        Args:
            task_id: Research task ID
            query: Original research query
            batch_size: Findings per streaming update (triggers update when reached)
        """
        self.task_id = task_id
        self.query = query
        self.batch_size = batch_size

        self.findings: List[StreamingFinding] = []
        self.seen_urls: set = set()
        self.total_added = 0
        self.buffered_findings: List[StreamingFinding] = []
        self.agent_status: Dict[str, Dict[str, Any]] = {}
        self.is_complete = False
        self.update_count = 0
        self._lock = asyncio.Lock()

    async def add_finding_async(
        self, finding: ResearchFinding, agent_name: str
    ) -> Optional[StreamingUpdate]:
        """Add finding and return update if batch ready.

        Args:
            finding: Research finding to add
            agent_name: Agent that discovered it

        Returns:
            StreamingUpdate if batch size reached, None otherwise
        """
        async with self._lock:
            # Deduplicate by URL
            if finding.url and finding.url in self.seen_urls:
                return None
            if finding.url:
                self.seen_urls.add(finding.url)

            # Add to collections
            streaming_finding = StreamingFinding(finding, agent_name, datetime.utcnow())
            self.findings.append(streaming_finding)
            self.buffered_findings.append(streaming_finding)
            self.total_added += 1

            # Update agent status
            if agent_name not in self.agent_status:
                self.agent_status[agent_name] = {"status": "running", "findings": 0}
            self.agent_status[agent_name]["findings"] += 1

            # Return update if batch size reached
            if len(self.buffered_findings) >= self.batch_size:
                return await self._create_update()

        return None

    async def mark_agent_complete(self, agent_name: str) -> Optional[StreamingUpdate]:
        """Mark agent as complete and flush its findings.

        Args:
            agent_name: Agent that completed

        Returns:
            StreamingUpdate with remaining buffered findings
        """
        async with self._lock:
            if agent_name in self.agent_status:
                self.agent_status[agent_name]["status"] = "completed"

            # Flush any buffered findings
            if self.buffered_findings:
                return await self._create_update()

        return None

    async def finalize(self) -> StreamingUpdate:
        """Mark research complete and return final update.

        Returns:
            Final StreamingUpdate with all remaining findings
        """
        async with self._lock:
            self.is_complete = True
            return await self._create_update(force=True)

    async def _create_update(self, force: bool = False) -> StreamingUpdate:
        """Create update from buffered findings.

        Args:
            force: Ignore batch size, create update anyway

        Returns:
            StreamingUpdate
        """
        if not self.buffered_findings and not force:
            return None

        # Get buffered findings
        update_findings = self.buffered_findings.copy()
        self.buffered_findings.clear()

        # Create update
        update = StreamingUpdate(
            task_id=self.task_id,
            new_findings=update_findings,
            total_findings=len(self.findings),
            agent_status=self.agent_status.copy(),
            is_complete=self.is_complete,
        )

        self.update_count += 1
        return update

    def get_current_status(self) -> Dict[str, Any]:
        """Get current status without creating streaming update.

        Returns:
            Status dict with findings count, agent status, completion
        """
        return {
            "task_id": self.task_id,
            "findings_count": len(self.findings),
            "total_added": self.total_added,
            "agent_status": self.agent_status.copy(),
            "is_complete": self.is_complete,
            "update_count": self.update_count,
        }
