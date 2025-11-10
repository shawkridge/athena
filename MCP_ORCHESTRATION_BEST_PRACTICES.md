# MCP Orchestration Best Practices

**Status**: Production Ready
**Based on**: Anthropic MCP Engineering Standards
**Date**: November 10, 2025

---

## Core Principles

Following these principles ensures efficient, scalable agent coordination:

### 1. Batch Your Operations

❌ **Inefficient**: Poll one task at a time
```python
for i in range(10):
    task = call_tool("orchestration_poll_tasks", limit=1)
    # 10 tool calls, lots of round-trips
```

✅ **Efficient**: Batch in single call
```python
tasks = call_tool("orchestration_poll_tasks", limit=10)
# 1 tool call, 10x fewer round-trips
```

**Token Savings**: 80% reduction in context overhead

---

### 2. Use Server-Side Filtering

❌ **Inefficient**: Get all tasks, filter in agent
```python
all_tasks = call_tool("orchestration_query_tasks")  # 50KB response
high_priority = [t for t in all_tasks if t["priority"] == "high"]
# Agent wastes tokens parsing unneeded data
```

✅ **Efficient**: Filter server-side
```python
high_priority = call_tool(
    "orchestration_query_tasks",
    filters={"priority": "high"}
)
# Server returns only matching tasks
```

**Token Savings**: 95% reduction in response size

---

### 3. Compose Tool Sequences

❌ **Inefficient**: Separate calls for each step
```python
# 5 tool calls to complete workflow
task_id = call_tool("orchestration_create_task", ...)
task = call_tool("orchestration_get_task_status", task_id)
agent = call_tool("orchestration_route_task", task_id)
call_tool("orchestration_assign_task", task_id, agent)
call_tool("orchestration_start_task", task_id)
```

✅ **Efficient**: Chain operations using returned values
```python
# 5 tool calls, but tightly coupled
# Agent maintains task_id and agent_id across calls
task_id = create_task(...)      # Returns task_id
agent = route_task(task_id)     # Uses returned task_id
assign_task(task_id, agent)     # Uses both from above
start_task(task_id)             # Uses task_id
```

**Token Savings**: Clearer context flow (fewer intermediate storage)

---

### 4. Leverage Aggregated Metrics

❌ **Inefficient**: Query individual agents
```python
agents = ["bot1", "bot2", "bot3", "bot4", "bot5"]
for agent_id in agents:
    health = call_tool("orchestration_get_agent_health", agent_id)
    # 5 tool calls to get overall health
```

✅ **Efficient**: Get aggregate statistics
```python
stats = call_tool("orchestration_get_agent_statistics")
# Single call returns: total_agents, avg_success_rate, skill_distribution
```

**Token Savings**: 80% fewer calls + pre-computed aggregations

---

### 5. Use Exclusion Lists Instead of Manual Filtering

❌ **Inefficient**: Route, check result, manually select next agent
```python
agent1 = route_task(task_id)
if agent1_unavailable:
    agent2 = route_task(task_id)  # No way to exclude agent1
    if agent2_unavailable:
        agent3 = route_task(task_id)
```

✅ **Efficient**: Exclude blacklisted agents in single call
```python
agent = call_tool(
    "orchestration_route_task",
    task_id=task_id,
    exclude_agents=["bot1", "bot2"]  # Skip known bad agents
)
# Router automatically tries next best agent
```

**Token Savings**: Single call does what previously needed 3+ calls

---

## Workflow Patterns

### Pattern 1: Simple Task Execution

```python
# 1. Create task
response = call_tool("orchestration_create_task",
    content="Analyze dataset",
    task_type="analysis",
    priority="high",
    requirements=["python", "data_analysis"]
)
task_id = response["task_id"]

# 2. Route to capable agent
route_response = call_tool("orchestration_route_task", task_id)
agent_id = route_response["selected_agent"]

# 3. Assign and start
call_tool("orchestration_assign_task", task_id, agent_id)
call_tool("orchestration_start_task", task_id)

# 4. Agent executes... when done:
call_tool("orchestration_complete_task",
    task_id=task_id,
    result="Analyzed 1000 records",
    metrics={"duration_ms": 2500}
)
```

**Context Overhead**: ~150 tokens
**Round Trips**: 5

---

### Pattern 2: Batch Processing

```python
# 1. Create multiple tasks
tasks = []
for i in range(20):
    response = call_tool("orchestration_create_task",
        content=f"Process batch {i}",
        task_type="processing"
    )
    tasks.append(response["task_id"])

# 2. Poll for assignments in batch
pending = call_tool("orchestration_poll_tasks",
    status="pending",
    limit=10  # Get next 10 pending
)

# 3. Route and assign in loop
for task_info in pending["tasks"]:
    agent = call_tool("orchestration_route_task", task_info["id"])
    if agent:
        call_tool("orchestration_assign_task", task_info["id"], agent)
```

