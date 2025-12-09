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


class YouTubeWatchdogConfig(BaseModel):
    enable_watchdog: bool = True
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
    platform: str
    rtmp_url: str
    stream_key: str
    description: str = ""
    channel_id: Optional[str] = None
    enable_watchdog: bool = True
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
    stream_key: str
    description: str
    channel_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime] = None
    enable_watchdog: bool = True
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


PLATFORM_PRESETS = {
    "youtube": {"name": "YouTube Live", "rtmp_url": "rtmp://a.rtmp.youtube.com/live2", "description": "YouTube Live"},
    "facebook": {"name": "Facebook Live", "rtmp_url": "rtmps://live-api-s.facebook.com:443/rtmp", "description": "Facebook Live"},
    "twitch": {"name": "Twitch", "rtmp_url": "rtmp://live.twitch.tv/app", "description": "Twitch"},
    "custom": {"name": "Custom RTMP", "rtmp_url": "", "description": "Custom RTMP server"}
}


@router.get("/presets")
def get_platform_presets():
    return PLATFORM_PRESETS


@router.get("", response_model=List[DestinationResponse])
def get_destinations(db: Session = Depends(get_db)):
    return db.query(StreamingDestination).order_by(StreamingDestination.created_at.desc()).all()


@router.get("/{destination_id}", response_model=DestinationResponse)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    dest = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    return dest


@router.post("", response_model=DestinationResponse)
def create_destination(data: DestinationCreate, db: Session = Depends(get_db)):
    dest = StreamingDestination(
        name=data.name, platform=data.platform, rtmp_url=data.rtmp_url, stream_key=data.stream_key,
        description=data.description, channel_id=data.channel_id, enable_watchdog=data.enable_watchdog,
        youtube_api_key=data.youtube_api_key, youtube_stream_id=data.youtube_stream_id,
        youtube_broadcast_id=data.youtube_broadcast_id, youtube_watch_url=data.youtube_watch_url,
        watchdog_check_interval=data.watchdog_check_interval, watchdog_enable_frame_probe=data.watchdog_enable_frame_probe,
        watchdog_enable_daily_reset=data.watchdog_enable_daily_reset, watchdog_daily_reset_hour=data.watchdog_daily_reset_hour
    )
    db.add(dest)
    db.commit()
    db.refresh(dest)
    return dest


@router.put("/{destination_id}", response_model=DestinationResponse)
def update_destination(destination_id: int, data: DestinationUpdate, db: Session = Depends(get_db)):
    dest = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dest, field, value)
    dest.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(dest)
    return dest


@router.delete("/{destination_id}")
def delete_destination(destination_id: int, db: Session = Depends(get_db)):
    dest = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    db.delete(dest)
    db.commit()
    return {"message": "Destination deleted"}


@router.post("/{destination_id}/mark-used")
def mark_destination_used(destination_id: int, db: Session = Depends(get_db)):
    dest = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    dest.last_used = datetime.utcnow()
    db.commit()
    return {"message": "Marked as used"}


@router.get("/{destination_id}/watchdog-config", response_model=YouTubeWatchdogConfig)
def get_watchdog_config(destination_id: int, db: Session = Depends(get_db)):
    dest = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    return YouTubeWatchdogConfig(
        enable_watchdog=dest.enable_watchdog or False, youtube_api_key=dest.youtube_api_key,
        youtube_stream_id=dest.youtube_stream_id, youtube_broadcast_id=dest.youtube_broadcast_id,
        youtube_watch_url=dest.youtube_watch_url, watchdog_check_interval=dest.watchdog_check_interval or 30,
        watchdog_enable_frame_probe=dest.watchdog_enable_frame_probe or False,
        watchdog_enable_daily_reset=dest.watchdog_enable_daily_reset or False,
        watchdog_daily_reset_hour=dest.watchdog_daily_reset_hour or 3
    )


@router.put("/{destination_id}/watchdog-config", response_model=YouTubeWatchdogConfig)
def update_watchdog_config(destination_id: int, config: YouTubeWatchdogConfig, db: Session = Depends(get_db)):
    dest = db.query(StreamingDestination).filter(StreamingDestination.id == destination_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    dest.enable_watchdog = config.enable_watchdog
    dest.youtube_api_key = config.youtube_api_key
    dest.youtube_stream_id = config.youtube_stream_id
    dest.youtube_broadcast_id = config.youtube_broadcast_id
    dest.youtube_watch_url = config.youtube_watch_url
    dest.watchdog_check_interval = config.watchdog_check_interval
    dest.watchdog_enable_frame_probe = config.watchdog_enable_frame_probe
    dest.watchdog_enable_daily_reset = config.watchdog_enable_daily_reset
    dest.watchdog_daily_reset_hour = config.watchdog_daily_reset_hour
    dest.updated_at = datetime.utcnow()
    db.commit()
    return config
