# Raspberry Pi Debug Guide - VistterStream Docker Deployment

## Current Status

✅ **COMPLETED:**
- All 4 Docker containers built and running
- Backend CORS configured correctly with Pi IP
- Frontend rebuilt with correct API URL (192.168.12.107:8000)
- `.env` file configured with proper environment variables
- All services are healthy and communicating

❌ **CURRENT ISSUE:**
- Browser cache is serving old JavaScript files
- Old JS has `localhost:8000`, new JS has `192.168.12.107:8000`
- CORS errors appear ONLY because browser is using cached old files

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi (192.168.12.107)             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Frontend   │  │   Backend    │  │  RTMP Relay  │      │
│  │   (Nginx)    │  │  (FastAPI)   │  │   (Nginx)    │      │
│  │   Port 3000  │  │  Port 8000   │  │  Port 1935   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                  │               │
│         └─────── API ─────┘                  │               │
│                           │                  │               │
│                    ┌──────────────┐          │               │
│                    │   Preview    │          │               │
│                    │  (MediaMTX)  │◄─────────┘               │
│                    │  Port 1936   │                          │
│                    │  Port 8888   │                          │
│                    └──────────────┘                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Container Details

### 1. Frontend (`vistterstream-frontend`)
- **Image**: `docker-frontend:latest` (built locally)
- **Port**: 3000
- **Built with**: `REACT_APP_API_URL=http://192.168.12.107:8000/api`
- **Serves**: Static React SPA via Nginx
- **Access**: `http://192.168.12.107:3000`

### 2. Backend (`vistterstream-backend`)
- **Image**: `docker-backend:latest` (built locally)
- **Port**: 8000
- **CORS**: `http://192.168.12.107:3000,http://localhost:3000`
- **Database**: SQLite at `/data/vistterstream.db` (persistent volume)
- **Uploads**: `/data/uploads` (persistent volume)

### 3. RTMP Relay (`vistterstream-rtmp-relay`)
- **Image**: `docker-rtmp-relay:latest` (built locally)
- **Port**: 1935 (RTMP ingestion from cameras)
- **Purpose**: Receives camera RTMP streams

### 4. Preview Server (`vistterstream-preview`)
- **Image**: `bluenviron/mediamtx:latest`
- **Ports**: 
  - 1936 (RTMP input)
  - 8888 (HLS output)
  - 9997 (API)
- **Purpose**: Timeline preview playback

## File Locations on Pi

```
~/VistterStream/
├── .env                          # Environment variables (NOT in git)
├── docker/
│   ├── docker-compose.rpi.yml   # Main compose file for Pi
│   ├── nginx-rtmp/              # RTMP relay config
│   └── mediamtx/                # Preview server config
├── backend/
│   ├── Dockerfile               # Backend container definition
│   ├── requirements.txt         # Python dependencies
│   └── ...
└── frontend/
    ├── Dockerfile               # Frontend container definition
    └── ...
```

## Environment Variables

**Location**: `~/VistterStream/.env`

```bash
# Current configuration
DATABASE_URL=sqlite:////data/vistterstream.db
UPLOADS_DIR=/data/uploads
RTMP_RELAY_HOST=rtmp-relay
RTMP_RELAY_PORT=1935
CORS_ALLOW_ORIGINS=http://192.168.12.107:3000,http://localhost:3000
```

## Common Commands

### Check Container Status
```bash
cd ~/VistterStream/docker
docker compose -f docker-compose.rpi.yml ps
```

### View Logs
```bash
# All containers
docker compose -f docker-compose.rpi.yml logs -f

# Specific container
docker compose -f docker-compose.rpi.yml logs -f backend
docker compose -f docker-compose.rpi.yml logs -f frontend
docker compose -f docker-compose.rpi.yml logs -f rtmp-relay
docker compose -f docker-compose.rpi.yml logs -f preview-server
```

### Check Environment Variables
```bash
# Backend CORS
docker compose -f docker-compose.rpi.yml exec backend env | grep CORS

# All backend env vars
docker compose -f docker-compose.rpi.yml exec backend env
```

