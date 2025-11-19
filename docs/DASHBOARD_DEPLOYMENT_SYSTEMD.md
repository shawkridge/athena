# Athena Dashboard - Systemd Deployment Guide

**Date:** November 18, 2025
**Version:** 1.0
**Deployment Method:** systemd services (no Docker)

---

## Overview

This guide covers deploying the Athena dashboard as native systemd services on Linux. This approach is ideal for:

✅ Single-machine deployments
✅ Direct system integration
✅ Lower resource overhead (no containerization)
✅ Simpler process management
✅ Better for local development and production

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Reverse Proxy (Caddy or Nginx)          │
│              http://localhost:80                 │
└─────────────────────────────────────────────────┘
           │                           │
           ↓                           ↓
┌──────────────────────┐    ┌──────────────────────┐
│  Frontend (Next.js)  │    │  Backend (FastAPI)   │
│   localhost:3000     │    │   localhost:8000     │
│  systemd service     │    │  systemd service     │
└──────────────────────┘    └──────────────────────┘
                                      │
                                      ↓
                       ┌──────────────────────────┐
                       │  PostgreSQL (existing)   │
                       │    localhost:5432        │
                       │   systemd service        │
                       └──────────────────────────┘
```

---

## Prerequisites

```bash
# System requirements
- Ubuntu 20.04+ or similar Linux distribution
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ (already installed for Athena)
- systemd (standard on most Linux systems)

# Install Node.js 20 (if not already installed)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install pnpm
curl -fsSL https://get.pnpm.io/install.sh | sh -

# Install Caddy (recommended) or Nginx
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

---

## 1. Project Structure

```
/home/user/athena/
├── dashboard/
│   ├── frontend/          # Next.js app
│   │   ├── src/
│   │   ├── public/
│   │   ├── package.json
│   │   ├── next.config.js
│   │   └── .next/        # Build output
│   │
│   ├── backend/           # FastAPI app
│   │   ├── main.py
│   │   ├── api/
│   │   ├── requirements.txt
│   │   └── venv/         # Python virtual environment
│   │
│   └── systemd/           # Service files
│       ├── athena-dashboard-frontend.service
│       ├── athena-dashboard-backend.service
│       └── athena-dashboard-caddy.service
│
└── src/athena/            # Existing Athena code
```

---

## 2. Backend Setup (FastAPI)

### 2.1 Create Backend Directory

```bash
cd /home/user/athena
mkdir -p dashboard/backend
cd dashboard/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn[standard] pydantic python-multipart
```

### 2.2 Create Main Application

**`/home/user/athena/dashboard/backend/main.py`**

```python
"""Athena Dashboard API - FastAPI Backend"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sys
from pathlib import Path

# Add Athena to Python path
athena_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(athena_path))

# Import Athena operations
from athena import initialize_athena
from athena.episodic.operations import recall, get_statistics as episodic_stats
from athena.memory.operations import search
from athena.procedural.operations import list_procedures
from athena.prospective.operations import list_tasks, get_active_tasks
from athena.graph.operations import search_entities, get_communities
from athena.meta.operations import get_statistics as meta_stats
from athena.consolidation.operations import get_consolidation_history

app = FastAPI(
    title="Athena Dashboard API",
    description="Real-time API for Athena Memory System Dashboard",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Athena on startup
@app.on_event("startup")
async def startup_event():
    """Initialize Athena memory system."""
    print("Initializing Athena memory system...")
    success = await initialize_athena()
    if success:
        print("✅ Athena initialized successfully")
    else:
        print("❌ Failed to initialize Athena")

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "athena-dashboard-api"}

# Statistics endpoints
@app.get("/api/statistics/episodic")
async def get_episodic_statistics():
    """Get episodic memory statistics."""
    return await episodic_stats()

@app.get("/api/statistics/meta")
async def get_meta_statistics():
    """Get meta-memory statistics."""
    return await meta_stats()

@app.get("/api/statistics/all")
async def get_all_statistics():
    """Get statistics from all layers."""
    return {
        "episodic": await episodic_stats(),
        "meta": await meta_stats(),
    }

# Episodic memory endpoints
@app.get("/api/episodic/events")
async def get_episodic_events(
    limit: int = 100,
    offset: int = 0,
    session_id: str | None = None
):
    """Get episodic events with pagination."""
    events = await recall(
        query="*",
        limit=limit + offset,
        session_id=session_id
    )

    # Convert to dict for JSON serialization
    events_data = [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "event_type": e.event_type,
            "content": e.content,
            "importance_score": e.importance_score,
            "session_id": e.session_id,
        }
        for e in events[offset:offset+limit]
    ]

    return {
        "events": events_data,
        "total": len(events),
        "limit": limit,
        "offset": offset
    }

# Procedural memory endpoints
@app.get("/api/procedural/procedures")
async def get_procedures(limit: int = 100):
    """Get procedures."""
    procedures = await list_procedures(limit=limit)

    return {
        "procedures": [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "success_rate": p.success_rate,
                "usage_count": p.usage_count,
            }
            for p in procedures
        ],
        "total": len(procedures)
    }

# Prospective memory endpoints
@app.get("/api/prospective/tasks")
async def get_tasks(status: str | None = None, limit: int = 100):
    """Get tasks."""
    if status == "active":
        tasks = await get_active_tasks(limit=limit)
    else:
        tasks = await list_tasks(limit=limit)

    return {
        "tasks": [
            {
                "id": t.id,
                "content": t.content,
                "status": t.status,
                "priority": t.priority,
                "phase": t.phase,
            }
            for t in tasks
        ],
        "total": len(tasks)
    }

# Knowledge graph endpoints
@app.get("/api/graph/entities")
async def get_entities(entity_type: str | None = None, limit: int = 100):
    """Get graph entities."""
    entities = await search_entities(
        query="*",
        entity_type=entity_type,
        limit=limit
    )

    return {
        "entities": [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
            }
            for e in entities
        ],
        "total": len(entities)
    }

# WebSocket for real-time updates
class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/live-updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)

    try:
        while True:
            # Send statistics every 10 seconds
            stats = await episodic_stats()
            await websocket.send_json({
                "type": "statistics_update",
                "layer": "episodic",
                "data": stats
            })
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

### 2.3 Create Requirements File

**`/home/user/athena/dashboard/backend/requirements.txt`**

```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.9.0
python-multipart==0.0.12
```

---

## 3. Frontend Setup (Next.js)

### 3.1 Create Next.js App

```bash
cd /home/user/athena/dashboard
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir

