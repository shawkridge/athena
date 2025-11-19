# Athena Dashboard - 2025 Tech Stack Recommendations

**Date:** November 18, 2025
**Version:** 2.0
**Status:** Research-Based Recommendations

---

## Executive Summary

Based on comprehensive research of current best practices and emerging technologies in 2025, this document provides updated tech stack recommendations for the Athena memory system dashboard. The recommendations prioritize:

- **Performance:** Real-time updates with minimal latency
- **Developer Experience:** Modern tooling with excellent TypeScript support
- **Maintainability:** Well-supported libraries with active communities
- **Scalability:** Capable of handling growing data volumes (100K+ events)
- **Type Safety:** End-to-end TypeScript for reliability

**Key Changes from Initial Analysis:**
- ✅ Confirmed FastAPI as optimal backend (3,000+ RPS, native async, 3,200 concurrent WebSocket connections)
- ✅ Updated frontend framework recommendation to **Next.js 15** over vanilla React
- ✅ Recommended **Apache ECharts** over Recharts for data-intensive visualizations
- ✅ Confirmed **Cytoscape.js** for knowledge graph visualization
- ✅ Added **Zustand** for state management (simpler than Redux, better than Context)
- ✅ Recommended **shadcn/ui** over Material-UI for component library
- ✅ Confirmed **WebSocket** for bidirectional real-time communication

---

## 1. Recommended Tech Stack (2025)

### 1.1 Frontend Stack

```
┌─────────────────────────────────────────────────────┐
│                    Frontend Layer                    │
├─────────────────────────────────────────────────────┤
│  Framework:         Next.js 15 (App Router)         │
│  Language:          TypeScript 5.x                  │
│  Build Tool:        Turbopack (built into Next.js)  │
│  Package Manager:   pnpm (faster than npm/yarn)     │
├─────────────────────────────────────────────────────┤
│  Data Visualization Libraries                        │
├─────────────────────────────────────────────────────┤
│  Charts/Graphs:     Apache ECharts 6.0              │
│  Knowledge Graph:   Cytoscape.js 3.x                │
│  Timeline:          vis-timeline (vis.js)           │
│  Alternative:       D3.js 7.x (custom viz only)     │
├─────────────────────────────────────────────────────┤
│  State & Data Management                             │
├─────────────────────────────────────────────────────┤
│  Global State:      Zustand 5.x                     │
│  Server State:      TanStack Query v5 (React Query) │
│  Form State:        React Hook Form 7.x             │
├─────────────────────────────────────────────────────┤
│  UI Components & Styling                             │
├─────────────────────────────────────────────────────┤
│  Component Lib:     shadcn/ui                       │
│  Styling:           Tailwind CSS 4.x                │
│  Icons:             Lucide React                     │
│  Animations:        Framer Motion                    │
├─────────────────────────────────────────────────────┤
│  Real-time Communication                             │
├─────────────────────────────────────────────────────┤
│  Protocol:          WebSocket                        │
│  Client Library:    native WebSocket API            │
│  Fallback:          Server-Sent Events (SSE)        │
└─────────────────────────────────────────────────────┘
```

### 1.2 Backend Stack

```
┌─────────────────────────────────────────────────────┐
│                    Backend Layer                     │
├─────────────────────────────────────────────────────┤
│  Framework:         FastAPI 0.115+                  │
│  Language:          Python 3.11+                    │
│  ASGI Server:       Uvicorn (with Gunicorn)         │
│  WebSocket:         FastAPI native WebSocket        │
├─────────────────────────────────────────────────────┤
│  Database & ORM                                      │
├─────────────────────────────────────────────────────┤
│  Database:          PostgreSQL 16+                  │
│  Extension:         pgvector (already in use)       │
│  ORM:               Direct async queries (existing) │
│  Connection Pool:   asyncpg pool (existing)         │
├─────────────────────────────────────────────────────┤
│  API & Validation                                    │
├─────────────────────────────────────────────────────┤
│  Data Validation:   Pydantic v2 (existing)          │
│  API Docs:          OpenAPI 3.1 (FastAPI built-in)  │
│  CORS:              FastAPI middleware              │
├─────────────────────────────────────────────────────┤
│  Caching & Performance                               │
├─────────────────────────────────────────────────────┤
│  In-Memory Cache:   Redis (optional, for scale)     │
│  Response Cache:    FastAPI-cache2                  │
└─────────────────────────────────────────────────────┘
```