### Restart Services
```bash
# Restart specific service
docker compose -f docker-compose.rpi.yml restart backend

# Restart all services
docker compose -f docker-compose.rpi.yml restart

# Full restart (reloads .env)
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml up -d
```

### Rebuild Containers
```bash
# Rebuild specific service
docker compose -f docker-compose.rpi.yml build frontend
docker compose -f docker-compose.rpi.yml up -d frontend

# Rebuild with no cache (force clean build)
docker compose -f docker-compose.rpi.yml build --no-cache frontend

# Rebuild all services
docker compose -f docker-compose.rpi.yml build
docker compose -f docker-compose.rpi.yml up -d
```

### Access Container Shell
```bash
# Backend Python shell
docker compose -f docker-compose.rpi.yml exec backend bash

# Frontend Nginx shell
docker compose -f docker-compose.rpi.yml exec frontend sh
```

## Diagnostic Commands

### Verify Frontend API URL
```bash
# Count references to Pi IP (should be > 0)
docker compose -f docker-compose.rpi.yml exec frontend sh -c \
  "grep -r '192.168.12.107' /usr/share/nginx/html/static/js/ 2>/dev/null | wc -l"

# Count references to localhost (should be 0 in new build)
docker compose -f docker-compose.rpi.yml exec frontend sh -c \
  "grep -r 'localhost:8000' /usr/share/nginx/html/static/js/ 2>/dev/null | wc -l"
```

### Test Backend API
```bash
# Health check
curl -i http://localhost:8000/api/health

# Test CORS (simulate browser preflight)
curl -i -X OPTIONS http://192.168.12.107:8000/api/cameras \
  -H "Origin: http://192.168.12.107:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type"
```

### Check Docker Resources
```bash
# Disk usage
docker system df

# Container resource usage
docker stats

# Volume info
docker volume ls
docker volume inspect docker_vistter_data
```

## Troubleshooting

### Issue: CORS Errors in Browser

**Symptoms:**
```
Access to XMLHttpRequest at 'http://192.168.12.107:8000/api/cameras' 
from origin 'http://192.168.12.107:3000' has been blocked by CORS policy
```

**Diagnosis:**
1. Check backend CORS value:
   ```bash
   docker compose -f docker-compose.rpi.yml exec backend env | grep CORS
   ```
   Expected: `CORS_ALLOW_ORIGINS=http://192.168.12.107:3000,http://localhost:3000`

2. Check if browser is using cached JS:
   - Open DevTools → Network tab
   - Check where API calls are going
   - If going to `localhost:8000` → browser cache issue
   - If going to `192.168.12.107:8000` → backend CORS issue

**Solution:**
- **If backend CORS is wrong**: Edit `.env`, then restart:
  ```bash
  docker compose -f docker-compose.rpi.yml down
  docker compose -f docker-compose.rpi.yml up -d
  ```

- **If frontend API URL is wrong**: Rebuild frontend:
  ```bash
  docker compose -f docker-compose.rpi.yml build --no-cache frontend
  docker compose -f docker-compose.rpi.yml up -d frontend
  ```

- **If browser cache issue**: Clear browser cache (see below)

### Issue: Frontend Shows localhost:8000

**Cause:** Browser cache or frontend not rebuilt

**Solution:**
1. Verify frontend container was rebuilt recently:
   ```bash
   docker compose -f docker-compose.rpi.yml images frontend
   ```
   Check "CREATED" timestamp

2. Clear browser cache:
   - **Hard refresh**: Cmd+Shift+R (Mac) or Ctrl+Shift+F5 (Windows/Linux)
   - **Clear cache**: Cmd+Shift+Delete (Mac) or Ctrl+Shift+Delete (Windows/Linux)
   - **Incognito mode**: Cmd+Shift+N (Mac) or Ctrl+Shift+N (Windows/Linux)

3. If still broken, rebuild:
   ```bash
   docker compose -f docker-compose.rpi.yml build --no-cache frontend
   docker compose -f docker-compose.rpi.yml up -d frontend
   ```

### Issue: Container Won't Start

**Check logs:**
```bash
docker compose -f docker-compose.rpi.yml logs [service-name]
```

