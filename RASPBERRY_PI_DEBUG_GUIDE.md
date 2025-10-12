# Raspberry Pi Debug Guide - VistterStream Docker Deployment

## Current Status

✅ **COMPLETED:**
- All 4 Docker containers built and running
- Backend CORS configured correctly with Pi hostname/IP
- Frontend rebuilt with correct API URL (`http://vistterpi.local:8000/api`, fallback `http://192.168.12.107:8000/api`)
- `.env` file configured with proper environment variables
- All services are healthy and communicating

❌ **CURRENT ISSUE:**
- Browser cache is serving old JavaScript files
- Old JS has `localhost:8000`, new JS has `192.168.12.107:8000`
- CORS errors appear ONLY because browser is using cached old files

## Hardware & OS Baseline

- Hardware: Raspberry Pi 5 (8 GB RAM) in the CanaKit Turbine case with active cooling
- Storage: 128 GB Samsung EVO+ microSD (CanaKit image)
- OS: Raspberry Pi OS (64-bit, Bookworm). Verify with `cat /etc/os-release`.
- Firmware: Prefer `sudo apt update && sudo apt full-upgrade`; only use `sudo rpi-update` when directed for firmware debugging.
- Cooling: Keep the turbine fan connected to avoid thermal throttling under sustained encodes.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi (vistterpi.local / 192.168.12.107)             │
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
- **Built with**: `REACT_APP_API_URL=http://vistterpi.local:8000/api` (include `http://192.168.12.107:8000/api` as a fallback during transition)
- **Serves**: Static React SPA via Nginx
- **Access**: `http://vistterpi.local:3000` (fallback `http://192.168.12.107:3000`)

### 2. Backend (`vistterstream-backend`)
- **Image**: `docker-backend:latest` (built locally)
- **Port**: 8000
- **CORS**: `http://vistterpi.local:3000,http://192.168.12.107:3000,http://localhost:3000`
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
CORS_ALLOW_ORIGINS=http://vistterpi.local:3000,http://192.168.12.107:3000,http://localhost:3000
```

> Rebuild the frontend with `REACT_APP_API_URL=http://vistterpi.local:8000/api` so browsers follow the hostname. Keep the IP fallback in CORS until the DHCP reservation is confirmed.

## Network & Hostname

- Set the Pi hostname to `vistterpi` with `sudo raspi-config` (System Options -> Hostname) or `sudo raspi-config nonint do_hostname vistterpi`, then reboot.
- Verify mDNS discovery from a control laptop:
  ```bash
  ping vistterpi.local
  getent hosts vistterpi.local
  avahi-browse -at | grep vistterpi
  ```
- Reserve `192.168.12.107` in the router DHCP table so the fallback IP stays stable. Update the fallback values in `.env` if the reservation changes.
- When building the frontend or updating the `.env`, prefer `http://vistterpi.local` to avoid cache churn when the IP changes.

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

### Check Hostname Resolution
```bash
# On the Pi, confirm hostname
hostname

# From any client on the LAN
ping vistterpi.local
getent hosts vistterpi.local
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

### Verify Hostname-Based Endpoints
```bash
# API via hostname
curl -i http://vistterpi.local:8000/api/health

# Frontend via hostname
curl -I http://vistterpi.local:3000
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
   Expected: `CORS_ALLOW_ORIGINS=http://vistterpi.local:3000,http://192.168.12.107:3000,http://localhost:3000`

2. Check if browser is using cached JS:
   - Open DevTools -> Network tab
   - Check where API calls are going
   - If hitting `localhost:8000` -> cached bundle still loading
   - If hitting `192.168.12.107:8000` -> hostname missing from build/CORS; rebuild frontend and refresh `.env`
   - If hitting `vistterpi.local:8000` -> hostname build is active

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

### Issue: Hostname vistterpi.local Does Not Resolve

**Symptoms:**
- `ping vistterpi.local` fails or resolves to the wrong IP
- Browser errors like `ERR_NAME_NOT_RESOLVED` or `ERR_CONNECTION_TIMED_OUT`

