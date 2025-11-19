# Athena Dashboard

Real-time web dashboard for monitoring and managing the Athena Memory System.

## Overview

The Athena Dashboard provides a comprehensive web interface for:

- **8 Memory Layers**: Episodic, Semantic, Procedural, Prospective, Knowledge Graph, Meta-Memory, Consolidation, and Planning
- **60+ Modules**: Full coverage of all Athena subsystems
- **Real-time Monitoring**: Live statistics and WebSocket updates
- **Visual Analytics**: ECharts for time-series data, Cytoscape.js for knowledge graphs
- **REST API**: FastAPI backend with ~50 endpoints

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Next.js 15 Frontend (Port 3000)                │
│  - React 19, TypeScript, Tailwind CSS           │
│  - ECharts, Cytoscape.js, TanStack Query        │
└───────────────┬─────────────────────────────────┘
                │
                │ HTTP/WebSocket
                ↓
┌─────────────────────────────────────────────────┐
│  FastAPI Backend (Port 8000)                    │
│  - Async Python, Pydantic, WebSocket support    │
│  - Imports Athena operations directly           │
└───────────────┬─────────────────────────────────┘
                │
                │ Direct imports
                ↓
┌─────────────────────────────────────────────────┐
│  Athena Memory System                           │
│  - src/athena/*/operations.py                   │
│  - PostgreSQL database                          │
└─────────────────────────────────────────────────┘
```

## Tech Stack

### Frontend
- **Framework**: Next.js 15.0 (App Router, Turbopack)
- **Language**: TypeScript 5.6
- **State**: Zustand 5.0 (global), TanStack Query 5.0 (server)
- **UI**: Tailwind CSS 3.4, shadcn/ui components, Lucide icons
- **Charts**: Apache ECharts 5.5 (10M+ data points)
- **Graph**: Cytoscape.js 3.30 (10,000+ nodes)

### Backend
- **Framework**: FastAPI 0.115 (3,000+ RPS)
- **Language**: Python 3.11+
- **Async**: uvicorn with WebSocket support
- **Validation**: Pydantic 2.9

### Deployment
- **Process Manager**: systemd services
- **Reverse Proxy**: Caddy (optional, for HTTPS)
- **Database**: PostgreSQL 13+ (Athena's existing database)

## Quick Start

### Prerequisites

```bash
# Python 3.11+ with pip
python3 --version

# Node.js 18+ with npm
node --version

# PostgreSQL 13+ (should already be running for Athena)
psql --version

# Athena must be installed and initialized
```

### Backend Setup

```bash
# Navigate to backend directory
cd /home/user/athena/dashboard/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Athena in development mode (if not already done)
pip install -e ../../

# Test the backend
python main.py

# Should see:
# 🚀 Starting Athena Dashboard API...
# ✅ Athena initialized successfully
# 🌐 API available at http://localhost:8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd /home/user/athena/dashboard/frontend

# Install dependencies
npm install

# Run in development mode
npm run dev

# Should see:
# ▲ Next.js 15.0.3
# - Local: http://localhost:3000
```

### Access the Dashboard

Open your browser to:
- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **Backend Health**: http://localhost:8000/health

## Development

### Backend Development

```bash
cd /home/user/athena/dashboard/backend
source venv/bin/activate

# Run with auto-reload
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# View logs
tail -f /var/log/athena-dashboard-backend.log
```

### Frontend Development

```bash
cd /home/user/athena/dashboard/frontend

# Development server (hot reload)
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build

# Preview production build
npm run start
```

## Production Deployment

### 1. Build Frontend

```bash
cd /home/user/athena/dashboard/frontend
npm run build
```

### 2. Setup Virtual Environment (Backend)

```bash
cd /home/user/athena/dashboard/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e ../../
```

### 3. Install systemd Services

```bash
# Copy service files
sudo cp /home/user/athena/dashboard/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable athena-dashboard-backend
sudo systemctl enable athena-dashboard-frontend

# Start services
sudo systemctl start athena-dashboard-backend
sudo systemctl start athena-dashboard-frontend

# Check status
sudo systemctl status athena-dashboard-backend
sudo systemctl status athena-dashboard-frontend
```

### 4. View Logs

```bash
# Backend logs
sudo journalctl -u athena-dashboard-backend -f

# Frontend logs
sudo journalctl -u athena-dashboard-frontend -f

# Both services
sudo journalctl -u athena-dashboard-* -f
```

### 5. (Optional) Setup Caddy Reverse Proxy

If you want HTTPS and a custom domain:

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# Create Caddyfile
sudo nano /etc/caddy/Caddyfile
```

Add:

```
athena.yourdomain.com {
    reverse_proxy localhost:3000
}
```

Restart Caddy:

```bash
sudo systemctl restart caddy
```

## API Endpoints

### System
- `GET /health` - Health check
- `GET /api/system/status` - System-wide status

### Episodic Memory (Layer 1)
- `GET /api/episodic/statistics` - Statistics
- `GET /api/episodic/events` - List events
- `GET /api/episodic/recent` - Recent events

### Semantic Memory (Layer 2)
- `GET /api/semantic/search` - Search memories

### Procedural Memory (Layer 3)
- `GET /api/procedural/statistics` - Statistics
- `GET /api/procedural/procedures` - List procedures

### Prospective Memory (Layer 4)
- `GET /api/prospective/statistics` - Statistics
- `GET /api/prospective/tasks` - List tasks

### Knowledge Graph (Layer 5)
- `GET /api/graph/statistics` - Statistics
- `GET /api/graph/entities` - List entities
- `GET /api/graph/entities/{id}/related` - Related entities

### Meta-Memory (Layer 6)
- `GET /api/meta/statistics` - Statistics

### Consolidation (Layer 7)
- `GET /api/consolidation/statistics` - Statistics
- `GET /api/consolidation/history` - Consolidation runs

### Planning (Layer 8)
- `GET /api/planning/statistics` - Statistics
- `GET /api/planning/plans` - List plans

### WebSocket
- `WS /ws/live-updates` - Real-time updates

## Project Structure

```
dashboard/
├── backend/                    # FastAPI backend
│   ├── main.py                # Main application
│   ├── requirements.txt       # Python dependencies
│   └── venv/                  # Virtual environment
│
├── frontend/                   # Next.js frontend
│   ├── src/
│   │   ├── app/               # Next.js App Router
│   │   │   ├── layout.tsx     # Root layout
│   │   │   ├── page.tsx       # Home/overview page
│   │   │   ├── episodic/      # Episodic memory page
│   │   │   ├── graph/         # Knowledge graph page
│   │   │   └── ...            # Other layer pages
│   │   ├── components/        # React components
│   │   │   ├── layout/        # Layout components
│   │   │   ├── charts/        # Chart components
│   │   │   ├── graph/         # Graph visualization
│   │   │   └── ui/            # UI components
│   │   ├── lib/               # Utilities
│   │   │   ├── api.ts         # API client
│   │   │   └── utils.ts       # Helper functions
│   │   ├── hooks/             # Custom React hooks
│   │   ├── stores/            # Zustand stores
│   │   └── types/             # TypeScript types
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   └── tailwind.config.ts
│
└── systemd/                    # Service files
    ├── athena-dashboard-backend.service
    └── athena-dashboard-frontend.service
```

## Troubleshooting

### Backend won't start

```bash
# Check if Athena is initialized
cd /home/user/athena
python -c "import asyncio; from src.athena import initialize_athena; asyncio.run(initialize_athena())"

# Check PostgreSQL
psql -h localhost -U postgres -d athena -c "SELECT 1"

# Check logs
sudo journalctl -u athena-dashboard-backend -n 50
```

### Frontend build fails

```bash
# Clear cache and reinstall
rm -rf node_modules .next
npm install
npm run build
```

### Port conflicts

```bash
# Check what's using port 8000
sudo lsof -i :8000

# Check what's using port 3000
sudo lsof -i :3000

# Change ports in service files if needed
```

### WebSocket connection fails

- Ensure backend is running on port 8000
- Check CORS settings in `backend/main.py`
- Verify WebSocket endpoint is accessible: `ws://localhost:8000/ws/live-updates`

## Performance

Expected performance (on modern hardware):

- **Backend**: 3,000+ requests/second (FastAPI benchmark)
- **Frontend**: First paint < 1s, time to interactive < 2s
- **Charts**: Handle 10M+ data points (ECharts progressive rendering)
- **Graph**: Render 10,000+ nodes (Cytoscape.js with layout optimization)
- **WebSocket**: 3,200+ concurrent connections

## Contributing

When adding new features:

1. **Backend**: Add endpoints to `backend/main.py`, import from Athena operations
2. **Frontend**: Create API functions in `src/lib/api.ts`, add pages in `src/app/`
3. **Test**: Run both backend and frontend in development mode
4. **Document**: Update this README with new endpoints

## License

MIT License - See main Athena repository for details.

## Support

For issues or questions:
- GitHub Issues: https://github.com/shawkridge/athena/issues
- Documentation: See `/home/user/athena/docs/`
