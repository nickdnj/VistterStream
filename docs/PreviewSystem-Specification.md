# Preview Server + Preview Window System Specification
**VistterStream Local Preview & Go-Live Subsystem**

## Document Version
- **Version**: 1.0  
- **Date**: October 4, 2025  
- **Status**: Draft for Implementation  
- **Authors**: Platform Team  

---

## 1. Executive Summary

The Preview Server + Preview Window subsystem enables **real-time local preview** of timeline output before pushing to external platforms (YouTube Live, Facebook Live, etc.). This provides a "mini YouTube Live" environment for operators to:

1. **Iterate on timelines** with <2s latency preview in the browser
2. **Verify compositions** (camera switching, overlays, transitions) before going live
3. **Seamlessly transition** from preview to live with a single button click

This feature is critical for production workflows where operators need confidence that their timeline is correct before streaming to public platforms.

---

## 2. Product Goals

- **Local-First Preview**: Enable timeline preview without internet connectivity or external streaming platforms
- **Low-Latency Playback**: Achieve <2s glass-to-glass latency for preview feedback
- **Single-User Architecture**: Support one active preview stream at a time (appliance is single-operator)
- **Seamless Go-Live**: Transition from preview to live streaming without restarting the timeline
- **Lightweight Footprint**: Run on Raspberry Pi 5 alongside existing streaming workload
- **Operator-Friendly UX**: Clear visual distinction between Preview and Live states

---

## 3. Architecture Overview

### 3.1 System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                    VISTTERSTREAM APPLIANCE                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │          Timeline Executor (Existing)                   │    │
│  │  • Camera switching                                     │    │
│  │  • Overlay compositing                                  │    │
│  │  • FFmpeg process management                            │    │
│  └──────────────┬──────────────────────────────────────────┘    │
│                 │                                                │
│                 ▼                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │          Stream Router (NEW)                            │    │
│  │  • Duplicates timeline output                           │    │
│  │  • Routes to Preview Server OR Live Destinations        │    │
│  └──────────┬─────────────────────┬───────────────────────┘    │
│             │                     │                             │
│             ▼                     ▼                             │
│  ┌──────────────────┐  ┌──────────────────────────┐           │
│  │  Preview Server   │  │  Live Destinations       │           │
│  │  (NEW)            │  │  (Existing)              │           │
│  │  • RTMP Ingest    │  │  • YouTube Live          │           │
│  │  • HLS Output     │  │  • Facebook Live         │           │
│  │  • HTTP Server    │  │  • Twitch                │           │
│  └─────────┬─────────┘  └──────────────────────────┘           │
│            │                                                    │
│            │ HLS Stream (HTTP)                                 │
│            ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐     │
│  │          Preview Window (NEW)                         │     │
│  │  React Component in Timeline Editor                   │     │
│  │  • HLS.js Player                                      │     │
│  │  • Start/Stop Preview Controls                        │     │
│  │  • Go Live Button                                     │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ RTMP (Go Live)
                           ▼
              ┌─────────────────────────┐
              │  External Platforms     │
              │  (YouTube, Facebook)    │
              └─────────────────────────┘
```

### 3.2 Component Architecture

| Component | Technology | Responsibility |
|-----------|-----------|----------------|
| **Stream Router** | Python asyncio service | Duplicate FFmpeg output, route to preview or live |
| **Preview Server** | FFmpeg + Nginx-RTMP (or MediaMTX) | RTMP ingest → HLS output |
| **HLS HTTP Server** | FastAPI static file serving | Serve HLS manifest and segments |
| **Preview Window** | React + HLS.js | Browser-based video player with controls |
| **Preview Control API** | FastAPI endpoints | Start/stop preview, go-live orchestration |

---

## 4. Detailed Design

### 4.1 Stream Router Service

**Purpose**: Duplicate timeline output to both preview and live destinations without restarting FFmpeg.

#### Implementation Strategy

**Option A: FFmpeg `tee` Muxer** (Recommended)
```python
# In FFmpegProcessManager.start_stream()
def build_output_args(preview_mode: bool, output_urls: List[str]):
    if preview_mode:
        # Route to preview server ONLY
        return ['-f', 'flv', 'rtmp://localhost:1935/preview/stream']
    else:
        # Route to live destinations (existing logic)
        return build_tee_outputs(output_urls)
```

**Option B: FFmpeg Multiple Outputs** (Future: Simultaneous Preview + Live)
```bash
# One encode, multiple outputs
ffmpeg -i <input> \
  -c:v h264_v4l2m2m -b:v 4500k \
  -f flv rtmp://localhost:1935/preview/stream \
  -f flv rtmp://a.rtmp.youtube.com/live2/<key> \
  -f flv rtmps://live-api-s.facebook.com:443/rtmp/<key>
```

#### State Machine

```python
class PreviewMode(Enum):
    IDLE = "idle"           # No timeline running
    PREVIEW = "preview"     # Timeline → Preview Server
    LIVE = "live"           # Timeline → Live Destinations
    PREVIEW_LIVE = "preview_live"  # Timeline → Both (future)

class StreamRouter:
    def __init__(self):
        self.mode = PreviewMode.IDLE
        self.timeline_id: Optional[int] = None
    
    async def start_preview(self, timeline_id: int):
        """Start timeline with preview output"""
        self.mode = PreviewMode.PREVIEW
        self.timeline_id = timeline_id
        
        # Start timeline with preview destination
        output_urls = ['rtmp://localhost:1935/preview/stream']
        await get_timeline_executor().start_timeline(
            timeline_id=timeline_id,
            output_urls=output_urls
        )
    
    async def go_live(self, destination_ids: List[int]):
        """Switch from preview to live without restarting timeline"""
        if self.mode != PreviewMode.PREVIEW:
            raise ValueError("Can only go live from preview mode")
        
        # PHASE 1: Stop preview stream
        await get_timeline_executor().stop_timeline(self.timeline_id)
        
        # PHASE 2: Restart with live destinations
        db = SessionLocal()
        destinations = db.query(StreamingDestination).filter(
            StreamingDestination.id.in_(destination_ids)
        ).all()
        output_urls = [dest.get_full_rtmp_url() for dest in destinations]
        db.close()
        
        await get_timeline_executor().start_timeline(
            timeline_id=self.timeline_id,
            output_urls=output_urls
        )
        
        self.mode = PreviewMode.LIVE
