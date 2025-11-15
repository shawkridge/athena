# Systemd Service Management Guide

## Overview

Two systemd services have been created and enabled for the Athena Dashboard:
- **athena-dashboard-backend**: FastAPI server with WebSocket support (port 8000)
- **athena-dashboard-frontend**: React dev server (port 3000)

Both services are configured to:
- Start automatically on system boot
- Restart automatically if they crash
- Log to systemd journal
- Run as the `user` user

---

## Quick Start

### Check Service Status
```bash
sudo systemctl status athena-dashboard-backend.service
sudo systemctl status athena-dashboard-frontend.service
```

### View Real-Time Logs
```bash
# Backend logs (last 50 lines, follow updates)
sudo journalctl -u athena-dashboard-backend.service -n 50 -f

# Frontend logs (last 50 lines, follow updates)
sudo journalctl -u athena-dashboard-frontend.service -n 50 -f

# Both services combined
sudo journalctl -u athena-dashboard-backend.service -u athena-dashboard-frontend.service -n 50 -f
```

### Control Services

**Start services:**
```bash
sudo systemctl start athena-dashboard-backend.service
sudo systemctl start athena-dashboard-frontend.service

# Or both at once:
sudo systemctl start athena-dashboard-{backend,frontend}.service
```

**Stop services:**
```bash
sudo systemctl stop athena-dashboard-backend.service
sudo systemctl stop athena-dashboard-frontend.service

# Or both at once:
sudo systemctl stop athena-dashboard-{backend,frontend}.service
```

**Restart services:**
```bash
sudo systemctl restart athena-dashboard-backend.service
sudo systemctl restart athena-dashboard-frontend.service

# Or both at once:
sudo systemctl restart athena-dashboard-{backend,frontend}.service
```

**Reload (if config changed, no restart needed):**
```bash
sudo systemctl reload athena-dashboard-backend.service
```

---

## Service Configuration

### Backend Service
**File**: `/etc/systemd/system/athena-dashboard-backend.service`

```ini
[Unit]
Description=Athena Dashboard Backend (FastAPI + WebSocket)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/.work/athena/athena_dashboard/backend
Environment="PATH=/home/user/.work/athena/.venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="HOST=0.0.0.0"
Environment="PORT=8000"
Environment="DEBUG=False"
ExecStart=/home/user/.work/athena/.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=athena-backend

[Install]
WantedBy=multi-user.target
```

**Key Details:**
- Runs Python uvicorn server for FastAPI
- Auto-restarts on crash (10 second delay)
- Logs to systemd journal
- Runs in current working directory: `/home/user/.work/athena/athena_dashboard/backend`
- Uses virtual environment: `.venv/bin/python`

### Frontend Service
**File**: `/etc/systemd/system/athena-dashboard-frontend.service`

```ini
[Unit]
Description=Athena Dashboard Frontend (React + Vite)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/.work/athena/athena_dashboard/frontend
Environment="PATH=/home/user/.work/athena/athena_dashboard/frontend/node_modules/.bin:/usr/local/bin:/usr/bin"
Environment="NODE_ENV=production"
ExecStart=/usr/bin/npm run dev
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=athena-frontend

[Install]
WantedBy=multi-user.target
```

**Key Details:**
- Runs npm dev server for Vite
- Auto-restarts on crash (10 second delay)
- Logs to systemd journal
- Runs in current working directory: `/home/user/.work/athena/athena_dashboard/frontend`

---

## Environment Variables

### Backend
Set in service file or create `/etc/systemd/system/athena-dashboard-backend.service.d/override.conf`:

```ini
[Service]
Environment="DB_HOST=localhost"
Environment="DB_PORT=5432"
Environment="DEBUG=True"
```

Then reload: `sudo systemctl daemon-reload`

### Frontend
Frontend environment variables go in `.env` file in the frontend directory:
```bash
cd athena_dashboard/frontend
echo "VITE_API_URL=http://localhost:8000" > .env
```

Then restart: `sudo systemctl restart athena-dashboard-frontend.service`

---

## Monitoring & Troubleshooting

### View Service Status
```bash
# Detailed status
sudo systemctl status athena-dashboard-backend.service

# Quick status (is it running?)
sudo systemctl is-active athena-dashboard-backend.service
```

### Check Logs for Errors
```bash
# Last 100 lines of logs
sudo journalctl -u athena-dashboard-backend.service -n 100

# Logs since last reboot
sudo journalctl -u athena-dashboard-backend.service --since today

# Logs with timestamps
sudo journalctl -u athena-dashboard-backend.service --no-pager -o short-full
```

### Common Issues

**Service won't start:**
```bash
# Check logs
sudo journalctl -u athena-dashboard-backend.service -n 50 --no-pager

# Check if port is already in use
sudo lsof -i :8000
sudo lsof -i :3000

# Check if dependencies are installed
pip list | grep fastapi
npm list | head -5
```

**High memory usage:**
```bash
# Check memory and CPU usage
ps aux | grep "python\|npm" | grep -v grep

# Restart service (will free memory)
sudo systemctl restart athena-dashboard-backend.service
```

