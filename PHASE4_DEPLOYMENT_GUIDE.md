# Phase 4.5: Production Deployment Guide

**Version**: 1.0
**Status**: Production-Ready
**Last Updated**: November 8, 2025

Complete guide for deploying Athena's optimized memory system to production.

---

## Table of Contents

1. [Pre-Deployment](#pre-deployment)
2. [Environment Setup](#environment-setup)
3. [Configuration](#configuration)
4. [Deployment](#deployment)
5. [Monitoring](#monitoring)
6. [Health Checks](#health-checks)
7. [Troubleshooting](#troubleshooting)
8. [Scaling](#scaling)

---

## Pre-Deployment

### Checklist

Before deploying to production:

- [ ] All Phase 4 tests passing (benchmarks, load tests, scenario tests)
- [ ] Performance targets verified (all metrics exceeded)
- [ ] Memory leaks detected and eliminated
- [ ] Load tested at production concurrency (1000+)
- [ ] Security audit completed
- [ ] Documentation reviewed and verified
- [ ] Backup strategy defined
- [ ] Rollback plan documented
- [ ] Monitoring alerting configured
- [ ] On-call team trained

### Requirements

**Hardware**:
- CPU: 4+ cores (8+ recommended for high load)
- Memory: 8GB minimum (16GB+ recommended)
- Storage: 100GB+ for database
- Network: 1Gbps+ connectivity

**Software**:
- Node.js 16+ (18+ recommended)
- SQLite 3.35+ (with sqlite-vec)
- Docker/Kubernetes (optional but recommended)

**Database**:
- SQLite with sqlite-vec extension
- Regular backups (hourly minimum)
- Replication for high availability

---

## Environment Setup

### Installation

```bash
# Clone repository
git clone <repo-url>
cd athena

# Install dependencies
npm install

# Install development dependencies (for monitoring)
npm install --save pm2 prometheus-client pino

# Build project
npm run build

# Verify installation
npm run test
```

### Directory Structure

```
/app
├── src/
│   ├── execution/           # Optimization layers
│   │   ├── caching_layer.ts
│   │   ├── circuit_breaker.ts
│   │   ├── connection_pool.ts
│   │   └── query_optimizer.ts
│   └── ...
├── tests/
│   ├── benchmarks/          # Performance benchmarks
│   ├── performance/         # Load tests
│   └── ...
├── config/
│   ├── production.json      # Production config
│   ├── staging.json         # Staging config
│   └── development.json     # Development config
├── docs/
│   └── deployment/          # Deployment docs
└── package.json
```

### Database Setup

```bash
# Create database with schema
npm run db:init

# Verify database
npm run db:verify

# Enable backups
npm run db:backup:enable

# Test backup
npm run db:backup:test
```

---

## Configuration

### Environment Variables

```bash
# Environment selection
export NODE_ENV=production

# Database
export DATABASE_PATH=/data/memory.db
export DATABASE_BACKUP_PATH=/data/backups
export DATABASE_REPLICATION_ENABLED=true
export DATABASE_REPLICA_HOST=replica-db.internal

# Cache configuration
export CACHE_MAX_SIZE=50000
export CACHE_DEFAULT_TTL=300000        # 5 minutes
export CACHE_WARMING_ENABLED=true

# Connection pooling
export POOL_MAX_CONNECTIONS=100
export POOL_MIN_CONNECTIONS=10
export POOL_IDLE_TIMEOUT=30000
export POOL_VALIDATION_INTERVAL=10000

# Circuit breaker
export BREAKER_FAILURE_THRESHOLD=0.5
export BREAKER_SUCCESS_THRESHOLD=0.8
export BREAKER_TIMEOUT=60000

# Monitoring
export METRICS_ENABLED=true
export METRICS_INTERVAL=30000
export HEALTHCHECK_INTERVAL=10000
export LOGGING_LEVEL=info

# Security
export ENABLE_RATE_LIMITING=true
export RATE_LIMIT_REQUESTS=1000
export RATE_LIMIT_WINDOW=60000
export ENABLE_API_AUTHENTICATION=true

# MCP Configuration
export MCP_SERVER_HOST=0.0.0.0
export MCP_SERVER_PORT=3000
export MCP_TIMEOUT=30000
```

### Configuration File

Create `config/production.json`:

```json
{
  "environment": "production",
  "server": {
    "host": "0.0.0.0",
    "port": 3000,
    "workers": 4,
    "timeout": 30000
  },
  "database": {
    "path": "/data/memory.db",
    "backupPath": "/data/backups",
    "backupInterval": 3600000,
    "replicationEnabled": true,
    "replicaHost": "replica-db.internal"
  },
  "cache": {
    "maxSize": 50000,
    "defaultTtl": 300000,
    "warmingEnabled": true,
    "monitoringEnabled": true
  },
  "pooling": {
    "database": {
      "maxConnections": 100,
      "minConnections": 10,
      "idleTimeout": 30000,
      "validationInterval": 10000
    },
    "mcp": {
      "maxConnections": 50,
      "minConnections": 5,
      "idleTimeout": 60000
    }
  },
  "circuitBreaker": {
    "failureThreshold": 0.5,
    "successThreshold": 0.8,
    "timeout": 60000,
    "volumeThreshold": 10
  },
  "monitoring": {
    "enabled": true,
    "interval": 30000,
    "metricsExport": true,
    "healthCheckInterval": 10000,
    "alertingEnabled": true
  },
  "logging": {
    "level": "info",
    "transport": "file",
    "path": "/var/log/athena",
    "maxSize": 1073741824,
    "maxFiles": 10
  },
  "security": {
    "rateLimiting": true,
    "requests": 1000,
    "window": 60000,
    "authentication": true
  }
}
```

---

## Deployment

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --production

# Copy source code
COPY src ./src
COPY config ./config

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => r.statusCode===200 ? process.exit(0) : process.exit(1))"

# Start application
CMD ["node", "src/server.js"]
```

Build and push:

```bash
# Build image
docker build -t athena:latest .

# Tag for registry
docker tag athena:latest registry.example.com/athena:latest

# Push to registry
docker push registry.example.com/athena:latest
```

### Kubernetes Deployment

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: athena
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: athena
  template:
    metadata:
      labels:
        app: athena
    spec:
      containers:
      - name: athena
        image: registry.example.com/athena:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: DATABASE_PATH
          value: "/data/memory.db"
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: data
          mountPath: /data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: athena-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: athena-service
  namespace: production
spec:
  selector:
    app: athena
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: athena-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: athena
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

Deploy:

```bash
# Create namespace
kubectl create namespace production

# Create persistent volume
kubectl apply -f k8s/pv.yaml -n production

# Deploy application
kubectl apply -f k8s/deployment.yaml

# Verify deployment
kubectl get pods -n production
kubectl logs -f deployment/athena -n production
```

### PM2 Process Manager

Create `ecosystem.config.js`:

```javascript
module.exports = {
  apps: [{
    name: 'athena',
    script: './src/server.js',
    instances: 'max',
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      DATABASE_PATH: '/data/memory.db'
    },
    error_file: '/var/log/athena/error.log',
    out_file: '/var/log/athena/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    max_memory_restart: '2G',
    autorestart: true,
    watch: false,
    ignore_watch: ['node_modules', 'logs'],
    max_restarts: 10,
    min_uptime: '10s'
  }]
};
```

Start with PM2:

```bash
# Start application
pm2 start ecosystem.config.js

# Monitor
pm2 monit

# View logs
pm2 logs athena

# Setup startup script
pm2 startup
pm2 save
```

---

## Monitoring

### Metrics Collection

```typescript
// Prometheus metrics
import promClient from 'prom-client';

// Create metrics
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_ms',
  help: 'Duration of HTTP requests in ms',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 5, 15, 50, 100, 500]
});

const cacheHitRate = new promClient.Gauge({
  name: 'cache_hit_rate',
  help: 'Cache hit rate 0-1',
  labelNames: ['cache_name']
});

const circuitBreakerState = new promClient.Gauge({
  name: 'circuit_breaker_state',
  help: 'Circuit breaker state (0=closed, 1=half-open, 2=open)',
  labelNames: ['service']
});

// Export metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.end(await promClient.register.metrics());
});
```

### Health Check Endpoint

```typescript
app.get('/health', async (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    checks: {
      database: await checkDatabase(),
      cache: await checkCache(),
      mcp: await checkMCP(),
      circuitBreaker: await checkCircuitBreaker()
    }
  };

  const healthy = Object.values(health.checks).every(c => c.status === 'healthy');
  res.status(healthy ? 200 : 503).json(health);
});
```

### Alerting Rules

Create Prometheus alerts:

```yaml
groups:
- name: athena
  interval: 30s
  rules:
  - alert: HighCacheHitRate
    expr: cache_hit_rate < 0.6
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Cache hit rate below 60%"

  - alert: HighLatency
    expr: histogram_quantile(0.95, http_request_duration_ms_bucket) > 500
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "P95 latency above 500ms"

  - alert: CircuitBreakerOpen
    expr: circuit_breaker_state == 2
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Circuit breaker is open"

  - alert: HighMemoryUsage
    expr: node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes < 0.2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Memory usage above 80%"
