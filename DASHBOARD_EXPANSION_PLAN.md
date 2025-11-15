# Dashboard Expansion Plan - Complete Athena Visibility

**Objective**: Build comprehensive dashboard covering all 8 memory layers + system monitoring
**Scope**: Phase 4B - Advanced Dashboard Features
**Estimated Effort**: 3-5 days
**Priority**: HIGH

---

## Current State

**Implemented**:
- ✅ Research Streaming (Phase 3.4)
- ✅ Agent Progress Monitoring
- ✅ Basic Memory Health

**Missing**:
- ❌ Full 8-layer memory system visibility
- ❌ Hook execution monitoring
- ❌ Episodic events timeline
- ❌ Semantic memory search
- ❌ Procedural skills library
- ❌ Task/goal management
- ❌ Knowledge graph visualization
- ❌ Consolidation analytics
- ❌ Meta-memory quality metrics
- ❌ Working memory status
- ❌ System-wide analytics

---

## Architecture: New Multi-Panel Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATHENA DASHBOARD (Expanded)                  │
├─────────────────────────────────────────────────────────────────┤
│ Navigation Sidebar                                              │
│ ├─ Home / Overview                                              │
│ ├─ Memory Layers (expandable)                                   │
│ │  ├─ Layer 1: Episodic Memory                                  │
│ │  ├─ Layer 2: Semantic Memory                                  │
│ │  ├─ Layer 3: Procedural Memory                                │
│ │  ├─ Layer 4: Prospective Memory                               │
│ │  ├─ Layer 5: Knowledge Graph                                  │
│ │  ├─ Layer 6: Meta-Memory                                      │
│ │  ├─ Layer 7: Consolidation                                    │
│ │  └─ Layer 8: RAG & Planning                                   │
│ ├─ System Monitoring                                            │
│ │  ├─ Hook Execution                                            │
│ │  ├─ Working Memory                                            │
│ │  └─ Performance Metrics                                       │
│ ├─ Analytics                                                    │
│ │  ├─ Learning Trends                                           │
│ │  ├─ Memory Quality                                            │
│ │  └─ System Health                                             │
│ └─ Settings                                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## New Pages (16 Total)

### 1. Home / Overview Page
**Component**: `OverviewPage.tsx`
- System health status (8 layers)
- Recent activity (last 24h)
- Key metrics at a glance
- Quick access shortcuts
- Alerts and notifications

### 2. Episodic Memory Layer (Layer 1)
**Component**: `EpisodicMemoryPage.tsx`
- Timeline view of events
- Event filtering (type, source, time range)
- Event details with drill-down
- Import/export functionality
- Search with full-text indexing

**Metrics**:
- Total events stored
- Events per hour (trend)
- Event types distribution
- Oldest/newest event
- Storage efficiency

### 3. Semantic Memory Layer (Layer 2)
**Component**: `SemanticMemoryPage.tsx`
- Knowledge base search
- Similarity search UI
- Retrieved memories with relevance scores
- Learned facts browser
- Vector embedding visualization

**Metrics**:
- Total memories
- Domains covered
- Quality scores (per domain)
- Search hit rate
- Memory decay analysis

### 4. Procedural Memory Layer (Layer 3)
**Component**: `ProceduralMemoryPage.tsx`
- Learned procedures library
- Procedure effectiveness ranking
- Execution history
- Success/failure rates
- Procedure details with steps

**Metrics**:
- Total procedures learned (101)
- Most effective procedures
- Procedure usage trends
- Success rate by procedure
- Learning rate

### 5. Prospective Memory Layer (Layer 4)
**Component**: `ProspectiveMemoryPage.tsx`
- Active goals and tasks
- Task status (pending/active/completed)
- Goal hierarchy visualization
- Deadline tracking
- Task triggers and conditions

**Metrics**:
- Active goals
- Task completion rate
- Goal achievement rate
- Overdue tasks
- Trigger effectiveness

### 6. Knowledge Graph Layer (Layer 5)
**Component**: `KnowledgeGraphPage.tsx`
- Interactive graph visualization
- Entity browser
- Relationship explorer
- Community detection results
- Graph statistics

**Metrics**:
- Total entities (5,426+)
- Relationships count
- Communities detected
- Graph density
- Centrality measures

