"""
Streaming Destinations API - Configure YouTube, Facebook, Twitch, etc.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from models.database import get_db
from models.destination import StreamingDestination

router = APIRouter(prefix="/api/destinations", tags=["destinations"])


# Pydantic schemas
class YouTubeWatchdogConfig(BaseModel):
    """YouTube-specific watchdog configuration"""
    enable_watchdog: bool = False
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: int = 30
    watchdog_enable_frame_probe: bool = False
    watchdog_enable_daily_reset: bool = False
    watchdog_daily_reset_hour: int = 3


class DestinationCreate(BaseModel):
    name: str
    platform: str  # "youtube", "facebook", "twitch", "custom"
    rtmp_url: str
    stream_key: str
    description: str = ""
    channel_id: Optional[str] = None
    
    # YouTube watchdog configuration (optional)
    enable_watchdog: bool = False
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: int = 30
    watchdog_enable_frame_probe: bool = False
    watchdog_enable_daily_reset: bool = False
    watchdog_daily_reset_hour: int = 3


class DestinationUpdate(BaseModel):
    name: Optional[str] = None
    platform: Optional[str] = None
    rtmp_url: Optional[str] = None
    stream_key: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    channel_id: Optional[str] = None
    
    # YouTube watchdog configuration (optional)
    enable_watchdog: Optional[bool] = None
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: Optional[int] = None
    watchdog_enable_frame_probe: Optional[bool] = None
    watchdog_enable_daily_reset: Optional[bool] = None
    watchdog_daily_reset_hour: Optional[int] = None


class DestinationResponse(BaseModel):
    id: int
    name: str
    platform: str
    rtmp_url: str
    stream_key: str  # Note: In production, you might want to mask this
    description: str
    channel_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime] = None
    
    # YouTube watchdog configuration
    enable_watchdog: bool = False
    youtube_api_key: Optional[str] = None
    youtube_stream_id: Optional[str] = None
    youtube_broadcast_id: Optional[str] = None
    youtube_watch_url: Optional[str] = None
    watchdog_check_interval: int = 30
    watchdog_enable_frame_probe: bool = False
    watchdog_enable_daily_reset: bool = False
    watchdog_daily_reset_hour: int = 3
    
    class Config:
        from_attributes = True


# Platform presets for easy setup
PLATFORM_PRESETS = {
    "youtube": {
        "name": "YouTube Live",
        "rtmp_url": "rtmp://a.rtmp.youtube.com/live2",
        "description": "YouTube Live primary server"
    },
    "facebook": {
        "name": "Facebook Live",
        "rtmp_url": "rtmps://live-api-s.facebook.com:443/rtmp",
        "description": "Facebook Live streaming"
    },
    "twitch": {
        "name": "Twitch",
        "rtmp_url": "rtmp://live.twitch.tv/app",
        "description": "Twitch live streaming"
    },
    "custom": {
        "name": "Custom RTMP",
        "rtmp_url": "",
        "description": "Custom RTMP server"
    }
}


@router.get("/presets")
def get_platform_presets():
    """Get platform presets for easy setup"""
    return PLATFORM_PRESETS


@router.get("/", response_model=List[DestinationResponse])
def get_destinations(db: Session = Depends(get_db)):
    """Get all streaming destinations"""
    destinations = db.query(StreamingDestination).order_by(StreamingDestination.created_at.desc()).all()
    return destinations


@router.get("/{destination_id}", response_model=DestinationResponse)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    """Get a specific destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    return destination


@router.post("/", response_model=DestinationResponse)
def create_destination(destination_data: DestinationCreate, db: Session = Depends(get_db)):
    """Create a new streaming destination"""
    try:
        destination = StreamingDestination(
            name=destination_data.name,
            platform=destination_data.platform,
            rtmp_url=destination_data.rtmp_url,
            stream_key=destination_data.stream_key,
            description=destination_data.description,
            channel_id=destination_data.channel_id,
            # YouTube watchdog fields
            enable_watchdog=destination_data.enable_watchdog,
            youtube_api_key=destination_data.youtube_api_key,
            youtube_stream_id=destination_data.youtube_stream_id,
            youtube_broadcast_id=destination_data.youtube_broadcast_id,
            youtube_watch_url=destination_data.youtube_watch_url,
            watchdog_check_interval=destination_data.watchdog_check_interval,
            watchdog_enable_frame_probe=destination_data.watchdog_enable_frame_probe,
            watchdog_enable_daily_reset=destination_data.watchdog_enable_daily_reset,
            watchdog_daily_reset_hour=destination_data.watchdog_daily_reset_hour
        )
        db.add(destination)
        db.commit()
        db.refresh(destination)
        return destination
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create destination: {str(e)}")


