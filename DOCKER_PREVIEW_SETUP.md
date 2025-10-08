# 🐳 Docker Preview Setup - Quick Start

**Running MediaMTX Preview Server in Docker (Recommended)**

---

## 🎯 Architecture

```
┌─────────────────────────────────────┐
│  Docker Compose                      │
│                                      │
│  ┌──────────────────────────────┐   │
│  │  RTMP Relay (Nginx)          │   │
│  │  Port 1935 - Camera feeds    │   │
│  └──────────────────────────────┘   │
│                                      │
│  ┌──────────────────────────────┐   │
│  │  Preview Server (MediaMTX)   │   │
│  │  Port 1936 - Timeline RTMP   │   │
│  │  Port 8888 - HLS output      │   │
│  │  Port 9997 - API             │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Port Mapping**:
- **1935**: RTMP Relay (camera feeds)
- **1936**: Preview Server RTMP (timeline output) ← **NEW!**
- **8888**: HLS output (browser playback)
- **9997**: MediaMTX API (health checks)

---

## 🚀 Quick Start

### Step 1: Start Docker Services

```bash
cd /Users/nickd/Workspaces/VistterStream/docker
docker-compose up -d
```

This starts:
- ✅ RTMP Relay (for cameras)
- ✅ Preview Server (MediaMTX)

### Step 2: Verify Services

```bash
# Check containers are running
docker-compose ps

# Should show both containers as "Up"
# - vistterstream-rtmp-relay
# - vistterstream-preview

# Check preview server health
curl http://localhost:9997/v1/config/get
```

### Step 3: Start Backend

```bash
cd /Users/nickd/Workspaces/VistterStream/backend
source ../venv/bin/activate
python start.py
```

### Step 4: Start Frontend

```bash
cd /Users/nickd/Workspaces/VistterStream/frontend
npm start
```

### Step 5: Test Preview!

1. Open http://localhost:3000
2. Go to **Timeline Editor**
3. Select **"Wharfside Waterfront"** timeline (shown in your screenshot)
4. Click **"Start Preview"** ← Should work now!
5. Video should appear within 5 seconds 🎬

---

## 🔧 Configuration Changes Made

### 1. Updated `docker/docker-compose.yml`
- Added `preview-server` service
- MediaMTX on port **1936** (RTMP) to avoid conflict with port 1935
- HLS on port **8888** (browser access)
- API on port **9997** (health checks)

### 2. Updated `backend/services/stream_router.py`
- Changed RTMP URL from `rtmp://localhost:1935/preview/stream`
- To: `rtmp://localhost:1936/preview/stream`

### 3. Updated `docker/mediamtx/mediamtx.yml`
- Changed API address from `127.0.0.1:9997`
- To: `0.0.0.0:9997` (accessible from host)

---

## 🐛 Troubleshooting

### Preview Server Not Running Warning

**Symptoms**: Yellow warning in UI: "⚠️ Preview server is not running"

**Solutions**:

1. **Check if containers are running**:
   ```bash
   docker-compose ps
   ```

2. **Check preview server logs**:
   ```bash
   docker logs vistterstream-preview
   ```

3. **Restart preview server**:
   ```bash
   docker-compose restart preview-server
   ```

4. **Check health endpoint**:
   ```bash
   curl http://localhost:9997/v1/config/get
   ```
   Should return JSON config

### Port Conflicts

If you get port binding errors:

```bash
# Check what's using the ports
lsof -i :1936
lsof -i :8888
lsof -i :9997

# Kill any processes using these ports
kill <PID>

# Then restart
docker-compose down
docker-compose up -d
```

### Can't Connect to RTMP

**Error**: "Failed to start preview"

**Check**:
```bash
# Test RTMP connectivity
ffmpeg -re -f lavfi -i testsrc=duration=10:size=1280x720:rate=30 \
  -f flv rtmp://localhost:1936/preview/stream
```

Should start streaming without errors.

---

## 📊 Monitoring

### View Preview Server Logs
```bash
docker logs -f vistterstream-preview
```

### View All Services
```bash
docker-compose logs -f
```

### Check Active Streams
```bash
curl http://localhost:9997/v1/paths/list
```

Should show `"preview"` path when timeline is running.

---

## 🔄 Managing Services

### Start Services
```bash
cd docker
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Restart Preview Server Only
```bash
docker-compose restart preview-server
```

### Rebuild After Config Changes
```bash
docker-compose down
docker-compose up -d --force-recreate preview-server
```

---

## ✅ Verification Checklist

After starting Docker Compose:

- [ ] Containers running: `docker-compose ps`
- [ ] Preview API responds: `curl http://localhost:9997/v1/config/get`
- [ ] Backend started: `python start.py`
- [ ] Frontend started: `npm start`
- [ ] No yellow warning in UI
- [ ] "Start Preview" button enabled
- [ ] Click "Start Preview" → video appears!

---

## 🎬 Expected Behavior

1. **Before Starting**:
   - PreviewWindow shows: "Preview Offline"
   - Yellow warning: "Preview server is not running" ← **Should be GONE now!**

2. **After Docker Compose Up**:
   - Warning disappears
   - "Start Preview" button is **blue and enabled**

3. **After Clicking Start Preview**:
   - Blue "PREVIEW" badge appears
   - Video plays within 5 seconds
   - Timeline name shows in badge

4. **Ready to Go Live**:
   - Select destinations (checkboxes appear)
   - Click red "GO LIVE" button
   - Confirm → Stream goes live!

---

## 🎯 Why Docker is Better

✅ **No manual installation** - Just `docker-compose up`  
✅ **Consistent ports** - Always the same setup  
✅ **Easy troubleshooting** - `docker logs` shows everything  
✅ **Production-ready** - Deploy anywhere Docker runs  
✅ **Auto-restart** - Services restart on failure  
✅ **Health checks** - Docker monitors service health  

---

## 🚀 Next Steps

1. ✅ Start Docker: `docker-compose up -d`
2. ✅ Verify: `curl http://localhost:9997/v1/config/get`
3. ✅ Start backend & frontend
4. ✅ Test preview in Timeline Editor
5. ✅ Try go-live to YouTube!

---

**Status**: 🐳 **Docker-based preview ready!**

See the warning disappear in your UI! 🎉