```

---

## Health Checks

### Readiness Probe

```typescript
app.get('/ready', async (req, res) => {
  const ready = await checkReadiness();
  res.status(ready ? 200 : 503).json({
    ready,
    checks: await getReadinessChecks()
  });
});

async function checkReadiness() {
  return await Promise.all([
    checkDatabase(),
    checkCache(),
    checkMCP()
  ]).then(results => results.every(r => r.status === 'healthy'));
}
```

### Liveness Probe

```typescript
app.get('/live', async (req, res) => {
  const alive = process.uptime() > 30;  // 30 second grace period
  res.status(alive ? 200 : 503).json({ alive });
});
```

---

## Troubleshooting

### Common Issues

#### High Latency

```bash
# Check cache hit rate
curl http://localhost:3000/metrics | grep cache_hit_rate

# If low, warm cache
curl -X POST http://localhost:3000/admin/cache-warm

# Check circuit breaker status
curl http://localhost:3000/metrics | grep circuit_breaker_state
```

#### High Memory Usage

```bash
# Check memory stats
curl http://localhost:3000/health | jq '.memory'

# If high, trigger garbage collection
curl -X POST http://localhost:3000/admin/gc

# Check cache size
curl http://localhost:3000/metrics | grep cache_size_bytes
```

#### Database Issues

```bash
# Check database health
curl http://localhost:3000/health | jq '.checks.database'