**Diagnosis:**
1. On the Pi, confirm hostname: `hostname`
2. Ensure Avahi is running: `systemctl status avahi-daemon` (should be `active (running)`)
3. From your laptop or desktop, test discovery: `ping vistterpi.local` or `getent hosts vistterpi.local`

**Solution:**
- Set the hostname with `sudo raspi-config` -> System Options -> Hostname -> `vistterpi`, then reboot
- Restart mDNS export if needed: `sudo systemctl restart avahi-daemon`
- On Windows, install Bonjour Print Services or add `vistterpi.local` to `C:\Windows\System32\drivers\etc\hosts`
- Use the IP fallback temporarily, but rebuild with the hostname once discovery is fixed

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
- Backend API accessible at `http://vistterpi.local:8000` (fallback `http://192.168.12.107:8000`)
- Frontend accessible at `http://vistterpi.local:3000` (fallback `http://192.168.12.107:3000`)
- CORS configured correctly in backend
- Frontend built with correct API URL
- Database and uploads persist across restarts
- RTMP relay ready for camera streams
- Preview server ready for timeline playback

### What Needs Fixing ⚠️
- Browser cache needs to be cleared (client-side issue, not server)
- Confirm every operator device resolves `vistterpi.local`; keep the IP fallback until all clients pass
- User needs to do hard refresh or clear browser cache

### Next Steps 🚀
1. Open `http://vistterpi.local:3000` on each client and hard refresh (or use a private window) to purge cached IP builds
2. Add cameras through the UI
3. Configure RTMP streams against the RTMP relay
4. Test timeline preview functionality from the preview client

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
4. **Hostname Discovery**: Some clients cache stale `vistterpi.local` responses; flush DNS/mDNS or fall back to the IP while fixing the network setup

## Browser Cache Reset Recipes

### Chrome / Edge (macOS & Windows)
- Open DevTools (`Cmd+Opt+I` or `Ctrl+Shift+I`), then right-click the reload icon and choose "Empty Cache and Hard Reload"
- Or clear cached files: Settings -> Privacy & Security -> Clear browsing data -> Cached images and files
- Verify the fresh bundle: `view-source:http://vistterpi.local:3000/static/js/main.*.js` and confirm requests target `vistterpi.local`

### Firefox (macOS & Windows)
- Force reload with `Cmd+Shift+R` or `Ctrl+Shift+R`
- If stale, clear cache: Settings -> Privacy & Security -> Cookies and Site Data -> Clear Data -> Cached Web Content
- Confirm by opening the Network tab and watching API calls for the hostname value

### Safari (macOS & iOS)
- macOS: Preferences -> Advanced -> enable "Show Develop menu"; then Develop -> Empty Caches and reload
- iOS: Settings -> Safari -> Clear History and Website Data (Cache only) and reopen the site
- For iOS testing, open a private tab (Tabs -> Private) to bypass cached bundles

### iOS / Android Chromium Browsers
- Use a private/incognito tab to bypass cached static assets
- If still stale, clear cache: Settings -> Privacy -> Clear browsing data -> Cached images and files
- Inspect via `chrome://inspect/#devices` from a laptop to confirm the bundle URL (advanced)

## Advanced Diagnostic Checks

### Confirm Latest Frontend Build Deployed
```bash
docker compose -f docker-compose.rpi.yml exec frontend ls -lah /usr/share/nginx/html/static/js
docker compose -f docker-compose.rpi.yml exec frontend sh -c "grep -R 'REACT_APP_API_URL' /usr/share/nginx/html/static/js 2>/dev/null | head"
```
- Compare timestamps against the last rebuild; hashed bundle names should refresh after each build
- If hashes stay identical between builds, try `docker compose -f docker-compose.rpi.yml build --no-cache frontend`

### Inspect Response Headers for Caching
```bash
curl -I http://vistterpi.local:3000/static/js/main.*.js
```
- `Cache-Control: max-age=31536000` is expected (React build default); browsers must see new hash names to invalidate cache
- If `ETag` or `Last-Modified` look stale, clear any CDN or proxy layers (none by default)