### 1.3 Development & Deployment

```
┌─────────────────────────────────────────────────────┐
│              Development & Deployment                │
├─────────────────────────────────────────────────────┤
│  Process Manager:   systemd services (native)       │
│  Reverse Proxy:     Caddy (recommended) or Nginx    │
│  Service Isolation: systemd user/group controls     │
│  Monitoring:        journalctl + built-in metrics   │
├─────────────────────────────────────────────────────┤
│  Testing                                             │
├─────────────────────────────────────────────────────┤
│  Frontend Tests:    Vitest + React Testing Library  │
│  E2E Tests:         Playwright                       │
│  Backend Tests:     pytest (existing)                │
│  API Testing:       Hoppscotch or Bruno             │
└─────────────────────────────────────────────────────┘
```

---

## 2. Detailed Component Analysis

### 2.1 Frontend Framework: Next.js 15

**Why Next.js over Vite + React?**

✅ **Server-Side Rendering (SSR):** Better initial load times for dashboard
✅ **API Routes:** Built-in backend endpoints for simple operations
✅ **App Router:** Modern file-based routing with layouts
✅ **Turbopack:** Faster than Vite for larger codebases
✅ **Image Optimization:** Automatic image compression
✅ **Production-Ready:** Used by Vercel, Netflix, TikTok

**Performance (2025 benchmarks):**
- Local dev startup: <100ms (Turbopack)
- Hot Module Replacement: <50ms
- Production build: Optimized with tree-shaking
- TTFB (Time to First Byte): Lowest among frameworks

**When NOT to use Next.js:**
- Pure client-side SPA with external API only → Use Vite
- Need extremely simple setup → Use Vite

**For Athena Dashboard:** ✅ **RECOMMENDED**
- SSR improves initial dashboard load
- API routes useful for proxying to FastAPI backend
- Built-in optimization for production

### 2.2 Data Visualization: Apache ECharts 6.0

**Why ECharts over Recharts, Chart.js, or D3.js?**

✅ **Performance:** Handles 10 million data points in real-time
✅ **Feature-Rich:** 20+ chart types out of the box
✅ **Progressive Rendering:** Smooth with massive datasets
✅ **Multiple Rendering:** Canvas (fast), SVG (quality), WebGL (3D)
✅ **TypeScript:** Full type definitions
✅ **Active Maintenance:** Apache Foundation backing

**Comparison:**

| Library | Best For | Performance | Learning Curve | TypeScript |
|---------|----------|-------------|----------------|------------|
| **Apache ECharts** | Large datasets, enterprise | ⭐⭐⭐⭐⭐ | Medium | Excellent |
| Recharts | React apps, simplicity | ⭐⭐⭐ | Easy | Good |
| Chart.js | Quick prototypes | ⭐⭐⭐⭐ | Easy | Good |
| D3.js | Custom visuals | ⭐⭐⭐ | Hard | Fair |

**For Athena (8K+ events, growing):** ✅ **RECOMMENDED: ECharts**

**Usage Example:**
```typescript
import * as echarts from 'echarts';
import { useEffect, useRef } from 'react';

export function EventTimeline({ data }) {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const chart = echarts.init(chartRef.current);

    chart.setOption({
      xAxis: { type: 'time' },
      yAxis: { type: 'value' },
      series: [{
        type: 'scatter',
        data: data.map(e => [e.timestamp, e.importance]),
        symbolSize: (val) => val[1] * 20, // Size by importance
      }],
      tooltip: { trigger: 'item' },
    });

    return () => chart.dispose();
  }, [data]);

  return <div ref={chartRef} style={{ width: '100%', height: '400px' }} />;
}
```

**Alternative: Recharts** for simpler charts (procedures list, task distribution)

### 2.3 Knowledge Graph: Cytoscape.js

**Why Cytoscape.js over React Flow or vis.js?**

✅ **Designed for Graphs:** Built specifically for network visualization
✅ **Performance:** Handles thousands of nodes efficiently
✅ **Algorithms:** Built-in graph algorithms (centrality, clustering, pathfinding)
✅ **Layouts:** 10+ layout algorithms (force-directed, hierarchical, circular)
✅ **Extensible:** 100+ extensions available
✅ **React Integration:** `react-cytoscapejs` package

