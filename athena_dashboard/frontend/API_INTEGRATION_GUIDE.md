# Athena Dashboard - API Integration Guide

## Overview

This guide explains how to connect the frontend dashboard pages to your Athena backend API. All pages use the `useAPI` hook for data fetching with built-in loading and error handling.

## Quick Start

### API Base URL

The API base URL is configured in `vite.config.ts`:

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

In production, update the `VITE_API_URL` environment variable.

## Data Flow Pattern

Every page follows this pattern:

```typescript
import { useAPI } from '@/hooks'

interface ResponseData {
  data: SomeType
  stats: StatsType
}

export const MyPage = () => {
  const { data, loading, error } = useAPI<ResponseData>('/api/endpoint')

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorMessage error={error} />

  return <div>{/* render data */}</div>
}
```

## API Endpoints Required

### Overview Page

**GET `/api/system/overview`**

Returns system health summary and key metrics.

```json
{
  "totalEvents": 8128,
  "totalMemories": 5230,
  "qualityScore": 87.5,
  "avgQueryTime": 45.3,
  "successRate": 99.2,
  "errorCount": 3,
  "layers": [
    {
      "name": "Layer 1: Episodic",
      "health": 92,
      "itemCount": 8128
    }
  ]
}
```

---

### System Health Page

**GET `/api/system/health`**

Returns detailed health metrics for all memory layers.

```json
{
  "layers": [
    {
      "name": "Layer 1: Episodic",
      "health": 92,
      "status": "healthy",
      "itemCount": 8128,
      "queryTime": 45,
      "lastUpdated": "2025-11-15T10:30:00Z"
    }
  ],
  "metrics": [
    {
      "timestamp": "2025-11-15T10:00:00Z",
      "overallHealth": 88,
      "databaseSize": 128.5,
      "queryLatency": 50
    }
  ]
}
```

---

### Episodic Memory Page

**GET `/api/episodic/events?page={page}&search={query}&startDate={date}&endDate={date}`**

Returns paginated episodic events with filtering.

```json
{
  "events": [
    {
      "id": "evt_001",
      "timestamp": "2025-11-15T10:30:00Z",
      "type": "tool_execution",
      "description": "Executed tool: bash",
      "data": { "command": "ls -la" }
    }
  ],
  "total": 8128,
  "stats": {
    "totalEvents": 8128,
    "avgStorageSize": 2.5,
    "queryTimeMs": 45
  }
}
```

---

### Semantic Memory Page

**GET `/api/semantic/search?search={query}&domains={list}`**

Returns knowledge memories with quality metrics.

```json
{
  "memories": [
    {
      "id": "mem_001",
      "content": "Python is a programming language",
      "domain": "programming",
      "quality": 95,
      "lastAccessed": "2025-11-15T10:30:00Z"
    }
  ],
  "total": 5230,
  "stats": {
    "totalMemories": 5230,
    "avgQuality": 87.5,
    "domains": [
      { "name": "programming", "count": 2100 },
      { "name": "web", "count": 1500 }
    ]
  }
}
```

---

### Procedural Memory Page

**GET `/api/procedural/skills`**

Returns learned skills and their effectiveness.

```json
{
  "skills": [
    {
      "id": "skill_001",
      "name": "Web Scraping",
      "category": "data-collection",
      "effectiveness": 92,
      "executions": 156,
      "lastUsed": "2025-11-15T10:30:00Z"
    }
  ],
  "stats": {
    "totalSkills": 101,
    "avgEffectiveness": 87.5,
    "totalExecutions": 8920
  }
}
```

---

### Prospective Memory Page

**GET `/api/prospective/tasks`**

Returns current tasks and goals.

```json
{
  "tasks": [
    {
      "id": "task_001",
      "title": "Build dashboard",
      "status": "active",
      "priority": "high",
      "deadline": "2025-11-20T00:00:00Z"
    }
  ],
  "stats": {
    "total": 12,
    "completed": 8,
    "pending": 3,
    "overdue": 1
  }
}
```

---

### Knowledge Graph Page

**GET `/api/graph/stats`**

Returns knowledge graph statistics.

```json
{
  "stats": {
    "entities": 2500,
    "relationships": 8900,
    "communities": 45,
    "density": 0.34
  }
}
```

---

### Meta-Memory Page

**GET `/api/meta/quality`**

Returns quality metrics and expertise scores.

```json
{
  "quality": 87.5,
  "expertise": [
    { "domain": "programming", "score": 92 },
    { "domain": "data-science", "score": 78 }
  ],
  "attention": [
    { "layer": "Episodic", "allocation": 15 },
    { "layer": "Semantic", "allocation": 25 }
  ]
}
```

---

### Consolidation Page

**GET `/api/consolidation/analytics`**

