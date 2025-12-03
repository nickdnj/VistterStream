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
from services.youtube_api_helper import YouTubeAPIHelper, YouTubeAPIError
from services.youtube_oauth import DatabaseYouTubeTokenProvider
from datetime import datetime
import logging

router = APIRouter(prefix="/api/timeline-execution", tags=["timeline-execution"])
logger = logging.getLogger(__name__)


class StartTimelineRequest(BaseModel):
    timeline_id: int
    destination_ids: list[int]  # List of destination IDs to stream to
    encoding_profile: Optional[dict] = None  # Optional custom encoding


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
    
    output_urls = [dest.get_full_rtmp_url() for dest in destinations]
    destination_names = [dest.name for dest in destinations]
    
    # Mark destinations as used
    for dest in destinations:
        dest.last_used = datetime.utcnow()
    db.commit()
    
    # Auto-reset YouTube broadcasts if they're in "complete" state
    # This allows streams to restart without manual intervention
    for dest in destinations:
        if (dest.platform == "youtube" and 
            dest.youtube_oauth_connected and 
            dest.youtube_broadcast_id):
            try:
                logger.info(f"Checking YouTube broadcast status for destination {dest.id} ({dest.name})")
                provider = DatabaseYouTubeTokenProvider(dest)
                helper = YouTubeAPIHelper(token_provider=provider)
                
                async with helper:
                    # Check current broadcast status
                    status = await helper.get_broadcast_status(dest.youtube_broadcast_id)
                    current_status = status.get('life_cycle_status', 'unknown')
                    
                    logger.info(f"Broadcast {dest.youtube_broadcast_id} status: {current_status}")
                    
                    # If broadcast is "complete", reset it to allow new stream
                    if current_status == 'complete':
                        logger.warning(
                            f"Broadcast {dest.youtube_broadcast_id} is in 'complete' state. "
                            f"Auto-resetting to allow stream restart..."
                        )
                        # Reset broadcast (complete → testing → live)
                        reset_result = await helper.reset_broadcast(dest.youtube_broadcast_id)
                        logger.info(
                            f"Broadcast reset successful. New status: {reset_result.get('life_cycle_status')}"
                        )
                    elif current_status == 'live':
                        logger.info(f"Broadcast is already live, no reset needed")
                    elif current_status == 'testing':
                        # Transition from testing to live
                        logger.info(f"Broadcast is in testing, transitioning to live...")
                        await helper.transition_broadcast(dest.youtube_broadcast_id, 'live')
                        logger.info("Broadcast transitioned to live")
                    else:
                        logger.info(f"Broadcast status is '{current_status}', no action needed")
                        
            except YouTubeAPIError as e:
                logger.warning(
                    f"Failed to check/reset YouTube broadcast for destination {dest.id}: {e}. "
                    f"Stream will attempt to start anyway."
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error checking YouTube broadcast for destination {dest.id}: {e}",
                    exc_info=True
                )
                # Don't fail the timeline start if broadcast check fails
    
    # TEMP: Back to old executor - seamless needs more debugging
    executor = get_timeline_executor()
    
    # Start timeline
    success = await executor.start_timeline(
        timeline_id=request.timeline_id,
        output_urls=output_urls,
        encoding_profile=None,  # TODO: Support custom encoding profiles
        destination_names=destination_names,
        destination_ids=request.destination_ids
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