```

### 4.2 Preview Server

**Purpose**: Accept RTMP input from timeline executor, transcode to HLS for browser playback.

#### Technology Choice: MediaMTX (Recommended)

**Why MediaMTX over Nginx-RTMP?**
- Single binary, no dependencies (perfect for embedded appliance)
- Built-in HLS/DASH/WebRTC support
- Low-latency mode (LL-HLS support)
- Active maintenance (Nginx-RTMP deprecated)
- ARM64 native support
- Configurable via YAML

**Alternative: FFmpeg-only** (Fallback)
- Use FFmpeg to read RTMP and generate HLS segments
- FastAPI serves segments
- More manual but no additional dependencies

#### MediaMTX Configuration

**File: `/backend/services/preview-server/mediamtx.yml`**

```yaml
# MediaMTX Configuration for VistterStream Preview Server
# See: https://github.com/bluenviron/mediamtx

logLevel: info
logDestinations: [stdout]
logFile: /var/log/vistterstream/preview-server.log

# API for health checks
api: yes
apiAddress: 127.0.0.1:9997

# RTMP Ingest (from Timeline Executor)
rtmpAddress: :1935
rtmpEncryption: "no"

# HLS Output (to Browser)
hlsAddress: :8888
hlsEncryption: "no"
hlsAlwaysRemux: yes  # Always remux to ensure clean segments
hlsSegmentCount: 3   # Keep only 3 segments for low latency
hlsSegmentDuration: 1s  # 1 second segments
hlsPartDuration: 200ms  # LL-HLS partial segments
hlsSegmentMaxSize: 50M
hlsAllowOrigin: "*"  # CORS for local browser access

# Paths
paths:
  preview:
    # Accept RTMP input from timeline executor
    source: publisher
    
    # Output HLS for browser playback
    record: no
    
    # Low-latency settings
    readTimeout: 10s
    readBufferCount: 512
```

#### Deployment

**Docker Compose** (for development/testing):

```yaml
# docker/docker-compose-preview.yml
version: '3.8'

services:
  preview-server:
    image: bluenviron/mediamtx:latest
    container_name: vistterstream-preview
    ports:
      - "1935:1935"  # RTMP ingest
      - "8888:8888"  # HLS output
    volumes:
      - ./mediamtx.yml:/mediamtx.yml
    restart: unless-stopped
    networks:
      - vistterstream
```

**Standalone Binary** (production on Pi):

```bash
# Install MediaMTX on Raspberry Pi
wget https://github.com/bluenviron/mediamtx/releases/download/v1.3.0/mediamtx_v1.3.0_linux_arm64v8.tar.gz
tar -xzf mediamtx_v1.3.0_linux_arm64v8.tar.gz
sudo mv mediamtx /usr/local/bin/
sudo mv mediamtx.yml /etc/vistterstream/

# Create systemd service
sudo tee /etc/systemd/system/vistterstream-preview.service << EOF
[Unit]
Description=VistterStream Preview Server
After=network.target

[Service]
Type=simple
User=vistterstream
ExecStart=/usr/local/bin/mediamtx /etc/vistterstream/mediamtx.yml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable vistterstream-preview
sudo systemctl start vistterstream-preview
```

#### Health Monitoring

```python
# backend/services/preview_server_health.py

import httpx
import logging

logger = logging.getLogger(__name__)

class PreviewServerHealth:
    def __init__(self, api_url: str = "http://localhost:9997"):
        self.api_url = api_url
    
    async def check_health(self) -> bool:
        """Check if MediaMTX is running and accepting connections"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_url}/v1/config/get")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Preview server health check failed: {e}")
            return False
    
    async def get_active_streams(self) -> dict:
        """Get list of active streams from MediaMTX"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_url}/v1/paths/list")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to get active streams: {e}")
        
        return {"paths": []}