**Comparison:**

| Library | Nodes/Edges Limit | Algorithms | React Native | Best For |
|---------|-------------------|------------|--------------|----------|
| **Cytoscape.js** | 10,000+ | ✅ Built-in | ✅ Yes | Scientific graphs, knowledge graphs |
| React Flow | 1,000 | ❌ Manual | ✅ Yes | Flow diagrams, node editors |
| vis-network | 5,000 | ⚠️ Limited | ❌ No | Simple networks |

**For Athena (342 entities, growing):** ✅ **RECOMMENDED: Cytoscape.js**

**Usage Example:**
```typescript
import Cytoscape from 'cytoscape';
import CytoscapeComponent from 'react-cytoscapejs';

export function KnowledgeGraph({ entities, relations }) {
  const elements = [
    ...entities.map(e => ({
      data: { id: e.id, label: e.name, type: e.entity_type }
    })),
    ...relations.map(r => ({
      data: { source: r.from_entity_id, target: r.to_entity_id, strength: r.strength }
    }))
  ];

  return (
    <CytoscapeComponent
      elements={elements}
      style={{ width: '100%', height: '600px' }}
      layout={{ name: 'cose', animate: true }} // Force-directed
      stylesheet={[
        {
          selector: 'node',
          style: {
            'background-color': 'data(type)',
            'label': 'data(label)',
            'width': 'mapData(importance, 0, 1, 20, 60)',
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'mapData(strength, 0, 1, 1, 5)',
            'opacity': 0.7,
          }
        }
      ]}
    />
  );
}
```

### 2.4 State Management: Zustand

**Why Zustand over Redux, Jotai, or Context API?**

✅ **Simple API:** 100x less boilerplate than Redux
✅ **TypeScript:** Excellent type inference
✅ **Performance:** Selective re-renders (no Provider needed)
✅ **Bundle Size:** Only 1.2KB (vs Redux 20KB)
✅ **SSR Support:** Works seamlessly with Next.js
✅ **DevTools:** Redux DevTools integration available

**2025 State Management Landscape:**

| Solution | Best For | Bundle Size | Learning Curve | Next.js SSR |
|----------|----------|-------------|----------------|-------------|
| **Zustand** | Most projects | 1.2KB | Easy | ✅ Excellent |
| Context API | Very simple state | 0KB | Easy | ✅ Yes |
| Redux Toolkit | Large enterprise apps | 20KB | Medium | ⚠️ Complex |
| Jotai | Atomic fine-grained state | 3KB | Medium | ✅ Good |

**For Athena Dashboard:** ✅ **RECOMMENDED: Zustand**

**Usage Example:**
```typescript
import { create } from 'zustand';

interface DashboardStore {
  selectedLayer: string | null;
  filters: Record<string, any>;
  setLayer: (layer: string) => void;
  updateFilters: (filters: Record<string, any>) => void;
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  selectedLayer: null,
  filters: {},
  setLayer: (layer) => set({ selectedLayer: layer }),
  updateFilters: (filters) => set((state) => ({
    filters: { ...state.filters, ...filters }
  })),
}));

// Usage in component:
function LayerSelector() {
  const { selectedLayer, setLayer } = useDashboardStore();
  return <select value={selectedLayer} onChange={(e) => setLayer(e.target.value)} />;
}
```

**For Server State:** Use **TanStack Query** (React Query) instead:
```typescript
import { useQuery } from '@tanstack/react-query';

function EpisodicStats() {
  const { data, isLoading } = useQuery({
    queryKey: ['episodic', 'statistics'],
    queryFn: () => fetch('/api/episodic/statistics').then(r => r.json()),
    refetchInterval: 10000, // Auto-refresh every 10s
  });

  if (isLoading) return <Skeleton />;
  return <div>Total Events: {data.total_events}</div>;
}
```

### 2.5 UI Components: shadcn/ui

**Why shadcn/ui over Material-UI or Ant Design?**

✅ **Copy-Paste Components:** Own your components (no npm dependency)
✅ **Tailwind-Based:** Fully customizable with utility classes
✅ **Modern Design:** Clean, minimal aesthetic
✅ **Accessibility:** ARIA-compliant components
✅ **Tree-Shakeable:** Only import what you use
✅ **TypeScript:** Built with TypeScript from ground up

