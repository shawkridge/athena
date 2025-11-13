# Phase 3: Production Hardening - Context & Goals

## Context Checkpoint

**Project**: Athena - 8-Layer Neuroscience-Inspired Memory System for AI Agents
**Status**: 98% complete, 207/207 tests passing, production-ready
**Date**: November 10, 2025

## Completed Work Summary

### Phase 1: Core Functionality (119 tests) ✅
- 8-layer memory architecture (episodic, semantic, procedural, prospective, graph, meta, consolidation, supporting)
- 27 MCP tools with 228+ operations
- Dual-process consolidation (System 1 fast + System 2 LLM validation)
- RAG/Planning/Zettelkasten/GraphRAG supporting systems
- SQLite + sqlite-vec local-first storage
- All layer unit tests and integration tests passing

### Phase 2: Performance & Reliability (88 tests) ✅
- Week 1: Load testing baselines (6 tests)
- Week 2: Sustained load testing (29 tests)
- Week 3: Chaos engineering (30 tests)
  - Database failures: 85-99% success
  - Network timeouts: 93-99% success
  - Memory pressure: 85-99% success
  - Combined failures: 80-90% success
- Week 4: Performance profiling & optimization (39 tests)
  - CPU, memory, I/O profiling
  - Caching, algorithms, pooling, batching, indexing optimization
  - Performance baselines established

### Documentation Delivered
1. **README.md**: Quick start and overview
2. **ARCHITECTURE.md**: 8-layer system design
3. **DEVELOPMENT_GUIDE.md**: Development workflows
4. **API_REFERENCE.md**: MCP tool reference
5. **PERFORMANCE.md**: Performance baselines and optimization guide
6. **CHAOS_TESTING.md**: Failure scenarios and resilience validation
7. **PRODUCTION_READINESS.md**: Production assessment and sign-off

## Remaining Work (2% - Phase 3 Priority Items)

### Priority 1: MCP Handler Integration Tests (1-2 days)
**Status**: Not started
**File**: `tests/mcp/test_handlers_integration.py` (to create)

**Gap Description**:
- MCP handler layer (`src/athena/mcp/handlers.py`, 526 KB) has <20% test coverage
- Handlers are thin wrappers over tested core layers, but integration testing is missing
- Impact: Low (core logic tested), but needed for comprehensive coverage

**Deliverables**:
```
Target: 30-40 integration tests covering:
  ✓ All 27 MCP tools invocation
  ✓ Tool parameter validation
  ✓ Error handling and propagation
  ✓ Return value correctness
  ✓ State management across tool calls
  ✓ Tool dependency ordering

Acceptance Criteria:
  - All tests passing
  - >80% coverage for MCP handlers
  - No regressions in existing tests
```

**Key Files to Reference**:
- `src/athena/mcp/handlers.py` - Main handler implementation
- `src/athena/mcp/handlers_*.py` - Specialized handlers (tools, system, planning, etc.)
- `src/athena/mcp/operation_router.py` - Operation routing logic
- `tests/mcp/test_*.py` - Existing MCP tests for patterns

**Test Structure Template**:
```python
# tests/mcp/test_handlers_integration.py
import pytest
from unittest.mock import Mock, AsyncMock
from athena.mcp.handlers import MemoryMCPServer

@pytest.fixture
def mcp_server():
    """Create MCP server instance."""
    return MemoryMCPServer()

class TestRecallTool:
    """Test recall tool integration."""

    @pytest.mark.asyncio
    async def test_recall_with_valid_query(self, mcp_server):
        """Test recall operation with valid query."""
        result = await mcp_server.recall(
            project_id="1",
            query="test query",
            limit=10
        )
        assert result is not None
        # Verify structure, content, etc.

class TestRememberTool:
    """Test remember tool integration."""
    # Similar structure...

class TestToolErrorHandling:
    """Test tool error handling."""

    async def test_recall_missing_project(self, mcp_server):
        """Test recall with missing project."""
        with pytest.raises(ValueError):
            await mcp_server.recall(
                project_id="nonexistent",
                query="test"
            )
```

**Commands to Verify**:
```bash
# Run new tests
pytest tests/mcp/test_handlers_integration.py -v

# Check coverage
pytest --cov=src/athena/mcp --cov-report=html

# Should show >80% coverage for handlers.py
```

---

