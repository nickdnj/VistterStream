# 🎬 Preview System - Getting Started

**Local Preview + Go Live for VistterStream**

## What is This?

The Preview System lets you see your timeline output in real-time **before** pushing to YouTube Live, Facebook, or Twitch. Think of it as having a "mini YouTube Live" on your local machine.

### Key Features

- ✅ **Local Preview**: See timeline output in browser with <2s latency
- ✅ **No Internet Required**: Preview works offline (internet only needed for go-live)
- ✅ **One-Click Go Live**: Transition from preview to live streaming with a single button
- ✅ **Multi-Destination**: Select multiple destinations (YouTube, Facebook, etc.) before going live
- ✅ **Real-Time Status**: Visual indicators (PREVIEW / LIVE / OFFLINE)

---

## Quick Start (5 Minutes)

### Prerequisites

- VistterStream backend and frontend working
- Node.js 16+ and Python 3.8+ installed
- FFmpeg installed

### Installation

**Option 1: Automatic (Recommended)**

```bash
cd /Users/nickd/Workspaces/VistterStream
./install-preview-system.sh
```

This script will:
1. Download and install MediaMTX
2. Configure MediaMTX for preview
3. Install Python dependencies (httpx)
4. Install frontend dependencies (hls.js)
5. Start MediaMTX service (on Linux)

**Option 2: Manual**

See `docs/PreviewSystem-QuickStart.md` for step-by-step instructions.

---

## How to Use

### 1. Start Everything

**Terminal 1 - MediaMTX (Preview Server)**:
```bash
# On macOS:
mediamtx /etc/vistterstream/mediamtx.yml

# On Linux (Raspberry Pi):
sudo systemctl start vistterstream-preview
```

**Terminal 2 - VistterStream Backend**:
```bash
cd backend
source ../venv/bin/activate
python start.py
```

**Terminal 3 - Frontend**:
```bash
cd frontend
npm start
```

### 2. Open VistterStream

Open `http://localhost:3000` in your browser and go to **Timeline Editor**.

### 3. Create or Select a Timeline

- Create a new timeline or select an existing one
- Add camera cues, overlays, etc.

### 4. Start Preview

1. Look for the **"Live Preview & Go Live"** section above the timeline tracks
2. Click **"Start Preview"**
3. Video should appear within 5 seconds
4. You'll see a blue **PREVIEW** badge

### 5. Go Live (When Ready)

1. While preview is running, select destinations (YouTube, Facebook, etc.)
2. Click the red **"GO LIVE"** button
3. Confirm the destination list
4. Stream goes live! Badge changes to red **LIVE**

### 6. Stop Streaming

Click **"Stop Preview"** or **"Stop Live Stream"** to end the stream.

---

## Architecture at a Glance

```
Timeline → StreamRouter → MediaMTX (RTMP→HLS) → Browser Player
                       ↓
                    YouTube/Facebook/Twitch
```

**Components**:
- **MediaMTX**: RTMP server that converts timeline output to HLS for browser playback
- **StreamRouter**: Python service that routes stream to preview or live destinations
- **PreviewWindow**: React component with HLS.js player and controls
- **Preview API**: FastAPI endpoints (`/api/preview/*`)

---

## Troubleshooting

### Preview Won't Start

**Error**: "Preview server is not running"

**Solution**:
```bash
# Check if MediaMTX is running:
curl http://localhost:9997/v1/config/get

# If not, start it:
# macOS:
mediamtx /etc/vistterstream/mediamtx.yml

# Linux:
sudo systemctl start vistterstream-preview
sudo systemctl status vistterstream-preview
```

### Black Screen (No Video)

**Symptoms**: Player loads but no video appears

**Solution**:
1. Check if timeline is actually running:
   ```bash
   curl http://localhost:8000/api/timeline-execution/status/1
   ```

2. Check if MediaMTX is receiving RTMP:
   ```bash
   curl http://localhost:9997/v1/paths/list
   ```
   Should show `"preview": {"ready": true}`

3. Verify HLS manifest exists:
   ```bash
   curl http://localhost:8888/preview/index.m3u8
   ```

### High Latency (>5 seconds)

**Solution**: Edit `/etc/vistterstream/mediamtx.yml`:

```yaml
hlsSegmentDuration: 0.5s  # Reduce from 1s
```

Then restart MediaMTX.

### Go Live Fails

**Symptoms**: Error when clicking "GO LIVE"

**Solutions**:
1. Verify destinations are configured: `/api/destinations`
2. Check stream keys are valid
3. Test RTMP connection manually with FFmpeg:
   ```bash
   ffmpeg -re -i test.mp4 -c copy -f flv rtmp://a.rtmp.youtube.com/live2/YOUR_KEY
   ```

