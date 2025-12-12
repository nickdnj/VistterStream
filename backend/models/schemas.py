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
    onvif_port: int = Field(default=80, ge=1, le=65535)  # ONVIF port for PTZ (8899 for Sunba, 80 default)
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
    onvif_port: Optional[int] = Field(None, ge=1, le=65535)
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
    zoom: float = Field(default=1.0, ge=0.0, le=10.0)

class PresetCreate(PresetBase):
    camera_id: int

class PresetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    pan: Optional[float] = Field(None, ge=-180.0, le=180.0)
    tilt: Optional[float] = Field(None, ge=-90.0, le=90.0)
    zoom: Optional[float] = Field(None, ge=0.0, le=10.0)

class Preset(PresetBase):
    id: int
    camera_id: int
    camera_preset_token: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Asset schemas
class AssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(static_image|api_image|video|graphic|google_drawing)$")
    file_path: Optional[str] = None
    api_url: Optional[str] = None
    api_refresh_interval: int = Field(default=30, ge=1, le=3600)
    width: Optional[int] = Field(None, ge=1, le=3840)
    height: Optional[int] = Field(None, ge=1, le=2160)
    position_x: float = Field(default=0.0, ge=0.0, le=1.0)
    position_y: float = Field(default=0.0, ge=0.0, le=1.0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    description: Optional[str] = None

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = Field(None, pattern="^(static_image|api_image|video|graphic|google_drawing)$")
    file_path: Optional[str] = None
    api_url: Optional[str] = None
    api_refresh_interval: Optional[int] = Field(None, ge=1, le=3600)
    width: Optional[int] = Field(None, ge=1, le=3840)
    height: Optional[int] = Field(None, ge=1, le=2160)
    position_x: Optional[float] = Field(None, ge=0.0, le=1.0)
    position_y: Optional[float] = Field(None, ge=0.0, le=1.0)
    opacity: Optional[float] = Field(None, ge=0.0, le=1.0)
    description: Optional[str] = None

class Asset(AssetBase):
    id: int
    is_active: bool
    created_at: datetime
    last_updated: Optional[datetime] = None
    
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
    preset_id: Optional[int] = None

class StreamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    camera_id: Optional[int] = None
    preset_id: Optional[int] = None
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

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


# Status schemas
class SystemStatus(BaseModel):
    status: str
    uptime: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_usage: float
    active_cameras: int
    active_streams: int
    timeline_streaming: bool
    timeline_name: Optional[str] = None
    timeline_destinations: Optional[list[str]] = None

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


# ============================================================================
# ReelForge Schemas - Automated Social Media Content Generation
# ============================================================================

class ReelPanDirection(str, Enum):
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    CENTER = "center"


class ReelPublishMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"
    SCHEDULED = "scheduled"


class ReelPostStatus(str, Enum):
    QUEUED = "queued"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ReelExportStatus(str, Enum):
    EXPORTED = "exported"  # User downloaded the video
    POSTED = "posted"  # User marked as manually posted


class ReelPlatform(str, Enum):
    YOUTUBE_SHORTS = "youtube_shorts"
    INSTAGRAM_REELS = "instagram_reels"
    TIKTOK = "tiktok"
    FACEBOOK_REELS = "facebook_reels"


# AI Configuration Schema
class ReelAIConfig(BaseModel):
    """AI content generation configuration"""
    tone: str = Field(default="casual", description="Content tone (casual, professional, excited, etc.)")
    voice: str = Field(default="friendly local guide", description="Voice/persona for content")
    instructions: str = Field(default="", description="General instructions for AI content generation")
    prompt_1: str = Field(default="Morning greeting with current conditions", description="First headline prompt")
    prompt_2: str = Field(default="Weather and conditions update", description="Second headline prompt")
    prompt_3: str = Field(default="Highlight of the day", description="Third headline prompt")
    prompt_4: str = Field(default="Call to action", description="Fourth headline prompt")
    prompt_5: str = Field(default="Sign off with social links", description="Fifth headline prompt")


# Generated Headline Schema
class ReelHeadline(BaseModel):
    """Individual generated headline with timing"""
    text: str
    start_time: float = Field(description="Start time in seconds")
    duration: float = Field(default=6.0, description="Duration in seconds")


# ReelTemplate Schemas
class ReelTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    camera_id: Optional[int] = None
    preset_id: Optional[int] = None
    clip_duration: int = Field(default=30, ge=10, le=60, description="Clip duration in seconds")
    pan_direction: ReelPanDirection = ReelPanDirection.LEFT_TO_RIGHT
    pan_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    ai_config: ReelAIConfig = Field(default_factory=ReelAIConfig)
    overlay_style: str = Field(default="bottom_text")
    font_family: str = Field(default="Arial")
    font_size: int = Field(default=48, ge=12, le=120)
    text_color: str = Field(default="#FFFFFF")
    text_shadow: bool = True
    text_background: str = Field(default="rgba(0,0,0,0.5)")
    text_position_y: float = Field(default=0.8, ge=0.0, le=1.0)
    publish_mode: ReelPublishMode = ReelPublishMode.MANUAL
    schedule_times: List[str] = Field(default_factory=list, description="Schedule times in HH:MM format")
    default_title_template: str = Field(default="{headline_1}")
    default_description_template: Optional[str] = None
    default_hashtags: str = Field(default="#shorts")


class ReelTemplateCreate(ReelTemplateBase):
    pass


class ReelTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    camera_id: Optional[int] = None
    preset_id: Optional[int] = None
    clip_duration: Optional[int] = Field(None, ge=10, le=60)
    pan_direction: Optional[ReelPanDirection] = None
    pan_speed: Optional[float] = Field(None, ge=0.5, le=2.0)
    ai_config: Optional[ReelAIConfig] = None
    overlay_style: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[int] = Field(None, ge=12, le=120)
    text_color: Optional[str] = None
    text_shadow: Optional[bool] = None
    text_background: Optional[str] = None
    text_position_y: Optional[float] = Field(None, ge=0.0, le=1.0)
    publish_mode: Optional[ReelPublishMode] = None
    schedule_times: Optional[List[str]] = None
    default_title_template: Optional[str] = None
    default_description_template: Optional[str] = None
    default_hashtags: Optional[str] = None
    is_active: Optional[bool] = None


class ReelTemplate(ReelTemplateBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        use_enum_values = True


# ReelPost Schemas
class ReelPostBase(BaseModel):
    template_id: Optional[int] = None
    camera_id: int
    preset_id: Optional[int] = None


class ReelPostCreate(ReelPostBase):
    """Create a new post by queueing a capture"""
    pass


class ReelPostQueue(BaseModel):
    """Queue a capture request"""
    camera_id: int
    preset_id: Optional[int] = None
    template_id: Optional[int] = None
    trigger_mode: str = Field(default="next_view", description="'next_view' or 'scheduled'")
    scheduled_at: Optional[datetime] = Field(None, description="When to capture (for scheduled mode)")


class ReelPost(BaseModel):
    id: int
    template_id: Optional[int] = None
    status: ReelPostStatus
    error_message: Optional[str] = None
    camera_id: int
    preset_id: Optional[int] = None
    source_clip_path: Optional[str] = None
    portrait_clip_path: Optional[str] = None
    output_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    generated_headlines: List[ReelHeadline] = Field(default_factory=list)
    download_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    capture_started_at: Optional[datetime] = None
    capture_completed_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        use_enum_values = True


class ReelPostWithDetails(ReelPost):
    """Post with related camera/preset/template names"""
    camera_name: Optional[str] = None
    preset_name: Optional[str] = None
    template_name: Optional[str] = None


# ReelPublishTarget Schemas (platform preferences for manual posting)
class ReelPublishTargetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    platform: ReelPlatform
    default_title_template: str = Field(default="{headline_1}")
    default_description_template: Optional[str] = None
    default_hashtags: Optional[str] = None


class ReelPublishTargetCreate(ReelPublishTargetBase):
    pass


class ReelPublishTargetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    platform: Optional[ReelPlatform] = None
    default_title_template: Optional[str] = None
    default_description_template: Optional[str] = None
    default_hashtags: Optional[str] = None
    is_active: Optional[bool] = None


class ReelPublishTarget(ReelPublishTargetBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        use_enum_values = True


# ReelExport Schemas (tracking manual downloads/posts)
class ReelExportBase(BaseModel):
    post_id: int
    target_id: Optional[int] = None  # Optional platform preference
    title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None


class ReelExportCreate(ReelExportBase):
    pass


class ReelExportUpdate(BaseModel):
    """Update export status after manual posting"""
    status: Optional[ReelExportStatus] = None
    platform_url: Optional[str] = None  # User can add URL after manual posting


class ReelExport(ReelExportBase):
    id: int
    status: ReelExportStatus
    platform_url: Optional[str] = None
    exported_at: datetime
    posted_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        use_enum_values = True


# Camera selection for ReelForge UI
class CameraWithPresets(BaseModel):
    """Camera with its presets for ReelForge selection UI"""
    id: int
    name: str
    type: CameraType
    presets: List[Preset] = Field(default_factory=list)
    
    class Config:
        from_attributes = True
        use_enum_values = True


# Capture Trigger Mode
class ReelTriggerMode(str, Enum):
    NEXT_VIEW = "next_view"  # Capture when timeline hits this camera/preset
    SCHEDULED = "scheduled"  # Capture at scheduled time


# Capture Queue Status
class ReelCaptureQueueItem(BaseModel):
    """Item in the capture queue"""
    id: int
    post_id: int
    camera_id: int
    preset_id: Optional[int] = None
    trigger_mode: ReelTriggerMode = ReelTriggerMode.NEXT_VIEW
    scheduled_at: Optional[datetime] = None
    status: str
    priority: int = 0
    created_at: datetime
    expires_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    camera_name: Optional[str] = None
    preset_name: Optional[str] = None
    # Error tracking
    error_message: Optional[str] = None
    attempt_count: int = 0
    last_attempt_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        use_enum_values = True


# ============================================================================
# ReelForge Settings Schemas
# ============================================================================

class ReelForgeSettingsBase(BaseModel):
    """Base schema for ReelForge settings"""
    openai_model: str = Field(default="gpt-5-mini", description="OpenAI model to use for content generation")
    system_prompt: str = Field(
        default="""You are a social media content creator specializing in short-form video content like TikTok, Instagram Reels, and YouTube Shorts. You create short, punchy headlines that grab attention.

Guidelines:
- Keep headlines SHORT (under 10 words)
- Make them engaging and scroll-stopping
- Match the tone and voice specified
- Use current date/time context when relevant
- Always respond with valid JSON only""",
        description="System prompt for AI headline generation"
    )
    temperature: float = Field(default=0.8, ge=0.0, le=1.0, description="AI creativity (0=focused, 1=creative)")
    max_tokens: int = Field(default=500, ge=100, le=2000, description="Maximum tokens in AI response")
    default_template_id: Optional[int] = None
    # Weather Integration
    tempest_api_url: str = Field(default="http://host.docker.internal:8085", description="TempestWeather API URL")
    weather_enabled: bool = Field(default=True, description="Enable weather data in AI prompts")


class ReelForgeSettingsCreate(ReelForgeSettingsBase):
    """Schema for creating ReelForge settings"""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key (will be encrypted)")


class ReelForgeSettingsUpdate(BaseModel):
    """Schema for updating ReelForge settings"""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key (will be encrypted)")
    openai_model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=2000)
    default_template_id: Optional[int] = None
    tempest_api_url: Optional[str] = None
    weather_enabled: Optional[bool] = None


class ReelForgeSettings(ReelForgeSettingsBase):
    """Schema for ReelForge settings response"""
    id: int
    has_api_key: bool = Field(description="Whether an API key is configured (key itself is not returned)")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ReelForgeSettingsTestResult(BaseModel):
    """Result of testing OpenAI connection"""
    success: bool
    message: str
    model_used: Optional[str] = None
