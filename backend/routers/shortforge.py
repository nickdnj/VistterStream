"""
ShortForge API Router — dashboard, settings, and pipeline management endpoints.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.database import get_db, Camera
from models.shortforge import Moment, Clip, PublishedShort, ShortForgeConfig
from routers.auth import get_current_user
from utils.crypto import encrypt, decrypt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/shortforge", tags=["shortforge"])


# --- Pydantic Schemas ---

class PipelineStatus(BaseModel):
    enabled: bool = False
    camera_id: Optional[int] = None
    camera_name: Optional[str] = None
    state: str = "disabled"  # disabled, running, paused, error
    shorts_today: int = 0
    max_shorts_per_day: int = 6
    moments_today: int = 0
    next_post: Optional[str] = None
    disk_usage_mb: float = 0

class ShortRead(BaseModel):
    id: int
    clip_id: int
    youtube_video_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    views: int = 0
    published_at: Optional[datetime] = None
    status: str = "published"
    error_message: Optional[str] = None
    # From clip
    headline: Optional[str] = None
    rendered_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    safe_to_publish: Optional[bool] = None
    # From moment
    moment_id: Optional[int] = None
    trigger_type: Optional[str] = None
    score: Optional[float] = None
    frame_path: Optional[str] = None
    moment_timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True

class MomentRead(BaseModel):
    id: int
    camera_id: int
    timestamp: datetime
    trigger_type: str
    score: float
    frame_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ConfigRead(BaseModel):
    id: int
    enabled: bool
    camera_id: Optional[int] = None
    motion_threshold: float
    brightness_threshold: float
    activity_threshold: float
    cooldown_seconds: int
    detector_interval_seconds: int
    max_shorts_per_day: int
    quiet_hours_start: str
    quiet_hours_end: str
    min_posting_interval_minutes: int
    default_tags: str
    description_template: str
    safety_gate_enabled: bool
    raw_clip_retention_days: int
    rendered_clip_retention_days: int
    snapshot_retention_days: int
    ai_model: str
    has_openai_key: bool = False

    class Config:
        from_attributes = True

class ConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    camera_id: Optional[int] = None
    motion_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    brightness_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    activity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    cooldown_seconds: Optional[int] = Field(None, ge=10, le=3600)
    detector_interval_seconds: Optional[int] = Field(None, ge=1, le=60)
    max_shorts_per_day: Optional[int] = Field(None, ge=1, le=50)
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    min_posting_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    default_tags: Optional[str] = None
    description_template: Optional[str] = None
    safety_gate_enabled: Optional[bool] = None
    raw_clip_retention_days: Optional[int] = Field(None, ge=1, le=365)
    rendered_clip_retention_days: Optional[int] = Field(None, ge=1, le=365)
    snapshot_retention_days: Optional[int] = Field(None, ge=1, le=365)
    openai_api_key: Optional[str] = None  # plaintext, will be encrypted
    ai_model: Optional[str] = None


# --- Endpoints ---

@router.get("/status", response_model=PipelineStatus)
async def get_pipeline_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get ShortForge pipeline status for the dashboard status bar."""
    config = db.query(ShortForgeConfig).first()
    if not config:
        return PipelineStatus()

    now = datetime.now(timezone.utc)

    # Count shorts published today
    shorts_today = (
        db.query(func.count(PublishedShort.id))
        .filter(
            PublishedShort.status == "published",
            func.date(PublishedShort.published_at) == now.date(),
        )
        .scalar() or 0
    )

    # Count moments detected today
    moments_today = (
        db.query(func.count(Moment.id))
        .filter(func.date(Moment.timestamp) == now.date())
        .scalar() or 0
    )

    # Get camera name
    camera_name = None
    if config.camera_id:
        camera = db.query(Camera).filter(Camera.id == config.camera_id).first()
        if camera:
            camera_name = camera.name

    # Determine pipeline state
    state = "disabled"
    if config.enabled:
        state = "running"
        if not config.camera_id:
            state = "error"

    # Calculate disk usage
    from pathlib import Path
    data_dir = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")
    disk_mb = 0
    if data_dir.exists():
        disk_mb = sum(f.stat().st_size for f in data_dir.rglob("*") if f.is_file()) / (1024 * 1024)

    return PipelineStatus(
        enabled=config.enabled,
        camera_id=config.camera_id,
        camera_name=camera_name,
        state=state,
        shorts_today=shorts_today,
        max_shorts_per_day=config.max_shorts_per_day or 6,
        moments_today=moments_today,
        disk_usage_mb=round(disk_mb, 1),
    )


