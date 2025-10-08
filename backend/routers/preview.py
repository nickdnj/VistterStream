"""
Preview Control API
Manages local preview workflow: start preview, stop preview, go live

See: docs/PreviewSystem-Specification.md Section 4.3
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
from services.timeline_executor import get_playback_position

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
            detail="Preview server is not running. Please start MediaMTX or check system status."
        )
    
    # Start preview via stream router
    router_service = get_stream_router()
    try:
        await router_service.start_preview(timeline_id=request.timeline_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    
    try:
        await router_service.stop()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop preview: {str(e)}")
    
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
            detail="Preview server is not responding. Please start MediaMTX."
        )
    
    streams = await health.get_active_streams()
    items = streams.get("items", {})
    
    # Format stream info for response
    active_streams = []
    for name, info in items.items():
        if info.get("ready"):
            active_streams.append({
                "name": name,
                "ready": True,
                "num_readers": info.get("numReaders", 0)
            })
    
    return {
        "status": "healthy",
        "active_streams": active_streams,
        "total_streams": len(items)
    }


@router.get("/playback-position")
async def get_preview_playback_position():
    """
    Get current playback position for preview timeline.
    Returns current cue index and timeline time.
    """
    router_service = get_stream_router()
    
    if router_service.mode != PreviewMode.PREVIEW or not router_service.timeline_id:
        return {
            "is_playing": False,
            "position": None
        }
    
    position = get_playback_position(router_service.timeline_id)
    
    return {
        "is_playing": True,
        "timeline_id": router_service.timeline_id,
        "position": position
    }
