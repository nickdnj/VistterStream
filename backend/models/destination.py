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
    
    # Optional metadata
    description = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime)
    
    def get_full_rtmp_url(self) -> str:
        """Get the complete RTMP URL with stream key"""
        return f"{self.rtmp_url}/{self.stream_key}"