cd frontend
pnpm install
```

### 3.2 Configure API Connection

**`/home/user/athena/dashboard/frontend/.env.local`**

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### 3.3 Create Basic Dashboard Page

**`/home/user/athena/dashboard/frontend/app/page.tsx`**

```typescript
'use client';

import { useEffect, useState } from 'react';

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Fetch initial statistics
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/statistics/all`)
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error('Failed to fetch stats:', err));

    // Connect to WebSocket
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL}/ws/live-updates`);

    ws.onopen = () => setIsConnected(true);
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'statistics_update') {
        setStats((prev: any) => ({
          ...prev,
          [message.layer]: message.data
        }));
      }
    };
    ws.onclose = () => setIsConnected(false);

    return () => ws.close();
  }, []);

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-4xl font-bold mb-8">Athena Dashboard</h1>

      <div className="mb-4">
        Status: {isConnected ? (
          <span className="text-green-600">● Connected</span>
        ) : (
          <span className="text-red-600">● Disconnected</span>
        )}
      </div>

      {stats && (
        <div className="grid grid-cols-2 gap-4">
          <div className="p-6 border rounded-lg">
            <h2 className="text-xl font-semibold mb-2">Episodic Memory</h2>
            <p className="text-3xl">{stats.episodic?.total_events || 0}</p>
            <p className="text-sm text-gray-600">Total Events</p>
          </div>

          <div className="p-6 border rounded-lg">
            <h2 className="text-xl font-semibold mb-2">Quality Score</h2>
            <p className="text-3xl">{(stats.episodic?.quality_score || 0).toFixed(2)}</p>
            <p className="text-sm text-gray-600">Average Quality</p>
          </div>
        </div>
      )}
    </main>
  );
}
```

### 3.4 Build for Production

```bash
cd /home/user/athena/dashboard/frontend
pnpm build
```

---

## 4. Systemd Service Files

### 4.1 Backend Service

**`/etc/systemd/system/athena-dashboard-backend.service`**

```ini
[Unit]
Description=Athena Dashboard Backend (FastAPI)
After=postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/home/user/athena/dashboard/backend

# Environment variables
Environment="PATH=/home/user/athena/dashboard/backend/venv/bin"
Environment="PYTHONPATH=/home/user/athena/src"
Environment="DB_HOST=localhost"
Environment="DB_PORT=5432"
Environment="DB_NAME=athena"
Environment="DB_USER=postgres"
Environment="DB_PASSWORD=postgres"

# Run command
ExecStart=/home/user/athena/dashboard/backend/venv/bin/uvicorn main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --log-level info

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=athena-backend

