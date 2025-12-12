"""
ReelForge API endpoints - Automated social media content generation

Note: This is the MVP version focused on content generation only.
Posts are downloaded manually and uploaded by the user to social platforms.
Automatic publishing will be available in VistterStream Cloud.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import base64
import asyncio
import logging

from models.database import get_db, SessionLocal, Camera, Preset, ReelForgeSettings

logger = logging.getLogger(__name__)
from models.reelforge import ReelTemplate, ReelPost, ReelPublishTarget, ReelExport, ReelCaptureQueue
from models.schemas import (
    ReelTemplateCreate, ReelTemplateUpdate, ReelTemplate as ReelTemplateSchema,
    ReelPostCreate, ReelPostQueue, ReelPost as ReelPostSchema, ReelPostWithDetails,
    ReelPublishTargetCreate, ReelPublishTargetUpdate, ReelPublishTarget as ReelPublishTargetSchema,
    ReelExportCreate, ReelExportUpdate, ReelExport as ReelExportSchema,
    CameraWithPresets, Preset as PresetSchema,
    ReelCaptureQueueItem, ReelPostStatus,
    ReelForgeSettingsUpdate, ReelForgeSettings as ReelForgeSettingsSchema,
    ReelForgeSettingsTestResult
)

router = APIRouter(prefix="/api/reelforge", tags=["reelforge"])


# ============================================================================
# Settings Endpoints
# ============================================================================

def _encrypt_api_key(api_key: str) -> str:
    """Simple base64 encoding for API key storage (in production, use proper encryption)"""
    return base64.b64encode(api_key.encode()).decode()


def _decrypt_api_key(encrypted: str) -> str:
    """Decode base64 encoded API key"""
    return base64.b64decode(encrypted.encode()).decode()


@router.get("/settings", response_model=ReelForgeSettingsSchema)
def get_settings(db: Session = Depends(get_db)):
    """Get ReelForge settings"""
    settings = db.query(ReelForgeSettings).first()
    
    # If no settings exist, create default settings
    if not settings:
        settings = ReelForgeSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    # Return with has_api_key flag
    return {
        "id": settings.id,
        "openai_model": settings.openai_model,
        "system_prompt": settings.system_prompt,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "default_template_id": settings.default_template_id,
        "tempest_api_url": settings.tempest_api_url or "http://host.docker.internal:8085",
        "weather_enabled": settings.weather_enabled if settings.weather_enabled is not None else True,
        "has_api_key": bool(settings.openai_api_key_enc),
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }


@router.post("/settings", response_model=ReelForgeSettingsSchema)
def update_settings(
    settings_update: ReelForgeSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update ReelForge settings"""
    settings = db.query(ReelForgeSettings).first()
    
    # If no settings exist, create them
    if not settings:
        settings = ReelForgeSettings()
        db.add(settings)
    
    # Update fields
    if settings_update.openai_api_key is not None:
        if settings_update.openai_api_key == "":
            settings.openai_api_key_enc = None
        else:
            settings.openai_api_key_enc = _encrypt_api_key(settings_update.openai_api_key)
    
    if settings_update.openai_model is not None:
        settings.openai_model = settings_update.openai_model
    
    if settings_update.system_prompt is not None:
        settings.system_prompt = settings_update.system_prompt
    
    if settings_update.temperature is not None:
        settings.temperature = settings_update.temperature
    
    if settings_update.max_tokens is not None:
        settings.max_tokens = settings_update.max_tokens
    
    if settings_update.default_template_id is not None:
        settings.default_template_id = settings_update.default_template_id
    
    if settings_update.tempest_api_url is not None:
        settings.tempest_api_url = settings_update.tempest_api_url
    
    if settings_update.weather_enabled is not None:
        settings.weather_enabled = settings_update.weather_enabled
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    
    return {
        "id": settings.id,
        "openai_model": settings.openai_model,
        "system_prompt": settings.system_prompt,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "default_template_id": settings.default_template_id,
        "tempest_api_url": settings.tempest_api_url or "http://host.docker.internal:8085",
        "weather_enabled": settings.weather_enabled if settings.weather_enabled is not None else True,
        "has_api_key": bool(settings.openai_api_key_enc),
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }


@router.post("/settings/test", response_model=ReelForgeSettingsTestResult)
def test_openai_connection(db: Session = Depends(get_db)):
    """Test the OpenAI connection with current settings"""
    settings = db.query(ReelForgeSettings).first()
    
    if not settings or not settings.openai_api_key_enc:
        return {
            "success": False,
            "message": "No API key configured",
            "model_used": None
        }
    
    try:
        from openai import OpenAI
        
        api_key = _decrypt_api_key(settings.openai_api_key_enc)
        client = OpenAI(api_key=api_key)
        
        # Make a simple test call (v1.0.0+ API)
        response = client.chat.completions.create(
            model=settings.openai_model or "gpt-5-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello' in one word."}
            ],
            max_tokens=10
        )
        
        return {
            "success": True,
            "message": "Connection successful!",
            "model_used": settings.openai_model or "gpt-5-mini"
        }
        
    except ImportError:
        return {
            "success": False,
            "message": "OpenAI package not installed",
            "model_used": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "model_used": None
        }


@router.get("/settings/variables")
def get_template_variables():
    """Get available template variables for use in AI prompts"""
    try:
        from utils.ai_content import get_template_variables
        variables = get_template_variables()
    except ImportError:
        # Fallback if service not available
        variables = {
            "today_date": "Current date (e.g., 'December 11, 2024')",
            "day_of_week": "Day name (e.g., 'Wednesday')",
            "time_of_day": "morning, afternoon, or evening",
            "current_time": "Current time (e.g., '2:45 PM')",
        }
    
    return {
        "variables": variables,
        "usage": "Use {variable_name} in your template prompts to insert dynamic values"
    }


# Variable categories for grouping in the UI
VARIABLE_CATEGORIES = {
    "time": ["today_date", "day_of_week", "time_of_day", "current_time"],
    "weather": ["temperature", "feels_like", "conditions", "humidity", "wind", "wind_gust", 
                "pressure", "pressure_trend", "uv_index", "rain_today", "location"],
    "tides": ["tide_stage", "next_tide", "next_tide_time", "tide_height", "water_temp"],
    "astronomy": ["moon_phase", "moon_illumination", "solunar_major", "solunar_minor"],
    "forecast": ["forecast_high", "forecast_low", "forecast_conditions"]
}


def categorize_variable(key: str) -> str:
    """Determine the category for a variable"""
    for category, keys in VARIABLE_CATEGORIES.items():
        if key in keys:
            return category
    return "other"


@router.get("/settings/variables/live")
def get_live_variables():
    """Get template variables with their current live values from TempestWeather"""
    try:
        from services.weather_data_service import fetch_weather_data_sync, get_available_variables
        
        # Get variable definitions
        variables = get_available_variables()
        
        # Get current values from TempestWeather
        current_values = fetch_weather_data_sync() or {}
        
        # Build response with categories and live values
        result = []
        for key, description in variables.items():
            result.append({
                "key": key,
                "description": description,
                "value": current_values.get(key, "--"),
                "category": categorize_variable(key)
            })
        
        # Sort by category then key
        category_order = ["time", "weather", "tides", "astronomy", "forecast", "other"]
        result.sort(key=lambda x: (category_order.index(x["category"]) if x["category"] in category_order else 99, x["key"]))
        
        return {
            "variables": result,
            "weather_connected": bool(current_values),
            "usage": "Drag variables into text fields to insert {variable_name} syntax"
        }
        
    except Exception as e:
        # Return variables without live values if weather service fails
        try:
            from utils.ai_content import get_template_variables
            variables = get_template_variables()
        except ImportError:
            variables = {
                "today_date": "Current date",
                "day_of_week": "Day name",
                "time_of_day": "morning, afternoon, or evening",
                "current_time": "Current time",
            }
        
        return {
            "variables": [
                {"key": k, "description": v, "value": "--", "category": categorize_variable(k)}
                for k, v in variables.items()
            ],
            "weather_connected": False,
            "error": str(e),
            "usage": "Drag variables into text fields to insert {variable_name} syntax"
        }


@router.post("/settings/weather-test")
def test_weather_connection(db: Session = Depends(get_db)):
    """Test the TempestWeather connection"""
    settings = db.query(ReelForgeSettings).first()
    
    api_url = "http://host.docker.internal:8085"
    if settings and settings.tempest_api_url:
        api_url = settings.tempest_api_url
    
    try:
        import httpx
        
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{api_url}/api/data")
            response.raise_for_status()
            data = response.json()
            
            # Extract a sample of what we got
            current = data.get("current", {})
            temp = current.get("temperature", "N/A")
            conditions = current.get("conditions", "N/A")
            
            return {
                "success": True,
                "message": f"Connected! Current: {temp}, {conditions}",
                "api_url": api_url
            }
            
    except ImportError:
        return {
            "success": False,
            "message": "httpx package not installed",
            "api_url": api_url
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "api_url": api_url
        }


