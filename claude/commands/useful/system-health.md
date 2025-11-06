---
description: Check system health and performance - monitors bottlenecks and optimization opportunities
argument-hint: "Optional: --detailed for full performance analysis"
---

# System Health

Check overall system health, performance, and identify bottlenecks and optimization opportunities.

Usage:
- `/system-health` - Quick health snapshot
- `/system-health --detailed` - Deep performance analysis

Monitors:
- **Memory Performance**: Query speed, consolidation efficiency
- **Storage Health**: Database size, index efficiency
- **Execution Performance**: Task speed, automation reliability
- **System Capacity**: Cognitive load, resource utilization
- **Error Rates**: Failed operations, timeouts
- **Integration Health**: Tool responsiveness, agent effectiveness

Returns:
- Overall health score (0.0-1.0)
- Component health breakdown
- Performance metrics summary
- Bottleneck identification
- Optimization recommendations
- Capacity warnings (if near limits)
- Recent trends (improving/degrading)

Example output:
```
System Health: 0.82 (GOOD)

Components:
  ✓ Memory Operations: 0.90 (excellent)
  ⚠ Consolidation: 0.65 (slow, should optimize)
  ✓ Task Execution: 0.85 (good)
  ⚠ Storage: 0.72 (approaching size limit)

Performance:
  - Avg semantic search: 85ms (target <100ms)
  - Consolidation cycle: 3.2s (target <2.5s)
  - Task startup: 250ms (target <200ms)

Critical Bottlenecks:
  1. Consolidation System 2 LLM validation too slow
  2. Episodic event clustering growing O(n²)
  3. Graph community detection expensive (weekly run)

Recommendations:
  - Optimize LLM validation batching (estimate: 30% faster)
  - Implement incremental clustering (estimate: 50% faster)
  - Cache community detection results (estimate: 10x faster)
```

The system-monitor agent runs this daily to track health trends.
