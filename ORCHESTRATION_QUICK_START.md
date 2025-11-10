# Multi-Agent Orchestration - Quick Start Guide

This guide shows how to use Athena's orchestration layer to coordinate multiple agents on tasks.

---

## 1. Basic Setup

```python
from athena.core.database import Database
from athena.episodic.store import EpisodicStore
from athena.graph.store import GraphStore
from athena.meta.store import MetaMemoryStore
from athena.orchestration import TaskQueue, AgentRegistry, CapabilityRouter

# Initialize components
db = Database("~/.athena/memory.db")
episodic = EpisodicStore(db)
graph = GraphStore(db)
meta = MetaMemoryStore(db)

# Create orchestration layer
task_queue = TaskQueue(episodic, graph)
agent_registry = AgentRegistry(graph, meta)
router = CapabilityRouter(agent_registry)
```

---

## 2. Register Agents

```python
# Register agents with capabilities
agent_registry.register_agent(
    agent_id="researcher_bot",
    capabilities=["python", "web", "research"],
    metadata={"max_concurrent_tasks": 5}
)

agent_registry.register_agent(
    agent_id="analysis_bot",
    capabilities=["python", "data_analysis", "visualization"],
    metadata={"max_concurrent_tasks": 3}
)
```

---

## 3. Create Tasks

```python
# Create a research task
task_id = task_queue.create_task(
    content="Research asyncio patterns in Python",
    task_type="research",
    priority="high",
    requirements=["python", "web"]  # Required capabilities
)

# Create analysis task (depends on research)
analysis_task = task_queue.create_task(
    content="Analyze the research findings",
    task_type="analysis",
    priority="medium",
    requirements=["data_analysis", "python"],
    dependencies=[task_id]  # Depends on research task
)
```

---

## 4. Route Tasks to Agents

```python
# Get task object
task = task_queue.get_task_status(task_id)

# Route to best capable agent
agent = router.route_task(task)

if agent:
    print(f"Routed to: {agent}")
    task_queue.assign_task(task_id, agent)
else:
    print("No capable agents available")
```

---

## 5. Execute Tasks

```python
# Agent polls for assigned tasks
assigned_tasks = task_queue.poll_tasks(
    agent_id="researcher_bot",
    status="assigned",
    limit=10
)

for task in assigned_tasks:
    # Agent starts execution
    task_queue.start_task(task.id)

    try:
        # Do work here...
        result = "Found 5 important patterns..."

        # Mark complete
        task_queue.complete_task(
            task.id,
            result=result,
            metrics={
                "duration_ms": 2500,
                "rows_processed": 100
            }
        )

        # Update agent metrics
        agent_registry.update_agent_performance(
            "researcher_bot",
            success=True,
            duration_ms=2500
        )

    except Exception as e:
        # Mark failed
        task_queue.fail_task(
            task.id,
            error=str(e),
            should_retry=True  # Retry if transient
        )

        agent_registry.update_agent_performance(
            "researcher_bot",
            success=False,
            duration_ms=500
        )
```

---

## 6. Monitor Queue and Agents

```python
# Get queue statistics
stats = task_queue.get_queue_statistics()
print(f"Pending: {stats.pending_count}")
print(f"Assigned: {stats.assigned_count}")
print(f"Running: {stats.running_count}")
print(f"Completed: {stats.completed_count}")
print(f"Failed: {stats.failed_count}")
print(f"Success rate: {stats.success_rate:.1%}")

# Get agent health
health = agent_registry.get_agent_health("researcher_bot")
print(f"Success rate: {health['success_rate']:.1%}")
print(f"Avg time: {health['avg_completion_ms']:.0f}ms")
print(f"Status: {health['status']}")

# Get overall statistics
overall = agent_registry.get_agent_statistics()
print(f"Total agents: {overall.total_agents}")
print(f"Avg success: {overall.avg_success_rate:.1%}")
print(f"Skills: {overall.skill_distribution}")
```

---

## 7. Query Tasks

```python
# Find all pending research tasks
pending_research = task_queue.query_tasks({
    "status": "pending",
    "task_type": "research"
})

# Find all high-priority tasks for an agent
agent_work = task_queue.query_tasks({
    "agent_id": "researcher_bot",
    "priority": "high"
})

# Find completed tasks in date range
from datetime import datetime, timedelta
week_ago = int((datetime.now() - timedelta(days=7)).timestamp())
recent_work = task_queue.query_tasks({
    "status": "completed",
    "created_after": week_ago
})
```

---

## 8. Agent Learning

Agents can learn new capabilities from execution:

```python
# Agent completes a new type of task
agent_registry.learn_new_capability(
    agent_id="researcher_bot",
    capability="machine_learning",
    confidence=0.8
)

# Now agent can handle ML tasks
ml_task = task_queue.create_task(
    content="Train ML model on dataset",
    task_type="ml",
    requirements=["machine_learning", "python"]
)

# Router will match with researcher_bot now
agent = router.route_task(task_queue.get_task_status(ml_task.id))
```

---

## 9. Priority and Dependencies