**WebSocket connection failing:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Check firewall
sudo ufw status
sudo ufw allow 8000/tcp
sudo ufw allow 3000/tcp
```

---

## Systemd Commands Reference

### Service Management
```bash
# Start a service
sudo systemctl start <service-name>

# Stop a service
sudo systemctl stop <service-name>

# Restart a service
sudo systemctl restart <service-name>

# Reload configuration (without restarting)
sudo systemctl reload <service-name>

# Check service status
sudo systemctl status <service-name>

# Check if service is running
sudo systemctl is-active <service-name>

# Enable on boot
sudo systemctl enable <service-name>

# Disable from boot
sudo systemctl disable <service-name>

# Check if enabled
sudo systemctl is-enabled <service-name>
```

### Journal (Logs) Commands
```bash
# View logs for specific service
sudo journalctl -u <service-name>

# Follow logs in real-time (tail -f)
sudo journalctl -u <service-name> -f

# Last N lines
sudo journalctl -u <service-name> -n 50

# Since a time
sudo journalctl -u <service-name> --since today
sudo journalctl -u <service-name> --since "2 hours ago"

# With timestamps
sudo journalctl -u <service-name> -o short-full

# With no pager (don't pipe through 'less')
sudo journalctl -u <service-name> --no-pager
```

### Service Files
```bash
# Reload systemd daemon (after editing .service files)
sudo systemctl daemon-reload

# List all services
sudo systemctl list-units --type=service

# List enabled services
sudo systemctl list-unit-files --state=enabled

# Edit a service file (opens in nano/vim)
sudo systemctl edit <service-name>

# View service file content
sudo cat /etc/systemd/system/<service-name>.service
```

---

## Creating Custom Overrides

If you need to modify a service without editing the original file:

```bash
# Create override directory
sudo mkdir -p /etc/systemd/system/athena-dashboard-backend.service.d

# Create override file
sudo nano /etc/systemd/system/athena-dashboard-backend.service.d/override.conf
```

**Example override (increase memory limit):**
```ini
[Service]
MemoryLimit=1G
TasksMax=100
```

**Example override (change restart behavior):**
```ini
[Service]
Restart=on-failure
RestartForceExitStatus=1
RestartMaxDelaySec=1min
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart athena-dashboard-backend.service
```

---

## Performance Tuning

### Increase File Descriptor Limits
```bash
sudo nano /etc/systemd/system/athena-dashboard-backend.service.d/limits.conf
```

Add:
```ini
[Service]
LimitNOFILE=65535
LimitNPROC=4096
```

### Memory and CPU Limits
```bash
sudo nano /etc/systemd/system/athena-dashboard-backend.service.d/limits.conf
```

Add:
```ini
[Service]
MemoryLimit=512M
MemoryAccounting=true
CPUAccounting=true
```

---

## Backup and Restore

### Backup Service Files
```bash
sudo cp /etc/systemd/system/athena-dashboard-*.service ~/backup/
```

### Restore Service Files
```bash
sudo cp ~/backup/athena-dashboard-*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

---

## Security Considerations

### Run as Unprivileged User
Both services run as `user` (not root), which is secure.

### Restrict Port Access (Optional)
```bash
# Only allow localhost access
sudo ufw allow from 127.0.0.1 to 127.0.0.1 port 8000
sudo ufw allow from 127.0.0.1 to 127.0.0.1 port 3000

# Allow from specific IP
sudo ufw allow from 192.168.1.100 to any port 8000
```

### Log Rotation
Systemd journal logs are automatically rotated. Check with:
```bash
# Show journal disk usage
sudo journalctl --disk-usage

# Vacuum old logs (older than 30 days)
sudo journalctl --vacuum-time=30d

# Vacuum to size limit
sudo journalctl --vacuum-size=500M
```

---

## Integrating with Your Workflow

### Development
```bash
# Watch logs while developing
sudo journalctl -u athena-dashboard-backend.service -f

# In another terminal, edit code and:
sudo systemctl restart athena-dashboard-backend.service
```

### Production
```bash
# Check both services are running
sudo systemctl status athena-dashboard-{backend,frontend}.service

# View consolidated logs
sudo journalctl -u athena-dashboard-backend.service -u athena-dashboard-frontend.service -n 100

# Set up monitoring (e.g., with systemd-watchdog)
# See: https://wiki.archlinux.org/title/Systemd#Watchdog
```

---

## Summary

| Task | Command |
|------|---------|
| Check status | `sudo systemctl status athena-dashboard-backend.service` |
| View logs | `sudo journalctl -u athena-dashboard-backend.service -f` |
| Start | `sudo systemctl start athena-dashboard-backend.service` |
| Stop | `sudo systemctl stop athena-dashboard-backend.service` |
| Restart | `sudo systemctl restart athena-dashboard-backend.service` |
| Enable boot | `sudo systemctl enable athena-dashboard-backend.service` |
| Disable boot | `sudo systemctl disable athena-dashboard-backend.service` |

---

**Last Updated**: November 15, 2025
**Services**: 2 active (backend + frontend)
**Status**: ✅ Both running and enabled

