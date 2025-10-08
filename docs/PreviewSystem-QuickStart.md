# Preview System - Quick Start Guide

> **For Developers**: Get the Preview Server + Preview Window running in 30 minutes

## What is This?

The Preview System lets operators see their timeline output in real-time **before** pushing to YouTube Live. Think of it as a "local YouTube Live" environment:

- **Preview Mode**: Timeline streams to local server → displays in browser (no internet needed)
- **Go Live**: One-click transition from preview to live streaming
- **Low Latency**: <2 second glass-to-glass delay

## Architecture at a Glance

```
Timeline Executor → Stream Router → Preview Server (MediaMTX)
                                      ↓
                                   HLS Output
                                      ↓
                               PreviewWindow.tsx (React)
```

## Prerequisites

- VistterStream backend running (Python/FastAPI)
- VistterStream frontend running (React/TypeScript)
- FFmpeg installed with hardware acceleration
- Node.js 16+ (for frontend dependencies)

## Installation Steps

### 1. Install MediaMTX (Preview Server)

**On Mac (Development)**:

```bash
# Download MediaMTX
curl -L -o mediamtx.tar.gz https://github.com/bluenviron/mediamtx/releases/download/v1.3.0/mediamtx_v1.3.0_darwin_amd64.tar.gz
tar -xzf mediamtx.tar.gz
sudo mv mediamtx /usr/local/bin/
```

**On Raspberry Pi 5 (Production)**:

```bash
# Download ARM64 version
wget https://github.com/bluenviron/mediamtx/releases/download/v1.3.0/mediamtx_v1.3.0_linux_arm64v8.tar.gz
tar -xzf mediamtx_v1.3.0_linux_arm64v8.tar.gz
sudo mv mediamtx /usr/local/bin/
```

### 2. Configure MediaMTX

Create `/etc/vistterstream/mediamtx.yml`:

```yaml
logLevel: info
api: yes
apiAddress: 127.0.0.1:9997

# RTMP ingest from timeline executor
rtmpAddress: :1935

# HLS output for browser
hlsAddress: :8888
hlsSegmentDuration: 1s
hlsSegmentCount: 3
hlsAllowOrigin: "*"

paths:
  preview:
    source: publisher
```

### 3. Start MediaMTX

**Development**:

```bash
mediamtx /etc/vistterstream/mediamtx.yml
```

**Production (systemd service)**:

```bash
sudo tee /etc/systemd/system/vistterstream-preview.service << 'EOF'
[Unit]
Description=VistterStream Preview Server
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/local/bin/mediamtx /etc/vistterstream/mediamtx.yml
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable vistterstream-preview
sudo systemctl start vistterstream-preview
```

### 4. Install Backend Dependencies

```bash
cd backend
source ../venv/bin/activate
pip install httpx  # For preview server health checks
```

### 5. Add Backend Services

Create these new files (see full spec for code):

- `backend/services/stream_router.py` - Routes timeline output to preview/live
- `backend/services/preview_server_health.py` - Health monitoring
- `backend/routers/preview.py` - API endpoints

Register the preview router in `backend/main.py`:

```python
from routers import preview

app.include_router(preview.router)
```

### 6. Install Frontend Dependencies

```bash
cd frontend
npm install hls.js
```

### 7. Add Frontend Component

Create `frontend/src/components/PreviewWindow.tsx` (see full spec for code)

Import in `TimelineEditor.tsx`:

```typescript
import PreviewWindow from './PreviewWindow';

// Add above timeline tracks:
<PreviewWindow timelineId={selectedTimeline?.id || null} />
```

### 8. Test the System

**Verify MediaMTX is Running**:

```bash
curl http://localhost:9997/v1/config/get
# Should return JSON configuration
```

**Test Preview Flow**:

1. Start VistterStream backend: `python backend/start.py`
2. Start frontend dev server: `cd frontend && npm start`
3. Open `http://localhost:3000` in browser
4. Go to Timeline Editor
5. Select a timeline
6. Click **"Start Preview"**
7. Video should appear within 5 seconds

**Test Go Live**:

1. While preview is running, select destinations (e.g., YouTube)
2. Click **"GO LIVE"**
3. Verify stream appears on YouTube Live dashboard

## Troubleshooting

### Preview Won't Start

**Error**: "Preview server is not running"

**Solution**:
```bash
# Check MediaMTX status
ps aux | grep mediamtx

# Restart MediaMTX
sudo systemctl restart vistterstream-preview

# Check logs
journalctl -u vistterstream-preview -f
```

### Black Screen / No Video

**Symptoms**: Player loads but no video appears

**Solution**:
```bash
# Check if RTMP stream is being received
curl http://localhost:9997/v1/paths/list

# Should show "preview" path with "ready: true"

# Verify HLS manifest exists
curl http://localhost:8888/preview/index.m3u8

# Check timeline is actually running
curl http://localhost:8000/api/timeline-execution/status/1
```

### High Latency (>5 seconds)

**Solution**: Reduce HLS segment duration in `mediamtx.yml`:

```yaml
hlsSegmentDuration: 0.5s  # Down from 1s
```

Restart MediaMTX after changes.

### CPU Overload on Raspberry Pi

**Symptoms**: Preview stutters, CPU >90%

**Solution**:
1. Check current CPU usage: `top`
2. Reduce preview quality (future feature)
3. Ensure hardware acceleration enabled: `vcgencmd get_config int | grep decode`

## API Reference

### Start Preview

```bash
POST /api/preview/start
{
  "timeline_id": 1
}

Response: 200 OK
{
  "message": "Preview started successfully",
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
{
  "destination_ids": [1, 2]
}

Response: 200 OK
{
  "message": "Now streaming LIVE",
  "destinations": ["YouTube Main", "Facebook Page"],
  "mode": "live"
}
```

### Stop Preview

```bash
POST /api/preview/stop

Response: 200 OK
{
  "message": "Preview stopped successfully"
}
```

## Performance Targets

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Latency** | <2s | Add timestamp to video, compare in preview |
| **CPU Usage** | <15% additional | `top -p $(pgrep mediamtx)` |
| **Memory** | <200MB | `ps aux \| grep mediamtx` |
| **Time to Preview** | <5s | Click "Start Preview" → video visible |

## Next Steps

1. **Read Full Spec**: See `PreviewSystem-Specification.md` for complete architecture
2. **Implementation Tasks**: See `PreviewSystem-TODO.md` for development roadmap
3. **Testing**: Run integration tests with real timelines and cameras
4. **Deploy to Pi**: Test performance on Raspberry Pi 5 hardware

## Getting Help

- **Architecture Questions**: See `PreviewSystem-Specification.md` Section 4
- **API Errors**: Check backend logs: `tail -f backend/logs/app.log`
- **UI Issues**: Check browser console for errors
- **Performance**: See Operational Runbook in full spec (Section 11)

---

**Ready to code?** Start with Phase 1 in `PreviewSystem-TODO.md` 🚀

