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
from datetime import datetime, timezone
import logging
from routers.auth import get_current_user

router = APIRouter(prefix="/api/timeline-execution", tags=["timeline-execution"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


class StartTimelineRequest(BaseModel):
    timeline_id: int
    destination_ids: list[int]  # List of destination IDs to stream to
    encoding_profile: Optional[dict] = None  # Optional custom encoding
    start_position: Optional[float] = None  # Start from this time offset (seconds)


class TimelineStatusResponse(BaseModel):
    timeline_id: int
    is_running: bool
    timeline_name: Optional[str] = None
    destination_ids: Optional[list[int]] = None


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

    # Auto-create YouTube broadcasts for OAuth destinations (always fresh per stream start)
    for dest in destinations:
        if dest.platform == "youtube_oauth" and dest.youtube_oauth_connected and dest.youtube_oauth_refresh_token_enc:
            try:
                from services.youtube_destination_service import (
                    get_credentials, create_broadcast, capture_and_upload_broadcast_thumbnail,
                )
                from utils.crypto import decrypt
                client_secret = decrypt(dest.youtube_oauth_client_secret_enc)
                refresh_token = decrypt(dest.youtube_oauth_refresh_token_enc)
                credentials = get_credentials(
                    client_id=dest.youtube_oauth_client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                )
                broadcast_title = timeline.broadcast_title or timeline.name
                broadcast_desc = timeline.broadcast_description or ""
                privacy_status = timeline.broadcast_privacy or "public"
                tags = [t.strip() for t in (timeline.broadcast_tags or "").split(",") if t.strip()] or None
                category_id = timeline.broadcast_category_id or None
                result = create_broadcast(
                    credentials=credentials,
                    title=broadcast_title,
                    description=broadcast_desc,
                    privacy_status=privacy_status,
                    create_stream=True,
                    enable_dvr=False,
                    tags=tags,
                    category_id=category_id,
                )
                dest.youtube_broadcast_id = result.get("broadcast_id")
                dest.youtube_stream_id = result.get("stream_id")
                if result.get("stream_key"):
                    dest.stream_key = result["stream_key"]
                if result.get("rtmp_url"):
                    dest.rtmp_url = result["rtmp_url"]
                if result.get("watch_url"):
                    dest.youtube_watch_url = result["watch_url"]
                logger.info("Auto-created YouTube broadcast %s for destination %s", result.get("broadcast_id"), dest.name)
                # Upload thumbnail if enabled
                if timeline.broadcast_thumbnail_enabled and result.get("broadcast_id"):
                    try:
                        await capture_and_upload_broadcast_thumbnail(
                            db, timeline, credentials, result["broadcast_id"],
                        )
                    except Exception as thumb_err:
                        logger.warning("Broadcast thumbnail upload failed (non-fatal): %s", thumb_err)
            except Exception as e:
                logger.error("Failed to auto-create broadcast for %s: %s", dest.name, e)
                raise HTTPException(status_code=500, detail=f"Failed to create YouTube broadcast for {dest.name}: {e}")

    output_urls = [dest.get_full_rtmp_url() for dest in destinations]
    destination_names = [dest.name for dest in destinations]

    # Mark destinations as used
    for dest in destinations:
        dest.last_used = datetime.now(timezone.utc)
    db.commit()
    
    # TEMP: Back to old executor - seamless needs more debugging
    executor = get_timeline_executor()
    
    # Start timeline
    success = await executor.start_timeline(
        timeline_id=request.timeline_id,
        output_urls=output_urls,
        encoding_profile=None,  # TODO: Support custom encoding profiles
        destination_names=destination_names,
        destination_ids=request.destination_ids,
        start_position=request.start_position
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

    # Clear stale broadcast IDs so the next start creates a fresh broadcast
    dest_ids = getattr(executor, 'timeline_destination_ids', {}).get(timeline_id) or []
    if dest_ids:
        dests = db.query(StreamingDestination).filter(
            StreamingDestination.id.in_(dest_ids)
        ).all()
    else:
        # Fallback: clear all OAuth destinations that have a broadcast
        dests = db.query(StreamingDestination).filter(
            StreamingDestination.platform == "youtube_oauth",
            StreamingDestination.youtube_broadcast_id.isnot(None),
        ).all()
    for dest in dests:
        if dest.platform == "youtube_oauth" and dest.youtube_broadcast_id:
            logger.info("Clearing broadcast %s for destination %s after stop", dest.youtube_broadcast_id, dest.name)
            dest.youtube_broadcast_id = None
            dest.youtube_stream_id = None
            dest.youtube_watch_url = None
    if dests:
        db.commit()

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
    
    # Get destination IDs if running
    destination_ids = None
    if is_running and hasattr(executor, 'timeline_destination_ids'):
        destination_ids = executor.timeline_destination_ids.get(timeline_id)
    
    return {
        "timeline_id": timeline_id,
        "is_running": is_running,
        "timeline_name": timeline.name,
        "destination_ids": destination_ids
    }


@router.get("/active")
async def get_active_timelines():
    """Get all currently running timelines"""
    executor = get_timeline_executor()
    
    return {
        "active_timeline_ids": list(executor.active_timelines.keys()),
        "count": len(executor.active_timelines)
    }

