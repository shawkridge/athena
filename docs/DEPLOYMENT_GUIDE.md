# Deployment Guide

Guide to deploying Athena in production environments.

## Table of Contents

- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Database Setup](#database-setup)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Monitoring & Health](#monitoring--health)
- [Scaling](#scaling)
- [Backup & Recovery](#backup--recovery)

---

## Pre-Deployment Checklist

### Requirements

- [ ] PostgreSQL 12+ (remote or local)
- [ ] Python 3.10+
- [ ] 4GB+ RAM
- [ ] 500MB+ disk space
- [ ] Ollama or Anthropic API key for embeddings
- [ ] Monitoring solution (optional but recommended)

### Security Checklist

- [ ] Database credentials in secrets manager (not in code)
- [ ] API keys in environment variables or secrets
- [ ] HTTPS/TLS enabled for all connections
- [ ] Firewall restricts database access to app servers
- [ ] Regular backups enabled and tested
- [ ] Access control configured
- [ ] Audit logging enabled

### Performance Checklist

- [ ] Database connection pool tuned
- [ ] Cache enabled and sized appropriately
- [ ] Indexes created on common queries
- [ ] Slow query log enabled
- [ ] Load testing completed
- [ ] CPU/memory limits set

---

## Database Setup

### PostgreSQL Installation (Production)

#### On Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql  # Start on boot
```

#### On macOS (AWS RDS recommended)

```bash
# Or use AWS RDS for managed database
# Create RDS instance at https://console.aws.amazon.com

# Store connection details securely
aws secretsmanager create-secret \
  --name prod/athena-db-password \
  --secret-string "$(openssl rand -base64 32)"
```

#### On Docker

```dockerfile
FROM postgres:15-alpine

ENV POSTGRES_DB=athena
ENV POSTGRES_USER=athena
ENV POSTGRES_PASSWORD=changeme  # Use secrets in production!

VOLUME ["/var/lib/postgresql/data"]
```

### Schema Creation

```bash
# Connect to database
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Run schema initialization
# Tables are created automatically on first application run
# Or manually:
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f schema.sql
```

### Performance Tuning

```sql
-- For production workload
-- Edit /etc/postgresql/15/main/postgresql.conf

-- Memory
shared_buffers = 256MB          # 25% of system RAM
effective_cache_size = 1GB      # 50% of system RAM
work_mem = 50MB

-- Connections
max_connections = 200           # Adjust based on load

-- Query optimization
random_page_cost = 1.1          # For SSD storage

-- Logging
log_min_duration_statement = 1000  # Log queries >1s
log_statement = 'all'
```

### Backup Strategy

```bash
# Daily backup
0 2 * * * pg_dump -h localhost -U postgres athena > /mnt/backups/athena-$(date +\%Y\%m\%d).sql

# Test restore weekly
pg_restore -h localhost -d athena_test /mnt/backups/athena-latest.sql
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy code
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose port (if running MCP server)
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "from athena.core.database import Database; Database().get_health()" || exit 1

# Run application
CMD ["python", "-m", "athena.mcp"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: athena
      POSTGRES_USER: athena
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U athena"]
      interval: 10s
      timeout: 5s
      retries: 5

  athena:
    build: .
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: athena
      DB_USER: athena
      DB_PASSWORD: ${DB_PASSWORD}
      EMBEDDING_PROVIDER: ${EMBEDDING_PROVIDER}
      OLLAMA_HOST: http://ollama:11434
    ports:
      - "5000:5000"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "from athena.core.database import Database; Database().get_health()"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"

volumes:
  postgres_data:
  ollama_data:
```

### Build and Run

```bash
# Build image
docker build -t athena:latest .

# Run container
docker run -d \
  --name athena \
  -e DB_HOST=postgres \
  -e DB_PASSWORD=secret \
  -p 5000:5000 \
  athena:latest

# With docker-compose
docker-compose up -d
```

---

## Kubernetes Deployment

### ConfigMap (Configuration)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: athena-config
  namespace: default
data:
  LOG_LEVEL: "INFO"
  EMBEDDING_PROVIDER: "ollama"
  CACHE_SIZE: "5000"
  DB_MIN_POOL_SIZE: "5"
  DB_MAX_POOL_SIZE: "20"
```

### Secret (Credentials)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: athena-secrets
  namespace: default
type: Opaque
stringData:
  DB_PASSWORD: "your-secure-password"
  ANTHROPIC_API_KEY: "sk-ant-v0-xxxxx"
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: athena
  namespace: default
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
        image: athena:latest
        ports:
        - containerPort: 5000
        env:
        - name: DB_HOST
          value: postgres-service
        - name: DB_PORT
          value: "5432"
        - name: DB_NAME
          value: athena
        - name: DB_USER
          value: athena
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: athena-secrets
              key: DB_PASSWORD
        envFrom:
        - configMapRef:
            name: athena-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 10
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: athena-service
  namespace: default
spec:
  selector:
    app: athena
  type: LoadBalancer
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5000
```

### Deploy

```bash
# Create namespace
kubectl create namespace athena

# Apply configurations
kubectl apply -f configmap.yaml -n athena
kubectl apply -f secret.yaml -n athena
kubectl apply -f deployment.yaml -n athena
kubectl apply -f service.yaml -n athena

# Check status
kubectl get pods -n athena
kubectl logs -f deployment/athena -n athena
```

---

## Monitoring & Health

### Health Check Endpoint

```python
# Available at /health
{
  "status": "healthy",
  "database": "connected",
  "memory_usage": "512MB",
  "response_time": "45ms",
  "version": "0.9.0"
}
```

### Metrics to Monitor

```bash
# CPU usage
top -p <athena-pid>

# Memory usage
ps aux | grep athena | grep -v grep | awk '{print $6}' # KB

# Database connections
psql -d athena -c "SELECT count(*) FROM pg_stat_activity;"

# Request latency
# Monitor /metrics endpoint

# Error rates
# Monitor logs for ERROR level messages
```

### Logging

```bash
# Structured logging to file
docker logs athena > /var/log/athena.log

# Parse logs
grep "ERROR" /var/log/athena.log | tail -20

# Monitor in real-time
tail -f /var/log/athena.log
```

### Alerting

```bash
# Example: Alert if database connection fails
watch -n 60 'psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" || echo "DATABASE CONNECTION FAILED"'

# Example: Alert if memory >2GB
docker stats athena --no-stream | awk 'NR==2 {gsub(/[^0-9.]/,"",$6); if ($6 > 2) print "MEMORY ALERT: " $6}'
```

---

## Scaling

### Horizontal Scaling (Multiple Instances)

```bash
# With docker-compose
docker-compose up -d --scale athena=3

# With Kubernetes
kubectl scale deployment athena --replicas=5

# Load balancer distributes traffic
```

### Vertical Scaling (Larger Instance)

```bash
# Increase resources in Kubernetes
kubectl set resources deployment athena \
  --requests=memory=1Gi,cpu=500m \
  --limits=memory=4Gi,cpu=2000m

# Or in docker with resource limits
docker run -m 4g --cpus="2" athena:latest
```

### Connection Pool Tuning

```bash
# For multiple instances
export DB_MIN_POOL_SIZE=2      # Per instance
export DB_MAX_POOL_SIZE=10     # Per instance
# Total pool = instances * max_pool_size
```

---

## Backup & Recovery

### Automated Backups

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR=/mnt/backups/athena

pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME \
  | gzip > $BACKUP_DIR/athena-$DATE.sql.gz

# Retention policy (keep last 30 days)
find $BACKUP_DIR -name "athena-*.sql.gz" -mtime +30 -delete
```

### Restore from Backup

```bash
# List available backups
ls -la /mnt/backups/athena/

# Restore database
gunzip < /mnt/backups/athena/athena-20250113.sql.gz | psql -h $DB_HOST -U $DB_USER -d athena

# Verify restore
psql -h $DB_HOST -U $DB_USER -d athena -c "SELECT count(*) FROM episodic_events;"
```

### Point-in-Time Recovery

```bash
# PostgreSQL provides PITR with archiving enabled
# This allows recovery to any point in time

# Configure in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /backup/wal_archive/%f && cp %p /backup/wal_archive/%f'
```

---

## Rollback Procedure

If deployment fails:

```bash
# Docker
docker stop athena
docker rm athena
docker run -d --name athena athena:previous-version

# Kubernetes
kubectl rollout undo deployment/athena
kubectl rollout status deployment/athena

# Database
# If schema migration failed
psql -d athena -c "DROP TABLE new_table;"
# Or restore from backup
gunzip < /mnt/backups/athena/athena-backup.sql.gz | psql -d athena
```

---

## Production Checklist

- [ ] Database configured with backups
- [ ] Secrets stored in secrets manager
- [ ] Health checks configured
- [ ] Monitoring and alerting active
- [ ] Load balancer configured
- [ ] SSL/TLS certificates installed
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Disaster recovery plan documented
- [ ] Team trained on runbooks

---

## See Also

- [CONFIGURATION.md](./CONFIGURATION.md) - Environment setup
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues
- [API_REFERENCE.md](./API_REFERENCE.md) - API documentation

---

**Version**: 1.0
**Last Updated**: November 13, 2025
**Status**: Production Ready