Returns consolidation progress and statistics.

```json
{
  "currentProgress": 65,
  "lastRun": {
    "id": "run_001",
    "startTime": "2025-11-15T10:00:00Z",
    "endTime": "2025-11-15T10:05:00Z",
    "status": "completed",
    "duration": 300,
    "patternsFound": 156,
    "system1Time": 100,
    "system2Time": 200
  },
  "runs": [
    {
      "id": "run_001",
      "startTime": "2025-11-15T10:00:00Z",
      "endTime": "2025-11-15T10:05:00Z",
      "status": "completed",
      "duration": 300,
      "patternsFound": 156,
      "system1Time": 100,
      "system2Time": 200
    }
  ],
  "statistics": {
    "totalRuns": 42,
    "avgPatternsPerRun": 156,
    "successRate": 98.5,
    "totalPatterns": 6552
  },
  "patternDistribution": [
    { "name": "Temporal", "value": 2100 },
    { "name": "Semantic", "value": 1800 }
  ]
}
```

---

### Hook Execution Page

**GET `/api/hooks/status`**

Returns hook execution status and performance.

```json
{
  "hooks": [
    {
      "name": "SessionStart",
      "status": "active",
      "executions": 243,
      "avgLatency": 125.5,
      "successRate": 99.8
    }
  ],
  "metrics": [
    {
      "timestamp": "2025-11-15T10:30:00Z",
      "latency": 125,
      "successRate": 99.8
    }
  ]
}
```

---

### Working Memory Page

**GET `/api/working-memory/current`**

Returns current working memory items.

```json
{
  "items": [
    {
      "id": "item_001",
      "title": "Build dashboard",
      "age": "2m ago",
      "importance": 85
    }
  ],
  "cognitive": {
    "load": 6,
    "capacity": 9
  }
}
```

---

### RAG & Planning Page

**GET `/api/rag/metrics`**

Returns RAG and planning metrics.

```json
{
  "metrics": {
    "avgQueryTime": 150,
    "retrievalQuality": 92.5,
    "planValidationRate": 95,
    "verificationsPassed": 1245
  },
  "queryPerformance": [
    { "strategy": "HyDE", "avgTime": 120 },
    { "strategy": "BM25", "avgTime": 80 }
  ]
}
```

---

### Learning Analytics Page

**GET `/api/learning/analytics`**

Returns learning effectiveness metrics.

```json
{
  "stats": {
    "avgEffectiveness": 87.5,
    "strategiesLearned": 42,
    "gapResolutions": 156,
    "improvementTrend": 12
  },
  "learningCurve": [
    {
      "timestamp": "2025-11-15T10:00:00Z",
      "effectiveness": 75,
      "learningRate": 8.5
    }
  ]
}
```

---

## Error Handling

Every page automatically handles errors. If an API call fails, the page displays:

```
Something went wrong
[Error message from API]
```

To customize error messages, modify the error state in individual pages.

## Loading States

All pages show a loading spinner while fetching data. Customize by changing the loading UI:

```typescript
if (loading) {
  return <div className="animate-pulse space-y-4">...</div>
}
```

## Data Refresh

To refresh data after user actions, use the `refetch` function from useAPI:

```typescript
const { data, loading, error, refetch } = useAPI<ResponseData>('/api/endpoint')

const handleAction = async () => {
  await refetch()
}
```

## Pagination

Pages that need pagination pass `page` as a query parameter:

```typescript
const queryParams = new URLSearchParams({ page: page.toString() })
const { data } = useAPI(`/api/endpoint?${queryParams}`)
```

## Type Safety

Always define response interfaces for type safety:

```typescript
interface ApiResponse {
  data: SomeType
  stats: StatsType
  metadata?: MetadataType
}

const { data } = useAPI<ApiResponse>('/api/endpoint')
// TypeScript will ensure data matches ApiResponse structure
```

## Testing API Endpoints

Before implementing endpoints in the backend, test the expected structure:

1. **SwaggerUI**: http://localhost:8000/docs
2. **API Testing Tool**: Use Postman or curl
3. **Frontend**: Check network tab in DevTools

## Environment Variables

For production deployment, set:

```bash
VITE_API_URL=https://your-api-domain.com
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS errors | Configure CORS in FastAPI backend |
| 404 errors | Verify endpoint path matches API routes |
| Slow loading | Check API response time, implement caching |
| Type errors | Ensure response interface matches API data |

## Summary

- ✅ All 16 pages ready for API integration
- ✅ useAPI hook handles loading/errors automatically
- ✅ Type-safe data fetching with TypeScript
- ✅ Code splitting for performance
- ✅ Error boundaries for resilience

Connect these endpoints to your Athena backend and the dashboard is complete! 🚀