```python
# High-priority task
urgent = task_queue.create_task(
    content="Fix critical bug",
    task_type="debugging",
    priority="high",  # Will be selected first when polling
    requirements=["python"]
)

# Chain of dependent tasks
step1 = task_queue.create_task(
    content="Step 1: Research",
    task_type="research",
    priority="high"
)

step2 = task_queue.create_task(
    content="Step 2: Analyze",
    task_type="analysis",
    dependencies=[step1]  # Can't start until step1 completes
)

step3 = task_queue.create_task(
    content="Step 3: Implement",
    task_type="implementation",
    dependencies=[step2]
)

# Check dependencies
task2 = task_queue.get_task_status(step2.id)
print(f"Depends on: {task2.dependencies}")
print(f"Status: {task2.status}")
```

---

## 10. Using with MCP Tools

```python
# Via MCP server - these operations are exposed as tools
from athena.mcp.handlers_orchestration import OrchestrationHandlers

handlers = OrchestrationHandlers(task_queue, agent_registry, router)

# Register with MCP server
def setup_mcp_server(server):
    handlers.register_tools(server)
    # 18 orchestration tools now available:
    # - orchestration_create_task
    # - orchestration_poll_tasks
    # - orchestration_assign_task
    # - ... and 15 more
```

---

## Common Patterns

### Pattern 1: Simple Task Execution

```python
# Create task
task_id = task_queue.create_task(
    "Process dataset",
    "analysis",
    requirements=["python", "data_analysis"]
)

# Route and assign
task = task_queue.get_task_status(task_id)
agent = router.route_task(task)
task_queue.assign_task(task_id, agent)

# Execute
task_queue.start_task(task_id)
task_queue.complete_task(task_id, "Processed 1000 records")
```

### Pattern 2: Load Balancing

```python
# Router automatically balances based on utilization
# High-success but overloaded agents get lower priority

# Agent 1: 95% success, 10 running tasks (score = 0.95 * 0 = 0)
# Agent 2: 80% success, 2 running tasks (score = 0.80 * 0.75 = 0.6)

# Router will prefer Agent 2 despite lower success rate
# This prevents overloading the best agent
```

### Pattern 3: Retry on Failure

```python
task_id = task_queue.create_task(...)
task_queue.assign_task(task_id, agent)
task_queue.start_task(task_id)

try:
    # Execute
    pass
except TemporaryError:
    # Soft failure - retry
    task_queue.fail_task(task_id, error, should_retry=True)
    # Task returns to pending, can be reassigned
except PermanentError:
    # Hard failure - don't retry
    task_queue.fail_task(task_id, error, should_retry=False)
    # Task stays failed, needs manual intervention
```

### Pattern 4: Skill Specialization

```python
# Team of specialized agents
agent_registry.register_agent("nlp_expert", ["nlp", "analysis"])
agent_registry.register_agent("vision_expert", ["cv", "analysis"])
agent_registry.register_agent("data_expert", ["data_analysis", "sql"])

# Tasks find their specialists
nlp_task = task_queue.create_task(
    "Analyze sentiment",
    requirements=["nlp"]
)

vision_task = task_queue.create_task(
    "Extract text from images",
    requirements=["cv"]
)

# Router matches specialists
nlp_agent = router.route_task(task_queue.get_task_status(nlp_task.id))  # → nlp_expert
vision_agent = router.route_task(task_queue.get_task_status(vision_task.id))  # → vision_expert
```

---

## Troubleshooting

### "No capable agents available"

```python
# Check what capabilities are required
task = task_queue.get_task_status(task_id)
print(f"Required: {task.requirements}")

# Check what agents have available
all_agents = agent_registry.get_agents_by_capability([])  # Get all agents
for agent_id in all_agents:
    caps = agent_registry.get_agent_capability(agent_id)
    print(f"{agent_id}: {caps}")

# Register an agent with required skills
agent_registry.register_agent("new_bot", task.requirements)
```

### Agent not being selected despite capability

```python
# Check agent health
health = agent_registry.get_agent_health("agent_id")
if health["success_rate"] < 0.5:
    print("Agent has low success rate")
if health.get("status") == "degraded":
    print("Agent is degraded")

# Check utilization
# If agent has many running tasks, router prefers others
# Complete some tasks to free up capacity
```

### Task stuck in assigned state

```python
# Check if agent called start_task
task = task_queue.get_task_status(task_id)
print(f"Status: {task.status}")
print(f"Assigned to: {task.assigned_to}")

# Agent must call start_task to move to running
if task.status == "assigned":
    task_queue.start_task(task_id)
```

---

## Performance Tips

1. **Use polling limits**: Don't poll all tasks, use `limit=10` to batch
2. **Index on task_status**: Queries on status are indexed
3. **Batch updates**: Update multiple agent metrics together
4. **Clean up old tasks**: Delete completed tasks older than 30 days
5. **Monitor agent load**: Use `should_rebalance()` to detect skew

---

## Next Steps

- See `PHASE_1_ORCHESTRATION_COMPLETION_REPORT.md` for full architecture details
- See `tests/integration/test_orchestration_phase1.py` for more examples
- See `OPTIMAL_ORCHESTRATION_DESIGN.md` for future extensions (Phase 2+)

---

**Last Updated**: November 10, 2025
**Version**: 1.0 (Production Ready)