# Verify database integrity
npm run db:verify

# Restore from backup
npm run db:restore

# Check backup status
npm run db:backup:status
```

---

## Scaling

### Horizontal Scaling

```bash
# With Kubernetes
kubectl scale deployment athena --replicas=5

# With PM2
pm2 scale athena 5

# Verify scaling
kubectl get pods -l app=athena
pm2 list
```

### Load Balancing

Configure load balancer (e.g., Nginx):

```nginx
upstream athena {
  server athena-1:3000;
  server athena-2:3000;
  server athena-3:3000;
  keepalive 64;
}

server {
  listen 80;
  server_name memory.example.com;

  location / {
    proxy_pass http://athena;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }

  location /metrics {
    proxy_pass http://athena;
    access_log off;
  }

  location /health {
    proxy_pass http://athena;
    access_log off;
  }
}
```

### Capacity Planning

```
Current: 1 instance
- Throughput: 500 ops/sec
- P95 Latency: 113ms
- Memory: 150MB

After 4.1-4.4 optimization: 1 instance
- Throughput: 3000 ops/sec (6x)
- P95 Latency: 50ms (2.3x faster)
- Memory: 100MB (33% reduction)

Scaling guide:
- 1 instance: 3000 ops/sec
- 3 instances: 9000 ops/sec
- 10 instances: 30,000 ops/sec
```

---

## Backup & Recovery

### Automated Backups

```bash
# Enable automated backups (hourly)
npm run db:backup:enable --interval=3600

# Verify backups
npm run db:backup:list

# Create manual backup
npm run db:backup:create

# Restore from backup
npm run db:restore --backup-id=<id>

# Backup retention policy
npm run db:backup:cleanup --keep=30  # Keep 30 backups
```

### Disaster Recovery Plan

1. **Detection** (automated alerts)
   - Monitor health checks
   - Alert on failures

2. **Immediate Actions**
   - Failover to replica
   - Scale up remaining instances

3. **Recovery**
   - Restore from latest backup
   - Verify data integrity
   - Restart services

4. **Post-Incident**
   - Root cause analysis
   - Implement preventive measures
   - Update runbooks

---

## Security

### Authentication

```bash
export ENABLE_API_AUTHENTICATION=true
export API_KEY_LENGTH=32
export API_KEY_ROTATION=2592000  # 30 days
```

### Rate Limiting

```bash
export ENABLE_RATE_LIMITING=true
export RATE_LIMIT_REQUESTS=1000
export RATE_LIMIT_WINDOW=60000    # 1 minute
```

### SSL/TLS

```nginx
server {
  listen 443 ssl;
  ssl_certificate /etc/ssl/certs/athena.crt;
  ssl_certificate_key /etc/ssl/private/athena.key;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers HIGH:!aNULL:!MD5;
}
```

---

## Maintenance

### Regular Tasks

**Daily**:
- Monitor metrics
- Check alerts
- Review logs

**Weekly**:
- Backup verification
- Performance analysis
- Security scan

**Monthly**:
- Capacity planning
- Database optimization
- Security audit

---

## Support

### Documentation
- PHASE4_OPTIMIZATION_GUIDE.md
- PHASE4_PERFORMANCE_REPORT.md
- API documentation

### Monitoring Dashboard
- Grafana for visualization
- Prometheus for metrics
- ELK stack for logs

### On-Call Support
- 24/7 monitoring
- Automated alerting
- Escalation procedures

---

**Generated**: November 8, 2025
**Status**: Production-Ready ✅
**Version**: 1.0
