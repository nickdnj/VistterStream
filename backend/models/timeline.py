"""
Timeline models for composite streams with camera switching
Based on docs/StreamingPipeline-TechnicalSpec.md Multi-Track Timeline System
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Timeline(Base):
    """Timeline for composite streams"""
    __tablename__ = "timelines"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    duration = Column(Float, nullable=False)  # Total duration in seconds
    fps = Column(Integer, default=30)
    resolution = Column(String, default="1920x1080")
    loop = Column(Boolean, default=True)  # Loop forever or play once
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tracks = relationship("TimelineTrack", back_populates="timeline", cascade="all, delete-orphan")
    executions = relationship("TimelineExecution", back_populates="timeline")


class TimelineTrack(Base):
    """Track within a timeline (video track or overlay track)"""
    __tablename__ = "timeline_tracks"
    
    id = Column(Integer, primary_key=True, index=True)
    timeline_id = Column(Integer, ForeignKey("timelines.id"), nullable=False)
    track_type = Column(String, nullable=False)  # 'video' or 'overlay'
    layer = Column(Integer, default=0)  # Z-order for overlays
    is_enabled = Column(Boolean, default=True)
    
    # Relationships
    timeline = relationship("Timeline", back_populates="tracks")
    cues = relationship("TimelineCue", back_populates="track", cascade="all, delete-orphan")


class TimelineCue(Base):
    """Individual cue/action in a timeline track"""
    __tablename__ = "timeline_cues"
    
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, ForeignKey("timeline_tracks.id"), nullable=False)
    cue_order = Column(Integer, nullable=False)  # Execution order
    start_time = Column(Float, nullable=False)  # Start time in seconds
    duration = Column(Float, nullable=False)  # Duration in seconds
    action_type = Column(String, nullable=False)  # 'show_camera', 'show_media', 'show_overlay'
    action_params = Column(JSON, nullable=False)  # Camera ID, preset, transition, etc.
    transition_type = Column(String, default="cut")  # 'cut', 'fade', 'wipe'
    transition_duration = Column(Float, default=0.0)  # Transition duration in seconds
    
    # Relationships
    track = relationship("TimelineTrack", back_populates="cues")


class TimelineExecution(Base):
    """Execution history of a timeline"""
    __tablename__ = "timeline_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    timeline_id = Column(Integer, ForeignKey("timelines.id"), nullable=False)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    status = Column(String, default="running")  # 'running', 'completed', 'stopped', 'error'
    error_message = Column(String)
    metrics = Column(JSON)  # Execution stats
    
    # Relationships
    timeline = relationship("Timeline", back_populates="executions")