### 7. Meta-Memory Layer (Layer 6)
**Component**: `MetaMemoryPage.tsx`
- Quality scores dashboard
- Expertise tracking (by domain)
- Attention allocation
- Cognitive load visualization
- Confidence scores

**Metrics**:
- Overall quality score
- Per-layer quality
- Expertise ranking
- Attention distribution
- Uncertainty analysis

### 8. Consolidation Layer (Layer 7)
**Component**: `ConsolidationPage.tsx`
- Consolidation run history
- Pattern extraction results
- Dual-process insights (System 1/2)
- Clustering visualization
- Pattern effectiveness

**Metrics**:
- Consolidation runs (count, frequency)
- Patterns extracted
- Pattern quality
- Cluster quality
- Compression ratio

### 9. RAG & Planning Layer (Layer 8)
**Component**: `RAGPlanningPage.tsx`
- Query processing pipeline
- Retrieval results
- Plan validation history
- Formal verification reports
- Scenario simulation results

**Metrics**:
- Retrieval quality (precision/recall)
- Plan success rate
- Verification passes
- Simulation coverage
- Response quality

### 10. Hook Execution Monitor
**Component**: `HookExecutionPage.tsx`
- Real-time hook performance
- Hook latency metrics
- Success/failure rates
- Hook execution timeline
- Agent invocation tracking

**Metrics**:
- Hook latency (ms)
- Success rate
- Agent invocations per hook
- Most active hooks
- Error rates

### 11. Working Memory Monitor
**Component**: `WorkingMemoryPage.tsx`
- Current working memory (7±2 items)
- Freshness timeline
- Item importance scoring
- Cognitive load gauge
- Context switching analysis

**Metrics**:
- Current load (0-7)
- Average item freshness
- Load trend (last 24h)
- Context switches
- Capacity utilization

### 12. Learning Analytics
**Component**: `LearningAnalyticsPage.tsx`
- Strategy effectiveness ranking
- Procedure learning rate
- Knowledge acquisition trends
- Gap resolution tracking
- Learning curve visualization

**Metrics**:
- Procedures per week
- Quality improvement rate
- Learning velocity
- Domain coverage growth
- Effectiveness trend

### 13. System Health Dashboard
**Component**: `SystemHealthPage.tsx`
- 8-layer health overview
- Consolidation progress
- Memory utilization
- System performance
- Alerts and warnings

**Metrics**:
- Overall system health
- Per-layer health
- Database size
- Query latency
- API response times

### 14. Research Console (Enhanced)
**Component**: `ResearchConsolePage.tsx`
(Already implemented in Phase 4A, but enhanced)
- Multi-task research support
- Research history
- Result archiving
- Batch research
- Research templates

### 15. Analytics & Insights
**Component**: `AnalyticsPage.tsx`
- Custom metric dashboards
- Time-series analysis
- Correlation analysis
- Anomaly detection
- Forecasting/predictions

### 16. Settings & Administration
**Component**: `SettingsPage.tsx`
- Dashboard customization
- Alert configuration
- Data retention settings
- Export/import options
- System configuration

---

## Backend API Endpoints Required

### Episodic Memory API
```
GET /api/episodic/events?limit=100&offset=0&sort=timestamp
GET /api/episodic/events/{id}
GET /api/episodic/timeline?range=24h
GET /api/episodic/stats
GET /api/episodic/search?query=...
```

### Semantic Memory API
```
GET /api/semantic/memories?limit=50&offset=0
GET /api/semantic/memories/{id}
POST /api/semantic/search
GET /api/semantic/domains
GET /api/semantic/quality/{domain}
GET /api/semantic/stats
```

### Procedural Memory API
```
GET /api/procedural/skills?limit=100&sort=effectiveness
GET /api/procedural/skills/{id}
GET /api/procedural/skill/{id}/history
GET /api/procedural/stats
GET /api/procedural/effectiveness-ranking
```

### Prospective Memory API
```
GET /api/prospective/goals
GET /api/prospective/tasks?status=active
GET /api/prospective/tasks/{id}
POST /api/prospective/tasks/{id}/complete
GET /api/prospective/stats
```

### Knowledge Graph API
```
GET /api/graph/entities?limit=100
GET /api/graph/entities/{id}
GET /api/graph/relationships?limit=100
GET /api/graph/communities
GET /api/graph/visualization
GET /api/graph/stats
```