### Verify Backend CORS at Runtime
```bash
docker compose -f docker-compose.rpi.yml exec backend python - <<'PY'
from vistterstream.config import settings
print(settings.cors_allow_origins)
PY
```
- Output must include `http://vistterpi.local:3000`; if not, double-check `.env` and restart the stack

### Check LAN DNS / mDNS State
```bash
avahi-browse -at | grep vistterpi
arp -a | grep vistterpi
systemd-resolve --status | grep vistterpi -B2
```
- Confirms the Pi is advertising itself and clients resolve the name to the expected IP
- If collisions appear, power-cycle any other device using `vistterpi` as the hostname

### Capture Frontend Requests in Flight
```bash
# Run from a laptop
mitmproxy --mode reverse:http://vistterpi.local:3000
```
- Point the browser at `http://127.0.0.1:8080` (default mitmproxy listener) to inspect outbound requests
- Helpful when confirming the SPA is hitting the hostname-based API after cache clears

## Field Checklist (Operator)

- Frontend, backend, RTMP relay, and preview containers show "Up" in `docker compose ps`
- `ping vistterpi.local` resolves correctly from every control laptop or tablet
- Browser opened in private/incognito mode and points to `http://vistterpi.local:3000`
- First camera ingests successfully to `rtmp://vistterpi.local:1935/live/<camera-key>`
- Timeline preview reachable at `http://vistterpi.local:8888/stream.m3u8`
- `.env` stored safely with current hostname/IP notes for future rebuilds

## Maintenance & Health Checks

### Weekly
- `sudo apt update && sudo apt full-upgrade` to pull security patches and container runtime fixes
- `docker system df` to confirm image layers are not filling the SD card
- `df -h /` to verify at least 3-4 GB free for new builds and logs
- `docker compose -f docker-compose.rpi.yml ps` to ensure all services report `Up`

### Monthly
- Schedule a maintenance reboot: `sudo reboot`, then rerun the Quick Reference commands
- Export a SQLite backup (see Backup & Restore) and copy it off-device
- `docker image prune` to clear orphaned layers after confirming builds are healthy
- Review logs for warnings: `journalctl -u docker --since '1 month ago' | tail`

### Temperature & Throttling
- `vcgencmd measure_temp` (expected < 70°C under load with the turbine fan)
- `vcgencmd get_throttled` should return `0x0`; non-zero indicates power or cooling issues
- Inspect fan operation visually if throttling flags appear

## Backup & Restore

### Prepare Backup Directory
```bash
mkdir -p ~/VistterStream/backups
```

### Create SQLite Snapshot (Hot Backup)
```bash
# Run on the Pi
cd ~/VistterStream/docker
docker compose -f docker-compose.rpi.yml exec backend \
  sqlite3 /data/vistterstream.db \
  ".backup /data/backups/vistterstream-$(date +%Y%m%d).db"
```
- Backups land inside the backend container volume at `/data/backups` (mapped to `~/VistterStream/backups` on the host)
- Copy the newest file to NAS/SSD: `rsync -av ~/VistterStream/backups/ user@nas:/srv/backups/vistterstream/`

### Restore Procedure
```bash
cd ~/VistterStream/docker
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml run --rm backend \
  sh -c "cp /data/backups/<backup-file>.db /data/vistterstream.db"
docker compose -f docker-compose.rpi.yml up -d
```
- Replace `<backup-file>.db` with the desired backup name before running the copy command
- Verify data via the UI and `docker compose ... logs backend | tail`
- Keep `.env` and backup files together when archiving for disaster recovery

### SD Card Care
- Enable automatic trimming monthly: add `fstrim.timer` (already enabled on Bookworm; verify with `systemctl status fstrim.timer`)
- Avoid full disk writes; keep `/var/log` rotation defaults (`sudo journalctl --vacuum-time=7d` trims older logs if needed)
- Snapshot the SD card after major milestones: `sudo dd if=/dev/mmcblk0 of=vistterstream-$(date +%Y%m%d).img bs=4M status=progress`


---

**Last Updated**: 2025-03 (Cache reset, maintenance, backup guidance added)  
**Hostname**: vistterpi.local  
**Pi IP**: 192.168.12.107 (DHCP reservation recommended)  
**Status**: Deployment complete, browser cache clear needed