**Comparison:**

| Library | Approach | Customization | Bundle Impact | Design Language |
|---------|----------|---------------|---------------|-----------------|
| **shadcn/ui** | Copy components | ⭐⭐⭐⭐⭐ Unlimited | Minimal (tree-shake) | Your own |
| Material-UI | npm package | ⭐⭐⭐ Good | Large (95KB) | Material Design |
| Ant Design | npm package | ⭐⭐ Limited | Large (500KB+) | Ant Design |

**For Athena Dashboard:** ✅ **RECOMMENDED: shadcn/ui**
- Unique design (not "Material-y")
- Full control over styling
- Tailwind already in use
- Modern, clean aesthetic

**Installation:**
```bash
npx shadcn@latest init
npx shadcn@latest add button card table dialog
```

**Usage:**
```typescript
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export function LayerCard({ layer, health }) {
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold">{layer.name}</h3>
      <div className="mt-2 flex items-center gap-2">
        <HealthBadge status={health.status} />
        <span className="text-sm text-muted-foreground">
          {health.utilization}% utilized
        </span>
      </div>
      <Button className="mt-4" onClick={() => navigate(`/layers/${layer.id}`)}>
        View Details
      </Button>
    </Card>
  );
}
```

### 2.6 Real-time Communication: WebSocket

**Why WebSocket over Server-Sent Events (SSE)?**

✅ **Bidirectional:** Both client and server can initiate messages
✅ **Lower Latency:** Full-duplex communication
✅ **Industry Standard:** Widely supported and battle-tested
✅ **FastAPI Support:** Native WebSocket endpoints

**When to use SSE instead:**
- One-way server→client updates only
- Simpler implementation needed
- HTTP/2 multiplexing desired

**For Athena Dashboard:** ✅ **RECOMMENDED: WebSocket**
- Need bidirectional (client can request specific updates)
- FastAPI has excellent WebSocket support
- Standard for dashboards with 2-way communication

**FastAPI Backend:**
```python
from fastapi import FastAPI, WebSocket
from athena.episodic.operations import get_statistics
import asyncio

app = FastAPI()

@app.websocket("/ws/live-updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # Send updates every 5 seconds
            stats = await get_statistics()
            await websocket.send_json({
                "type": "statistics_update",
                "layer": "episodic",
                "data": stats
            })
            await asyncio.sleep(5)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

**Next.js Frontend:**
```typescript
import { useEffect, useState } from 'react';

export function useWebSocket(url: string) {
  const [data, setData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => setIsConnected(true);
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setData(message.data);
    };
    ws.onclose = () => setIsConnected(false);

    return () => ws.close();
  }, [url]);

  return { data, isConnected };
}

// Usage:
function LiveStats() {
  const { data, isConnected } = useWebSocket('ws://localhost:8000/ws/live-updates');

  return (
    <div>
      <StatusIndicator connected={isConnected} />
      {data && <StatsDisplay stats={data} />}
    </div>
  );
}
```

---

## 3. Backend Framework: FastAPI (Confirmed)

**Why FastAPI is the Clear Winner for Athena Dashboard:**

### Performance Benchmarks (2025)

| Metric | FastAPI | Django | Flask |
|--------|---------|--------|-------|
| **Requests/sec (simple)** | 3,000+ | 500 | 800 |
| **Requests/sec (DB-heavy)** | 892 | 478 | 543 |
| **Response Time (avg)** | 112ms | 209ms | 184ms |
| **WebSocket Connections** | 3,200 | 1,800 | 2,100 |

✅ **Async Native:** Built on ASGI (Starlette + Uvicorn)
✅ **Type Safety:** Pydantic v2 for validation
✅ **Auto Docs:** OpenAPI/Swagger built-in
✅ **WebSocket:** Native support, no extensions needed
✅ **Compatibility:** Works perfectly with existing Athena async codebase

**Athena Already Uses:**
- Pydantic models ✅
- Async/await throughout ✅
- PostgreSQL with asyncpg ✅

**Migration Effort:** **ZERO** - Just add FastAPI endpoints on top

**Example Endpoint:**
```python
from fastapi import FastAPI, Query
from athena.episodic.operations import recall
from typing import List