**Context Overhead**: ~200 tokens
**Round Trips**: 3 + (number of tasks / limit)

---

### Pattern 3: Team Specialization

```python
# 1. Register specialized agents
call_tool("orchestration_register_agent",
    agent_id="python_expert",
    capabilities=["python", "analysis"]
)
call_tool("orchestration_register_agent",
    agent_id="ml_expert",
    capabilities=["machine_learning", "python"]
)

# 2. Create tasks that route to specialists
python_task = call_tool("orchestration_create_task",
    content="Write Python function",
    requirements=["python"]  # Routes to python_expert or ml_expert
)

ml_task = call_tool("orchestration_create_task",
    content="Train ML model",
    requirements=["machine_learning"]  # Routes to ml_expert
)

# 3. Monitor quality
stats = call_tool("orchestration_get_agent_statistics")
# Shows skill distribution and agent counts
```

**Benefits**:
- Automatic specialist matching
- Tasks find best-qualified agents
- Load balanced across team
- Quality tracked per agent

---

### Pattern 4: Error Handling & Retry

```python
# 1. Create task
task_id = create_task(...)

# 2. Attempt execution
agent = route_task(task_id)
assign_task(task_id, agent)
start_task(task_id)

# 3. Agent reports success or failure
try:
    result = do_work()
    complete_task(task_id, result)
except TemporaryError as e:
    # Soft failure - task returns to pending for retry
    fail_task(task_id, str(e), should_retry=True)

except PermanentError as e:
    # Hard failure - task stays failed
    fail_task(task_id, str(e), should_retry=False)

# 4. Monitor retries
queue_metrics = get_queue_metrics()
if queue_metrics["failed"] > 0:
    # Investigate failed tasks
    failed_tasks = query_tasks({"status": "failed"})
```

**Fault Tolerance**:
- Automatic retries on transient errors
- Failed tasks preserved for analysis
- Metrics track failure patterns

---

## Performance Optimization Checklist

Before deployment, verify:

