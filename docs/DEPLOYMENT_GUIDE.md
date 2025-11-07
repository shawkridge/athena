# Athena HTTP Migration - Deployment Guide (Phase 4)

## Overview

This guide describes how to deploy the complete Athena system with HTTP service integration, dashboard backend, and supporting services.

## Architecture

```
Claude Code / Hooks
    ↓
Athena HTTP Service (Port 3000)
    ↓
Memory Database (SQLite)

Dashboard Web App
    ↓
Dashboard Backend (Port 8000)
    ↓
Athena HTTP Service (Port 3000)

Supporting Services:
- Redis (Port 6379) - Caching
- Ollama (Port 11434) - Local LLM
- pgAdmin (Port 5050) - Database management (optional)
```

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB free disk space (for Ollama)
- 4GB+ RAM recommended
- Linux/Mac/Windows with Docker Desktop

## Quick Start

### 1. Build Images

```bash
cd /home/user/.work/athena
docker-compose build
```

This builds:
- `athena-athena` - Athena HTTP service (1.5GB)
- `athena-backend` - Dashboard backend (635MB)
- Uses pre-built `redis:7-alpine`
- Pulls `ollama/ollama` (1.9GB - may take 10+ minutes)

### 2. Start Services

```bash
docker-compose up -d
```

Services will start in this order:
1. **redis** (immediate) - In-memory cache
2. **ollama** (1-2 min) - LLM model loading
3. **athena** (30 seconds) - HTTP API server
4. **backend** (30 seconds) - Dashboard API server

### 3. Verify Services

```bash
# Check all services running
docker-compose ps

# View service logs
docker-compose logs -f athena      # Athena service
docker-compose logs -f backend     # Dashboard backend
docker-compose logs -f ollama      # LLM service

# Check service health
curl http://localhost:3000/health  # Athena
curl http://localhost:8000/health  # Dashboard
```

### 4. Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Athena** | http://localhost:3000 | Memory system HTTP API |
| **Athena Docs** | http://localhost:3000/docs | Swagger documentation |
| **Dashboard** | http://localhost:8000 | Web dashboard (if available) |
| **Dashboard Docs** | http://localhost:8000/docs | Dashboard API documentation |
| **Ollama** | http://localhost:11434 | LLM service API |
| **Redis** | localhost:6379 | Cache service |
| **pgAdmin** | http://localhost:5050 | Database management UI |

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Athena HTTP Service
ATHENA_HOST=0.0.0.0
ATHENA_PORT=3000
ATHENA_LOG_LEVEL=INFO
ATHENA_DATABASE_URL=sqlite:///data/memory.db

# Dashboard Backend
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8000
ATHENA_HTTP_URL=http://athena:3000
USE_ATHENA_HTTP=true
REDIS_URL=redis://redis:6379

# Ollama
OLLAMA_HOST=http://ollama:11434

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
```

### Persistent Data

Services store data in Docker volumes:

```bash
# View volumes
docker volume ls | grep athena

# Backup database
docker run --rm -v athena_data:/data -v $(pwd):/backup \
  ubuntu tar cvf /backup/athena_backup.tar /data

# Restore database
docker run --rm -v athena_data:/data -v $(pwd):/backup \
  ubuntu tar xvf /backup/athena_backup.tar -C /
```

## Testing

### Smoke Tests

Run basic functionality tests:

```bash
bash SMOKE_TESTS.sh
```

Tests cover:
- Service health endpoints
- API documentation endpoints
- Inter-service communication

### Manual Testing

**Test Athena HTTP API:**

```bash
# Health check
curl http://localhost:3000/health

# Memory operations
curl -X POST http://localhost:3000/memory/remember \
  -H "Content-Type: application/json" \
  -d '{"content": "test memory", "memory_type": "fact"}'

# Query memories
curl http://localhost:3000/memory/search?query=test
```

**Test Dashboard Backend:**

```bash
# Health check
curl http://localhost:8000/health

# View API documentation
curl http://localhost:8000/openapi.json
```

**Test Inter-service Communication:**

```bash
# From dashboard container
docker exec athena-backend curl http://athena:3000/health

# From Athena container
docker exec athena-http curl http://redis:6379/ping
```

## Common Tasks

### View Logs

```bash
# All services
docker-compose logs

# Specific service with 50 lines
docker-compose logs --tail 50 athena

# Follow real-time logs
docker-compose logs -f athena backend

# Filter by time (last 10 minutes)
docker-compose logs --since 10m athena
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart athena

# Force restart (rebuild if needed)
docker-compose up -d --force-recreate athena
```

### Stop Services

```bash
# Stop all services (preserve data)
docker-compose stop

# Stop specific service
docker-compose stop athena

# Stop and remove containers (preserve volumes)
docker-compose down

# Stop and remove everything (including volumes)
docker-compose down -v
```

### Update Services

```bash
# Rebuild images
docker-compose build

# Start with new images
docker-compose up -d

# Or combined
docker-compose up -d --build
```

## Troubleshooting

### Services won't start

**Check logs:**
```bash
docker-compose logs athena
docker-compose logs backend
```

**Common issues:**
- Port conflicts: Check if ports 3000, 8000, 11434 are in use
- Memory: Ollama requires significant RAM
- Disk space: Need 4GB+ for Ollama

**Solution:**
```bash
# Kill other services on ports
lsof -i :3000
kill -9 <PID>