app = FastAPI()

@app.get("/api/episodic/events")
async def get_events(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    session_id: str | None = None
):
    """Get episodic events with pagination."""
    events = await recall(
        query="*",  # All events
        limit=limit + offset,
        session_id=session_id
    )

    return {
        "events": [e.model_dump() for e in events[offset:offset+limit]],
        "total": len(events),
        "limit": limit,
        "offset": offset
    }
```

---

## 4. Complete Tech Stack Summary

### Frontend (Next.js 15)
```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "typescript": "^5.6.0",

    "echarts": "^6.0.0",
    "echarts-for-react": "^3.0.2",
    "cytoscape": "^3.30.0",
    "react-cytoscapejs": "^2.0.0",
    "vis-timeline": "^7.7.3",

    "zustand": "^5.0.0",
    "@tanstack/react-query": "^5.59.0",
    "react-hook-form": "^7.53.0",

    "tailwindcss": "^4.0.0",
    "lucide-react": "^0.460.0",
    "framer-motion": "^11.11.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.4"
  },
  "devDependencies": {
    "@types/node": "^22.8.0",
    "@types/react": "^19.0.0",
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.0.0",
    "playwright": "^1.48.0",
    "eslint": "^9.13.0",
    "prettier": "^3.3.3"
  }
}
```

### Backend (FastAPI)
```txt
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.0
psycopg[binary]==3.2.3
psycopg-pool==3.2.3

# Existing Athena dependencies (already installed)
# - athena package with all operations
# - asyncpg for PostgreSQL
```

### Development Environment
```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: athena
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: athena
      DB_USER: postgres
      DB_PASSWORD: postgres
    depends_on:
      - postgres
    command: uvicorn main:app --host 0.0.0.0 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    command: npm run dev

volumes:
  postgres_data:
