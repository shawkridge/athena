# Athena Monitoring Dashboard

Real-time web-based monitoring dashboard for the Athena memory system. Provides complete visibility into hook execution, memory health, cognitive load, task tracking, and learning analytics.

**Status**: Phase 1 - Backend Implementation (Complete)
**Next**: Phase 2 - WebSocket Integration & Phase 3 - React Frontend

---

## Features

### 📊 Dashboard Pages (Planned)

- **Overview Dashboard** - System health at a glance
- **Hook Execution Monitor** - Real-time hook performance tracking
- **Memory System Health** - Quality metrics and consolidation status
- **Cognitive Load Monitor** - Working memory visualization
- **Projects & Tasks** - Goal and task tracking
- **Learning Analytics** - Strategy effectiveness and patterns
- **Advanced Analysis** - Critical path and anomalies

### 🎯 Metrics Tracked

- **Hook Execution**: Latency, success rate, agent invocations
- **Memory Health**: Quality score, consolidation progress, gaps
- **Cognitive Load**: Current load (0-7), capacity utilization
- **Task Metrics**: Completion rates, milestones, blockers
- **Learning**: Strategy effectiveness, procedure reuse, gaps resolved

---

## Architecture

### Backend Stack

```
FastAPI 0.104+ (REST + WebSocket API)
├── SQLAlchemy (Database ORM)
├── Pydantic (Data validation)
└── Redis (Caching layer)
```

### Services

- **DataLoader**: Queries Athena memory database (SQLite)
- **CacheManager**: Redis-backed caching with in-memory fallback
- **MetricsAggregator**: Computes all dashboard metrics

### Data Sources

- Athena memory database: `~/.athena/memory.db`
- Episodic events (tool executions, consolidations)
- Semantic memory (quality metrics, procedures)
- Working memory (cognitive load)
- Knowledge graph (domains, gaps)

---

## Getting Started

### Prerequisites

- Python 3.10+
- Redis (optional, falls back to in-memory cache)
- Docker & Docker Compose (optional)

### Installation

#### Option 1: Local Development

```bash
# Clone and navigate to directory
cd athena_dashboard/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example .env

# Run development server
python app.py
```

Server runs on `http://localhost:8000`

#### Option 2: Docker Compose

```bash
# From athena_dashboard directory
docker-compose up -d

# Logs
docker-compose logs -f backend

# Stop
docker-compose down
```

Services:
- Backend: `http://localhost:8000`
- Redis: `localhost:6379`
- PgAdmin: `http://localhost:5050`

---

## API Endpoints

### Health

```
GET  /health                    Health check
GET  /info                      Application info
```

### Dashboard

```
GET  /api/dashboard/overview    Complete overview with all metrics
```

### Hooks

```
GET  /api/hooks/status          Status of all hooks
GET  /api/hooks/{name}/metrics  Metrics for specific hook
GET  /api/hooks/{name}/history  Historical data for hook
```

### Memory

```
GET  /api/memory/health         Memory system health
GET  /api/memory/consolidation  Consolidation progress
GET  /api/memory/gaps           Knowledge gaps identified
GET  /api/memory/domains        Domain coverage analysis
```

### Cognitive Load

```
GET  /api/load/current          Current load (0-7 items)
GET  /api/load/history          Historical load data
GET  /api/load/trend            Load trend analysis
```

### Tasks & Projects

```
GET  /api/projects              All projects with status
GET  /api/projects/{id}         Project details
GET  /api/goals                 Active goals
GET  /api/tasks                 Active tasks
```

### Learning

```
GET  /api/learning/strategies   Strategy effectiveness
GET  /api/learning/procedures   Top procedures by effectiveness
GET  /api/learning/trends       Learning metric trends
```

### Analysis

```
GET  /api/analysis/critical-path     Critical path analysis
GET  /api/analysis/bottlenecks       Performance bottlenecks
GET  /api/analysis/anomalies         Detected anomalies
```

---

## WebSocket Endpoints (Phase 2)

Real-time updates via WebSocket:

```
WS  /ws/live/hooks              Real-time hook execution
WS  /ws/live/memory             Real-time memory metrics
WS  /ws/live/load               Real-time load updates
WS  /ws/live/tasks              Real-time task updates
WS  /ws/notifications           System alerts
```

