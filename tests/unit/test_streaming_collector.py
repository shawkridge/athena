"""Unit tests for StreamingResultCollector (Phase 3.4)."""

import pytest
import asyncio
from datetime import datetime

from athena.research.models import ResearchFinding
from athena.research.streaming import StreamingResultCollector, StreamingUpdate


@pytest.fixture
def collector():
    """Create a streaming collector for testing."""
    return StreamingResultCollector(task_id=42, query="test query", batch_size=3)


def create_finding(title: str, source: str, url: str, credibility: float = 0.8) -> ResearchFinding:
    """Helper to create test finding."""
    return ResearchFinding(
        research_task_id=42,
        source=source,
        title=title,
        summary=f"Summary for {title}",
        url=url,
        credibility_score=credibility,
    )


@pytest.mark.asyncio
async def test_add_finding_buffering(collector):
    """Test that findings are buffered until batch size."""
    f1 = create_finding("Paper 1", "arXiv", "http://arxiv.org/1")
    f2 = create_finding("Paper 2", "arXiv", "http://arxiv.org/2")

    # Add 2 findings (batch size is 3) - should not return update
    update1 = await collector.add_finding_async(f1, "arxiv-agent")
    assert update1 is None, "Should buffer first finding"

    update2 = await collector.add_finding_async(f2, "arxiv-agent")
    assert update2 is None, "Should buffer second finding"

    # Add 3rd finding - should trigger update
    f3 = create_finding("Paper 3", "arXiv", "http://arxiv.org/3")
    update3 = await collector.add_finding_async(f3, "arxiv-agent")
    assert update3 is not None, "Should return update at batch size"
    assert len(update3.new_findings) == 3, "Update should contain 3 findings"
    assert update3.total_findings == 3, "Total should be 3"


@pytest.mark.asyncio
async def test_deduplication(collector):
    """Test that duplicate URLs are not added."""
    f1 = create_finding("Paper 1", "arXiv", "http://arxiv.org/1")
    f2 = create_finding("Paper 1 Copy", "GitHub", "http://arxiv.org/1")  # Same URL

    # Add first
    await collector.add_finding_async(f1, "arxiv-agent")
    assert len(collector.findings) == 1

    # Add duplicate - should be ignored
    await collector.add_finding_async(f2, "github-agent")
    assert len(collector.findings) == 1, "Duplicate should not be added"


@pytest.mark.asyncio
async def test_agent_status_tracking(collector):
    """Test that agent status is tracked correctly."""
    f1 = create_finding("Paper 1", "arXiv", "http://arxiv.org/1")
    f2 = create_finding("Paper 2", "arXiv", "http://arxiv.org/2")
    f3 = create_finding("Repo 1", "GitHub", "http://github.com/1")

    # Add findings from two agents
    await collector.add_finding_async(f1, "arxiv-agent")
    await collector.add_finding_async(f2, "arxiv-agent")
    update = await collector.add_finding_async(f3, "github-agent")

    assert "arxiv-agent" in update.agent_status
    assert update.agent_status["arxiv-agent"]["findings"] == 2
    assert update.agent_status["arxiv-agent"]["status"] == "running"

    assert "github-agent" in update.agent_status
    assert update.agent_status["github-agent"]["findings"] == 1


@pytest.mark.asyncio
async def test_mark_agent_complete(collector):
    """Test marking agent as complete."""
    f1 = create_finding("Paper 1", "arXiv", "http://arxiv.org/1")

    await collector.add_finding_async(f1, "arxiv-agent")
    assert collector.agent_status["arxiv-agent"]["status"] == "running"

    update = await collector.mark_agent_complete("arxiv-agent")
    assert collector.agent_status["arxiv-agent"]["status"] == "completed"


@pytest.mark.asyncio
async def test_finalize(collector):
    """Test finalization of research."""
    findings = [
        create_finding("Paper 1", "arXiv", f"http://arxiv.org/{i}")
        for i in range(1, 4)
    ]

    for f in findings[:2]:
        await collector.add_finding_async(f, "arxiv-agent")

    # Add last finding and finalize
    await collector.add_finding_async(findings[2], "arxiv-agent")
    final_update = await collector.finalize()

    assert final_update.is_complete is True
    assert final_update.total_findings == 3


def test_streaming_update_to_dict(collector):
    """Test StreamingUpdate serialization."""
    f = create_finding("Paper 1", "arXiv", "http://arxiv.org/1")
    streaming_f = StreamingResultCollector(42, "test", 5).findings
    # Just verify the dict conversion works
    update = StreamingUpdate(
        task_id=42,
        new_findings=[],
        total_findings=0,
        agent_status={},
        is_complete=False,
    )

    d = update.to_dict()
    assert d["task_id"] == 42
    assert d["is_complete"] is False
    assert "timestamp" in d


def test_streaming_update_to_markdown():
    """Test StreamingUpdate markdown export."""
    update = StreamingUpdate(
        task_id=42,
        new_findings=[],
        total_findings=5,
        agent_status={"arxiv-agent": {"status": "completed", "findings": 3}},
        is_complete=False,
    )

    md = update.to_markdown()
    assert "5 findings" in md
    assert "arxiv-agent" in md
    assert "completed" in md


@pytest.mark.asyncio
async def test_concurrent_additions(collector):
    """Test concurrent finding additions (thread safety)."""
    async def add_findings(agent_name: str, count: int):
        for i in range(count):
            f = create_finding(f"Paper {i}", agent_name, f"http://test/{agent_name}/{i}")
            await collector.add_finding_async(f, agent_name)

    # Add findings from 3 agents concurrently
    await asyncio.gather(
        add_findings("arxiv-agent", 2),
        add_findings("github-agent", 2),
        add_findings("docs-agent", 2),
    )

    assert len(collector.findings) == 6
    assert collector.agent_status["arxiv-agent"]["findings"] == 2
    assert collector.agent_status["github-agent"]["findings"] == 2
    assert collector.agent_status["docs-agent"]["findings"] == 2
