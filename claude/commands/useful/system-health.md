---
description: Check system health and performance (filesystem API) - executes health checks locally, returns metrics summaries
argument-hint: "Optional: --detailed for full performance analysis"
---

# System Health (Filesystem API Edition)

Check overall system health, performance, and identify bottlenecks using filesystem API paradigm - discover operations, execute locally, return metric summaries.

Usage:
- `/system-health` - Quick health snapshot (summary metrics)
- `/system-health --detailed` - Detailed analysis with bottleneck investigation

## How It Works

### Step 1: Discover Health Operations
- List available health check operations
- Discover performance monitoring operations
- Progressive disclosure across layers

### Step 2: Execute Health Checks
All checks execute locally in sandbox:
- **Memory Performance**: Query timing, consolidation efficiency
- **Storage Health**: Database metrics, index efficiency
- **Execution Performance**: Task timing, automation reliability
- **System Capacity**: Cognitive load, resource utilization
- **Error Rates**: Failed operations, timeout patterns
- **Integration Health**: Tool responsiveness, agent effectiveness

### Step 3: Collect Metrics
- Aggregate performance data
- Calculate scores and trends
- Identify anomalies
- All processing happens locally

### Step 4: Return Summaries
Return only summary metrics (not full analysis data):
- Component scores, not component details
- Trend directions, not trend data
- Bottleneck IDs, not bottleneck content
- Recommendations, not detailed fixes

## Returns (Summary Only)

**Quick Mode** (`/system-health`):
```json
{
  "status": "success",
  "execution_method": "filesystem_api",
  "execution_time_ms": 142,
  "timestamp": "2025-11-12T10:30:00Z",

  "overall_health": 0.82,
  "health_status": "GOOD",

  "components": {
    "memory_operations": 0.90,
    "consolidation": 0.65,
    "task_execution": 0.85,
    "storage": 0.72,
    "error_handling": 0.88
  },

  "performance_summary": {
    "semantic_search_avg_ms": 85,
    "consolidation_cycle_s": 3.2,
    "task_startup_ms": 250,
    "p95_latency_ms": 450
  },

  "capacity": {
    "cognitive_load_usage_percent": 67,
    "storage_usage_percent": 75,
    "database_efficiency": 0.78
  },

  "trends": {
    "memory_ops": "stable",
    "consolidation": "degrading",
    "task_exec": "improving",
    "error_rate": "stable"
  },

  "critical_bottleneck_count": 3,

  "recommendations": [
    "Optimize consolidation LLM validation (est. 30% faster)",
    "Review episodic event clustering algorithm",
    "Cache graph community detection results"
  ]
}
```

**Detailed Mode** (`/system-health --detailed`):
- Full metric breakdown per layer
- Individual bottleneck analysis
- Optimization suggestions with cost/benefit
- Trend analysis over time
- Comparative performance metrics

## Monitors (Filesystem API Execution)

- **Memory Performance** (semantic layer)
  - Query speed tracking
  - Consolidation efficiency
  - Search latency p50, p95, p99

- **Storage Health** (core layer)
  - Database size trends
  - Index efficiency ratios
  - Fragmentation analysis

- **Execution Performance** (prospective layer)
  - Task timing metrics
  - Automation success rates
  - Timeout frequency

- **System Capacity** (meta layer)
  - Cognitive load usage
  - Resource utilization
  - Capacity headroom

- **Error Rates** (all layers)
  - Failed operations count
  - Timeout patterns
  - Error categorization

- **Integration Health** (cross-layer)
  - Tool responsiveness
  - Agent effectiveness
  - Latency by tool

## Token Efficiency

**Old Pattern**:
- Load detailed metrics: 150K tokens
- Return full analysis: 50K tokens
- Process in context: 15K tokens
- **Total: 215K+ tokens**

**New Pattern (Filesystem API)**:
- Discover health operations: 100 tokens
- Execute checks locally: 0 tokens (sandbox)
- Return summaries: 400 tokens
- **Total: <500 tokens**

**Savings: 99%+ token reduction** 🎯

## Implementation Notes

The system-monitor agent uses this by:
1. Discovering health check operations
2. Executing checks locally (all data stays in sandbox)
3. Analyzing summary metrics (scores, trends, recommendations)
4. If deep investigation needed, requesting detailed mode
5. Tracking trends over time using summary data

Daily health checks cost <500 tokens instead of 215K+, keeping your memory system efficient and responsive.