[Install]
WantedBy=multi-user.target
```

### 4.2 Frontend Service (Production)

**`/etc/systemd/system/athena-dashboard-frontend.service`**

```ini
[Unit]
Description=Athena Dashboard Frontend (Next.js)
After=network.target

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/home/user/athena/dashboard/frontend

# Environment
Environment="PATH=/home/user/.local/share/pnpm:/usr/bin:/bin"
Environment="NODE_ENV=production"
Environment="PORT=3000"
Environment="HOSTNAME=127.0.0.1"

# Run command (production mode)
ExecStart=/home/user/.local/share/pnpm/pnpm start

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=athena-frontend

[Install]
WantedBy=multi-user.target
```

### 4.3 Frontend Service (Development - Alternative)

**`/etc/systemd/system/athena-dashboard-frontend-dev.service`**

```ini
[Unit]
Description=Athena Dashboard Frontend (Next.js Dev Mode)
After=network.target

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/home/user/athena/dashboard/frontend

# Environment
Environment="PATH=/home/user/.local/share/pnpm:/usr/bin:/bin"
Environment="NODE_ENV=development"

# Run command (development mode with hot reload)
ExecStart=/home/user/.local/share/pnpm/pnpm dev

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=athena-frontend-dev

[Install]
WantedBy=multi-user.target
```

---

## 5. Reverse Proxy Setup (Caddy)

### 5.1 Caddyfile Configuration

**`/etc/caddy/Caddyfile`**

```caddy
# Athena Dashboard
localhost {
    # Frontend (Next.js)
    reverse_proxy / 127.0.0.1:3000

    # Backend API
    reverse_proxy /api/* 127.0.0.1:8000

    # WebSocket
    reverse_proxy /ws/* 127.0.0.1:8000

    # Logging
    log {
        output file /var/log/caddy/athena-dashboard.log
        format json
    }
}
```

### 5.2 Alternative: Nginx Configuration

**`/etc/nginx/sites-available/athena-dashboard`**

```nginx
upstream frontend {
    server 127.0.0.1:3000;
}

upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name localhost;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Logging
    access_log /var/log/nginx/athena-dashboard-access.log;
    error_log /var/log/nginx/athena-dashboard-error.log;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/athena-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 6. Deployment Commands

### 6.1 Install and Enable Services

```bash
# Copy service files
sudo cp /home/user/athena/dashboard/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable athena-dashboard-backend
sudo systemctl enable athena-dashboard-frontend
sudo systemctl enable caddy

# Start services
sudo systemctl start athena-dashboard-backend
sudo systemctl start athena-dashboard-frontend
sudo systemctl start caddy
```

### 6.2 Check Service Status

```bash
# Check all services
sudo systemctl status athena-dashboard-backend
sudo systemctl status athena-dashboard-frontend
sudo systemctl status caddy

# View logs
sudo journalctl -u athena-dashboard-backend -f
sudo journalctl -u athena-dashboard-frontend -f

# Quick status check
systemctl is-active athena-dashboard-backend
systemctl is-active athena-dashboard-frontend
```

### 6.3 Restart Services

```bash
# Restart after code changes
sudo systemctl restart athena-dashboard-backend
sudo systemctl restart athena-dashboard-frontend

# Reload Caddy config
sudo systemctl reload caddy
```

### 6.4 Stop Services

```bash
sudo systemctl stop athena-dashboard-backend
sudo systemctl stop athena-dashboard-frontend
```

---

## 7. Development Workflow

### 7.1 Development Mode

For development, you can run services manually without systemd:

```bash
# Terminal 1: Backend
cd /home/user/athena/dashboard/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd /home/user/athena/dashboard/frontend
pnpm dev

# Access: http://localhost:3000
```

### 7.2 Production Mode

Use systemd services as documented above:

```bash
# Build frontend
cd /home/user/athena/dashboard/frontend
pnpm build

# Start services
sudo systemctl start athena-dashboard-backend
sudo systemctl start athena-dashboard-frontend
sudo systemctl start caddy

# Access: http://localhost (port 80)
```

---

## 8. Monitoring and Maintenance

### 8.1 Log Locations

```bash
# Systemd journal logs
sudo journalctl -u athena-dashboard-backend --since "1 hour ago"
sudo journalctl -u athena-dashboard-frontend --since "1 hour ago"

# Caddy logs
sudo tail -f /var/log/caddy/athena-dashboard.log

# Nginx logs (if using nginx)
sudo tail -f /var/log/nginx/athena-dashboard-access.log
sudo tail -f /var/log/nginx/athena-dashboard-error.log
```

### 8.2 Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Frontend (through proxy)
curl http://localhost/

# Check PostgreSQL
systemctl status postgresql
```

### 8.3 Resource Usage

```bash
# Check service resource usage
systemctl status athena-dashboard-backend | grep Memory
systemctl status athena-dashboard-frontend | grep Memory

# Detailed stats
sudo systemd-cgtop
```

---

## 9. Troubleshooting

### 9.1 Service Won't Start

```bash
# Check service status
sudo systemctl status athena-dashboard-backend
sudo systemctl status athena-dashboard-frontend

# View full logs
sudo journalctl -u athena-dashboard-backend -n 100 --no-pager
sudo journalctl -u athena-dashboard-frontend -n 100 --no-pager

# Common issues:
# - Wrong file paths in service file
# - Python venv not activated
# - PostgreSQL not running
# - Port already in use
```

### 9.2 Frontend Can't Connect to Backend

```bash
# Check if backend is listening
sudo netstat -tlnp | grep 8000

# Check CORS settings in backend
# Verify NEXT_PUBLIC_API_URL in frontend/.env.local

# Test backend directly
curl http://localhost:8000/api/statistics/all
```

### 9.3 WebSocket Not Connecting

```bash
# Check if WebSocket endpoint is accessible
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://localhost:8000/ws/live-updates

# Verify proxy configuration (Caddy/Nginx) handles WebSocket upgrades
```

### 9.4 Permission Issues

```bash
# Ensure correct ownership
sudo chown -R user:user /home/user/athena/dashboard

# Check service file has correct User=user
sudo cat /etc/systemd/system/athena-dashboard-backend.service | grep User
```

---

## 10. Updates and Maintenance

### 10.1 Update Backend Code

```bash
# Pull latest code
cd /home/user/athena
git pull

# Restart backend service
sudo systemctl restart athena-dashboard-backend

# Check logs
sudo journalctl -u athena-dashboard-backend -f
```

### 10.2 Update Frontend Code

```bash
# Pull latest code
cd /home/user/athena/dashboard/frontend
git pull  # if in git

# Install new dependencies (if any)
pnpm install

# Rebuild
pnpm build

# Restart frontend service
sudo systemctl restart athena-dashboard-frontend
```

### 10.3 Update Dependencies

```bash
# Backend
cd /home/user/athena/dashboard/backend
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Frontend
cd /home/user/athena/dashboard/frontend
pnpm update
```

---

## 11. Security Considerations

### 11.1 Firewall Rules

```bash
# Only allow local access (recommended for single-machine)
sudo ufw allow from 127.0.0.1 to any port 8000
sudo ufw allow from 127.0.0.1 to any port 3000

# If exposing to network (be careful!)
# sudo ufw allow 80/tcp
```

### 11.2 Service Isolation

```bash
# Run services as non-root user (already configured in service files)
# User=user
# Group=user

# Restrict file permissions
chmod 750 /home/user/athena/dashboard
chmod 640 /home/user/athena/dashboard/backend/.env  # if you create one
```

---

## 12. Performance Optimization

### 12.1 Backend Workers

Adjust workers based on CPU cores:

```bash
# In service file:
# ExecStart=... --workers 4  # For 4+ CPU cores
```

### 12.2 Frontend Optimization

```bash
# Enable standalone output for smaller footprint
# In next.config.js:
module.exports = {
  output: 'standalone',
}

# Then copy .next/standalone to production
```

### 12.3 Caching

Add caching to Caddy:

```caddy
localhost {
    reverse_proxy / 127.0.0.1:3000

    # Cache static assets
    @static {
        path /_next/static/*
    }
    header @static Cache-Control "public, max-age=31536000, immutable"
}
```

---

## Quick Reference

### Common Commands

```bash
# Start all services
sudo systemctl start athena-dashboard-backend athena-dashboard-frontend caddy

# Stop all services
sudo systemctl stop athena-dashboard-backend athena-dashboard-frontend

# Restart all services
sudo systemctl restart athena-dashboard-backend athena-dashboard-frontend

# View logs
sudo journalctl -u athena-dashboard-backend -f
sudo journalctl -u athena-dashboard-frontend -f

# Check status
systemctl status athena-dashboard-*
```

### URLs

- Frontend: http://localhost (or http://localhost:3000 direct)
- Backend API: http://localhost:8000/api/
- API Docs: http://localhost:8000/docs (FastAPI auto-generated)
- Health Check: http://localhost:8000/health

---

**Document Version:** 1.0
**Last Updated:** November 18, 2025
**Deployment Method:** systemd (no Docker)

---

## Appendix: Service File Templates

All service files are located in `/home/user/athena/dashboard/systemd/` for easy copying to `/etc/systemd/system/`.

This deployment method is simpler, more direct, and better suited for Athena's single-machine architecture than Docker containers.