### Meta-Memory API
```
GET /api/meta/quality-scores
GET /api/meta/quality/{layer}
GET /api/meta/expertise
GET /api/meta/attention
GET /api/meta/stats
```

### Consolidation API
```
GET /api/consolidation/runs?limit=50
GET /api/consolidation/runs/{id}
GET /api/consolidation/patterns
GET /api/consolidation/stats
GET /api/consolidation/progress
```

### RAG & Planning API
```
GET /api/rag/retrievals?limit=50
GET /api/rag/query-performance
POST /api/planning/validate
GET /api/planning/verification-results
GET /api/planning/stats
```

### Hook Execution API
```
GET /api/hooks/status
GET /api/hooks/{name}/metrics
GET /api/hooks/{name}/history
GET /api/hooks/{name}/latency-chart
GET /api/hooks/stats
```

### Working Memory API
```
GET /api/memory/working
GET /api/memory/working/timeline
GET /api/memory/working/capacity
GET /api/memory/cognitive-load
GET /api/memory/stats
```

### System API
```
GET /api/system/health
GET /api/system/performance
GET /api/system/alerts
GET /api/system/database-size
GET /api/system/stats
```

---

## Frontend Components Structure

```
src/
├── pages/
│   ├── OverviewPage.tsx (NEW)
│   ├── EpisodicMemoryPage.tsx (NEW)
│   ├── SemanticMemoryPage.tsx (NEW)
│   ├── ProceduralMemoryPage.tsx (NEW)
│   ├── ProspectiveMemoryPage.tsx (NEW)
│   ├── KnowledgeGraphPage.tsx (NEW)
│   ├── MetaMemoryPage.tsx (NEW)
│   ├── ConsolidationPage.tsx (NEW)
│   ├── RAGPlanningPage.tsx (NEW)
│   ├── HookExecutionPage.tsx (NEW)
│   ├── WorkingMemoryPage.tsx (NEW)
│   ├── LearningAnalyticsPage.tsx (NEW)
│   ├── SystemHealthPage.tsx (NEW)
│   ├── ResearchConsolePage.tsx (Enhanced)
│   ├── AnalyticsPage.tsx (NEW)
│   └── SettingsPage.tsx (NEW)
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx (NEW - navigation)
│   │   ├── Header.tsx (NEW - top bar)
│   │   └── MainLayout.tsx (NEW - wrapper)
│   │
│   ├── charts/
│   │   ├── TimeSeriesChart.tsx (NEW)
│   │   ├── BarChart.tsx (NEW)
│   │   ├── PieChart.tsx (NEW)
│   │   ├── HeatMap.tsx (NEW)
│   │   ├── GraphVisualization.tsx (NEW - d3.js)
│   │   └── GaugeChart.tsx (NEW)
│   │
│   ├── common/
│   │   ├── Stat.tsx (NEW - metric display)
│   │   ├── Card.tsx (NEW - container)
│   │   ├── SearchBar.tsx (NEW)
│   │   ├── DateRange.tsx (NEW)
│   │   ├── Filter.tsx (NEW)
│   │   └── Pagination.tsx (NEW)
│   │
│   ├── memory/
│   │   ├── EpisodicTimeline.tsx (NEW)
│   │   ├── SemanticSearch.tsx (NEW)
│   │   ├── ProceduresList.tsx (NEW)
│   │   ├── TaskBoard.tsx (NEW)
│   │   └── MetricsGrid.tsx (NEW)
│   │
│   └── research/
│       ├── StreamingResearch.tsx (Existing)
│       ├── AgentProgress.tsx (Existing)
│       └── MemoryHealth.tsx (Existing)
│
├── hooks/
│   ├── useWebSocket.ts (Existing)
│   ├── useAPI.ts (NEW - data fetching)
│   ├── useChart.ts (NEW - chart rendering)
│   └── useLocalStorage.ts (NEW - dashboard state)
│
└── types/
    ├── streaming.ts (Existing)
    ├── memory.ts (NEW - all layer types)
    ├── metrics.ts (NEW - system metrics)
    └── api.ts (NEW - API response types)
```

---

## Implementation Strategy

