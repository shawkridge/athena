# SDK Integration: Implementation Guide

**Date**: November 21, 2025
**Status**: Implementation Ready
**Audience**: Developers implementing SDK + Athena integration

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Phase-by-Phase Implementation](#2-phase-by-phase-implementation)
3. [Code Examples](#3-code-examples)
4. [Migration Strategy](#4-migration-strategy)
5. [Testing Strategy](#5-testing-strategy)
6. [Performance Optimization](#6-performance-optimization)
7. [Troubleshooting](#7-troubleshooting)
8. [Best Practices](#8-best-practices)

---

## 1. Quick Start

### Prerequisites

```bash
# Install Anthropic SDK
pip install claude-agent-sdk

# Verify Athena is running
psql -h localhost -U postgres -d athena -c "SELECT 1;"

# Verify environment
python3 --version  # Should be 3.10+
```

### Hello World: SDK Agent with Athena Memory

```python
# examples/hello_athena_agent.py

import asyncio
from claude_agent_sdk import ClaudeSDKClient, create_sdk_mcp_server
from athena.episodic.operations import remember, recall

# Step 1: Create sync wrappers for Athena operations
def athena_remember_sync(content: str, tags: str = "") -> str:
    """Store event in memory."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    event_id = asyncio.run(remember(content=content, tags=tag_list))
    return f"Stored: {event_id}"

def athena_recall_sync(query: str, limit: int = 5) -> str:
    """Query memories."""
    events = asyncio.run(recall(query=query, limit=limit))
    if not events:
        return "No memories found."

    result = []
    for i, event in enumerate(events, 1):
        result.append(f"{i}. {event.get('content', '')}")
    return "\n".join(result)

# Step 2: Create MCP server with Athena tools
athena_mcp = create_sdk_mcp_server([
    athena_remember_sync,
    athena_recall_sync,
])

# Step 3: Create SDK client with Athena tools
client = ClaudeSDKClient(
    allowed_tools=["Read", "Write"],
    mcp_servers={"athena": athena_mcp},
    working_directory="/home/user/athena",
)

# Step 4: Use agent with memory
async def main():
    print("=== First interaction ===")
    response1 = ""
    async for message in client.query(
        prompt="Remember that my favorite color is blue. Use athena_remember_sync."
    ):
        response1 += str(message)
    print(response1)

    print("\n=== Second interaction (new session) ===")
    response2 = ""
    async for message in client.query(
        prompt="What's my favorite color? Use athena_recall_sync to check."
    ):
        response2 += str(message)
    print(response2)

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it**:
```bash
python examples/hello_athena_agent.py
```

**Expected output**:
```
=== First interaction ===
I'll remember that your favorite color is blue.
[Agent uses athena_remember_sync tool]
Stored: event_abc123

=== Second interaction (new session) ===
Let me check my memory...
[Agent uses athena_recall_sync tool]
Based on my memory, your favorite color is blue!
```

**Key takeaway**: Agent remembers across sessions via Athena memory!

---

## 2. Phase-by-Phase Implementation

### Phase 1: Basic Memory Integration (Week 1)

**Goal**: Single SDK agent that can store/recall memories

**Tasks**:

1. **Create Athena MCP module**

```python
# src/athena/sdk_integration/mcp_tools.py

"""
Athena operations exposed as SDK tools.
"""

import asyncio
from typing import List, Dict, Any
from athena.episodic.operations import remember, recall
from athena.semantic.operations import store, search

def create_athena_mcp_tools():
    """Create list of Athena tools for SDK MCP server."""

    def athena_remember(content: str, tags: str = "", importance: float = 0.5) -> str:
        """
        Store an event in episodic memory.

        Args:
            content: What happened
            tags: Comma-separated tags
            importance: 0.0-1.0 (0.5 is default)

        Returns:
            Event ID
        """
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        event_id = asyncio.run(remember(
            content=content,
            tags=tag_list,
            importance=importance,
        ))
        return f"Stored event {event_id}"

    def athena_recall(query: str, tags: str = "", limit: int = 10) -> str:
        """
        Query episodic memory.

        Args:
            query: Search query
            tags: Filter by tags (comma-separated)
            limit: Max results

        Returns:
            Formatted list of events
        """
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
        events = asyncio.run(recall(query=query, tags=tag_list, limit=limit))

        if not events:
            return "No matching events found."

        result = []
        for i, event in enumerate(events, 1):
            timestamp = event.get('timestamp', 'unknown')
            content = event.get('content', '')
            importance = event.get('importance', 0.5)
            result.append(f"{i}. [{timestamp}] [{importance:.0%}] {content}")

        return "\n".join(result)

    def athena_store(content: str, topics: str = "", confidence: float = 0.8) -> str:
        """
        Store a learned fact in semantic memory.

        Args:
            content: The fact/learning
            topics: Comma-separated topics
            confidence: 0.0-1.0 confidence level

        Returns:
            Fact ID
        """
        topic_list = [t.strip() for t in topics.split(",") if t.strip()]
        fact_id = asyncio.run(store(
            content=content,
            topics=topic_list,
            confidence=confidence,
        ))
        return f"Stored fact {fact_id}"

    def athena_search(query: str, limit: int = 10) -> str:
        """
        Search semantic memory for learned facts.

        Args:
            query: Search query
            limit: Max results

        Returns:
            Formatted list of facts
        """
        facts = asyncio.run(search(query=query, limit=limit))

        if not facts:
            return "No matching facts found."

        result = []
        for i, fact in enumerate(facts, 1):
            content = fact.get('content', '')
            confidence = fact.get('confidence', 0.8)
            topics = fact.get('topics', [])
            result.append(f"{i}. [{confidence:.0%}] {content} (topics: {', '.join(topics)})")

        return "\n".join(result)

    return [
        athena_remember,
        athena_recall,
        athena_store,
        athena_search,
    ]
```

2. **Create helper to build SDK agent**

```python
# src/athena/sdk_integration/agent_builder.py

from claude_agent_sdk import ClaudeSDKClient, create_sdk_mcp_server
from .mcp_tools import create_athena_mcp_tools

def build_athena_agent(
    allowed_tools=None,
    working_directory="/home/user/athena",
):
    """
    Build SDK agent with Athena memory integration.

    Args:
        allowed_tools: List of SDK tools to allow
        working_directory: Working directory for agent

    Returns:
        ClaudeSDKClient with Athena tools
    """
    if allowed_tools is None:
        allowed_tools = ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]

    # Create Athena MCP server
    athena_tools = create_athena_mcp_tools()
    athena_mcp = create_sdk_mcp_server(athena_tools)

    # Create SDK client
    client = ClaudeSDKClient(
        allowed_tools=allowed_tools,
        mcp_servers={"athena": athena_mcp},
        working_directory=working_directory,
    )

    return client
```

3. **Test it**

```python
# tests/sdk_integration/test_basic_memory.py

import pytest
import asyncio
from athena.sdk_integration.agent_builder import build_athena_agent

@pytest.mark.asyncio
async def test_agent_can_store_and_recall():
    """Test that SDK agent can use Athena memory."""

    agent = build_athena_agent()

    # Store a memory
    response1 = ""
    async for msg in agent.query(
        "Use athena_remember to store: 'The capital of France is Paris'"
    ):
        response1 += str(msg)

    assert "Stored event" in response1

    # Recall the memory
    response2 = ""
    async for msg in agent.query(
        "Use athena_recall to find memories about France"
    ):
        response2 += str(msg)

    assert "Paris" in response2
```

**Success Criteria**:
- ✅ SDK agent can call athena_remember
- ✅ SDK agent can call athena_recall
- ✅ Memories persist across agent restarts
- ✅ Tests pass

---

### Phase 2: Task Coordination (Week 2-3)

**Goal**: Multiple SDK agents coordinate via Athena prospective memory

**Tasks**:

1. **Add task coordination tools**

```python
# src/athena/sdk_integration/mcp_tools.py (additions)

from athena.prospective.operations import (
    create_task,
    get_active_tasks,
    claim_task,
    update_task_status,
    get_task,
)

def create_task_coordination_tools(agent_id: str):
    """Create task coordination tools for an agent."""

    def athena_create_task(description: str, required_skills: str = "") -> str:
        """
        Create a task for another agent.

        Args:
            description: What needs to be done
            required_skills: Comma-separated skills needed

        Returns:
            Task ID
        """
        skills = [s.strip() for s in required_skills.split(",") if s.strip()]
        task_id = asyncio.run(create_task(
            title=description[:100],
            description=description,
            metadata={
                "required_skills": skills,
                "created_by": agent_id,
            },
        ))
        return f"Created task {task_id}"

    def athena_get_tasks(agent_type: str = "") -> str:
        """
        Get available tasks to work on.

        Args:
            agent_type: Filter by agent type

        Returns:
            List of available tasks
        """
        tasks = asyncio.run(get_active_tasks())

        # Filter by agent type if specified
        if agent_type:
            tasks = [
                t for t in tasks
                if agent_type in t.metadata.get("required_skills", [])
            ]

        if not tasks:
            return "No available tasks."

        result = []
        for i, task in enumerate(tasks, 1):
            result.append(f"{i}. [{task.task_id}] {task.title}")

        return "\n".join(result)

    def athena_claim_task(task_id: str) -> str:
        """
        Claim a task to work on it.

        Args:
            task_id: ID of task to claim

        Returns:
            Success or failure message
        """
        claimed = asyncio.run(claim_task(agent_id, task_id))
        if claimed:
            return f"Successfully claimed task {task_id}"
        return f"Could not claim task {task_id} (already assigned)"

    def athena_update_task(task_id: str, status: str, result: str = "") -> str:
        """
        Update task status.

        Args:
            task_id: Task to update
            status: New status (pending|in_progress|completed|failed)
            result: Result description (optional)

        Returns:
            Success message
        """
        asyncio.run(update_task_status(
            task_id=task_id,
            status=status,
            metadata={"result": result} if result else None,
        ))
        return f"Updated task {task_id} to {status}"

    return [
        athena_create_task,
        athena_get_tasks,
        athena_claim_task,
        athena_update_task,
    ]
```

2. **Create agent worker**

```python
# src/athena/sdk_integration/agent_worker.py

"""
SDK agent that polls for tasks and executes them.
"""

import asyncio
from claude_agent_sdk import ClaudeSDKClient, create_sdk_mcp_server
from .mcp_tools import create_athena_mcp_tools, create_task_coordination_tools

class SDKAgentWorker:
    """SDK agent that works on tasks from prospective memory."""

    def __init__(self, agent_id: str, agent_type: str, capabilities: list):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.capabilities = capabilities

        # Build Athena MCP with memory + coordination tools
        memory_tools = create_athena_mcp_tools()
        task_tools = create_task_coordination_tools(agent_id)
        all_tools = memory_tools + task_tools

        athena_mcp = create_sdk_mcp_server(all_tools)

        # Create SDK client
        self.client = ClaudeSDKClient(
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep"],
            mcp_servers={"athena": athena_mcp},
            working_directory="/home/user/athena",
        )

        self._should_run = True
        self.current_task = None

    async def work_loop(self):
        """Main work loop: poll for tasks and execute."""

        print(f"[{self.agent_id}] Starting work loop...")

        while self._should_run:
            try:
                # Get available tasks for this agent type
                response = ""
                async for msg in self.client.query(
                    f"Use athena_get_tasks('{self.agent_type}') to find available tasks"
                ):
                    response += str(msg)

                # If tasks available, claim one
                if "No available tasks" not in response:
                    # Ask agent to claim a task
                    claim_response = ""
                    async for msg in self.client.query(
                        "Use athena_claim_task to claim the first available task from the list"
                    ):
                        claim_response += str(msg)

                    if "Successfully claimed" in claim_response:
                        # Extract task ID (simplified - would parse properly)
                        # Execute the task
                        exec_response = ""
                        async for msg in self.client.query(
                            "Execute the task you just claimed and use athena_update_task when complete"
                        ):
                            exec_response += str(msg)

                        print(f"[{self.agent_id}] Completed task")

                # Sleep before next poll
                await asyncio.sleep(2)

            except Exception as e:
                print(f"[{self.agent_id}] Error: {e}")
                await asyncio.sleep(5)

    def stop(self):
        """Stop work loop."""
        self._should_run = False
```

3. **Test multi-agent coordination**

```python
# tests/sdk_integration/test_coordination.py

import pytest
import asyncio
from athena.sdk_integration.agent_worker import SDKAgentWorker
from athena.prospective.operations import create_task

@pytest.mark.asyncio
async def test_two_agents_coordinate():
    """Test that two agents can coordinate via tasks."""

    # Spawn two agents
    agent_a = SDKAgentWorker(
        agent_id="agent-a",
        agent_type="research",
        capabilities=["research", "web_search"],
    )

    agent_b = SDKAgentWorker(
        agent_id="agent-b",
        agent_type="analysis",
        capabilities=["analysis", "code_review"],
    )

    # Start agents in background
    task_a = asyncio.create_task(agent_a.work_loop())
    task_b = asyncio.create_task(agent_b.work_loop())

    # Create a task for research agent
    task_id = await create_task(
        title="Research async patterns",
        description="Find best practices for async Python",
        metadata={"required_skills": ["research"]},
    )

    # Wait for agent A to claim and complete
    await asyncio.sleep(10)

    # Verify task was completed
    from athena.prospective.operations import get_task
    task = await get_task(task_id)
    assert task.status == "completed"

    # Stop agents
    agent_a.stop()
    agent_b.stop()
    task_a.cancel()
    task_b.cancel()
```

**Success Criteria**:
- ✅ Multiple SDK agents run concurrently
- ✅ Agents poll for work
- ✅ Agents claim tasks atomically (no double-claiming)
- ✅ Agents execute and report completion
- ✅ Tests pass

---

### Phase 3: Hooks & Auto-Injection (Week 4)

**Goal**: Automatic working memory injection via hooks

**Tasks**:

1. **Create hook system**

```python
# src/athena/sdk_integration/hooks.py

"""
SDK hooks for automatic Athena integration.
"""

from typing import Dict, Any
from athena.episodic.operations import remember, recall
import asyncio

class AthenaHooks:
    """Collection of hooks for SDK + Athena integration."""

    def __init__(self, agent_id: str, working_memory_limit: int = 7):
        self.agent_id = agent_id
        self.working_memory_limit = working_memory_limit

    async def inject_working_memory(self, prompt: str) -> Dict[str, Any]:
        """
        Inject relevant working memories when user submits prompt.

        This hook is called by SDK on UserPromptSubmit event.
        """
        # Query memories relevant to this prompt
        memories = await recall(
            query=prompt,
            limit=self.working_memory_limit,
        )

        if not memories:
            return {}

        # Format memories for injection
        context = "\n## Working Memory\n\n"
        context += "Recent relevant memories:\n\n"

        for i, mem in enumerate(memories, 1):
            timestamp = mem.get('timestamp', 'unknown')
            importance = mem.get('importance', 0.5)
            content = mem.get('content', '')
            context += f"{i}. [{timestamp}] [{importance:.0%}] {content}\n"

        return {"context_injection": context}

    async def store_tool_execution(self, tool_name: str, result: Any) -> None:
        """
        Store successful tool executions in memory.

        This hook is called by SDK on PostToolUse event.
        """
        await remember(
            content=f"Agent {self.agent_id} executed {tool_name}",
            tags=["tool_execution", tool_name.lower(), self.agent_id],
            importance=0.4,
            source=self.agent_id,
        )

    async def validate_tool_use(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Validate tool usage before execution.

        This hook is called by SDK on PreToolUse event.

        Returns:
            "allow" | "deny" | "ask"
        """
        # Log the request
        await remember(
            content=f"Agent {self.agent_id} requesting {tool_name}",
            tags=["tool_request", tool_name.lower(), self.agent_id],
            importance=0.3,
            source=self.agent_id,
        )

        # Security checks
        if tool_name == "Bash":
            command = params.get("command", "")
            dangerous_patterns = ["rm -rf", "dd if=", ":(){ :|:& };:"]

            if any(pattern in command for pattern in dangerous_patterns):
                await remember(
                    content=f"SECURITY: Blocked dangerous command: {command}",
                    tags=["security", "blocked", self.agent_id],
                    importance=0.95,
                    source=self.agent_id,
                )
                return "deny"

        return "allow"


def install_hooks(client, agent_id: str, working_memory_limit: int = 7):
    """
    Install Athena hooks on SDK client.

    Args:
        client: ClaudeSDKClient instance
        agent_id: Unique agent identifier
        working_memory_limit: Number of memories to inject

    Returns:
        Client with hooks installed
    """
    hooks = AthenaHooks(agent_id, working_memory_limit)

    # Install hooks
    client.add_hook("UserPromptSubmit", hooks.inject_working_memory)
    client.add_hook("PostToolUse", hooks.store_tool_execution)
    client.add_hook("PreToolUse", hooks.validate_tool_use)

    return client
```

2. **Update agent builder to use hooks**

```python
# src/athena/sdk_integration/agent_builder.py (updated)

from .hooks import install_hooks
import uuid

def build_athena_agent(
    agent_type: str = "general",
    agent_id: str = None,
    allowed_tools=None,
    working_directory="/home/user/athena",
    enable_hooks: bool = True,
    working_memory_limit: int = 7,
):
    """Build SDK agent with Athena memory integration."""

    if agent_id is None:
        agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"

    if allowed_tools is None:
        allowed_tools = ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]

    # Create Athena MCP server
    from .mcp_tools import create_athena_mcp_tools, create_task_coordination_tools

    memory_tools = create_athena_mcp_tools()
    task_tools = create_task_coordination_tools(agent_id)
    all_tools = memory_tools + task_tools

    athena_mcp = create_sdk_mcp_server(all_tools)

    # Create SDK client
    client = ClaudeSDKClient(
        allowed_tools=allowed_tools,
        mcp_servers={"athena": athena_mcp},
        working_directory=working_directory,
    )

    # Install hooks if enabled
    if enable_hooks:
        client = install_hooks(
            client,
            agent_id=agent_id,
            working_memory_limit=working_memory_limit,
        )

    return client, agent_id
```

3. **Test hooks**

```python
# tests/sdk_integration/test_hooks.py

import pytest
import asyncio
from athena.sdk_integration.agent_builder import build_athena_agent

@pytest.mark.asyncio
async def test_working_memory_injection():
    """Test that working memory is auto-injected."""

    agent, agent_id = build_athena_agent(enable_hooks=True)

    # First interaction: Store some information
    response1 = ""
    async for msg in agent.query("My favorite color is purple"):
        response1 += str(msg)

    # The PostToolUse hook should have stored this

    # Second interaction: Ask about it
    # The UserPromptSubmit hook should inject the memory
    response2 = ""
    async for msg in agent.query("What's my favorite color?"):
        response2 += str(msg)

    # Agent should find it in working memory (not via explicit recall)
    assert "purple" in response2.lower()

@pytest.mark.asyncio
async def test_dangerous_command_blocked():
    """Test that dangerous commands are blocked by PreToolUse hook."""

    agent, agent_id = build_athena_agent(enable_hooks=True)

    response = ""
    async for msg in agent.query("Run: rm -rf /"):
        response += str(msg)

    # Hook should have denied this
    assert "denied" in response.lower() or "cannot" in response.lower()
```

**Success Criteria**:
- ✅ Hooks auto-inject working memory
- ✅ Hooks auto-store tool executions
- ✅ Hooks block dangerous commands
- ✅ No manual remember/recall needed
- ✅ Tests pass

---

### Phase 4: Production Deployment (Week 5)

**Goal**: Replace current Athena orchestration with SDK-based version

**Tasks**:

1. **Create production orchestrator**

```python
# src/athena/sdk_integration/orchestrator.py

"""
Production orchestrator using SDK agents with Athena memory.
"""

import asyncio
from typing import List, Dict, Any, Optional
from athena.sdk_integration.agent_worker import SDKAgentWorker
from athena.prospective.operations import create_task, get_task
from athena.planning.operations import decompose_task

class ProductionOrchestrator:
    """
    Production-ready multi-agent orchestrator.

    Uses SDK agents with Athena memory for coordination.
    """

    def __init__(self, max_agents: int = 4):
        self.max_agents = max_agents
        self.agents: Dict[str, SDKAgentWorker] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}

    async def orchestrate(self, task_description: str) -> Dict[str, Any]:
        """
        Orchestrate multi-agent task execution.

        Args:
            task_description: High-level task description

        Returns:
            Results from all subtasks
        """
        print(f"[Orchestrator] Starting: {task_description}")

        # Step 1: Decompose task
        subtasks = await decompose_task(task_description)
        print(f"[Orchestrator] Decomposed into {len(subtasks)} subtasks")

        # Step 2: Determine required agent types
        agent_types = self._determine_agent_types(subtasks)

        # Step 3: Spawn agents
        for agent_type in agent_types[:self.max_agents]:
            await self._spawn_agent(agent_type)

        # Step 4: Create tasks in prospective memory
        task_ids = []
        for subtask in subtasks:
            task_id = await create_task(
                title=subtask["title"],
                description=subtask["description"],
                metadata={"required_skills": subtask.get("required_skills", [])},
            )
            task_ids.append(task_id)
            print(f"[Orchestrator] Created task: {subtask['title']}")

        # Step 5: Monitor until completion
        print(f"[Orchestrator] Monitoring {len(task_ids)} tasks...")
        await self._wait_for_completion(task_ids)

        # Step 6: Gather results
        results = await self._gather_results(task_ids)

        # Step 7: Cleanup
        await self._cleanup()

        print("[Orchestrator] Complete!")
        return results

    async def _spawn_agent(self, agent_type: str):
        """Spawn an agent and start its work loop."""
        agent_id = f"{agent_type}_{len(self.agents)}"

        agent = SDKAgentWorker(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=self._get_capabilities(agent_type),
        )

        self.agents[agent_id] = agent

        # Start work loop in background
        task = asyncio.create_task(agent.work_loop())
        self.agent_tasks[agent_id] = task

        print(f"[Orchestrator] Spawned agent: {agent_id}")

    def _determine_agent_types(self, subtasks: List[Dict]) -> List[str]:
        """Determine which agent types are needed."""
        types = set()
        for task in subtasks:
            title_lower = task["title"].lower()
            if any(word in title_lower for word in ["research", "find", "search"]):
                types.add("research")
            elif any(word in title_lower for word in ["analyze", "review"]):
                types.add("analysis")
            elif any(word in title_lower for word in ["write", "document"]):
                types.add("documentation")
            else:
                types.add("general")
        return list(types)

    def _get_capabilities(self, agent_type: str) -> List[str]:
        """Get capabilities for agent type."""
        caps_map = {
            "research": ["research", "web_search", "code_search"],
            "analysis": ["analysis", "code_review", "testing"],
            "documentation": ["documentation", "writing"],
            "general": ["general_purpose"],
        }
        return caps_map.get(agent_type, ["general_purpose"])

    async def _wait_for_completion(self, task_ids: List[str]):
        """Wait for all tasks to complete."""
        while True:
            all_done = True
            for task_id in task_ids:
                task = await get_task(task_id)
                if task.status not in ["completed", "failed"]:
                    all_done = False
                    break

            if all_done:
                break

            await asyncio.sleep(5)

    async def _gather_results(self, task_ids: List[str]) -> Dict[str, Any]:
        """Gather results from completed tasks."""
        results = {"tasks": []}

        for task_id in task_ids:
            task = await get_task(task_id)
            results["tasks"].append({
                "task_id": task_id,
                "title": task.title,
                "status": task.status,
                "result": task.metadata.get("result", ""),
            })

        return results

    async def _cleanup(self):
        """Stop all agents."""
        for agent in self.agents.values():
            agent.stop()

        for task in self.agent_tasks.values():
            task.cancel()

        self.agents.clear()
        self.agent_tasks.clear()
```

2. **Create CLI entry point**

```python
# src/athena/sdk_integration/cli.py

"""
CLI for SDK + Athena orchestration.
"""

import asyncio
import click
from .orchestrator import ProductionOrchestrator

@click.group()
def cli():
    """Athena SDK Integration CLI"""
    pass

@cli.command()
@click.argument("task_description")
@click.option("--max-agents", default=4, help="Maximum concurrent agents")
def orchestrate(task_description, max_agents):
    """Orchestrate multi-agent task execution."""

    async def run():
        orchestrator = ProductionOrchestrator(max_agents=max_agents)
        results = await orchestrator.orchestrate(task_description)

        click.echo("\n=== Results ===")
        for task_result in results["tasks"]:
            click.echo(f"\n{task_result['title']}: {task_result['status']}")
            if task_result['result']:
                click.echo(f"  {task_result['result']}")

    asyncio.run(run())

@cli.command()
def agent():
    """Start a single agent worker."""
    # Would start an agent in work loop mode
    pass

if __name__ == "__main__":
    cli()
```

3. **Deploy**

```bash
# Install as editable
pip install -e .

# Run orchestration
athena-sdk orchestrate "Analyze the authentication module and write a security report"
```

**Success Criteria**:
- ✅ Production orchestrator works end-to-end
- ✅ Can orchestrate complex tasks
- ✅ CLI is user-friendly
- ✅ Performance meets targets (see Phase 1 benchmarks)
- ✅ Ready for production use

---

### Phase 5: Polish & Documentation (Week 6)

**Tasks**:
1. Performance optimization (based on profiling)
2. Error handling improvements
3. Monitoring dashboard
4. User documentation
5. API reference
6. Example projects

---

## 3. Code Examples

### Example 1: Single Agent Research Task

```python
from athena.sdk_integration import build_athena_agent

async def research_task():
    """Single agent researches a topic and stores findings."""

    agent, agent_id = build_athena_agent(
        agent_type="research",
        enable_hooks=True,
    )

    # Agent automatically:
    # - Injects working memory (via UserPromptSubmit hook)
    # - Stores tool executions (via PostToolUse hook)
    # - Validates commands (via PreToolUse hook)

    result = ""
    async for message in agent.query(
        """
        Research async/await patterns in Python.
        Use web search if needed.
        Store key findings using athena_store.
        """
    ):
        result += str(message)

    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(research_task())
```

### Example 2: Multi-Agent Pipeline

```python
from athena.sdk_integration import ProductionOrchestrator

async def multi_agent_pipeline():
    """
    Multi-agent pipeline:
    1. Research agent finds information
    2. Analysis agent processes it
    3. Documentation agent writes report
    """

    orchestrator = ProductionOrchestrator(max_agents=3)

    results = await orchestrator.orchestrate(
        """
        Analyze the codebase security:
        1. Research common vulnerabilities in Python web apps
        2. Analyze our codebase for those vulnerabilities
        3. Write a security report with recommendations
        """
    )

    print("=== Pipeline Results ===")
    for task_result in results["tasks"]:
        print(f"\n{task_result['title']}")
        print(f"Status: {task_result['status']}")
        print(f"Result: {task_result['result'][:200]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(multi_agent_pipeline())
```

### Example 3: Agent Team with Specialized Skills

```python
from athena.sdk_integration import SDKAgentWorker
import asyncio

async def specialized_team():
    """
    Create a team of specialized agents:
    - SecurityAgent: Analyzes security
    - PerformanceAgent: Analyzes performance
    - DocumentationAgent: Writes docs
    """

    agents = [
        SDKAgentWorker(
            agent_id="security-1",
            agent_type="security",
            capabilities=["security_analysis", "penetration_testing"],
        ),
        SDKAgentWorker(
            agent_id="performance-1",
            agent_type="performance",
            capabilities=["profiling", "optimization"],
        ),
        SDKAgentWorker(
            agent_id="docs-1",
            agent_type="documentation",
            capabilities=["writing", "markdown"],
        ),
    ]

    # Start all agents
    tasks = [asyncio.create_task(agent.work_loop()) for agent in agents]

    # Create tasks for each agent
    from athena.prospective.operations import create_task

    await create_task(
        title="Security audit",
        description="Perform security audit of auth module",
        metadata={"required_skills": ["security_analysis"]},
    )

    await create_task(
        title="Performance analysis",
        description="Profile API endpoints and identify bottlenecks",
        metadata={"required_skills": ["profiling"]},
    )

    await create_task(
        title="Documentation",
        description="Write API documentation",
        metadata={"required_skills": ["writing"]},
    )

    # Let agents work
    await asyncio.sleep(60)

    # Stop agents
    for agent in agents:
        agent.stop()
    for task in tasks:
        task.cancel()

if __name__ == "__main__":
    asyncio.run(specialized_team())
```

---

## 4. Migration Strategy

### Migrating from Current Orchestration

**Current**: `src/athena/coordination/orchestrator.py` (tmux-based)
**Target**: `src/athena/sdk_integration/orchestrator.py` (SDK-based)

**Migration Steps**:

1. **Run both systems in parallel** (Week 1-2)
   - Keep current orchestrator active
   - Test SDK orchestrator on non-critical tasks
   - Compare performance

2. **Migrate agent types one-by-one** (Week 3-4)
   - Week 3: Migrate ResearchAgent → SDK version
   - Week 4: Migrate AnalysisAgent → SDK version
   - Keep others on current system

3. **Feature parity check** (Week 5)
   - Verify all features work
   - Performance benchmarks
   - User acceptance testing

4. **Full cutover** (Week 6)
   - Switch default to SDK orchestrator
   - Archive old orchestrator (keep for rollback)
   - Monitor for 1 week

5. **Remove old code** (Week 7)
   - Delete old orchestrator if SDK version stable
   - Update all documentation

**Rollback Plan**:
```python
# Environment variable controls which orchestrator to use
import os

if os.getenv("USE_SDK_ORCHESTRATOR", "false") == "true":
    from athena.sdk_integration import ProductionOrchestrator as Orchestrator
else:
    from athena.coordination import Orchestrator  # Old version

# User can rollback instantly by setting env var
```

---

## 5. Testing Strategy

### Unit Tests

```bash
# Test individual components
pytest tests/sdk_integration/test_mcp_tools.py -v
pytest tests/sdk_integration/test_hooks.py -v
pytest tests/sdk_integration/test_agent_builder.py -v
```

### Integration Tests

```bash
# Test SDK + Athena interaction
pytest tests/sdk_integration/test_basic_memory.py -v
pytest tests/sdk_integration/test_coordination.py -v
pytest tests/sdk_integration/test_orchestration.py -v
```

### Performance Tests

```bash
# Benchmark against targets
pytest tests/sdk_integration/test_performance.py -v --benchmark

# Expected:
# - Agent startup: <2s
# - Memory query: <100ms
# - Task claim: <20ms
# - Context usage: <30K tokens
```

### Load Tests

```bash
# Test with many agents
pytest tests/sdk_integration/test_load.py -v --agents=20

# Expected:
# - 20 concurrent agents
# - No deadlocks
# - All tasks complete
# - <10% failure rate
```

---

## 6. Performance Optimization

### Optimization 1: Connection Pooling

```python
# Use connection pool for all DB operations
from athena.core.database import Database

db = Database(
    pool_min_size=5,
    pool_max_size=20,
)
```

**Before**: Each agent creates new connection (slow)
**After**: Agents share connection pool (10x faster)

### Optimization 2: Batch Memory Queries

```python
# Instead of N queries
for i in range(100):
    await remember(f"Event {i}")

# Do batch insert
await remember_batch([f"Event {i}" for i in range(100)])
```

**Before**: 100 round-trips to DB
**After**: 1 round-trip (100x faster)

### Optimization 3: Memory Query Caching

```python
# Cache frequently accessed memories
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_recall(query: str, limit: int):
    return asyncio.run(recall(query, limit=limit))
```

**Before**: Every query hits database
**After**: Cache hit = instant (1000x faster for repeated queries)

---

## 7. Troubleshooting

**Problem**: Agent not finding tools

**Solution**:
```python
# Verify MCP server registered
print(client.mcp_servers.keys())  # Should include 'athena'

# List available tools
for tool in athena_mcp.list_tools():
    print(tool.name)
```

**Problem**: Hooks not firing

**Solution**:
```python
# Verify hooks installed
print(client.hooks.keys())  # Should include event names

# Add debug logging
async def debug_hook(event_name: str, *args):
    print(f"Hook fired: {event_name}")
    return {}

client.add_hook("*", debug_hook)  # Catch all events
```

**Problem**: High latency

**Solution**:
```python
# Profile with cProfile
import cProfile
cProfile.run('asyncio.run(agent.execute("test"))')

# Common causes:
# 1. Too many DB round-trips → Use batch operations
# 2. No connection pooling → Add pool
# 3. Slow queries → Add indexes
```

---

## 8. Best Practices

### ✅ Do

1. **Use hooks for automatic operations**
   ```python
   # Don't manually remember/recall
   # Let hooks do it automatically
   agent, id = build_athena_agent(enable_hooks=True)
   ```

2. **Use connection pooling**
   ```python
   db = Database(pool_min_size=5, pool_max_size=20)
   ```

3. **Batch operations when possible**
   ```python
   await remember_batch(events)  # Not: for e in events: await remember(e)
   ```

4. **Filter memories with tags**
   ```python
   memories = await recall(query, tags=["relevant", "recent"])
   ```

5. **Set appropriate importance**
   ```python
   await remember("Critical error", importance=0.9)  # Not 0.5
   ```

### ❌ Don't

1. **Don't load all memories at once**
   ```python
   # ❌ Bad
   all_memories = await recall("", limit=10000)

   # ✅ Good
   relevant = await recall(query, limit=7)
   ```

2. **Don't create agents in loops**
   ```python
   # ❌ Bad
   for task in tasks:
       agent = build_athena_agent()

   # ✅ Good
   agent = build_athena_agent()
   for task in tasks:
       await agent.execute(task)
   ```

3. **Don't block async code**
   ```python
   # ❌ Bad
   result = asyncio.run(recall(query))  # In async function

   # ✅ Good
   result = await recall(query)
   ```

4. **Don't ignore errors**
   ```python
   # ❌ Bad
   try:
       await agent.execute(task)
   except:
       pass

   # ✅ Good
   try:
       await agent.execute(task)
   except Exception as e:
       logger.error(f"Task failed: {e}")
       await remember(f"Error: {e}", tags=["error"], importance=0.8)
   ```

---

## Next Steps

1. **Start with Phase 1** (Week 1)
   - Create MCP tools
   - Build basic agent
   - Test memory persistence

2. **Move to Phase 2** (Week 2-3)
   - Add coordination tools
   - Test multi-agent workflows

3. **Continue to Phase 3-5** (Week 4-6)
   - Hooks, production deployment, polish

**Questions?** See `docs/SDK_INTEGRATION_ARCHITECTURE.md` for detailed architecture.

---

**Document Version**: 1.0
**Status**: Implementation Ready
**Start Date**: Week of November 25, 2025