@router.get("/shorts", response_model=list[ShortRead])
async def list_shorts(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List published shorts for the dashboard grid."""
    query = db.query(PublishedShort)
    if status:
        query = query.filter(PublishedShort.status == status)
    shorts = (
        query.order_by(PublishedShort.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []
    for short in shorts:
        clip = db.query(Clip).filter(Clip.id == short.clip_id).first()
        moment = None
        if clip:
            moment = db.query(Moment).filter(Moment.id == clip.moment_id).first()

        results.append(ShortRead(
            id=short.id,
            clip_id=short.clip_id,
            youtube_video_id=short.youtube_video_id,
            title=short.title,
            description=short.description,
            views=short.views or 0,
            published_at=short.published_at,
            status=short.status,
            error_message=short.error_message,
            headline=clip.headline if clip else None,
            rendered_path=clip.rendered_path if clip else None,
            duration_seconds=clip.duration_seconds if clip else None,
            safe_to_publish=clip.safe_to_publish if clip else None,
            moment_id=moment.id if moment else None,
            trigger_type=moment.trigger_type if moment else None,
            score=moment.score if moment else None,
            frame_path=moment.frame_path if moment else None,
            moment_timestamp=moment.timestamp if moment else None,
        ))

    return results


@router.get("/shorts/{short_id}", response_model=ShortRead)
async def get_short_detail(
    short_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detail for a single short (for the slide-over)."""
    short = db.query(PublishedShort).filter(PublishedShort.id == short_id).first()
    if not short:
        raise HTTPException(status_code=404, detail="Short not found")

    clip = db.query(Clip).filter(Clip.id == short.clip_id).first()
    moment = None
    if clip:
        moment = db.query(Moment).filter(Moment.id == clip.moment_id).first()

    return ShortRead(
        id=short.id,
        clip_id=short.clip_id,
        youtube_video_id=short.youtube_video_id,
        title=short.title,
        description=short.description,
        views=short.views or 0,
        published_at=short.published_at,
        status=short.status,
        error_message=short.error_message,
        headline=clip.headline if clip else None,
        rendered_path=clip.rendered_path if clip else None,
        duration_seconds=clip.duration_seconds if clip else None,
        safe_to_publish=clip.safe_to_publish if clip else None,
        moment_id=moment.id if moment else None,
        trigger_type=moment.trigger_type if moment else None,
        score=moment.score if moment else None,
        frame_path=moment.frame_path if moment else None,
        moment_timestamp=moment.timestamp if moment else None,
    )


@router.get("/moments", response_model=list[MomentRead])
async def list_moments(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List detected moments for the moment log table."""
    moments = (
        db.query(Moment)
        .order_by(Moment.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [MomentRead.model_validate(m) for m in moments]


@router.get("/config", response_model=ConfigRead)
async def get_config(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get ShortForge configuration."""
    config = db.query(ShortForgeConfig).first()
    if not config:
        config = ShortForgeConfig()
        db.add(config)
        db.commit()
        db.refresh(config)

    return ConfigRead(
        id=config.id,
        enabled=config.enabled,
        camera_id=config.camera_id,
        motion_threshold=config.motion_threshold if config.motion_threshold is not None else 0.05,
        brightness_threshold=config.brightness_threshold if config.brightness_threshold is not None else 0.15,
        activity_threshold=config.activity_threshold if config.activity_threshold is not None else 0.10,
        cooldown_seconds=config.cooldown_seconds or 120,
        detector_interval_seconds=config.detector_interval_seconds or 5,
        max_shorts_per_day=config.max_shorts_per_day or 6,
        quiet_hours_start=config.quiet_hours_start or "22:00",
        quiet_hours_end=config.quiet_hours_end or "06:00",
        min_posting_interval_minutes=config.min_posting_interval_minutes or 60,
        default_tags=config.default_tags or "",
        description_template=config.description_template or "",
        safety_gate_enabled=config.safety_gate_enabled if config.safety_gate_enabled is not None else True,
        raw_clip_retention_days=config.raw_clip_retention_days or 7,
        rendered_clip_retention_days=config.rendered_clip_retention_days or 30,
        snapshot_retention_days=config.snapshot_retention_days or 3,
        ai_model=config.ai_model or "gpt-4o-mini",
        has_openai_key=bool(config.openai_api_key_enc),
    )


@router.put("/config", response_model=ConfigRead)
async def update_config(
    update: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update ShortForge configuration."""
    config = db.query(ShortForgeConfig).first()
    if not config:
        config = ShortForgeConfig()
        db.add(config)
        db.commit()
        db.refresh(config)

    update_data = update.model_dump(exclude_unset=True)

    # Handle API key encryption
    if "openai_api_key" in update_data:
        key = update_data.pop("openai_api_key")
        if key and key != "••••••••":
            config.openai_api_key_enc = encrypt(key)
        elif not key:
            config.openai_api_key_enc = None

    # Apply remaining fields
    for field, value in update_data.items():
        if hasattr(config, field):
            setattr(config, field, value)

    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)

    logger.info("ShortForge config updated by %s", current_user.username)

    # If enabled state changed, restart scheduler
    if "enabled" in update_data:
        try:
            from services.shortforge.scheduler import get_shortforge_scheduler
            scheduler = get_shortforge_scheduler()
            await scheduler.stop()
            await scheduler.start()
        except Exception:
            logger.exception("Failed to restart ShortForge scheduler after config change")

    return await get_config(db=db, current_user=current_user)


@router.delete("/shorts/{short_id}")
async def delete_short(
    short_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a published short (removes from database, does not delete from YouTube)."""
    short = db.query(PublishedShort).filter(PublishedShort.id == short_id).first()
    if not short:
        raise HTTPException(status_code=404, detail="Short not found")

    short.status = "removed"
    db.commit()
    return {"message": "Short marked as removed"}


@router.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get aggregate stats for the dashboard."""
    total_shorts = db.query(func.count(PublishedShort.id)).filter(PublishedShort.status == "published").scalar() or 0
    total_views = db.query(func.sum(PublishedShort.views)).filter(PublishedShort.status == "published").scalar() or 0
    total_moments = db.query(func.count(Moment.id)).scalar() or 0

    return {
        "total_shorts": total_shorts,
        "total_views": total_views,
        "total_moments": total_moments,
    }