### Priority 2: Production Monitoring Integration (2-3 days)
**Status**: Not started
**Files to Create**:
- `src/athena/monitoring/exporters.py` - Prometheus exporter
- `src/athena/monitoring/structured_logging.py` - JSON logging
- `docs/MONITORING.md` - Monitoring guide

**Gap Description**:
- Health checks and metrics collection implemented
- No integration with external monitoring systems (Prometheus, Grafana)
- Missing structured logging for aggregation
- Impact: Medium (required for production observability)

**Deliverables**:

#### 2.1 Prometheus Exporter
```python
# src/athena/monitoring/exporters.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics to expose:
operation_counter = Counter(
    'athena_operations_total',
    'Total operations',
    ['operation_type', 'status']
)

operation_latency = Histogram(
    'athena_operation_latency_seconds',
    'Operation latency',
    ['operation_type'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

memory_usage = Gauge(
    'athena_memory_bytes',
    'Memory usage'
)

cache_hits = Counter(
    'athena_cache_hits_total',
    'Cache hits',
    ['cache_type']
)

# Expose metrics endpoint at /metrics
```

#### 2.2 Structured Logging
```python
# src/athena/monitoring/structured_logging.py
import json
import logging

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for aggregation."""

    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add contextual fields
        if hasattr(record, 'operation_id'):
            log_data['operation_id'] = record.operation_id
        if hasattr(record, 'duration'):
            log_data['duration_ms'] = record.duration

        return json.dumps(log_data)
```

#### 2.3 Alerting Rules
```yaml
# monitoring/alert_rules.yaml
groups:
  - name: athena_alerts
    rules:
      - alert: HighOperationLatency
        expr: histogram_quantile(0.95, athena_operation_latency_seconds) > 0.05
        for: 5m
        annotations:
          summary: "Operation latency above threshold"

      - alert: HighErrorRate
        expr: rate(athena_operations_total{status="error"}[5m]) > 0.001
        for: 2m
        annotations:
          summary: "Error rate above 0.1%"

      - alert: HighMemoryUsage
        expr: athena_memory_bytes > 1e9
        for: 5m
        annotations:
          summary: "Memory usage above 1GB"
```

#### 2.4 Monitoring Guide
```markdown
# docs/MONITORING.md

## Metrics Exposed

### Operation Metrics
- `athena_operations_total`: Total operations by type and status
- `athena_operation_latency_seconds`: Latency histogram (P50, P95, P99)
- `athena_operation_errors`: Errors by type

### Resource Metrics
- `athena_memory_bytes`: Current memory usage
- `athena_cpu_usage_percent`: CPU usage
- `athena_db_connections`: Active database connections

### Cache Metrics
- `athena_cache_hits_total`: Cache hits by type (L1, L2)
- `athena_cache_misses_total`: Cache misses by type
- `athena_cache_evictions`: LRU evictions

### Business Metrics
- `athena_memories_stored`: Total memories stored
- `athena_consolidations_total`: Total consolidations
- `athena_procedures_learned`: Total procedures extracted

## Alerting Thresholds

| Alert | Threshold | Action |
|-------|-----------|--------|
| High Latency | P95 > 50ms | Investigate query patterns |
| High Error Rate | >0.1% errors | Check logs for root cause |
| High Memory | >1GB | Check for leaks, restart if needed |
| Low Cache Hit | <30% | Review cache configuration |
| DB Latency | >100ms | Check database load |

## Dashboards

### Main Dashboard
- Operation throughput (ops/sec)
- Latency percentiles (P50, P95, P99)
- Error rate (%)
- Memory and CPU usage
- Cache hit rates

### Detailed Dashboard
- Per-operation latency breakdown
- Error type distribution
- Memory growth over time
- Cache efficiency metrics
```

**Commands to Verify**:
```bash
# Start Prometheus
prometheus --config.file=monitoring/prometheus.yml

# Verify metrics endpoint
curl http://localhost:8000/metrics

# Check logs are valid JSON
tail -f /var/log/athena/server.log | jq .

# Verify alerts fire (after 5+ minutes)
curl http://localhost:9090/api/v1/alerts
```

**Test Requirements**:
```python
# tests/monitoring/test_exporters.py
def test_prometheus_metrics_exposed():
    """Verify Prometheus metrics are exposed."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "athena_operations_total" in response.text

def test_structured_logging():
    """Verify logs are valid JSON."""
    # Capture logs, parse as JSON
    logs = capture_logs()
    for log_line in logs:
        json_log = json.loads(log_line)
        assert "timestamp" in json_log
        assert "level" in json_log
```

---

