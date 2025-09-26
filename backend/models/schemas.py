"""
Pydantic schemas for API request/response models
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class CameraType(str, Enum):
    STATIONARY = "stationary"
    PTZ = "ptz"

class Protocol(str, Enum):
    RTSP = "rtsp"
    RTMP = "rtmp"

class StreamStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"

class StreamDestination(str, Enum):
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    TWITCH = "twitch"

# Camera schemas
class CameraBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: CameraType
    protocol: Protocol
    address: str = Field(..., min_length=1)
    username: Optional[str] = None
    password: Optional[str] = None
    port: int = Field(default=554, ge=1, le=65535)
    stream_path: str = Field(default="/stream1")
    snapshot_url: Optional[str] = None

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[CameraType] = None
    protocol: Optional[Protocol] = None
    address: Optional[str] = Field(None, min_length=1)
    username: Optional[str] = None
    password: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    stream_path: Optional[str] = None
    snapshot_url: Optional[str] = None

class Camera(CameraBase):
    id: int
    is_active: bool
    created_at: datetime
    last_seen: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CameraWithStatus(Camera):
    status: str = "unknown"  # "online", "offline", "error"
    last_error: Optional[str] = None

# Preset schemas
class PresetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    pan: float = Field(default=0.0, ge=-180.0, le=180.0)
    tilt: float = Field(default=0.0, ge=-90.0, le=90.0)
    zoom: float = Field(default=1.0, ge=0.1, le=10.0)

class PresetCreate(PresetBase):
    camera_id: int

class PresetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    pan: Optional[float] = Field(None, ge=-180.0, le=180.0)
    tilt: Optional[float] = Field(None, ge=-90.0, le=90.0)
    zoom: Optional[float] = Field(None, ge=0.1, le=10.0)

class Preset(PresetBase):
    id: int
    camera_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Stream schemas
class StreamBase(BaseModel):
    destination: StreamDestination
    stream_key: str = Field(..., min_length=1)
    rtmp_url: str = Field(..., min_length=1)

class StreamCreate(StreamBase):
    camera_id: int

class StreamUpdate(BaseModel):
    destination: Optional[StreamDestination] = None
    stream_key: Optional[str] = Field(None, min_length=1)
    rtmp_url: Optional[str] = Field(None, min_length=1)

class Stream(StreamBase):
    id: int
    camera_id: int
    status: StreamStatus
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

# Authentication schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Status schemas
class SystemStatus(BaseModel):
    status: str
    uptime: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_cameras: int
    active_streams: int

class CameraStatus(BaseModel):
    camera_id: int
    name: str
    status: str  # "online", "offline", "error"
    last_seen: Optional[datetime]
    error_message: Optional[str] = None

# API Response schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class CameraTestResponse(BaseModel):
    success: bool
    message: str
    rtsp_accessible: bool = False
    snapshot_accessible: bool = False
    error_details: Optional[str] = None
