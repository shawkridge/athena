# Multi-Agent Coordination System Guide

## Overview

The Athena Multi-Agent Coordination System enables Claude Code to orchestrate multiple specialist agents working in parallel on decomposed tasks. This solves the "long session" problem by:

- **Parallel Execution**: Multiple agents work simultaneously, each with fresh context
- **Memory-Driven Coordination**: Shared state via PostgreSQL (no message brokers)
- **Lean Context**: Orchestrator offloads state to Athena memory (20K tokens vs 200K+)
- **Automatic Recovery**: Health monitoring detects and recovers from agent failures
- **Visual Monitoring**: Real-time dashboard showing agent and task status

## Architecture

```
┌─────────────────────────────────────┐
│ Orchestrator (main tmux pane)       │
│ - Decomposes tasks                  │
│ - Assigns work to agents            │
│ - Monitors progress                 │
│ - Handles failures                  │
└─────────────┬───────────────────────┘
              │
    ┌─────────┴──────────┬──────────┬──────────┐
    │                    │          │          │
┌───▼────┐  ┌──────┐  ┌──▼───┐  ┌──▼────┐  ┌─▼──┐
│Research│  │Analysis│ │Synthesis │Validation│Monitor│
│ Agent  │  │ Agent  │ │ Agent   │ Agent   │Dashboard
│(pane 1)│  │(pane 2)│ │(pane 3) │(pane 4)│(pane 0)
└───┬────┘  └───┬────┘ └───┬────┘ └───┬────┘ └──┬──┘
    │          │          │          │        │
    └──────────┴──────────┴──────────┴────────┘
              │
         PostgreSQL
    (Athena Memory Layer)
```

## Quick Start

### 1. Initialize Database

The coordination system is automatically initialized when the migration runs:

```bash
cd /home/user/.work/athena
python3 -m migrations.runner
```

This creates:
- `agents` table (agent registry)
- Extended `prospective_tasks` (agent assignment fields)
- Helper functions (claim_task, detect_stale_agents, etc.)

### 2. Spawn Agents

Start agent workers in tmux panes:

```bash
./scripts/spawn_agents.sh athena_agents 4
```

This:
- Creates tmux session with 5 panes (4 agents + 1 monitor)
- Starts Research, Analysis, Synthesis, Validation agents
- Runs monitor dashboard in first pane
- Displays real-time status

### 3. Orchestrate a Task

In your Claude Code session:

```python
from athena.coordination import Orchestrator
from athena.core.database import Database

db = Database()
await db.initialize()

orchestrator = Orchestrator(db, tmux_session_name="athena_agents")

# Decompose and execute a task
results = await orchestrator.orchestrate(
    parent_task_id="research_and_implement",
    max_concurrent_agents=4
)
```

### 4. Monitor Progress

The monitor dashboard (pane 0) shows:
- **Agents**: Status, task assignment, heartbeat health
- **Tasks**: Pending/In-Progress/Completed/Failed counts
- **Metrics**: Active agents, task velocity, stale agents

Press `Ctrl+C` in monitor to start/stop auto-refresh.

### 5. Handle /clear

When context gets full:

```
Context 80% full; offloading to memory...
```

The orchestrator automatically:
1. Saves state to episodic memory
2. Reduces context usage (just task IDs)
3. Runs `/clear` (agents keep working)
4. Reloads state from memory after `/clear`

No manual intervention needed!

### 6. Cleanup

When done, kill the session:

```bash
./scripts/cleanup_agents.sh athena_agents true
```

The `true` flag archives agent logs for debugging.

## How It Works

### Agent Lifecycle

```
Register → Idle → Work Loop → Execute Task → Report → Complete → Idle
  ↑                              ↑
  │                              │
  └──────────── Respawn on failure ────────────┘
```

Each agent:
1. Polls for assigned work in database
2. Claims task atomically (optimistic locking)
3. Executes task (reports progress)
4. Stores findings in Athena memory
5. Reports completion or failure
6. Returns to idle state

### Task Claiming (Atomic)

Task claiming uses PostgreSQL's optimistic locking:

```sql
UPDATE prospective_tasks
SET assigned_agent_id = $1, status = 'IN_PROGRESS'
WHERE task_id = $2 AND status = 'PENDING' AND version = $3
```

- Only ONE agent can claim a task
- Version stamp prevents lost updates
- No explicit locks (high throughput)

### Memory Offloading

When orchestrator context reaches 80%:

```python
# State is saved to episodic_events as JSON checkpoint
checkpoint = {
    "orchestrator_id": "...",
    "parent_task_id": "...",
    "decomposed_subtasks": [...],
    "completed_tasks": [...],
    "progress_pct": 60.0,
    "timestamp": "...",
}

# Orchestrator reloads from checkpoint after /clear
# Uses ~17K tokens instead of 200K+
```

Context usage per component:
- Orchestrator identity: 10K tokens
- Active task IDs: 5K tokens (50 tasks)
- Agent status: 2K tokens (10 agents)
- **Total: ~17K tokens (8.5% of window)**

### Health Monitoring

