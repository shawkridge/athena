# Athena Production Monitoring Guide (Phase 3)

Complete guide to monitoring and observability for Athena memory system.

## Overview

Athena integrates with Prometheus and ELK stack for complete observability:
- **Prometheus**: Time-series metrics and alerting
- **Structured Logging**: JSON logs for aggregation
- **Grafana**: Visual dashboards
- **Datadog/ELK**: Log aggregation and analysis

## Metrics Exposed

### Operation Metrics

#### `athena_operations_total`
- Type: Counter
- Labels: `operation_type`, `status`
- Description: Total operations by type and status
- Example:
  ```prometheus
  athena_operations_total{operation_type="recall", status="success"} 1250
  athena_operations_total{operation_type="recall", status="error"} 3
  ```

#### `athena_operation_latency_seconds`
- Type: Histogram
- Labels: `operation_type`
- Buckets: 0.01s, 0.05s, 0.1s, 0.5s, 1.0s, 5.0s
- Description: Operation latency distribution
- Percentiles:
  - P50 (median): Typical operation time
  - P95: 95% of operations complete within this time
  - P99: 99% of operations complete within this time

#### `athena_operation_errors_total`
- Type: Counter
- Labels: `operation_type`, `error_type`
- Description: Total errors by operation and error type
- Example:
  ```prometheus
  athena_operation_errors_total{operation_type="recall", error_type="ValueError"} 2
  ```

### Resource Metrics

#### `athena_memory_bytes`
- Type: Gauge
- Description: Process memory usage in bytes
- Alert: Warning >1GB, Critical >2GB

#### `athena_cpu_percent`
- Type: Gauge
- Description: CPU usage percentage (0-100)
- Alert: Warning >80%

#### `athena_db_connections_active`
- Type: Gauge
- Description: Active database connections
- Alert: Warning >10 connections

#### `athena_working_memory_items_current`
- Type: Gauge
- Description: Current items in working memory (capacity: 7±2)
- Alert: Warning >15 items

### Cache Metrics

#### `athena_cache_hits_total`
- Type: Counter
- Labels: `cache_type`
- Description: Total cache hits by cache type

#### `athena_cache_misses_total`
- Type: Counter
- Labels: `cache_type`
- Description: Total cache misses by cache type

#### `athena_cache_evictions_total`
- Type: Counter
- Labels: `cache_type`
- Description: Total LRU evictions

**Cache Hit Rate Calculation**:
```prometheus
sum(rate(athena_cache_hits_total[5m])) /
(sum(rate(athena_cache_hits_total[5m])) + sum(rate(athena_cache_misses_total[5m])))
```

Alert: Warning if <30%

### Business Metrics

#### `athena_memories_stored_total`
- Type: Gauge
- Description: Total memories stored in system

#### `athena_consolidations_total`
- Type: Counter
- Labels: `strategy`
- Description: Total consolidation runs by strategy

#### `athena_procedures_learned_total`
- Type: Gauge
- Description: Total procedures extracted from episodic events

#### `athena_graph_entities_total`
- Type: Gauge
- Description: Total entities in knowledge graph

#### `athena_graph_relations_total`
- Type: Gauge
- Description: Total relations in knowledge graph

## Alerting Rules

### Performance Thresholds

| Alert | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| High Latency (P95) | >50ms | Warning | Investigate query patterns |
| High Latency (P99) | >100ms | Critical | Immediate investigation |
| High Error Rate | >0.1% | Warning | Check logs for root cause |
| Critical Error Rate | >1% | Critical | Page on-call engineer |

### Resource Thresholds

| Alert | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| High Memory | >1GB | Warning | Check for memory leaks |
| Critical Memory | >2GB | Critical | Restart service |
| High CPU | >80% | Warning | Profile and optimize |
| High DB Connections | >10 | Warning | Check for connection leaks |

### Data Quality Thresholds

| Alert | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| Low Cache Hit Rate | <30% | Info | Review cache configuration |
| High Cache Evictions | >1/sec | Warning | Increase cache size |
| No Consolidation | >1 hour | Warning | Check scheduler |

## Setup Instructions

### 1. Start Prometheus

```bash
prometheus --config.file=monitoring/prometheus.yml
```

Then visit: http://localhost:9090

### 2. Start Grafana

```bash
docker run -d \
  -p 3000:3000 \
  -v grafana_storage:/var/lib/grafana \
  grafana/grafana
```

Default credentials: admin / admin

### 3. Configure Grafana Data Source

1. Visit: http://localhost:3000
2. Settings → Data Sources → Add
3. Choose Prometheus
4. URL: http://localhost:9090
5. Save & Test

### 4. Import Dashboards

Create new dashboard with these panels:

#### Main Dashboard

**Operations Per Second**:
```prometheus
sum(rate(athena_operations_total[1m])) by (status)
```

**P95/P99 Latency**:
```prometheus
histogram_quantile(0.95, rate(athena_operation_latency_seconds_bucket[5m]))
histogram_quantile(0.99, rate(athena_operation_latency_seconds_bucket[5m]))
```

