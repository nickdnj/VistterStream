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
    name: str = Field(..., min_length=1, max_length=100)
    destination_id: int
    resolution: str = Field(default="1920x1080")
    bitrate: str = Field(default="4500k")
    framerate: int = Field(default=30, ge=15, le=60)

class StreamCreate(StreamBase):
    camera_id: int

class StreamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    destination_id: Optional[int] = None
    resolution: Optional[str] = None
    bitrate: Optional[str] = None
    framerate: Optional[int] = Field(None, ge=15, le=60)
    is_active: Optional[bool] = None

class Stream(StreamBase):
    id: int
    camera_id: int
    status: StreamStatus
    is_active: bool
    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_error: Optional[str] = None
    
    class Config:
        from_attributes = True
        use_enum_values = True  # Serialize enums as their values

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

# FFmpeg and Streaming schemas
class StreamMetricsSchema(BaseModel):
    """Real-time stream metrics from FFmpeg"""
    bitrate_current: float = Field(0.0, description="Current bitrate in Mbps")
    bitrate_target: float = Field(4.5, description="Target bitrate in Mbps")
    framerate_actual: float = Field(0.0, description="Actual framerate")
    framerate_target: float = Field(30.0, description="Target framerate")
    dropped_frames: int = Field(0, description="Number of dropped frames")
    encoding_time_ms: float = Field(0.0, description="Encoding time per frame in ms")
    buffer_fullness: float = Field(100.0, description="Buffer fullness percentage")
    uptime_seconds: int = Field(0, description="Stream uptime in seconds")
    total_bytes_sent: int = Field(0, description="Total bytes sent")
    last_update: datetime = Field(default_factory=datetime.utcnow, description="Last metrics update time")
    
    class Config:
        from_attributes = True

class EncodingProfileSchema(BaseModel):
    """Encoding profile configuration"""
    codec: str = Field(..., description="Video codec (h264_v4l2m2m, h264_videotoolbox, libx264)")
    resolution: tuple[int, int] = Field((1920, 1080), description="Video resolution (width, height)")
    framerate: int = Field(30, ge=1, le=60, description="Target framerate")
    bitrate: str = Field("4500k", description="Target bitrate (e.g., '4500k')")
    keyframe_interval: int = Field(2, ge=1, description="Keyframe interval in seconds")
    buffer_size: str = Field("9000k", description="Encoder buffer size")
    preset: str = Field("fast", description="Encoding preset (fast, medium, slow)")
    profile: str = Field("main", description="H.264 profile (baseline, main, high)")
    level: str = Field("4.1", description="H.264 level")

class StreamProcessStatus(BaseModel):
    """Stream process status information"""
    stream_id: int
    status: str = Field(..., description="Stream status (stopped, starting, running, degraded, error)")
    retry_count: int = Field(0, description="Number of restart attempts")
    started_at: Optional[datetime] = None
    last_error: Optional[str] = None
    metrics: StreamMetricsSchema
    
    class Config:
        from_attributes = True

class HardwareCapabilitiesSchema(BaseModel):
    """Hardware encoder capabilities"""
    encoder: str = Field(..., description="Detected encoder (h264_v4l2m2m, h264_videotoolbox, libx264)")
    decoder: Optional[str] = Field(None, description="Hardware decoder if available")
    platform: str = Field(..., description="Platform (pi5, mac, software)")
    max_concurrent_streams: int = Field(..., description="Maximum concurrent streams supported")
    supports_hardware: bool = Field(..., description="Whether hardware acceleration is available")