```

### 4.3 Preview Control API

**New Router: `/backend/routers/preview.py`**

```python
"""
Preview Control API
Manages local preview workflow: start preview, stop preview, go live
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from models.database import get_db
from models.timeline import Timeline
from models.destination import StreamingDestination
from services.stream_router import get_stream_router, PreviewMode
from services.preview_server_health import PreviewServerHealth

router = APIRouter(prefix="/api/preview", tags=["preview"])


class StartPreviewRequest(BaseModel):
    timeline_id: int


class GoLiveRequest(BaseModel):
    destination_ids: List[int]


class PreviewStatusResponse(BaseModel):
    is_active: bool
    mode: str  # 'idle', 'preview', 'live'
    timeline_id: Optional[int] = None
    timeline_name: Optional[str] = None
    hls_url: Optional[str] = None
    server_healthy: bool


@router.post("/start")
async def start_preview(request: StartPreviewRequest, db: Session = Depends(get_db)):
    """
    Start preview mode - timeline outputs to local preview server only.
    
    Workflow:
    1. Verify timeline exists
    2. Check preview server health
    3. Start timeline with preview destination (rtmp://localhost:1935/preview/stream)
    4. Return HLS playback URL
    """
    # Verify timeline exists
    timeline = db.query(Timeline).filter(Timeline.id == request.timeline_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    # Check preview server health
    health = PreviewServerHealth()
    if not await health.check_health():
        raise HTTPException(
            status_code=503, 
            detail="Preview server is not running. Please check system status."
        )
    
    # Start preview via stream router
    router_service = get_stream_router()
    try:
        await router_service.start_preview(timeline_id=request.timeline_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start preview: {str(e)}")
    
    # Return HLS URL for browser playback
    # MediaMTX serves HLS at http://localhost:8888/{path}/index.m3u8
    hls_url = "http://localhost:8888/preview/index.m3u8"
    
    return {
        "message": "Preview started successfully",
        "timeline_id": request.timeline_id,
        "timeline_name": timeline.name,
        "hls_url": hls_url,
        "mode": "preview"
    }


@router.post("/stop")
async def stop_preview():
    """
    Stop preview mode - stops the timeline execution.
    """
    router_service = get_stream_router()
    
    if router_service.mode == PreviewMode.IDLE:
        raise HTTPException(status_code=400, detail="No preview is running")
    
    timeline_id = router_service.timeline_id
    await router_service.stop()
    
    return {
        "message": "Preview stopped successfully",
        "timeline_id": timeline_id
    }


@router.post("/go-live")
async def go_live(request: GoLiveRequest, db: Session = Depends(get_db)):
    """
    Transition from preview to live streaming.
    
    Workflow:
    1. Verify we're in preview mode
    2. Verify destinations exist
    3. Stop preview stream
    4. Restart timeline with live destinations
    5. Keep timeline execution state (position, loop count)
    
    NOTE: Current implementation restarts the timeline. 
    Future: Seamless transition without restart (requires FFmpeg dynamic output).
    """
    router_service = get_stream_router()
    
    if router_service.mode != PreviewMode.PREVIEW:
        raise HTTPException(
            status_code=400, 
            detail="Can only go live from preview mode. Start preview first."
        )
    
    # Verify destinations
    destinations = db.query(StreamingDestination).filter(
        StreamingDestination.id.in_(request.destination_ids)
    ).all()
    
    if not destinations:
        raise HTTPException(status_code=404, detail="No valid destinations found")
    
    destination_names = [dest.name for dest in destinations]
    
    # Go live via stream router
    try:
        await router_service.go_live(destination_ids=request.destination_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to go live: {str(e)}")
    
    return {
        "message": "Now streaming LIVE",
        "timeline_id": router_service.timeline_id,
        "destinations": destination_names,
        "mode": "live",
        "warning": "Timeline was restarted from beginning. Seamless transition coming in future version."
    }


@router.get("/status", response_model=PreviewStatusResponse)
async def get_preview_status(db: Session = Depends(get_db)):
    """
    Get current preview/live status.
    """
    router_service = get_stream_router()
    health = PreviewServerHealth()
    
    server_healthy = await health.check_health()
    
    timeline_name = None
    if router_service.timeline_id:
        timeline = db.query(Timeline).filter(
            Timeline.id == router_service.timeline_id
        ).first()
        if timeline:
            timeline_name = timeline.name
    
    hls_url = None
    if router_service.mode == PreviewMode.PREVIEW:
        hls_url = "http://localhost:8888/preview/index.m3u8"
    
    return {
        "is_active": router_service.mode != PreviewMode.IDLE,
        "mode": router_service.mode.value,
        "timeline_id": router_service.timeline_id,
        "timeline_name": timeline_name,
        "hls_url": hls_url,
        "server_healthy": server_healthy
    }


@router.get("/health")
async def check_preview_server_health():
    """
    Check if preview server (MediaMTX) is running and healthy.
    """
    health = PreviewServerHealth()
    is_healthy = await health.check_health()
    
    if not is_healthy:
        raise HTTPException(
            status_code=503,
            detail="Preview server is not responding"
        )
    
    streams = await health.get_active_streams()
    
    return {
        "status": "healthy",
        "active_streams": streams.get("paths", [])
    }
```

### 4.4 Preview Window UI Component

**New Component: `/frontend/src/components/PreviewWindow.tsx`**

```typescript
import React, { useState, useEffect, useRef } from 'react';
import Hls from 'hls.js';
import axios from 'axios';
import { 
  PlayIcon, 
  StopIcon, 
  SignalIcon,
  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline';

interface PreviewStatus {
  is_active: boolean;
  mode: 'idle' | 'preview' | 'live';
  timeline_id: number | null;
  timeline_name: string | null;
  hls_url: string | null;
  server_healthy: boolean;
}

interface Destination {
  id: number;
  name: string;
  platform: string;
  is_active: boolean;
}

interface PreviewWindowProps {
  timelineId: number | null;
  onPreviewStart?: () => void;
  onPreviewStop?: () => void;
  onGoLive?: () => void;
}

const PreviewWindow: React.FC<PreviewWindowProps> = ({
  timelineId,
  onPreviewStart,
  onPreviewStop,
  onGoLive
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  
  const [status, setStatus] = useState<PreviewStatus>({
    is_active: false,
    mode: 'idle',
    timeline_id: null,
    timeline_name: null,
    hls_url: null,
    server_healthy: false
  });
  
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [selectedDestinations, setSelectedDestinations] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load status and destinations
  useEffect(() => {
    loadPreviewStatus();
    loadDestinations();
    
    // Poll status every 2 seconds
    const interval = setInterval(loadPreviewStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  // Initialize HLS player when preview starts
  useEffect(() => {
    if (status.mode === 'preview' && status.hls_url && videoRef.current) {
      initializeHlsPlayer(status.hls_url);
    } else {
      cleanupHlsPlayer();
    }
    
    return () => cleanupHlsPlayer();
  }, [status.mode, status.hls_url]);

  const loadPreviewStatus = async () => {
    try {
      const response = await axios.get('/api/preview/status');
      setStatus(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to load preview status:', err);
    }
  };

  const loadDestinations = async () => {
    try {
      const response = await axios.get('/api/destinations');
      setDestinations(response.data.filter((d: Destination) => d.is_active));
    } catch (err) {
      console.error('Failed to load destinations:', err);
    }
  };

  const initializeHlsPlayer = (hlsUrl: string) => {
    if (!videoRef.current) return;

    if (Hls.isSupported()) {
      const hls = new Hls({
        maxBufferLength: 2,  // Low latency: 2 second buffer
        maxMaxBufferLength: 4,
        liveSyncDuration: 1,
        liveMaxLatencyDuration: 3,
        lowLatencyMode: true
      });
      
      hls.loadSource(hlsUrl);
      hls.attachMedia(videoRef.current);
      
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current?.play();
      });
      
      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error('HLS error:', data);
        if (data.fatal) {
          setError(`Playback error: ${data.type}`);
        }
      });
      
      hlsRef.current = hls;
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      videoRef.current.src = hlsUrl;
      videoRef.current.play();
    }
  };

  const cleanupHlsPlayer = () => {
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.src = '';
    }
  };

  const handleStartPreview = async () => {
    if (!timelineId) {
      setError('No timeline selected');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      await axios.post('/api/preview/start', { timeline_id: timelineId });
      await loadPreviewStatus();
      onPreviewStart?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start preview');
    } finally {
      setLoading(false);
    }
  };

  const handleStopPreview = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await axios.post('/api/preview/stop');
      await loadPreviewStatus();
      onPreviewStop?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to stop preview');
    } finally {
      setLoading(false);
    }
  };

  const handleGoLive = async () => {
    if (selectedDestinations.length === 0) {
      setError('Please select at least one destination');
      return;
    }

    const confirmMessage = `Go LIVE to ${selectedDestinations.length} destination(s)?\n\n` +
      `This will publish your stream to:\n` +
      destinations
        .filter(d => selectedDestinations.includes(d.id))
        .map(d => `• ${d.name} (${d.platform})`)
        .join('\n');
    
    if (!window.confirm(confirmMessage)) {
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      await axios.post('/api/preview/go-live', {
        destination_ids: selectedDestinations
      });
      await loadPreviewStatus();
      onGoLive?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to go live');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = () => {
    switch (status.mode) {
      case 'preview': return 'bg-blue-500';
      case 'live': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (status.mode) {
      case 'preview': return 'PREVIEW';
      case 'live': return 'LIVE';
      default: return 'OFFLINE';
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg shadow-lg overflow-hidden">
      {/* Video Player */}
      <div className="relative bg-black" style={{ paddingBottom: '56.25%' }}>
        {status.mode === 'preview' || status.mode === 'live' ? (
          <>
            <video
              ref={videoRef}
              className="absolute inset-0 w-full h-full"
              controls={false}
              muted
              playsInline
            />
            
            {/* Status Badge */}
            <div className="absolute top-4 left-4 flex items-center space-x-2">
              <div className={`${getStatusColor()} px-3 py-1 rounded-full flex items-center space-x-2`}>
                <SignalIcon className="w-4 h-4 text-white animate-pulse" />
                <span className="text-white font-bold text-sm">{getStatusText()}</span>
              </div>
              {status.timeline_name && (
                <div className="bg-gray-800 bg-opacity-75 px-3 py-1 rounded-full">
                  <span className="text-white text-sm">{status.timeline_name}</span>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <PlayIcon className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Preview Offline</p>
              <p className="text-sm">Select a timeline and click "Start Preview"</p>
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="p-4 space-y-4">
        {/* Error Message */}
        {error && (
          <div className="bg-red-900 bg-opacity-50 border border-red-500 rounded-lg p-3 flex items-start space-x-2">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-red-200 text-sm">{error}</div>
          </div>
        )}

        {/* Preview Server Health Warning */}
        {!status.server_healthy && (
          <div className="bg-yellow-900 bg-opacity-50 border border-yellow-500 rounded-lg p-3">
            <div className="text-yellow-200 text-sm">
              ⚠️ Preview server is not running. Check system status.
            </div>
          </div>
        )}

        {/* Preview Controls */}
        <div className="flex items-center space-x-3">
          {status.mode === 'idle' ? (
            <button
              onClick={handleStartPreview}
              disabled={loading || !timelineId || !status.server_healthy}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center space-x-2 transition"
            >
              <PlayIcon className="w-5 h-5" />
              <span>{loading ? 'Starting...' : 'Start Preview'}</span>
            </button>
          ) : status.mode === 'preview' ? (
            <>
              <button
                onClick={handleStopPreview}
                disabled={loading}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center space-x-2 transition"
              >
                <StopIcon className="w-5 h-5" />
                <span>Stop Preview</span>
              </button>
              <button
                onClick={handleGoLive}
                disabled={loading || selectedDestinations.length === 0}
                className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-bold py-2 px-4 rounded-lg flex items-center justify-center space-x-2 transition animate-pulse"
              >
                <SignalIcon className="w-5 h-5" />
                <span>{loading ? 'Going Live...' : 'GO LIVE'}</span>
              </button>
            </>
          ) : (
            <button
              onClick={handleStopPreview}
              disabled={loading}
              className="flex-1 bg-red-700 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-lg flex items-center justify-center space-x-2 transition"
            >
              <StopIcon className="w-5 h-5" />
              <span>Stop Live Stream</span>
            </button>
          )}
        </div>

        {/* Destination Selection (shown in preview mode) */}
        {status.mode === 'preview' && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">
              Select Live Destinations:
            </label>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {destinations.map((dest) => (
                <label
                  key={dest.id}
                  className="flex items-center space-x-2 p-2 hover:bg-gray-800 rounded cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedDestinations.includes(dest.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedDestinations([...selectedDestinations, dest.id]);
                      } else {
                        setSelectedDestinations(selectedDestinations.filter(id => id !== dest.id));
                      }
                    }}
                    className="w-4 h-4"
                  />
                  <span className="text-sm text-gray-300">
                    {dest.name} ({dest.platform})
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Info */}
        <div className="text-xs text-gray-500 space-y-1">
          <div>• Preview latency: ~2 seconds</div>
          <div>• Timeline will restart when going live (seamless transition coming soon)</div>
        </div>
      </div>
    </div>
  );
};

export default PreviewWindow;
```

### 4.5 Integration with Timeline Editor

**Update: `/frontend/src/components/TimelineEditor.tsx`**

```typescript
// Add import
import PreviewWindow from './PreviewWindow';

// Add to component (above timeline tracks):

return (
  <div className="p-6 space-y-6">
    {/* Preview Window - NEW */}
    <div className="bg-gray-800 rounded-lg p-4">
      <h2 className="text-xl font-bold text-white mb-4">Preview Monitor</h2>
      <PreviewWindow
        timelineId={selectedTimeline?.id || null}
        onPreviewStart={() => {
          console.log('Preview started');
        }}
        onPreviewStop={() => {
          console.log('Preview stopped');
        }}
        onGoLive={() => {
          alert('Now streaming LIVE!');
        }}
      />
    </div>

    {/* Existing Timeline Editor UI */}
    {/* ... rest of timeline editor ... */}
  </div>
);
```

---

## 5. Database Schema Extensions

**No new tables required.** All state is managed in-memory by `StreamRouter` service.

Optional: Add audit logging for preview/live transitions:

```sql
-- Optional: Preview/Live audit log
CREATE TABLE preview_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type VARCHAR(20) NOT NULL,  -- 'preview_start', 'preview_stop', 'go_live'
    timeline_id INTEGER REFERENCES timelines(id),
    destination_ids JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);
```

---

## 6. Functional Requirements

### 6.1 Preview Mode

| Requirement ID | Description | Priority | Status |
|---------------|-------------|----------|--------|
| PREV-001 | Start timeline in preview mode (output to local server only) | P0 | Draft |
| PREV-002 | Display preview in browser with <2s latency | P0 | Draft |
| PREV-003 | Support 1920x1080 @ 30fps preview | P0 | Draft |
| PREV-004 | Show preview status badge (PREVIEW / LIVE / OFFLINE) | P1 | Draft |
| PREV-005 | Preview server health check before starting | P1 | Draft |
| PREV-006 | Stop preview and clean up resources | P0 | Draft |
| PREV-007 | Preview works without internet connectivity | P0 | Draft |

### 6.2 Go Live Workflow

| Requirement ID | Description | Priority | Status |
|---------------|-------------|----------|--------|
| LIVE-001 | Transition from preview to live with single button | P0 | Draft |
| LIVE-002 | Select one or more live destinations before going live | P0 | Draft |
| LIVE-003 | Confirmation dialog with destination list | P1 | Draft |
| LIVE-004 | Graceful fallback if live transition fails | P1 | Draft |
| LIVE-005 | Stop live stream and return to preview | P2 | Draft |
| LIVE-006 | Visual distinction: red LIVE badge, pulsing "GO LIVE" button | P1 | Draft |

### 6.3 Operator Experience

| Requirement ID | Description | Priority | Status |
|---------------|-------------|----------|--------|
| UX-001 | Preview window above timeline editor (no extra clicks) | P0 | Draft |
| UX-002 | Clear error messages for common failures | P1 | Draft |
| UX-003 | Preview player controls (mute/unmute, fullscreen) | P2 | Future |
| UX-004 | Timeline playhead sync with preview (visual only) | P2 | Future |
| UX-005 | Keyboard shortcuts (Space = play/pause, L = go live) | P3 | Future |

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Preview Latency** | <2 seconds glass-to-glass | Operator needs fast feedback for iteration |
| **CPU Overhead** | <15% additional load | Must run alongside live streaming on Pi 5 |
| **Memory Footprint** | <200MB for preview server | Embedded appliance constraints |
| **HLS Segment Size** | 1-2 seconds | Balance latency vs. compatibility |

### 7.2 Reliability

| Requirement | Specification |
|-------------|---------------|
| **Preview Server Uptime** | 99% availability (restart on crash) |
| **Graceful Degradation** | If preview server fails, show error but don't block live streaming |
| **Resource Cleanup** | Automatic cleanup of stale HLS segments (>5 min old) |
| **Concurrent Limit** | 1 active preview stream (single-operator appliance) |

### 7.3 Security

| Requirement | Specification |
|-------------|---------------|
| **Local-Only Access** | Preview HLS served on localhost only (no external exposure) |
| **No Auth on Preview Server** | MediaMTX runs without auth (localhost trust boundary) |
| **CORS Policy** | Allow all origins for local browser access |
| **Audit Logging** | Log preview start/stop and go-live events |

### 7.4 Compatibility

| Platform | Support Level |
|----------|---------------|
| **Raspberry Pi 5** | Primary target (ARM64) |
| **Mac (Intel/Apple Silicon)** | Development target |
| **Intel NUC / x86_64** | Secondary production target |
| **Browsers** | Chrome 90+, Safari 14+, Firefox 88+ (HLS.js support) |

---

## 8. Implementation Phases

### Phase 1: Preview Server Setup (Week 1)

**Goal**: Get MediaMTX running and serving HLS locally.

- [ ] Install MediaMTX on development Mac
- [ ] Configure MediaMTX for RTMP ingest + HLS output
- [ ] Test with manual FFmpeg RTMP push
- [ ] Verify HLS playback in Chrome/Safari
- [ ] Create systemd service for Pi deployment
- [ ] Document installation procedure

**Acceptance Criteria**:
- MediaMTX accepts RTMP on `rtmp://localhost:1935/preview/stream`
- HLS available at `http://localhost:8888/preview/index.m3u8`
- Latency <2s measured with timer in frame

### Phase 2: Stream Router Service (Week 1-2)

**Goal**: Route timeline output to preview server.

- [ ] Create `StreamRouter` class in `/backend/services/stream_router.py`
- [ ] Implement `start_preview()` method
- [ ] Implement `stop()` method
- [ ] Implement `go_live()` method with timeline restart
- [ ] Add state machine (IDLE → PREVIEW → LIVE)
- [ ] Unit tests for state transitions

**Acceptance Criteria**:
- Timeline can start with preview destination
- Preview stream appears in MediaMTX
- Go-live successfully switches destinations
- Clean shutdown without orphaned processes

### Phase 3: Preview Control API (Week 2)

**Goal**: Expose REST API for preview control.

- [ ] Create `/backend/routers/preview.py`
- [ ] Implement `POST /api/preview/start`
- [ ] Implement `POST /api/preview/stop`
- [ ] Implement `POST /api/preview/go-live`
- [ ] Implement `GET /api/preview/status`
- [ ] Implement `GET /api/preview/health`
- [ ] API documentation (OpenAPI)

**Acceptance Criteria**:
- API endpoints return correct status codes
- Error handling for invalid requests
- Health check reports MediaMTX status
- Integration tests with mock timeline executor

### Phase 4: Preview Window UI (Week 2-3)

**Goal**: Build React component with HLS player and controls.

- [ ] Install `hls.js` dependency
- [ ] Create `PreviewWindow.tsx` component
- [ ] Implement HLS player with low-latency config
- [ ] Add Start/Stop/Go Live buttons
- [ ] Add destination selection checkboxes
- [ ] Add status badges (PREVIEW / LIVE)
- [ ] Error message display
- [ ] Preview server health indicator

**Acceptance Criteria**:
- Video plays smoothly with <2s latency
- Buttons enable/disable based on state
- Error messages are actionable
- Component updates when status changes (polling)

### Phase 5: Timeline Editor Integration (Week 3)

**Goal**: Embed preview window in timeline editor UI.

- [ ] Add `PreviewWindow` above timeline tracks
- [ ] Wire up timeline selection to preview
- [ ] Add keyboard shortcuts (optional)
- [ ] Responsive layout adjustments
- [ ] User testing with real timelines

**Acceptance Criteria**:
- Preview window visible when timeline selected
- UI remains responsive during preview
- Layout works on 1920x1080 and 1366x768 screens

### Phase 6: Testing & Hardening (Week 3-4)

**Goal**: Validate on Raspberry Pi and edge cases.

- [ ] Deploy to Raspberry Pi 5
- [ ] Test with 3-camera timeline (camera switching + overlays)
- [ ] Test go-live with YouTube (real stream key)
- [ ] Measure CPU/memory usage during preview
- [ ] Test preview server crash recovery
- [ ] Test rapid start/stop cycles
- [ ] Load testing: 60-minute preview session
- [ ] Documentation: operator guide

**Acceptance Criteria**:
- Preview runs on Pi 5 without overheating
- Go-live successfully publishes to YouTube
- System recovers from preview server crashes
- Operator can use preview without training

### Phase 7: Polish & Documentation (Week 4)

**Goal**: Production-ready release.

- [ ] Operator user guide (screenshots + workflow)
- [ ] Troubleshooting guide
- [ ] Architecture documentation (this spec)
- [ ] Demo video
- [ ] Release notes
- [ ] Update main README with preview features

---

## 9. Testing Strategy

### 9.1 Unit Tests

| Test Suite | Coverage |
|------------|----------|
| `StreamRouter` state machine | All transitions (IDLE ↔ PREVIEW ↔ LIVE) |
| Preview API endpoints | Success/failure cases, validation |
| HLS health checks | MediaMTX up/down scenarios |

### 9.2 Integration Tests

| Test Case | Description |
|-----------|-------------|
| **Preview Lifecycle** | Start preview → play HLS → stop preview |
| **Go Live Workflow** | Preview → select destinations → go live → verify RTMP output |
| **Preview Server Crash** | Kill MediaMTX → verify health check fails → restart server |
| **Concurrent Prevention** | Start preview twice → second request rejected |

### 9.3 End-to-End Tests

| Scenario | Steps | Expected Result |
|----------|-------|----------------|
| **Basic Preview** | 1. Select timeline<br>2. Click Start Preview<br>3. Verify video plays | Video appears within 5s, <2s latency |
| **Go Live to YouTube** | 1. Start preview<br>2. Select YouTube destination<br>3. Click Go Live | YouTube receives stream, no errors |
| **Preview on Pi 5** | Run preview for 30 minutes on Pi 5 | CPU <70%, no thermal throttling |
| **Network Failure** | Unplug ethernet during preview | Preview continues (local), graceful error on go-live |

### 9.4 Performance Benchmarks

| Metric | Measurement Method | Target |
|--------|-------------------|--------|
| **Latency** | Timer in video frame → HLS player timestamp | <2s |
| **CPU Usage** | `top` during preview + live streaming | <80% total |
| **Memory Usage** | `free -h` before/after preview | <200MB additional |
| **HLS Segment Generation** | MediaMTX logs | 1-2s per segment |

---

## 10. Deployment Checklist

### 10.1 Development Environment (Mac)

```bash
# 1. Install MediaMTX
brew install mediamtx  # If available
# OR download binary from GitHub releases

# 2. Configure MediaMTX
cp docs/mediamtx.yml /usr/local/etc/mediamtx.yml
mediamtx /usr/local/etc/mediamtx.yml &

# 3. Install frontend dependencies
cd frontend
npm install hls.js

# 4. Start backend
cd backend
source ../venv/bin/activate
python start.py

# 5. Test preview
# Open http://localhost:3000, select timeline, click Start Preview
```

### 10.2 Production Deployment (Raspberry Pi 5)

```bash
# 1. Install MediaMTX
wget https://github.com/bluenviron/mediamtx/releases/download/v1.3.0/mediamtx_v1.3.0_linux_arm64v8.tar.gz
tar -xzf mediamtx_v1.3.0_linux_arm64v8.tar.gz
sudo mv mediamtx /usr/local/bin/
sudo mkdir -p /etc/vistterstream
sudo mv mediamtx.yml /etc/vistterstream/

# 2. Create systemd service
sudo tee /etc/systemd/system/vistterstream-preview.service << 'EOF'
[Unit]
Description=VistterStream Preview Server
After=network.target

[Service]
Type=simple
User=pi
ExecStart=/usr/local/bin/mediamtx /etc/vistterstream/mediamtx.yml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 3. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable vistterstream-preview
sudo systemctl start vistterstream-preview

# 4. Verify health
curl http://localhost:9997/v1/config/get

# 5. Update VistterStream backend
cd /home/pi/VistterStream/backend
source ../venv/bin/activate
pip install httpx  # If not already installed
sudo systemctl restart vistterstream

# 6. Update frontend
cd ../frontend
npm install hls.js
npm run build
# Serve from backend static files
```

### 10.3 Verification Steps

```bash
# 1. Check MediaMTX is running
ps aux | grep mediamtx
curl http://localhost:9997/v1/config/get

# 2. Test RTMP ingest
ffmpeg -re -i /path/to/test/video.mp4 \
  -c copy -f flv rtmp://localhost:1935/preview/stream

# 3. Test HLS playback
curl http://localhost:8888/preview/index.m3u8
# Should return HLS manifest

# 4. Check VistterStream logs
journalctl -u vistterstream -f
# Look for "Preview server health: OK"

# 5. Test preview in browser
# Open http://<pi-ip>:8000
# Go to Timeline Editor
# Click Start Preview
```

---

## 11. Operational Runbook

### 11.1 Common Issues

| Issue | Symptoms | Resolution |
|-------|----------|------------|
| **Preview won't start** | "Preview server not running" error | Check MediaMTX: `systemctl status vistterstream-preview`<br>Restart: `sudo systemctl restart vistterstream-preview` |
| **Black screen in preview** | Player loads but no video | Check FFmpeg is pushing RTMP: `curl http://localhost:9997/v1/paths/list`<br>Verify timeline is running: `/api/timeline-execution/status/{id}` |
| **High latency (>5s)** | Video delayed significantly | Reduce HLS segment duration in mediamtx.yml<br>Check network: `ping localhost` (should be <1ms)<br>Check CPU: `top` (should be <80%) |
| **Go Live fails** | Error message on transition | Verify destinations configured: `/api/destinations`<br>Check stream keys are valid<br>Test manual RTMP push to destination |
| **MediaMTX crashes** | Preview server health check fails | Check logs: `journalctl -u vistterstream-preview`<br>Restart service: `sudo systemctl restart vistterstream-preview`<br>Check disk space: `df -h` |

### 11.2 Monitoring

**Key Metrics to Watch**:

```bash
# CPU usage (should be <80% during preview + live)
top -p $(pgrep mediamtx)

# Memory usage
ps aux | grep mediamtx | awk '{print $6}'

# Disk usage (HLS segments can accumulate)
du -sh /tmp/mediamtx/

# Active streams
curl -s http://localhost:9997/v1/paths/list | jq '.paths[].name'

# Preview server uptime
systemctl status vistterstream-preview | grep Active
```

**Alerts to Configure**:
- MediaMTX service down → restart automatically (systemd does this)
- CPU >90% for >30s → log warning, consider reducing preview quality
- Disk usage >90% → clean up old HLS segments
- Preview latency >5s → investigate network or encoding issues

### 11.3 Maintenance

**Weekly Tasks**:
- Check MediaMTX logs for errors: `journalctl -u vistterstream-preview --since "1 week ago"`
- Verify preview server health: `curl http://localhost:9997/v1/config/get`
- Test go-live workflow with test stream key

**Monthly Tasks**:
- Update MediaMTX to latest stable release
- Review HLS segment cleanup (ensure old segments deleted)
- Performance benchmark: measure latency and CPU usage

---

## 12. Future Enhancements

### 12.1 Seamless Go-Live (Phase 2)

**Problem**: Current implementation restarts the timeline when going live.

**Solution**: Use FFmpeg dynamic output switching.

```bash
# Use FFmpeg's tee muxer to add outputs dynamically
# Requires FFmpeg compiled with network protocol support
ffmpeg -i <input> \
  -f tee "rtmp://localhost:1935/preview/stream|[f=flv:rtmp_live=live]rtmp://youtube.com/<key>"
```

**Challenges**:
- FFmpeg doesn't support dynamic tee output changes
- Would require custom FFmpeg wrapper or patch
- Alternative: Use intermediate RTMP relay (e.g., SRS)

**Timeline**: Q1 2026

### 12.2 Multi-User Preview (Phase 3)

**Feature**: Allow multiple operators to view preview simultaneously.

**Architecture**:
- MediaMTX already supports multiple HLS clients
- Add session management to track viewers
- Implement access control (optional authentication)

**Benefits**:
- Remote producer can preview before approving go-live
- Training/demo scenarios with multiple viewers

**Timeline**: Q2 2026

### 12.3 DVR / Instant Replay (Phase 3)

**Feature**: Record last N minutes of preview for instant replay.

**Implementation**:
- Configure MediaMTX to record HLS segments
- Add UI scrubber to seek backward
- Implement "clip" feature to save highlights

**Use Cases**:
- Review previous camera angles
- Verify overlay timing
- Create social media clips

**Timeline**: Q2 2026

### 12.4 WebRTC Preview (Phase 4)

**Feature**: Replace HLS with WebRTC for sub-second latency.

**Benefits**:
- <500ms latency (vs. 2s for HLS)
- Better for interactive workflows

**Challenges**:
- Browser compatibility (Safari WebRTC limitations)
- NAT traversal (STUN/TURN servers)
- More complex implementation

**Timeline**: Q3 2026

---

## 13. Success Metrics

### 13.1 Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Preview Latency** | <2s (P95) | Video timestamp → HLS player |
| **Go-Live Success Rate** | >99% | Successful transitions / total attempts |
| **Preview Server Uptime** | >99% | Uptime checks over 30 days |
| **CPU Overhead** | <15% additional | CPU usage delta (preview on vs. off) |
| **Time to Preview** | <5s | Click "Start Preview" → video visible |

### 13.2 User Experience Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Operator Satisfaction** | >4.5/5 | Post-release survey |
| **Time Saved per Stream** | >10 minutes | Comparison to manual testing |
| **Support Tickets** | <5/month | Preview-related issues |
| **Feature Adoption** | >80% | Operators using preview before go-live |

### 13.3 Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Reduced Stream Errors** | -50% | Live stream failures before/after |
| **Faster Timeline Creation** | -30% | Time to create+test timeline |
| **Operator Confidence** | >90% | "I trust preview to match live" |

---

## 14. Dependencies & Assumptions

### 14.1 External Dependencies

| Dependency | Version | Purpose | Risk Mitigation |
|------------|---------|---------|-----------------|
| **MediaMTX** | v1.3.0+ | Preview server (RTMP→HLS) | Fallback to FFmpeg-only solution |
| **HLS.js** | v1.4.0+ | Browser HLS playback | Native HLS for Safari |
| **FFmpeg** | 5.1+ | Video processing | Already required by VistterStream |
| **httpx** | 0.24+ | Python HTTP client | Standard async library |

### 14.2 Assumptions

1. **Single Operator**: Preview system assumes one operator per appliance (no multi-user coordination)
2. **Local Network**: Preview HLS served on localhost only (no external access)
3. **Browser Compatibility**: Operator uses modern browser (Chrome 90+, Safari 14+)
4. **Hardware Capacity**: Raspberry Pi 5 can handle preview + live streaming (validated in testing)
5. **Timeline Restart Acceptable**: Operators accept timeline restart on go-live (seamless transition is future work)

### 14.3 Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Preview latency >2s** | Medium | High | Use 1s HLS segments, low-latency mode, measure early |
| **MediaMTX crashes** | Low | Medium | Systemd auto-restart, health monitoring |
| **Go-live fails** | Low | High | Validate destinations before go-live, fallback to direct streaming |
| **CPU overload on Pi** | Medium | High | Performance testing, adaptive quality reduction |
| **HLS.js compatibility** | Low | Medium | Fallback to native HLS (Safari) |

---

## 15. Open Questions

1. **Seamless Go-Live**: Is timeline restart acceptable for MVP, or is seamless transition a hard requirement?
   - **Recommendation**: Accept restart for MVP, plan seamless for Phase 2.

2. **Preview Recording**: Should preview always be recorded for DVR / post-analysis?
   - **Recommendation**: Optional feature for Phase 3 (adds disk usage).

3. **Multi-Preview**: Support multiple preview "channels" (e.g., preview different timelines simultaneously)?
   - **Recommendation**: Out of scope (single-operator appliance).

4. **Authentication**: Should preview HLS require authentication even on localhost?
   - **Recommendation**: No for MVP (localhost trust boundary), revisit if remote access added.

5. **Quality Presets**: Should operators choose preview quality (low/medium/high) to save CPU?
   - **Recommendation**: Phase 2 enhancement (auto-adjust based on load).

---

## 16. Traceability Matrix

### 16.1 Alignment with Product Goals

| PRD Goal | Preview System Feature |
|----------|------------------------|
| **Preserve local camera investments** | Preview uses same camera infrastructure |
| **Deliver broadcast-ready streams** | Preview verifies overlay sync before live |
| **Remain self-reliant offline** | Preview works without internet |
| **Provide operational transparency** | Preview status visible in UI |

### 16.2 Integration with Existing Architecture

| SAD Component | Preview System Integration |
|---------------|----------------------------|
| **Timeline Orchestrator** | Outputs to preview server via StreamRouter |
| **Stream Engine (FFmpeg)** | Reuses existing encoding pipeline |
| **Web/API Gateway** | Adds `/api/preview` router |
| **Frontend Timeline Editor** | Embeds PreviewWindow component |

### 16.3 Requirements Coverage

| Use Case | Preview Requirements Covered |
|----------|------------------------------|
| **UC-05: Timeline Synchronization** | Preview verifies timeline before VistterStudio push |
| **UC-06: Manual Stream Control** | Preview → Go Live replaces direct manual control |
| **UC-08: Overlay Scene Playback** | Preview shows overlays before live |

---

## 17. Appendices

### Appendix A: MediaMTX Configuration Reference

**Full Configuration File**: See Section 4.2

**Key Settings Explained**:

```yaml
hlsSegmentDuration: 1s   # Shorter = lower latency, more CPU
hlsSegmentCount: 3       # Keep only 3 segments (rolling buffer)
hlsPartDuration: 200ms   # LL-HLS support for <1s latency (future)
hlsAllowOrigin: "*"      # CORS for browser access
```

**Tuning for Latency**:
- Reduce `hlsSegmentDuration` to 0.5s for <1s latency (increases CPU)
- Increase to 2s for lower CPU usage (increases latency to 3-4s)

### Appendix B: HLS.js Configuration Reference

**Low-Latency Configuration**:

```typescript
const hls = new Hls({
  maxBufferLength: 2,          // Max 2s of video buffered
  maxMaxBufferLength: 4,       // Emergency max buffer
  liveSyncDuration: 1,         // Sync to 1s from live edge
  liveMaxLatencyDuration: 3,   // Max 3s behind live
  lowLatencyMode: true,        // Enable LL-HLS features
  backBufferLength: 0          // Don't keep old segments
});
```

**Troubleshooting**:
- If playback stutters → increase `maxBufferLength` to 4
- If latency too high → reduce `liveSyncDuration` to 0.5

### Appendix C: FFmpeg RTMP Push Examples

**Test Preview Server Manually**:

```bash
# Push test video to preview server
ffmpeg -re -i test-video.mp4 \
  -c:v h264_v4l2m2m -b:v 4500k \
  -c:a aac -b:a 128k \
  -f flv rtmp://localhost:1935/preview/stream

# Push camera feed
ffmpeg -rtsp_transport tcp -i rtsp://camera.local/stream \
  -c:v h264_v4l2m2m -b:v 4500k \
  -f flv rtmp://localhost:1935/preview/stream
```

**Monitor HLS Output**:

```bash
# Check HLS manifest
curl http://localhost:8888/preview/index.m3u8

# Download and play HLS stream
ffplay http://localhost:8888/preview/index.m3u8

# Measure latency (requires timestamp overlay in source)
# Compare source timestamp to HLS player timestamp
```

### Appendix D: API Examples

**Start Preview**:

```bash
curl -X POST http://localhost:8000/api/preview/start \
  -H "Content-Type: application/json" \
  -d '{"timeline_id": 1}'
```

**Check Status**:

```bash
curl http://localhost:8000/api/preview/status
```

**Go Live**:

```bash
curl -X POST http://localhost:8000/api/preview/go-live \
  -H "Content-Type: application/json" \
  -d '{"destination_ids": [1, 2]}'
```

---

## 18. Approval & Sign-Off

| Role | Name | Approval Date | Signature |
|------|------|---------------|-----------|
| **Product Manager** | [TBD] | [TBD] | [ ] |
| **Tech Lead** | [TBD] | [TBD] | [ ] |
| **Frontend Lead** | [TBD] | [TBD] | [ ] |
| **Backend Lead** | [TBD] | [TBD] | [ ] |
| **QA Lead** | [TBD] | [TBD] | [ ] |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-04 | Platform Team | Initial draft for implementation |

---

**END OF SPECIFICATION**