---

## File Locations

All new files created for the Preview System:

### Backend
- `backend/services/stream_router.py` - Routes timeline output
- `backend/services/preview_server_health.py` - Health monitoring
- `backend/routers/preview.py` - API endpoints

### Frontend
- `frontend/src/components/PreviewWindow.tsx` - React component

### Configuration
- `docker/mediamtx/mediamtx.yml` - MediaMTX config
- `docker/mediamtx/vistterstream-preview.service` - Systemd service
- `docker/docker-compose-preview.yml` - Docker Compose (optional)

### Documentation
- `docs/PreviewSystem-Specification.md` - Complete spec (18,000 words)
- `docs/PreviewSystem-QuickStart.md` - 30-minute setup guide
- `docs/PreviewSystem-TODO.md` - Implementation checklist
- `docs/PreviewSystem-Summary.md` - Executive summary

---

## Performance Tips

### For Raspberry Pi 5

1. **Ensure hardware acceleration is enabled**:
   ```bash
   vcgencmd get_config int | grep decode
   ```

2. **Monitor CPU usage**:
   ```bash
   top -p $(pgrep mediamtx)
   ```
   Should be <70% during preview

3. **Check temperature**:
   ```bash
   vcgencmd measure_temp
   ```
   Should stay below 70°C

### For All Systems

- Preview latency target: <2 seconds
- CPU overhead target: <15% additional
- Memory usage target: <200MB for MediaMTX

---

## API Reference

### Start Preview

```bash
POST /api/preview/start
Content-Type: application/json

{
  "timeline_id": 1
}

Response: 200 OK
{
  "message": "Preview started successfully",
  "timeline_id": 1,
  "timeline_name": "Marina Show",
  "hls_url": "http://localhost:8888/preview/index.m3u8",
  "mode": "preview"
}
```

### Get Status

```bash
GET /api/preview/status

Response: 200 OK
{
  "is_active": true,
  "mode": "preview",
  "timeline_id": 1,
  "timeline_name": "Marina Show",
  "hls_url": "http://localhost:8888/preview/index.m3u8",
  "server_healthy": true
}
```

### Go Live

```bash
POST /api/preview/go-live
Content-Type: application/json

{
  "destination_ids": [1, 2]
}

Response: 200 OK
{
  "message": "Now streaming LIVE",
  "timeline_id": 1,
  "destinations": ["YouTube Main", "Facebook Page"],
  "mode": "live"
}
```

### Stop Preview

```bash
POST /api/preview/stop

Response: 200 OK
{
  "message": "Preview stopped successfully",
  "timeline_id": 1
}
```

### Check Health

```bash
GET /api/preview/health

Response: 200 OK
{
  "status": "healthy",
  "active_streams": [
    {
      "name": "preview",
      "ready": true,
      "num_readers": 1
    }
  ],
  "total_streams": 1
}
```

---

## Known Limitations (MVP)

1. **Timeline Restarts on Go-Live**: Timeline resets to beginning when transitioning to live
   - *Future*: Seamless transition (Q1 2026)

2. **Single Preview Stream**: One active preview at a time
   - *Future*: Multi-user preview (Q2 2026)

3. **No DVR/Recording**: Preview is live-only
   - *Future*: Record last N minutes (Q2 2026)

---

## Next Steps

### For Operators
1. ✅ Install preview system (5 minutes)
2. ✅ Test with a simple timeline
3. ✅ Try go-live to YouTube test stream
4. ✅ Iterate on timeline design with instant feedback

### For Developers
1. Read `docs/PreviewSystem-Specification.md` for architecture
2. Review `docs/PreviewSystem-TODO.md` for future enhancements
3. Contribute improvements via GitHub

---

## Support

- **Architecture Questions**: See `docs/PreviewSystem-Specification.md` Section 4
- **Setup Issues**: See `docs/PreviewSystem-QuickStart.md`
- **API Documentation**: See this file (API Reference section)
- **GitHub Issues**: Report bugs or request features

---

## Success Metrics

Track these to ensure preview system is working well:

- ✅ Preview latency <2 seconds (measure with timestamp in video)
- ✅ CPU usage <80% on Raspberry Pi 5
- ✅ Go-live success rate >99%
- ✅ Operator satisfaction: Can preview without training?

---

**Status**: ✅ **COMPLETE AND READY TO USE**

**Questions?** See `docs/PreviewSystem-QuickStart.md` or contact the platform team.

🚀 **Happy Streaming!**