**Common issues:**
- **Port already in use**: Check with `sudo netstat -tulpn | grep [port]`
- **Volume permissions**: Check with `docker volume inspect docker_vistter_data`
- **Build failures**: Check `docker compose build` output

### Issue: /dev/video11 Error

**Error:**
```
error gathering device information while adding custom device "/dev/video11": 
no such file or directory
```

**Cause:** Pi doesn't have hardware encoder device (Pi 4) or device not configured (Pi 5)

**Solution:** Already fixed! Device pass-through is optional. Backend will use:
- `h264_v4l2m2m` if `/dev/video11` exists (Pi 5 hardware encoding)
- `libx264` if not (software encoding - works on all Pis)

To enable hardware encoding on Pi 5:
1. Check device exists: `ls -l /dev/video11`
2. Uncomment device lines in `docker-compose.rpi.yml`:
   ```yaml
   devices:
     - "/dev/video11:/dev/video11"
   group_add:
     - "44"  # video group
   ```
3. Restart: `docker compose -f docker-compose.rpi.yml restart backend`

## Update Workflow

### Pull Updates from GitHub
```bash
cd ~/VistterStream

# Save any local changes
git stash

# Pull updates
git pull origin master

# Rebuild affected services
cd docker
docker compose -f docker-compose.rpi.yml build
docker compose -f docker-compose.rpi.yml up -d
```

### Update .env File
```bash
# Edit
nano ~/VistterStream/.env

# Apply changes (requires full restart)
cd ~/VistterStream/docker
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml up -d
```

## Performance Tips

### Check Resource Usage
```bash
# Real-time stats
docker stats

# Check disk space
df -h
docker system df
```

### Clean Up Docker Resources
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes (CAREFUL - deletes data!)
docker volume prune

# Remove everything unused
docker system prune -a
```

### Enable Hardware Encoding (Pi 5 Only)
1. Verify device: `ls -l /dev/video11`
2. Edit `docker-compose.rpi.yml` - uncomment device lines
3. Restart backend
4. Check logs: `docker compose -f docker-compose.rpi.yml logs backend | grep -i encoder`

## Current State Summary

### What's Working ✅
- All 4 containers built and running
- Backend API accessible at `http://192.168.12.107:8000`
- Frontend accessible at `http://192.168.12.107:3000`
- CORS configured correctly in backend
- Frontend built with correct API URL
- Database and uploads persist across restarts
- RTMP relay ready for camera streams
- Preview server ready for timeline playback

### What Needs Fixing ⚠️
- Browser cache needs to be cleared (client-side issue, not server)
- User needs to do hard refresh or clear browser cache

### Next Steps 🚀
1. Clear browser cache on the device accessing the Pi
2. Add cameras through the UI
3. Configure RTMP streams
4. Test timeline preview functionality

## Quick Reference Card

```bash
# START EVERYTHING
cd ~/VistterStream/docker
docker compose -f docker-compose.rpi.yml up -d

# STOP EVERYTHING
docker compose -f docker-compose.rpi.yml down

# VIEW LOGS
docker compose -f docker-compose.rpi.yml logs -f

# RESTART AFTER .ENV CHANGE
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml up -d

# REBUILD FRONTEND
docker compose -f docker-compose.rpi.yml build --no-cache frontend
docker compose -f docker-compose.rpi.yml up -d frontend

# CHECK STATUS
docker compose -f docker-compose.rpi.yml ps

# CHECK CORS
docker compose -f docker-compose.rpi.yml exec backend env | grep CORS
```

## Support Information

- **Documentation**: `~/VistterStream/RASPBERRY_PI_SETUP.md`
- **Docker Compose**: `~/VistterStream/docker/docker-compose.rpi.yml`
- **Environment**: `~/VistterStream/.env` (not tracked by git)
- **Logs**: `docker compose -f docker-compose.rpi.yml logs [service]`

## Known Issues

1. **Browser Cache**: After rebuilding frontend, browser cache must be cleared
2. **React Build Args**: API URL is baked in at build time, not runtime
3. **Env File Loading**: Requires full `down` + `up`, not just `restart`

---

**Last Updated**: 2025-10-11  
**Pi IP**: 192.168.12.107  
**Status**: Deployment complete, browser cache clear needed

