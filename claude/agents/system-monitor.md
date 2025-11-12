---
name: system-monitor
description: |
  System monitoring using filesystem API paradigm (discover → analyze → detect → recommend).
  Tracks health across 6 dimensions: performance, storage, execution speed, capacity, errors, integration.
  Executes locally, returns summaries only (99%+ token reduction).
---

# System Monitor Agent (Filesystem API Edition)

Continuous system health tracking and performance monitoring with bottleneck detection and optimization recommendations.

## What This Agent Does

Monitors system health across 6 key dimensions (performance, storage, execution, capacity, errors, integration), detects bottlenecks and critical paths, and provides actionable optimization recommendations.

## When to Use

- Periodic health checks (every session)
- Performance degradation investigation
- Capacity planning
- Bottleneck identification
- Integration health verification
- Optimization opportunity discovery

## How It Works (Filesystem API Paradigm)

### Step 1: Discover
- Use `adapter.list_operations_in_layer("monitoring")`
- Discover available monitoring operations
- Show what health and performance metrics are available

### Step 2: Analyze Health
- Monitor 6 dimensions in parallel
- Performance metrics: query times, throughput
- Storage health: database size, fragmentation
- Execution speed: operation latencies
- Capacity: memory utilization, working memory load
- Error rates: failures, timeouts
- Integration: cross-layer coordination health

### Step 3: Detect Issues
- Identify bottlenecks and slow paths
- Compare against baselines and targets
- Flag capacity warnings
- Detect performance trends
- Identify integration issues

### Step 4: Return Summary
- Overall health score (0.0-1.0)
- Component breakdown with status
- Bottleneck analysis with impact scores
- Critical path visualization
- Optimization recommendations ranked by impact
- Trend analysis and predictions

## 6 Monitoring Dimensions

1. **Performance**: Query latency, search speed, throughput
2. **Storage**: Database size, compression efficiency, defragmentation
3. **Execution Speed**: Operation latencies, p95/p99 response times
4. **Capacity**: Memory utilization, working memory load, headroom
5. **Errors**: Failure rates, timeout rates, error categories
6. **Integration**: Cross-layer coordination, dependency health

## Returns (Summary Only)

```json
{
  "status": "success",
  "execution_method": "filesystem_api_parallel",
  "execution_time_ms": 412,

  "timestamp": "2025-11-12T10:15:45Z",

  "overall_health": {
    "score": 0.84,
    "status": "healthy",
    "trend": "stable",
    "recommendation": "No immediate action needed"
  },

  "component_health": {
    "performance": {
      "score": 0.88,
      "status": "healthy",
      "avg_latency_ms": 145,
      "p95_latency_ms": 287,
      "throughput_ops_per_sec": 45
    },
    "storage": {
      "score": 0.82,
      "status": "healthy",
      "database_size_mb": 285,
      "compression_ratio": 0.78,
      "fragmentation_percent": 12
    },
    "execution": {
      "score": 0.85,
      "status": "healthy",
      "slowest_operation": "consolidation",
      "slowest_latency_ms": 2450,
      "operations_monitored": 18
    },
    "capacity": {
      "score": 0.87,
      "status": "healthy",
      "memory_utilization_percent": 43,
      "working_memory_load": 3,
      "capacity_headroom": 4
    },
    "errors": {
      "score": 0.90,
      "status": "healthy",
      "failure_rate_percent": 0.3,
      "timeout_rate_percent": 0.1,
      "error_categories": 2
    },
    "integration": {
      "score": 0.79,
      "status": "caution",
      "cross_layer_calls": 342,
      "integration_failures": 1,
      "coordination_health": 0.99
    }
  },

  "bottlenecks": [
    {
      "id": "semantic_search_latency",
      "component": "Semantic Layer",
      "issue": "Search latency trending up",
      "current_latency_ms": 234,
      "baseline_latency_ms": 180,
      "impact_score": 0.75,
      "affected_operations": ["recall", "research"],
      "trend": "increasing"
    },
    {
      "id": "consolidation_speed",
      "component": "Consolidation Layer",
      "issue": "Consolidation running slow",
      "current_duration_ms": 2450,
      "baseline_duration_ms": 1800,
      "impact_score": 0.62,
      "affected_operations": ["consolidate"],
      "trend": "stable"
    }
  ],

  "critical_path_analysis": {
    "critical_path": ["Query Input", "Semantic Search", "Consolidation", "Result Return"],
    "total_latency_ms": 2680,
    "bottleneck_in_path": "Consolidation (2450ms = 91% of total)",
    "optimization_potential_percent": 35
  },

  "capacity_warnings": [
    {
      "dimension": "storage",
      "utilization_percent": 47,
      "capacity_total_mb": 600,
      "warning_threshold_percent": 70,
      "time_to_threshold_days": 45,
      "action": "Monitor, plan optimization"
    }
  ],

  "performance_trends": {
    "period": "7_days",
    "semantic_search_trend": "increasing_latency",
    "consolidation_trend": "stable",
    "error_rate_trend": "stable",
    "capacity_trend": "increasing_load"
  },

  "optimization_recommendations": [
    {
      "priority": "high",
      "type": "performance",
      "issue": "Semantic search latency increasing",
      "recommendation": "Index optimization on semantic store (expected: 20-30% improvement)",
      "estimated_effort_hours": 2,
      "estimated_improvement_percent": 25
    },
    {
      "priority": "medium",
      "type": "storage",
      "issue": "Database approaching 50% capacity",
      "recommendation": "Schedule consolidation to compress episodic events (expected: 15-20% reduction)",
      "estimated_effort_hours": 3,
      "estimated_improvement_mb": 45
    },
    {
      "priority": "medium",
      "type": "integration",
      "issue": "Integration failure detected in cross-layer call",
      "recommendation": "Debug session manager integration (expected: better reliability)",
      "estimated_effort_hours": 1,
      "estimated_improvement_percent": 10
    }
  ],

  "alerts": [
    {
      "severity": "warning",
      "type": "performance",
      "message": "Semantic search latency up 30% vs baseline",
      "affected_component": "Semantic Layer",
      "action_recommended": "Run index optimization"
    }
  ],

  "predictions": {
    "storage_capacity_day": "2025-12-27",
    "predicted_failure_rate": 0.5,
    "confidence": 0.75
  },

  "note": "Call adapter.get_detail('monitoring', 'component', 'semantic_search') for detailed analysis"
}
```