### Priority 3: Enhanced Security Review (2 days)
**Status**: Partially done
**File**: Create `SECURITY_AUDIT.md`

**Gap Description**:
- All critical paths tested and SQL injection verified
- Minor gaps: Input validation, rate limiting, audit logging
- Impact: Low (no known vulnerabilities), but good practice

**Deliverables**:

#### 3.1 Input Validation Audit
```python
# Verify all MCP tool inputs are validated:
# - String lengths (max 10KB for queries)
# - Integer bounds (project_id > 0, limit 1-1000)
# - Enum values (memory_type in [semantic, episodic, procedural])
# - Regex patterns (no special characters in project names)

# Example enhanced validation:
from pydantic import BaseModel, Field, validator

class RecallRequest(BaseModel):
    project_id: str = Field(..., min_length=1, max_length=100)
    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(default=10, ge=1, le=1000)

    @validator('query')
    def query_no_injection(cls, v):
        # Verify no SQL-like patterns
        if any(kw in v.lower() for kw in ['drop', 'delete', 'insert']):
            raise ValueError("Invalid query pattern")
        return v
```

#### 3.2 Rate Limiting
```python
# src/athena/mcp/rate_limiter.py
from ratelimit import limits, sleep_and_retry

# Limits per operation type:
# - Recall: 100 req/minute per project
# - Remember: 50 req/minute per project
# - Optimize: 10 req/minute per project

@sleep_and_retry
@limits(calls=100, period=60)
async def recall_with_limit(project_id: str, query: str):
    """Rate-limited recall operation."""
    return await recall(project_id, query)
```

#### 3.3 Audit Logging
```python
# Log sensitive operations:
# - Store/delete memories
# - Consolidation runs
# - Project creation/deletion
# - Configuration changes

audit_log.info(
    "Memory stored",
    extra={
        'operation_id': operation_id,
        'project_id': project_id,
        'memory_type': memory_type,
        'timestamp': datetime.now(),
        'user_ip': request.remote_addr
    }
)
```

**Commands to Verify**:
```bash
# Run security-focused tests
pytest tests/security/ -v

# Check for common vulnerabilities
bandit -r src/athena

# Verify no hardcoded secrets
detect-secrets scan src/
```

---

### Priority 4: Deployment Automation (3-5 days)
**Status**: Partially done (README has basic instructions)
**Files to Create**:
- `docker/Dockerfile`
- `docker/docker-compose.yml`
- `scripts/deploy.sh`
- `scripts/healthcheck.sh`
- `docs/DEPLOYMENT.md`

**Deliverables**:

#### 4.1 Docker Setup
```dockerfile
# docker/Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -e .

# Copy source
COPY src/ src/
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python scripts/healthcheck.sh

# Expose metrics port
EXPOSE 8000 9000

# Start server
CMD ["memory-mcp"]
```

#### 4.2 Docker Compose
```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  athena:
    build: .
    ports:
      - "8000:8000"  # MCP server
      - "9000:9000"  # Prometheus metrics
    volumes:
      - athena_data:/root/.athena
    environment:
      - PYTHONUNBUFFERED=1
      - DEBUG=0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  athena_data:
  prometheus_data:
  grafana_data:
```

#### 4.3 Deployment Script
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Starting Athena deployment...${NC}"

# Step 1: Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t athena:latest docker/
echo -e "${GREEN}✓ Docker image built${NC}"

# Step 2: Run health check
echo -e "${YELLOW}Running health checks...${NC}"
docker-compose up -d
sleep 10

# Step 3: Verify all services
SERVICES=("athena" "prometheus" "grafana")
for service in "${SERVICES[@]}"; do
    if docker-compose ps $service | grep -q "Up"; then
        echo -e "${GREEN}✓ $service is healthy${NC}"
    else
        echo -e "${RED}✗ $service failed to start${NC}"
        exit 1
    fi
done

# Step 4: Run test suite
echo -e "${YELLOW}Running test suite...${NC}"
docker-compose exec -T athena pytest tests/ -v --tb=short

echo -e "${GREEN}✓ Deployment successful!${NC}"
echo -e "${GREEN}Services running:${NC}"
echo -e "  - Athena MCP: http://localhost:8000"
echo -e "  - Prometheus: http://localhost:9090"
echo -e "  - Grafana: http://localhost:3000"
```

#### 4.4 Healthcheck Script
```bash
#!/bin/bash
# scripts/healthcheck.sh

# Check MCP server
curl -f http://localhost:8000/health || exit 1