# Free up space
docker system prune -a
```

### Services crash on startup

**Check health:**
```bash
docker-compose ps
# STATUS shows: "Exited (1)" or similar
```

**Debug:**
```bash
# Run service in foreground to see errors
docker-compose run --rm athena

# Check application logs
docker-compose logs athena | tail -100
```

**Restart from scratch:**
```bash
docker-compose down -v
docker-compose up -d
```

### Slow performance

**Check resource usage:**
```bash
docker stats

# Monitor specific service
docker stats athena-backend
```

**Optimize:**
```bash
# Increase Docker memory allocation
# (Docker Desktop settings)

# Reduce unnecessary services
# (Comment out in docker-compose.yml)
```

### Connection timeouts

**Test connectivity:**
```bash
# From host
curl -v http://localhost:3000/health

# From inside container
docker exec athena-backend curl http://athena:3000/health

# Check network
docker network ls
docker network inspect athena_default
```

## Production Deployment

### Security Considerations

1. **Use reverse proxy** (Nginx, Traefik)
   ```bash
   # Don't expose ports directly
   # Hide behind HTTPS proxy
   ```

2. **Set environment variables**
   ```bash
   # Use .env for secrets
   ATHENA_API_KEY=<secure-key>
   OLLAMA_API_KEY=<secure-key>
   ```

3. **Enable authentication**
   ```bash
   # For Dashboard backend
   USE_AUTHENTICATION=true
   AUTH_TOKEN_SECRET=<secure-token>
   ```

4. **Restrict network access**
   ```bash
   # Only expose necessary ports
   # Use firewall rules
   ```

### Scaling

**Horizontal scaling:**
```bash
# Multiple Athena instances
services:
  athena:
    deploy:
      replicas: 3

  athena-2:
    image: athena-athena
    ports:
      - "3001:3000"

  athena-3:
    image: athena-athena
    ports:
      - "3002:3000"
```

**Load balancing:**
```bash
# Use Nginx as reverse proxy
# Route to http://athena:3000,3001,3002
```

### Monitoring

**Health checks:**
```bash
# Continuous monitoring
while true; do
  curl -f http://localhost:3000/health || \
    docker-compose restart athena
  sleep 30
done
```

**Metrics:**
```bash
# Docker stats
docker stats --no-stream

# Application metrics
curl http://localhost:3000/metrics
```

### Backup & Recovery

**Daily backup:**
```bash
#!/bin/bash
BACKUP_DIR="/backups/athena"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
docker run --rm -v athena_data:/data \
  -v $BACKUP_DIR:/backup \
  ubuntu tar czf /backup/memory_$DATE.tar.gz /data

# Keep last 7 days
find $BACKUP_DIR -name "memory_*.tar.gz" -mtime +7 -delete
```

**Restore from backup:**
```bash
# Stop services
docker-compose stop

# Restore database
docker run --rm -v athena_data:/data \
  -v /backups/athena:/backup \
  ubuntu tar xzf /backup/memory_20231106.tar.gz -C /

# Restart services
docker-compose up -d
```

## Performance Tuning

### Athena HTTP Service

```yaml
# docker-compose.yml
environment:
  PYTHONUNBUFFERED: 1
  WORKERS: 4              # Gunicorn workers
  WORKER_CLASS: uvicorn   # Async workers
  TIMEOUT: 120            # Request timeout
```

### Redis Caching

```bash
# Increase Redis memory
# docker-compose.yml
command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### Database Optimization

```bash
# WAL mode for SQLite
SQLITE_PRAGMA: "journal_mode=WAL;synchronous=NORMAL"
```

## Maintenance

### Regular Tasks

**Weekly:**
- Review logs for errors
- Check disk usage
- Verify backups completed

**Monthly:**
- Clean up old data
- Update Docker images
- Performance analysis

**Quarterly:**
- Security audit
- Dependency updates
- Capacity planning

### Clean Up

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune

# Full cleanup
docker system prune -a --volumes
```

## Support

### Debug Information

When reporting issues, provide:

```bash
# System info
docker-compose ps
docker-compose logs --tail 100

# Configuration
cat docker-compose.yml
env | grep ATHENA

# Resource usage
docker stats --no-stream
df -h
free -h
```

### Useful Commands

```bash
# Interactive shell in container
docker exec -it athena-http bash

# Check container processes
docker top athena-http

# Inspect container
docker inspect athena-http

# View container events
docker events --filter container=athena-http

# Stress test service
ab -n 1000 -c 10 http://localhost:3000/health
```

## Next Steps

1. ✅ Run smoke tests (`bash SMOKE_TESTS.sh`)
2. ✅ Access Athena API docs (http://localhost:3000/docs)
3. ✅ Access Dashboard (if available)
4. ✅ Configure environment variables
5. ✅ Set up monitoring
6. ✅ Configure backups
7. ✅ Plan production deployment

## Additional Resources

- Athena Architecture: See `/ARCHITECTURE.md`
- Phase 1-3 Docs: See `/PHASE*_HTTP_COMPLETION.md`
- API Reference: http://localhost:3000/docs (when running)

---

**Status:** Phase 4 Docker Stack - Deployment Guide
**Version:** 1.0
**Last Updated:** 2025-11-06