- [ ] Using `limit` parameter on all list operations
- [ ] Filtering criteria specified (don't return all data)
- [ ] Aggregations used instead of manual calculation
- [ ] Tool chains minimize round-trips
- [ ] Error handling implemented (try/catch with retries)
- [ ] Batching applied to loops (1 call per batch, not per item)
- [ ] Exclusion lists used for failed agents (not manual workarounds)
- [ ] Metrics checked periodically (not per-task)

---

## Common Anti-Patterns (Avoid These!)

### Anti-Pattern 1: Poll Everything

```python
# ❌ BAD
all_tasks = get_all_tasks()
for task in all_tasks:
    if task["status"] == "pending":
        route_and_execute(task)
```

**Problem**: Returns 1000s of tasks, blocks on all of them

```python
# ✅ GOOD
pending = poll_tasks(status="pending", limit=10)
for task in pending["tasks"]:
    route_and_execute(task)
# Process next batch
pending = poll_tasks(status="pending", limit=10)
```

---

### Anti-Pattern 2: Manual Filtering

```python
# ❌ BAD
all_agents = get_all_agents()
capable = []
for agent in all_agents:
    if all(skill in agent["skills"] for skill in required):
        capable.append(agent)
best = max(capable, key=lambda a: a["success_rate"])
```

**Problem**: Agent does work that server could do (sorting, filtering)

```python
# ✅ GOOD
agents = find_capable_agents(requirements=["python", "analysis"])
# Router already ranked by quality, returns best
```

---

### Anti-Pattern 3: Retry Loops

```python
# ❌ BAD
for attempt in range(3):
    try:
        agent = route_task(task_id)
        if agent:
            break
    except:
        pass
```

**Problem**: Manual retry logic, no persistence

```python
# ✅ GOOD
agent = route_task(task_id, exclude_agents=blacklist)
if not agent:
    fail_task(task_id, "No capable agents", should_retry=True)
    # Task persisted, can retry later
```

---

### Anti-Pattern 4: Real-Time Health Checks

```python
# ❌ BAD
for agent_id in agents:
    health = get_agent_health(agent_id)  # 10 calls for 10 agents
    print(f"{agent_id}: {health['success_rate']}")
```

**Problem**: 10 tool calls for aggregate info

```python
# ✅ GOOD
stats = get_agent_statistics()  # 1 call
print(f"Avg success rate: {stats['avg_success_rate']}")
print(f"Skill distribution: {stats['skill_distribution']}")
```

---

## Monitoring & Observability

### Key Metrics to Track

1. **Task Queue Health**
   ```python
   metrics = get_queue_metrics()
   pending = metrics["pending"]
   success_rate = metrics["success_rate"]

   # Alert if pending > 100 or success_rate < 0.8
   ```

2. **Agent Performance**
   ```python
   stats = get_agent_statistics()
   avg_success = stats["avg_success_rate"]

   # Alert if avg < 0.7
   ```

3. **Routing Efficiency**
   ```python
   routing = get_routing_stats()
   assignment_rate = routing["assignment_rate"]

   # Alert if < 0.8 (20% of tasks can't be routed)
   ```

### Health Check Template

```python
def check_system_health():
    health = get_health()

    if health["queue"]["success_rate"] < 0.8:
        print("WARNING: Low task success rate")
        return "degraded"

    if health["queue"]["active_tasks"] > 100:
        print("WARNING: High queue depth")
        return "degraded"

    if health["agents"]["total_agents"] == 0:
        print("ERROR: No agents registered")
        return "failed"

    return "healthy"
```

---

## Security Considerations

### Input Validation

Always validate before tool calls:

```python
if not task_id or len(task_id) < 10:
    return {"error": "Invalid task_id"}

if not agent_id or len(agent_id) > 100:
    return {"error": "Invalid agent_id"}

if priority not in ["low", "medium", "high"]:
    return {"error": f"Invalid priority: {priority}"}
```

### Error Message Handling

Never expose internal details:

```python
# ❌ BAD
try:
    result = route_task(...)
except Exception as e:
    return {"error": str(e), "traceback": traceback.format_exc()}

# ✅ GOOD
try:
    result = route_task(...)
except Exception as e:
    return {"error": "Routing failed, no capable agents available"}
```

---

## Scalability Guidelines

| Metric | Recommended Limit | Rationale |
|--------|-------------------|-----------|
| Tasks per poll | 10-50 | Prevents overwhelming agent context |
| Concurrent tasks | 100-1000 | Database scales to 10K+ easily |
| Agents per team | 10-100 | Keep routing efficient |
| Poll frequency | 5-30 sec | Balance latency vs efficiency |
| Batch size | 10 | Reduce round-trips |

---

## Testing Checklist

Before deploying to production:

```python
def test_orchestration():
    # 1. Task lifecycle
    task_id = create_task(...)
    assert task_id is not None

    # 2. Agent registration
    register_agent("test_bot", ["python"])
    agent = find_capable_agents(["python"])
    assert "test_bot" in agent

    # 3. Routing
    task = get_task_status(task_id)
    agent = route_task(task_id)
    assert agent is not None

    # 4. Execution
    assign_task(task_id, agent)
    start_task(task_id)
    complete_task(task_id, "Done")

    # 5. Verification
    final = get_task_status(task_id)
    assert final.status == "completed"

    # 6. Metrics
    metrics = get_queue_metrics()
    assert metrics["completed"] == 1
```

---

## Quick Reference: Tool Selection Guide

| Goal | Tool | Example |
|------|------|---------|
| Create task | `orchestration_create_task` | New work unit |
| Get next work | `orchestration_poll_tasks` | Agent polling |
| Find agents | `orchestration_find_capable_agents` | Search by skill |
| Route task | `orchestration_route_task` | Assign to best |
| Assign task | `orchestration_assign_task` | Explicit assignment |
| Track progress | `orchestration_get_task_status` | Status check |
| Complete task | `orchestration_complete_task` | Mark done |
| Handle failure | `orchestration_fail_task` | Error recovery |
| System health | `orchestration_get_health` | Overall status |
| Query tasks | `orchestration_query_tasks` | Complex search |

---

## Troubleshooting

### Problem: "No capable agents available"

**Check**:
1. Are agents registered? `get_agent_statistics()`
2. Do they have required skills? `find_capable_agents(requirements)`
3. Are they overloaded? `get_agent_health(agent_id)`

**Solution**:
- Register more agents
- Add skills to existing agents
- Wait for agents to complete tasks

### Problem: Task stuck in "assigned"

**Check**:
```python
task = get_task_status(task_id)
if task.status == "assigned":
    print(f"Assigned to: {task.assigned_to}")
    print(f"Since: {task.assigned_at}")
```

**Solution**:
- Agent must call `start_task()`
- If agent died, reassign: `fail_task(..., should_retry=True)`

### Problem: Low success rate

**Check**:
```python
stats = get_agent_statistics()
print(f"Avg success: {stats['avg_success_rate']}")

failed = query_tasks({"status": "failed"})
for task in failed:
    print(f"Task {task['id']}: {task['error']}")
```

**Solution**:
- Review failed task errors
- Retrain failing agents
- Increase task requirements (only assign to proven agents)

---

## Conclusion

Following these best practices ensures:

✅ **Efficient**: Minimal context overhead (20-80 tokens per operation)
✅ **Scalable**: Handles 100-1000s of concurrent tasks
✅ **Reliable**: Built-in error handling and retry logic
✅ **Observable**: Rich metrics and health monitoring
✅ **Maintainable**: Clear patterns and clear error messages

Use batching, server-side filtering, and tool composition to keep agent context lightweight and round-trips minimal.

---

**Last Updated**: November 10, 2025
**Status**: Production Ready
**Version**: 1.0
