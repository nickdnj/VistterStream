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
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    camera = relationship("Camera", back_populates="presets")

class Stream(Base):
    __tablename__ = "streams"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    destination = Column(String, nullable=False)  # "youtube", "facebook", "twitch"
    stream_key = Column(String, nullable=False)
    rtmp_url = Column(String, nullable=False)
    status = Column(String, default="stopped")  # "stopped", "starting", "running", "error"
    started_at = Column(DateTime)
    stopped_at = Column(DateTime)
    error_message = Column(String)
    
    # Relationships
    camera = relationship("Camera", back_populates="streams")

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