---

## Configuration

Environment variables in `.env`:

```env
# Server
DEBUG=False
HOST=0.0.0.0
PORT=8000

# Database
ATHENA_DB_PATH=${HOME}/.athena/memory.db
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=True

# API
CORS_ORIGINS=["http://localhost:3000"]

# Logging
LOG_LEVEL=INFO
```

---

## Testing

Run unit tests:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_api.py -v

# With coverage
pytest --cov=. tests/

# Watch mode
ptw tests/
```

Tests include:
- Health endpoint verification
- API endpoint response validation
- Database connectivity
- Cache layer functionality
- Error handling

---

## Development

### Code Structure

```
backend/
├── app.py                 Main FastAPI application
├── config.py              Configuration management
├── models/
│   ├── __init__.py
│   └── metrics.py         Pydantic response models
├── services/
│   ├── __init__.py
│   ├── data_loader.py     Database queries
│   ├── cache_manager.py   Caching layer
│   └── metrics_aggregator.py  Metric computation
├── routes/                Route modules (Phase 2)
├── tests/
│   ├── __init__.py
│   └── test_api.py        API tests
├── requirements.txt       Dependencies
└── Dockerfile            Container definition
```

### Adding New Endpoints

1. Add Pydantic model in `models/metrics.py`
2. Add query method in `services/data_loader.py`
3. Add computation method in `services/metrics_aggregator.py`
4. Add route in `app.py` or new file in `routes/`
5. Add tests in `tests/test_api.py`

### Running Linting & Formatting

```bash
# Format with Black
black .

# Check with Ruff
ruff check .

# Type checking
mypy .
```

---

## Performance

### Caching Strategy

- **Overview**: 30 second cache
- **Hook Metrics**: 60 second cache
- **Memory Metrics**: 60 second cache
- **Other endpoints**: No cache (computed per request)

### Optimization Tips

1. **Redis**: Install Redis for persistent caching
2. **Database Indexing**: Ensure Athena database has indexes on frequently queried columns
3. **Connection Pooling**: SQLAlchemy uses connection pooling by default
4. **Batch Queries**: DataLoader batches similar queries

---

## Deployment

### Docker

```bash
# Build image
docker build -t athena-dashboard-backend ./backend

# Run container
docker run -p 8000:8000 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -v ~/.athena:/athena/.athena:ro \
  athena-dashboard-backend
```

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Use production ASGI server (Gunicorn)
- [ ] Enable Redis caching
- [ ] Set up log aggregation
- [ ] Configure database backups
- [ ] Set up monitoring/alerting
- [ ] Use HTTPS in production
- [ ] Set resource limits (CPU, memory)
- [ ] Configure health checks

---

## Troubleshooting

### Backend won't start

```bash
# Check Python version (3.10+)
python --version

# Verify dependencies
pip list | grep fastapi

# Check port availability
lsof -i :8000
```

### Redis connection error

```bash
# Redis not required - backend falls back to in-memory cache
# But to use Redis:
redis-cli ping  # Should return PONG
```

### Database not found

```bash
# Check Athena database path
ls -la ~/.athena/memory.db

# Update ATHENA_DB_PATH in .env if different location
```

---

## Phase 2: WebSocket & Real-time Updates

Upcoming features:

- WebSocket connections for live data
- Real-time metric updates
- Event streaming
- Notification system
- Auto-refresh dashboard

---

## Phase 3: React Frontend

Upcoming features:

- Interactive dashboard UI
- Real-time charts (Plotly/Chart.js)
- Filtering and drilling down
- Customizable dashboards
- Mobile-responsive design
- Dark mode

---

## Contributing

1. Follow code style with `black` and `ruff`
2. Add tests for new endpoints
3. Update docstrings
4. Run full test suite before committing

---

## License

Part of Athena memory system project.

---

## Support

- **Documentation**: `/MONITORING_DASHBOARD_PLAN.md`
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Athena Project**: `/home/user/.work/athena`

---

**Status**: Phase 1 Complete ✅
**Next Steps**: Phase 2 WebSocket Integration → Phase 3 React Frontend
**Estimated Timeline**: 3 weeks total
