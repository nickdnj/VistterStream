"""
Streaming destination models
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from .database import Base


class StreamingDestination(Base):
    """Configured streaming destinations (YouTube, Facebook, Twitch, etc.)"""
    __tablename__ = "streaming_destinations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    
    # RTMP configuration
    rtmp_url = Column(String, nullable=False)
    stream_key = Column(String, nullable=False)
    channel_id = Column(String)
    
    # Optional metadata
    description = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Watchdog configuration
    enable_watchdog = Column(Boolean, default=True)
    youtube_api_key = Column(String)
    youtube_stream_id = Column(String)
    youtube_broadcast_id = Column(String)
    youtube_watch_url = Column(String)
    watchdog_check_interval = Column(Integer, default=30)
    watchdog_enable_frame_probe = Column(Boolean, default=False)
    watchdog_enable_daily_reset = Column(Boolean, default=False)
    watchdog_daily_reset_hour = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime)
    
    def get_full_rtmp_url(self) -> str:
        return f"{self.rtmp_url}/{self.stream_key}"