**Error Rate**:
```prometheus
sum(rate(athena_operations_total{status="error"}[5m])) /
sum(rate(athena_operations_total[5m]))
```

**Resource Usage**:
```prometheus
athena_memory_bytes
athena_cpu_percent
athena_db_connections_active
```

**Cache Hit Rate**:
```prometheus
sum(rate(athena_cache_hits_total[5m])) /
(sum(rate(athena_cache_hits_total[5m])) + sum(rate(athena_cache_misses_total[5m])))
```

#### Detailed Dashboard

**Error Distribution**:
```prometheus
sum by (error_type) (rate(athena_operation_errors_total[5m]))
```

**Memory Growth**:
```prometheus
rate(athena_memories_stored_total[1h])
```

**Procedure Learning Rate**:
```prometheus
rate(athena_procedures_learned_total[1h])
```

**Graph Growth**:
```prometheus
athena_graph_entities_total
athena_graph_relations_total
```

## JSON Structured Logging

All logs are exported as JSON for aggregation:

```json
{
  "timestamp": "2025-11-10T15:30:45.123Z",
  "level": "INFO",
  "logger": "athena.memory",
  "message": "Operation complete: recall (0.045s)",
  "operation_id": "op_abc123",
  "operation_type": "recall",
  "duration_seconds": 0.045,
  "status": "complete"
}
```

### Log Aggregation Setup

#### With ELK Stack

1. **Filebeat** → collect logs
2. **Elasticsearch** → store logs
3. **Kibana** → analyze logs

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /var/log/athena/*.log
    json.message_key: message
    json.keys_under_root: true

output.elasticsearch:
  hosts: ["localhost:9200"]
```

#### With Datadog

```python
from pythonjsonlogger import jsonlogger

handler = logging.FileHandler('/var/log/athena/app.log')
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
```

## Operational Procedures

### Debugging High Latency

1. **Check P95/P99 percentiles**:
   ```prometheus
   histogram_quantile(0.95, rate(athena_operation_latency_seconds_bucket[5m]))
   ```

2. **Identify slow operations**:
   ```prometheus
   topk(5, rate(athena_operation_latency_seconds_sum[5m]) /
        rate(athena_operation_latency_seconds_count[5m]))
   ```

3. **Check error correlation**:
   ```prometheus
   sum by (operation_type) (rate(athena_operations_total{status="error"}[5m]))
   ```

### Debugging High Error Rate

1. **Count errors by type**:
   ```prometheus
   sum by (error_type) (rate(athena_operation_errors_total[5m]))
   ```

2. **Check logs**:
   ```bash
   # ELK/Kibana
   level: ERROR AND operation_type: recall

   # Datadog
   level:ERROR operation_type:recall
   ```

3. **Correlate with resources**:
   - Check memory usage
   - Check database connections
   - Check CPU usage

### Debugging Memory Growth

1. **Check memory trend**:
   ```prometheus
   rate(athena_memories_stored_total[1h])
   ```

2. **Check consolidation**:
   ```prometheus
   increase(athena_consolidations_total[1h])
   ```

3. **Review logs**:
   ```bash
   # Filter consolidation errors
   operation_type: consolidate status: error
   ```

## Best Practices

### 1. Alert Tuning
- Set thresholds based on SLA requirements
- Use severity levels appropriately
- Include runbooks in annotations

### 2. Metrics Naming
- Use `athena_` prefix for all metrics
- Include units in metric names (e.g., `_seconds`, `_bytes`)
- Use consistent label naming

### 3. Log Context
- Always set `operation_id` for traceability
- Include relevant business context
- Log at appropriate levels

### 4. Dashboard Design
- Create separate dashboards for different personas
  - Ops: Resource usage, errors, availability
  - Dev: Operation latency, error distribution
  - Product: Business metrics, growth trends

### 5. Cardinality Management
- Be careful with high-cardinality labels
- Don't use user IDs or request IDs as labels
- Use structured logging for low-cardinality fields

## Troubleshooting

### Prometheus can't scrape metrics

1. Check Athena is running on correct port
2. Verify firewall allows access
3. Check `/metrics` endpoint directly:
   ```bash
   curl http://localhost:8000/metrics
   ```

### Metrics missing from Prometheus

1. Wait 30s after Prometheus start (initialization delay)
2. Check `prometheus.yml` job configuration
3. View Prometheus targets: http://localhost:9090/targets

### High memory usage in Prometheus

1. Reduce metric retention: `--storage.tsdb.retention.time=7d`
2. Reduce cardinality in labels
3. Check for cardinality explosion in high-dimension metrics

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Structured Logging Best Practices](https://www.kartar.net/2015/12/structured-logging/)
- [Athena Architecture](./ARCHITECTURE.md)
- [Production Readiness](./PRODUCTION_READINESS.md)

---

**Version**: 1.0
**Phase**: Phase 3 - Production Hardening
**Last Updated**: November 10, 2025