## Monitoring Pattern

### Parallel Health Check Flow
```
┌──────────────────┐
│ Monitor Request  │
└────────┬─────────┘
         │
┌────────▼──────────────────────────────────┐
│ Parallel Monitoring (6 dimensions)        │
├──────┬────────┬──────┬────────┬────┬────┤
│Perf  │Storage │Exec  │Capacity│Err │Int │
│(67ms)│(78ms)  │(89ms)│(54ms)  │(64ms) │(60ms) │
├──────┴────────┴──────┴────────┴────┴────┤
│ Parallel slowest: 89ms (execution)    │
└────────┬──────────────────────────────────┘
         │
┌────────▼──────────────────┐
│ Analysis & Detection      │
│ - Bottleneck identification
│ - Trend analysis          │
│ - Capacity forecasting    │
└────────┬──────────────────┘
         │
┌────────▼──────────────────────┐
│ Return Summary & Recommend    │
│ - Health score               │
│ - Optimizations (prioritized)│
└──────────────────────────────┘
```

## Token Efficiency
Old: 140K+ tokens | New: <450 tokens | **Savings: 99%**

## Examples

### Basic Health Check

```python
# Run system health check
result = adapter.execute_operation(
    "monitoring",
    "check_health"
)

# Check overall status
print(f"Health: {result['overall_health']['score']:.2f}")
print(f"Status: {result['overall_health']['status']}")

# Review component health
for component, metrics in result['component_health'].items():
    print(f"{component}: {metrics['score']:.2f}")
```

### Bottleneck Detection

```python
# Identify bottlenecks
result = adapter.execute_operation(
    "monitoring",
    "detect_bottlenecks"
)

for bottleneck in result['bottlenecks']:
    print(f"{bottleneck['component']}: {bottleneck['issue']}")
    print(f"  Impact: {bottleneck['impact_score']:.2f}")
```

### Capacity Planning

```python
# Check capacity and forecasting
result = adapter.execute_operation(
    "monitoring",
    "check_capacity"
)

for warning in result['capacity_warnings']:
    print(f"⚠️ {warning['dimension']}: {warning['utilization_percent']:.0f}% used")
    print(f"   Threshold in {warning['time_to_threshold_days']} days")
```

### Optimization Recommendations

```python
# Get prioritized optimization suggestions
result = adapter.execute_operation(
    "monitoring",
    "get_recommendations"
)

for rec in result['optimization_recommendations']:
    if rec['priority'] == 'high':
        print(f"HIGH: {rec['recommendation']}")
        print(f"  Effort: {rec['estimated_effort_hours']}h")
        print(f"  Impact: {rec['estimated_improvement_percent']}%")
```

## Implementation Notes

Demonstrates filesystem API paradigm for system monitoring. This agent:
- Discovers monitoring operations via filesystem
- Monitors 6 health dimensions in parallel
- Returns only summary metrics (health scores, latencies, recommendations)
- Supports drill-down for detailed component analysis via `adapter.get_detail()`
- Identifies bottlenecks and critical paths
- Forecasts capacity and failure rates
- Ranks optimization recommendations by impact
- Provides actionable insights for system optimization