### Phase 1: Infrastructure (2 days)
1. Expand backend with new API endpoints
2. Create database queries for all layers
3. Set up caching for expensive queries
4. Add data aggregation pipelines

### Phase 2: Core Visualizations (2-3 days)
1. Build charting components (using Chart.js or Recharts)
2. Create layout components (sidebar, header)
3. Implement page navigation
4. Build common UI components

### Phase 3: Memory Layer Pages (3-4 days)
1. Episodic memory page + timeline
2. Semantic memory search
3. Procedural skills library
4. Task/goal management
5. Knowledge graph visualization

### Phase 4: System Monitoring (2 days)
1. Hook execution monitor
2. Working memory status
3. System health dashboard
4. Performance metrics

### Phase 5: Analytics & Polish (2 days)
1. Learning analytics dashboard
2. Research console enhancement
3. Settings/configuration page
4. Dashboard customization

---

## Key Technology Decisions

### Charting Library
- **Recharts** (built-in React, responsive, easy)
- OR **Chart.js** (more powerful, wider use)
- OR **Plotly.js** (scientific, high-quality)

### Graph Visualization
- **D3.js** (powerful but steep learning curve)
- OR **Cytoscape.js** (specialized for graphs)
- OR **Vis.js** (good balance)
- OR **Force-Graph** (3D support)

### Data Fetching
- Custom `useAPI` hook (with caching)
- OR React Query (industry standard)
- OR SWR (lightweight)

### State Management
- Local component state (keep it simple)
- Context API (for theme/user prefs)
- OR Zustand (lightweight store)

### Real-Time Updates
- Polling (simple, works for dashboards)
- WebSocket (like research console)
- Server-Sent Events (SSE)

---

## User Experience Enhancements

### Navigation
- Sidebar with expandable sections
- Breadcrumb navigation
- Quick access menu
- Search functionality

### Filtering & Sorting
- Multi-select filters
- Date range pickers
- Custom sort options
- Saved filter presets

### Data Export
- CSV/JSON export
- PDF reports
- Data archiving
- Share/embed options

### Customization
- Drag-drop widget arrangement
- Custom metric selection
- Alert configuration
- Theme preferences

### Performance
- Lazy loading for pages
- Data virtualization for large lists
- Image optimization
- Caching strategies

---

## Success Criteria

- ✅ All 8 memory layers visible in dashboard
- ✅ Real-time updates for critical metrics
- ✅ Sub-500ms page load times
- ✅ Responsive on mobile/tablet/desktop
- ✅ No TypeScript errors
- ✅ Full test coverage for critical paths
- ✅ Accessibility (WCAG 2.1 AA)
- ✅ Comprehensive documentation

---

## Estimated Timeline

| Phase | Tasks | Days |
|-------|-------|------|
| 1 | Backend APIs, caching | 2 |
| 2 | Components, layout, navigation | 2-3 |
| 3 | Memory layer pages | 3-4 |
| 4 | System monitoring | 2 |
| 5 | Analytics, polish | 2 |
| **Total** | | **11-14 days** |

Or accelerated: **5-7 days** with focused scope

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Complex queries slow backend | High | Implement caching, query optimization |
| Large graphs hard to visualize | Medium | Lazy load, aggregation, filtering |
| Frontend becomes bloated | Medium | Code splitting, lazy routes |
| Scope creep | High | Define MVP, prioritize features |
| Performance degradation | High | Benchmarking, profiling early |

---

## MVP Scope (5-7 days)

If we need to move faster, focus on:
1. ✅ Overview page (all layers at a glance)
2. ✅ Episodic memory timeline
3. ✅ Consolidation progress
4. ✅ System health dashboard
5. ✅ Hook execution monitor
6. ✅ Working memory status
7. ✅ Enhanced research console
8. ⏭️ (Later) Semantic search, graph viz, analytics

---

## Next Steps

1. **Choose charting library** (Recharts recommended)
2. **Design API endpoints** (start with /api/system/health)
3. **Create data models** (TypeScript types)
4. **Build backend queries** (database layer)
5. **Create layout components** (sidebar, header)
6. **Implement pages systematically** (one at a time)

---

**Ready to start? Let me know:**
- Full expansion or MVP focus?
- Which memory layer to prioritize?
- Charting library preference?

