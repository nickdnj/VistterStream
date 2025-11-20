"""
Database models and configuration
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vistterstream.db")

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

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
    created_at = Column(DateTime, default=datetime.utcnow)
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

    # Cloud Companion App (VistterStudio)
    cloud_pairing_token = Column(String, nullable=True)  # JWT token for cloud auth
    cloud_device_id = Column(String, nullable=True)  # UUID of this device in cloud
    cloud_api_url = Column(String, default="wss://api.vistterstudio.com/ws/device")  # WebSocket URL
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    camera = relationship("Camera", back_populates="presets")

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "static_image", "api_image", "video", "graphic"
    
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
    created_at = Column(DateTime, default=datetime.utcnow)
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
    created_at = Column(DateTime, default=datetime.utcnow)
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

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