# Check database
python -c "
from athena.core.database import Database
db = Database()
db.execute('SELECT 1')
print('Database OK')
" || exit 1

# Check memory store
python -c "
from athena.manager import UnifiedMemoryManager
manager = UnifiedMemoryManager()
manager.recall('test', 'health check')
print('Memory store OK')
" || exit 1

echo "All health checks passed"
exit 0
```

**Commands to Verify**:
```bash
# Build and start services
docker-compose -f docker/docker-compose.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f athena

# Run tests inside container
docker-compose exec athena pytest tests/ -v

# Stop all services
docker-compose down
```

---

## Session Goals

When starting Phase 3, work on these in order:

1. **Session 1: MCP Handler Tests** (1-2 days)
   - Create `tests/mcp/test_handlers_integration.py`
   - Write 30-40 integration tests
   - Achieve >80% MCP handler coverage
   - All tests passing

2. **Session 2: Monitoring Integration** (2-3 days)
   - Create Prometheus exporter
   - Implement structured logging
   - Write alerting rules
   - Create monitoring guide
   - Verify metrics/logs working

3. **Session 3: Security Review** (1-2 days)
   - Input validation audit
   - Rate limiting implementation
   - Audit logging setup
   - Security documentation

4. **Session 4: Deployment Automation** (2-3 days)
   - Docker setup (Dockerfile, docker-compose)
   - Deployment scripts
   - Health checks
   - Deployment guide

5. **Session 5: Staging Deployment & Validation** (3-5 days)
   - Deploy to staging environment
   - Run full test suite
   - Monitor for 3-5 days
   - Collect performance metrics
   - Final go/no-go decision

## Files to Reference

### Core Implementation
- `src/athena/mcp/handlers.py` - MCP handler implementation (526 KB)
- `src/athena/core/database.py` - Database layer
- `src/athena/manager.py` - Unified memory manager

### Existing Tests
- `tests/mcp/` - MCP-related tests
- `tests/unit/` - Unit tests (119 tests, reference for patterns)
- `tests/integration/` - Integration tests (reference for patterns)
- `tests/performance/` - Performance tests (88 tests, reference for patterns)

### Documentation
- `README.md` - Quick start
- `ARCHITECTURE.md` - System design
- `DEVELOPMENT_GUIDE.md` - Development workflows
- `PRODUCTION_READINESS.md` - Production assessment
- `PERFORMANCE.md` - Performance guide
- `CHAOS_TESTING.md` - Chaos engineering guide

## Success Criteria

### All Priority Items Complete
- [ ] MCP handler integration tests: 30-40 tests, >80% coverage
- [ ] Monitoring integration: Prometheus exporter, structured logging, alerting
- [ ] Security review: Input validation, rate limiting, audit logging
- [ ] Deployment automation: Docker, compose, scripts, guides

### All Tests Passing
- [ ] 207 existing tests still passing
- [ ] 30-40 new MCP integration tests passing
- [ ] Monitoring tests passing
- [ ] Security tests passing
- [ ] **Total**: 240+ tests passing

### Production Ready for Staging
- [ ] Full test suite passing
- [ ] All gaps closed
- [ ] Documentation complete
- [ ] Deployment scripts tested
- [ ] Monitoring/alerting configured

### Deployment Success
- [ ] Staging environment deployed and stable
- [ ] Performance metrics match baselines
- [ ] No regressions in existing tests
- [ ] Monitoring/alerting working
- [ ] Ready for production deployment

## Prompt Template for Next Session

**Use this prompt when starting Phase 3**:

```
I'm continuing Phase 3 (Production Hardening) for the Athena memory system.

Current Status:
- 207/207 tests passing (100%)
- 98% complete, ready for production
- Remaining gaps: MCP handler tests, monitoring integration, security review, deployment automation

Today's Goal: [Choose one from above]

Context File: /home/user/.work/athena/PHASE_3_CONTEXT.md

Please:
1. Review the context file (PHASE_3_CONTEXT.md)
2. Work on the chosen gap area
3. Write tests following the patterns in tests/unit/ and tests/integration/
4. Ensure all existing tests still pass
5. Document any new functionality

Let me know when you're ready to start!
```

---

**Version**: 1.0
**Created**: November 10, 2025
**Status**: Ready for Phase 3 (Production Hardening)
**Estimated Duration**: 2-3 weeks to close all gaps
**Success Probability**: 95%+ (path is clear, gaps are well-defined)