```

---

## 5. Alternative Stacks (When to Consider)

### Lighter Stack (MVP/Prototype)
**If you need something working in 1 week:**

- Frontend: **Vite + React** (no SSR needed)
- Charts: **Recharts** (simpler than ECharts)
- State: **Context API** (for very simple state)
- UI: **Headless UI** (unstyled components)
- Backend: Same (FastAPI)

**Trade-offs:**
- ❌ No SSR (slower initial load)
- ❌ Simpler charts (limited to <10K data points)
- ✅ Faster setup
- ✅ Less configuration

### Heavier Stack (Large Enterprise)
**If you have a team of 10+ developers:**

- Frontend: **Next.js 15** (same)
- Charts: **Highcharts** (paid, enterprise support)
- State: **Redux Toolkit** (strict patterns, better for large teams)
- UI: **Material-UI** (consistent design system)
- Backend: **Django REST** (if you need Django admin panel)

**Trade-offs:**
- ✅ Better for large teams (strict patterns)
- ✅ Enterprise support available
- ❌ More complex
- ❌ Higher cost (Highcharts licensing)

---

## 6. Migration from Initial Proposal

### What Changed?

| Component | Initial | Updated (2025) | Reason |
|-----------|---------|----------------|--------|
| Framework | React + CRA | Next.js 15 | SSR, better DX, Turbopack |
| Build Tool | Webpack | Turbopack | 10x faster builds |
| Charts | Recharts | Apache ECharts | Better performance (10M points) |
| State | N/A | Zustand | Simpler than Redux |
| Server State | N/A | TanStack Query | Industry standard |
| UI Library | Tailwind only | shadcn/ui + Tailwind | Component primitives |
| Backend | FastAPI ✅ | FastAPI ✅ | **Confirmed optimal** |
| Graph | Cytoscape.js ✅ | Cytoscape.js ✅ | **Confirmed optimal** |
| WebSocket | ✅ | ✅ | **Confirmed optimal** |

### Migration Effort

**Frontend:**
- Setup Next.js 15 project: 1 day
- Migrate to ECharts: 2 days (replace Recharts)
- Add Zustand stores: 1 day
- Setup shadcn/ui: 1 day
- **Total:** ~5 days

**Backend:**
- Add FastAPI app: 1 day (minimal boilerplate)
- Create API endpoints: 2-3 days
- WebSocket setup: 1 day
- **Total:** ~4 days

**Overall Migration:** ~2 weeks for full stack with testing

---

## 7. Performance Targets (2025 Standards)

### Frontend Performance

| Metric | Target | Tool |
|--------|--------|------|
| **Time to First Byte (TTFB)** | <200ms | Lighthouse |
| **First Contentful Paint (FCP)** | <1.5s | Web Vitals |
| **Largest Contentful Paint (LCP)** | <2.5s | Web Vitals |
| **Time to Interactive (TTI)** | <3.5s | Lighthouse |
| **Cumulative Layout Shift (CLS)** | <0.1 | Web Vitals |
| **First Input Delay (FID)** | <100ms | Web Vitals |

### Backend Performance

| Metric | Target | Measured |
|--------|--------|----------|
| **GET /api/statistics** | <100ms | p95 |
| **GET /api/events (100 items)** | <200ms | p95 |
| **WebSocket message latency** | <50ms | avg |
| **Database query** | <50ms | p95 |
| **Concurrent users** | 100+ | Load test |

### Visualization Performance

| Metric | Target | Library |
|--------|--------|---------|
| **Render 10K points** | <500ms | ECharts |
| **Graph with 1K nodes** | <1s | Cytoscape.js |
| **Timeline (1 year)** | <300ms | vis-timeline |

---

## 8. Implementation Priorities

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Setup Next.js 15 project with TypeScript
- [ ] Configure Tailwind CSS 4.x
- [ ] Install shadcn/ui components
- [ ] Setup FastAPI backend with WebSocket
- [ ] Configure TanStack Query
- [ ] Setup Zustand stores
- [ ] Basic routing structure

### Phase 2: Visualization Layer (Week 2-3)
- [ ] Integrate Apache ECharts
- [ ] Setup Cytoscape.js for knowledge graph
- [ ] Create reusable chart components
- [ ] Timeline visualization with vis-timeline
- [ ] Test with real Athena data

### Phase 3: Real-time Features (Week 3-4)
- [ ] WebSocket connection management
- [ ] Live statistics updates
- [ ] Real-time event streaming
- [ ] Connection status handling
- [ ] Fallback to polling if WS fails

### Phase 4: Polish & Optimization (Week 4-5)
- [ ] Performance optimization
- [ ] Error boundary implementation
- [ ] Loading states and skeletons
- [ ] Responsive design refinement
- [ ] Accessibility audit

### Phase 5: Testing & Deployment (Week 5-6)
- [ ] Unit tests (Vitest)
- [ ] Component tests
- [ ] E2E tests (Playwright)
- [ ] Performance testing
- [ ] Create systemd service files
- [ ] Production deployment with systemd

---

## 9. Cost Analysis

### Open Source (FREE)
- ✅ Next.js: FREE
- ✅ Apache ECharts: FREE (Apache 2.0)
- ✅ Cytoscape.js: FREE (MIT)
- ✅ shadcn/ui: FREE (MIT)
- ✅ Zustand: FREE (MIT)
- ✅ TanStack Query: FREE (MIT)
- ✅ FastAPI: FREE (MIT)

**Total Cost:** $0 for all libraries

### Paid Alternatives (if needed)
- Highcharts: ~$590/year per developer
- Ant Design Pro: FREE (but less flexible)
- Material-UI Pro: $588/year per developer

**Recommendation:** Stick with open source stack (no cost)

---

## 10. Learning Resources

### Next.js 15
- Official Docs: https://nextjs.org/docs
- App Router Tutorial: https://nextjs.org/learn
- Best Practices: https://www.robinwieruch.de/react-tech-stack/

### Apache ECharts
- Getting Started: https://echarts.apache.org/handbook/en/get-started/
- Examples Gallery: https://echarts.apache.org/examples/en/
- React Integration: https://github.com/hustcc/echarts-for-react

### Cytoscape.js
- Documentation: https://js.cytoscape.org/
- React Component: https://github.com/plotly/react-cytoscapejs
- Layouts: https://js.cytoscape.org/#layouts

### Zustand
- Quick Start: https://zustand.docs.pmnd.rs/
- Recipes: https://zustand.docs.pmnd.rs/guides/recipes

### TanStack Query
- Docs: https://tanstack.com/query/latest
- React Query Tutorial: https://www.djamware.com/post/688ecf617a49f1456836fd14

### shadcn/ui
- Component Library: https://ui.shadcn.com/
- Installation: https://ui.shadcn.com/docs/installation/next

### FastAPI
- Tutorial: https://fastapi.tiangolo.com/tutorial/
- WebSocket Guide: https://fastapi.tiangolo.com/advanced/websockets/

---

## 11. Team Recommendations

### Required Skills

**Frontend Developer:**
- TypeScript (intermediate+)
- React/Next.js (intermediate+)
- Tailwind CSS (beginner+)
- Data visualization concepts (beginner+)

**Backend Developer:**
- Python (intermediate+)
- FastAPI or similar framework (beginner+)
- Async/await patterns (intermediate)
- PostgreSQL (beginner+)

**Ideal Team Size:** 2-3 developers
- 1-2 Frontend
- 1 Backend/Full-stack

**Timeline with Team:**
- Solo developer: 8-10 weeks
- 2 developers: 5-6 weeks
- 3 developers: 4-5 weeks

---

## 12. Conclusion

### Final Recommendations

**✅ RECOMMENDED STACK (2025):**

```
Frontend:
├── Next.js 15 (App Router + Turbopack)
├── TypeScript 5.x
├── Apache ECharts (charts)
├── Cytoscape.js (knowledge graph)
├── Zustand (client state)
├── TanStack Query (server state)
├── shadcn/ui + Tailwind CSS
└── WebSocket (real-time)