@router.put("/{destination_id}", response_model=DestinationResponse)
def update_destination(
    destination_id: int,
    destination_data: DestinationUpdate,
    db: Session = Depends(get_db)
):
    """Update a streaming destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    # Update basic fields
    if destination_data.name is not None:
        destination.name = destination_data.name
    if destination_data.platform is not None:
        destination.platform = destination_data.platform
    if destination_data.rtmp_url is not None:
        destination.rtmp_url = destination_data.rtmp_url
    if destination_data.stream_key is not None:
        destination.stream_key = destination_data.stream_key
    if destination_data.description is not None:
        destination.description = destination_data.description
    if destination_data.channel_id is not None:
        destination.channel_id = destination_data.channel_id
    if destination_data.is_active is not None:
        destination.is_active = destination_data.is_active
    
    # Update YouTube watchdog fields
    if destination_data.enable_watchdog is not None:
        destination.enable_watchdog = destination_data.enable_watchdog
    if destination_data.youtube_api_key is not None:
        destination.youtube_api_key = destination_data.youtube_api_key
    if destination_data.youtube_stream_id is not None:
        destination.youtube_stream_id = destination_data.youtube_stream_id
    if destination_data.youtube_broadcast_id is not None:
        destination.youtube_broadcast_id = destination_data.youtube_broadcast_id
    if destination_data.youtube_watch_url is not None:
        destination.youtube_watch_url = destination_data.youtube_watch_url
    if destination_data.watchdog_check_interval is not None:
        destination.watchdog_check_interval = destination_data.watchdog_check_interval
    if destination_data.watchdog_enable_frame_probe is not None:
        destination.watchdog_enable_frame_probe = destination_data.watchdog_enable_frame_probe
    if destination_data.watchdog_enable_daily_reset is not None:
        destination.watchdog_enable_daily_reset = destination_data.watchdog_enable_daily_reset
    if destination_data.watchdog_daily_reset_hour is not None:
        destination.watchdog_daily_reset_hour = destination_data.watchdog_daily_reset_hour
    
    destination.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(destination)
    return destination


@router.delete("/{destination_id}")
def delete_destination(destination_id: int, db: Session = Depends(get_db)):
    """Delete a streaming destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    db.delete(destination)
    db.commit()
    return {"message": "Destination deleted successfully"}


@router.post("/{destination_id}/mark-used")
def mark_destination_used(destination_id: int, db: Session = Depends(get_db)):
    """Mark a destination as recently used (updates last_used timestamp)"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    destination.last_used = datetime.utcnow()
    db.commit()
    
    return {"message": "Destination marked as used"}


@router.get("/{destination_id}/watchdog-config", response_model=YouTubeWatchdogConfig)
def get_watchdog_config(destination_id: int, db: Session = Depends(get_db)):
    """Get YouTube watchdog configuration for a destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="Watchdog only supported for YouTube destinations")
    
    return YouTubeWatchdogConfig(
        enable_watchdog=destination.enable_watchdog or False,
        youtube_api_key=destination.youtube_api_key,
        youtube_stream_id=destination.youtube_stream_id,
        youtube_broadcast_id=destination.youtube_broadcast_id,
        youtube_watch_url=destination.youtube_watch_url,
        watchdog_check_interval=destination.watchdog_check_interval or 30,
        watchdog_enable_frame_probe=destination.watchdog_enable_frame_probe or False,
        watchdog_enable_daily_reset=destination.watchdog_enable_daily_reset or False,
        watchdog_daily_reset_hour=destination.watchdog_daily_reset_hour or 3
    )


@router.put("/{destination_id}/watchdog-config", response_model=YouTubeWatchdogConfig)
def update_watchdog_config(
    destination_id: int,
    config: YouTubeWatchdogConfig,
    db: Session = Depends(get_db)
):
    """Update YouTube watchdog configuration for a destination"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="Watchdog only supported for YouTube destinations")
    
    # Update watchdog configuration
    destination.enable_watchdog = config.enable_watchdog
    destination.youtube_api_key = config.youtube_api_key
    destination.youtube_stream_id = config.youtube_stream_id
    destination.youtube_broadcast_id = config.youtube_broadcast_id
    destination.youtube_watch_url = config.youtube_watch_url
    destination.watchdog_check_interval = config.watchdog_check_interval
    destination.watchdog_enable_frame_probe = config.watchdog_enable_frame_probe
    destination.watchdog_enable_daily_reset = config.watchdog_enable_daily_reset
    destination.watchdog_daily_reset_hour = config.watchdog_daily_reset_hour
    destination.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(destination)
    
    return config


@router.post("/{destination_id}/validate-watchdog")
async def validate_watchdog_config(destination_id: int, db: Session = Depends(get_db)):
    """Validate YouTube watchdog configuration by testing API connectivity"""
    destination = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="Watchdog only supported for YouTube destinations")
    
    if not destination.enable_watchdog:
        raise HTTPException(status_code=400, detail="Watchdog is not enabled for this destination")
    
    # Validate required fields
    missing_fields = []
    if not destination.youtube_api_key:
        missing_fields.append("youtube_api_key")
    if not destination.youtube_stream_id:
        missing_fields.append("youtube_stream_id")
    if not destination.youtube_broadcast_id:
        missing_fields.append("youtube_broadcast_id")
    if not destination.youtube_watch_url:
        missing_fields.append("youtube_watch_url")
    
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing_fields)}"
        )
    
    # Test API connectivity
    try:
        from services.youtube_api_helper import YouTubeAPIHelper, YouTubeAPIError
        
        async with YouTubeAPIHelper(destination.youtube_api_key) as api:
            # Test stream health
            try:
                stream_health = await api.get_stream_health(destination.youtube_stream_id)
                stream_status = "OK"
                stream_message = f"Stream health: {stream_health['status']}"
            except YouTubeAPIError as e:
                stream_status = "ERROR"
                stream_message = f"Stream check failed: {str(e)}"
            
            # Test broadcast status
            try:
                broadcast_status = await api.get_broadcast_status(destination.youtube_broadcast_id)
                broadcast_status_result = "OK"
                broadcast_message = f"Broadcast status: {broadcast_status['life_cycle_status']}"
            except YouTubeAPIError as e:
                broadcast_status_result = "ERROR"
                broadcast_message = f"Broadcast check failed: {str(e)}"
            
            overall_status = "OK" if stream_status == "OK" and broadcast_status_result == "OK" else "ERROR"
            
            return {
                "status": overall_status,
                "stream_check": {
                    "status": stream_status,
                    "message": stream_message
                },
                "broadcast_check": {
                    "status": broadcast_status_result,
                    "message": broadcast_message
                },
                "message": "Validation complete" if overall_status == "OK" else "Validation failed - check details"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")

