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
    name = Column(String, nullable=False)  # "My YouTube Channel", "Facebook Page", etc.
    platform = Column(String, nullable=False)  # "youtube", "facebook", "twitch", "custom"
    
    # RTMP configuration
    rtmp_url = Column(String, nullable=False)  # Base RTMP server URL
    stream_key = Column(String, nullable=False)  # Stream key (encrypted in production)
    channel_id = Column(String)  # Channel/account identifier
    
    # Optional metadata
    description = Column(String)
    is_active = Column(Boolean, default=True)
    
    # YouTube-specific watchdog configuration
    # These fields are only used when platform="youtube" and enable_watchdog=True
    enable_watchdog = Column(Boolean, default=False)
    youtube_api_key = Column(String)  # YouTube Data API v3 key (optional, can use system-wide)
    youtube_stream_id = Column(String)  # YouTube stream resource ID
    youtube_broadcast_id = Column(String)  # YouTube broadcast ID
    youtube_watch_url = Column(String)  # Public watch URL for frame probing
    
    # Watchdog settings (defaults match watchdog service)
    watchdog_check_interval = Column(Integer, default=30)  # Seconds between health checks
    watchdog_enable_frame_probe = Column(Boolean, default=False)  # Verify actual video frames
    watchdog_enable_daily_reset = Column(Boolean, default=False)  # Daily broadcast reset
    watchdog_daily_reset_hour = Column(Integer, default=3)  # UTC hour for daily reset (0-23)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime)
    
    def get_full_rtmp_url(self) -> str:
        """Get the complete RTMP URL with stream key"""
        return f"{self.rtmp_url}/{self.stream_key}"