The `HealthMonitor` background task:
- Detects stale heartbeats (agent hung)
- Finds stuck tasks (no progress)
- Identifies retryable failures
- Automatically respawns agents (up to 3 attempts)
- Reassigns failed tasks

Thresholds (configurable):
- Stale heartbeat: 60 seconds
- Stuck task: 300 seconds (5 minutes)
- Max retries: 3 attempts

## Extending the System

### Adding a New Specialist Agent

1. Create agent class:

```python
# src/athena/coordination/agents/custom.py

from ..agent_worker import AgentWorker
from ..models import AgentType, Task

class CustomAgent(AgentWorker):
    def __init__(self, agent_id: str, db):
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.CUSTOM,  # Add type to enum
            db=db,
        )

    async def execute(self, task: Task) -> Dict[str, Any]:
        # Your custom logic here
        await self.report_progress(50, findings={"stage": "processing"})
        # ... do work ...
        return findings
```

2. Add to capabilities mapping:

```python
# src/athena/coordination/models.py

AGENT_CAPABILITIES = {
    # ...
    AgentType.CUSTOM: ["capability1", "capability2"],
}
```

3. Export in `__init__.py`:

```python
from .agents.custom import CustomAgent

__all__ = [..., "CustomAgent"]
```

4. Include in spawn script:

```bash
AGENT_TYPES=("research" "analysis" "synthesis" "validation" "custom")
```

### Integrating with Web UI

The coordination system is designed for eventual web UI:

1. All operations are clean Python async functions (no tmux coupling)
2. State stored in database (queryable)
3. No blocking operations (suitable for HTTP endpoints)

Future FastAPI integration:

```python
from fastapi import FastAPI
from athena.coordination import Orchestrator, HealthMonitor

app = FastAPI()

@app.post("/orchestrate")
async def orchestrate_task(task_id: str):
    orchestrator = Orchestrator(db)
    return await orchestrator.orchestrate(task_id)

@app.get("/status/{orchestrator_id}")
async def get_status(orchestrator_id: str):
    # Query state from database
    return await db.fetch_one(...)
```

## Troubleshooting

### Agents Not Starting

Check tmux session:
```bash
tmux list-sessions
tmux capture-pane -t athena_agents:0 -p  # View pane output
```

Check agent logs:
```bash
tail -f logs/agents/athena_agents-*/pane_*.log
```

### Tasks Not Being Claimed

Check agent heartbeat:
```bash
psql -c "SELECT agent_id, status, last_heartbeat FROM agents"
```

If heartbeat is stale, agent process may have crashed.

### High Context Usage

Check orchestration state size:
```python
await offload_mgr.checkpoint_orchestration_state(state)
# Should reduce context by offloading
```

Use minimal context mode:
```python
context = await offload_mgr.get_minimal_context(state)
# Returns just IDs and stats
```

### Stuck Tasks

Health monitor should detect and reassign within 5 minutes.
To manually intervene:

```bash
psql -c "SELECT * FROM prospective_tasks WHERE status='IN_PROGRESS' ORDER BY claimed_at"
```

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Agent startup | <1s | Minimal I/O |
| Task claim | <10ms | Optimistic lock |
| Progress report | <50ms | DB update |
| Heartbeat | <5ms | Simple UPDATE |
| Health check | <1s | Full cycle (10s interval) |
| Monitor refresh | <100ms | Dashboard render |

## Memory Usage

| Component | Tokens | % of 200K |
|-----------|--------|----------|
| Orchestrator base | 10K | 5% |
| Task pointers (50) | 5K | 2.5% |
| Agent status (10) | 2K | 1% |
| **Total** | **17K** | **8.5%** |

Compare to single-agent (full context):
- Single agent with same task: ~150K tokens (75%)
- Multi-agent orchestration: ~17K tokens (8.5%)
- **Savings: 88% context reduction**

## Next Steps

1. **Test with sample task** - Run orchestration on a decomposed task
2. **Monitor dashboard** - Verify agents are claiming work
3. **Trigger /clear** - Confirm context offloading works
4. **Add custom agents** - Implement domain-specific specialist
5. **Scale up** - Test with 6+ agents and complex workflows

## Architecture Decisions

### Why PostgreSQL (not message queues)?

- **Simpler**: No Kafka/RabbitMQ setup
- **Queryable**: Easy to monitor and debug
- **Persistent**: Task state survives restart
- **Atomic**: Built-in support for optimistic locking
- **Integrated**: Already in Athena stack

### Why Tmux (not subprocess)?

- **Visual**: Can see agent output in real-time
- **Debuggable**: Each agent has its own window
- **Killable**: Can pause/resume individual agents
- **Minimal**: No additional dependencies

### Why Episodic Memory (not separate table)?

- **Unified**: All events in one system
- **Consolidatable**: Patterns extracted by consolidation
- **Searchable**: Full semantic search over checkpoints
- **Auditable**: Complete history preserved

## References

- `src/athena/coordination/` - Core implementation
- `src/athena/coordination/agents/` - Specialist agents
- `scripts/spawn_agents.sh` - Agent spawning
- `migrations/008_agent_coordination.sql` - Database schema
