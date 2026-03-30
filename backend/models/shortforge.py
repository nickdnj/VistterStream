"""
ShortForge database models — automated YouTube Shorts pipeline
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from models.database import Base


class Moment(Base):
    """Detected moments from the camera feed"""
    __tablename__ = "moments"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    trigger_type = Column(String, nullable=False)  # 'motion', 'brightness', 'activity'
    score = Column(Float, nullable=False)
    frame_path = Column(String)  # snapshot at trigger time
    status = Column(String, default="detected")  # detected, captured, rendered, published, skipped, failed
    error_message = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    camera = relationship("Camera")
    clip = relationship("Clip", back_populates="moment", uselist=False)


class Clip(Base):
    """Captured video clips from moments"""
    __tablename__ = "clips"

    id = Column(Integer, primary_key=True, index=True)
    moment_id = Column(Integer, ForeignKey("moments.id"), nullable=False)
    file_path = Column(String, nullable=False)  # raw horizontal clip
    duration_seconds = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    rendered_path = Column(String)  # vertical 1080x1920 output
    headline = Column(String)  # AI-generated headline
    safe_to_publish = Column(Boolean, default=True)  # AI safety gate
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    moment = relationship("Moment", back_populates="clip")
    published_short = relationship("PublishedShort", back_populates="clip", uselist=False)


class PublishedShort(Base):
    """Published YouTube Shorts"""
    __tablename__ = "published_shorts"

    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("clips.id"), nullable=False)
    youtube_video_id = Column(String)
    title = Column(String)
    description = Column(Text)
    tags = Column(String)  # comma-separated
    views = Column(Integer, default=0)
    published_at = Column(DateTime)
    status = Column(String, default="published")  # published, removed, failed
    error_message = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    clip = relationship("Clip", back_populates="published_short")


class ShortForgeConfig(Base):
    """ShortForge pipeline configuration (singleton row)"""
    __tablename__ = "shortforge_config"

    id = Column(Integer, primary_key=True, index=True)

    # Pipeline control
    enabled = Column(Boolean, default=False)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    timeline_id = Column(Integer, nullable=True)  # Timeline to monitor (overrides camera_id)

    # Detection thresholds
    motion_threshold = Column(Float, default=0.05)
    brightness_threshold = Column(Float, default=0.15)
    activity_threshold = Column(Float, default=0.10)
    cooldown_seconds = Column(Integer, default=120)  # min seconds between moments
    detector_interval_seconds = Column(Integer, default=5)  # how often to analyze frames

    # Posting rules
    max_shorts_per_day = Column(Integer, default=6)
    quiet_hours_start = Column(String, default="22:00")  # HH:MM
    quiet_hours_end = Column(String, default="06:00")  # HH:MM
    min_posting_interval_minutes = Column(Integer, default=60)

    # Content defaults
    default_tags = Column(String, default="")  # comma-separated
    description_template = Column(Text, default="{{headline}} | {{location}} | {{conditions}}")
    safety_gate_enabled = Column(Boolean, default=True)

    # Capture windows (JSON list of window configs)
    # Each: {"name": str, "label": str, "reference": "sunrise"|"sunset"|"fixed",
    #         "offset_minutes": int, "duration_minutes": int, "enabled": bool}
    capture_windows_json = Column(JSON, nullable=True)

    # Storage retention (days)
    raw_clip_retention_days = Column(Integer, default=7)
    rendered_clip_retention_days = Column(Integer, default=30)
    snapshot_retention_days = Column(Integer, default=3)

    # AI config
    openai_api_key_enc = Column(String)  # encrypted
    ai_model = Column(String, default="gpt-4o-mini")

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    camera = relationship("Camera")
