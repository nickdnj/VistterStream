"""
Database models and configuration
"""

from contextlib import contextmanager
from sqlalchemy import create_engine, event, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import logging
import os

logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vistterstream.db")

# Create engine with larger pool for background services
_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_size=20,
    max_overflow=30,
    pool_timeout=60,
    pool_recycle=300,
    pool_pre_ping=True,
)

# Log pool exhaustion warnings
@event.listens_for(engine, "checkout")
def _on_checkout(dbapi_conn, connection_rec, connection_proxy):
    pool = engine.pool
    checked_out = getattr(pool, "checkedout", lambda: -1)()
    if checked_out > 10:
        logger.warning(
            "DB pool high usage: %d checked out (overflow: %s)",
            checked_out, getattr(pool, "overflow", lambda: "?")(),
        )

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class
Base = declarative_base()

# Database models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    # General settings
    appliance_name = Column(String, default="VistterStream Appliance")
    timezone = Column(String, default="America/New_York")
    
    # Location information
    state_name = Column(String)  # State/Province name
    city = Column(String)  # City name
    latitude = Column(Float)  # Geographic latitude
    longitude = Column(Float)  # Geographic longitude
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ReelForgeSettings(Base):
    """ReelForge-specific settings for AI content generation"""
    __tablename__ = "reelforge_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # OpenAI Configuration
    openai_api_key_enc = Column(String)  # Encrypted API key (base64 encoded)
    openai_model = Column(String, default="gpt-5-mini")  # Model to use
    
    # System Prompt (editable)
    system_prompt = Column(String, default="""You are a social media content creator specializing in short-form video content like TikTok, Instagram Reels, and YouTube Shorts. You create short, punchy headlines that grab attention.

Guidelines:
- Keep headlines SHORT (under 10 words)
- Make them engaging and scroll-stopping
- Match the tone and voice specified
- Use current date/time context when relevant
- Always respond with valid JSON only""")
    
    # AI Generation Settings
    temperature = Column(Float, default=0.8)  # 0.0-1.0, higher = more creative
    max_tokens = Column(Integer, default=500)
    
    # Default Template
    default_template_id = Column(Integer, ForeignKey("reel_templates.id"), nullable=True)
    
    # Weather Data Integration (TempestWeather API)
    tempest_api_url = Column(String, default="http://host.docker.internal:8085")  # TempestWeather service URL
    weather_enabled = Column(Boolean, default=True)  # Enable weather data in AI prompts
    
    # YouTube OAuth Configuration (for auto-publishing to YouTube Shorts)
    youtube_client_id = Column(String)
    youtube_client_secret_enc = Column(String)  # Encrypted
    youtube_refresh_token_enc = Column(String)  # Encrypted OAuth refresh token
    youtube_connected = Column(Boolean, default=False)  # Whether YouTube is connected
    youtube_channel_name = Column(String)  # Connected channel name for display
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "stationary" or "ptz"
    protocol = Column(String, nullable=False)  # "rtsp" or "rtmp"
    address = Column(String, nullable=False)
    username = Column(String)
    password_enc = Column(String)
    port = Column(Integer, default=554)
    onvif_port = Column(Integer, default=80)  # ONVIF port for PTZ control (8899 for Sunba, 80 default)
    stream_path = Column(String, default="/stream1")
    snapshot_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime)
    
    # Relationships
    presets = relationship("Preset", back_populates="camera", cascade="all, delete-orphan")
    streams = relationship("Stream", back_populates="camera", cascade="all, delete-orphan")

class Preset(Base):
    __tablename__ = "presets"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    name = Column(String, nullable=False)
    pan = Column(Float, default=0.0)
    tilt = Column(Float, default=0.0)
    zoom = Column(Float, default=1.0)
    camera_preset_token = Column(String)  # Token returned by camera for ONVIF control
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    camera = relationship("Camera", back_populates="presets")

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "static_image", "api_image", "video", "graphic", "google_drawing"
    
    # For static images/videos
    file_path = Column(String)  # Local file path or URL
    
    # For API-based images (dynamic content)
    api_url = Column(String)  # API endpoint that returns image
    api_refresh_interval = Column(Integer, default=30)  # Seconds between refreshes
    
    # Display properties
    width = Column(Integer)  # Width in pixels (null = auto)
    height = Column(Integer)  # Height in pixels (null = auto)
    position_x = Column(Float, default=0.0)  # X position (0-1, 0=left, 1=right)
    position_y = Column(Float, default=0.0)  # Y position (0-1, 0=top, 1=bottom)
    opacity = Column(Float, default=1.0)  # 0-1
    
    # Location information (synced with settings)
    state_name = Column(String)  # State/Province name
    city = Column(String)  # City name
    latitude = Column(Float)  # Geographic latitude
    longitude = Column(Float)  # Geographic longitude
    
    # Metadata
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime)

class Stream(Base):
    __tablename__ = "streams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # "YouTube Main Stream", etc.
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    preset_id = Column(Integer, ForeignKey("presets.id"), nullable=True)  # Optional PTZ preset
    destination_id = Column(Integer, ForeignKey("streaming_destinations.id"), nullable=False)
    
    # Encoding profile
    resolution = Column(String, default="1920x1080")  # "1920x1080", "1280x720", etc.
    bitrate = Column(String, default="4500k")  # Target bitrate
    framerate = Column(Integer, default=30)  # FPS
    
    # Stream status
    status = Column(String, default="stopped")  # "stopped", "starting", "running", "error"
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)
    last_error = Column(String)
    
    # Relationships
    camera = relationship("Camera", back_populates="streams")
    preset = relationship("Preset", foreign_keys=[preset_id])
    destination = relationship("StreamingDestination", foreign_keys=[destination_id])

# Import timeline models to register them with SQLAlchemy
from .timeline import Timeline, TimelineTrack, TimelineCue, TimelineExecution  # noqa: F401
from .schedule import Schedule, ScheduleTimeline  # noqa: F401
from .destination import StreamingDestination  # noqa: F401
from .reelforge import ReelTemplate, ReelPost, ReelPublishTarget, ReelExport, ReelCaptureQueue  # noqa: F401

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Context manager for background services (use: with get_session() as db: ...)
@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get database session (FastAPI routes)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
