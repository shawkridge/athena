# Monitoring Dashboard Plan

Comprehensive web-based dashboard for real-time monitoring of the Athena memory system, including hook execution, memory health, cognitive load, consolidation, projects, and task tracking.

**Status**: Planning Phase
**Type**: Web Dashboard (Browser-based)
**Scope**: Complete system visibility
**Timeline**: 2-3 weeks estimated

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Dashboard Pages](#dashboard-pages)
3. [Key Metrics](#key-metrics)
4. [Technical Stack](#technical-stack)
5. [Data Models](#data-models)
6. [API Specification](#api-specification)
7. [Frontend Wireframes](#frontend-wireframes)
8. [Implementation Phases](#implementation-phases)

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Web Browser                                │
│         (React/Vue.js + Chart.js/Plotly)                   │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  REST/WebSocket API │
        │  (FastAPI Backend)  │
        └──────────┬──────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
[Memory DB]  [Hook Events]  [Task DB]
 (SQLite)     (Episodic)   (Projects)
```

### Key Components

1. **Frontend** (React/Vue.js)
   - Dashboard pages (overview, hooks, memory, tasks, projects)
   - Real-time charts and metrics
   - Interactive tables with filtering/sorting
   - WebSocket for live updates

2. **Backend API** (FastAPI)
   - REST endpoints for all metrics
   - WebSocket endpoints for real-time data
   - Authentication/authorization
   - Data aggregation and caching

3. **Data Sources**
   - Athena memory database (SQLite)
   - Hook execution logs
   - Task/project database
   - Episodic events

---

## Dashboard Pages

### 1. Overview Dashboard (Main Landing Page)

**Purpose**: System health at a glance

**Sections**:
- **System Status** (3 cards)
  - Memory Quality Score: 0.85 (color: green/yellow/red)
  - Cognitive Load: 4/7 items (progress bar)
  - Last Consolidation: 2 hours ago

- **Live Metrics** (4 mini-charts)
  - Hook Execution Rate (ops/min)
  - Memory Consolidation Progress (%)
  - Agent Invocation Frequency
  - Cognitive Load Trend (24h)

- **Recent Activity** (Table)
  - Timestamp, Event Type, Status, Duration
  - Last 10 events with filtering

- **Health Indicators** (Status grid)
  - Database: ✅ Healthy
  - Hooks: ✅ All Active
  - Memory: ⚠️ Warning
  - Tasks: ✅ On Track

---

### 2. Hook Execution Monitor

**Purpose**: Real-time hook performance tracking

**Sections**:
- **Hook Status** (6 cards - one per hook)
  ```
  ┌─────────────────────────┐
  │ post-tool-use.sh        │
  │ Status: ✅ Active       │
  │ Calls: 342 / session    │
  │ Avg Latency: 42ms       │
  │ Success Rate: 99.7%     │
  │ Last: 2s ago            │
  └─────────────────────────┘
  ```

- **Hook Performance Timeline** (Line chart)
  - X-axis: Time (last 24h)
  - Y-axis: Latency (ms)
  - One line per hook
  - Hover for details

- **Agent Invocations** (Pie chart)
  - Breakdown by agent
  - Click to filter by agent
  - Show priority and success rate

- **Error Analysis** (Table)
  - Hook, Error Type, Count, Last Occurrence
  - Sortable, filterable

- **Execution Statistics** (Detailed stats)
  - Total executions: 12,450
  - Avg latency: 45ms
  - Error rate: 0.3%
  - Slowest hook: pre-execution.sh (1.2s)

---

### 3. Memory System Health

**Purpose**: Memory quality and consolidation tracking

**Sections**:
- **Quality Metrics** (Gauges - 4 cards)
  ```
  Compression Ratio: 78%  [████████░] GREEN
  Recall Accuracy:   85%  [████████░] GREEN
  Consistency:       82%  [████████░] GREEN
  Density:           88%  [████████░] GREEN
  ```

- **Consolidation Pipeline** (Progress visual)
  ```
  Episodic Events: 8,245  [████████████]
  → Extracted Patterns: 145 patterns (78% compression)
  → Semantic Memory: 2,150 facts
  → Procedures: 101 workflows
  → Quality: 0.85 (Excellent)
  ```

- **Memory Layers Breakdown** (Stacked bar chart)
  - Episodic (events)
  - Semantic (facts)
  - Procedural (workflows)
  - Prospective (goals/tasks)
  - Knowledge Graph (entities)
  - Meta-Memory (quality info)

- **Gap Analysis** (Table)
  - Gap Type, Domain, Count, Severity
  - Contradictions, Uncertainties, Unknowns
  - Click to investigate

- **Domain Expertise** (Radar chart)
  - Spokes: Different domains (auth, database, api, architecture, etc.)
  - Coverage level per domain

- **Recent Consolidations** (Timeline)
  - Date/Time, Events Processed, Patterns Extracted, Quality Score
  - Click for details

---

### 4. Cognitive Load Monitor

**Purpose**: Working memory capacity tracking

**Sections**:
- **Current Load** (Large gauge)
  ```
  4/7 Items
  ████░░░
  ```
  With zones: GREEN (0-3), YELLOW (4-5), RED (6-7)

- **Active Items** (List with decay visualization)
  ```
  1. Active Goal: "Implement authentication" [████░░░] 80% fresh
  2. Recent Fact: "JWT implementation pattern" [███░░░░] 60% fresh
  3. Procedure: "database-optimization" [██░░░░░] 40% fresh
  4. Query Context: "Previous search results" [█░░░░░░] 20% fresh
  ```

- **Load Trend** (Line chart - 24h)
  - Show peaks and valleys
  - Highlight warnings (>5 items)
  - Show consolidation events (dips)

- **Decay Rates** (Animation)
  - Show which items are fading fastest
  - Estimated time before loss

- **Capacity Warnings**
  - "⚠️ Approaching capacity (5/7)"
  - "🚨 CRITICAL (7/7) - Consolidation recommended"

---

### 5. Projects & Tasks

**Purpose**: Project progress and task tracking

**Sections**:
- **Active Projects** (Cards grid)
  ```
  ┌─────────────────────────┐
  │ Project: athena         │
  │ Progress: 95%           │
  │ ████████████░ 11/12     │
  │ Tasks: 42/43            │
  │ Health: ✅ On Track     │
  │ Last Update: 1h ago     │
  └─────────────────────────┘
  ```

- **Project Timeline** (Gantt-style chart)
  - Phases and milestones
  - Completion percentages
  - Blockers/risks

- **Active Goals** (Priority table)
  - Goal, Priority, Deadline, Progress, Status
  - Color-coded by priority
  - Click for details

- **Task Breakdown** (Tree structure)
  - Expandable project → phase → task hierarchy
  - Status indicators (✅, 🔄, ⚠️, ❌)
  - Progress percentages

- **Milestone Tracker**
  - Upcoming milestones
  - Completion status
  - Days remaining

- **Resource Allocation** (Pie chart)
  - Estimated vs actual hours per project
  - Resource conflicts highlighted

---

### 6. Learning Analytics

**Purpose**: Strategy effectiveness and learning patterns

**Sections**:
- **Strategy Effectiveness** (Bar chart)
  - Strategy names on X-axis
  - Success rate on Y-axis
  - Color by effectiveness (green/yellow/red)

- **Learning Metrics** (Stats cards)
  - Encoding Efficiency: 82%
  - Pattern Recognition: 145 patterns extracted
  - Procedure Reuse Rate: 34%
  - Knowledge Gaps Resolved: 23/45

- **Consolidation Quality Trend** (Line chart)
  - Quality score over time (days/weeks)
  - Show impact of consolidation strategies
  - Target line at 0.85

- **Top Procedures** (Table)
  - Procedure name, Usage Count, Success Rate, Last Used
  - Most effective first

- **Learning Patterns** (Heatmap)
  - Time of day vs learning effectiveness
  - Day of week patterns
  - Identify optimal learning times

---

### 7. Advanced Analysis

**Purpose**: Deep insights and optimization

**Sections**:
- **Critical Path Analysis**
  - Longest task chains
  - Bottleneck identification
  - Optimization suggestions

- **Dependency Graph**
  - Interactive visualization
  - Show task/goal dependencies
  - Highlight blockers

- **Performance Profiling**
  - Tool execution times
  - Agent response times
  - Database query performance
  - Identify slow operations

- **Anomaly Detection**
  - Unusual execution patterns
  - Performance degradation
  - Error rate spikes

- **Recommendations**
  - "Run consolidation now (high load)"
  - "Archive old events (database growth)"
  - "Review authentication procedures (low effectiveness)"

---

## Key Metrics

### Hook Execution Metrics
- **Execution Count**: Total operations per hook
- **Average Latency**: Mean execution time (ms)
- **P95 Latency**: 95th percentile (performance tail)
- **Success Rate**: % of successful executions
- **Error Rate**: % of failures
- **Agent Invocations**: Number of agents triggered

### Memory System Metrics
- **Quality Score**: 0.0-1.0 (compression, recall, consistency)
- **Consolidation Status**: % complete, events processed
- **Memory Usage**: Total database size
- **Gap Count**: Contradictions + uncertainties
- **Domain Coverage**: % coverage per domain
- **Procedure Effectiveness**: Usage rate, success rate

### Cognitive Load Metrics
- **Current Load**: X/7 items in working memory
- **Capacity Utilization**: %
- **Item Decay Rate**: % per hour
- **Load Warnings**: Count of capacity warnings
- **Consolidation Frequency**: Consolidations per session
- **Context Switch Cost**: Time to switch projects

### Task & Goal Metrics
- **Active Goals**: Count
- **Task Completion Rate**: % completed on time
- **Milestone Progress**: % to next milestone
- **Blocker Count**: Active blockers
- **Estimated vs Actual**: Time estimate accuracy
- **Resource Utilization**: % of allocated time used

### Learning Metrics
- **Encoding Efficiency**: % of events consolidated
- **Pattern Discovery**: New patterns per session
- **Procedure Reuse**: % of tasks using procedures
- **Strategy Effectiveness**: Success rate per strategy
- **Knowledge Gaps**: Count remaining
- **Learning Velocity**: Improvements per week

---

## Technical Stack

### Frontend
```
React 18.x
├── State: Redux Toolkit + React Query
├── UI Components: Material-UI or Tailwind
├── Charts: Plotly.js or Chart.js
├── Real-time: Socket.io client
└── Testing: Jest + React Testing Library
```

### Backend
```
Python 3.10+
├── Framework: FastAPI
├── Database: SQLite (existing) + Redis (caching)
├── Real-time: WebSockets (FastAPI native)
├── API: REST + GraphQL (optional)
├── Auth: JWT tokens
└── Testing: Pytest
```

### DevOps
```
├── Containerization: Docker
├── Orchestration: Docker Compose
├── Monitoring: Prometheus + Grafana (optional)
├── CI/CD: GitHub Actions
└── Deployment: Local/Docker
```

---

## Data Models

### API Response Models

```python
# Hook Metrics
class HookMetrics(BaseModel):
    hook_name: str
    status: str  # "active" | "error" | "idle"
    execution_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    success_rate: float  # 0.0-1.0
    error_count: int
    last_execution: datetime
    agents_invoked: List[str]

# Memory Metrics
class MemoryMetrics(BaseModel):
    quality_score: float  # 0.0-1.0
    compression_ratio: float  # 0.0-1.0
    recall_accuracy: float  # 0.0-1.0
    consistency: float  # 0.0-1.0
    event_count: int
    semantic_count: int
    procedure_count: int
    gap_count: int
    domain_coverage: Dict[str, float]
    last_consolidation: datetime

# Cognitive Load
class CognitiveLoad(BaseModel):
    current_load: int  # 0-7
    max_capacity: int  # 7
    utilization_percent: float
    active_items: List[WorkingMemoryItem]
    decay_rate: float  # % per hour
    warnings: List[str]

# Task Metrics
class TaskMetrics(BaseModel):
    active_goals: int
    active_tasks: int
    completion_rate: float
    on_time_rate: float
    blocker_count: int
    milestone_progress: float
    estimated_vs_actual_ratio: float

# Learning Metrics
class LearningMetrics(BaseModel):
    encoding_efficiency: float
    patterns_extracted: int
    procedure_reuse_rate: float
    strategy_effectiveness: Dict[str, float]
    knowledge_gaps_remaining: int
    learning_velocity: float  # improvements per week
```

---

## API Specification

### Endpoints (REST)

```
GET  /api/dashboard/overview
     → Returns all overview metrics

GET  /api/hooks/status
     → List all hooks with current status

GET  /api/hooks/{hook_name}/metrics
     → Detailed metrics for specific hook

GET  /api/hooks/{hook_name}/history?hours=24
     → Historical data for time period

GET  /api/memory/health
     → Complete memory health report

GET  /api/memory/consolidation
     → Consolidation pipeline status

GET  /api/memory/gaps
     → List knowledge gaps/contradictions

GET  /api/memory/domains
     → Domain coverage analysis

GET  /api/load/current
     → Current cognitive load status

GET  /api/load/history?hours=24
     → Historical load data

GET  /api/load/trend
     → Load trend analysis

GET  /api/projects
     → List all projects with progress

GET  /api/projects/{project_id}
     → Detailed project information

GET  /api/goals?project_id=1
     → Goals for specific project

GET  /api/tasks?project_id=1
     → Tasks for specific project

GET  /api/learning/strategies
     → Strategy effectiveness analysis

GET  /api/learning/procedures
     → Top procedures by effectiveness

GET  /api/learning/trends
     → Learning metric trends

GET  /api/analysis/critical-path?project_id=1
     → Critical path analysis

GET  /api/analysis/bottlenecks
     → Performance bottleneck analysis

GET  /api/analysis/anomalies
     → Detected anomalies
```

### WebSocket Endpoints

```
WS  /ws/live/hooks
    → Real-time hook execution updates

WS  /ws/live/memory
    → Real-time memory metrics

WS  /ws/live/load
    → Real-time cognitive load updates

WS  /ws/live/tasks
    → Real-time task/goal updates

WS  /ws/notifications
    → System alerts and warnings
```

---

## Frontend Wireframes

### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  Athena Monitoring Dashboard              [Profile ⚙️] │
├─────────────────────────────────────────────────────────┤
│  [Overview] [Hooks] [Memory] [Load] [Tasks] [Learning] │
├──────────────────────────────────────────────────────────
│                                                          │
│  [System Status Cards]                   [Live Chart]   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │████░░░░│    │
│  │Quality   │ │Load      │ │Hooks     │  │        │    │
│  │ 0.85     │ │4/7       │ │6 Active  │  │ Trend  │    │
│  └──────────┘ └──────────┘ └──────────┘  │        │    │
│                                           └────────┘    │
│  [Recent Activity Table]                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Time  │ Event         │ Status │ Duration       │  │
│  │ 12:45 │ consolidate   │ ✅     │ 2.3s          │  │
│  │ 12:44 │ post-tool-use │ ✅     │ 45ms          │  │
│  │ 12:43 │ session-start │ ✅     │ 320ms         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────
```

### Page-Specific Layouts

**Hooks Page**:
- 6 hook status cards (left column)
- Performance timeline (large, right)
- Agent breakdown pie chart (bottom left)
- Error analysis table (bottom right)

**Memory Page**:
- Quality gauges (top row)
- Consolidation pipeline (large middle)
- Layer breakdown chart (left)
- Gap analysis table (right)

**Load Page**:
- Large load gauge (top center)
- Active items list (left)
- 24h trend chart (right)
- Warnings panel (bottom)

---

## Implementation Phases

### Phase 1: Core Backend (Week 1)

**Tasks**:
1. Create FastAPI application structure
2. Implement data aggregation layer
3. Build REST API endpoints (overview, hooks, memory, load)
4. Add database queries for metrics
5. Implement caching layer (Redis)
6. Unit tests for API endpoints

**Files to Create**:
```
athena_dashboard/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── config.py
│   ├── models/
│   │   ├── metrics.py
│   │   └── responses.py
│   ├── routes/
│   │   ├── dashboard.py
│   │   ├── hooks.py
│   │   ├── memory.py
│   │   ├── load.py
│   │   ├── tasks.py
│   │   └── learning.py
│   ├── services/
│   │   ├── metrics_aggregator.py
│   │   ├── data_loader.py
│   │   └── cache_manager.py
│   └── tests/
│       └── test_api.py
└── docker-compose.yml
```

### Phase 2: WebSocket & Real-time (Week 1.5)

**Tasks**:
1. Add WebSocket support to FastAPI
2. Implement real-time data streaming
3. Create live event queue
4. Add connection management
5. WebSocket tests

**Files to Create**:
```
├── backend/
│   ├── websocket/
│   │   ├── manager.py
│   │   ├── handlers.py
│   │   └── events.py
│   ├── routes/
│   │   └── websocket.py
│   └── tests/
│       └── test_websocket.py
```

### Phase 3: Frontend - Structure (Week 2)

**Tasks**:
1. Create React app structure
2. Set up routing (React Router)
3. Build layout/navigation
4. Implement Redux state management
5. Create reusable UI components
6. Style with Material-UI or Tailwind

**Files to Create**:
```
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── index.js
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   ├── NavBar.jsx
│   │   │   ├── MetricCard.jsx
│   │   │   ├── Chart.jsx
│   │   │   └── Table.jsx
│   │   ├── pages/
│   │   │   ├── Overview.jsx
│   │   │   ├── Hooks.jsx
│   │   │   ├── Memory.jsx
│   │   │   ├── Load.jsx
│   │   │   ├── Tasks.jsx
│   │   │   └── Learning.jsx
│   │   ├── store/
│   │   │   └── slices/
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   └── websocket.js
│   │   └── styles/
│   └── package.json
```

### Phase 4: Frontend - Pages (Week 2.5)

**Tasks**:
1. Implement Overview page with all sections
2. Implement Hooks page with performance charts
3. Implement Memory page with health gauges
4. Implement Load page with capacity visualization
5. Implement Tasks page with project tracking
6. Implement Learning page with analytics

**Files per page**:
```
pages/
├── Overview.jsx (200 lines)
├── Hooks.jsx (300 lines)
├── Memory.jsx (350 lines)
├── Load.jsx (250 lines)
├── Tasks.jsx (400 lines)
└── Learning.jsx (300 lines)
```

### Phase 5: Real-time Integration (Week 3)

**Tasks**:
1. Connect frontend to WebSocket endpoints
2. Implement live data updates
3. Add animations for metric changes
4. Implement notification system
5. Add auto-refresh capabilities
6. Performance optimization

### Phase 6: Testing & Deployment (Week 3.5)

**Tasks**:
1. End-to-end tests (Cypress/Playwright)
2. Load testing (k6 or similar)
3. Security review
4. Docker containerization
5. Docker Compose configuration
6. Deployment documentation

---

## Example Visualizations

### Overview Dashboard - ASCII Art

```
╔════════════════════════════════════════════════════════════════╗
║                    ATHENA MONITORING DASHBOARD                 ║
║                                                                ║
║  System Status              Live Metrics (Last 24h)           ║
║  ┌──────────────────────┐  ┌──────────────────────────────┐  ║
║  │ Quality: 0.85 ✅     │  │ Hook Execution Rate          │  ║
║  │ Load: 4/7 ⚠️        │  │ ████████░░ 342 ops/min      │  ║
║  │ Hooks: 6/6 ✅       │  │                              │  ║
║  │ Consol: 2h ago ✅   │  │ Cognitive Load               │  ║
║  │ Tasks: 42/43 ✅     │  │ ████░░░░░░ 4/7 items        │  ║
║  └──────────────────────┘  │                              │  ║
║                             │ Consolidation Progress       │  ║
║  Recent Activity            │ ███████████░░░ 78% complete│  ║
║  ┌──────────────────────┐   └──────────────────────────────┘  ║
║  │ post-tool-use    ✅  │                                    ║
║  │ session-start    ✅  │   Health Indicators                ║
║  │ consolidate      ✅  │   ┌──────────────────────────────┐ ║
║  │ pre-execution    ✅  │   │ Database      ✅ Healthy     │ ║
║  │ post-task-compl  ✅  │   │ Hooks         ✅ All Active  │ ║
║  │ context-inject   ✅  │   │ Memory        ⚠️ Moderate    │ ║
║  └──────────────────────┘   │ Tasks         ✅ On Track    │ ║
║                             └──────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════╝
```

---

## Next Steps

1. **Decide on exact tech stack** (React vs Vue, Plotly vs Chart.js, etc.)
2. **Set up project structure** and GitHub repository
3. **Begin Phase 1** (Backend API development)
4. **Create detailed component specifications** for each page
5. **Set up CI/CD pipeline** for automated testing/deployment

---

**Estimated Effort**: 80-100 hours (3 weeks)
**Team Size**: 1-2 developers
**Complexity**: Medium-High
**Value**: High (complete system visibility)
