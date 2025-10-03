"""
Timeline execution API endpoints (start/stop/status)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from models.database import get_db
from models.timeline import Timeline
from models.destination import StreamingDestination
from services.timeline_executor import get_timeline_executor
from services.seamless_timeline_executor import get_seamless_timeline_executor
from services.ffmpeg_manager import EncodingProfile
from datetime import datetime

router = APIRouter(prefix="/api/timeline-execution", tags=["timeline-execution"])


class StartTimelineRequest(BaseModel):
    timeline_id: int
    destination_ids: list[int]  # List of destination IDs to stream to
    encoding_profile: Optional[dict] = None  # Optional custom encoding


class TimelineStatusResponse(BaseModel):
    timeline_id: int
    is_running: bool
    timeline_name: Optional[str] = None


@router.post("/start")
async def start_timeline(request: StartTimelineRequest, db: Session = Depends(get_db)):
    """Start executing a timeline with configured destinations"""
    
    # Verify timeline exists
    timeline = db.query(Timeline).filter(Timeline.id == request.timeline_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    # Get destinations and build output URLs
    destinations = db.query(StreamingDestination).filter(
        StreamingDestination.id.in_(request.destination_ids)
    ).all()
    
    if not destinations:
        raise HTTPException(status_code=404, detail="No valid destinations found")
    
    output_urls = [dest.get_full_rtmp_url() for dest in destinations]
    destination_names = [dest.name for dest in destinations]
    
    # Mark destinations as used
    for dest in destinations:
        dest.last_used = datetime.utcnow()
    db.commit()
    
    # TEMP: Back to old executor - seamless needs more debugging
    executor = get_timeline_executor()
    
    # Start timeline
    success = await executor.start_timeline(
        timeline_id=request.timeline_id,
        output_urls=output_urls,
        encoding_profile=None  # TODO: Support custom encoding profiles
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Timeline is already running")
    
    return {
        "message": "Timeline started successfully",
        "timeline_id": request.timeline_id,
        "timeline_name": timeline.name,
        "destinations": destination_names,
        "output_count": len(output_urls)
    }


@router.post("/stop/{timeline_id}")
async def stop_timeline(timeline_id: int, db: Session = Depends(get_db)):
    """Stop a running timeline"""
    
    # Verify timeline exists
    timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    # TEMP: Back to old executor
    executor = get_timeline_executor()
    
    # Stop timeline
    success = await executor.stop_timeline(timeline_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Timeline is not running")
    
    return {
        "message": "Timeline stopped successfully",
        "timeline_id": timeline_id
    }


@router.get("/status/{timeline_id}", response_model=TimelineStatusResponse)
async def get_timeline_status(timeline_id: int, db: Session = Depends(get_db)):
    """Get the execution status of a timeline"""
    
    # Verify timeline exists
    timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    # Get executor
    executor = get_timeline_executor()
    
    # Check if running
    is_running = timeline_id in executor.active_timelines
    
    return {
        "timeline_id": timeline_id,
        "is_running": is_running,
        "timeline_name": timeline.name
    }


@router.get("/active")
async def get_active_timelines():
    """Get all currently running timelines"""
    executor = get_timeline_executor()
    
    return {
        "active_timeline_ids": list(executor.active_timelines.keys()),
        "count": len(executor.active_timelines)
    }

