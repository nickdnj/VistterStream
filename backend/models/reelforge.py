"""
ReelForge models for automated social media content generation
Captures camera clips, converts to portrait format, generates AI content, publishes to platforms
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class ReelTemplate(Base):
    """Reusable template for generating ReelForge posts"""
    __tablename__ = "reel_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Video Source Configuration
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    preset_id = Column(Integer, ForeignKey("presets.id"), nullable=True)  # Nullable for stationary cameras
    clip_duration = Column(Integer, default=30)  # Duration in seconds
    
    # Portrait Crop/Pan Configuration
    pan_direction = Column(String, default="left_to_right")  # 'left_to_right', 'right_to_left', 'center'
    pan_speed = Column(Float, default=1.0)  # Speed multiplier
    
    # AI Content Configuration
    ai_config = Column(JSON, default=dict)
    # Structure:
    # {
    #     "tone": "casual",
    #     "voice": "friendly surf instructor",
    #     "instructions": "Create engaging content for a surf shop...",
    #     "prompt_1": "Morning greeting with current conditions",
    #     "prompt_2": "Weather and wave update",
    #     "prompt_3": "Highlight of the day",
    #     "prompt_4": "Call to action for the shop",
    #     "prompt_5": "Sign off with social links"
    # }
    
    # Overlay Style Configuration
    overlay_style = Column(String, default="bottom_text")  # 'bottom_text', 'top_bar', 'center', 'custom'
    font_family = Column(String, default="Arial")
    font_size = Column(Integer, default=48)
    text_color = Column(String, default="#FFFFFF")
    text_shadow = Column(Boolean, default=True)
    text_background = Column(String, default="rgba(0,0,0,0.5)")  # Semi-transparent background
    text_position_y = Column(Float, default=0.8)  # 0-1, vertical position (0.8 = 80% down)
    
    # Publishing Configuration
    publish_mode = Column(String, default="manual")  # 'manual', 'auto', 'scheduled'
    schedule_times = Column(JSON, default=list)  # Array of times: ["08:00", "14:00", "18:00"]
    default_title_template = Column(String, default="{headline_1}")
    default_description_template = Column(Text)
    default_hashtags = Column(String, default="#shorts")
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    camera = relationship("Camera", foreign_keys=[camera_id])
    preset = relationship("Preset", foreign_keys=[preset_id])
    posts = relationship("ReelPost", back_populates="template", cascade="all, delete-orphan")


class ReelPost(Base):
    """Individual generated ReelForge post"""
    __tablename__ = "reel_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("reel_templates.id"), nullable=True)
    
    # Generation Status
    status = Column(String, default="queued")  # 'queued', 'capturing', 'processing', 'ready', 'failed'
    error_message = Column(Text)
    
    # Download tracking
    download_count = Column(Integer, default=0)
    
    # Source Configuration (captured at queue time)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    preset_id = Column(Integer, ForeignKey("presets.id"), nullable=True)
    
    # File Paths
    source_clip_path = Column(String)  # Original 30-sec landscape clip
    portrait_clip_path = Column(String)  # After portrait conversion with pan
    output_path = Column(String)  # Final rendered video with overlays
    thumbnail_path = Column(String)  # Generated thumbnail
    
    # Generated AI Content
    generated_headlines = Column(JSON, default=list)
    # Structure:
    # [
    #     {"text": "Beautiful morning!", "start_time": 0, "duration": 6},
    #     {"text": "Waves are 3-4ft", "start_time": 6, "duration": 6},
    #     ...
    # ]
    
    # Scheduling Configuration
    scheduled_capture_at = Column(DateTime)  # One-time: capture at this specific time
    recurring_schedule = Column(JSON)  # {"enabled": true, "times": ["08:00", "14:00"], "days": [0,1,2,3,4,5,6]}
    
    # Auto-publish Configuration
    auto_publish = Column(Boolean, default=False)  # Auto-publish when ready
    publish_platform = Column(String)  # 'youtube_shorts', 'tiktok', 'instagram_reels'
    publish_title = Column(String)  # Custom title for publishing
    publish_description = Column(Text)  # Custom description
    publish_tags = Column(String)  # Comma-separated tags
    published_at = Column(DateTime)  # When it was published
    published_url = Column(String)  # URL of the published video
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    capture_started_at = Column(DateTime)
    capture_completed_at = Column(DateTime)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    
    # Relationships
    template = relationship("ReelTemplate", back_populates="posts")
    camera = relationship("Camera", foreign_keys=[camera_id])
    preset = relationship("Preset", foreign_keys=[preset_id])
    exports = relationship("ReelExport", back_populates="post", cascade="all, delete-orphan")


class ReelPublishTarget(Base):
    """Platform preferences for ReelForge posts (hashtags, description templates, etc.)
    
    Note: This is for storing platform-specific defaults only.
    Actual posting is done manually by the user - no OAuth/API integration.
    Future: VistterStream Cloud will handle automatic posting.
    """
    __tablename__ = "reel_publish_targets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)  # 'youtube_shorts', 'instagram_reels', 'tiktok', 'facebook_reels'
    
    # Default Post Settings (used when preparing content for manual posting)
    default_title_template = Column(String, default="{headline_1}")
    default_description_template = Column(Text)
    default_hashtags = Column(String)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    exports = relationship("ReelExport", back_populates="target")


class ReelExport(Base):
    """Track export/download of a post for manual posting to a platform
    
    Note: This tracks when a user downloads a video for a specific platform.
    The actual posting is done manually by the user outside of VistterStream.
    """
    __tablename__ = "reel_exports"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("reel_posts.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("reel_publish_targets.id"), nullable=True)  # Optional platform preference
    
    # Export Status
    status = Column(String, default="exported")  # 'exported', 'posted' (user marks as posted)
    
    # Platform URL (user can optionally add after manual posting)
    platform_url = Column(String)  # URL to view the post (user enters after posting)
    
    # Prepared metadata for the platform
    title = Column(String)
    description = Column(Text)
    hashtags = Column(String)
    
    # Timestamps
    exported_at = Column(DateTime, default=datetime.utcnow)
    posted_at = Column(DateTime)  # User marks when they posted
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post = relationship("ReelPost", back_populates="exports")
    target = relationship("ReelPublishTarget", back_populates="exports")


class ReelCaptureQueue(Base):
    """Queue for pending capture requests - processed by timeline executor or scheduler"""
    __tablename__ = "reel_capture_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("reel_posts.id"), nullable=False)
    
    # Target camera/preset to capture
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    preset_id = Column(Integer, ForeignKey("presets.id"), nullable=True)
    
    # Trigger Mode
    trigger_mode = Column(String, default="next_view")  # 'next_view' or 'scheduled'
    # 'next_view': Capture when timeline switches to this camera/preset
    # 'scheduled': Capture at the scheduled_at time
    
    scheduled_at = Column(DateTime)  # When to capture (for scheduled mode)
    
    # Queue Status
    status = Column(String, default="waiting")  # 'waiting', 'capturing', 'completed', 'failed'
    priority = Column(Integer, default=0)  # Higher = more urgent
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Optional expiration
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Error tracking
    error_message = Column(String, nullable=True)  # Error details if failed
    attempt_count = Column(Integer, default=0)     # Number of capture attempts
    last_attempt_at = Column(DateTime)             # When last attempt occurred
    
    # Relationships
    post = relationship("ReelPost", foreign_keys=[post_id])
    camera = relationship("Camera", foreign_keys=[camera_id])
    preset = relationship("Preset", foreign_keys=[preset_id])