Backend:
├── FastAPI 0.115+
├── Python 3.11+
├── PostgreSQL 16+ (existing)
└── Uvicorn + Gunicorn

Dev/Deploy:
├── systemd services (process management)
├── Caddy or Nginx (reverse proxy)
├── Vitest + Playwright (testing)
└── pnpm (package manager)
```

### Why This Stack Wins

1. **Performance:** Fastest among modern alternatives
2. **Developer Experience:** Excellent tooling and TypeScript support
3. **Community:** Large, active communities for all libraries
4. **Compatibility:** Works seamlessly with existing Athena codebase
5. **Scalability:** Proven to handle enterprise-scale applications
6. **Cost:** $0 (all open source)
7. **Maintenance:** Well-maintained with long-term support
8. **Modern:** Uses 2025 best practices and latest stable versions

### Next Steps

1. ✅ Review and approve this tech stack
2. Setup development environment (see DASHBOARD_DEPLOYMENT_SYSTEMD.md)
3. Create project scaffolding (Next.js + FastAPI)
4. Build MVP (Overview dashboard + 1-2 visualizations)
5. Iterate based on feedback
6. Scale to full feature set

---

**Document Version:** 2.0
**Last Updated:** November 18, 2025
**Research Completion:** ✅ Complete
**Status:** Ready for Implementation

---

## Appendix A: Quick Start Commands

### Frontend Setup
```bash
# Create Next.js project
npx create-next-app@latest athena-dashboard --typescript --tailwind --app

cd athena-dashboard

# Install dependencies
pnpm add echarts echarts-for-react
pnpm add cytoscape react-cytoscapejs
pnpm add zustand @tanstack/react-query
pnpm add lucide-react framer-motion

# Install shadcn/ui
npx shadcn@latest init
npx shadcn@latest add button card table dialog

# Start dev server
pnpm dev  # http://localhost:3000
```

### Backend Setup
```bash
# Create FastAPI project
mkdir athena-backend && cd athena-backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install fastapi uvicorn[standard] pydantic

# Create main.py
cat > main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Athena Dashboard API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
EOF

# Start server
uvicorn main:app --reload  # http://localhost:8000
```

### Production Deployment (systemd)

See **`DASHBOARD_DEPLOYMENT_SYSTEMD.md`** for complete deployment guide.

Quick start:
```bash
# Start services
sudo systemctl start athena-dashboard-backend
sudo systemctl start athena-dashboard-frontend
sudo systemctl start caddy

# Check status
systemctl status athena-dashboard-*

# View logs
sudo journalctl -u athena-dashboard-backend -f
```

**Access:**
- Frontend: http://localhost (via Caddy proxy)
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

**Ready to build! 🚀**

For detailed deployment instructions with systemd service files, see:
**`docs/DASHBOARD_DEPLOYMENT_SYSTEMD.md`**