# ============================================================================
# Template Endpoints
# ============================================================================

@router.get("/templates", response_model=List[ReelTemplateSchema])
def get_templates(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all ReelForge templates"""
    query = db.query(ReelTemplate)
    if active_only:
        query = query.filter(ReelTemplate.is_active == True)
    return query.order_by(ReelTemplate.name).all()


@router.get("/templates/{template_id}", response_model=ReelTemplateSchema)
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific template"""
    template = db.query(ReelTemplate).filter(ReelTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates", response_model=ReelTemplateSchema)
def create_template(template_data: ReelTemplateCreate, db: Session = Depends(get_db)):
    """Create a new template"""
    try:
        # Validate camera exists if specified
        if template_data.camera_id:
            camera = db.query(Camera).filter(Camera.id == template_data.camera_id).first()
            if not camera:
                raise HTTPException(status_code=400, detail="Camera not found")
        
        # Validate preset exists and belongs to camera if specified
        if template_data.preset_id:
            preset = db.query(Preset).filter(Preset.id == template_data.preset_id).first()
            if not preset:
                raise HTTPException(status_code=400, detail="Preset not found")
            if template_data.camera_id and preset.camera_id != template_data.camera_id:
                raise HTTPException(status_code=400, detail="Preset does not belong to specified camera")
        
        template = ReelTemplate(
            name=template_data.name,
            description=template_data.description,
            camera_id=template_data.camera_id,
            preset_id=template_data.preset_id,
            clip_duration=template_data.clip_duration,
            pan_direction=template_data.pan_direction.value if template_data.pan_direction else "left_to_right",
            pan_speed=template_data.pan_speed,
            ai_config=template_data.ai_config.model_dump() if template_data.ai_config else {},
            overlay_style=template_data.overlay_style,
            font_family=template_data.font_family,
            font_size=template_data.font_size,
            text_color=template_data.text_color,
            text_shadow=template_data.text_shadow,
            text_background=template_data.text_background,
            text_position_y=template_data.text_position_y,
            publish_mode=template_data.publish_mode.value if template_data.publish_mode else "manual",
            schedule_times=template_data.schedule_times,
            default_title_template=template_data.default_title_template,
            default_description_template=template_data.default_description_template,
            default_hashtags=template_data.default_hashtags
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.put("/templates/{template_id}", response_model=ReelTemplateSchema)
def update_template(
    template_id: int,
    template_data: ReelTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update a template"""
    template = db.query(ReelTemplate).filter(ReelTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        update_dict = template_data.model_dump(exclude_unset=True)
        
        # Handle enum values
        if 'pan_direction' in update_dict and update_dict['pan_direction']:
            update_dict['pan_direction'] = update_dict['pan_direction'].value if hasattr(update_dict['pan_direction'], 'value') else update_dict['pan_direction']
        if 'publish_mode' in update_dict and update_dict['publish_mode']:
            update_dict['publish_mode'] = update_dict['publish_mode'].value if hasattr(update_dict['publish_mode'], 'value') else update_dict['publish_mode']
        
        # Handle ai_config
        if 'ai_config' in update_dict and update_dict['ai_config']:
            update_dict['ai_config'] = update_dict['ai_config'].model_dump() if hasattr(update_dict['ai_config'], 'model_dump') else update_dict['ai_config']
        
        for key, value in update_dict.items():
            setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)
        return template
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a template"""
    template = db.query(ReelTemplate).filter(ReelTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        db.delete(template)
        db.commit()
        return {"message": "Template deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


# ============================================================================
# Post Endpoints
# ============================================================================

@router.get("/posts", response_model=List[ReelPostWithDetails])
def get_posts(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all posts, optionally filtered by status"""
    query = db.query(ReelPost).options(
        joinedload(ReelPost.camera),
        joinedload(ReelPost.preset),
        joinedload(ReelPost.template)
    )
    
    if status:
        query = query.filter(ReelPost.status == status)
    
    posts = query.order_by(ReelPost.created_at.desc()).limit(limit).all()
    
    # Map to response with additional details
    result = []
    for post in posts:
        post_dict = {
            "id": post.id,
            "template_id": post.template_id,
            "status": post.status,
            "error_message": post.error_message,
            "camera_id": post.camera_id,
            "preset_id": post.preset_id,
            "source_clip_path": post.source_clip_path,
            "portrait_clip_path": post.portrait_clip_path,
            "output_path": post.output_path,
            "thumbnail_path": post.thumbnail_path,
            "generated_headlines": post.generated_headlines or [],
            "download_count": post.download_count or 0,
            "created_at": post.created_at,
            "updated_at": post.updated_at,
            "capture_started_at": post.capture_started_at,
            "capture_completed_at": post.capture_completed_at,
            "processing_started_at": post.processing_started_at,
            "processing_completed_at": post.processing_completed_at,
            "camera_name": post.camera.name if post.camera else None,
            "preset_name": post.preset.name if post.preset else None,
            "template_name": post.template.name if post.template else None,
        }
        result.append(post_dict)
    
    return result


@router.get("/posts/{post_id}", response_model=ReelPostWithDetails)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get a specific post"""
    post = db.query(ReelPost).options(
        joinedload(ReelPost.camera),
        joinedload(ReelPost.preset),
        joinedload(ReelPost.template)
    ).filter(ReelPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "id": post.id,
        "template_id": post.template_id,
        "status": post.status,
        "error_message": post.error_message,
        "camera_id": post.camera_id,
        "preset_id": post.preset_id,
        "source_clip_path": post.source_clip_path,
        "portrait_clip_path": post.portrait_clip_path,
        "output_path": post.output_path,
        "thumbnail_path": post.thumbnail_path,
        "generated_headlines": post.generated_headlines or [],
        "download_count": post.download_count or 0,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "capture_started_at": post.capture_started_at,
        "capture_completed_at": post.capture_completed_at,
        "processing_started_at": post.processing_started_at,
        "processing_completed_at": post.processing_completed_at,
        "camera_name": post.camera.name if post.camera else None,
        "preset_name": post.preset.name if post.preset else None,
        "template_name": post.template.name if post.template else None,
    }


@router.post("/posts/queue", response_model=ReelPostSchema)
def queue_capture(
    queue_data: ReelPostQueue,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Queue a new capture request
    
    Trigger modes:
    - 'next_view': Capture when timeline naturally switches to this camera/preset
    - 'scheduled': Capture at the specified scheduled_at time
    """
    try:
        # Validate camera exists
        camera = db.query(Camera).filter(Camera.id == queue_data.camera_id).first()
        if not camera:
            raise HTTPException(status_code=400, detail="Camera not found")

        # Validate preset exists and belongs to camera if specified
        if queue_data.preset_id:
            preset = db.query(Preset).filter(Preset.id == queue_data.preset_id).first()
            if not preset:
                raise HTTPException(status_code=400, detail="Preset not found")
            if preset.camera_id != queue_data.camera_id:
                raise HTTPException(status_code=400, detail="Preset does not belong to specified camera")

        # Validate template exists if specified
        if queue_data.template_id:
            template = db.query(ReelTemplate).filter(ReelTemplate.id == queue_data.template_id).first()
            if not template:
                raise HTTPException(status_code=400, detail="Template not found")
        
        # Validate trigger mode and scheduled_at
        trigger_mode = queue_data.trigger_mode or "next_view"
        if trigger_mode == "scheduled" and not queue_data.scheduled_at:
            raise HTTPException(status_code=400, detail="scheduled_at is required for scheduled trigger mode")

        # Create the post record
        post = ReelPost(
            template_id=queue_data.template_id,
            camera_id=queue_data.camera_id,
            preset_id=queue_data.preset_id,
            status="queued"
        )
        db.add(post)
        db.flush()

        # Create queue entry
        queue_entry = ReelCaptureQueue(
            post_id=post.id,
            camera_id=queue_data.camera_id,
            preset_id=queue_data.preset_id,
            trigger_mode=trigger_mode,
            scheduled_at=queue_data.scheduled_at,
            status="waiting"
        )
        db.add(queue_entry)

        db.commit()
        db.refresh(post)

        return post
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to queue capture: {str(e)}")


@router.get("/posts/{post_id}/download")
def download_post(
    post_id: int,
    target_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Download the generated video file for manual posting
    
    Optionally specify a target_id to get platform-specific metadata (hashtags, etc.)
    """
    post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.status != "ready":
        raise HTTPException(status_code=400, detail=f"Post is not ready for download (status: {post.status})")
    
    if not post.output_path:
        raise HTTPException(status_code=404, detail="Video file not found")
    
    video_path = Path(post.output_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    
    # Increment download count
    post.download_count = (post.download_count or 0) + 1
    
    # Create export record
    export = ReelExport(
        post_id=post_id,
        target_id=target_id,
        status="exported"
    )
    
    # If target specified, get default metadata
    if target_id:
        target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
        if target:
            # Format title from template
            title = target.default_title_template or "{headline_1}"
            if post.generated_headlines and len(post.generated_headlines) > 0:
                title = title.replace("{headline_1}", post.generated_headlines[0].get('text', ''))
            export.title = title
            export.description = target.default_description_template
            export.hashtags = target.default_hashtags
    
    db.add(export)
    db.commit()
    
    # Return the video file
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"reelforge_{post_id}.mp4"
    )


@router.get("/posts/{post_id}/metadata")
def get_post_metadata(
    post_id: int,
    target_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get metadata (title, description, hashtags) for a post
    
    Useful for copying text when manually posting to social platforms.
    Optionally specify target_id to get platform-specific defaults.
    """
    post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Start with headlines
    headlines = post.generated_headlines or []
    headline_1 = headlines[0].get('text', '') if headlines else ''
    
    # Get all headlines as description
    description = "\n".join([h.get('text', '') for h in headlines])
    
    # Default hashtags
    hashtags = "#shorts"
    title = headline_1
    
    # Override with target-specific defaults if provided
    if target_id:
        target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
        if target:
            if target.default_title_template:
                title = target.default_title_template.replace("{headline_1}", headline_1)
            if target.default_description_template:
                description = target.default_description_template + "\n\n" + description
            if target.default_hashtags:
                hashtags = target.default_hashtags
    
    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "headlines": headlines
    }


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    """Delete a post"""
    post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Also delete any queue entries
    db.query(ReelCaptureQueue).filter(ReelCaptureQueue.post_id == post_id).delete()
    
    try:
        db.delete(post)
        db.commit()
        return {"message": "Post deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete post: {str(e)}")


# ============================================================================
# Publish Target Endpoints
# ============================================================================

@router.get("/targets", response_model=List[ReelPublishTargetSchema])
def get_targets(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all publish targets"""
    query = db.query(ReelPublishTarget)
    if active_only:
        query = query.filter(ReelPublishTarget.is_active == True)
    return query.order_by(ReelPublishTarget.name).all()


@router.get("/targets/{target_id}", response_model=ReelPublishTargetSchema)
def get_target(target_id: int, db: Session = Depends(get_db)):
    """Get a specific publish target"""
    target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.post("/targets", response_model=ReelPublishTargetSchema)
def create_target(target_data: ReelPublishTargetCreate, db: Session = Depends(get_db)):
    """Create a new platform preference target
    
    Targets store default metadata (hashtags, description templates) for each platform.
    No OAuth/API credentials needed - posts are downloaded and manually uploaded.
    """
    try:
        target = ReelPublishTarget(
            name=target_data.name,
            platform=target_data.platform.value if hasattr(target_data.platform, 'value') else target_data.platform,
            default_title_template=target_data.default_title_template,
            default_description_template=target_data.default_description_template,
            default_hashtags=target_data.default_hashtags
        )
        db.add(target)
        db.commit()
        db.refresh(target)
        return target
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create target: {str(e)}")


@router.put("/targets/{target_id}", response_model=ReelPublishTargetSchema)
def update_target(
    target_id: int,
    target_data: ReelPublishTargetUpdate,
    db: Session = Depends(get_db)
):
    """Update a publish target"""
    target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    try:
        update_dict = target_data.model_dump(exclude_unset=True)
        
        # Handle enum values
        if 'platform' in update_dict and update_dict['platform']:
            update_dict['platform'] = update_dict['platform'].value if hasattr(update_dict['platform'], 'value') else update_dict['platform']
        
        for key, value in update_dict.items():
            setattr(target, key, value)
        
        target.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(target)
        return target
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update target: {str(e)}")


@router.delete("/targets/{target_id}")
def delete_target(target_id: int, db: Session = Depends(get_db)):
    """Delete a publish target"""
    target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    try:
        db.delete(target)
        db.commit()
        return {"message": "Target deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete target: {str(e)}")


# ============================================================================
# Camera Selection Endpoints (for UI)
# ============================================================================

@router.get("/cameras", response_model=List[CameraWithPresets])
def get_cameras_with_presets(db: Session = Depends(get_db)):
    """Get all cameras with their presets for ReelForge selection UI"""
    cameras = db.query(Camera).options(
        joinedload(Camera.presets)
    ).filter(Camera.is_active == True).order_by(Camera.name).all()
    
    result = []
    for camera in cameras:
        camera_dict = {
            "id": camera.id,
            "name": camera.name,
            "type": camera.type,
            "presets": [
                {
                    "id": p.id,
                    "name": p.name,
                    "pan": p.pan,
                    "tilt": p.tilt,
                    "zoom": p.zoom,
                    "camera_id": p.camera_id,
                    "camera_preset_token": p.camera_preset_token,
                    "created_at": p.created_at
                }
                for p in sorted(camera.presets, key=lambda x: x.name)
            ]
        }
        result.append(camera_dict)
    
    return result


# ============================================================================
# Capture Queue Endpoints
# ============================================================================

@router.get("/queue", response_model=List[ReelCaptureQueueItem])
def get_capture_queue(
    include_failed: bool = True,
    db: Session = Depends(get_db)
):
    """Get current capture queue including waiting and optionally failed items"""
    query = db.query(ReelCaptureQueue).options(
        joinedload(ReelCaptureQueue.camera),
        joinedload(ReelCaptureQueue.preset)
    )
    
    # Include waiting and optionally failed items
    if include_failed:
        query = query.filter(ReelCaptureQueue.status.in_(["waiting", "capturing", "failed"]))
    else:
        query = query.filter(ReelCaptureQueue.status == "waiting")
    
    queue_items = query.order_by(
        ReelCaptureQueue.priority.desc(),
        ReelCaptureQueue.created_at
    ).all()

    result = []
    for item in queue_items:
        result.append({
            "id": item.id,
            "post_id": item.post_id,
            "camera_id": item.camera_id,
            "preset_id": item.preset_id,
            "trigger_mode": item.trigger_mode or "next_view",
            "scheduled_at": item.scheduled_at,
            "status": item.status,
            "priority": item.priority,
            "created_at": item.created_at,
            "expires_at": item.expires_at,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
            "camera_name": item.camera.name if item.camera else None,
            "preset_name": item.preset.name if item.preset else None,
            "error_message": item.error_message,
            "attempt_count": item.attempt_count or 0,
            "last_attempt_at": item.last_attempt_at
        })

    return result


@router.delete("/queue/{queue_id}")
def cancel_queued_capture(queue_id: int, db: Session = Depends(get_db)):
    """Cancel a queued capture request"""
    queue_item = db.query(ReelCaptureQueue).filter(ReelCaptureQueue.id == queue_id).first()
    if not queue_item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    if queue_item.status != "waiting":
        raise HTTPException(status_code=400, detail=f"Cannot cancel - capture already {queue_item.status}")
    
    try:
        # Update associated post status
        post = db.query(ReelPost).filter(ReelPost.id == queue_item.post_id).first()
        if post:
            post.status = "failed"
            post.error_message = "Cancelled by user"
        
        db.delete(queue_item)
        db.commit()
        return {"message": "Capture cancelled"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel capture: {str(e)}")


@router.post("/queue/{queue_id}/trigger")
def trigger_queued_capture(queue_id: int, db: Session = Depends(get_db)):
    """
    Prioritize a queued capture to trigger on next timeline match.
    Sets high priority so it captures next time the camera/preset becomes active.
    """
    queue_item = db.query(ReelCaptureQueue).filter(ReelCaptureQueue.id == queue_id).first()
    if not queue_item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    if queue_item.status not in ["waiting", "failed"]:
        raise HTTPException(status_code=400, detail=f"Cannot trigger - capture is {queue_item.status}")
    
    try:
        # Reset status to waiting if it was failed
        if queue_item.status == "failed":
            queue_item.status = "waiting"
            queue_item.error_message = None
        
        # Set high priority so it's next in line
        queue_item.priority = 100
        
        db.commit()
        return {
            "message": "Capture prioritized - will trigger on next timeline match",
            "queue_id": queue_id,
            "priority": queue_item.priority
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to trigger capture: {str(e)}")


@router.post("/queue/{queue_id}/retry")
def retry_queued_capture(queue_id: int, db: Session = Depends(get_db)):
    """
    Retry a failed capture. Resets status to waiting and clears error.
    """
    queue_item = db.query(ReelCaptureQueue).filter(ReelCaptureQueue.id == queue_id).first()
    if not queue_item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    if queue_item.status != "failed":
        raise HTTPException(status_code=400, detail=f"Can only retry failed captures - status is {queue_item.status}")
    
    try:
        # Reset to waiting status
        queue_item.status = "waiting"
        queue_item.error_message = None
        queue_item.started_at = None
        queue_item.completed_at = None
        # Keep attempt_count to track total attempts
        
        # Also reset the associated post if it was marked failed
        post = db.query(ReelPost).filter(ReelPost.id == queue_item.post_id).first()
        if post and post.status == "failed":
            post.status = "queued"
            post.error_message = None
        
        db.commit()
        return {
            "message": "Capture reset for retry",
            "queue_id": queue_id,
            "attempt_count": queue_item.attempt_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to retry capture: {str(e)}")


@router.post("/queue/{queue_id}/execute")
async def execute_capture_now(
    queue_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Immediately execute a capture with active control:
    1. Pause the timeline (if running)
    2. Move PTZ camera to target preset
    3. Wait for camera to settle
    4. Execute FFmpeg capture
    5. Resume timeline
    
    This is the "Capture Now" action that takes immediate control.
    """
    queue_item = db.query(ReelCaptureQueue).filter(ReelCaptureQueue.id == queue_id).first()
    if not queue_item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    if queue_item.status not in ["waiting", "failed"]:
        raise HTTPException(status_code=400, detail=f"Cannot execute - capture is {queue_item.status}")
    
    # Update status to show we're starting
    queue_item.status = "capturing"
    queue_item.error_message = None
    queue_item.started_at = datetime.utcnow()
    queue_item.attempt_count = (queue_item.attempt_count or 0) + 1
    queue_item.last_attempt_at = datetime.utcnow()
    
    # Update associated post
    post = db.query(ReelPost).filter(ReelPost.id == queue_item.post_id).first()
    if post:
        post.status = "capturing"
        post.error_message = None
    
    db.commit()
    
    # Start the capture in background
    background_tasks.add_task(
        _execute_capture_active,
        queue_id=queue_id,
        camera_id=queue_item.camera_id,
        preset_id=queue_item.preset_id,
        post_id=queue_item.post_id
    )
    
    return {
        "message": "Capture started",
        "queue_id": queue_id,
        "status": "capturing",
        "steps": [
            "Pausing timeline...",
            "Moving camera to preset...",
            "Waiting for settle...",
            "Capturing video...",
            "Resuming timeline..."
        ]
    }


async def _execute_capture_active(
    queue_id: int,
    camera_id: int,
    preset_id: Optional[int],
    post_id: int
):
    """
    Execute the active capture flow:
    1. Pause timeline
    2. Move camera to preset
    3. Wait for settle
    4. Capture
    5. Resume timeline
    """
    import base64
    from services.seamless_timeline_executor import get_seamless_timeline_executor
    from services.ptz_service import get_ptz_service
    from services.reelforge_capture_service import get_reelforge_capture_service
    
    db = SessionLocal()
    timeline_was_running = False
    
    try:
        # Get camera and preset info
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        preset = db.query(Preset).filter(Preset.id == preset_id).first() if preset_id else None
        queue_item = db.query(ReelCaptureQueue).filter(ReelCaptureQueue.id == queue_id).first()
        post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
        
        if not camera:
            raise Exception(f"Camera {camera_id} not found")
        
        # Step 1: Pause the timeline if running
        executor = get_seamless_timeline_executor()
        if executor.is_running():
            timeline_was_running = True
            logger.info(f"📹 ReelForge: Pausing timeline for capture...")
            await executor.pause()
            await asyncio.sleep(1)  # Brief pause
        
        # Step 2: Move camera to preset
        if preset:
            logger.info(f"📹 ReelForge: Moving {camera.name} to preset '{preset.name}'...")
            
            password = None
            if camera.password_enc:
                try:
                    password = base64.b64decode(camera.password_enc).decode()
                except:
                    pass
            
            if password:
                ptz_service = get_ptz_service()
                pan = preset.pan if preset.pan is not None else 0.0
                tilt = preset.tilt if preset.tilt is not None else 0.0
                zoom = preset.zoom if preset.zoom is not None else 1.0
                
                try:
                    await ptz_service.move_to_preset(
                        address=camera.address,
                        port=camera.onvif_port,
                        username=camera.username,
                        password=password,
                        preset_token=preset.camera_preset_token or str(preset_id),
                        pan=pan,
                        tilt=tilt,
                        zoom=zoom,
                    )
                except Exception as e:
                    logger.warning(f"📹 ReelForge: PTZ move warning: {e}")
        
        # Step 3: Wait for camera to settle
        logger.info(f"📹 ReelForge: Waiting for camera settle (3s)...")
        await asyncio.sleep(3)
        
        # Step 4: Execute capture directly via FFmpeg
        logger.info(f"📹 ReelForge: Starting video capture...")
        
        # Get clip duration from template
        clip_duration = 30
        if post and post.template_id:
            template = db.query(ReelTemplate).filter(ReelTemplate.id == post.template_id).first()
            if template:
                clip_duration = template.clip_duration
        
        # Build RTSP URL
        rtsp_password = base64.b64decode(camera.password_enc).decode() if camera.password_enc else None
        if camera.username and rtsp_password:
            rtsp_url = f"rtsp://{camera.username}:{rtsp_password}@{camera.address}:{camera.port}{camera.stream_path}"
        else:
            rtsp_url = f"rtsp://{camera.address}:{camera.port}{camera.stream_path}"
        
        # Create output directory and path
        from pathlib import Path
        clips_dir = Path("/data/uploads/reelforge/clips")
        clips_dir.mkdir(parents=True, exist_ok=True)
        output_path = clips_dir / f"{post_id}.mp4"
        
        # Build FFmpeg command
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-rtsp_transport', 'tcp',
            '-i', rtsp_url,
            '-t', str(clip_duration),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        logger.info(f"📹 ReelForge: Capturing {clip_duration}s from {camera.name}...")
        
        # Execute FFmpeg
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Check result
        if process.returncode == 0 and output_path.exists():
            logger.info(f"📹 ReelForge: Capture complete! Saved to {output_path}")
            
            # Update database
            if post:
                post.source_clip_path = str(output_path)
                post.capture_completed_at = datetime.utcnow()
                post.status = "processing"
            if queue_item:
                queue_item.status = "completed"
                queue_item.completed_at = datetime.utcnow()
            db.commit()
            
            # Trigger processing pipeline
            logger.info(f"📹 ReelForge: Triggering processing pipeline...")
            try:
                from services.reelforge_processor import get_reelforge_processor
                processor = get_reelforge_processor()
                asyncio.create_task(processor.process_post(post_id))
            except Exception as proc_error:
                logger.error(f"📹 ReelForge: Failed to trigger processing: {proc_error}")
                # Set to ready anyway so user can access raw clip
                if post:
                    post.status = "ready"
                    db.commit()
        else:
            error_msg = stderr.decode()[:500] if stderr else "Unknown error"
            raise Exception(f"FFmpeg failed: {error_msg}")
        
    except Exception as e:
        logger.error(f"📹 ReelForge: Active capture failed: {e}")
        
        # Update status to failed
        try:
            queue_item = db.query(ReelCaptureQueue).filter(ReelCaptureQueue.id == queue_id).first()
            post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
            
            if queue_item:
                queue_item.status = "failed"
                queue_item.error_message = str(e)[:500]
                queue_item.completed_at = datetime.utcnow()
            
            if post:
                post.status = "failed"
                post.error_message = str(e)[:500]
            
            db.commit()
        except:
            pass
    
    finally:
        # Step 5: Resume timeline if it was running
        if timeline_was_running:
            logger.info(f"📹 ReelForge: Resuming timeline...")
            try:
                executor = get_seamless_timeline_executor()
                await executor.resume()
            except Exception as e:
                logger.warning(f"📹 ReelForge: Could not resume timeline: {e}")
        
        db.close()


# ============================================================================
# Export Tracking Endpoints
# ============================================================================

@router.get("/posts/{post_id}/exports", response_model=List[ReelExportSchema])
def get_post_exports(post_id: int, db: Session = Depends(get_db)):
    """Get all export records for a post (download history)"""
    post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return post.exports


@router.put("/exports/{export_id}", response_model=ReelExportSchema)
def update_export(
    export_id: int,
    export_data: ReelExportUpdate,
    db: Session = Depends(get_db)
):
    """Update an export record (e.g., mark as posted, add platform URL)
    
    Use this after manually posting to a platform to track where it was shared.
    """
    export = db.query(ReelExport).filter(ReelExport.id == export_id).first()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    
    try:
        if export_data.status:
            export.status = export_data.status.value if hasattr(export_data.status, 'value') else export_data.status
            if export_data.status == "posted":
                export.posted_at = datetime.utcnow()
        
        if export_data.platform_url:
            export.platform_url = export_data.platform_url
        
        db.commit()
        db.refresh(export)
        return export
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update export: {str(e)}")
